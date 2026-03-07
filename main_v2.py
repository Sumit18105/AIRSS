# main_v2.py — AIRSS Drone System

import os
import csv
import math
import threading
import time
import cv2
from collections import deque
from datetime import datetime

import config
from detector import SurvivorDetector
from alert import trigger_alert
from gps_mapper import GPSMapper
from dashboard import run_dashboard
from shared_state import state
from wifi_scanner import scanner as wifi_scanner
from captive_portal import dns_server


# ══════════════════════════════════════════════════════
# Stream Reader
# ══════════════════════════════════════════════════════

class StreamReader:
    def __init__(self, source, max_retries: int = 5, retry_delay: float = 2.0):
        self._source      = source
        self._max_retries = max_retries
        self._retry_delay = retry_delay
        self._cap         = None
        self._frame       = None
        self._running     = False
        self._lock        = threading.Lock()
        self._thread      = None

    def start(self) -> bool:
        for attempt in range(1, self._max_retries + 1):
            print(f"[Stream] Connecting... (Attempt {attempt}/{self._max_retries})")
            src = 0 if self._source == "0" else self._source
            cap = cv2.VideoCapture(src)
            if cap.isOpened():
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)   # keep buffer at 1 frame
                self._cap     = cap
                self._running = True
                self._thread  = threading.Thread(
                    target=self._update, daemon=True
                )
                self._thread.start()
                print(f"[Stream] ✅ Connected successfully.")
                print(f"[Stream] ✅ Streaming from: {self._source}")
                return True
            cap.release()
            if attempt < self._max_retries:
                time.sleep(self._retry_delay)
        print("[Stream] ❌ Failed to connect after all attempts.")
        return False

    def _update(self):
        while self._running:
            try:
                if self._cap and self._cap.isOpened():
                    ret, frame = self._cap.read()
                    if ret:
                        with self._lock:
                            self._frame = frame   # store reference, not copy
                    else:
                        time.sleep(0.01)
                else:
                    time.sleep(0.05)
            except Exception:
                break

    def read(self):
        with self._lock:
            return self._frame.copy() if self._frame is not None else None

    def is_running(self) -> bool:
        return self._running

    def stop(self):
        self._running = False
        time.sleep(0.2)
        if self._cap:
            try:
                self._cap.release()
            except Exception:
                pass
        print("[Stream] Stream stopped.")


# ══════════════════════════════════════════════════════
# Session Logger  — keeps file OPEN (was open/close per row)
# ══════════════════════════════════════════════════════

class SessionLogger:
    def __init__(self, log_dir: str = "logs"):
        os.makedirs(log_dir, exist_ok=True)
        ts          = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._path  = os.path.join(log_dir, f"mission_{ts}.csv")
        self._lock  = threading.Lock()

        # Open file once and keep it open for the entire session
        self._file   = open(self._path, "w", newline="", buffering=1)
        self._writer = csv.writer(self._file)
        self._writer.writerow([
            "timestamp", "frame", "survivors",
            "confidences", "screenshot", "lat", "lon"
        ])
        print(f"[Logger] 📋 Session log: {self._path}")

    def log(
        self,
        timestamp      : str,
        frame_num      : int,
        survivor_count : int,
        confidences    : list,
        screenshot_path: str,
        lat            : float = None,
        lon            : float = None,
    ):
        with self._lock:
            self._writer.writerow([
                timestamp,
                frame_num,
                survivor_count,
                ";".join(str(round(c, 2)) for c in confidences),
                screenshot_path,
                lat or "",
                lon or "",
            ])
            # buffering=1 means line-buffered — flushes each row automatically

    def close(self):
        with self._lock:
            try:
                self._file.close()
            except Exception:
                pass


# ══════════════════════════════════════════════════════
# FPS Tracker
# ══════════════════════════════════════════════════════

class FPSTracker:
    def __init__(self, window: int = 30):
        self._times = deque(maxlen=window)

    def tick(self):
        self._times.append(time.time())

    def get_fps(self) -> float:
        if len(self._times) < 2:
            return 0.0
        elapsed = self._times[-1] - self._times[0]
        return round((len(self._times) - 1) / elapsed, 1) if elapsed > 0 else 0.0


