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
    ```

3. **Connect your hardware:**

    - Connect the Raspberry Pi Camera (IMX219) to the CSI port.
    - Wire up LEDs to GPIO pins (check `config.py` for pin numbers).
    - Place toy cars on the road simulation for detection.

4. **Run the system:**

    ```bash
    python3 traffic_control.py
    ```

<br>

## 📷 Sample Output

<img src="docs/output_frame.jpg" width="500" alt="Sample Detection Frame">

<br>

## ⚙️ File Structure

```bash
smart-traffic-control/
├── camera/
│   └── capture.py        # Handles camera input using libcamera
├── detection/
│   └── yolo_detect.py    # Runs YOLOv8 on incoming frames
├── control/
│   └── traffic_light.py  # Logic to control GPIO traffic lights
├── config.py             # Config for pins, thresholds, paths
├── traffic_control.py    # Main script
├── requirements.txt
└── README.md

<br>

⚡ Future Improvements
Use real-time vehicle tracking for smoother light transitions.

Integrate cloud logging of traffic patterns.

Add pedestrian detection for crosswalk signals.

<br>
🧠 Credits
Made by GameRiot64 
Powered by Raspberry Pi and OpenCV