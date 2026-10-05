# ============================================================
# STUDENT360 - LIVE AI SURVEILLANCE ENGINE
# Fixed behavior pipeline: phone-use recall + temporal filtering
# ============================================================

from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse

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
FACE_RECOGNITION_INTERVAL = 3
FACE_DETECTION_CONFIDENCE = 0.80
FACE_RECOGNITION_THRESHOLD = 0.55
FACE_CONFIDENCE_MARGIN = 0.05
FACE_CACHE_SECONDS = 1.0

# -------------------------
# Person detection settings
# -------------------------
MIN_PERSON_WIDTH = 60
MIN_PERSON_HEIGHT = 100
PERSON_DETECTION_CONFIDENCE = 0.35

# -------------------------
# Behavior settings
# -------------------------
# IMPORTANT: Do not use 0.45 globally. Phones are small and commonly have
# lower confidence than the person's body/face.
BEHAVIOR_RAW_CONFIDENCE = 0.20
PHONE_RAW_CONFIDENCE = 0.20
SLEEPING_RAW_CONFIDENCE = 0.35
CHEATING_RAW_CONFIDENCE = 0.30

# Temporal filtering prevents one bad frame from becoming an alert.
PHONE_CONFIRM_FRAMES = 2
SLEEPING_CONFIRM_FRAMES = 4
CHEATING_CONFIRM_FRAMES = 3
NOT_ATTENTIVE_CONFIRM_FRAMES = 3
ATTENTIVE_CONFIRM_FRAMES = 3

# Keep an already confirmed alert briefly if YOLO misses one frame.
ALERT_HOLD_SECONDS = 1.20
ALERT_RELEASE_FRAMES = 4

# Phone boxes are small and often far from the face center.
PHONE_ASSOCIATION_MAX_DISTANCE = 450
BEHAVIOR_ASSOCIATION_MAX_DISTANCE = 360

# Debug boxes can be enabled if needed.
DRAW_FACE_DEBUG_BOX = False
DRAW_BEHAVIOR_DEBUG_BOXES = False

# Print raw phone detections at most once per second.
PHONE_DEBUG_INTERVAL = 1.0


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


