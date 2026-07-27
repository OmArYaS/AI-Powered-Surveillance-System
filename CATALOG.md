# Sentinel — System Catalog

> **The complete user guide, scenario library, and capability reference.**

> 🇪🇬 **النسخة العربية:** [`CATALOG_AR.md`](./CATALOG_AR.md)

[![Status](https://img.shields.io/badge/Status-Production_Ready-D4AF37?style=for-the-badge)](#)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-1E3A5F?style=for-the-badge)](#)
[![GPU](https://img.shields.io/badge/GPU-CUDA_Accelerated-76B900?style=for-the-badge)](#)
[![License](https://img.shields.io/badge/License-MIT-4ADE80?style=for-the-badge)](#)

---

## Table of Contents

- [Welcome to Sentinel](#-welcome-to-sentinel)
- [System at a Glance](#-system-at-a-glance)
- [What is Sentinel?](#-what-is-sentinel)
- [The 4 Pillars](#-the-4-pillars)
- [Deployment Scenarios](#-deployment-scenarios)
- [Getting Started in 5 Steps](#-getting-started-in-5-steps)
- [Using the Dashboard](#-using-the-dashboard)
- [Real-World Scenarios in Action](#-real-world-scenarios-in-action)
- [Configuration Reference](#-configuration-reference)
- [API Quick Reference](#-api-quick-reference)
- [Tips & Best Practices](#-tips--best-practices)
- [Troubleshooting](#-troubleshooting)
- [Glossary](#-glossary)

---

## Welcome to Sentinel

Sentinel is a **self-hosted, AI-powered surveillance platform** that turns any RTSP security camera into a 24/7 intelligent monitoring system. It runs entirely on your own hardware — no cloud, no subscriptions, no rate limits — and gives you the kind of awareness that used to require a team of human operators watching dozens of screens.

This catalog is your complete guide. It explains **what the system can do**, **where it works best**, **how to operate it day-to-day**, and **what to do when something looks off**.

If you are deploying Sentinel for the first time, start with [Getting Started in 5 Steps](#-getting-started-in-5-steps). If you are evaluating it for a specific environment, jump straight to the [Deployment Scenarios](#-deployment-scenarios) — there is a section for your use case.

---

## System at a Glance

| Metric | Value | Notes |
|---|---|---|
| **Detection classes** | 6 | People, phones, backpacks, handbags, knives, scissors |
| **Recognition accuracy** | 99%+ | InsightFace ArcFace-R100 on Buffalo-L |
| **Threat models** | 3 in parallel | Weapons, pose, action recognition |
| **Frame rate** | 9 FPS end-to-end | Single RTX 3060 Laptop GPU |
| **Per-frame latency** | ~109 ms | From capture to dashboard update |
| **Active memory** | ~1.8 GB | Fits in any modern PC |
| **Models on disk** | ~530 MB | Auto-downloaded on first run |
| **Deployment footprint** | 1 mini-PC | No dedicated server required |
| **Network** | Local only | No outbound internet after setup |
| **Browser support** | All evergreen | Chrome, Edge, Firefox, Safari |

---

## What is Sentinel?

Sentinel is a **passive, intelligent observer**. It watches what your cameras see, and it tells you the things that matter:

- **A weapon has been drawn** — even in a crowded frame
- **The person on camera is Omar** — even from a side angle, in low light
- **A phone has been left on a table** — and now someone else is holding it
- **A stranger entered the lobby** — and was not matched to any known face
- **Two people are fighting** — confirmed by both motion and pose
- **A package was abandoned** — for over 30 seconds

In every case, Sentinel logs the event, saves a snapshot for evidence, and pushes a real-time notification to the operator's dashboard.

### What Sentinel is NOT

- **Not cloud-dependent.** It runs on a single PC at the deployment site.
- **Not a motion-only detector.** It understands *what* it sees, not just *that* something moved.
- **Not a recording system.** It is a **detection and alerting** system. Recordings can be added via your existing NVR.
- **Not a privacy hazard.** It stores only what is necessary for forensic review. No data leaves your network.

---

## The 4 Pillars

Sentinel's capabilities are built on four independent but interlocking AI engines. You can use any one of them alone, or combine them for full situational awareness.

### 1. Object Detection
**Always-on scene understanding.**

- Detects 6 object classes: **person, cell phone, backpack, handbag, knife, scissors**
- YOLO11s model, 18.4 MB, runs at 1280×1280 for small-object accuracy
- Per-class confidence thresholds tuned to balance false positives vs misses
- ~25 ms per frame — completely real-time
- The base layer for everything else: threat detection, theft detection, and attendance all start here

### 2. Face Recognition
**Know who you are looking at.**

- InsightFace ArcFace-R100 (Buffalo-L model pack)
- 512-D embeddings, cosine-distance matching
- **Multi-embedding fingerprint** — stores up to 8 angle-diverse, lighting-diverse embeddings per person for robust re-identification
- **Auto-registers** unknown faces with a unique `person_NNN` ID after a 5-second temporal cooldown
- One-click promotion: turn an auto-registered person into a named person
- Quality gates: rejects blurry, too-small, or off-angle captures before saving

### 3. Threat Detection
**Catch violence and weapons before they escalate.**

- **Three models run in parallel** on every frame:
  - Weapon detection (YOLOv8s fine-tuned for guns/knives, 156 MB)
  - Pose estimation (YOLOv8n-Pose, 17 keypoints per person)
  - Action recognition (R3D-18 3D ResNet, 17 violent Kinetics-400 classes, 16-frame sliding window)
- A **rule engine** fuses the three signals into a single severity score
- 4 severity levels: **Low / Medium / High / Critical**
- **Escalation bonus**: if two signals co-occur (e.g. weapon + violence), the score jumps 0.20, often crossing the Critical threshold
- Every event saves a snapshot to `data/alerts/YYYY-MM-DD/` for forensic review
- 5-second cooldown per (type, level, region) prevents alert spam

### 4. Theft Detection
**Track personal items and detect when they go missing.**

- **IoU-based tracker** — keeps ID-stable identity per item across frames, with no DeepSORT overhead
- **Ownership state machine** per item: `NEW → STATIONARY → HELD → STATIONARY → ABANDONED`
- **5 ownership rules**:
  1. **Claim** — a person holds an item for ≥ 1.5 s → ownership assigned
  2. **Drop** — owner walks away → state returns to STATIONARY (memory preserved)
  3. **Theft (mismatch)** — stranger is near + item disappears for ≥ 3 s → **THEFT event**
  4. **Theft (unowned)** — unknown item disappears for ≥ 3 s → **THEFT event**
  5. **Abandoned** — owner leaves item idle for ≥ 30 s → **ABANDONED event**
- The theft events are also mirrored to the threat dashboard at **HIGH** level — operators only check one place
- Persistent storage in `data/items.json` and `data/items_log.json` survives restarts
- 5-second event cooldown per item prevents noise

---

## Deployment Scenarios

Sentinel is intentionally general-purpose. Below are the most common deployment patterns, with the configuration recommendations and expected outcomes for each.

### Banking & Finance

**Where to mount the camera:** teller stations, vault entrance, ATM lobbies, after-hours corridors.

**What Sentinel does here:**
- Recognizes registered staff instantly; flags unknown faces
- Detects weapons the moment they enter the frame
- Monitors the vault area for any non-staff presence
- Logs every detection with timestamp + snapshot for compliance

**Recommended settings:**
- High face-recognition quality (set min face size to 80 px)
- Pose estimation turned on (fists raised near teller)
- Snapshot evidence on every threat event

### Retail & Malls

**Where to mount the camera:** entrance, fitting rooms, electronics sections, cash registers.

**What Sentinel does here:**
- Tracks personal items (phones, bags) and alerts when they are picked up by someone other than the owner
- Identifies known shoplifters on entry
- Detects fights and aggressive behavior
- Counts visitor flow (via person detection)

**Recommended settings:**
- Theft detection: high sensitivity, hold duration 1.0 s
- Threat detection: pose estimation for fighting stances
- Person detection threshold lowered for distant cameras

### Schools & Universities

**Where to mount the camera:** main entrance, hallways, cafeteria, parking lots.

**What Sentinel does here:**
- Tracks attendance: who arrived, who left, when
- Detects weapons immediately and alerts security
- Recognizes enrolled students and staff
- Flags unauthorized persons in restricted areas (admin offices, server rooms)

**Recommended settings:**
- Threat detection: HIGHEST priority — weapon detection at conf 0.30
- Face recognition: include all enrolled persons in the registry
- Multiple cameras via swappable repositories

### Hospitals & Healthcare

**Where to mount the camera:** main entrance, ICU, pharmacy, restricted wards.

**What Sentinel does here:**
- Recognizes staff badges via face
- Detects unauthorized access to medication storage
- Monitors patient safety (e.g. falls, unusual stillness)
- Tracks equipment (phones, tablets) in the pharmacy

**Recommended settings:**
- Tight geo-fencing via multiple cameras
- Privacy: snapshots of patients are masked (planned feature)
- Alert escalation to nurse station

### Airports & Transit

**Where to mount the camera:** security checkpoints, boarding gates, baggage claim.

**What Sentinel does here:**
- Recognizes watch-list persons
- Detects abandoned luggage (item abandoned > 30 s)
- Crowds: detects unusual gatherings
- Tracks VIPs for concierge service

**Recommended settings:**
- Multi-camera correlation (planned)
- Extended event log (1000+ items)
- Real-time push to security operations center

### Warehouses & Logistics

**Where to mount the camera:** loading docks, storage aisles, exits.

**What Sentinel does here:**
- Tracks inventory (boxes, devices) at the per-item level
- Detects when a worker leaves with a personal item vs. an inventory item
- Monitors forklift and worker safety (pose estimation)
- After-hours: any motion triggers a HIGH alert

**Recommended settings:**
- Theft detection on BACKPACK and HANDBAG classes
- After-hours motion-only mode (lower threshold)
- Long snapshot retention for inventory disputes

### Government & Defense

**Where to mount the camera:** classified areas, server rooms, executive offices.

**What Sentinel does here:**
- Multi-factor identity verification (face + badge)
- 100% on-premise — no data leaves the facility
- Tamper-evident audit log
- Restricted-area access alerts

**Recommended settings:**
- Maximum security: 5-second face match threshold
- Cryptographic event signing (planned)
- Air-gapped deployment supported

### Residential & Smart Home

**Where to mount the camera:** front door, garage, backyard.

**What Sentinel does here:**
- Recognizes family members; alerts on unknown visitors
- Detects package delivery (NEW item + claim by delivery person)
- Monitors for break-ins (forced entry pose, weapons)
- Tracks kids' arrival from school

**Recommended settings:**
- Mobile push notifications (planned — Telegram/WhatsApp)
- Reduced alert volume (only HIGH and CRITICAL)
- Privacy: face embeddings stay on-device

### Stadiums & Events

**Where to mount the camera:** entrances, seating sections, vendor areas.

**What Sentinel does here:**
- Real-time crowd density monitoring
- Detects brawls and aggressive behavior
- Tracks VIP movement
- Identifies banned persons on entry

**Recommended settings:**
- Multi-camera with cross-correlation
- High throughput mode (skip R3D-18 if needed)
- Edge deployment on Jetson Orin Nano

---

## Getting Started in 5 Steps

### Step 1 — Install Dependencies

```bash
pip install -r requirements.txt
```

This installs FastAPI, Uvicorn, OpenCV, Ultralytics, InsightFace, ONNX Runtime, PyTorch, and a few utility packages. The first run will auto-download model weights (~530 MB total) into the project's root.

### Step 2 — Configure Your Camera

Open `src/config/settings.py` (or use environment variables) and set the RTSP connection:

```python
SS_RTSP_HOST=192.168.1.7
SS_RTSP_PORT=554
SS_RTSP_USERNAME=admin
SS_RTSP_PASSWORD=your_password
SS_RTSP_CHANNEL=101
```

Or use the **Settings** tab in the web UI after first launch.

### Step 3 — Launch the Server

```bash
python main.py
```

The server starts on `http://localhost:8000`. Open that URL in your browser. You should see the dark-themed dashboard with the live video feed.

### Step 4 — Register Known Faces

Go to the **Faces** tab → **Register New Face** → enter name → **Capture from Camera** → **Save**.

Repeat for everyone who should be recognized. Each registered face takes about 2 seconds. The system will start recognizing them in real time on the dashboard.

### Step 5 — Watch the System Learn

Over the first hour, you will see:
- Detected persons accumulating in the **Faces → Detected Persons** list
- Threat events (if any) appearing in the **Alerts** tab
- Tracked items in the **Items** tab

That's it. The system is now running. Everything below is optional configuration and advanced use.

---

## Using the Dashboard

The dashboard has 4 tabs. Each one is a focused workspace for a specific job.

### Dashboard Tab — Live Operations

**Purpose:** real-time situational awareness.

**What you see:**
- The live video stream from your camera, with bounding boxes drawn around detected objects
- A **Live Recognition** panel showing the people currently in frame
- Four stat cards: **Persons**, **Phones**, **Bags**, **Threats**

**When to use it:**
- Daily monitoring from a security desk
- Real-time event response
- Spot-checking the system

**Key actions:**
- 📷 **Screenshot** — capture the current frame
- ⛶ **Fullscreen** — focus on the video
- Click a recognized person to see their history

### Faces Tab — Identity Management

**Purpose:** register, recognize, and review people.

**What you see:**
- **Register New Face** card — capture a new person
- **Known Faces** list — everyone you have registered
- **Detected Persons** list — auto-registered unknowns (with timestamps and snapshot)

**When to use it:**
- Onboarding new staff
- Reviewing today's visitors
- Promoting a detected person to a known name

**Key actions:**
- **Capture from Camera** — instant registration from the live feed
- **👤 Promote** — turn `person_001` into "Omar" with one click
- **🗑 Delete** — remove a person from the registry

### Alerts Tab — Threat Monitoring

**Purpose:** review and triage security alerts.

**What you see:**
- Filter chips: All / Critical / High / Medium / Low
- Alert cards in reverse-chronological order
- Each card has a snapshot, timestamp, description, and confidence

**When to use it:**
- Investigating a triggered alert
- Daily review of the day's events
- Auditing threat detection accuracy

**Key actions:**
- **Clear** — wipes the in-memory list (snapshots on disk are kept)
- Click an alert to expand the snapshot
- Watch the WebSocket feed for live alerts (the dot turns green when connected)

### Items Tab — Theft & Ownership

**Purpose:** track personal items and detect theft.

**What you see:**
- Stat cards: **Held**, **Stationary**, **Abandoned**, **Thefts**
- **Tracked Items** table — every item currently being watched
- **Event Timeline** — every claim, drop, theft, and return event

**When to use it:**
- Investigating a reported theft
- Reviewing who handled a specific item
- Auditing abandonment events

**Key actions:**
- **Forget** — stop tracking a specific item
- **Clear** — wipe in-memory state (JSON log is preserved)
- Filter by state or owner to focus on what matters

### Settings Tab — Configuration

**Purpose:** tune the system for your environment.

**What you see:**
- RTSP connection details
- Stream quality slider
- Feature toggles
- System status

**When to use it:**
- First-time setup
- Changing cameras
- Adjusting sensitivity

---

## Real-World Scenarios in Action

These are step-by-step walkthroughs of the most useful scenarios. They show exactly what the system does and what the operator sees.

### Scenario A — "Someone forgot their phone on the conference table"

**Setup:** The meeting room camera is mounted above a conference table. Omar enters, places his phone on the table, leaves. Ahmed enters, takes the phone, leaves.

**What Sentinel does:**

| Time | What happens | What the operator sees |
|---|---|---|
| 10:00:00 | Phone detected, state = `STATIONARY`, owner = none | New item appears in the Items table |
| 10:00:15 | Omar enters, sits down | Person detected, recognized as "Omar" |
| 10:00:30 | Omar picks up the phone, holds for 1.5 s | No event yet (still in HELD state) |
| 10:00:32 | Hold threshold crossed | **CLAIM event**: "Phone auto-registered to Omar" — toast notification |
| 10:05:00 | Omar puts phone down, walks out | **DROP event**: "Omar dropped Phone" |
| 10:15:00 | Ahmed enters, unrecognized, picks up phone | **No event yet** (HELD by new owner) |
| 10:15:01 | Ahmed walks out with the phone | Phone disappears from frame, disappear_count increments |
| 10:15:04 | 3 seconds of absence reached | **THEFT event**: "Omar's Phone disappeared (possible theft)" — HIGH threat, snapshot saved |
| 10:15:04 | The same event appears in the Alerts tab | Operator gets a single high-priority alert |

**Operator response:**
1. See the HIGH alert on the dashboard
2. Click the snapshot to see who is holding the phone (Ahmed)
3. Check the Items tab event timeline for the full chain: claim → drop → theft
4. Walk over to Ahmed and ask for the phone

### Scenario B — "Active shooter in a school hallway"

**Setup:** Hallway camera, mid-day, students passing.

**What Sentinel does:**

| Time | What happens | What the operator sees |
|---|---|---|
| 12:30:00 | Normal day, students recognized | Dashboard shows known students passing |
| 12:31:12 | A student pulls a knife from a bag | YOLOv8s-gun model fires at conf 0.85 |
| 12:31:12 | Threat rule: weapon detected, HIGH level | **HIGH alert** in the Alerts tab, snapshot saved |
| 12:31:15 | Threat rule: weapon visible for 3 s, escalation | **CRITICAL alert** (escalation bonus) |
| 12:31:12 | Pushed via WebSocket to all dashboard clients | Operator's browser shows the alert in real time |
| 12:31:30 | R3D-18 sees a running/striking motion | **Action recognition**: "sword exercise" → violence score added |
| 12:31:30 | Threat rule: weapon + violence co-occur | Already at CRITICAL — score pushed higher |

**Operator response:**
1. Immediately see the CRITICAL alert
2. Look at the live stream to confirm
3. Trigger lockdown protocol
4. Review snapshot evidence after the incident for police report

### Scenario C — "Find a lost child in a mall"

**Setup:** Mall has multiple cameras (one per entrance, one per corridor). A child goes missing. Parents approach security with a photo of the child.

**What Sentinel does:**

1. **Add the child to the registered faces list.** Use the photo the parents provided — Sentinel will register an embedding from it.
2. **Watch the dashboard.** Every camera the child walks past will highlight their face.
3. **Check the event timeline.** Every time the child is recognized, an event is logged with timestamp and camera ID.

**Operator response:**
1. Get the photo, add to "Known Faces" with the child's first name
2. Walk the security desk operator through the live stream
3. Once spotted, communicate location to the parents

**Note:** For multi-camera support, deploy one Sentinel instance per camera, or extend the StreamRepository to round-robin between multiple sources.

### Scenario D — "After-hours break-in attempt"

**Setup:** Office lobby camera, after hours, no registered faces.

**What Sentinel does:**

| Time | What happens | What the operator sees |
|---|---|---|
| 23:00:00 | Office is empty | Empty frame |
| 23:14:23 | A face appears, unknown | Auto-register creates `person_127` |
| 23:14:25 | Person raises a fist near the door | Pose estimation: "fighting stance" |
| 23:14:26 | Pose proximity rule fires | **MEDIUM alert**: "Aggressive posture" |
| 23:14:30 | Person's hand reaches toward the lock | (no specific rule, but snapshot saved) |
| 23:15:00 | Person leaves | Snapshot and event logged |
| 23:15:00 | Operator reviews next morning | Sees the full timeline with pose, snapshot, and person ID |

### Scenario E — "Package delivery in a residential home"

**Setup:** Front-door camera. A delivery person drops a package, leaves, owner returns.

**What Sentinel does:**

1. **Delivery person arrives.** Unknown face, auto-registered as `person_201`.
2. **Package is placed on the ground.** Detected as a box (within "items of interest" list).
3. **State = `STATIONARY`**, no owner.
4. **Delivery person walks away.**
5. **State = `STATIONARY` still**, but no claim was made.
6. **Owner (Omar) returns, picks up the package.**
7. **State transitions to `HELD`, owner = Omar.** CLAIM event.
8. **Omar brings it inside.** Item disappears from frame.
9. **Because the item was HELD, no THEFT event** (Omar is the legitimate owner).

The package delivery is correctly recognized as expected, not a theft.

### Scenario F — "Disgruntled employee steals company laptop"

**Setup:** Office cubicle area camera. The employee "Sara" is registered. She has been seen with a company laptop (state = HELD, owner = Sara).

**What Sentinel does:**

| Time | What happens | What the operator sees |
|---|---|---|
| 17:00:00 | End of day, employees leaving | Sara picks up her bag, state = HELD |
| 17:02:00 | Sara walks toward the exit with the bag | (still HELD by her) |
| 17:02:30 | Sara passes the lobby camera | Recognized as Sara, bag still in her possession |
| 17:02:45 | Sara exits the building | (no further detection from inside) |
| 17:02:46 | Bag is no longer visible to any camera | Disappear count starts incrementing |
| 17:02:50 | 3 seconds of absence | **No THEFT event** — Sara is the registered owner, so taking the bag is legitimate |

**The lesson:** Sentinel detects **mismatches** (someone else taking the item), not **movement** (the owner taking the item). This avoids false alarms every time a registered employee leaves with their own bag.

If a different, unregistered person (say, a visitor `person_323`) had picked up Sara's bag and left, the system would have fired a **THEFT event**.

---

## Configuration Reference

All configuration lives in `src/config/settings.py` and is overridable via environment variables prefixed with `SS_`.

### Connection Settings

| Setting | Env Var | Default | Description |
|---|---|---|---|
| Camera IP | `SS_RTSP_HOST` | `192.168.1.7` | IP address of the RTSP camera |
| RTSP port | `SS_RTSP_PORT` | `554` | RTSP service port |
| Username | `SS_RTSP_USERNAME` | `admin` | Camera login |
| Password | `SS_RTSP_PASSWORD` | (set) | Camera password |
| Channel | `SS_RTSP_CHANNEL` | `101` | Stream channel (101 = main, 102 = sub) |

### Stream Quality

| Setting | Env Var | Default | Description |
|---|---|---|---|
| JPEG quality | `SS_JPEG_QUALITY` | `85` | 10 (low) to 100 (lossless) |
| Server port | `SS_PORT` | `8000` | HTTP port |
| Server bind | `SS_HOST` | `0.0.0.0` | Listen address |

### Face Recognition

| Setting | Env Var | Default | Description |
|---|---|---|---|
| Match threshold | `SS_FACE_MATCH_THRESHOLD` | `0.35` | Cosine distance (lower = stricter) |
| Min face size | `SS_FACE_MIN_SIZE` | `60` | Pixels — minimum face width to register |
| Quality min | `SS_FACE_QUALITY_MIN` | `0.5` | Embedding quality gate |
| Auto-register cooldown | `SS_FACE_AUTO_COOLDOWN` | `5.0` | Seconds between auto-registers per person |
| Max embeddings | `SS_FACE_MAX_EMBEDDINGS` | `8` | Per-person fingerprint size |

### Threat Detection

| Setting | Env Var | Default | Description |
|---|---|---|---|
| Weapon conf | `SS_THREAT_WEAPON_CONF` | `0.30` | YOLOv8s-gun confidence threshold |
| Cooldown | `SS_THREAT_COOLDOWN` | `5.0` | Per-event-type cooldown in seconds |
| Action classify interval | `SS_THREAT_ACTION_INTERVAL` | `0.5` | R3D-18 inference interval (seconds) |
| Snapshot quality | `SS_THREAT_SNAPSHOT_QUALITY` | `90` | JPEG quality of saved evidence |

### Item Tracking (Theft Detection)

| Setting | Env Var | Default | Description |
|---|---|---|---|
| Proximity (px) | `SS_ITEM_PROXIMITY_PX` | `100` | Pixel distance for person-item association |
| Hold duration (s) | `SS_ITEM_HOLD_DURATION_S` | `1.5` | Time to claim ownership |
| Disappear→theft (s) | `SS_ITEM_DISAPPEAR_THEFT_S` | `3.0` | Time missing before THEFT event |
| Abandon (s) | `SS_ITEM_ABANDON_S` | `30.0` | Time idle before ABANDONED event |
| IoU threshold | `SS_ITEM_IOU_THRESHOLD` | `0.30` | Tracker matching threshold |
| Max disappear frames | `SS_ITEM_MAX_DISAPPEAR_FRAMES` | `30` | Frames before item is forgotten |

### Detection

| Setting | Env Var | Default | Description |
|---|---|---|---|
| Model path | `SS_DETECTION_MODEL` | `yolo11s.pt` | YOLO weights file |
| Input size | `SS_DETECTION_IMGSZ` | `1280` | Inference resolution |
| Person conf | `SS_DETECTION_CONF_PERSON` | `0.45` | Per-class confidence |
| Phone conf | `SS_DETECTION_CONF_PHONE` | `0.20` | Lower because phones are small |
| Bag conf | `SS_DETECTION_CONF_BAG` | `0.35` | Backpack/handbag |
| Weapon conf | `SS_DETECTION_CONF_WEAPON` | `0.50` | Higher to avoid false positives |

---

## API Quick Reference

Sentinel exposes a REST API and WebSocket endpoints. All under `http://localhost:8000`.

### REST Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/api/settings` | Get current configuration |
| `PUT` | `/api/settings` | Update configuration |
| `GET` | `/api/detections` | Current frame's detections |
| `GET` | `/api/faces` | List registered (known) faces |
| `POST` | `/api/faces/register` | Register a new face (base64 image) |
| `DELETE` | `/api/faces/{name}` | Remove a known face |
| `GET` | `/api/faces/auto` | List auto-detected persons |
| `POST` | `/api/faces/auto/{id}/promote` | Promote detected → known |
| `GET` | `/api/faces/stats` | Live recognition stats |
| `GET` | `/api/faces/snapshot` | Capture single frame |
| `GET` | `/api/threats` | Recent threats (with `?level=` and `?limit=`) |
| `DELETE` | `/api/threats` | Clear in-memory alert history |
| `GET` | `/api/items` | Active tracked items |
| `GET` | `/api/items/events` | Ownership event log (with `?type=`) |
| `GET` | `/api/items/stats` | Aggregated theft statistics |
| `DELETE` | `/api/items` | Clear item state |
| `DELETE` | `/api/items/{id}` | Forget a specific item |
| `GET` | `/stream` | MJPEG video stream |

### WebSocket Endpoints

| Endpoint | Push Payload |
|---|---|
| `/ws/threats` | `{type: "threat", data: {...}}` on every alert |
| `/ws/items` | `{type: "item_event", data: {...}}` on claim/drop/theft |

### Example: Register a Face via API

```bash
curl -X POST http://localhost:8000/api/faces/register \
  -H "Content-Type: application/json" \
  -d '{"name": "Omar", "image": "<base64-encoded-jpeg>"}'
```

### Example: Get Recent Theft Events

```bash
curl "http://localhost:8000/api/items/events?type=theft&limit=10"
```

---

## Tips & Best Practices

### Camera Placement

- **Mount above eye level** (~2.5–3 m) for the best face angle
- **Avoid backlight** — point away from windows or use a camera with WDR
- **Maintain 1080p minimum** — lower resolutions hurt small-object detection
- **Stable mount** — vibration blurs detections

### Registration Tips

- **Capture from the live feed**, not from a photo — embedding quality is best when the registration matches the operating conditions
- **Register multiple times** — the system already does this automatically, but if a person is consistently misrecognized, add another capture
- **Use real names** — internal IDs are fine for testing, but production should use real names for the audit trail

### Sensitivity Tuning

- **False positives?** Increase the relevant confidence threshold
- **Missing events?** Decrease the threshold, or increase the hold/cooldown time
- **Alert spam?** Increase the cooldown
- **Slow detection?** Reduce input size from 1280 to 960

### Performance Tips

- **Use a dedicated GPU** — the system needs ~1.8 GB VRAM; an integrated GPU will work but at lower FPS
- **Limit concurrent browsers** — each connected WebSocket adds a small CPU cost
- **Archive old snapshots** — the `data/alerts/` folder grows with each event

### Security Tips

- **Change default credentials** — both the camera and the Sentinel web UI
- **Use HTTPS in production** — place Sentinel behind a reverse proxy (nginx, Caddy)
- **Restrict network access** — bind to a private IP, not `0.0.0.0`
- **Back up the face dataset** — `face_dataset/` is your most valuable asset

---

## Troubleshooting

### Server won't start
- **Check Python version:** `python --version` (needs 3.11+)
- **Check CUDA:** `python -c "import torch; print(torch.cuda.is_available())"`
- **Check port:** `netstat -an | findstr 8000` — change `SS_PORT` if busy

### Camera not connecting
- **Test RTSP directly:** `ffplay rtsp://user:pass@host:554/Streaming/Channels/101`
- **Check credentials** in the Settings tab
- **Verify the camera is reachable** from the Sentinel server's network

### Faces are not being recognized
- **Check the embedding match threshold** — lower it if too strict
- **Verify the registered face is good quality** — re-register in better lighting
- **Check the camera angle** — faces should be near-frontal at registration

### Threats are not firing
- **Check the threat model loaded** — see `data/logs/` for the load messages
- **Lower the weapon confidence** in settings
- **Verify the scene contains the expected class** — try a still image first

### Items are not being tracked
- **Verify the item is detected by YOLO** — check the dashboard's "Phones" or "Bags" stat
- **Lower the IoU threshold** in settings
- **Check `data/items.json`** — persisted items are loaded on startup

### High memory usage
- **Reduce max embeddings per person** — 4 is usually enough
- **Archive old events** — `data/items_log.json` and `data/items.json` grow with use
- **Reduce R3D-18 buffer size** in code

### WebSocket keeps disconnecting
- **Check network stability** — WebSocket is sensitive to dropouts
- **Check the operator's browser** — Chrome/Edge work best
- **Increase timeout** in the WebSocket client config

---

## Glossary

| Term | Definition |
|---|---|
| **RTSP** | Real-Time Streaming Protocol — the standard for IP camera video |
| **YOLO** | You Only Look Once — a family of real-time object detection models |
| **ArcFace** | A face recognition embedding model known for high accuracy |
| **InsightFace** | Open-source toolkit for face analysis (uses ArcFace internally) |
| **Embedding** | A numeric vector (here, 512 numbers) that represents a face's identity |
| **IoU** | Intersection over Union — a measure of bounding-box overlap (0 to 1) |
| **R3D-18** | A 3D ResNet model trained on Kinetics-400 for action recognition |
| **Kinetics-400** | A large video dataset with 400 human action classes |
| **WebSocket** | A persistent two-way network connection for real-time push |
| **MJPEG** | Motion JPEG — a simple video format used for browser streaming |
| **State machine** | A computational model with explicit states and transitions |
| **Cosine distance** | The angle between two vectors — used here to compare face embeddings |
| **CUDA** | NVIDIA's GPU computing platform |
| **ONNX** | Open Neural Network Exchange — a portable model format |
| **Buffalo-L** | A pre-trained model pack from InsightFace (detector + recognizer) |

---

## Getting More Help

- **Source code:** All files are in the `src/` directory with Clean Architecture layout
- **README:** Technical installation and API reference
- **In-code documentation:** Every module has a docstring; every class has its purpose in the class definition
- **Speaker notes:** The defense PowerPoint has detailed speaking points for each slide

---

*Sentinel — Eyes that never blink.*
