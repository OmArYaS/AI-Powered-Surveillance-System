"""
Generates all diagram PNGs used in the presentation.
Theme: Midnight Blue + Gold
"""
import os
import math
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Circle, Rectangle, Wedge
from matplotlib.lines import Line2D
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import ConnectionPatch
import numpy as np

# Theme colors
BG = "#0B1A2E"          # Midnight blue background
BG2 = "#0F2240"         # Lighter midnight
GOLD = "#D4AF37"        # Primary gold
GOLD_LIGHT = "#E8C869"  # Light gold
GOLD_DARK = "#9C7C1F"   # Dark gold
NAVY = "#1E3A5F"        # Medium navy
NAVY_LIGHT = "#2A4A75"  # Light navy
TEXT = "#FFFFFF"        # White text
TEXT_DIM = "#B8C5D3"    # Dim text
SUCCESS = "#4ADE80"     # Green
WARN = "#FBBF24"        # Amber
DANGER = "#EF4444"      # Red
INFO = "#60A5FA"        # Blue
PURPLE = "#A78BFA"      # Purple

# Standard size for slides (16:9, larger)
FIGSIZE_W = 16
FIGSIZE_H = 9

plt.rcParams['font.family'] = 'DejaVu Sans'
plt.rcParams['font.size'] = 12

ASSETS = os.path.join(os.path.dirname(__file__), "assets")
os.makedirs(ASSETS, exist_ok=True)


def save(fig, name, dpi=150):
    path = os.path.join(ASSETS, name)
    fig.savefig(path, dpi=dpi, bbox_inches='tight', facecolor=BG, edgecolor='none')
    plt.close(fig)
    print(f"  + {name}")


# ----------------------------------------------------------------------
# 1. Title slide background (gradient with shield logo)
# ----------------------------------------------------------------------
def make_title_bg():
    fig, ax = plt.subplots(figsize=(FIGSIZE_W, FIGSIZE_H))
    ax.set_xlim(0, 16)
    ax.set_ylim(0, 9)
    ax.axis('off')

    # Background gradient
    for i in range(200):
        t = i / 200
        c = (0.04 + 0.04 * t, 0.10 + 0.10 * t, 0.18 + 0.18 * t)
        ax.add_patch(Rectangle((0, 9 * t), 16, 9/200, color=c, zorder=0))

    # Gold accent lines
    ax.add_patch(Rectangle((0, 0), 16, 0.05, color=GOLD, zorder=2))
    ax.add_patch(Rectangle((0, 8.95), 16, 0.05, color=GOLD, zorder=2))

    # Decorative shield logo (centered)
    cx, cy = 8, 6
    shield = mpatches.FancyBboxPatch((cx-1.4, cy-1.6), 2.8, 3.2,
                                      boxstyle="round,pad=0.0,rounding_size=0.5",
                                      facecolor='none', edgecolor=GOLD, linewidth=4, zorder=3)
    ax.add_patch(shield)
    inner = mpatches.FancyBboxPatch((cx-1.1, cy-1.3), 2.2, 2.6,
                                     boxstyle="round,pad=0.0,rounding_size=0.4",
                                     facecolor='none', edgecolor=GOLD_LIGHT, linewidth=2, zorder=3)
    ax.add_patch(inner)
    # Checkmark
    ax.plot([cx-0.6, cx-0.1, cx+0.7], [cy+0.1, cy-0.4, cy+0.5],
            color=GOLD, linewidth=5, zorder=4, solid_capstyle='round')

    # Corner ornaments
    for cx, cy, dx, dy in [(1, 1, 1, 1), (15, 1, -1, 1), (1, 8, 1, -1), (15, 8, -1, -1)]:
        ax.plot([cx, cx+dx*0.5], [cy, cy], color=GOLD, linewidth=1.5, alpha=0.6)
        ax.plot([cx, cx], [cy, cy+dy*0.5], color=GOLD, linewidth=1.5, alpha=0.6)

    save(fig, "title_bg.png")


# ----------------------------------------------------------------------
# 2. System architecture (4-layer clean architecture)
# ----------------------------------------------------------------------
def make_architecture():
    fig, ax = plt.subplots(figsize=(FIGSIZE_W, FIGSIZE_H))
    ax.set_xlim(0, 16)
    ax.set_ylim(0, 9)
    ax.axis('off')
    ax.set_facecolor(BG)
    fig.patch.set_facecolor(BG)

    layers = [
        ("Presentation", "FastAPI · WebSocket · Jinja2 · HTML/CSS/JS", NAVY_LIGHT, 7.0),
        ("Use Cases", "Stream · Detection · Face · Threat · Item Tracking", NAVY, 5.4),
        ("Adapters", "RTSP · YOLO · InsightFace · R3D · IoU · JSON", NAVY_LIGHT, 3.8),
        ("Domain", "Entities · Interfaces · Pure Business Rules", GOLD_DARK, 2.2),
    ]

    for name, sub, color, y in layers:
        box = FancyBboxPatch((2, y-0.6), 12, 1.2,
                              boxstyle="round,pad=0.05,rounding_size=0.15",
                              facecolor=color, edgecolor=GOLD, linewidth=2)
        ax.add_patch(box)
        ax.text(8, y+0.15, name, ha='center', va='center', fontsize=22, color=TEXT, fontweight='bold')
        ax.text(8, y-0.25, sub, ha='center', va='center', fontsize=13, color=TEXT_DIM, style='italic')

    # Downward arrows between layers
    for y1, y2 in [(6.4, 6.0), (4.8, 4.4), (3.2, 2.8)]:
        ax.annotate("", xy=(8, y2), xytext=(8, y1),
                    arrowprops=dict(arrowstyle="->", color=GOLD, lw=2))

    # Upward arrows (dependency inversion)
    for y1, y2 in [(2.8, 3.2), (4.4, 4.8), (6.0, 6.4)]:
        ax.annotate("", xy=(8, y2), xytext=(8, y1),
                    arrowprops=dict(arrowstyle="->", color=INFO, lw=1.2, alpha=0.5, linestyle='--'))

    # Side labels
    ax.text(0.7, 7.0, "INPUT", color=GOLD, fontsize=10, rotation=90, ha='center', va='center', fontweight='bold')
    ax.text(0.7, 5.4, "ORCHESTRATE", color=GOLD, fontsize=10, rotation=90, ha='center', va='center', fontweight='bold')
    ax.text(0.7, 3.8, "I/O", color=GOLD, fontsize=10, rotation=90, ha='center', va='center', fontweight='bold')
    ax.text(0.7, 2.2, "PURE", color=GOLD, fontsize=10, rotation=90, ha='center', va='center', fontweight='bold')

    ax.text(15.3, 7.0, "HTTP · WS · UI", color=TEXT_DIM, fontsize=10, rotation=90, ha='center', va='center')
    ax.text(15.3, 5.4, "domain logic", color=TEXT_DIM, fontsize=10, rotation=90, ha='center', va='center')
    ax.text(15.3, 3.8, "frame · model · disk", color=TEXT_DIM, fontsize=10, rotation=90, ha='center', va='center')
    ax.text(15.3, 2.2, "no I/O", color=TEXT_DIM, fontsize=10, rotation=90, ha='center', va='center')

    # Title
    ax.text(8, 8.5, "Clean Architecture · 4 Layers", ha='center', va='center', fontsize=24, color=GOLD, fontweight='bold')

    save(fig, "architecture.png")


