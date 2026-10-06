# ============================================================
# STUDENT360 - LIVE AI SURVEILLANCE ENGINE
# Final behavior pipeline: YOLO + ByteTrack + conservative temporal voting
# ============================================================

from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from typing import Any

import os
import sys
import cv2
import time
import joblib
import numpy as np
import pandas as pd
import uuid
import threading
import shutil
import subprocess
from datetime import datetime
from collections import deque

from ultralytics import YOLO
from mtcnn import MTCNN
from keras_facenet import FaceNet
import torch

# ============================================================
# HARDWARE ACCELERATION (INTEL CPU / NVIDIA RTX GPU)
# ============================================================
CUDA_AVAILABLE = torch.cuda.is_available()
if CUDA_AVAILABLE:
    YOLO_DEVICE = 0
    YOLO_HALF = True
    print(f"🚀 [CUDA ACCELERATION] PyTorch GPU detected: {torch.cuda.get_device_name(0)}")
    print("⚡ Offloading YOLO models to NVIDIA RTX GPU with FP16 half-precision (device=0, half=True)")
else:
    YOLO_DEVICE = "cpu"
    YOLO_HALF = False
    print("⚠️ [CPU FALLBACK] CUDA unavailable. Running on Intel CPU.")

from database import (
    attendance_collection,
    behavior_collection,
    evidence_collection,
    sessions_collection,
)

# behavior_engine.py is used for canonical names/priority/thresholds when available.
try:
    from .behavior_engine import canonical_behavior, behavior_priority, BEHAVIOR_THRESHOLDS
except Exception:
    def canonical_behavior(label):
        value = str(label).strip().lower().replace(" ", "_").replace("-", "_")
        aliases = {
            "sleep": "sleeping",
            "phone": "phone_use",
            "using_phone": "phone_use",
            "cell_phone": "phone_use",
            "cellphone": "phone_use",
            "phoneusage": "phone_use",
            "normal": "attentive",
            "notattentive": "not_attentive",
        }
        return aliases.get(value, value)

    def behavior_priority(label):
        value = canonical_behavior(label)
        return {
            "cheating": 100,
            "malpractice": 100,
            "sleeping": 90,
            "phone_use": 80,
            "not_attentive": 70,
            "attentive": 10,
            "person": 0,
        }.get(value, 20)

    BEHAVIOR_THRESHOLDS = {}

router = APIRouter()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
SESSION_LOGS_FOLDER = os.path.join(UPLOAD_FOLDER, "session_logs")
EVIDENCE_FOLDER = os.path.join(UPLOAD_FOLDER, "evidence")
ATTENDANCE_FOLDER = os.path.join(BASE_DIR, "attendance")
MODELS_DIR = os.path.join(BASE_DIR, "models")
AI_ENGINE_MODELS_DIR = os.path.abspath(os.path.join(BASE_DIR, "../ai_engine/models"))

for folder in [UPLOAD_FOLDER, SESSION_LOGS_FOLDER, EVIDENCE_FOLDER, ATTENDANCE_FOLDER]:
    os.makedirs(folder, exist_ok=True)

# -------------------------
# Face recognition settings
# -------------------------
FACE_RECOGNITION_INTERVAL = 12
FACE_DETECTION_CONFIDENCE = 0.80
FACE_RECOGNITION_THRESHOLD = 0.55
FACE_CONFIDENCE_MARGIN = 0.05
FACE_CACHE_SECONDS = 5.0

# -------------------------
# Person detection settings
# -------------------------
MIN_PERSON_WIDTH = 60
MIN_PERSON_HEIGHT = 100
PERSON_DETECTION_CONFIDENCE = 0.35
PERSON_DETECTION_INTERVAL = 3
OBJECT_DETECTION_INTERVAL = 3
OBJECT_PHONE_CONFIDENCE = 0.28
OBJECT_PHONE_HOLD_SECONDS = 1.00

# -------------------------
# Behavior settings
# -------------------------
# IMPORTANT: Keep the model confidence gate at 0.50. Temporal voting, not
# a lower confidence threshold, provides robustness for this student-level model.
BEHAVIOR_RAW_CONFIDENCE = 0.30
PHONE_RAW_CONFIDENCE = 0.25
SLEEPING_RAW_CONFIDENCE = 0.35
CHEATING_RAW_CONFIDENCE = 0.35

# Temporal filtering prevents one bad frame from becoming an alert.
# A behavior must have repeated evidence inside a short time window.
# These are intentionally not simple consecutive-frame counters because
# small phones can disappear for a frame or two while the student moves.
PHONE_CONFIRM_FRAMES = 2
SLEEPING_CONFIRM_FRAMES = 6
CHEATING_CONFIRM_FRAMES = 4
NOT_ATTENTIVE_CONFIRM_FRAMES = 5
ATTENTIVE_CONFIRM_FRAMES = 3

PHONE_EVIDENCE_WINDOW = 2.00
SLEEPING_EVIDENCE_WINDOW = 1.60
CHEATING_EVIDENCE_WINDOW = 1.20
NOT_ATTENTIVE_EVIDENCE_WINDOW = 1.20

PHONE_MIN_AVERAGE_CONFIDENCE = 0.30
SLEEPING_MIN_AVERAGE_CONFIDENCE = 0.52
CHEATING_MIN_AVERAGE_CONFIDENCE = 0.50
NOT_ATTENTIVE_MIN_AVERAGE_CONFIDENCE = 0.48

# Once an alert is confirmed, do not immediately switch to attentive when
# one frame is missed. But also do not hold an alert for too long.
ALERT_HOLD_SECONDS = 1.20

# Phone boxes are small and may be held slightly outside the person box.
# Keep this lower than the previous 450 px so random nearby detections are
# not assigned to the wrong student.
PHONE_ASSOCIATION_MAX_DISTANCE = 240
PHONE_FACE_FALLBACK_MAX_DISTANCE = 360.0
PHONE_IMMEDIATE_CONFIDENCE = 0.45
BEHAVIOR_ASSOCIATION_MAX_DISTANCE = 300

# Run a second behavior inference on each recognized student's crop.
# This improves small-phone recall without changing face recognition.
PERSON_CROP_BEHAVIOR_ENABLED = False
PERSON_CROP_BEHAVIOR_CONFIDENCE = 0.20
# Only run the expensive student-crop pass when the full-frame pass did not
# already find a usable phone. This keeps phone detection responsive.
PERSON_CROP_ONLY_IF_NO_PHONE = True

# Debug boxes can be enabled if needed.
DRAW_FACE_DEBUG_BOX = False
DRAW_BEHAVIOR_DEBUG_BOXES = False

# Print raw phone detections at most once per second.
PHONE_DEBUG_INTERVAL = 0.35


# ============================================================
# NON-BLOCKING THREADED CAMERA FEED
# ============================================================

class ThreadedCamera:
    """
    High-Performance Non-Blocking Threaded Camera Feed.
    - Captures in a background daemon thread to drop stale frames and eliminate latency.
    - Utilizes cv2.CAP_DSHOW on Windows for instantaneous camera initialization.
    - Caps capture resolution to 640x480 (or 1280x720) @ 30 FPS.
    - Thread-safe frame reading and clean resource release.
    """
    def __init__(self, src=0, width=640, height=480, fps=30):
        self.src = src
        self.width = int(width)
        self.height = int(height)
        self.fps = int(fps)
        self.is_camera = isinstance(src, int) or (isinstance(src, str) and src.isdigit())
        self.stopped = False
        self.lock = threading.Lock()
        self.latest_frame = None
        self.grabbed = False
        self.cap = None
        self.thread = None

        self._init_source()

    def _init_source(self):
        if self.is_camera:
            cam_idx = int(self.src)
            try:
                self.cap = cv2.VideoCapture(cam_idx, cv2.CAP_DSHOW)
                if not self.cap or not self.cap.isOpened():
                    if self.cap:
                        self.cap.release()
                    self.cap = cv2.VideoCapture(cam_idx)
            except Exception:
                self.cap = cv2.VideoCapture(cam_idx)
        else:
            self.cap = cv2.VideoCapture(self.src)

        if self.cap is not None and self.cap.isOpened():
            try:
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
                self.cap.set(cv2.CAP_PROP_FPS, self.fps)
                self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            except Exception:
                pass

            ret, frame = self.cap.read()
            if ret and frame is not None:
                self.latest_frame = frame
                self.grabbed = True

    def start(self):
        if self.cap is not None and self.cap.isOpened():
            self.stopped = False
            self.thread = threading.Thread(target=self._capture_worker, daemon=True)
            self.thread.start()
        return self

    def _capture_worker(self):
        while not self.stopped:
            if self.cap is None or not self.cap.isOpened():
                break

            ret, frame = self.cap.read()
            if not ret or frame is None:
                if not self.is_camera:
                    with self.lock:
                        self.grabbed = False
                    break
                time.sleep(0.005)
                continue

            with self.lock:
                self.latest_frame = frame
                self.grabbed = True

            if not self.is_camera:
                time.sleep(1.0 / max(1, self.fps))

    def read(self):
        with self.lock:
            if not self.grabbed or self.latest_frame is None:
                return False, None
            return True, self.latest_frame.copy()

    def isOpened(self):
        return self.cap is not None and self.cap.isOpened() and not self.stopped

    def release(self):
        self.stopped = True
        if self.thread is not None and self.thread.is_alive():
            self.thread.join(timeout=0.6)
            self.thread = None
        if self.cap is not None:
            try:
                self.cap.release()
            except Exception:
                pass
            self.cap = None
        with self.lock:
            self.grabbed = False
            self.latest_frame = None


def resolve_model_file(filename):
    paths = [
        os.path.join(MODELS_DIR, filename),
        os.path.join(AI_ENGINE_MODELS_DIR, filename),
    ]
    for path in paths:
        if os.path.exists(path):
            return path
    return filename