def draw_fps(frame, fps: float):
    cv2.putText(
        frame, f"FPS: {fps:.1f}", (frame.shape[1] - 110, 25),
        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2, cv2.LINE_AA,
    )
    return frame


# ══════════════════════════════════════════════════════
# Detection Cooldown
# ══════════════════════════════════════════════════════

class DetectionCooldown:
    def __init__(self, time_gap: int = 10, distance_thresh: float = 5.0):
        self.time_gap         = time_gap
        self.distance_thresh  = distance_thresh
        self._last_time       = 0.0
        self._last_lat        = None
        self._last_lon        = None
        self._lock            = threading.Lock()

    def is_new_event(self, lat: float, lon: float) -> bool:
        with self._lock:
            now     = time.time()
            elapsed = now - self._last_time
            if elapsed >= self.time_gap:
                self._update(now, lat, lon)
                return True
            if self._last_lat is not None:
                dist = self._haversine(
                    self._last_lat, self._last_lon, lat, lon
                )
                if dist >= self.distance_thresh:
                    self._update(now, lat, lon)
                    return True
            return False

    def _update(self, now, lat, lon):
        self._last_time = now
        self._last_lat  = lat
        self._last_lon  = lon

    def time_remaining(self) -> float:
        with self._lock:
            return max(0.0, round(
                self.time_gap - (time.time() - self._last_time), 1
            ))

    @staticmethod
    def _haversine(lat1, lon1, lat2, lon2) -> float:
        R    = 6_371_000
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlam = math.radians(lon2 - lon1)
        a = (math.sin(dphi / 2) ** 2
             + math.cos(phi1) * math.cos(phi2)
             * math.sin(dlam / 2) ** 2)
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# ══════════════════════════════════════════════════════
# Detection Loop
# ══════════════════════════════════════════════════════

def detection_loop(stream, detector, mapper, logger):
    fps_tracker = FPSTracker(window=30)
    frame_number = 0
    state.is_active = True

    event_cooldown = DetectionCooldown(
        time_gap        = 10,
        distance_thresh = 5.0,
    )

    print("[Detection] Loop started.")
    print(
        f"[Detection] Cooldown: {event_cooldown.time_gap}s | "
        f"Distance: {event_cooldown.distance_thresh}m"
    )

    try:
        while stream.is_running():
            frame = stream.read()
            if frame is None:
                time.sleep(0.01)
                continue

            frame_number += 1
            fps_tracker.tick()
            fps = fps_tracker.get_fps()

            result = detector.process_frame(frame)

            state.update_frame(draw_fps(result.annotated_frame, fps))
            state.update_count(result.survivor_count)
            state.update_fps(fps)

            if result.was_yolo_run and result.survivor_count > 0:
                lat, lon, address, gps_source = mapper.get_real_gps()

                if event_cooldown.is_new_event(lat, lon):
                    print(
                        f"\n[AIRSS] NEW DETECTION"
                        f" | Frame {frame_number:05d}"
                        f" | Survivors: {result.survivor_count}"
                        f" | GPS: ({lat}, {lon})"
                        f" | Source: {gps_source}"
                        f" | Time: {result.timestamp}"
                    )

                    state.log_event(result.survivor_count)

                    mapper.add_survivor_marker(
                        lat         = lat,
                        lon         = lon,
                        count       = result.survivor_count,
                        screenshot  = result.screenshot_path,
                        timestamp   = result.timestamp,
                        address     = address,
                        source      = gps_source,
                        confidences = result.confidences,
                    )

                    log_entry = {
                        "timestamp"     : result.timestamp,
                        "survivor_count": result.survivor_count,
                        "confidences"   : result.confidences,
                        "screenshot"    : result.screenshot_path,
                        "lat"           : lat,
                        "lon"           : lon,
                        "address"       : address,
                        "gps_source"    : gps_source,
                    }
                    state.add_log_entry(log_entry)
                    state.add_gps_point(lat, lon, log_entry)

                    logger.log(
                        timestamp       = result.timestamp,
                        frame_num       = frame_number,
                        survivor_count  = result.survivor_count,
                        confidences     = result.confidences,
                        screenshot_path = result.screenshot_path,
                        lat             = lat,
                        lon             = lon,
                    )

                    trigger_alert(
                        survivor_count  = result.survivor_count,
                        screenshot_path = result.screenshot_path,
                        lat             = lat,
                        lon             = lon,
                        address         = address,
                        gps_source      = gps_source,
                    )

                else:
                    print(
                        f"[AIRSS] Tracking"
                        f" | Frame {frame_number:05d}"
                        f" | Count: {result.survivor_count}"
                        f" | Cooldown: {event_cooldown.time_remaining()}s"
                    )

            # ── cv2.imshow removed — dashboard shows live feed via MJPEG ──
            # (imshow + waitKey(1) was blocking the loop on every frame)

    except KeyboardInterrupt:
        print("\n[Detection] Stopped by user (Ctrl+C).")

    finally:
        state.is_active = False
        stream.stop()
        logger.close()
        dns_server.stop()
        _on_shutdown()


