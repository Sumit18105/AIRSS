# shared_state.py — AIRSS Drone System

import threading
from collections import deque
from datetime import datetime


class SharedState:

    def __init__(self, max_log_entries: int = 100):
        self._lock           = threading.Lock()
        self.latest_frame    = None
        self.survivor_count  = 0
        self.total_survivors = 0
        self.fps             = 0.0
        self.detection_log   = deque(maxlen=max_log_entries)
        self.rescue_requests = deque(maxlen=100)    # dedicated rescue storage
        self.gps_points      = []
        self.mission_start   = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.is_active       = False
        self.map_html        = None
        self.wifi_devices    = []
        self._mapper         = None

    # ── Frame ───────────────────────────────────────────
    def update_frame(self, frame):
        with self._lock:
            self.latest_frame = frame.copy()

    def get_frame(self):
        with self._lock:
            return self.latest_frame.copy() \
                if self.latest_frame is not None else None

    # ── Detection counts ────────────────────────────────
    def update_count(self, count: int):
        with self._lock:
            self.survivor_count = count

    def get_count(self) -> int:
        with self._lock:
            return self.survivor_count

    def log_event(self, count: int):
        with self._lock:
            self.total_survivors += count

    def update_fps(self, fps: float):
        with self._lock:
            self.fps = fps

    # ── Detection log ────────────────────────────────────
    def add_log_entry(self, entry: dict):
        with self._lock:
            self.detection_log.appendleft(entry)

    def get_log(self, limit: int = 20) -> list:
        with self._lock:
            return list(self.detection_log)[:limit]

    # ── Rescue requests (dedicated, separate from detection log) ──
    def add_rescue_request(self, entry: dict):
        with self._lock:
            self.rescue_requests.appendleft(entry)

    def get_rescue_requests(self, limit: int = 50) -> list:
        with self._lock:
            return list(self.rescue_requests)[:limit]

    # ── GPS ─────────────────────────────────────────────
    def add_gps_point(self, lat: float, lon: float, meta: dict):
        with self._lock:
            self.gps_points.append({"lat": lat, "lon": lon, **meta})

    def get_gps_points(self) -> list:
        with self._lock:
            return list(self.gps_points)

    # ── Map ─────────────────────────────────────────────
    def update_map_html(self, html: str):
        with self._lock:
            self.map_html = html

    def get_map_html(self) -> str:
        with self._lock:
            return self.map_html

    # ── WiFi ────────────────────────────────────────────
    def update_wifi_devices(self, devices: list):
        with self._lock:
            self.wifi_devices = devices

    def get_wifi_devices(self) -> list:
        with self._lock:
            return list(self.wifi_devices)

    # ── Mapper ref ──────────────────────────────────────
    def set_mapper(self, mapper):
        with self._lock:
            self._mapper = mapper

    def get_mapper(self):
        with self._lock:
            return self._mapper

    # ── Stats ────────────────────────────────────────────
    def get_stats(self) -> dict:
        with self._lock:
            return {
                "survivor_count" : self.survivor_count,
                "total_survivors": self.total_survivors,
                "fps"            : self.fps,
                "mission_start"  : self.mission_start,
                "total_events"   : len(self.detection_log),
                "rescue_requests": len(self.rescue_requests),
                "is_active"      : self.is_active,
                "wifi_devices"   : len(self.wifi_devices),
            }


state = SharedState()