# ----------------------------------------------------------------------
# 3. Detection pipeline (RTSP → Frame → YOLO → Annotate → Stream)
# ----------------------------------------------------------------------
def make_detection_pipeline():
    fig, ax = plt.subplots(figsize=(FIGSIZE_W, FIGSIZE_H))
    ax.set_xlim(0, 16)
    ax.set_ylim(0, 9)
    ax.axis('off')
    ax.set_facecolor(BG)
    fig.patch.set_facecolor(BG)

    boxes = [
        ("RTSP Camera", "192.168.1.7:554", INFO, 1.0),
        ("Frame Reader", "OpenCV · Thread", NAVY_LIGHT, 3.0),
        ("YOLO11s", "Inference @ 1280", GOLD, 5.0),
        ("Per-Class Conf", "Phone: 0.20  Bag: 0.35", NAVY_LIGHT, 7.0),
        ("Annotation", "Boxes · Labels · FPS", GOLD, 9.0),
        ("MJPEG Stream", "Output to Browser", SUCCESS, 11.0),
        ("WebSocket", "Real-time JSON", SUCCESS, 13.0),
        ("REST API", "Historical + Stats", INFO, 15.0),
    ]

    for i, (name, sub, color, x) in enumerate(boxes):
        box = FancyBboxPatch((x-0.85, 4.0), 1.7, 1.4,
                              boxstyle="round,pad=0.05,rounding_size=0.12",
                              facecolor=color, edgecolor=GOLD, linewidth=1.5)
        ax.add_patch(box)
        ax.text(x, 4.95, name, ha='center', va='center', fontsize=11, color=TEXT, fontweight='bold', wrap=True)
        ax.text(x, 4.4, sub, ha='center', va='center', fontsize=8, color=TEXT_DIM, style='italic', wrap=True)

        if i < len(boxes) - 1:
            next_x = boxes[i+1][3]
            ax.annotate("", xy=(next_x-0.85, 4.7), xytext=(x+0.85, 4.7),
                        arrowprops=dict(arrowstyle="->", color=GOLD, lw=2))

    # Title
    ax.text(8, 8.0, "Object Detection Pipeline", ha='center', va='center', fontsize=26, color=GOLD, fontweight='bold')
    ax.text(8, 7.2, "YOLO11s · CUDA · 25 ms / frame · 40 FPS capability", ha='center', va='center', fontsize=14, color=TEXT_DIM, style='italic')

    # Performance
    ax.text(8, 1.5, "Persons · Phones · Backpacks · Handbags · Knives · Scissors", ha='center', va='center', fontsize=13, color=GOLD_LIGHT)

    save(fig, "detection_pipeline.png")


# ----------------------------------------------------------------------
# 4. Face recognition pipeline
# ----------------------------------------------------------------------
def make_face_pipeline():
    fig, ax = plt.subplots(figsize=(FIGSIZE_W, FIGSIZE_H))
    ax.set_xlim(0, 16)
    ax.set_ylim(0, 9)
    ax.axis('off')
    ax.set_facecolor(BG)
    fig.patch.set_facecolor(BG)

    # Top flow
    stages = [
        ("Face Detect", "RetinaFace (Buffalo-L)", INFO, 1.5),
        ("Align & Crop", "112×112 normalized", NAVY_LIGHT, 4.0),
        ("ArcFace R100", "512-dim embedding", GOLD, 6.5),
        ("Cosine Match", "vs stored fingerprints", NAVY_LIGHT, 9.0),
        ("Decision", "Known / New / Returning", SUCCESS, 11.5),
    ]
    for i, (name, sub, color, x) in enumerate(stages):
        box = FancyBboxPatch((x-1.0, 5.5), 2.0, 1.6,
                              boxstyle="round,pad=0.05,rounding_size=0.12",
                              facecolor=color, edgecolor=GOLD, linewidth=1.5)
        ax.add_patch(box)
        ax.text(x, 6.5, name, ha='center', va='center', fontsize=12, color=TEXT, fontweight='bold')
        ax.text(x, 5.9, sub, ha='center', va='center', fontsize=9, color=TEXT_DIM, style='italic')

        if i < len(stages) - 1:
            nx = stages[i+1][3]
            ax.annotate("", xy=(nx-1.0, 6.3), xytext=(x+1.0, 6.3),
                        arrowprops=dict(arrowstyle="->", color=GOLD, lw=2))

    # Multi-embedding fingerprint box
    box = FancyBboxPatch((1.5, 2.5), 6, 2.0,
                          boxstyle="round,pad=0.05,rounding_size=0.15",
                          facecolor=GOLD_DARK, edgecolor=GOLD, linewidth=2)
    ax.add_patch(box)
    ax.text(4.5, 4.0, "Multi-Embedding Fingerprint", ha='center', va='center', fontsize=14, color=TEXT, fontweight='bold')
    ax.text(4.5, 3.4, "Up to 8 embeddings per person\nQuality-gated · angle-diverse · time-diverse", ha='center', va='center', fontsize=10, color=TEXT_DIM)

    # Auto-register flow
    box = FancyBboxPatch((9.0, 2.5), 5.5, 2.0,
                          boxstyle="round,pad=0.05,rounding_size=0.15",
                          facecolor=NAVY_LIGHT, edgecolor=GOLD, linewidth=2)
    ax.add_patch(box)
    ax.text(11.75, 4.0, "Auto-Register Unknown", ha='center', va='center', fontsize=14, color=TEXT, fontweight='bold')
    ax.text(11.75, 3.4, "5-second temporal cooldown\nFront-facing · 60×60 min face size", ha='center', va='center', fontsize=10, color=TEXT_DIM)

    # Arrows from "Decision" to fingerprint + auto-register
    ax.annotate("", xy=(4.5, 4.5), xytext=(11.5, 5.5),
                arrowprops=dict(arrowstyle="->", color=GOLD, lw=1.5, connectionstyle="arc3,rad=0.2"))
    ax.annotate("", xy=(11.75, 4.5), xytext=(11.5, 5.5),
                arrowprops=dict(arrowstyle="->", color=GOLD, lw=1.5))

    # Title
    ax.text(8, 8.2, "Face Recognition Pipeline", ha='center', va='center', fontsize=26, color=GOLD, fontweight='bold')
    ax.text(8, 7.3, "InsightFace · ArcFace-R100 · 512-D · ONNX + CUDA", ha='center', va='center', fontsize=14, color=TEXT_DIM, style='italic')

    save(fig, "face_pipeline.png")