print("Loading Student360 AI Recognition Engine...")
try:
    detector = MTCNN()
    embedder = FaceNet()
    face_svm = joblib.load(resolve_model_file("face_model.pkl"))
    label_encoder = joblib.load(resolve_model_file("label_encoder.pkl"))
    print("FaceNet and SVM loaded successfully.")
    try:
        print("Known face classes:", [str(x) for x in label_encoder.classes_])
    except Exception:
        pass
except Exception as e:
    print("FACE RECOGNITION ERROR:", repr(e))
    detector = None
    embedder = None
    face_svm = None
    label_encoder = None


active_ai_session: dict[str, Any] = {
    "is_running": False,
    "mode": None,
    "cap": None,
    "student_stats": {},
    "tracker_to_student_map": {},
    "recognized_faces": [],
    "person_detections": [],
    "session_id": None,
    "started_at": None,
    "frame_counter": 0,
    "behavior_states": {},
    "object_detections": [],
    "last_object_detection_time": 0.0,
}

camera_lock = threading.Lock()
_yolo_cache = {}
_person_detector = None


# ============================================================
# BEHAVIOR NORMALIZATION / THRESHOLD HELPERS
# ============================================================

def normalize_behavior(label):
    try:
        value = canonical_behavior(label)
    except Exception:
        value = str(label).strip().lower().replace(" ", "_").replace("-", "_")

    aliases = {
        "sleep": "sleeping",
        "phone": "phone_use",
        "using_phone": "phone_use",
        "cell_phone": "phone_use",
        "cellphone": "phone_use",
        "phoneusage": "phone_use",
        "normal": "attentive",
        "notattentive": "not_attentive",
    }
    value = value.strip().lower().replace(" ", "_").replace("-", "_")
    return aliases.get(value, value)


def live_behavior_priority(label):
    """Priority used only for live per-frame arbitration."""
    name = normalize_behavior(label)
    return {
        "cheating": 100,
        "malpractice": 100,
        "phone_use": 95,
        "sleeping": 90,
        "not_attentive": 70,
        "attentive": 10,
        "person": 0,
    }.get(name, 20)


def behavior_is_alert(label):
    return normalize_behavior(label) in {
        "cheating", "malpractice", "sleeping", "phone_use", "not_attentive"
    }


def safe_behavior_threshold(label):
    """Read BEHAVIOR_THRESHOLDS without assuming a particular dictionary shape."""
    name = normalize_behavior(label)
    try:
        value = BEHAVIOR_THRESHOLDS.get(name, None)
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, dict):
            for key in ("confidence", "min_confidence", "threshold", "min_score"):
                if key in value and isinstance(value[key], (int, float)):
                    return float(value[key])
    except Exception:
        pass

    # Conservative defaults. Phone is intentionally more recall-friendly.
    if name == "phone_use":
        return 0.20
    if name == "sleeping":
        return 0.35
    if name in {"cheating", "malpractice"}:
        return 0.30
    if name == "not_attentive":
        return 0.30
    return 0.20


def minimum_raw_confidence(label):
    name = normalize_behavior(label)
    if name == "phone_use":
        return PHONE_RAW_CONFIDENCE
    if name == "sleeping":
        return SLEEPING_RAW_CONFIDENCE
    if name in {"cheating", "malpractice"}:
        return CHEATING_RAW_CONFIDENCE
    return BEHAVIOR_RAW_CONFIDENCE


def effective_behavior_confidence(label, confidence):
    name = normalize_behavior(label)
    conf = float(confidence)
    return conf >= max(minimum_raw_confidence(name), safe_behavior_threshold(name))


# ============================================================
# TEMPORAL BEHAVIOR STABILIZER
# ============================================================

class LiveBehaviorStabilizer:
    """Conservative per-student/per-ByteTrack behavior state machine.

    The trained behavior model returns student-sized boxes. ByteTrack therefore
    identifies the same student across frames, while this class decides when a
    class change is strong enough to become the displayed behavior.

    Important rules:
      * track_id=None is never used as temporal confirmation evidence.
      * phone_use needs repeated same-track evidence, not one weak frame.
      * attentive must be sustained before replacing a confirmed alert.
      * a confirmed phone state cannot be defeated by one attentive frame.
      * when the model stops producing an alert, the alert is held only briefly.
    """

    def __init__(self):
        self.states = {}

    def reset(self):
        self.states.clear()

    def _new_state(self):
        return {
            "current": "attentive",
            "current_confidence": 1.0,
            "track_id": None,
            "evidence": deque(maxlen=60),
            "last_observation": 0.0,
            "last_alert_observation": 0.0,
        }

    def _settings(self, label):
        name = normalize_behavior(label)
        if name == "phone_use":
            return PHONE_CONFIRM_FRAMES, PHONE_EVIDENCE_WINDOW, PHONE_MIN_AVERAGE_CONFIDENCE
        if name == "sleeping":
            return SLEEPING_CONFIRM_FRAMES, SLEEPING_EVIDENCE_WINDOW, SLEEPING_MIN_AVERAGE_CONFIDENCE
        if name in {"cheating", "malpractice"}:
            return CHEATING_CONFIRM_FRAMES, CHEATING_EVIDENCE_WINDOW, CHEATING_MIN_AVERAGE_CONFIDENCE
        if name == "not_attentive":
            return NOT_ATTENTIVE_CONFIRM_FRAMES, NOT_ATTENTIVE_EVIDENCE_WINDOW, NOT_ATTENTIVE_MIN_AVERAGE_CONFIDENCE
        return ATTENTIVE_CONFIRM_FRAMES, 0.80, 0.70

    def _samples(self, state, label, now, window):
        name = normalize_behavior(label)
        return [
            item for item in state["evidence"]
            if item["label"] == name and now - item["time"] <= window
        ]

    @staticmethod
    def _average(samples):
        if not samples:
            return 0.0
        return sum(float(item["confidence"]) for item in samples) / len(samples)

    def _confirmed(self, state, label, now):
        name = normalize_behavior(label)
        required, window, minimum_average = self._settings(name)
        samples = self._samples(state, name, now, window)
        average = self._average(samples)

        if name == "phone_use":
            # Strong phone evidence may confirm slightly faster, but weak
            # 0.50-ish predictions must accumulate instead of firing alone.
            strong = [s for s in samples if s["confidence"] >= PHONE_IMMEDIATE_CONFIDENCE]
            confirmed = (
                (len(samples) >= required and average >= minimum_average)
                or (len(strong) >= 1)
            )
        else:
            confirmed = len(samples) >= required and average >= minimum_average

        return confirmed, average, len(samples)

    def update(self, student_id, candidate_label, candidate_confidence, now, track_id=None):
        student_id = str(student_id)
        candidate = normalize_behavior(candidate_label)
        confidence = float(candidate_confidence or 0.0)
        try:
            track = int(track_id) if track_id is not None else None
        except Exception:
            track = None

        state = self.states.setdefault(student_id, self._new_state())

        # The state is keyed by verified student_id, so a behavior-detector
        # track-ID change must not erase valid temporal evidence. Track IDs
        # are kept only as debugging metadata.
        if track is not None:
            state["track_id"] = track

        # Behavior state is keyed by the recognized student_id.
        # Do NOT require a behavior-box ByteTrack ID here. Small/short-lived
        # phone detections often have box.id=None, and crop detections are
        # intentionally student-specific but do not have a ByteTrack ID.
        # Spatial association has already tied this observation to a student.
        if candidate not in {"person", "human", "student"}:
            if candidate == "attentive":
                if confidence >= 0.50:
                    state["evidence"].append({
                        "label": "attentive",
                        "confidence": confidence,
                        "time": now,
                    })
            elif effective_behavior_confidence(candidate, confidence):
                state["evidence"].append({
                    "label": candidate,
                    "confidence": confidence,
                    "time": now,
                })
                state["last_alert_observation"] = now

        state["last_observation"] = now

        # Keep only recent evidence. One second is enough for live temporal
        # voting without allowing an old behavior to poison a later action.
        while state["evidence"] and now - state["evidence"][0]["time"] > 1.50:
            state["evidence"].popleft()

        current = state["current"]

        # --------------------------------------------------------------
        # If an alert is active, require a real replacement signal.
        # --------------------------------------------------------------
        if current != "attentive":
            attentive_samples = self._samples(state, "attentive", now, 0.80)
            attentive_avg = self._average(attentive_samples)
            attentive_confirmed = (
                len(attentive_samples) >= ATTENTIVE_CONFIRM_FRAMES
                and attentive_avg >= 0.70
            )

            if attentive_confirmed:
                state["current"] = "attentive"
                state["current_confidence"] = attentive_avg
                return state["current"], state["current_confidence"]

            # A different alert can replace the current one only after its own
            # confirmation. This prevents class flicker from raw predictions.
            confirmed_alerts = []
            for label in {item["label"] for item in state["evidence"]}:
                if label == "attentive":
                    continue
                confirmed, average, count = self._confirmed(state, label, now)
                if confirmed:
                    confirmed_alerts.append((label, average, count, behavior_priority(label)))

            if confirmed_alerts:
                # Phone takes precedence among confirmed alerts, then priority.
                phone = [x for x in confirmed_alerts if x[0] == "phone_use"]
                winner = max(phone or confirmed_alerts, key=lambda x: (x[1], x[2], x[3]))
                state["current"] = winner[0]
                state["current_confidence"] = winner[1]
                return state["current"], state["current_confidence"]

            if now - state["last_alert_observation"] <= ALERT_HOLD_SECONDS:
                return current, state["current_confidence"]

            state["current"] = "attentive"
            state["current_confidence"] = 1.0
            return "attentive", 1.0

        # --------------------------------------------------------------
        # Current state is attentive. An alert must earn its way in.
        # --------------------------------------------------------------
        confirmed_alerts = []
        for label in {item["label"] for item in state["evidence"]}:
            if label == "attentive":
                continue
            confirmed, average, count = self._confirmed(state, label, now)
            if confirmed:
                confirmed_alerts.append((label, average, count, behavior_priority(label)))

        if confirmed_alerts:
            phone = [x for x in confirmed_alerts if x[0] == "phone_use"]
            winner = max(phone or confirmed_alerts, key=lambda x: (x[1], x[2], x[3]))
            state["current"] = winner[0]
            state["current_confidence"] = winner[1]
            return state["current"], state["current_confidence"]

        # Stay attentive. The displayed confidence is not treated as model
        # accuracy, so 1.0 here simply means "no alert confirmed".
        state["current"] = "attentive"
        state["current_confidence"] = 1.0
        return "attentive", 1.0


