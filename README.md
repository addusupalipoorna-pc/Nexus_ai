# Advanced Object Detection & Multi-Object Tracking Desktop Application

A commercial-grade surveillance and monitoring desktop application that provides real-time Object Detection and Multi-Object Tracking (MOT) using YOLOv8 and a custom Deep SORT implementation. 

Designed with a high-end, cyber-security inspired dark user interface using PyQt6, it features live analytics, tracking trails, motion density heatmaps, performance graphs, video recording, screenshots, and alert triggers.

---

## Key Features

1. **Dual Capture Core**: Supports live webcams, IP RTSP streams, and local video file inputs. Includes a **Synthetic Simulator** fallback that simulates moving targets with tracking data if no camera is available.
2. **Deep SORT Tracker**: Implements a robust state-estimation Kalman Filter and Hungarian data-association algorithm using:
   - Cosine distance of **HSV Color Histograms** (visual signatures)
   - Intersection-over-Union (IoU) spatial overlap
   - Mahalanobis state-covariance gating
3. **Live Telemetry & Dashboard**: Displays active tracked IDs, system FPS, average model confidence, and itemized class counts in real time.
4. **Security Alert HUD**: Triggers notifications and audible sound alarms when custom rules are violated (e.g. Person overflow, vehicle detected).
5. **Analytical Hub**: Features rolling PyQtGraph charts for CPU/Memory telemetry and object counts, plus a database search/filter system connected to a SQLite back-end.
6. **Capture Modules**:
   - **Video Recorder**: Exports processed streams to high-quality MP4 formats (`/recordings`).
   - **Screenshots**: Captures raw or annotated views as PNGs (`/screenshots`).
   - **CSV Reports**: Exports historical logs containing timestamp, tracking ID, label, and confidence (`/exports`).

---

## Project Structure

```text
CodeAlpha_ObjectDetection/
├── database/
│   ├── db_manager.py       # SQLite database manager
│   └── logs.db             # SQLite database file (generated)
│
├── detection/
│   ├── camera.py           # Capture & processing QThread
│   ├── detector.py         # YOLOv8 model wrapper
│   └── tracker.py          # Kalman Filter + Deep SORT association
│
├── ui/
│   ├── dashboard.py        # Live view, stats, controls, alerts UI
│   ├── analytics.py        # PyQtGraph charts & log table UI
│   └── settings.py         # Camera sources & threshold UI
│
├── models/
│   └── yolov8n.pt          # YOLOv8 weight file (auto-downloaded)
│
├── recordings/             # Saved mp4 videos (generated)
├── screenshots/            # Saved png captures (generated)
├── exports/                # Saved csv reports (generated)
│
├── app.py                  # Main entrypoint
├── requirements.txt        # Project dependencies
└── README.md               # Documentation
```

---

## Installation & Setup

### Prerequisites
- Python 3.11+
- Windows OS (for winsound alert system)

### Setup Virtual Environment & Install Dependencies

```bash
# Clone the repository & navigate to workspace root
cd CodeAlpha_ObjectDetection

# Initialize virtual environment
python -m venv .venv

# Activate virtual environment
# On Windows PowerShell:
.venv\Scripts\Activate.ps1
# On Command Prompt:
.venv\Scripts\activate.bat

# Install packages
pip install -r requirements.txt
```

---

## How to Run

Run the application using your virtual environment Python:

```bash
python app.py
```

### Operations Guide
1. **Initiate Feed**: Choose the source from **CORE SETTINGS** (e.g. "Synthetic Simulator" for immediate test visualizer), then go to **LIVE TELEMETRY** and click **START CORE**.
2. **Controls**: Use **PAUSE** to freeze processing, **RECORD** to capture MP4 outputs, and **SCREENSHOT** to capture high-definition frames.
3. **Analytics**: Switch to **ANALYTICS HUB** to inspect historical database records, search specific tracking IDs, filter by class, export reports, or monitor live system resource graphs.
4. **Settings**: Adjust model confidence thresholds, overlay options (trails, heatmap opacity), and safety alarm thresholds dynamically.