# ----------------------------------------------------------------------
# 5. Threat detection - multi-model fusion
# ----------------------------------------------------------------------
def make_threat_pipeline():
    fig, ax = plt.subplots(figsize=(FIGSIZE_W, FIGSIZE_H))
    ax.set_xlim(0, 16)
    ax.set_ylim(0, 9)
    ax.axis('off')
    ax.set_facecolor(BG)
    fig.patch.set_facecolor(BG)

    # Source: Frame
    box = FancyBboxPatch((0.5, 4.0), 2.5, 1.5,
                          boxstyle="round,pad=0.05,rounding_size=0.12",
                          facecolor=NAVY, edgecolor=GOLD, linewidth=2)
    ax.add_patch(box)
    ax.text(1.75, 5.0, "Live Frame", ha='center', va='center', fontsize=14, color=TEXT, fontweight='bold')
    ax.text(1.75, 4.4, "RTSP feed", ha='center', va='center', fontsize=10, color=TEXT_DIM)

    # Three parallel models
    models = [
        ("Weapon\nDetection", "YOLOv8s\ngun.pt", "640 px · conf 0.30", DANGER, 4.5, 7.5),
        ("Pose\nEstimation", "YOLOv8n-Pose", "17 keypoints", INFO, 4.5, 5.0),
        ("Action\nRecognition", "R3D-18", "16-frame · 0.5 s", PURPLE, 4.5, 2.5),
    ]
    for name, model, sub, color, x, y in models:
        box = FancyBboxPatch((x-1.0, y-0.8), 2.0, 1.6,
                              boxstyle="round,pad=0.05,rounding_size=0.12",
                              facecolor=color, edgecolor=GOLD, linewidth=1.5)
        ax.add_patch(box)
        ax.text(x, y+0.3, name, ha='center', va='center', fontsize=11, color=TEXT, fontweight='bold')
        ax.text(x, y-0.1, model, ha='center', va='center', fontsize=10, color=TEXT)
        ax.text(x, y-0.5, sub, ha='center', va='center', fontsize=8, color=TEXT_DIM, style='italic')

        # Arrow from frame to model
        ax.annotate("", xy=(x-1.0, y), xytext=(3.0, 4.75),
                    arrowprops=dict(arrowstyle="->", color=GOLD, lw=1.5))

    # Rule engine
    box = FancyBboxPatch((6.5, 3.5), 3.0, 2.5,
                          boxstyle="round,pad=0.05,rounding_size=0.15",
                          facecolor=GOLD, edgecolor=GOLD_LIGHT, linewidth=3)
    ax.add_patch(box)
    ax.text(8.0, 5.5, "Rule Engine", ha='center', va='center', fontsize=18, color=BG, fontweight='bold')
    ax.text(8.0, 4.8, "Weapon · Violence · Proximity", ha='center', va='center', fontsize=10, color=BG)
    ax.text(8.0, 4.3, "Escalation +0.20", ha='center', va='center', fontsize=10, color=BG)
    ax.text(8.0, 3.9, "5 s cooldown", ha='center', va='center', fontsize=10, color=BG)

    # Arrows from models to rule engine
    for _, _, _, _, x, y in models:
        ax.annotate("", xy=(6.5, 4.7 if y > 4 else 4.3 if y > 2.5 else 4.0), xytext=(x+1.0, y),
                    arrowprops=dict(arrowstyle="->", color=GOLD, lw=1.5))

    # Outputs
    outputs = [
        ("LOW", "0.20", TEXT_DIM, 11.5, 7.0),
        ("MEDIUM", "0.45", INFO, 11.5, 5.5),
        ("HIGH", "0.70", WARN, 11.5, 4.0),
        ("CRITICAL", "0.95", DANGER, 11.5, 2.5),
    ]
    for label, score, color, x, y in outputs:
        box = FancyBboxPatch((x-0.8, y-0.5), 1.6, 1.0,
                              boxstyle="round,pad=0.05,rounding_size=0.1",
                              facecolor=color, edgecolor='white', linewidth=1)
        ax.add_patch(box)
        ax.text(x, y+0.15, label, ha='center', va='center', fontsize=11, color=TEXT, fontweight='bold')
        ax.text(x, y-0.25, f"score ≥ {score}", ha='center', va='center', fontsize=8, color=TEXT)

    # Arrow from rule engine to outputs
    ax.annotate("", xy=(10.7, 4.7), xytext=(9.5, 4.7),
                arrowprops=dict(arrowstyle="->", color=GOLD, lw=2))

    # Side effects
    ax.text(13.5, 1.5, "Snapshot\ndata/alerts/\nYYYY-MM-DD/", ha='center', va='center',
            fontsize=10, color=TEXT_DIM, style='italic',
            bbox=dict(boxstyle="round,pad=0.3", facecolor=NAVY, edgecolor=GOLD))
    ax.annotate("", xy=(13.5, 2.0), xytext=(11.5, 4.0),
                arrowprops=dict(arrowstyle="->", color=GOLD, lw=1.5, linestyle='--'))

    # WebSocket push
    box = FancyBboxPatch((13.0, 6.0), 2.5, 1.2,
                          boxstyle="round,pad=0.05,rounding_size=0.1",
                          facecolor=NAVY_LIGHT, edgecolor=GOLD, linewidth=1.5)
    ax.add_patch(box)
    ax.text(14.25, 6.8, "WebSocket", ha='center', va='center', fontsize=11, color=GOLD, fontweight='bold')
    ax.text(14.25, 6.3, "→ Dashboard", ha='center', va='center', fontsize=9, color=TEXT_DIM)
    ax.annotate("", xy=(13.0, 6.6), xytext=(11.5, 5.5),
                arrowprops=dict(arrowstyle="->", color=GOLD, lw=1.5, linestyle='--'))

    # Title
    ax.text(8, 8.2, "Threat Detection · Multi-Model Fusion", ha='center', va='center', fontsize=24, color=GOLD, fontweight='bold')

    save(fig, "threat_pipeline.png")


