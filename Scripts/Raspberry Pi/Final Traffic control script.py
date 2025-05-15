import cv2
import time
import math
import json
import os
import csv
import threading
import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo
from picamera2 import Picamera2
from ultralytics import YOLO
import numpy as np
from bleak import BleakClient

# ── Configuration ─────────────────────────────────────────────────────────────
CONFIG_PATH           = 'regions_config.json'
LOG_PATH              = 'vehicle_logs.csv'
SERVICE_ACCOUNT_FILE  = 'iot-project-group-ad-b9cb9dc874cc.json'
DRIVE_FOLDER_ID       = '1qxxCRspImrUp2oobBgObGJrBxhf8CW4y'
SCOPES                = ['https://www.googleapis.com/auth/drive.file']
TZ                    = ZoneInfo('Asia/Colombo')
miss                  = 5    # frames to wait before declaring exit

# Lane-to-LED mapping: lane_index → LED number on ESP32
LED_PINS = {
    0: 3,  # Lane 0 → LED #1
    1: 1,  # Lane 1 → LED #2
    2: 2,  # Lane 2 → LED #4
    3: 4,  # Lane 3 → LED #3
}

# Scoring weights (tune to your needs)
W_WAIT   = 0.5   # weight for live wait time
W_QUEUE  = 1.0   # weight for current queue length
W_EMERG  = 2.0   # weight for live emergency priority

# Emergency class priorities
priority_weights = {
    'fire truck':   2,
    'police car':   4,
    # add more if needed
}

# Minimum green/hold settings
alpha      = 0.2   # smoothing factor: lower = smoother
min_hold_s = 5.0   # seconds to hold green after last EMS leaves

# ── BLE CENTRAL SETUP ─────────────────────────────────────────────────────────
ESP32_MAC           = "ec:da:3b:bd:60:ce"
CHARACTERISTIC_UUID = "abcdef01-1234-5678-1234-56789abcdef0"

ble_client = None
ble_loop   = None

# track last state per lane so we only send on change
last_states = {lane: None for lane in LED_PINS}

async def ble_client_loop():
    global ble_client
    while True:
        try:
            async with BleakClient(ESP32_MAC) as client:
                ble_client = client
                print(f"[BLE] Connected to {ESP32_MAC}")
                await client.is_connected()
        except Exception as e:
            print(f"[BLE] Connection failed: {e}")
        print("[BLE] Disconnected; retrying in 5s...")
        await asyncio.sleep(5)

def start_ble_thread():
    global ble_loop
    ble_loop = asyncio.new_event_loop()
    t = threading.Thread(
        target=lambda: ble_loop.run_until_complete(ble_client_loop()),
        daemon=True
    )
    t.start()

start_ble_thread()

def send_led_states(active_lane, counts):
    """
    Send ON to the active_lane (if it has vehicles), OFF to others,
    but only when the desired state differs from last sent.
    """
    if not ble_client or not ble_client.is_connected:
        return

    for lane_idx, led_num in LED_PINS.items():
        want = "ON" if (lane_idx == active_lane and counts[lane_idx] > 0) else "OFF"
        if want != last_states[lane_idx]:
            cmd = f"{led_num}:{want}".encode()
            asyncio.run_coroutine_threadsafe(
                ble_client.write_gatt_char(CHARACTERISTIC_UUID, cmd),
                ble_loop
            )
            last_states[lane_idx] = want

# ── Google Drive Upload Helpers (unchanged) ─────────────────────────────────
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

def init_drive_service():
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES
    )
    return build('drive', 'v3', credentials=creds)

drive_service = init_drive_service()

def sort_logs():
    if not os.path.isfile(LOG_PATH):
        return
    with open(LOG_PATH, newline='') as f:
        rows = list(csv.DictReader(f))
    rows.sort(key=lambda r: (
        r['date'],
        r['arrival_time'] or '00:00:00',
        r['exit_time']   or '00:00:00'
    ))
    with open(LOG_PATH, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=[
            'date','vehicle_id','type','lane',
            'arrival_time','exit_time','wait_time_s'
        ])
        w.writeheader()
        w.writerows(rows)