behavior_stabilizer = LiveBehaviorStabilizer()


# ============================================================
# MODEL LOADING
# ============================================================

def get_yolo_model(mode):
    target = "classroom_model.pt" if mode == "classroom" else "exam_model.pt"
    model_path = resolve_model_file(target)

    if os.path.exists(model_path):
        if model_path not in _yolo_cache:
            print("Loading custom YOLO behavior model:", model_path)
            model = YOLO(model_path)
            if CUDA_AVAILABLE:
                try:
                    model.to(YOLO_DEVICE)
                    print(f"✅ YOLO behavior model offloaded to GPU device={YOLO_DEVICE}")
                except Exception as e:
                    print("YOLO CUDA transfer note:", e)
            _yolo_cache[model_path] = model
            try:
                print("BEHAVIOR MODEL CLASSES:", _yolo_cache[model_path].names)
            except Exception:
                pass
        return _yolo_cache[model_path]

    fallback_key = "yolov8n.pt"
    if fallback_key not in _yolo_cache:
        print("Custom behavior model not found. Using YOLOv8n fallback.")
        model = YOLO(fallback_key)
        if CUDA_AVAILABLE:
            try:
                model.to(YOLO_DEVICE)
                print(f"✅ Fallback YOLO model offloaded to GPU device={YOLO_DEVICE}")
            except Exception as e:
                print("YOLO CUDA transfer note:", e)
        _yolo_cache[fallback_key] = model
        try:
            print("FALLBACK MODEL CLASSES:", _yolo_cache[fallback_key].names)
        except Exception:
            pass
    return _yolo_cache[fallback_key]



def get_phone_model(mode):
    """
    Classroom mode needs a dedicated phone-capable model.

    According to the Student360 thesis, the classroom model is primarily
    attentive/sleeping/distracted, while the exam model includes Phone Use.
    Therefore classroom mode fuses:
        classroom_model.pt -> classroom state
        exam_model.pt      -> phone_use evidence only
    In exam mode the active exam model is already phone-capable.
    """
    if mode == "exam":
        return get_yolo_model("exam")

    phone_path = resolve_model_file("exam_model.pt")
    if os.path.exists(phone_path):
        if phone_path not in _yolo_cache:
            print("Loading dedicated phone-capable model:", phone_path)
            model = YOLO(phone_path)
            if CUDA_AVAILABLE:
                try:
                    model.to(YOLO_DEVICE)
                    print(f"✅ Dedicated phone model offloaded to GPU device={YOLO_DEVICE}")
                except Exception as e:
                    print("Phone model CUDA transfer note:", e)
            _yolo_cache[phone_path] = model
            try:
                print("PHONE MODEL CLASSES:", _yolo_cache[phone_path].names)
            except Exception:
                pass
        return _yolo_cache[phone_path]

    print("WARNING: exam_model.pt not found; phone fusion disabled.")
    return None


def detect_phone_evidence(frame, phone_yolo, students):
    """
    Run a recall-oriented phone pass and keep ONLY phone_use detections.
    It uses both full-frame inference and recognized-student crops.
    Temporal confirmation later removes one-frame false alarms.
    """
    if phone_yolo is None:
        return []

    frame_h, frame_w = frame.shape[:2]
    detections = []

    # Full-frame phone evidence.
    try:
        results = phone_yolo.predict(
            frame,
            conf=PHONE_RAW_CONFIDENCE,
            imgsz=960,
            iou=0.45,
            device=YOLO_DEVICE,
            half=YOLO_HALF,
            verbose=False,
        )
        for result in results:
            if result.boxes is None:
                continue
            for box in result.boxes:
                try:
                    cls_id = int(box.cls[0])
                    names = phone_yolo.names
                    label = names[cls_id] if cls_id in names else ""
                    canonical = normalize_behavior(label)
                    if canonical != "phone_use":
                        continue

                    confidence = float(box.conf[0]) if box.conf is not None else 0.0
                    if confidence < PHONE_RAW_CONFIDENCE:
                        continue

                    mapped = clamp_box(
                        box.xyxy[0].tolist(),
                        frame_w,
                        frame_h,
                    )
                    if mapped is None:
                        continue

                    detections.append({
                        "box": mapped,
                        "label": "phone_use",
                        "confidence": confidence,
                        "track_id": None,
                        "source": "phone_model_full_frame",
                    })
                except Exception:
                    continue
    except Exception as e:
        print("PHONE MODEL FULL-FRAME ERROR:", repr(e))

    # Student-crop phone evidence. This is the most important pass for a
    # small phone in a 640x480 webcam frame.
    for student in students:
        crop_box = expand_box(
            student["person_box"],
            frame_w,
            frame_h,
            left=0.12,
            right=0.12,
            top=0.05,
            bottom=0.15,
        )
        if crop_box is None:
            continue

        x1, y1, x2, y2 = crop_box
        crop = frame[y1:y2, x1:x2]
        if crop.size == 0 or crop.shape[0] < 80 or crop.shape[1] < 50:
            continue

        try:
            results = phone_yolo.predict(
                crop,
                conf=0.20,
                imgsz=640,
                iou=0.45,
                device=YOLO_DEVICE,
                half=YOLO_HALF,
                verbose=False,
            )
        except Exception as e:
            print("PHONE MODEL CROP ERROR:", repr(e))
            continue

        for result in results:
            if result.boxes is None:
                continue
            for box in result.boxes:
                try:
                    cls_id = int(box.cls[0])
                    names = phone_yolo.names
                    label = names[cls_id] if cls_id in names else ""
                    canonical = normalize_behavior(label)
                    if canonical != "phone_use":
                        continue

                    confidence = float(box.conf[0]) if box.conf is not None else 0.0
                    if confidence < 0.20:
                        continue

                    bx1, by1, bx2, by2 = box.xyxy[0].tolist()
                    mapped = clamp_box(
                        (x1 + bx1, y1 + by1, x1 + bx2, y1 + by2),
                        frame_w,
                        frame_h,
                    )
                    if mapped is None:
                        continue

                    detections.append({
                        "box": mapped,
                        "label": "phone_use",
                        "confidence": confidence,
                        "track_id": None,
                        "student_hint": student["student_id"],
                        "source": "phone_model_student_crop",
                    })
                except Exception:
                    continue

    return detections


def get_person_detector():
    global _person_detector
    if _person_detector is not None:
        return _person_detector

    try:
        person_model_path = resolve_model_file("yolov8n.pt")
        if os.path.exists(person_model_path):
            print("Loading dedicated person detector:", person_model_path)
            _person_detector = YOLO(person_model_path)
        else:
            print("Loading dedicated YOLOv8n person detector...")
            _person_detector = YOLO("yolov8n.pt")
        if CUDA_AVAILABLE:
            try:
                _person_detector.to(YOLO_DEVICE)
                print(f"✅ Person detector offloaded to GPU device={YOLO_DEVICE}")
            except Exception as e:
                print("Person detector CUDA transfer note:", e)
        return _person_detector
    except Exception as e:
        print("PERSON DETECTOR LOAD ERROR:", repr(e))
        return None


# ============================================================
# GEOMETRY HELPERS
# ============================================================

def clamp_box(box, frame_width, frame_height):
    if box is None:
        return None
    try:
        x1, y1, x2, y2 = [int(v) for v in box]
    except Exception:
        return None
    x1 = max(0, min(frame_width - 1, x1))
    y1 = max(0, min(frame_height - 1, y1))
    x2 = max(0, min(frame_width, x2))
    y2 = max(0, min(frame_height, y2))
    if x2 <= x1 or y2 <= y1:
        return None
    return (x1, y1, x2, y2)


def clamp_face_box(box, frame_width, frame_height):
    if box is None:
        return None
    try:
        x, y, w, h = [int(v) for v in box]
    except Exception:
        return None
    if w <= 0 or h <= 0:
        return None
    return clamp_box((x, y, x + w, y + h), frame_width, frame_height)


def box_center(box):
    x1, y1, x2, y2 = box
    return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)


def box_area(box):
    x1, y1, x2, y2 = box
    return max(0, x2 - x1) * max(0, y2 - y1)


def point_inside_box(point, box):
    px, py = point
    x1, y1, x2, y2 = box
    return x1 <= px <= x2 and y1 <= py <= y2


def calculate_iou(box_a, box_b):
    ax1, ay1, ax2, ay2 = box_a
    bx1, by1, bx2, by2 = box_b
    ix1 = max(ax1, bx1)
    iy1 = max(ay1, by1)
    ix2 = min(ax2, bx2)
    iy2 = min(ay2, by2)
    iw = max(0, ix2 - ix1)
    ih = max(0, iy2 - iy1)
    intersection = iw * ih
    union = box_area(box_a) + box_area(box_b) - intersection
    if union <= 0:
        return 0.0
    return intersection / union


def expand_box(box, frame_width, frame_height, left=0.0, right=0.0, top=0.0, bottom=0.0):
    x1, y1, x2, y2 = box
    width = x2 - x1
    height = y2 - y1
    expanded = (
        int(x1 - width * left),
        int(y1 - height * top),
        int(x2 + width * right),
        int(y2 + height * bottom),
    )
    return clamp_box(expanded, frame_width, frame_height)


