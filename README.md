# 🚦 Smart Traffic Control System using Raspberry Pi 5

A project to simulate a **Smart Traffic Light System** using Raspberry Pi 5, OpenCV, and YOLO object detection. This system detects and prioritizes traffic (toy cars) using computer vision, mimicking how real-world intelligent traffic systems work.

<br>

## 🛠️ Technologies Used

- **Hardware:**
  - Raspberry Pi 5
  - Raspberry Pi Camera Module (IMX219)
  - Toy Cars
  - LEDs (to simulate traffic lights)
  - Jumper Wires, Breadboard

- **Software:**
  - Python
  - OpenCV
  - YOLOv8 (via Ultralytics)
  - GPIO (Raspberry Pi GPIO control)
  - libcamera

<br>

## 🎯 Project Goals

- Detect toy cars on a mini road setup using a Pi Camera.
- Prioritize lanes with more cars using real-time object detection.
- Control LED signals (traffic lights) based on detected traffic density.
- Build a small-scale simulation mimicking smart traffic control.

<br>

## 🧰 Setup Instructions

1. **Clone the repository:**

    ```bash
    git clone https://github.com/your-username/smart-traffic-control.git
    cd smart-traffic-control
    ```

2. **Install dependencies:**

    ```bash
    pip install -r requirements.txt
    Create a service account key (secret) .json file and place it next to the python script.
    ```

3. **Connect your hardware:**

    - Connect the Raspberry Pi Camera (IMX219) to the CSI port.
    - Wire up LEDs to Arduino or ESP32.
    - Place toy cars on the road simulation for detection.

4. **Run the system:**

    ```bash
    Copy and paste the code into a ide of your choice (ie: Thonny) or use the terminal
    ```

<br>

## 📷 Sample Output

<video width="500" controls>
    <source src="sample video/traffic test.mp4" type="video/mp4">
    
</video>
<img src="samples/sample_img.png" width="500" alt="Sample Detection image">

<br>

## ⚙️ File Structure

```bash
smart-traffic-control/
|   README.md
|
+---Ai Data
|   |   data.yaml
|   |   yolov8n.pt
|   |   yolo_train_val_split.py
|   |
|   +---data
|   |   +---train
|   |   |   |   labels.cache
|   |   |   |
|   |   |   +---images
|   |   |   |
|   |   |   \---labels
|   |   |   
|   |   \---validation
|   |       |   labels.cache
|   |       |
|   |       +---images
|   |       |
|   |       \---labels
|   \---runs
|       \---detect
|           \---train20
|               
|
\---Scripts
    +---led control
    |   +---arduino nano (wired - over usb)
    |   |   \---trafficcontrol_nano
    |   |           trafficcontrol_nano.ino
    |   |
    |   \---Esp32
    |       \---ble_lights_2
    |               ble_lights_2.ino
    |
    \---Raspberry Pi
            detection boxes with score and go + cvs+ wired leds.py
            Final Traffic control script.py
```
<br>

⚡ Future Improvements
<ul>
<li>Use real-time vehicle tracking for smoother light transitions.</li>

<li>Integrate cloud logging of traffic patterns.</li>

<li>Add pedestrian detection for crosswalk signals.</li>
</ul>
<br>
🧠 Credits
Made by GameRiot64 
Powered by Raspberry Pi and OpenCV