def upload_to_drive(path, service, folder_id):
    sort_logs()
    q = f"name='{os.path.basename(path)}' and '{folder_id}' in parents and trashed=false"
    files = service.files().list(q=q, spaces='drive').execute().get('files', [])
    media = MediaFileUpload(path, mimetype='text/csv')
    if files:
        service.files().update(fileId=files[0]['id'], media_body=media).execute()
    else:
        meta = {'name': os.path.basename(path), 'parents': [folder_id]}
        service.files().create(body=meta, media_body=media, fields='id').execute()

def drive_thread():
    while True:
        try:
            upload_to_drive(LOG_PATH, drive_service, DRIVE_FOLDER_ID)
        except:
            pass
        time.sleep(60)

threading.Thread(target=drive_thread, daemon=True).start()

# ── Geometry Helpers ─────────────────────────────────────────────────────────
def rotate_point(x, y, cx, cy, angle):
    t = math.radians(angle)
    dx, dy = x - cx, y - cy
    return (
        dx*math.cos(t) - dy*math.sin(t) + cx,
        dx*math.sin(t) + dy*math.cos(t) + cy
    )

def iou(a, b):
    x1, y1 = max(a[0], b[0]), max(a[1], b[1])
    x2, y2 = min(a[2], b[2]), min(a[3], b[3])
    inter = max(0, x2-x1) * max(0, y2-y1)
    union = ((a[2]-a[0])*(a[3]-a[1]) + (b[2]-b[0])*(b[3]-b[1]) - inter)
    return inter/union if union > 0 else 0

# ── Region Class ─────────────────────────────────────────────────────────────
class Region:
    def __init__(self, x, y, w, h, angle=0):
        self.x, self.y, self.w, self.h = x, y, w, h
        self.angle = angle
        self.locked = False

    def get_corners(self):
        pts = [
            (self.x, self.y),
            (self.x+self.w, self.y),
            (self.x+self.w, self.y+self.h),
            (self.x, self.y+self.h)
        ]
        cx, cy = self.x + self.w/2, self.y + self.h/2
        return [rotate_point(x, y, cx, cy, self.angle) for x, y in pts]

    def contains(self, px, py):
        corners = self.get_corners()
        cnt = 0
        for i in range(4):
            x1,y1 = corners[i]
            x2,y2 = corners[(i+1)%4]
            if (y1>py) != (y2>py):
                xin = (x2-x1)*(py-y1)/(y2-y1) + x1
                if px < xin:
                    cnt += 1
        return (cnt % 2)==1

    def draw(self, frame, label=''):
        pts = np.array(self.get_corners(), dtype=np.int32).reshape(-1,1,2)
        cv2.polylines(frame, [pts], True, (0,255,0), 2)
        if label:
            x0,y0 = pts[0][0]
            cv2.putText(frame, label, (x0+5,y0-10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,255,0), 2)

# ── Load/Save Config ─────────────────────────────────────────────────────────
def load_config():
    if os.path.isfile(CONFIG_PATH):
        with open(CONFIG_PATH) as f:
            data = json.load(f)
        return [Region(**d) for d in data]
    return [Region(50+i*250, 50, 200,200) for i in range(4)]

def save_config():
    with open(CONFIG_PATH,'w') as f:
        json.dump([
            {'x':r.x, 'y':r.y, 'w':r.w, 'h':r.h, 'angle':r.angle}
            for r in regions
        ], f)

# ── Camera & Model ───────────────────────────────────────────────────────────
picam2 = Picamera2()
picam2.preview_configuration.main.size   = (1000,1000)
picam2.preview_configuration.main.format = 'RGB888'
picam2.preview_configuration.align()
picam2.configure('live view')
picam2.start()