# ============================================================
# STUDENT STATISTICS / EVIDENCE
# ============================================================

def initialize_student_stats(student_id, timestamp):
    stats = active_ai_session["student_stats"]
    if student_id not in stats:
        stats[student_id] = {
            "Date": timestamp.strftime("%Y-%m-%d"),
            "Arrival_Time": timestamp.strftime("%H:%M:%S"),
            "cheating_sec": 0.0,
            "non_cheating_sec": 0.0,
            "attentive_sec": 0.0,
            "sleeping_sec": 0.0,
            "phone_use_sec": 0.0,
            "not_attentive_sec": 0.0,
            "last_seen_time": time.time(),
            "last_evidence_time": 0.0,
        }
        print("NEW STUDENT DETECTED:", student_id)
    return stats[student_id]


def update_student_statistics(student_id, behavior_label, current_time, timestamp):
    stats = initialize_student_stats(student_id, timestamp)
    elapsed = max(0.0, min(current_time - stats["last_seen_time"], 1.0))
    stats["last_seen_time"] = current_time
    label = normalize_behavior(behavior_label)

    if label in {"cheating", "malpractice"}:
        stats["cheating_sec"] += elapsed
        stats["not_attentive_sec"] += elapsed
    elif label == "sleeping":
        stats["sleeping_sec"] += elapsed
        stats["not_attentive_sec"] += elapsed
    elif label == "phone_use":
        stats["phone_use_sec"] += elapsed
        stats["not_attentive_sec"] += elapsed
    elif label in {"attentive", "person"}:
        stats["attentive_sec"] += elapsed
    else:
        stats["non_cheating_sec"] += elapsed

    return stats


def save_evidence(student_id, behavior_label, frame):
    if student_id not in active_ai_session["student_stats"]:
        return

    stats = active_ai_session["student_stats"][student_id]
    current_time = time.time()
    if current_time - stats["last_evidence_time"] < 15:
        return

    timestamp = datetime.now()
    filename = (
        f"{student_id}_{normalize_behavior(behavior_label)}_"
        f"{timestamp.strftime('%Y%m%d_%H%M%S_%f')}.jpg"
    )
    evidence_path = os.path.join(EVIDENCE_FOLDER, filename)

    try:
        if not cv2.imwrite(evidence_path, frame):
            raise IOError("Failed to write evidence image")

        evidence_record = {
            "student_id": str(student_id),
            "behavior": normalize_behavior(behavior_label),
            "image": filename,
            "image_path": f"evidence/{filename}",
            "date": timestamp,
            "session_id": active_ai_session["session_id"],
            "mode": active_ai_session["mode"],
            "source": "live_surveillance",
        }
        result = evidence_collection.insert_one(evidence_record)
        stats["last_evidence_time"] = current_time
        print("EVIDENCE SAVED:", evidence_path)
        print("EVIDENCE MONGODB ID:", result.inserted_id)
    except Exception as e:
        print("EVIDENCE ERROR:", repr(e))


# ============================================================
# FACE RECOGNITION
# ============================================================

def recognize_face(face_image):
    if (
        face_image is None
        or face_image.size == 0
        or detector is None
        or embedder is None
        or face_svm is None
        or label_encoder is None
    ):
        return "Unknown", 0.0

    try:
        rgb_face = cv2.cvtColor(face_image, cv2.COLOR_BGR2RGB)
        resized = cv2.resize(rgb_face, (160, 160), interpolation=cv2.INTER_AREA)
        embedding = embedder.embeddings([resized])
        embedding = np.asarray(embedding, dtype=np.float32)

        if embedding.ndim == 1:
            embedding = np.expand_dims(embedding, axis=0)
        if embedding.ndim != 2 or embedding.shape[1] != 512 or not np.all(np.isfinite(embedding)):
            return "Unknown", 0.0

        probabilities = face_svm.predict_proba(embedding)[0]
        probabilities = np.asarray(probabilities, dtype=float)
        if len(probabilities) == 0:
            return "Unknown", 0.0

        order = np.argsort(probabilities)[::-1]
        best_index = int(order[0])
        best_confidence = float(probabilities[best_index])
        second_confidence = float(probabilities[int(order[1])]) if len(order) > 1 else 0.0
        margin = best_confidence - second_confidence
        predicted_label = str(label_encoder.inverse_transform([best_index])[0])

        if best_confidence >= FACE_RECOGNITION_THRESHOLD and (
            len(order) == 1 or margin >= FACE_CONFIDENCE_MARGIN
        ):
            return predicted_label, best_confidence

        direct_prediction = face_svm.predict(embedding)
        if len(direct_prediction) > 0:
            direct_index = int(direct_prediction[0])
            direct_label = str(label_encoder.inverse_transform([direct_index])[0])
            if best_confidence >= 0.50 and direct_label == predicted_label:
                return direct_label, best_confidence

    except Exception as e:
        print("FACE RECOGNITION ERROR:", repr(e))

    return "Unknown", 0.0


def detect_and_recognize_faces(frame):
    if detector is None:
        return []

    frame_height, frame_width = frame.shape[:2]
    try:
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        detections = detector.detect_faces(rgb)
    except Exception as e:
        print("FULL FRAME FACE DETECTION ERROR:", repr(e))
        return []

    faces = []
    for detection in detections:
        try:
            detection_confidence = float(detection.get("confidence", 0.0))
            if detection_confidence < FACE_DETECTION_CONFIDENCE:
                continue

            face_box = clamp_face_box(detection.get("box"), frame_width, frame_height)
            if face_box is None:
                continue

            x1, y1, x2, y2 = face_box
            if x2 - x1 < 30 or y2 - y1 < 30:
                continue

            face_crop = frame[y1:y2, x1:x2]
            student_id, identity_confidence = recognize_face(face_crop)
            faces.append({
                "box": face_box,
                "center": box_center(face_box),
                "student_id": student_id,
                "confidence": identity_confidence,
                "face_detection_confidence": detection_confidence,
                "area": box_area(face_box),
                "last_seen": time.time(),
            })
        except Exception as e:
            print("FACE PROCESSING ERROR:", repr(e))

    return faces


def update_face_cache(new_faces):
    now = time.time()
    existing = active_ai_session["recognized_faces"]
    valid_existing = [
        face for face in existing
        if face.get("student_id") != "Unknown"
        and now - face.get("last_seen", 0) <= FACE_CACHE_SECONDS
    ]

    by_student = {}
    for face in valid_existing + [f for f in new_faces if f.get("student_id") != "Unknown"]:
        student_id = face["student_id"]
        previous = by_student.get(student_id)
        if previous is None or face["confidence"] >= previous["confidence"]:
            by_student[student_id] = face

    active_ai_session["recognized_faces"] = list(by_student.values())
    return active_ai_session["recognized_faces"]


def get_current_recognized_faces():
    now = time.time()
    valid = [
        face for face in active_ai_session["recognized_faces"]
        if face.get("student_id") != "Unknown"
        and now - face.get("last_seen", 0) <= FACE_CACHE_SECONDS
    ]
    active_ai_session["recognized_faces"] = valid
    return valid


# ============================================================
# PERSON DETECTION
# ============================================================

def detect_persons(frame, behavior_yolo):
    frame_height, frame_width = frame.shape[:2]
    persons = []
    person_model = get_person_detector()

    if person_model is not None:
        try:
            results: Any = person_model(
                frame,
                conf=PERSON_DETECTION_CONFIDENCE,
                classes=[0],
                device=YOLO_DEVICE,
                half=YOLO_HALF,
                verbose=False,
            )
            for result in results:
                boxes = getattr(result, "boxes", None)
                if boxes is None:
                    continue
                for box in boxes:
                    try:
                        person_box = clamp_box(
                            box.xyxy[0].tolist(), frame_width, frame_height
                        )
                        if person_box is None:
                            continue
                        x1, y1, x2, y2 = person_box
                        if x2 - x1 < MIN_PERSON_WIDTH or y2 - y1 < MIN_PERSON_HEIGHT:
                            continue
                        persons.append({
                            "box": person_box,
                            "center": box_center(person_box),
                            "confidence": float(box.conf[0]),
                            "source": "person_model",
                        })
                    except Exception:
                        continue
        except Exception as e:
            print("DEDICATED PERSON DETECTOR ERROR:", repr(e))

    # Fallback only if dedicated person detection returned nothing.
    if not persons:
        try:
            results = behavior_yolo(
                frame,
                conf=0.20,
                device=YOLO_DEVICE,
                half=YOLO_HALF,
                verbose=False,
            )
            names = behavior_yolo.names
            for result in results:
                boxes = result.boxes
                if boxes is None:
                    continue
                for box in boxes:
                    try:
                        cls_id = int(box.cls[0])
                        label = names[cls_id] if cls_id in names else ""
                        normalized = normalize_behavior(label)
                        if normalized not in {"person", "human", "student"}:
                            continue

                        person_box = clamp_box(
                            box.xyxy[0].tolist(), frame_width, frame_height
                        )
                        if person_box is None:
                            continue
                        x1, y1, x2, y2 = person_box
                        if x2 - x1 < MIN_PERSON_WIDTH or y2 - y1 < MIN_PERSON_HEIGHT:
                            continue

                        persons.append({
                            "box": person_box,
                            "center": box_center(person_box),
                            "confidence": float(box.conf[0]),
                            "source": "custom_model",
                        })
                    except Exception:
                        continue
        except Exception as e:
            print("CUSTOM PERSON FALLBACK ERROR:", repr(e))

    persons.sort(key=lambda item: item["confidence"], reverse=True)
    filtered = []
    for candidate in persons:
        duplicate = False
        for kept in filtered:
            if calculate_iou(candidate["box"], kept["box"]) > 0.70:
                duplicate = True
                break
        if not duplicate:
            filtered.append(candidate)

    return filtered