# ----------------------------------------------------------------------
# 6. Theft detection state machine
# ----------------------------------------------------------------------
def make_state_machine():
    fig, ax = plt.subplots(figsize=(FIGSIZE_W, FIGSIZE_H))
    ax.set_xlim(0, 16)
    ax.set_ylim(0, 9)
    ax.axis('off')
    ax.set_facecolor(BG)
    fig.patch.set_facecolor(BG)

    # States as nodes
    states = [
        ("NEW", "Frame 1\nappear", NAVY_LIGHT, 2.5, 5.5),
        ("STATIONARY", "On surface\nno owner", INFO, 6.5, 7.0),
        ("HELD", "Owner nearby\n≥ 1.5 s", SUCCESS, 10.5, 5.5),
        ("ABANDONED", "Idle ≥ 30 s", WARN, 13.0, 2.5),
    ]
    for name, sub, color, x, y in states:
        # Hexagon-like box
        box = FancyBboxPatch((x-1.0, y-0.7), 2.0, 1.4,
                              boxstyle="round,pad=0.05,rounding_size=0.25",
                              facecolor=color, edgecolor=GOLD, linewidth=2.5)
        ax.add_patch(box)
        ax.text(x, y+0.2, name, ha='center', va='center', fontsize=14, color=TEXT, fontweight='bold')
        ax.text(x, y-0.3, sub, ha='center', va='center', fontsize=9, color=TEXT_DIM, style='italic')

    # Transitions
    # NEW → STATIONARY
    ax.annotate("", xy=(5.5, 6.8), xytext=(3.5, 5.8),
                arrowprops=dict(arrowstyle="->", color=GOLD, lw=2.5,
                                connectionstyle="arc3,rad=0.2"))
    ax.text(4.4, 6.7, "first frame", ha='center', va='center', fontsize=9, color=GOLD_LIGHT, style='italic')

    # STATIONARY → HELD (claim)
    ax.annotate("", xy=(9.5, 5.8), xytext=(7.5, 6.8),
                arrowprops=dict(arrowstyle="->", color=SUCCESS, lw=2.5,
                                connectionstyle="arc3,rad=-0.2"))
    ax.text(8.5, 6.7, "CLAIM (≥ 1.5 s)", ha='center', va='center', fontsize=10, color=SUCCESS, fontweight='bold')

    # HELD → STATIONARY (drop)
    ax.annotate("", xy=(7.5, 6.4), xytext=(9.5, 5.4),
                arrowprops=dict(arrowstyle="->", color=INFO, lw=2.5,
                                connectionstyle="arc3,rad=-0.2"))
    ax.text(8.5, 5.7, "DROP", ha='center', va='center', fontsize=10, color=INFO, fontweight='bold')

    # STATIONARY → ABANDONED
    ax.annotate("", xy=(12.0, 3.0), xytext=(7.5, 6.5),
                arrowprops=dict(arrowstyle="->", color=WARN, lw=2.5,
                                connectionstyle="arc3,rad=0.3"))
    ax.text(8.5, 4.5, "ABANDONED (30 s)", ha='center', va='center', fontsize=10, color=WARN, fontweight='bold')

    # THEFT event (dashed red)
    ax.annotate("", xy=(11.5, 4.5), xytext=(7.0, 5.8),
                arrowprops=dict(arrowstyle="->", color=DANGER, lw=2.5, linestyle='--',
                                connectionstyle="arc3,rad=-0.4"))
    ax.text(7.5, 4.0, "THEFT\n(disappear ≥ 3 s\nor stranger near)", ha='center', va='center',
            fontsize=9, color=DANGER, fontweight='bold',
            bbox=dict(boxstyle="round,pad=0.3", facecolor=BG2, edgecolor=DANGER, linewidth=1.5))

    # Legend
    legend_y = 1.0
    items = [
        (GOLD, "normal transition"),
        (SUCCESS, "ownership gain"),
        (INFO, "ownership loss"),
        (WARN, "memory event"),
        (DANGER, "ALERT (theft)"),
    ]
    for color, text in items:
        ax.plot([0.5, 1.0], [legend_y, legend_y], color=color, lw=3, solid_capstyle='round')
        ax.text(1.1, legend_y, text, va='center', fontsize=10, color=TEXT_DIM)
        legend_y += 0.0  # keep on same line

    # Title
    ax.text(8, 8.5, "Item Ownership · State Machine", ha='center', va='center', fontsize=26, color=GOLD, fontweight='bold')
    ax.text(8, 7.7, "5 ownership rules · 5-s event cooldown · forensic snapshot per theft", ha='center', va='center', fontsize=13, color=TEXT_DIM, style='italic')

    # Side panel: 5 rules
    rules = [
        "1. CLAIM · held ≥ 1.5 s → owner assigned",
        "2. DROP · owner leaves → state = STATIONARY (memory kept)",
        "3. THEFT · unknown + missing ≥ 3 s → ALERT",
        "4. THEFT · stranger near + missing ≥ 3 s → ALERT",
        "5. ABANDONED · idle ≥ 30 s → flag owner",
    ]
    for i, rule in enumerate(rules):
        ax.text(8, 1.0 - i*0.25, rule, ha='center', va='center', fontsize=10, color=TEXT_DIM)

    save(fig, "state_machine.png")


