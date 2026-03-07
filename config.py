# config.py — AIRSS Drone System

import os
from dotenv import load_dotenv

load_dotenv()

STREAM_URL           = os.getenv("STREAM_URL", "0")
MODEL_PATH           = os.getenv("MODEL_PATH", "yolov8n.pt")
CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.55"))

# ── Performance ──────────────────────────────────────
FRAME_SKIP   = int(os.getenv("FRAME_SKIP",   "5"))
INPUT_WIDTH  = int(os.getenv("INPUT_WIDTH",  "416"))
INPUT_HEIGHT = int(os.getenv("INPUT_HEIGHT", "416"))
JPEG_QUALITY = int(os.getenv("JPEG_QUALITY", "60"))

SCREENSHOT_COOLDOWN = int(os.getenv("SCREENSHOT_COOLDOWN", "10"))
GPS_CACHE_TTL       = int(os.getenv("GPS_CACHE_TTL",       "5"))
MAP_REBUILD_EVERY   = int(os.getenv("MAP_REBUILD_EVERY",   "1"))

# ── Server ───────────────────────────────────────────
DASHBOARD_PORT = int(os.getenv("DASHBOARD_PORT", "5000"))
HOTSPOT_IP     = os.getenv("HOTSPOT_IP", "192.168.137.1")

# ── Locations ────────────────────────────────────────
BASE_LOCATION = [
    float(os.getenv("BASE_LAT", "30.7333")),
    float(os.getenv("BASE_LON", "76.7794")),
]

# ── Manual GPS override ──────────────────────────────
# Set these in .env to your exact location for indoor testing
# Leave blank to disable — system will use phone GPS automatically
_manual_lat = os.getenv("MANUAL_GPS_LAT", "")
_manual_lon = os.getenv("MANUAL_GPS_LON", "")
MANUAL_GPS = (
    (float(_manual_lat), float(_manual_lon))
    if _manual_lat and _manual_lon else None
)

# ── Email ────────────────────────────────────────────
EMAIL_SENDER   = os.getenv("EMAIL_SENDER",   "")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "")
EMAIL_RECEIVER = os.getenv("EMAIL_RECEIVER", "")

ALERT_COOLDOWN_SECONDS = int(os.getenv("ALERT_COOLDOWN_SECONDS", "30"))
SMTP_SERVER            = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT              = int(os.getenv("SMTP_PORT", "587"))

# ── Voice ────────────────────────────────────────────
VOICE_RATE   = int(os.getenv("VOICE_RATE",   "150"))
VOICE_VOLUME = float(os.getenv("VOICE_VOLUME", "1.0"))

if EMAIL_SENDER:
    print(f"[Config] Credentials loaded for: {EMAIL_SENDER}")
if MANUAL_GPS:
    print(f"[Config] Manual GPS override active: {MANUAL_GPS}")