# ============================================================
# PHYSICAL CELL-PHONE DETECTION / ASSOCIATION
# ============================================================

def detect_persons_and_phones(frame):
    """
    One lightweight YOLOv8n pass for both:
      class 0  = person
      class 67 = cell phone

    Returns:
        persons, phones

    This avoids running separate person and phone models.
    """
    frame_height, frame_width = frame.shape[:2]
    persons = []
    phones = []

    model = get_person_detector()
    if model is None:
        return persons, phones

    try:
        results: Any = model(
            frame,
            conf=min(PERSON_DETECTION_CONFIDENCE, OBJECT_PHONE_CONFIDENCE),
            classes=[0, 67],
            imgsz=640,
            device=YOLO_DEVICE,
            half=YOLO_HALF,
            verbose=False,
        )
    except Exception as e:
        print("PERSON/PHONE OBJECT DETECTOR ERROR:", repr(e))
        return persons, phones

    for result in results:
        boxes = getattr(result, "boxes", None)
        if boxes is None:
            continue

        for box in boxes:
            try:
                cls_id = int(box.cls[0])
                confidence = float(box.conf[0]) if box.conf is not None else 0.0

                mapped = clamp_box(
                    box.xyxy[0].tolist(),
                    frame_width,
                    frame_height,
                )
                if mapped is None:
                    continue

                x1, y1, x2, y2 = mapped

                if cls_id == 0:
                    if confidence < PERSON_DETECTION_CONFIDENCE:
                        continue
                    if x2 - x1 < MIN_PERSON_WIDTH or y2 - y1 < MIN_PERSON_HEIGHT:
                        continue

                    persons.append({
                        "box": mapped,
                        "center": box_center(mapped),
                        "confidence": confidence,
                        "source": "yolov8n_person",
                    })

                elif cls_id == 67:
                    if confidence < OBJECT_PHONE_CONFIDENCE:
                        continue

                    phones.append({
                        "box": mapped,
                        "center": box_center(mapped),
                        "confidence": confidence,
                        "source": "yolov8n_cell_phone",
                    })

            except Exception:
                continue

    # Deduplicate person boxes.
    persons.sort(key=lambda item: item["confidence"], reverse=True)
    filtered_persons = []
    for candidate in persons:
        if any(calculate_iou(candidate["box"], kept["box"]) > 0.70 for kept in filtered_persons):
            continue
        filtered_persons.append(candidate)

    # Deduplicate phone boxes.
    phones.sort(key=lambda item: item["confidence"], reverse=True)
    filtered_phones = []
    for candidate in phones:
        if any(calculate_iou(candidate["box"], kept["box"]) > 0.60 for kept in filtered_phones):
            continue
        filtered_phones.append(candidate)

    return filtered_persons, filtered_phones


def assign_physical_phones_to_students(phones, students, frame_shape):
    """
    Associate each physical cell-phone detection with the most plausible
    recognized student.

    Returns:
        {
          student_id: {
              "confidence": ...,
              "box": ...,
              "source": "yolov8n_cell_phone"
          }
        }
    """
    assignments = {}

    if not phones or not students:
        return assignments

    for phone in phones:
        best_student = None
        best_score = float("inf")

        for student in students:
            belongs, score = phone_box_belongs_to_student(
                phone["box"],
                student,
                frame_shape,
            )
            if not belongs:
                continue

            if score < best_score:
                best_score = score
                best_student = student

        if best_student is None:
            continue

        sid = best_student["student_id"]
        previous = assignments.get(sid)

        if previous is None or phone["confidence"] > previous["confidence"]:
            assignments[sid] = {
                "confidence": float(phone["confidence"]),
                "box": phone["box"],
                "source": "yolov8n_cell_phone",
            }

    return assignments


def fuse_final_behaviors(raw_student_behaviors, physical_phone_assignments, students):
    """
    Final per-frame fusion before temporal stabilization.

    Rules:
      1. Physical phone near a student strongly supports phone_use.
      2. If custom classroom YOLO already says phone_use, keep it.
      3. Physical phone evidence prevents sleeping from winning.
      4. Otherwise preserve the classroom-model behavior.

    The returned structure matches assign_behaviors_to_students().
    """
    result = {}

    for student in students:
        sid = student["student_id"]

        raw = raw_student_behaviors.get(
            sid,
            {
                "label": "attentive",
                "box": student["person_box"],
                "priority": live_behavior_priority("attentive"),
                "confidence": 1.0,
                "source": "default",
                "track_id": None,
            },
        )

        physical = physical_phone_assignments.get(sid)

        if physical is not None:
            raw_label = normalize_behavior(raw.get("label", "attentive"))
            raw_conf = float(raw.get("confidence", 0.0))
            object_conf = float(physical["confidence"])

            # Fusion score. A physical phone is strong contextual evidence,
            # while custom phone_use adds additional support.
            fused_conf = object_conf
            if raw_label == "phone_use":
                fused_conf = min(0.99, max(object_conf, raw_conf) + 0.08)

            result[sid] = {
                "label": "phone_use",
                "box": physical["box"],
                "priority": live_behavior_priority("phone_use"),
                "confidence": max(PHONE_RAW_CONFIDENCE, fused_conf),
                "source": (
                    "fused_custom+physical_phone"
                    if raw_label == "phone_use"
                    else "physical_phone_override"
                ),
                "track_id": raw.get("track_id"),
            }
            continue

        # No physical phone. Keep custom model result.
        result[sid] = raw

    return result


# ============================================================
# FACE -> PERSON ASSOCIATION
# ============================================================

def match_faces_to_persons(persons, faces):
    students = []

    for person in persons:
        person_box = person["box"]
        candidates = []

        for face in faces:
            if face.get("student_id") == "Unknown":
                continue
            if point_inside_box(face["center"], person_box):
                candidates.append(face)

        if not candidates:
            continue

        candidates.sort(
            key=lambda f: (f.get("area", 0), f.get("confidence", 0.0)),
            reverse=True,
        )
        face = candidates[0]

        students.append({
            "person_box": person_box,
            "person_confidence": person["confidence"],
            "face_box": face["box"],
            "student_id": face["student_id"],
            "face_confidence": face["confidence"],
            "center": person["center"],
        })

    unique = {}
    for student in students:
        student_id = student["student_id"]
        previous = unique.get(student_id)
        score = student["face_confidence"] + 0.25 * student["person_confidence"]
        if previous is None:
            student["_match_score"] = score
            unique[student_id] = student
        elif score > previous["_match_score"]:
            student["_match_score"] = score
            unique[student_id] = student

    for student in unique.values():
        student.pop("_match_score", None)

    return list(unique.values())


# ============================================================
# BEHAVIOR -> STUDENT ASSOCIATION
# ============================================================

def phone_box_is_reasonable(phone_box, student=None, frame_shape=None):
    """Validate a phone box using the camera frame, not a fragile person-box size.

    The previous implementation compared the phone dimensions to the YOLO person
    box. If the person detector returned a narrow/partial body box, a perfectly
    valid phone could be rejected. Here we use frame-relative limits and a
    plausible phone aspect ratio.
    """
    bx1, by1, bx2, by2 = phone_box
    bw = max(1, bx2 - bx1)
    bh = max(1, by2 - by1)

    if bw < 12 or bh < 12:
        return False

    aspect = bw / float(bh)
    if aspect < 0.25 or aspect > 2.50:
        return False

    if frame_shape is not None:
        frame_h, frame_w = frame_shape[:2]
        if bw > 0.30 * frame_w:
            return False
        if bh > 0.70 * frame_h:
            return False
        if (bw * bh) > 0.18 * frame_w * frame_h:
            return False

    return True


def _distance_from_box(point, box):
    """Euclidean distance from a point to a rectangle, zero when inside."""
    px, py = point
    x1, y1, x2, y2 = box
    dx = max(x1 - px, 0, px - x2)
    dy = max(y1 - py, 0, py - y2)
    return (dx * dx + dy * dy) ** 0.5


def phone_box_belongs_to_student(phone_box, student, frame_shape=None):
    """Associate a phone with the nearest compatible student's body region."""
    if not phone_box_is_reasonable(phone_box, student, frame_shape):
        return False, float("inf")

    phone_center = box_center(phone_box)
    person_box = student["person_box"]

    # Best case: phone center is actually inside the student's person box.
    if point_inside_box(phone_center, person_box):
        overlap = calculate_iou(phone_box, person_box)
        return True, -1000.0 - overlap * 500.0

    # Real classroom footage often has the phone extending outside the body
    # detector's right/left edge because the hand is extended. Measure distance
    # to the body rectangle rather than distance to the person's center.
    boundary_distance = _distance_from_box(phone_center, person_box)
    if boundary_distance <= PHONE_ASSOCIATION_MAX_DISTANCE:
        overlap = calculate_iou(phone_box, person_box)
        return True, boundary_distance - overlap * 300.0

    # Also allow a modest expanded body region.
    if frame_shape is not None:
        frame_h, frame_w = frame_shape[:2]
    else:
        frame_w = max(person_box[2], phone_box[2]) + 1
        frame_h = max(person_box[3], phone_box[3]) + 1

    expanded = expand_box(
        person_box,
        frame_w,
        frame_h,
        left=0.18,
        right=0.18,
        top=0.10,
        bottom=0.22,
    )
    if expanded is not None and point_inside_box(phone_center, expanded):
        return True, 25.0

    return False, float("inf")