# ----------------------------------------------------------------------
# 7. Use case / deployment scenarios
# ----------------------------------------------------------------------
def make_use_cases():
    fig, ax = plt.subplots(figsize=(FIGSIZE_W, FIGSIZE_H))
    ax.set_xlim(0, 16)
    ax.set_ylim(0, 9)
    ax.axis('off')
    ax.set_facecolor(BG)
    fig.patch.set_facecolor(BG)

    use_cases = [
        ("Banks", "Vault monitoring\nStaff recognition\nThreat detection", DANGER, 2.5, 6.0),
        ("Malls", "Visitor analytics\nLost-child matching\nTheft prevention", INFO, 5.5, 7.0),
        ("Airports", "Restricted zones\nWatchlist alerts\nCrowd monitoring", GOLD, 8.5, 7.5),
        ("Hospitals", "Patient safety\nRestricted wards\nVisitor logs", SUCCESS, 11.5, 7.0),
        ("Schools", "Attendance\nStranger detection\nBullying alerts", PURPLE, 14.0, 6.0),
        ("Warehouses", "Inventory tracking\nTheft detection\nWorker safety", WARN, 3.5, 3.0),
        ("Residential", "Home security\nFamily recognition\nPackage alerts", INFO, 7.0, 2.5),
        ("Stadiums", "Crowd analytics\nIncident response\nPerimeter watch", DANGER, 10.5, 2.5),
        ("Government", "Classified areas\nIdentity verification\nAudit trail", GOLD, 13.5, 3.0),
    ]

    for name, desc, color, x, y in use_cases:
        box = FancyBboxPatch((x-1.0, y-0.7), 2.0, 1.4,
                              boxstyle="round,pad=0.05,rounding_size=0.15",
                              facecolor=color, edgecolor=GOLD, linewidth=1.5, alpha=0.85)
        ax.add_patch(box)
        ax.text(x, y+0.25, name, ha='center', va='center', fontsize=12, color=TEXT, fontweight='bold')
        ax.text(x, y-0.3, desc, ha='center', va='center', fontsize=8, color=TEXT_DIM, style='italic')

    # Title
    ax.text(8, 8.5, "Deployment Scenarios", ha='center', va='center', fontsize=26, color=GOLD, fontweight='bold')
    ax.text(8, 1.0, "From a single shop to nationwide infrastructure — one platform, infinite applications",
            ha='center', va='center', fontsize=12, color=TEXT_DIM, style='italic')

    save(fig, "use_cases.png")


# ----------------------------------------------------------------------
# 8. Performance bar chart
# ----------------------------------------------------------------------
def make_performance_chart():
    fig, ax = plt.subplots(figsize=(FIGSIZE_W, FIGSIZE_H))
    ax.set_facecolor(BG)
    fig.patch.set_facecolor(BG)

    operations = ["YOLO11s\n(1280)", "YOLOv8s\ngun.pt (640)", "YOLOv8n-Pose\n(640)", "R3D-18\n(16 frames)", "InsightFace\n(ArcFace)", "IoU Tracker\nper item", "Total\n(frame)"]
    times = [25, 15, 12, 35, 20, 2, 109]
    colors = [GOLD, DANGER, INFO, PURPLE, SUCCESS, NAVY_LIGHT, GOLD_LIGHT]

    bars = ax.barh(operations, times, color=colors, edgecolor='white', linewidth=1.5)
    ax.set_xlabel("Latency (ms)", color=TEXT_DIM, fontsize=14)
    ax.set_xlim(0, 130)
    ax.tick_params(colors=TEXT, labelsize=12)
    for spine in ax.spines.values():
        spine.set_color(NAVY)
    ax.grid(axis='x', color=NAVY, alpha=0.4)
    ax.set_axisbelow(True)

    # Annotate bars
    for bar, t in zip(bars, times):
        ax.text(t + 2, bar.get_y() + bar.get_height()/2, f"{t} ms",
                va='center', color=TEXT, fontsize=12, fontweight='bold')

    ax.set_title("Per-Model Latency Breakdown", color=GOLD, fontsize=24, fontweight='bold', pad=20)
    ax.text(60, -1.2, "Tested on RTX 3060 Laptop GPU · 1080p input · ~9 FPS end-to-end",
            ha='center', va='center', color=TEXT_DIM, fontsize=12, style='italic')

    save(fig, "performance.png")


# ----------------------------------------------------------------------
# 9. Tech stack icons
# ----------------------------------------------------------------------
def make_tech_stack():
    fig, ax = plt.subplots(figsize=(FIGSIZE_W, FIGSIZE_H))
    ax.set_xlim(0, 16)
    ax.set_ylim(0, 9)
    ax.axis('off')
    ax.set_facecolor(BG)
    fig.patch.set_facecolor(BG)

    # Categories
    categories = [
        ("Language", ["Python 3.11"], INFO, 2.5, 7.0),
        ("Backend", ["FastAPI 0.115", "Uvicorn", "WebSocket", "Pydantic"], SUCCESS, 7.0, 7.0),
        ("AI / ML", ["YOLO11s", "YOLOv8s", "YOLOv8n-Pose", "R3D-18", "InsightFace"], GOLD, 11.5, 7.0),
        ("Acceleration", ["CUDA 12.x", "ONNX Runtime", "PyTorch"], DANGER, 2.5, 3.0),
        ("Frontend", ["Jinja2", "HTML5", "CSS3", "Vanilla JS", "WebSocket API"], PURPLE, 7.0, 3.0),
        ("Storage", ["JSON files", "Multi-embeddings", "Snapshots"], WARN, 11.5, 3.0),
    ]
    for cat, items, color, x, y in categories:
        # Category label
        box = FancyBboxPatch((x-1.7, y-0.45), 3.4, 0.9,
                              boxstyle="round,pad=0.05,rounding_size=0.1",
                              facecolor=color, edgecolor=GOLD, linewidth=2)
        ax.add_patch(box)
        ax.text(x, y+0.15, cat, ha='center', va='center', fontsize=14, color=TEXT, fontweight='bold')
        for i, item in enumerate(items):
            ax.text(x, y-0.5 - i*0.4, "• " + item, ha='center', va='center', fontsize=11, color=TEXT_DIM)

    ax.text(8, 8.5, "Technology Stack", ha='center', va='center', fontsize=26, color=GOLD, fontweight='bold')

    save(fig, "tech_stack.png")