active_ai_session = {
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
    value = str(value).strip().lower().replace(" ", "_").replace("-", "_")
    return aliases.get(value, value)


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
    """Small per-student state machine for stable live behavior labels."""

    def __init__(self):
        self.states = {}

    def reset(self):
        self.states.clear()

    def _required_frames(self, label):
        name = normalize_behavior(label)
        if name == "phone_use":
            return PHONE_CONFIRM_FRAMES
        if name == "sleeping":
            return SLEEPING_CONFIRM_FRAMES
        if name in {"cheating", "malpractice"}:
            return CHEATING_CONFIRM_FRAMES
        if name == "not_attentive":
            return NOT_ATTENTIVE_CONFIRM_FRAMES
        return ATTENTIVE_CONFIRM_FRAMES

    def update(self, student_id, candidate_label, candidate_confidence, now):
        student_id = str(student_id)
        candidate = normalize_behavior(candidate_label)
        confidence = float(candidate_confidence)

        state = self.states.setdefault(
            student_id,
            {
                "current": "attentive",
                "current_confidence": 1.0,
                "candidate": None,
                "candidate_frames": 0,
                "last_observed": 0.0,
                "missing_alert_frames": 0,
                "history": deque(maxlen=8),
            },
        )

        if candidate not in {"attentive", "person"} and not effective_behavior_confidence(candidate, confidence):
            candidate = "attentive"
            confidence = 0.0

        # Raw observation exists.
        if candidate != "attentive":
            state["last_observed"] = now
            state["missing_alert_frames"] = 0
        elif state["current"] != "attentive":
            state["missing_alert_frames"] += 1

        # Same as current behavior: refresh confidence and keep it stable.
        if candidate == state["current"]:
            if confidence > 0:
                old = float(state["current_confidence"])
                state["current_confidence"] = 0.70 * old + 0.30 * confidence
            state["candidate"] = None
            state["candidate_frames"] = 0
            state["history"].append((candidate, confidence, now))
            return state["current"], state["current_confidence"]

        # If an alert is currently active, briefly hold it through missed detections.
        if state["current"] != "attentive" and candidate == "attentive":
            if (
                now - state["last_observed"] <= ALERT_HOLD_SECONDS
                and state["missing_alert_frames"] < ALERT_RELEASE_FRAMES
            ):
                state["history"].append((state["current"], state["current_confidence"], now))
                return state["current"], state["current_confidence"]

        # Start/count a new candidate behavior.
        if candidate == state["candidate"]:
            state["candidate_frames"] += 1
        else:
            state["candidate"] = candidate
            state["candidate_frames"] = 1

        required = self._required_frames(candidate)
        state["history"].append((candidate, confidence, now))

        if state["candidate_frames"] >= required:
            state["current"] = candidate
            state["current_confidence"] = max(0.0, min(1.0, confidence))
            state["candidate"] = None
            state["candidate_frames"] = 0
            state["missing_alert_frames"] = 0
            return state["current"], state["current_confidence"]

        return state["current"], state["current_confidence"]


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
            _yolo_cache[model_path] = YOLO(model_path)
            try:
                print("BEHAVIOR MODEL CLASSES:", _yolo_cache[model_path].names)
            except Exception:
                pass
        return _yolo_cache[model_path]

    fallback_key = "yolov8n.pt"
    if fallback_key not in _yolo_cache:
        print("Custom behavior model not found. Using YOLOv8n fallback.")
        _yolo_cache[fallback_key] = YOLO(fallback_key)
        try:
            print("FALLBACK MODEL CLASSES:", _yolo_cache[fallback_key].names)
        except Exception:
            pass
    return _yolo_cache[fallback_key]


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
            "behavior": str(normalize_behavior(behavior_label)),
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
            results = person_model(
                frame,
                conf=PERSON_DETECTION_CONFIDENCE,
                classes=[0],
                verbose=False,
            )
            for result in results:
                boxes = result.boxes
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
            results = behavior_yolo(frame, conf=0.20, verbose=False)
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

def phone_box_belongs_to_student(phone_box, student):
    """Phone-specific association. A phone does NOT need to be near the face."""
    person_box = student["person_box"]
    px, py = box_center(phone_box)

    # 1. Phone center is inside the body box.
    if point_inside_box((px, py), person_box):
        return True, 0.0

    # 2. Slightly expand the body box to account for hands/phone extending out.
    expanded = expand_box(
        person_box,
        max(person_box[2], phone_box[2]) + 1,
        max(person_box[3], phone_box[3]) + 1,
        left=0.15,
        right=0.15,
        top=0.05,
        bottom=0.20,
    )
    if expanded is not None and point_inside_box((px, py), expanded):
        return True, 30.0

    # 3. Distance fallback. Phones are often held outside the exact person box.
    cx, cy = student["center"]
    dx = cx - px
    dy = cy - py
    distance = (dx * dx + dy * dy) ** 0.5
    if distance <= PHONE_ASSOCIATION_MAX_DISTANCE:
        return True, distance

    return False, float("inf")


def find_best_student_for_behavior(behavior_box, behavior_label, students):
    if not students:
        return None

    label = normalize_behavior(behavior_label)

    # Phone use needs its own geometry because the phone itself is a small box.
    if label == "phone_use":
        best = None
        best_score = float("inf")
        for student in students:
            belongs, distance = phone_box_belongs_to_student(behavior_box, student)
            if not belongs:
                continue

            overlap = calculate_iou(behavior_box, student["person_box"])
            score = distance - (overlap * 250.0)
            if score < best_score:
                best_score = score
                best = student
        return best

    behavior_center = box_center(behavior_box)
    best = None
    best_score = float("inf")

    for student in students:
        person_box = student["person_box"]
        face_box = student["face_box"]
        person_iou = calculate_iou(behavior_box, person_box)
        face_inside = point_inside_box(student["center"], behavior_box)
        face_overlap = calculate_iou(behavior_box, face_box)

        if person_iou > 0.15 or face_inside or face_overlap > 0.05:
            score = -1000.0 - person_iou * 500.0 - face_overlap * 300.0
        else:
            person_center = student["center"]
            dx = person_center[0] - behavior_center[0]
            dy = person_center[1] - behavior_center[1]
            distance = (dx * dx + dy * dy) ** 0.5
            score = distance * (1.0 - min(person_iou, 0.90))

        if score < best_score:
            best_score = score
            best = student

    if best is None or best_score > BEHAVIOR_ASSOCIATION_MAX_DISTANCE:
        return None
    return best


def assign_behaviors_to_students(behavior_detections, students):
    """Choose the strongest raw behavior for each recognized student."""
    result = {}

    for detection in behavior_detections:
        label = normalize_behavior(detection["label"])
        confidence = float(detection["confidence"])

        if label in {"person", "human", "student"}:
            continue

        # Never let a low-confidence raw alert reach the association layer.
        if not effective_behavior_confidence(label, confidence):
            continue

        student = find_best_student_for_behavior(
            detection["box"], label, students
        )
        if student is None:
            continue

        student_id = student["student_id"]
        existing = result.get(student_id)
        candidate_priority = behavior_priority(label)

        if (
            existing is None
            or candidate_priority > existing["priority"]
            or (
                candidate_priority == existing["priority"]
                and confidence > existing["confidence"]
            )
        ):
            result[student_id] = {
                "label": label,
                "box": detection["box"],
                "priority": candidate_priority,
                "confidence": confidence,
            }

    # No confirmed raw alert means the raw state is attentive.
    for student in students:
        student_id = student["student_id"]
        if student_id not in result:
            result[student_id] = {
                "label": "attentive",
                "box": student["person_box"],
                "priority": behavior_priority("attentive"),
                "confidence": 1.0,
            }

    return result


def stabilize_student_behaviors(raw_student_behaviors, students, now):
    final = {}

    for student in students:
        student_id = student["student_id"]
        raw = raw_student_behaviors.get(
            student_id,
            {"label": "attentive", "confidence": 1.0, "box": student["person_box"]},
        )

        final_label, final_confidence = behavior_stabilizer.update(
            student_id,
            raw["label"],
            raw["confidence"],
            now,
        )

        final[student_id] = {
            "label": final_label,
            "confidence": final_confidence,
            "box": raw.get("box", student["person_box"]),
        }

    return final


# ============================================================
# DRAWING
# ============================================================

def get_behavior_color(label):
    if behavior_is_alert(label):
        return (0, 0, 255)
    return (0, 220, 0)


def draw_student_box(frame, student, behavior_label, behavior_confidence):
    x1, y1, x2, y2 = student["person_box"]
    student_id = str(student["student_id"])
    face_confidence = float(student["face_confidence"])
    behavior_confidence = float(behavior_confidence)
    behavior_name = normalize_behavior(behavior_label)

    color = get_behavior_color(behavior_name)
    label = (
        f"{student_id} | ID {face_confidence * 100:.0f}% | "
        f"{behavior_name} {behavior_confidence * 100:.0f}%"
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
    except Exception as e:
        print("YOLO LOAD ERROR:", repr(e))
        active_ai_session["is_running"] = False
        return

    print("LIVE VIDEO STREAM STARTED")
    print("MAIN STUDENT BOX: YOLO PERSON DETECTION")
    print("FACE BOX: RECOGNITION ONLY")
    print("BEHAVIOR: PREDICT + TEMPORAL STABILIZATION")
    print("BEHAVIOR RAW CONFIDENCE:", BEHAVIOR_RAW_CONFIDENCE)
    print("PHONE RAW CONFIDENCE:", PHONE_RAW_CONFIDENCE)
    print("PHONE CONFIRM FRAMES:", PHONE_CONFIRM_FRAMES)
    print("SLEEPING CONFIRM FRAMES:", SLEEPING_CONFIRM_FRAMES)

    frame_counter = 0
    last_phone_debug_time = 0.0

    try:
        while active_ai_session["is_running"]:
            ret, frame = cap.read()
            if not ret or frame is None:
                print("CAMERA FRAME ERROR")
                break

            current_time = time.time()
            timestamp = datetime.now()
            frame_counter += 1
            active_ai_session["frame_counter"] = frame_counter

            # --------------------------------------------------
            # 1. BEHAVIOR YOLO
            # --------------------------------------------------
            # IMPORTANT: predict() rather than track(). We do not need
            # behavior tracking IDs, and small phone detections should
            # not be lost by tracker confidence filtering.
            behavior_detections = []

            try:
                results = behavior_yolo.predict(
                    frame,
                    conf=BEHAVIOR_RAW_CONFIDENCE,
                    verbose=False,
                )
            except Exception as e:
                print("YOLO BEHAVIOR PREDICTION ERROR:", repr(e))
                results = []

            for result in results:
                boxes = result.boxes
                if boxes is None:
                    continue

                for box in boxes:
                    try:
                        coords = box.xyxy[0].tolist()
                        behavior_box = clamp_box(
                            coords,
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

                        # Ignore generic person detections here.
                        if canonical in {"person", "human", "student"}:
                            continue

                        # We intentionally keep phone candidates at low confidence.
                        if confidence < minimum_raw_confidence(canonical):
                            continue

                        detection = {
                            "box": behavior_box,
                            "label": canonical,
                            "confidence": confidence,
                            "track_id": None,
                        }
                        behavior_detections.append(detection)
                        draw_behavior_debug(frame, detection)

                        if canonical == "phone_use" and (
                            current_time - last_phone_debug_time >= PHONE_DEBUG_INTERVAL
                        ):
                            print(
                                f"PHONE RAW DETECTION: conf={confidence:.3f}, "
                                f"box={behavior_box}"
                            )
                            last_phone_debug_time = current_time

                    except Exception as e:
                        print("YOLO BOX ERROR:", repr(e))

            # --------------------------------------------------
            # 2. FACE RECOGNITION
            # --------------------------------------------------
            if frame_counter % FACE_RECOGNITION_INTERVAL == 0:
                new_faces = detect_and_recognize_faces(frame)
                update_face_cache(new_faces)

            recognized_faces = get_current_recognized_faces()

            # --------------------------------------------------
            # 3. PERSON DETECTION
            # --------------------------------------------------
            persons = detect_persons(frame, behavior_yolo)
            active_ai_session["person_detections"] = persons

            # --------------------------------------------------
            # 4. FACE -> PERSON -> STUDENT
            # --------------------------------------------------
            students = match_faces_to_persons(persons, recognized_faces)

            # --------------------------------------------------
            # 5. RAW BEHAVIOR -> STUDENT
            # --------------------------------------------------
            raw_student_behaviors = assign_behaviors_to_students(
                behavior_detections,
                students,
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

        print("INITIALIZING STUDENT360 CAMERA...")
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        if not cap.isOpened():
            cap.release()
            cap = cv2.VideoCapture(0)

        if not cap.isOpened():
            cap.release()
            raise HTTPException(
                status_code=500,
                detail="Unable to open webcam",
            )

        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

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
        })

        print("================================")
        print("AI SESSION STARTED")
        print("SESSION ID:", session_id)
        print("MODE:", mode)
        print("CAMERA INITIALIZED")
        print("MAIN BOX: PERSON")
        print("FACE RECOGNITION: FULL FRAME")
        print("BEHAVIOR: PREDICT + TEMPORAL STABILIZATION")
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
        cap.release()
        print("CAMERA RELEASED")

    mode = active_ai_session["mode"]
    stats = active_ai_session["student_stats"]
    session_id = active_ai_session["session_id"]
    started_at = active_ai_session["started_at"]
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
    filepath = os.path.join(UPLOAD_FOLDER, file.filename)

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