def find_best_student_for_behavior(behavior_box, behavior_label, students, student_hint=None):
    """Associate a student-level behavior box with the closest real student.

    All behavior classes, including phone_use, use the same student-level
    geometry because the trained behavior model returns student-sized boxes.
    """
    if not students:
        return None

    if student_hint is not None:
        for student in students:
            if str(student["student_id"]) == str(student_hint):
                return student

    behavior_center = box_center(behavior_box)
    best = None
    best_score = float("inf")

    for student in students:
        person_box = student["person_box"]
        face_box = student["face_box"]
        person_iou = calculate_iou(behavior_box, person_box)
        face_inside = point_inside_box(student["center"], behavior_box)
        face_overlap = calculate_iou(behavior_box, face_box)

        # Require an actual spatial relationship. Do not assign a behavior
        # merely because another student happens to be nearby.
        if person_iou > 0.20 or face_inside or face_overlap > 0.05:
            score = -1000.0 - person_iou * 500.0 - face_overlap * 300.0
        else:
            person_center = student["center"]
            dx = person_center[0] - behavior_center[0]
            dy = person_center[1] - behavior_center[1]
            distance = (dx * dx + dy * dy) ** 0.5
            score = distance

        if score < best_score:
            best_score = score
            best = student

    if best is None:
        return None

    # For non-overlapping boxes, distance must still be reasonable.
    if best_score > BEHAVIOR_ASSOCIATION_MAX_DISTANCE:
        return None
    return best

def detect_behaviors_inside_student_crops(frame, behavior_yolo, students):
    """Second-pass behavior inference on each recognized student's crop.

    The full-frame pass is retained. This crop pass is only an additional
    source of evidence, especially for small phones that are hard to detect
    in a 640x480 full frame.
    """
    if not PERSON_CROP_BEHAVIOR_ENABLED or not students:
        return []

    frame_h, frame_w = frame.shape[:2]
    detections = []

    for student in students:
        crop_box = expand_box(
            student["person_box"],
            frame_w,
            frame_h,
            left=0.08,
            right=0.08,
            top=0.05,
            bottom=0.08,
        )
        if crop_box is None:
            continue

        x1, y1, x2, y2 = crop_box
        crop = frame[y1:y2, x1:x2]
        if crop.size == 0 or crop.shape[0] < 80 or crop.shape[1] < 50:
            continue

        try:
            results = behavior_yolo.predict(
                crop,
                conf=PERSON_CROP_BEHAVIOR_CONFIDENCE,
                imgsz=640,
                iou=0.45,
                device=YOLO_DEVICE,
                half=YOLO_HALF,
                verbose=False,
            )
        except Exception as e:
            print("PERSON CROP BEHAVIOR ERROR:", repr(e))
            continue

        for result in results:
            boxes = result.boxes
            if boxes is None:
                continue

            for box in boxes:
                try:
                    cls_id = int(box.cls[0])
                    names = behavior_yolo.names
                    label = names[cls_id] if cls_id in names else "person"
                    canonical = normalize_behavior(label)
                    confidence = float(box.conf[0]) if box.conf is not None else 0.0

                    if canonical in {"person", "human", "student"}:
                        continue
                    if confidence < PERSON_CROP_BEHAVIOR_CONFIDENCE:
                        continue

                    bx1, by1, bx2, by2 = box.xyxy[0].tolist()
                    mapped = clamp_box(
                        (x1 + bx1, y1 + by1, x1 + bx2, y1 + by2),
                        frame_w,
                        frame_h,
                    )
                    if mapped is None:
                        continue

                    # Crop inference already belongs to this recognized student.
                    detections.append({
                        "box": mapped,
                        "label": canonical,
                        "confidence": confidence,
                        "track_id": None,
                        "student_hint": student["student_id"],
                        "source": "student_crop",
                    })
                except Exception:
                    continue

    return detections


def assign_behaviors_to_students(behavior_detections, students, frame_shape=None):
    """Associate YOLO student-level behavior detections with recognized students."""
    result = {}

    for detection in behavior_detections:
        label = normalize_behavior(detection["label"])
        confidence = float(detection["confidence"])

        if label in {"person", "human", "student"}:
            continue

        # Every behavior class is filtered using the same raw-model rule.
        # phone_use is NOT treated as a physical phone object.
        if confidence < max(
            minimum_raw_confidence(label),
            safe_behavior_threshold(label),
        ):
            continue

        student = find_best_student_for_behavior(
            detection["box"],
            label,
            students,
            detection.get("student_hint"),
        )
        if student is None:
            continue

        student_id = student["student_id"]
        candidate_priority = live_behavior_priority(label)
        existing = result.get(student_id)

        candidate = {
            "label": label,
            "box": detection["box"],
            "priority": candidate_priority,
            "confidence": confidence,
            "source": detection.get("source", "full_frame"),
            "track_id": detection.get("track_id"),
        }

        if (
            existing is None
            or candidate_priority > existing["priority"]
            or (
                candidate_priority == existing["priority"]
                and confidence > existing["confidence"]
            )
        ):
            result[student_id] = candidate

    # A student with no behavior detection is considered attentive.
    for student in students:
        student_id = student["student_id"]
        if student_id not in result:
            result[student_id] = {
                "label": "attentive",
                "box": student["person_box"],
                "priority": live_behavior_priority("attentive"),
                "confidence": 1.0,
                "source": "default",
                "track_id": None,
            }

    return result

def phone_decision_state(raw_confidence):
    """Return an honest UI state for a validated phone detection.

    The YOLO probability is intentionally not displayed as a fake
    "accuracy" value. A validated phone detection is a system decision based
    on model output plus student-specific spatial association.
    """
    raw = max(0.0, min(1.0, float(raw_confidence or 0.0)))
    if raw >= 0.40:
        return "confirmed"
    return "detected"


def stabilize_student_behaviors(raw_student_behaviors, students, now):
    final = {}

    for student in students:
        student_id = student["student_id"]
        raw = raw_student_behaviors.get(
            student_id,
            {
                "label": "attentive",
                "confidence": 1.0,
                "box": student["person_box"],
                "source": "default",
                "track_id": None,
            },
        )

        track_id = raw.get("track_id")
        final_label, final_confidence = behavior_stabilizer.update(
            student_id,
            raw["label"],
            raw["confidence"],
            now,
            track_id=track_id,
        )

        final[student_id] = {
            "label": final_label,
            "confidence": final_confidence,
            "phone_state": (
                phone_decision_state(final_confidence)
                if normalize_behavior(final_label) == "phone_use"
                else None
            ),
            "box": raw.get("box", student["person_box"]),
            "source": raw.get("source", "default"),
            "track_id": track_id,
        }

        print(
            f"FINAL BEHAVIOR: student={student_id}, track_id={track_id}, "
            f"behavior={final_label}, conf={final_confidence:.3f}, "
            f"raw={normalize_behavior(raw.get('label', 'attentive'))}:{float(raw.get('confidence', 0.0)):.3f}"
        )

    return final


# ============================================================
# DRAWING
# ============================================================

def get_behavior_color(label):
    if behavior_is_alert(label):
        return (0, 0, 255)
    return (0, 220, 0)


def draw_student_box(frame, student, behavior_label, behavior_confidence, phone_state=None):
    x1, y1, x2, y2 = student["person_box"]
    student_id = str(student["student_id"])
    face_confidence = float(student["face_confidence"])
    behavior_confidence = float(behavior_confidence)
    behavior_name = normalize_behavior(behavior_label)

    color = get_behavior_color(behavior_name)
    if behavior_name == "phone_use":
        # Do not call YOLO's probability an "accuracy" percentage. The
        # phone decision has already passed student-specific association.
        # Show a clear state instead, while the raw model score remains in
        # the backend logs for debugging/evaluation.
        suffix = f" ({phone_state})" if phone_state else ""
        label = f"{student_id} | ID {face_confidence * 100:.0f}% | phone_use{suffix}"
    else:
        label = (
            f"{student_id} | ID {face_confidence * 100:.0f}% | "
            f"{behavior_name}"
        )

    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 3)

    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.55
    thickness = 2
    (text_width, text_height), baseline = cv2.getTextSize(
        label, font, font_scale, thickness
    )

    label_bottom = y1
    label_top = y1 - text_height - baseline - 10

    if label_top < 0:
        label_top = y1
        label_bottom = min(
            frame.shape[0], y1 + text_height + baseline + 10
        )
        text_y = label_bottom - baseline - 5
    else:
        text_y = label_bottom - baseline - 5

    label_left = x1
    label_right = min(frame.shape[1], x1 + text_width + 12)
    cv2.rectangle(
        frame,
        (label_left, label_top),
        (label_right, label_bottom),
        color,
        -1,
    )
    cv2.putText(
        frame,
        label,
        (x1 + 6, text_y),
        font,
        font_scale,
        (255, 255, 255),
        thickness,
        cv2.LINE_AA,
    )

    if DRAW_FACE_DEBUG_BOX:
        fx1, fy1, fx2, fy2 = student["face_box"]
        cv2.rectangle(frame, (fx1, fy1), (fx2, fy2), (255, 180, 0), 1)


def draw_behavior_debug(frame, detection):
    if not DRAW_BEHAVIOR_DEBUG_BOXES:
        return

    x1, y1, x2, y2 = detection["box"]
    label = f'{normalize_behavior(detection["label"])} ({detection["confidence"]:.2f})'
    cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 255, 0), 1)
    cv2.putText(
        frame,
        label,
        (x1, max(15, y1 - 5)),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.45,
        (255, 255, 0),
        1,
        cv2.LINE_AA,
    )


# ============================================================
# LIVE STREAM
# ============================================================