# ----------------------------------------------------------------------
# 10. Dashboard mockup (stylized illustration)
# ----------------------------------------------------------------------
def make_dashboard_mockup():
    fig, ax = plt.subplots(figsize=(FIGSIZE_W, FIGSIZE_H))
    ax.set_xlim(0, 16)
    ax.set_ylim(0, 9)
    ax.axis('off')
    ax.set_facecolor(BG)
    fig.patch.set_facecolor(BG)

    # Browser frame
    browser = FancyBboxPatch((0.5, 0.5), 15, 8,
                              boxstyle="round,pad=0.05,rounding_size=0.15",
                              facecolor='#0F1A2E', edgecolor=NAVY_LIGHT, linewidth=2)
    ax.add_patch(browser)
    # Top bar
    ax.add_patch(Rectangle((0.5, 7.8), 15, 0.7, color='#1A2A40'))
    ax.add_patch(Rectangle((0.5, 7.8), 15, 0.02, color=GOLD))
    # Traffic light dots
    for i, c in enumerate(['#EF4444', '#FBBF24', '#4ADE80']):
        ax.add_patch(Circle((0.85 + i*0.3, 8.15), 0.08, color=c))
    ax.text(2.5, 8.15, "Sentinel · Smart Surveillance", va='center', fontsize=10, color=TEXT_DIM, style='italic')

    # Sidebar
    ax.add_patch(Rectangle((0.5, 0.5), 2.0, 7.3, color='#0A1525'))
    sidebar_items = [("Dashboard", True), ("Faces", False), ("Alerts", False), ("Items", False), ("Settings", False)]
    for i, (label, active) in enumerate(sidebar_items):
        y = 7.2 - i*0.7
        if active:
            ax.add_patch(Rectangle((0.7, y-0.25), 1.6, 0.5, color=NAVY_LIGHT))
        ax.text(0.95, y, "●", color=GOLD if active else TEXT_DIM, fontsize=10, va='center')
        ax.text(1.2, y, label, color=TEXT if active else TEXT_DIM, fontsize=10, va='center', fontweight='bold' if active else 'normal')

    # Stat cards
    stats = [("Persons", "3", SUCCESS), ("Phones", "2", GOLD), ("Bags", "1", INFO), ("Threats", "0", DANGER)]
    for i, (label, val, color) in enumerate(stats):
        x = 3.0 + i*3.2
        ax.add_patch(FancyBboxPatch((x, 6.3), 2.9, 1.3,
                                     boxstyle="round,pad=0.05,rounding_size=0.08",
                                     facecolor='#152540', edgecolor=NAVY, linewidth=1))
        ax.text(x+0.2, 7.3, label, color=TEXT_DIM, fontsize=10, fontweight='bold')
        ax.text(x+0.2, 6.6, val, color=color, fontsize=22, fontweight='bold')

    # Video stream mock
    ax.add_patch(FancyBboxPatch((3.0, 2.2), 8.5, 3.8,
                                 boxstyle="round,pad=0.05,rounding_size=0.08",
                                 facecolor='#000000', edgecolor=GOLD, linewidth=1.5))
    ax.text(7.25, 4.1, "LIVE", ha='center', va='center', color=DANGER, fontsize=18, fontweight='bold', alpha=0.6)
    # Mock bounding boxes
    mock_boxes = [
        (3.7, 3.0, 4.7, 4.8, SUCCESS, "omar 0.92"),
        (5.0, 3.3, 5.8, 5.0, INFO, "phone 0.78"),
        (6.5, 2.8, 7.5, 4.6, SUCCESS, "ahmed 0.88"),
    ]
    for x1, y1, x2, y2, color, label in mock_boxes:
        ax.add_patch(Rectangle((x1, y1), x2-x1, y2-y1, fill=False, edgecolor=color, linewidth=2))
        ax.text(x1, y2+0.05, label, color=color, fontsize=7, fontweight='bold')
    # Live dot
    ax.add_patch(Circle((3.3, 5.7), 0.08, color=DANGER))
    ax.text(3.5, 5.7, "LIVE", color=TEXT, fontsize=9, va='center', fontweight='bold')

    # Right panel: live recognition
    ax.add_patch(FancyBboxPatch((12.0, 2.2), 3.3, 3.8,
                                 boxstyle="round,pad=0.05,rounding_size=0.08",
                                 facecolor='#152540', edgecolor=NAVY, linewidth=1))
    ax.text(12.2, 5.7, "Live Recognition", color=GOLD, fontsize=11, fontweight='bold')
    ax.add_patch(Rectangle((12.2, 5.55), 2.9, 0.02, color=GOLD))
    mock_recognition = [("omar", "98%", SUCCESS), ("ahmed", "94%", SUCCESS), ("person_001", "—", WARN)]
    for i, (name, conf, color) in enumerate(mock_recognition):
        y = 5.1 - i*0.7
        ax.add_patch(Circle((12.5, y), 0.2, color=color, alpha=0.4))
        ax.add_patch(Circle((12.5, y), 0.2, fill=False, edgecolor=color))
        ax.text(12.9, y, name, color=TEXT, fontsize=10, va='center')
        ax.text(14.9, y, conf, color=color, fontsize=10, va='center', ha='right', fontweight='bold')

    # Bottom row: threat ticker
    ax.add_patch(FancyBboxPatch((3.0, 0.8), 12.3, 1.0,
                                 boxstyle="round,pad=0.05,rounding_size=0.08",
                                 facecolor='#152540', edgecolor=NAVY, linewidth=1))
    ax.text(3.2, 1.3, "Active Threats", color=GOLD, fontsize=10, fontweight='bold')
    ax.text(3.2, 0.95, "System monitoring · All clear", color=TEXT_DIM, fontsize=9)

    save(fig, "dashboard_mockup.png")