model       = YOLO('/home/gr64/all_vehicles/best_ncnn_model')
class_names = model.names
regions     = load_config()

# ── Tracking State & Priority Helpers ───────────────────────────────────────
track_meta        = {}
emergency_entries = {i: [] for i in range(len(regions))}
smoothed_scores   = [0.0] * len(regions)
last_ems_exit     = [None] * len(regions)
current_green     = 0
green_start       = time.time()

# ── Mouse Callbacks ─────────────────────────────────────────────────────────
selected = None
mode     = None
def mouse(event, x, y, flags, param):
    global selected, mode
    if event == cv2.EVENT_LBUTTONDOWN:
        for r in reversed(regions):
            tr = r.get_corners()[1]
            br = r.get_corners()[2]
            if not r.locked and math.hypot(x-tr[0], y-tr[1])<10:
                selected,mode = r,'rotate'; return
            if not r.locked and math.hypot(x-br[0], y-br[1])<15:
                selected,mode = r,'resize'; return
            if r.contains(x,y):
                selected,mode = r,'move'; return
    elif event == cv2.EVENT_MOUSEMOVE and selected and mode and not selected.locked:
        getattr(selected, mode)(x,y)
    elif event == cv2.EVENT_LBUTTONUP:
        selected,mode = None,None

cv2.namedWindow('Live Preview')
cv2.setMouseCallback('Live Preview', mouse)

# Open CSV for appending
log_exists = os.path.isfile(LOG_PATH)
csv_file   = open(LOG_PATH, 'a', newline='')
csv_w      = csv.DictWriter(csv_file, fieldnames=[
    'date','vehicle_id','type','lane','arrival_time','exit_time','wait_time_s'
])
if not log_exists:
    csv_w.writeheader()

interval, show_fps, flip_h, flip_v = 1/30, True, False, True