def generate_video_stream():
    global active_ai_session

    cap = active_ai_session["cap"]
    if cap is None or not cap.isOpened():
        print("ERROR: Camera is not initialized")
        active_ai_session["is_running"] = False
        return

    mode = active_ai_session["mode"]
    print("Loading behavior YOLO model...")

    try:
        behavior_yolo = get_yolo_model(mode)
        phone_yolo = None  # classroom_model.pt already contains phone_use
    except Exception as e:
        print("YOLO LOAD ERROR:", repr(e))
        active_ai_session["is_running"] = False
        return

    print("LIVE VIDEO STREAM STARTED")
    print("MAIN STUDENT BOX: YOLO PERSON DETECTION")
    print("FACE BOX: RECOGNITION ONLY")
    print("BEHAVIOR: YOLO + BYTETRACK + STUDENT-LEVEL ASSOCIATION + CONSERVATIVE TEMPORAL VOTING")
    print("BEHAVIOR RAW CONFIDENCE:", BEHAVIOR_RAW_CONFIDENCE)
    print("PHONE RAW CONFIDENCE:", PHONE_RAW_CONFIDENCE)
    print("PHONE CONFIRM: 1 strong hit >= 0.45 OR 2 moderate hits within 2.0s")
    print("PHONE EVIDENCE WINDOW:", PHONE_EVIDENCE_WINDOW)
    print("PHONE MIN AVG CONFIDENCE:", PHONE_MIN_AVERAGE_CONFIDENCE)
    print("TEMPORAL EVIDENCE: keyed by verified student_id; track_id optional")
    print("PHONE STRONG OBSERVATION THRESHOLD:", PHONE_IMMEDIATE_CONFIDENCE)
    print("PHONE EXTRA MODEL/CROP PASS: DISABLED FOR LOW LATENCY")
    print("PHONE BODY-BOX ASSOCIATION MAX DISTANCE:", PHONE_ASSOCIATION_MAX_DISTANCE)
    print("SLEEPING CONFIRM EVIDENCE:", SLEEPING_CONFIRM_FRAMES)
    print("PERSON CROP BEHAVIOR:", PERSON_CROP_BEHAVIOR_ENABLED)
    print("PERSON CROP ONLY IF NO PHONE:", PERSON_CROP_ONLY_IF_NO_PHONE)
    print("PHONE SOURCES: classroom_model.pt + yolov8n cell-phone class")
    print("OBJECT DETECTOR INTERVAL:", OBJECT_DETECTION_INTERVAL)
    print("PHYSICAL PHONE CONFIDENCE:", OBJECT_PHONE_CONFIDENCE)
    try:
        print("ACTIVE BEHAVIOR CLASSES:", behavior_yolo.names)
    except Exception:
        pass

    frame_counter = 0
    last_phone_debug_time = 0.0
    consecutive_frame_misses = 0

    try:
        while active_ai_session["is_running"]:
            ret, frame = cap.read()
            if not ret or frame is None:
                consecutive_frame_misses += 1
                if consecutive_frame_misses > 60:
                    print("CAMERA FRAME TIMEOUT (No frames received for 600ms)")
                    break
                time.sleep(0.01)
                continue

            consecutive_frame_misses = 0
            current_time = time.time()
            timestamp = datetime.now()
            frame_counter += 1
            active_ai_session["frame_counter"] = frame_counter

            # --------------------------------------------------
            # 1. BEHAVIOR YOLO + BYTETRACK (CUDA FP16 ACCELERATED)
            # --------------------------------------------------
            # Restore the original working architecture: YOLO tracking with
            # ByteTrack. The behavior model produces student-level boxes, so
            # those boxes are passed directly to student association.
            behavior_detections = []

            try:
                results = behavior_yolo.track(
                    frame,
                    persist=True,
                    tracker="bytetrack.yaml",
                    conf=min(
                        BEHAVIOR_RAW_CONFIDENCE,
                        PHONE_RAW_CONFIDENCE,
                        SLEEPING_RAW_CONFIDENCE,
                        CHEATING_RAW_CONFIDENCE,
                    ),
                    imgsz=640,
                    iou=0.45,
                    device=YOLO_DEVICE,
                    half=YOLO_HALF,
                    verbose=False,
                )
            except Exception as e:
                print("YOLO BEHAVIOR TRACKING ERROR:", repr(e))
                results = []

            for result in results:
                boxes = result.boxes
                if boxes is None:
                    continue

                for box in boxes:
                    try:
                        behavior_box = clamp_box(
                            box.xyxy[0].tolist(),
                            frame.shape[1],
                            frame.shape[0],
                        )
                        if behavior_box is None:
                            continue

                        cls_id = int(box.cls[0])
                        names = behavior_yolo.names
                        label = names[cls_id] if cls_id in names else "person"
                        confidence = float(box.conf[0]) if box.conf is not None else 0.0
                        canonical = normalize_behavior(label)

                        if canonical in {"person", "human", "student"}:
                            continue

                        if confidence < minimum_raw_confidence(canonical):
                            continue

                        track_id = None
                        try:
                            if box.id is not None:
                                track_id = int(box.id[0])
                        except Exception:
                            track_id = None

                        detection = {
                            "box": behavior_box,
                            "label": canonical,
                            "confidence": confidence,
                            "track_id": track_id,
                            "source": "full_frame_bytetrack",
                        }
                        behavior_detections.append(detection)
                        draw_behavior_debug(frame, detection)

                        print(
                            f"BEHAVIOR RAW: frame={frame_counter}, "
                            f"class={canonical}, conf={confidence:.3f}, "
                            f"track_id={track_id}, box={behavior_box}"
                        )

                    except Exception as e:
                        print("YOLO BOX ERROR:", repr(e))

            # 2. FACE RECOGNITION
            # --------------------------------------------------
            if frame_counter == 1 or frame_counter % FACE_RECOGNITION_INTERVAL == 0:
                new_faces = detect_and_recognize_faces(frame)
                update_face_cache(new_faces)

            recognized_faces = get_current_recognized_faces()

            # --------------------------------------------------
            # 3. PERSON DETECTION
            # --------------------------------------------------
            # One YOLOv8n pass handles BOTH person + physical cell phone.
            if (
                frame_counter == 1
                or frame_counter % OBJECT_DETECTION_INTERVAL == 0
                or not active_ai_session.get("person_detections")
            ):
                persons, object_phones = detect_persons_and_phones(frame)
                active_ai_session["person_detections"] = persons
                active_ai_session["object_detections"] = object_phones
                active_ai_session["last_object_detection_time"] = current_time
            else:
                persons = active_ai_session.get("person_detections", [])
                object_phones = active_ai_session.get("object_detections", [])

                # Do not hold stale phone evidence for too long.
                if (
                    current_time
                    - float(active_ai_session.get("last_object_detection_time", 0.0))
                    > OBJECT_PHONE_HOLD_SECONDS
                ):
                    object_phones = []

            # --------------------------------------------------
            # 4. FACE -> PERSON -> STUDENT
            # --------------------------------------------------
            students = match_faces_to_persons(persons, recognized_faces)

            # --------------------------------------------------
            # 5. RAW BEHAVIOR -> STUDENT
            # Behavior YOLO already produced student-level boxes. Do not run
            # a second inference on individual crops.
            # 6. RAW BEHAVIOR -> STUDENT
            # --------------------------------------------------
            # classroom_model.pt already contains:
            # attentive, not_attentive, phone_use, sleeping.
            # Use ONE behavior inference per frame for low latency.
            raw_student_behaviors = assign_behaviors_to_students(
                behavior_detections,
                students,
                frame.shape,
            )

            # Associate generic YOLOv8n cell-phone boxes to recognized students.
            physical_phone_assignments = assign_physical_phones_to_students(
                object_phones,
                students,
                frame.shape,
            )

            # Fuse custom behavior model + physical phone evidence.
            raw_student_behaviors = fuse_final_behaviors(
                raw_student_behaviors,
                physical_phone_assignments,
                students,
            )

            for phone_student_id, phone_info in physical_phone_assignments.items():
                print(
                    f"PHYSICAL PHONE: student={phone_student_id}, "
                    f"conf={phone_info['confidence']:.3f}, "
                    f"box={phone_info['box']}"
                )

            for debug_student_id, debug_behavior in raw_student_behaviors.items():
                if normalize_behavior(debug_behavior["label"]) == "phone_use":
                    print(
                        f"PHONE ASSIGNED: student={debug_student_id}, "
                        f"conf={debug_behavior['confidence']:.3f}, "
                        f"source={debug_behavior.get('source', 'unknown')}, "
                        f"box={debug_behavior['box']}"
                    )

            # --------------------------------------------------
            # 6. TEMPORAL STABILIZATION
            # --------------------------------------------------
            student_behaviors = stabilize_student_behaviors(
                raw_student_behaviors,
                students,
                current_time,
            )

            # --------------------------------------------------
            # 7. STATISTICS + DISPLAY + EVIDENCE
            # --------------------------------------------------
            for student_id, behavior_info in student_behaviors.items():
                update_student_statistics(
                    student_id,
                    behavior_info["label"],
                    current_time,
                    timestamp,
                )

            student_lookup = {
                student["student_id"]: student for student in students
            }

            for student_id, behavior_info in student_behaviors.items():
                student = student_lookup.get(student_id)
                if student is None:
                    continue

                behavior_label = behavior_info["label"]
                behavior_confidence = behavior_info["confidence"]

                draw_student_box(
                    frame,
                    student,
                    behavior_label,
                    behavior_confidence,
                    behavior_info.get("phone_state"),
                )

                if behavior_is_alert(behavior_label):
                    save_evidence(
                        student_id,
                        behavior_label,
                        frame.copy(),
                    )

            # --------------------------------------------------
            # 8. ENCODE STREAM FRAME
            # --------------------------------------------------
            ret, buffer = cv2.imencode(".jpg", frame)
            if not ret:
                continue

            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n"
                + buffer.tobytes()
                + b"\r\n"
            )

    except Exception as e:
        print("VIDEO STREAM ERROR:", repr(e))
    finally:
        print("VIDEO STREAM GENERATOR CLOSED")


# ============================================================
# ENDPOINTS
# ============================================================

@router.get("/video-feed")
async def video_feed():
    if not active_ai_session["is_running"]:
        raise HTTPException(
            status_code=400,
            detail="Camera session is not active",
        )

    cap = active_ai_session.get("cap")
    if cap is None or not cap.isOpened():
        raise HTTPException(
            status_code=500,
            detail="Camera is not initialized",
        )

    return StreamingResponse(
        generate_video_stream(),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )


@router.post("/start-camera")
async def start_camera(data: dict):
    global active_ai_session

    with camera_lock:
        if active_ai_session["is_running"]:
            raise HTTPException(
                status_code=400,
                detail="An AI session is already running",
            )

        mode = data.get("mode", "classroom")
        if mode not in {"classroom", "exam"}:
            raise HTTPException(
                status_code=400,
                detail="Invalid monitoring mode",
            )

        print("INITIALIZING STUDENT360 THREADED CAMERA (DIRECTSHOW, 640x480 @ 30 FPS)...")
        cap = ThreadedCamera(src=0, width=640, height=480, fps=30).start()
        time.sleep(0.15)  # Allow background daemon thread to grab first frame

        if not cap.isOpened():
            cap.release()
            raise HTTPException(
                status_code=500,
                detail="Unable to open webcam with DirectShow/Default backend",
            )

        ret, test_frame = cap.read()
        if not ret or test_frame is None:
            cap.release()
            raise HTTPException(
                status_code=500,
                detail="Camera opened but failed to capture frame",
            )

        session_id = str(uuid.uuid4())
        started_at = datetime.now()

        behavior_stabilizer.reset()

        active_ai_session.update({
            "cap": cap,
            "is_running": True,
            "mode": mode,
            "student_stats": {},
            "tracker_to_student_map": {},
            "recognized_faces": [],
            "person_detections": [],
            "session_id": session_id,
            "started_at": started_at,
            "frame_counter": 0,
            "behavior_states": {},
            "object_detections": [],
            "last_object_detection_time": 0.0,
        })

        print("================================")
        print("AI SESSION STARTED")
        print("SESSION ID:", session_id)
        print("MODE:", mode)
        print("CAMERA INITIALIZED")
        print("MAIN BOX: PERSON")
        print("FACE RECOGNITION: FULL FRAME")
        print("BEHAVIOR: YOLO + BYTETRACK + STUDENT-LEVEL ASSOCIATION + CONSERVATIVE TEMPORAL VOTING")
        print("BEHAVIOR RAW CONFIDENCE:", BEHAVIOR_RAW_CONFIDENCE)
        print("PHONE RAW CONFIDENCE:", PHONE_RAW_CONFIDENCE)
        print("================================")

        return {
            "status": "success",
            "session_id": session_id,
            "mode": mode,
            "message": "Camera initialized successfully",
        }


@router.post("/stop-camera")
async def stop_camera():
    global active_ai_session

    if not active_ai_session["is_running"]:
        return {
            "status": "warning",
            "message": "No active session",
        }

    active_ai_session["is_running"] = False

    cap = active_ai_session.get("cap")
    if cap is not None:
        try:
            cap.release()
        except Exception as e:
            print("Camera release error:", repr(e))
        active_ai_session["cap"] = None
        print("THREADED CAMERA RELEASED CLEANLY")

    try:
        cv2.destroyAllWindows()
    except Exception:
        pass

    mode = active_ai_session["mode"]
    stats = active_ai_session["student_stats"]
    session_id = str(active_ai_session.get("session_id") or "unknown")
    started_at = active_ai_session.get("started_at") or datetime.now()
    ended_at = datetime.now()

    date_str = ended_at.strftime("%Y-%m-%d_%H-%M-%S")
    csv_filename = (
        f"session_summary_{mode}_{date_str}_{session_id[:8]}.csv"
    )
    csv_path = os.path.join(SESSION_LOGS_FOLDER, csv_filename)

    columns = [
        "Student_ID",
        "Date",
        "Arrival_Time",
        "cheating_sec",
        "non_cheating_sec",
        "attentive_sec",
        "sleeping_sec",
        "phone_use_sec",
        "not_attentive_sec",
    ]

    if stats:
        df = pd.DataFrame.from_dict(stats, orient="index")
        df.index.name = "Student_ID"
        df.reset_index(inplace=True)
        df = df.drop(
            columns=["last_seen_time", "last_evidence_time"],
            errors="ignore",
        )
        df = df.reindex(columns=columns, fill_value=0)
        df = df.round(2)
    else:
        print("WARNING: No recognized students found")
        df = pd.DataFrame(columns=columns)

    try:
        df.to_csv(csv_path, index=False)
        print("CSV SAVED:", os.path.abspath(csv_path))
    except Exception as e:
        print("CSV ERROR:", repr(e))
        raise HTTPException(
            status_code=500,
            detail=f"CSV saving failed: {str(e)}",
        )

    attendance_inserted = 0
    behavior_inserted = 0
    database_errors = []

    for _, row in df.iterrows():
        student_id = str(row["Student_ID"])
        record_date = str(row["Date"])

        attendance_record = {
            "student_id": student_id,
            "date": record_date,
            "arrival_time": str(row["Arrival_Time"]),
            "session_id": session_id,
            "mode": mode,
            "status": "Present",
            "created_at": ended_at,
        }

        behavior_record = {
            "student_id": student_id,
            "date": record_date,
            "session_id": session_id,
            "mode": mode,
            "cheating_sec": float(row["cheating_sec"]),
            "non_cheating_sec": float(row["non_cheating_sec"]),
            "attentive_sec": float(row["attentive_sec"]),
            "sleeping_sec": float(row["sleeping_sec"]),
            "phone_use_sec": float(row["phone_use_sec"]),
            "not_attentive_sec": float(row["not_attentive_sec"]),
            "created_at": ended_at,
        }

        try:
            attendance_collection.insert_one(attendance_record)
            attendance_inserted += 1
            print("ATTENDANCE SAVED:", student_id)
        except Exception as e:
            database_errors.append({
                "collection": "attendance",
                "student_id": student_id,
                "error": str(e),
            })
            print("ATTENDANCE ERROR:", repr(e))

        try:
            behavior_collection.insert_one(behavior_record)
            behavior_inserted += 1
            print("BEHAVIOUR SAVED:", student_id)
        except Exception as e:
            database_errors.append({
                "collection": "behavior",
                "student_id": student_id,
                "error": str(e),
            })
            print("BEHAVIOUR ERROR:", repr(e))

    session_status = (
        "completed" if not database_errors else "completed_with_errors"
    )

    try:
        sessions_collection.insert_one({
            "session_id": session_id,
            "mode": mode,
            "started_at": started_at,
            "ended_at": ended_at,
            "csv_filename": csv_filename,
            "csv_path": csv_path,
            "total_students": len(df),
            "attendance_inserted": attendance_inserted,
            "behavior_inserted": behavior_inserted,
            "status": session_status,
        })
        print("SESSION REPORT SAVED TO MONGODB")
    except Exception as e:
        database_errors.append({
            "collection": "sessions",
            "error": str(e),
        })
        print("SESSION DATABASE ERROR:", repr(e))

    behavior_stabilizer.reset()

    active_ai_session.update({
        "cap": None,
        "is_running": False,
        "mode": None,
        "student_stats": {},
        "tracker_to_student_map": {},
        "recognized_faces": [],
        "person_detections": [],
        "session_id": None,
        "started_at": None,
        "frame_counter": 0,
        "behavior_states": {},
        "object_detections": [],
        "last_object_detection_time": 0.0,
    })

    print("================================")
    print("SESSION COMPLETED")
    print("TOTAL STUDENTS:", len(df))
    print("ATTENDANCE:", attendance_inserted)
    print("BEHAVIOUR:", behavior_inserted)
    print("DATABASE ERRORS:", len(database_errors))
    print("CSV:", csv_path)
    print("================================")

    return {
        "status": "success" if not database_errors else "partial_success",
        "message": "AI session stopped and report generated",
        "session_id": session_id,
        "csv_file": csv_filename,
        "total_students": len(df),
        "attendance_inserted": attendance_inserted,
        "behavior_inserted": behavior_inserted,
        "database_errors": database_errors,
    }


@router.post("/process-video")
async def process_video(file: UploadFile = File(...)):
    filename = file.filename or f"video_{uuid.uuid4().hex}.mp4"
    filepath = os.path.join(UPLOAD_FOLDER, filename)

    try:
        with open(filepath, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        pipeline_path = os.path.abspath(
            os.path.join(BASE_DIR, "../ai_engine/unified_pipeline.py")
        )

        subprocess.run(
            [sys.executable, pipeline_path, filepath],
            check=True,
        )

        return {
            "status": "success",
            "message": "Video processed successfully",
        }
    except Exception as e:
        print("VIDEO PROCESSING ERROR:", repr(e))
        raise HTTPException(
            status_code=500,
            detail=f"Video processing failed: {str(e)}",
        )


# ============================================================
# HOT RELOAD FACE MODELS
# ============================================================

def reload_face_models():
    global face_svm, label_encoder, detector, embedder

    try:
        if detector is None:
            detector = MTCNN()
        if embedder is None:
            embedder = FaceNet()

        face_model_path = resolve_model_file("face_model.pkl")
        encoder_path = resolve_model_file("label_encoder.pkl")

        face_svm = joblib.load(face_model_path)
        label_encoder = joblib.load(encoder_path)

        active_ai_session["tracker_to_student_map"] = {}
        active_ai_session["recognized_faces"] = []
        behavior_stabilizer.reset()

        try:
            students = [str(x) for x in label_encoder.classes_]
        except Exception:
            students = []

        print("==========================================")
        print("FACE MODEL HOT RELOAD SUCCESSFUL")
        print("Face model:", face_model_path)
        print("Label encoder:", encoder_path)
        print("Known students:", students)
        print("==========================================")

        return {
            "status": "success",
            "message": "Face recognition models reloaded successfully.",
            "students": students,
        }

    except Exception as e:
        print("FAILED TO RELOAD FACE MODELS:", repr(e))
        return {
            "status": "error",
            "message": str(e),
        }