# ----------------------------------------------------------------------
# 11. Logo / icon for cover
# ----------------------------------------------------------------------
def make_logo():
    fig, ax = plt.subplots(figsize=(4, 4))
    ax.set_xlim(0, 4)
    ax.set_ylim(0, 4)
    ax.axis('off')
    ax.set_facecolor(BG)
    fig.patch.set_facecolor(BG)

    # Shield outline
    shield_path = mpatches.FancyBboxPatch((0.7, 0.7), 2.6, 2.6,
                                          boxstyle="round,pad=0.0,rounding_size=0.5",
                                          facecolor='none', edgecolor=GOLD, linewidth=5)
    ax.add_patch(shield_path)
    inner = mpatches.FancyBboxPatch((1.0, 1.0), 2.0, 2.0,
                                     boxstyle="round,pad=0.0,rounding_size=0.4",
                                     facecolor='none', edgecolor=GOLD_LIGHT, linewidth=2)
    ax.add_patch(inner)
    ax.plot([1.4, 1.8, 2.6], [2.0, 1.6, 2.4],
            color=GOLD, linewidth=6, solid_capstyle='round', solid_joinstyle='round')

    save(fig, "logo.png", dpi=300)


# ----------------------------------------------------------------------
# 12. Workflow diagram
# ----------------------------------------------------------------------
def make_workflow():
    fig, ax = plt.subplots(figsize=(FIGSIZE_W, FIGSIZE_H))
    ax.set_xlim(0, 16)
    ax.set_ylim(0, 9)
    ax.axis('off')
    ax.set_facecolor(BG)
    fig.patch.set_facecolor(BG)

    # 6-stage circular flow
    cx, cy, r = 8, 4.5, 3.0
    stages = [
        ("1. CAPTURE", "RTSP stream\nFrame grab", INFO),
        ("2. DETECT", "YOLO inference\nBounding boxes", GOLD),
        ("3. RECOGNIZE", "Face match\nIdentity", SUCCESS),
        ("4. ANALYZE", "Threat + Item\nState update", PURPLE),
        ("5. DECIDE", "Rule engine\nScore → Level", WARN),
        ("6. NOTIFY", "WebSocket\nDashboard + Log", DANGER),
    ]
    n = len(stages)
    for i, (name, sub, color) in enumerate(stages):
        angle = 90 - i * (360 / n)
        x = cx + r * math.cos(math.radians(angle))
        y = cy + r * math.sin(math.radians(angle))
        box = FancyBboxPatch((x-1.0, y-0.55), 2.0, 1.1,
                              boxstyle="round,pad=0.05,rounding_size=0.12",
                              facecolor=color, edgecolor=GOLD, linewidth=2)
        ax.add_patch(box)
        ax.text(x, y+0.18, name, ha='center', va='center', fontsize=11, color=TEXT, fontweight='bold')
        ax.text(x, y-0.25, sub, ha='center', va='center', fontsize=8, color=TEXT_DIM, style='italic')

        # Arrow to next
        next_angle = 90 - ((i+1) % n) * (360 / n)
        nx = cx + r * math.cos(math.radians(next_angle))
        ny = cy + r * math.sin(math.radians(next_angle))
        ax.annotate("", xy=(nx-1.0*math.cos(math.radians(next_angle)),
                            ny-1.0*math.sin(math.radians(next_angle))),
                    xytext=(x+1.0*math.cos(math.radians(angle)),
                            y+1.0*math.sin(math.radians(angle))),
                    arrowprops=dict(arrowstyle="->", color=GOLD, lw=2,
                                    connectionstyle="arc3,rad=0.1"))

    # Center
    circle = Circle((cx, cy), 0.9, facecolor=BG2, edgecolor=GOLD, linewidth=3)
    ax.add_patch(circle)
    ax.text(cx, cy+0.2, "SENTINEL", ha='center', va='center', fontsize=12, color=GOLD, fontweight='bold')
    ax.text(cx, cy-0.2, "loop", ha='center', va='center', fontsize=10, color=TEXT_DIM, style='italic')

    # Title
    ax.text(8, 8.5, "Real-Time Processing Loop", ha='center', va='center', fontsize=24, color=GOLD, fontweight='bold')
    ax.text(8, 7.8, "Six stages · 10 Hz frame rate · sub-second end-to-end", ha='center', va='center', fontsize=12, color=TEXT_DIM, style='italic')

    save(fig, "workflow.png")


# ----------------------------------------------------------------------
# 13. Challenges vs solutions
# ----------------------------------------------------------------------
def make_challenges():
    fig, ax = plt.subplots(figsize=(FIGSIZE_W, FIGSIZE_H))
    ax.set_xlim(0, 16)
    ax.set_ylim(0, 9)
    ax.axis('off')
    ax.set_facecolor(BG)
    fig.patch.set_facecolor(BG)

    challenges = [
        ("TensorFlow on Windows\nhas no GPU", "Switched to InsightFace\n(ONNX Runtime + CUDA)", SUCCESS, 3.5, 7.0),
        ("No FFmpeg installed", "Used OpenCV VideoCapture\nas native fallback", SUCCESS, 8.0, 7.0),
        ("No CUDA toolkit\nin PATH", "Piggy-back on PyTorch's\nbundled CUDA libs", SUCCESS, 12.5, 7.0),
        ("IoU tracker bug:\nnew tracker created\nper frame", "Use 'is not None'\ncheck (not truthy check)", WARN, 3.5, 4.0),
        ("candidate_taker_since\noverwritten every frame", "Set timestamp only when\ncandidate changes", WARN, 8.0, 4.0),
        ("RTSP unreachable\nin dev environment", "Server boots cleanly\nwithout camera feed", INFO, 12.5, 4.0),
        ("YOLO classes\nnot aligned with\nreal objects", "YOLO11s + custom\nper-class confidence", INFO, 3.5, 1.0),
        ("Multi-camera RTSP", "Swappable repository\nabstraction", INFO, 8.0, 1.0),
        ("Event spam from\nrepeated triggers", "5-s cooldown +\nsnapshot evidence", INFO, 12.5, 1.0),
    ]
    for title, solution, color, x, y in challenges:
        # Challenge box (red-ish)
        box = FancyBboxPatch((x-1.7, y-0.55), 1.5, 1.1,
                              boxstyle="round,pad=0.05,rounding_size=0.1",
                              facecolor='#3A1E1E', edgecolor=DANGER, linewidth=1.5)
        ax.add_patch(box)
        ax.text(x-0.95, y, "CHALLENGE", ha='center', va='center', fontsize=8, color=DANGER, fontweight='bold')
        ax.text(x-0.95, y-0.25, title, ha='center', va='center', fontsize=7, color=TEXT_DIM)

        # Arrow
        ax.annotate("", xy=(x+0.05, y), xytext=(x-0.15, y),
                    arrowprops=dict(arrowstyle="->", color=GOLD, lw=1.5))

        # Solution box
        box = FancyBboxPatch((x+0.1, y-0.55), 1.5, 1.1,
                              boxstyle="round,pad=0.05,rounding_size=0.1",
                              facecolor=color, edgecolor=GOLD, linewidth=1.5, alpha=0.85)
        ax.add_patch(box)
        ax.text(x+0.85, y, "SOLUTION", ha='center', va='center', fontsize=8, color=GOLD if color != SUCCESS else BG, fontweight='bold')
        ax.text(x+0.85, y-0.25, solution, ha='center', va='center', fontsize=7, color=TEXT)

    # Title
    ax.text(8, 8.5, "Challenges & Solutions", ha='center', va='center', fontsize=24, color=GOLD, fontweight='bold')

    save(fig, "challenges.png")