def _on_shutdown():
    print("\n[AIRSS] Generating mission report...")
    try:
        from report_generator import generate_report
        path = generate_report(output_dir="reports")
        print(f"[AIRSS] Report saved: {path}")
    except Exception as e:
        print(f"[AIRSS] Report error: {e}")

    stats = state.get_stats()
    gps   = state.get_gps_points()
    print()
    print("=" * 55)
    print(" AIRSS - MISSION SESSION SUMMARY")
    print("=" * 55)
    print(f" Mission Start     : {stats.get('mission_start', '-')}")
    print(f" Total Survivors   : {stats.get('total_survivors', 0)}")
    print(f" Detection Events  : {stats.get('total_events', 0)}")
    print(f" GPS Points Logged : {len(gps)}")
    print(f" WiFi Devices Seen : {stats.get('wifi_devices', 0)}")
    print("=" * 55)


# ══════════════════════════════════════════════════════
# Main Entry Point
# ══════════════════════════════════════════════════════

def main():
    print("=" * 55)
    print(" AIRSS - AI-Integrated Rescue & Support System")
    print("=" * 55)
    print(f" Dashboard    -> http://localhost:{config.DASHBOARD_PORT}")
    print(f" Rescue Portal-> http://{config.HOTSPOT_IP}:{config.DASHBOARD_PORT}/rescue")
    print(f" PDF Report   -> http://localhost:{config.DASHBOARD_PORT}/download-report")
    print(f" Hotspot SSID -> AIRSS-RESCUE | Pass: rescue123")
    print(f" Stream URL   -> {config.STREAM_URL}")
    print(f" Frame Skip   -> {config.FRAME_SKIP}  |  Size -> {config.INPUT_WIDTH}x{config.INPUT_HEIGHT}")
    print("=" * 55)
    print(" Run start_hotspot.bat as Admin first!")
    print(" Press Ctrl+C to quit.")
    print("=" * 55)

    stream = StreamReader(config.STREAM_URL)
    if not stream.start():
        print("[AIRSS] Stream failed to connect.")
        print(" -> Webcam   : set STREAM_URL=0 in .env")
        print(" -> IP Webcam: set STREAM_URL=http://[IP]:8080/video")
        return

    detector = SurvivorDetector(
        model_path        = config.MODEL_PATH,
        confidence_thresh = config.CONFIDENCE_THRESHOLD,
        frame_skip        = config.FRAME_SKIP,
        input_width       = config.INPUT_WIDTH,
        input_height      = config.INPUT_HEIGHT,
    )

    mapper = GPSMapper()
    state.set_mapper(mapper)

    logger = SessionLogger(log_dir="logs")

    wifi_scanner.start()
    dns_server.start()

    flask_thread = threading.Thread(
        target = run_dashboard,
        kwargs = {"host": "0.0.0.0", "port": config.DASHBOARD_PORT},
        daemon = True,
    )
    flask_thread.start()
    print(f"[AIRSS] Dashboard -> http://localhost:{config.DASHBOARD_PORT}")

    detection_loop(stream, detector, mapper, logger)


if __name__ == "__main__":
    main()
