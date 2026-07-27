# Sentinel — Smart Surveillance System

> A production-grade, AI-powered surveillance platform that turns any RTSP camera into an intelligent monitoring system with **real-time object detection**, **face recognition**, and **automatic visitor tracking** — all running locally on your GPU with zero cloud dependency.

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg)
![YOLO11](https://img.shields.io/badge/YOLO-11s-00FFFF.svg)
![InsightFace](https://img.shields.io/badge/InsightFace-Buffalo--L-orange.svg)
![CUDA](https://img.shields.io/badge/CUDA-12.x-76B900.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

---

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Screenshots](#screenshots)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [API Reference](#api-reference)
- [How It Works](#how-it-works)
- [Performance](#performance)
- [Development](#development)
- [Troubleshooting](#troubleshooting)
- [Roadmap](#roadmap)
- [License](#license)

> 📖 **Looking for a user guide, scenario walkthroughs, or deployment patterns?**
> See **[`CATALOG.md`](./CATALOG.md)** (English) or **[`CATALOG_AR.md`](./CATALOG_AR.md)** (العربية) — the complete system catalogs with real-world scenarios, dashboard walkthroughs, configuration reference, and best practices.

---

## Overview

**Sentinel** is a self-hosted security and surveillance dashboard that uses state-of-the-art computer vision to:

1. **Detect** people, phones, bags, and weapons in real time from any RTSP camera
2. **Recognize** registered faces with a single match
3. **Auto-register** unknown visitors with unique IDs and snapshots
4. **Re-identify** returning visitors across angles, lighting, and time
5. **Alert** on threats (knives, scissors) with visual + dashboard indicators

Everything runs **locally on your machine** — no data leaves your network, no cloud subscriptions, no rate limits.

Built with **Clean Architecture** principles for maintainability and extensibility.

---

## Key Features

### 🎯 Real-Time Object Detection
- Powered by **YOLO11s** (18.4MB) on CUDA
- Detects: **persons**, **cell phones**, **backpacks**, **handbags**, **knives**, **scissors**
- Per-class confidence thresholds (lower for small objects like phones)
- Inference at **1280×1280** for small-object accuracy
- ~25ms per frame on RTX 3060 (40 FPS capability)

### 👤 Intelligent Face Recognition
- **InsightFace** with **ArcFace-R100** (Buffalo-L pack, ONNX)
- GPU-accelerated via **ONNX Runtime + CUDA**
- 512-d normalized embeddings with **cosine similarity** matching
- **~16ms per frame** on RTX 3060

### 🆔 Smart Visitor Tracking (auto-registration)
- When an unknown face appears → **auto-registered** with `person_NNN` ID
- Cropped face snapshot saved to disk
- Returning visitors recognized across:
  - Different angles
  - Different lighting
  - Across days
- **Multi-embedding fingerprint**: each person accumulates up to 8 reference embeddings
- **Quality gates** prevent junk registrations (size ≥ 80px, blur check, detection score)
- **Temporal cooldown** prevents duplicate registrations from frame jitter

### 🎨 Modern Dashboard UI
- Sidebar navigation with live badge counts
- 4 live stat cards (persons, phones, bags, threats)
- MJPEG stream with fullscreen + screenshot
- Live recognition panel (known / returning / new)
- Faces registry with promote-to-known flow
- **Alerts tab** with real-time threat feed (WebSocket-pushed)
- Settings with live save

### 🚨 Threat Detection & Alerts
- **Weapon detection** via fine-tuned YOLOv8s (`gun.pt`, 17 violent Kinetics-400 classes)
- **Pose estimation** with YOLOv8n-Pose (17 keypoints per person)
- **Action recognition** via R3D-18 (3D ResNet, Kinetics-400) — sliding 16-frame window
- **Rule engine** combines all signals:
  - Weapon (high/critical)
  - Violence classification (high)
  - Pose + proximity (medium)
  - Escalation bonus when multiple signals co-occur
- **Real-time WebSocket** pushes new threats to the dashboard
- **Snapshot on alert** saved to `data/alerts/YYYY-MM-DD/`
- **5-second cooldown** per (type, level, region) to prevent spam
- **4 threat levels**: low / medium / high / critical

### 📱 Item Tracking & Theft Detection
- **IoU-based tracker** keeps ID-stable per item across frames (no DeepSORT overhead)
- **Ownership state machine** per item: `NEW → STATIONARY → HELD → STATIONARY → ABANDONED`
- **Five ownership rules**:
  - **Claim** — held by a person for ≥ 1.5s → ownership assigned
  - **Drop** — owner walks away → state returns to STATIONARY (memory preserved)
  - **Theft (mismatch)** — stranger is near + item disappears for ≥ 3s → THEFT event
  - **Theft (unowned)** — unknown item disappears for ≥ 3s → THEFT event
  - **Abandoned** — owner leaves item for ≥ 30s → ABANDONED event
- **Escalation** — THEFT events are mirrored to the threat dashboard at HIGH level
- **Persistence** — items + event log survive restarts (`data/items.json`, `data/items_log.json`)
- **WebSocket** live feed (`/ws/items`) for new claim/drop/theft events
- **Forensic snapshot** on every theft event saved to `data/alerts/YYYY-MM-DD/`
- **Items tab UI** — live table, ownership filter, event timeline with toast notifications

### 🏗️ Clean Architecture
```
src/
├── domain/          # Pure entities & interfaces (no I/O)
│   ├── entities/    # CameraConfig, CameraInfo
│   └── interfaces/  # StreamRepository, DetectionRepository, FaceRepository
├── usecases/        # Business logic (orchestration)
├── adapters/        # I/O implementations
│   ├── rtsp/        # OpenCV RTSP reader
│   ├── yolo/        # YOLODetectionRepository
│   ├── insightface/ # InsightFaceRepository (GPU)
│   └── ...
├── presentation/    # FastAPI routes, templates, static
└── config/          # Pydantic settings
```

### ⚡ Performance Optimizations
- **Threaded RTSP reader** (always latest frame, no lag)
- **GPU inference** for both YOLO and InsightFace
- **CUDA runtime piggy-backing** — uses PyTorch's bundled CUDA libs
- **Cancellable streaming** — clean shutdown, no leaked threads
- **Per-class confidence** — fewer false positives, more true positives

### 🎁 UX Polish
- Toast notifications (success/error/warning)
- Modal confirmations (no ugly `confirm()`)
- Empty states with helpful guidance
- Live clock in top bar
- Connection status indicator
- Loading spinners
- Time-ago formatting for visitor lists

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                       Browser (UI)                          │
│  HTML / CSS (modular) / Vanilla JS (modular) / MJPEG        │
└──────────────────┬──────────────────────────────────────────┘
                   │ HTTP
┌──────────────────▼──────────────────────────────────────────┐
│                  FastAPI Application                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐     │
│  │ /api/stream │  │ /api/faces  │  │ /api/settings   │     │
│  │ (MJPEG)     │  │ /api/detect │  │                 │     │
│  └──────┬──────┘  └──────┬──────┘  └────────┬────────┘     │
└─────────┼────────────────┼──────────────────┼─────────────┘
          │                │                  │
┌─────────▼────────────────▼──────────────────▼─────────────┐
│                    Use Cases                                │
│  CameraStream  │  Detection  │  Face (auto-registration)   │
└─────────┬────────────────────┬──────────────────┬──────────┘
          │                    │                  │
┌─────────▼────────┐  ┌────────▼─────────┐  ┌─────▼──────────┐
│ OpenCV RTSP      │  │ YOLODetection    │  │ InsightFace    │
│ (threaded)       │  │ (YOLO11s, GPU)   │  │ (ArcFace, GPU) │
└──────────────────┘  └──────────────────┘  └────────────────┘
          │                    │                  │
          ▼                    ▼                  ▼
   ┌──────────────────────────────────────────────────────┐
   │          Dataset (face_dataset/ on disk)             │
   │   omar/embedding_0.npy  (known)                      │
   │   __unknowns__/person_001/embedding_{0..N}.npy       │
   └──────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| **Backend** | FastAPI + Uvicorn | Async HTTP server, MJPEG streaming |
| **Detection** | Ultralytics YOLO11s | Object detection (person, phone, bag, weapon) |
| **Weapons** | YOLOv8s `gun.pt` | Firearm detection (guns, rifles) |
| **Pose** | YOLOv8n-Pose | 17-keypoint body skeleton |
| **Action** | torchvision R3D-18 (Kinetics-400) | 3D ResNet, 16-frame sliding window |
| **Face Recognition** | InsightFace (Buffalo-L) | Face detection + ArcFace embeddings |
| **Inference Runtime** | ONNX Runtime (CUDA) | GPU inference for face models |
| **CUDA** | PyTorch-bundled | Provides CUDA runtime for ONNX |
| **RTSP** | OpenCV (CAP_FFMPEG) | Camera stream reading |
| **Templates** | Jinja2 | HTML rendering |
| **Frontend** | Vanilla JS + CSS Grid | Lightweight, no framework bloat |
| **Validation** | Pydantic v2 | Settings + request/response models |
| **Config** | pydantic-settings | Env-based configuration |

### Model Sizes
| Model | Size | Purpose |
|---|---|---|
| `yolo11s.pt` | 18.4 MB | Object detection (persons, phones, bags, knives, scissors) |
| `gun.pt` | 156 MB | Weapon detection (guns / rifles) |
| `yolov8n-pose.pt` | 6.8 MB | 17-keypoint pose estimation |
| `r3d_18` (Kinetics-400) | ~73 MB | Action recognition (3D ResNet) |
| `buffalo_l/` (InsightFace) | ~280 MB | Face detection + recognition |

---

## Installation

### Prerequisites

- **Python 3.11+**
- **NVIDIA GPU** with CUDA support (recommended, RTX 3060 or better)
- **NVIDIA driver** supporting CUDA 12.x
- **8GB+ RAM** (16GB recommended)
- **~500MB disk** for models + dependencies

### Quick Start

```powershell
# Clone the repository
git clone <repo-url>
cd "Smart Surveillance System"

# Create virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Run the server
python main.py
```

The server will start on **http://localhost:8000**.

On first run, it will automatically download:
- `yolo11s.pt` (~18.4 MB)
- InsightFace `buffalo_l` pack (~280 MB)

### Hardware Setup (Hikvision RTSP example)

Update `main.py` or use the **Settings** tab in the UI to set your camera credentials:

```python
config = CameraConfig(
    host="192.168.1.7",          # Camera IP
    port=554,                     # RTSP port
    username="admin",
    password="your_password",
    channel=101,                  # 101=main, 102=sub
)
```

RTSP URL format: `rtsp://admin:password@192.168.1.7:554/Streaming/Channels/101`

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|---|---|---|
| `SS_HOST` | `0.0.0.0` | Server bind address |
| `SS_PORT` | `8000` | Server port |
| `SS_RTSP_HOST` | `192.168.1.7` | Camera IP |
| `SS_RTSP_PORT` | `554` | RTSP port |
| `SS_RTSP_USERNAME` | `admin` | Camera username |
| `SS_RTSP_PASSWORD` | (set) | Camera password |
| `SS_RTSP_CHANNEL` | `101` | Camera channel |
| `SS_JPEG_QUALITY` | `85` | Stream JPEG quality (10-100) |
| `SS_ITEM_PROXIMITY_PX` | `100` | Person-item proximity for ownership (px) |
| `SS_ITEM_HOLD_DURATION_S` | `1.5` | Seconds holding to claim ownership |
| `SS_ITEM_DISAPPEAR_THEFT_S` | `3.0` | Seconds missing before THEFT event |
| `SS_ITEM_ABANDON_S` | `30.0` | Seconds idle before ABANDONED event |
| `SS_ITEM_IOU_THRESHOLD` | `0.30` | IoU threshold for tracker matching |
| `SS_ITEM_MAX_DISAPPEAR_FRAMES` | `30` | Frames before an item is forgotten |

### Runtime Settings (via UI)

The **Settings** tab allows editing:
- RTSP connection (host, port, username, password, channel)
- JPEG quality slider (10-100)
- Feature toggles (motion detection, auto recording, notifications, night vision)

---

## Usage

### Web Interface

Open **http://localhost:8000** in your browser.

#### Dashboard Tab
- Live video stream
- Stat cards: persons, phones, bags, threats (updates every 1s)
- Live recognition panel: green for known, orange for returning visitors, yellow pulse for new

#### Faces Tab
- **Register New Face**: enter name, capture snapshot from camera, save
- **Known Faces**: list of registered people
- **Detected Persons**: auto-registered visitors with snapshots, click 👤 to assign a real name (promotes to known)

#### Settings Tab
- Edit RTSP credentials
- Adjust stream quality
- Toggle features

#### Items Tab
- **Stats cards** — held, stationary, abandoned counts, total thefts
- **Tracked Items table** — ID, type, state, owner, first/last seen, Forget action
- **Event Timeline** — chronological claim/drop/theft/returned events with confidence
- **Live WebSocket** — toasts on new ownership events, danger-pulse on theft

#### Alerts Tab
- Filter threats by level (Critical/High/Medium/Low)
- Real-time WebSocket feed with pulse animation on new threats
- Click snapshot to enlarge
### Workflow

1. **First-time setup**: Go to Settings → enter RTSP credentials → Save
2. **Register people you know**: Faces tab → Register New Face → enter name → Capture → Save
3. **System auto-registers unknowns**: anyone appearing on camera gets a `person_NNN` ID automatically
4. **Promote unknowns to knowns**: Faces tab → Detected Persons → click 👤 → enter real name

---

## API Reference

### Settings
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/settings` | Get current settings |
| `PUT` | `/api/settings` | Update settings (partial) |

### Detection
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/detections` | Current detection stats (persons, phones, bags, threats) |
| `GET` | `/stream` | MJPEG video stream (multipart/x-mixed-replace) |

### Face Recognition
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/faces` | List known faces |
| `POST` | `/api/faces/register` | Register a new known face |
| `DELETE` | `/api/faces/{name}` | Delete a known face |
| `GET` | `/api/faces/auto` | List auto-detected persons |
| `GET` | `/api/faces/auto/{id}/snapshot` | Get cropped face snapshot |
| `DELETE` | `/api/faces/auto/{id}` | Delete a detected person |
| `POST` | `/api/faces/auto/{id}/promote` | Promote detected → known |
| `GET` | `/api/faces/stats` | Live face recognition stats |
| `GET` | `/api/faces/snapshot` | Capture single frame from stream |

### Threat Detection
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/threats` | Recent threat events (with `?level=` and `?limit=`) |
| `GET` | `/api/threats/{id}/snapshot` | JPEG snapshot of a specific threat event |
| `DELETE` | `/api/threats` | Clear in-memory event history (disk snapshots kept) |
| `WS` | `/ws/threats` | Real-time threat push (`{type:"threat", data:{...}}`) |

### Item Tracking (Theft Detection)
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/items` | Active items with state, owner, bbox |
| `GET` | `/api/items/events` | Ownership event log (with `?limit=` and `?type=`) |
| `GET` | `/api/items/stats` | Aggregated counts (by state, type, thefts) |
| `GET` | `/api/items/{event_id}/snapshot` | JPEG snapshot for a theft event |
| `DELETE` | `/api/items` | Clear in-memory items + log (disk kept) |
| `DELETE` | `/api/items/{item_id}` | Stop tracking a specific item |
| `WS` | `/ws/items` | Real-time ownership events (`{type:"item_event", data:{...}}`) |

### Example: Register a face
```bash
curl -X POST http://localhost:8000/api/faces/register \
  -H "Content-Type: application/json" \
  -d '{"name": "Omar", "image": "<base64-encoded-jpeg>"}'
```

### Example: Promote a detected person
```bash
curl -X POST http://localhost:8000/api/faces/auto/person_001/promote \
  -H "Content-Type: application/json" \
  -d '{"name": "Ahmed"}'
```

---

## How It Works

### Object Detection Pipeline
1. RTSP frame captured by `OpenCVStreamRepository` (background thread)
2. Frame passed to `DetectionUseCase` → `YOLODetectionRepository`
3. YOLO11s runs inference on GPU at 1280×1280
4. Per-class confidence filtering (phone 0.20, person 0.45, etc.)
5. Bounding boxes drawn with rounded rects + corner brackets + label pills
6. Annotated frame goes to MJPEG stream

### Face Recognition Pipeline
1. Annotated frame → `FaceUseCase` → `InsightFaceRepository`
2. InsightFace detects faces + extracts 512-d embeddings (GPU)
3. For each face, two-stage matching:
   - **Stage 1**: Match against `known` (manual, threshold 0.45)
   - **Stage 2**: Match against `auto` (returning, threshold 0.80, more lenient)
4. If no match → quality check → auto-register as `person_NNN`
5. If match → save new embedding (with dedup) to build a "fingerprint"

### Multi-Embedding Fingerprint
Each auto-registered person can have up to **8 reference embeddings**, capturing different angles/lighting. This makes re-identification robust:
- Person at 0° angle matches `embedding_0`
- Person at 30° angle matches `embedding_2`
- Person at 60° angle matches `embedding_5`

Matching uses the **minimum cosine distance** across all stored embeddings.

### Threat Detection Pipeline
1. Same frame is fed (in parallel) to:
   - `WeaponDetectionRepository` (YOLOv8s-`gun.pt`, 640px, conf 0.30) → weapons list
   - `PoseEstimationRepository` (YOLOv8n-Pose, 640px) → list of `PoseKeypoints`
   - `R3DActionClassifier` — pushes frame to a 16-frame sliding window, predicts every 0.5s
2. The `RuleEngine` evaluates each signal:
   - `weapon` → MEDIUM (≥0.30) / HIGH (≥0.60)
   - `is_violent` action → HIGH
   - `is_fighting_stance` pose **near another person** → MEDIUM (proximity)
3. `ThreatUseCase` aggregates the rule hits:
   - Computes a `threat_score` per hit (with **escalation bonus** when weapon + violence co-occur)
   - Maps score → `LOW / MEDIUM / HIGH / CRITICAL`
   - Saves a snapshot (`data/alerts/YYYY-MM-DD/HH-MM-SS-level-xxxxxx.jpg`)
   - Applies a 5s cooldown per (type, level, spatial bucket) to prevent spam
   - Pushes the event over WebSocket to all connected dashboard clients
4. The **Alerts tab** receives the WebSocket message and prepends a card with pulse animation

### Item Tracking & Theft Detection Pipeline
1. Each frame's YOLO detections are filtered for "items of interest" (cell phones, etc.)
2. `IoUTracker` matches current detections to existing tracks by bounding-box IoU
   - New bbox with no match → creates a new `TrackedItem` (state = `NEW`)
   - Matched bbox → resets `disappear_count`, updates `last_bbox`
   - Unmatched existing item → increments `disappear_count`
3. `OwnershipEngine.process` runs the state machine:
   - **STATIONARY** + person nearby ≥ 1.5s → set `owner_id`, transition to `HELD` → emit **CLAIM** event
   - **HELD** + owner gone ≥ 0.5s → transition to `STATIONARY` (or **THEFT** if a stranger is now near) → emit **DROP/THEFT** event
   - **STATIONARY** + item missing for ≥ 3s → emit **THEFT** event
   - **STATIONARY** + no contact for ≥ 30s → emit **ABANDONED** event
4. `ItemTrackingUseCase` records each event, persists to `data/items_log.json`, broadcasts over `/ws/items`, and on **THEFT** mirrors it as a HIGH-level threat to the Alerts tab
5. The **Items tab** receives WebSocket messages, shows toasts, and updates the table + timeline

---

## Performance

### Tested on RTX 3060 Laptop GPU

| Stage | Latency | FPS |
|---|---|---|
| YOLO11s @ 1280×1280 (main) | ~25 ms | 40 |
| YOLO8s `gun.pt` @ 640 (weapons) | ~15 ms | 65 |
| YOLO8n-Pose @ 640 (pose) | ~10 ms | 100 |
| R3D-18 action (every 0.5s, 16-frame clip) | ~30 ms | — |
| InsightFace (detection + recognition) | ~16 ms | 60 |
| **Combined per frame** | **~50 ms** | **~20** |

### CPU fallback (no GPU)
| Stage | Latency |
|---|---|
| YOLO11s @ 1280 | ~250 ms |
| InsightFace | ~250 ms |

> **Tip**: For best performance, use a dedicated NVIDIA GPU with at least 4GB VRAM.

### Memory footprint
- Idle: ~600 MB
- Active (YOLO + InsightFace + weapons + pose + R3D): ~1.8 GB
- Models on disk: ~530 MB
- Per-alert snapshot: ~80 KB (JPEG q=90)

---

## Development

### Project Layout

```
Smart Surveillance System/
├── main.py                          # Entry point
├── requirements.txt                 # Python dependencies
├── gun.pt                           # YOLO8s weapons (auto-downloaded)
├── yolo11s.pt                       # Main YOLO detector
├── yolo11n.pt
├── yolov8n-pose.pt                  # Pose estimation
├── face_dataset/                    # Auto-created
│   ├── omar/                        # Known faces
│   │   ├── 0.jpg
│   │   └── embedding_0.npy
│   └── __unknowns__/                # Auto-registered
│       ├── person_001/
│       │   ├── 0.jpg
│       │   └── embedding_*.npy      # Up to 8
│       └── ...
├── data/
│   └── alerts/                      # Threat snapshots
│       └── 2026-06-06/
│           └── 14-22-11-high-ab12cd.jpg
├── src/
│   ├── config/
│   │   └── settings.py              # Pydantic settings
│   ├── domain/                      # Pure logic (no I/O)
│   │   ├── entities/
│   │   │   ├── camera.py
│   │   │   └── threat.py            # ThreatLevel, ThreatEvent, ...
│   │   └── interfaces/
│   │       ├── stream_repository.py
│   │       ├── detection_repository.py
│   │       ├── face_repository.py
│   │       └── threat_repository.py
│   ├── usecases/
│   │   ├── camera_stream.py
│   │   ├── detection.py
│   │   ├── face.py
│   │   └── threat.py                # ThreatUseCase (aggregates signals)
│   ├── adapters/
│   │   ├── rtsp/
│   │   │   └── opencv_stream_repository.py
│   │   ├── yolo/
│   │   │   ├── detection_repository.py
│   │   │   ├── weapon_detection_repository.py
│   │   │   └── pose_estimation_repository.py
│   │   ├── torch/
│   │   │   └── r3d_action_classifier.py
│   │   ├── threat/
│   │   │   └── rule_engine.py
│   │   └── insightface/
│   │       └── face_repository.py
│   └── presentation/
│       ├── api/
│       │   └── app.py               # FastAPI factory + lifespan
│       ├── routes/
│       │   ├── camera.py
│       │   ├── face.py
│       │   ├── settings.py
│       │   └── threat.py            # /api/threats + /ws/threats
│       ├── realtime/
│       │   └── ws_manager.py        # WebSocketManager (broadcast hub)
│       ├── templates/
│       │   └── index.html
│       └── static/
│           ├── css/
│           │   ├── base.css
│           │   ├── layout.css
│           │   ├── components.css
│           │   ├── dashboard.css
│           │   ├── faces.css
│           │   ├── settings.css
│           │   └── alerts.css
│           └── js/
│               ├── utils.js
│               ├── api.js
│               ├── stream.js
│               ├── dashboard.js
│               ├── faces.js
│               ├── settings.js
│               ├── alerts.js
│               └── app.js
```

### Adding a New Detection Class

1. Add the YOLO class ID to `YOLO_CLASS_MAP` in `src/domain/interfaces/detection_repository.py`
2. Add a color in `DETECTION_COLORS`
3. Add a display label in `LABEL_DISPLAY` (in `detection_repository.py`)
4. Add a per-class confidence in `CLASS_CONFIDENCE`

### Adding a New Face Provider

Implement the `FaceRepository` interface in `src/domain/interfaces/face_repository.py` and place the adapter under `src/adapters/`. Wire it up in `main.py`.

### Frontend Conventions

- **CSS**: scoped by view (`dashboard.css`, `faces.css`, etc.) + shared (`components.css`, `layout.css`, `base.css`)
- **JS**: one module per view (`dashboard.js`, `faces.js`, etc.) + shared (`utils.js`, `api.js`)
- **Icons**: SVG inline via the `icon()` helper in `utils.js`
- **API**: all calls go through `api.*` wrappers in `api.js`
- **Notifications**: `showToast()` for status, `showModal()` for confirmations, `showPrompt()` for input

---

## Troubleshooting

### Server won't start
- Check Python version: `python --version` (need 3.11+)
- Verify dependencies: `pip install -r requirements.txt`
- Check for port conflict: another process using 8000?

### Camera not connecting
- Test RTSP URL with VLC: `rtsp://user:pass@host:port/channels/101`
- Verify IP, port, username, password
- Try channel 102 (sub-stream) if main is slow

### GPU not being used
- Check: `python -c "import torch; print(torch.cuda.is_available())"`
- Verify NVIDIA driver is up to date
- InsightFace will fall back to CPU if CUDA fails (slower but works)

### Models not detected (faces missed)
- Face size in frame too small? Move closer to camera or zoom in
- Blurry? Check focus, lighting
- Profile angle? Try facing camera more directly
- Add more samples: re-register from different angles

### Phones not detected
- Phone is small in frame? Try larger model (`yolo11m.pt`) or higher imgsz (1920)
- Or lower the phone confidence threshold in `CLASS_CONFIDENCE`
- COCO training data is biased toward Western phones, may struggle with certain brands

### Server doesn't shut down cleanly
- Already fixed in latest version (lifespan handler + CancelledError filter)
- If issues persist, check `main.py` for the `_CancelledErrorFilter`

### Threat alerts never fire
- Make sure `gun.pt` and `yolov8n-pose.pt` are in the project root
- R3D-18 is downloaded automatically by `torchvision` on first use (~73MB)
- Check the WebSocket status badge in the Alerts tab (should be green "Live")
- If only the LOW/MEDIUM levels appear, the action classifier may be over-cautious — that's expected, since Kinetics-400 has limited violence classes

---

## Roadmap

- [x] Weapon detection (gun.pt)
- [x] Pose estimation (yolov8n-pose.pt)
- [x] Action recognition (R3D-18)
- [x] Real-time threat alerts (WebSocket)
- [x] Snapshot on alert (data/alerts/)
- [ ] Multi-camera support (currently single camera)
- [ ] Event timeline (when did each person appear?)
- [ ] Webhook / Telegram alerts
- [ ] Recording on motion / threat detection
- [ ] Heatmap / analytics dashboard
- [ ] Re-ID across non-overlapping cameras
- [ ] ONVIF discovery
- [ ] Mobile app (PWA)
- [ ] Face liveness detection (anti-spoofing)
- [ ] Voice / sound event detection
- [ ] Custom YOLO training for specific scenarios

---

## License

MIT License. See `LICENSE` for details.

---

## Credits

- [Ultralytics YOLO](https://github.com/ultralytics/ultralytics) — object detection
- [InsightFace](https://github.com/deepinsight/insightface) — face recognition
- [ONNX Runtime](https://github.com/microsoft/onnxruntime) — inference runtime
- [FastAPI](https://fastapi.tiangolo.com/) — web framework
- [PyTorch](https://pytorch.org/) — CUDA runtime (bundled libs)
- [torchvision R3D-18](https://pytorch.org/vision/stable/models/video.html) — action recognition (Kinetics-400)
- [Shantanukadam/weapon_detection](https://huggingface.co/Shantanukadam/weapon_detection) — gun.pt weapon detector

---

**Built with ❤️ for self-hosted, privacy-respecting surveillance.**