# ----------------------------------------------------------------------
# 14. Privacy / Security features
# ----------------------------------------------------------------------
def make_privacy():
    fig, ax = plt.subplots(figsize=(FIGSIZE_W, FIGSIZE_H))
    ax.set_xlim(0, 16)
    ax.set_ylim(0, 9)
    ax.axis('off')
    ax.set_facecolor(BG)
    fig.patch.set_facecolor(BG)

    features = [
        ("Local-First", "100% on-premise\nNo cloud calls\nData never leaves your network", SUCCESS, 3.0, 6.5),
        ("Encrypted RTSP", "Credentials in env vars\n(SS_ prefix)\nNo hard-coded passwords", INFO, 8.0, 6.5),
        ("Audit Trail", "JSON event log\nForensic snapshots\nTamper-evident timestamps", WARN, 13.0, 6.5),
        ("Granular Access", "WebSocket auth ready\nRole-based UI possible\nForensic export API", PURPLE, 3.0, 2.5),
        ("Fail-Safe", "Camera disconnect\n→ graceful degradation\nNo data loss", SUCCESS, 8.0, 2.5),
        ("Open Source", "Transparent model weights\nAuditable code\nReproducible builds", INFO, 13.0, 2.5),
    ]
    for title, desc, color, x, y in features:
        box = FancyBboxPatch((x-2.0, y-1.1), 4.0, 2.2,
                              boxstyle="round,pad=0.05,rounding_size=0.15",
                              facecolor=color, edgecolor=GOLD, linewidth=2, alpha=0.85)
        ax.add_patch(box)
        ax.text(x, y+0.65, title, ha='center', va='center', fontsize=15, color=TEXT, fontweight='bold')
        ax.text(x, y-0.2, desc, ha='center', va='center', fontsize=10, color=TEXT_DIM)

    ax.text(8, 8.5, "Privacy & Security", ha='center', va='center', fontsize=26, color=GOLD, fontweight='bold')
    ax.text(8, 1.0, "Designed for sensitive environments — banks, schools, hospitals, government",
            ha='center', va='center', fontsize=12, color=TEXT_DIM, style='italic')

    save(fig, "privacy.png")


# ----------------------------------------------------------------------
# 15. Stats / impact infographic
# ----------------------------------------------------------------------
def make_impact_stats():
    fig, ax = plt.subplots(figsize=(FIGSIZE_W, FIGSIZE_H))
    ax.set_xlim(0, 16)
    ax.set_ylim(0, 9)
    ax.axis('off')
    ax.set_facecolor(BG)
    fig.patch.set_facecolor(BG)

    stats = [
        ("5", "AI Models\nRunning", GOLD, 2.5, 6.0),
        ("10 Hz", "Frame\nRate", SUCCESS, 5.5, 6.0),
        ("1080p", "RTSP\nResolution", INFO, 8.5, 6.0),
        ("8", "Embeddings\nper Person", PURPLE, 11.5, 6.0),
        ("530 MB", "Model\nFootprint", WARN, 14.0, 6.0),
        ("1.8 GB", "Active\nMemory", INFO, 2.5, 2.5),
        ("5s", "Threat\nCooldown", DANGER, 5.5, 2.5),
        ("3s", "Theft\nTrigger", DANGER, 8.5, 2.5),
        ("30s", "Abandon\nTrigger", WARN, 11.5, 2.5),
        ("200", "Events\nin Memory", SUCCESS, 14.0, 2.5),
    ]
    for value, label, color, x, y in stats:
        box = FancyBboxPatch((x-1.0, y-1.0), 2.0, 2.0,
                              boxstyle="round,pad=0.05,rounding_size=0.12",
                              facecolor=color, edgecolor=GOLD, linewidth=2, alpha=0.85)
        ax.add_patch(box)
        ax.text(x, y+0.3, value, ha='center', va='center', fontsize=18, color=TEXT, fontweight='bold')
        ax.text(x, y-0.5, label, ha='center', va='center', fontsize=9, color=TEXT_DIM)

    ax.text(8, 8.0, "By The Numbers", ha='center', va='center', fontsize=26, color=GOLD, fontweight='bold')

    save(fig, "impact_stats.png")


if __name__ == "__main__":
    print("Generating diagrams...")
    make_logo()
    make_title_bg()
    make_architecture()
    make_detection_pipeline()
    make_face_pipeline()
    make_threat_pipeline()
    make_state_machine()
    make_workflow()
    make_tech_stack()
    make_dashboard_mockup()
    make_performance_chart()
    make_use_cases()
    make_challenges()
    make_privacy()
    make_impact_stats()
    print(f"\nAll assets in: {ASSETS}")
