# detector.py
import cv2
import os
import time
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Tuple

from ultralytics import YOLO
import config


@dataclass
class DetectionResult:
    survivor_count  : int
    boxes           : List[Tuple[int, int, int, int]]
    confidences     : List[float]
    annotated_frame : object
    screenshot_path : str
    timestamp       : str
    was_yolo_run    : bool


class SurvivorDetector:

    PERSON_CLASS_ID = 0

    def __init__(
        self,
        model_path       : str   = "yolov8n.pt",
        confidence_thresh: float = 0.55,
        frame_skip       : int   = 3,
        screenshot_dir   : str   = None,
        input_width      : int   = 640,
        input_height     : int   = 480,
    ):
        self.confidence_thresh    = confidence_thresh
        self.frame_skip           = frame_skip
        self.input_width          = input_width
        self.input_height         = input_height
        self.screenshot_dir       = screenshot_dir or getattr(config, "SCREENSHOT_DIR", "screenshots")
        self._screenshot_cooldown = getattr(config, "SCREENSHOT_COOLDOWN", 10)

        self._frame_counter        = 0
        self._screenshot_count     = 0
        self._last_results         = []
        self._last_screenshot_time = 0

        # Background thread pool for async screenshot saving
        self._executor = ThreadPoolExecutor(
            max_workers=2, thread_name_prefix="ScreenshotSaver"
        )

        os.makedirs(self.screenshot_dir, exist_ok=True)
        print(f"[Detector] Screenshot folder: '{self.screenshot_dir}/'")

        print(f"[Detector] Loading YOLOv8 model: {model_path} ...")
        self.model = YOLO(model_path)
        self.model.fuse()          # fuse Conv+BN layers → faster CPU inference
        print(f"[Detector] ✅ Model loaded. Confidence threshold: {confidence_thresh}")

    def process_frame(self, frame) -> DetectionResult:
        self._frame_counter += 1
        timestamp    = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        was_yolo_run = False

        frame = cv2.resize(frame, (self.input_width, self.input_height))

        if self._frame_counter % self.frame_skip == 0:
            raw_detections    = self._run_yolo(frame)
            self._last_results = raw_detections
            was_yolo_run       = True
        else:
            raw_detections = self._last_results

        annotated_frame, boxes, confidences = self._draw_annotations(
            frame.copy(), raw_detections
        )
        survivor_count  = len(boxes)
        annotated_frame = self._draw_hud(annotated_frame, survivor_count, timestamp)

        # Screenshot with cooldown — saved ASYNC (never blocks detection loop)
        screenshot_path = ""
        now = time.time()
        if was_yolo_run and survivor_count > 0:
            if (now - self._last_screenshot_time) >= self._screenshot_cooldown:
                screenshot_path            = self._build_screenshot_path()
                self._last_screenshot_time = now
                self._executor.submit(
                    self._write_screenshot, annotated_frame.copy(), screenshot_path
                )

        return DetectionResult(
            survivor_count  = survivor_count,
            boxes           = boxes,
            confidences     = confidences,
            annotated_frame = annotated_frame,
            screenshot_path = screenshot_path,
            timestamp       = timestamp,
            was_yolo_run    = was_yolo_run,
        )

    def _run_yolo(self, frame) -> list:
        detections = []
        results = self.model.predict(
            source  = frame,
            conf    = self.confidence_thresh,
            classes = [self.PERSON_CLASS_ID],
            verbose = False,
        )
        for result in results:
            for box in result.boxes:
                cls_id = int(box.cls[0])
                conf   = float(box.conf[0])
                if cls_id == self.PERSON_CLASS_ID and conf >= self.confidence_thresh:
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    detections.append({"box": (x1, y1, x2, y2), "conf": round(conf, 2)})
        return detections

    def _draw_annotations(self, frame, detections: list):
        boxes, confidences = [], []
        for det in detections:
            x1, y1, x2, y2 = det["box"]
            conf            = det["conf"]
            boxes.append((x1, y1, x2, y2))
            confidences.append(conf)

            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

            label = f"Person {conf:.2f}"
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 1)
            label_y = max(y1 - 5, th + 5)

            cv2.rectangle(
                frame,
                (x1, label_y - th - 4), (x1 + tw + 4, label_y + 2),
                (0, 255, 0), -1,
            )
            cv2.putText(
                frame, label, (x1 + 2, label_y),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 1, cv2.LINE_AA,
            )
        return frame, boxes, confidences

    def _draw_hud(self, frame, survivor_count: int, timestamp: str):
        overlay = frame.copy()
        cv2.rectangle(overlay, (5, 5), (310, 75), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.5, frame, 0.5, 0, frame)

        count_color = (0, 255, 0) if survivor_count == 0 else (0, 80, 255)
        cv2.putText(
            frame, f"Survivors: {survivor_count}", (12, 32),
            cv2.FONT_HERSHEY_SIMPLEX, 0.8, count_color, 2, cv2.LINE_AA,
        )
        cv2.putText(
            frame, timestamp, (12, 60),
            cv2.FONT_HERSHEY_SIMPLEX, 0.48, (200, 200, 200), 1, cv2.LINE_AA,
        )
        return frame

    def _build_screenshot_path(self) -> str:
        self._screenshot_count += 1
        ts       = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"survivor_{self._screenshot_count:03d}_{ts}.jpg"
        return os.path.join(self.screenshot_dir, filename)

    def _write_screenshot(self, frame, path: str):
        """Runs in background thread — never blocks detection loop."""
        success = cv2.imwrite(path, frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        if success:
            print(f"[Detector] 📸 Screenshot saved: {path}")
        else:
            print(f"[Detector] ⚠️ Failed to save: {path}")

    def reset_counter(self):
        self._frame_counter    = 0
        self._screenshot_count = 0
        self._last_results     = []
        self._last_screenshot_time = 0
        print("[Detector] Counters reset.")

    def get_stats(self) -> dict:
        return {
            "frames_processed" : self._frame_counter,
            "screenshots_saved": self._screenshot_count,
            "model"            : "YOLOv8n",
            "confidence_thresh": self.confidence_thresh,
            "frame_skip"       : self.frame_skip,
        }