while True:
    start = time.time()
    frame = picam2.capture_array()
    if flip_h: frame = cv2.flip(frame,1)
    if flip_v: frame = cv2.flip(frame,0)

    # 1) Run detection & filtering
    res       = model.track(frame, persist=True)
    annotated = res[0].plot()
    now       = time.time()
    date_s    = datetime.now(TZ).strftime('%Y-%m-%d')

    # 2) Build filtered list & counts
    filtered = []
    counts   = [0]*len(regions)
    for d in res[0].boxes:
        if d.id is None or d.cls is None:
            continue
        xy = d.xyxy[0].tolist()
        c  = int(d.cls)
        if not any(int(f.cls)==c and iou(xy, f.xyxy[0].tolist())>0.5 for f in filtered):
            filtered.append(d)

    # ——— Log exits to CSV —————————————————————————————————————
    live_ids = {int(d.id) for d in filtered}
    for vid, m in list(track_meta.items()):
        for lane_idx, entry_ts in list(m.get('entry', {}).items()):
            if vid not in live_ids:
                exit_ts = now
                wait_s  = exit_ts - entry_ts
                csv_w.writerow({
                    'date'        : date_s,
                    'vehicle_id'  : vid,
                    'type'        : m['label'][lane_idx],
                    'lane'        : lane_idx,
                    'arrival_time': datetime.fromtimestamp(entry_ts, TZ).strftime('%H:%M:%S'),
                    'exit_time'   : datetime.fromtimestamp(exit_ts, TZ).strftime('%H:%M:%S'),
                    'wait_time_s' : f"{wait_s:.2f}"
                })
                csv_file.flush()
                del m['entry'][lane_idx]
    # ——————————————————————————————————————————————————————————

    # 3) Live metrics & record emergency entries
    live_wait      = [0.0]*len(regions)
    live_emergency = [0]*len(regions)

    for det in filtered:
        vid, cls = int(det.id), int(det.cls)
        label    = class_names[cls]
        x1,y1,x2,y2 = det.xyxy[0]
        cx,cy      = int((x1+x2)/2), int((y1+y2)/2)

        if vid not in track_meta:
            track_meta[vid] = {'entry':{}, 'label':{}}
        m = track_meta[vid]

        for i, r in enumerate(regions):
            if r.contains(cx, cy):
                counts[i] += 1
                if i not in m['entry']:
                    m['entry'][i] = now
                    m['label'][i] = label
                live_wait[i] += now - m['entry'][i]
                if label in priority_weights:
                    live_emergency[i] += priority_weights[label]
                    if m['entry'][i] not in emergency_entries[i]:
                        emergency_entries[i].append(m['entry'][i])

    # 4) Compute raw scores with EMS override
    raw_scores = []
    for i in range(len(regions)):
        if emergency_entries[i]:
            earliest = min(emergency_entries[i])
            score = 1e6 + (now - earliest)
        else:
            score = (W_WAIT * live_wait[i] +
                     W_QUEUE * counts[i] +
                     W_EMERG * live_emergency[i])
        raw_scores.append(score)

    # 5) Exponential smoothing
    for i in range(len(regions)):
        smoothed_scores[i] = alpha * raw_scores[i] + (1-alpha) * smoothed_scores[i]

    # 6) Track EMS exit times
    has_ems = [bool(emergency_entries[i]) for i in range(len(regions))]
    for i in range(len(regions)):
        if not has_ems[i] and last_ems_exit[i] is None:
            last_ems_exit[i] = now
        elif has_ems[i]:
            last_ems_exit[i] = None

    # 7) Choose green with hold logic
    time_on = now - green_start
    if time_on < min_hold_s:
        chosen = current_green
    else:
        chosen = max(range(len(regions)), key=lambda j: smoothed_scores[j])
        if (last_ems_exit[chosen] is not None and
            now - last_ems_exit[chosen] < min_hold_s):
            chosen = current_green
    if chosen != current_green:
        current_green = chosen
        green_start   = now

    # ── BLE LED Update ────────────────────────────────────────────────────────
    # Send ON to the chosen lane, OFF to others (only on actual change)
    send_led_states(current_green, counts)

    # 8) Scoreboard overlay (black box + white Lane labels)
    sb_x, sb_y = 10, 10
    line_h     = 20
    cv2.rectangle(annotated,
                  (sb_x-5, sb_y-5),
                  (sb_x+200, sb_y+line_h*len(regions)+5),
                  (0,0,0), cv2.FILLED)
    for idx, sc in enumerate(smoothed_scores):
        cv2.putText(annotated,
                    f"Lane {idx}: {sc:.1f}",
                    (sb_x, sb_y + line_h*(idx+1) - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,255), 1)

    # 9) Draw regions + 'GO' only when vehicles present
    for i, r in enumerate(regions):
        r.draw(annotated, f"#{i}")
        if i == current_green and counts[i] > 0:
            corners = r.get_corners()
            xs, ys = zip(*corners)
            cx, cy = int(sum(xs)/4), int(sum(ys)/4)
            cv2.putText(annotated, "GO",
                        (cx-30, cy+10),
                        cv2.FONT_HERSHEY_DUPLEX, 1.5, (0,255,0), 3)

    # 10) FPS overlay top-right
    if show_fps:
        fps = 1000 / res[0].speed['inference']
        h, w = annotated.shape[:2]
        cv2.putText(annotated, f"FPS:{fps:.1f}",
                    (w-150, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 2)

    cv2.imshow('Live Preview', annotated)

    # 11) Key handling
    k = cv2.waitKey(1) & 0xFF
    if   k == ord('q'): break
    elif k == ord('h'): flip_h    = not flip_h
    elif k == ord('v'): flip_v    = not flip_v
    elif k == ord('l') and selected: selected.locked = not selected.locked
    elif k == ord('f'): show_fps  = not show_fps

    # 12) Maintain frame rate
    dt = time.time() - start
    if dt < interval:
        time.sleep(interval - dt)

# ── Cleanup ───────────────────────────────────────────────────────────────────
save_config()
csv_file.close()
cv2.destroyAllWindows()
