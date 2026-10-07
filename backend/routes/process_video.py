# ============================================================
# STUDENT360 - LIVE AI SURVEILLANCE ENGINE
# Final behavior pipeline: YOLO + ByteTrack + conservative temporal voting
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
DEMO_VIDEOS_DIR = os.path.join(BASE_DIR, "demo_videos")

for folder in [UPLOAD_FOLDER, SESSION_LOGS_FOLDER, EVIDENCE_FOLDER, ATTENDANCE_FOLDER, DEMO_VIDEOS_DIR]:
    os.makedirs(folder, exist_ok=True)

# -------------------------
# Face recognition settings
# -------------------------
FACE_RECOGNITION_INTERVAL = 6
FACE_DETECTION_CONFIDENCE = 0.60
FACE_RECOGNITION_THRESHOLD = 0.50
FACE_CONFIDENCE_MARGIN = 0.02
FACE_CACHE_SECONDS = 8.0
IDENTITY_HOLD_SECONDS = 45.0

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
CHEATING_RAW_CONFIDENCE = 0.30

# Hybrid exam fallback used only in Exam Proctor mode.
# This does NOT replace the YOLO exam model; it supplements it when
# suspicious head movement is obvious but the model confidence is weak.
EXAM_HEAD_TURN_RATIO = 0.18
EXAM_HEAD_TURN_CONFIRM_FRAMES = 3
EXAM_FACE_MISSING_SECONDS = 1.20
EXAM_HEURISTIC_HOLD_SECONDS = 0.90

# Classroom sleeping fallback.
# Used when the face becomes hidden because the student lays the head down.
SLEEP_FACE_MISSING_SECONDS = 1.20
SLEEP_HEAD_LOW_RATIO = 0.62
SLEEP_HEURISTIC_HOLD_SECONDS = 0.60
SLEEP_HEURISTIC_CONFIDENCE = 0.65

# Temporal filtering prevents one bad frame from becoming an alert.
# A behavior must have repeated evidence inside a short time window.
# These are intentionally not simple consecutive-frame counters because
# small phones can disappear for a frame or two while the student moves.
PHONE_CONFIRM_FRAMES = 2
SLEEPING_CONFIRM_FRAMES = 3
CHEATING_CONFIRM_FRAMES = 2
NOT_ATTENTIVE_CONFIRM_FRAMES = 3
ATTENTIVE_CONFIRM_FRAMES = 3

PHONE_EVIDENCE_WINDOW = 2.00
SLEEPING_EVIDENCE_WINDOW = 2.50
CHEATING_EVIDENCE_WINDOW = 2.00
NOT_ATTENTIVE_EVIDENCE_WINDOW = 2.00

PHONE_MIN_AVERAGE_CONFIDENCE = 0.30
SLEEPING_MIN_AVERAGE_CONFIDENCE = 0.42
CHEATING_MIN_AVERAGE_CONFIDENCE = 0.40
NOT_ATTENTIVE_MIN_AVERAGE_CONFIDENCE = 0.38

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

# ------------------------------------------------------------
# DEMO / EXAM RELIABILITY SETTINGS
# These do not change the normal classroom live-camera thresholds above.
# ------------------------------------------------------------
DEMO_PERSON_CONFIDENCE = 0.18
DEMO_PERSON_IMGSZ = 768
DEMO_OBJECT_DETECTION_INTERVAL = 2  # run YOLOv8n person/phone pass every 2 demo frames
DEMO_BEHAVIOR_IMGSZ = 512
DEMO_FACE_RECOGNITION_INTERVAL = 8
DEMO_MAX_CATCHUP_FRAMES = 6
DEMO_UNKNOWN_CONFIRM_SECONDS = 3.00
DEMO_UNKNOWN_TRACK_TTL = 2.50

DEMO_FACE_DETECTION_CONFIDENCE = 0.35
DEMO_FACE_CANDIDATE_MIN_CONFIDENCE = 0.25
DEMO_FACE_CANDIDATE_MIN_MARGIN = 0.005
DEMO_FACE_CANDIDATE_CONFIRMATIONS = 2

EXAM_CROP_CONFIDENCE_LIVE = 0.06
EXAM_CROP_CONFIDENCE_DEMO = 0.22
EXAM_VOTE_WINDOW_SECONDS = 1.80
EXAM_CHEATING_MIN_SAMPLES_LIVE = 2
EXAM_CHEATING_MIN_SAMPLES_DEMO = 3
EXAM_CHEATING_MIN_RATIO_LIVE = 0.30
EXAM_CHEATING_MIN_RATIO_DEMO = 0.70
EXAM_CHEATING_MIN_AVG_LIVE = 0.18
EXAM_CHEATING_MIN_AVG_DEMO = 0.42
EXAM_CHEATING_IMMEDIATE_LIVE = 0.55


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


# ------------------------------------------------------------
# DEMO-ONLY OPEN-SET FACE RECOVERY
# ------------------------------------------------------------
# train_faces.py stores the original FaceNet embeddings in
# models/face_training_data.pkl as {"X": embeddings, "y": student_ids}.
# We use those embeddings only as a second verifier for difficult/far faces
# in prerecorded demo videos. Live recognition remains unchanged.

_demo_training_X_norm = None
_demo_training_y = None


def load_demo_training_embeddings():
    global _demo_training_X_norm, _demo_training_y

    _demo_training_X_norm = None
    _demo_training_y = None

    path = resolve_model_file("face_training_data.pkl")

    if not os.path.exists(path):
        print("DEMO FACE TRAINING DATA NOT FOUND:", path)
        return False

    try:
        data = joblib.load(path)

        if not isinstance(data, dict):
            return False

        X = data.get("X")
        y = data.get("y")

        if X is None or y is None:
            return False

        X = np.asarray(X, dtype=np.float32)
        y = np.asarray([str(v) for v in y], dtype=object)

        if X.ndim != 2 or X.shape[1] != 512 or len(X) != len(y):
            print("DEMO FACE TRAINING DATA INVALID:", X.shape, len(y))
            return False

        norms = np.linalg.norm(X, axis=1, keepdims=True)
        norms = np.maximum(norms, 1e-8)

        _demo_training_X_norm = X / norms
        _demo_training_y = y

        print(
            "Demo face embedding verifier loaded:",
            len(X),
            "samples for",
            len(np.unique(y)),
            "students",
        )
        return True

    except Exception as exc:
        print("DEMO FACE TRAINING DATA LOAD ERROR:", repr(exc))
        return False


load_demo_training_embeddings()


def demo_embedding_identity(face_image):
    """
    Demo-only open-set identity verifier.

    Returns a known student only when:
      1. multiple stored embeddings of the SAME student are similar,
      2. the best student is clearly better than the runner-up.

    This is safer than just lowering the SVM threshold globally.
    """
    if (
        face_image is None
        or face_image.size == 0
        or embedder is None
        or _demo_training_X_norm is None
        or _demo_training_y is None
    ):
        return "Unknown", 0.0, 0.0

    try:
        rgb = cv2.cvtColor(face_image, cv2.COLOR_BGR2RGB)
        resized = cv2.resize(
            rgb,
            (160, 160),
            interpolation=cv2.INTER_CUBIC,
        )

        embedding = embedder.embeddings([resized])
        embedding = np.asarray(embedding, dtype=np.float32).reshape(-1)

        if embedding.shape[0] != 512 or not np.all(np.isfinite(embedding)):
            return "Unknown", 0.0, 0.0

        norm = float(np.linalg.norm(embedding))
        if norm <= 1e-8:
            return "Unknown", 0.0, 0.0

        embedding = embedding / norm
        similarities = _demo_training_X_norm @ embedding

        student_scores = {}

        for sid in np.unique(_demo_training_y):
            idx = np.where(_demo_training_y == sid)[0]
            sims = similarities[idx]

            if len(sims) == 0:
                continue

            # Average the best few stored examples for robustness.
            top = np.sort(sims)[-min(4, len(sims)):]
            student_scores[str(sid)] = float(np.mean(top))

        if not student_scores:
            return "Unknown", 0.0, 0.0

        ordered = sorted(
            student_scores.items(),
            key=lambda item: item[1],
            reverse=True,
        )

        best_label, best_score = ordered[0]
        second_score = ordered[1][1] if len(ordered) > 1 else -1.0
        gap = best_score - second_score

        # Moderately tolerant because this path is already restricted to
        # prerecorded demo crops and still passes through temporal voting.
        if best_score >= 0.42 and gap >= 0.010:
            return best_label, best_score, gap

        return "Unknown", best_score, gap

    except Exception as exc:
        print("DEMO EMBEDDING ID ERROR:", repr(exc))
        return "Unknown", 0.0, 0.0


active_ai_session = {
    "is_running": False,
    "mode": None,
    "source_type": "camera",
    "source_path": None,
    "source_fps": 0.0,
    "cap": None,
    "student_stats": {},
    "tracker_to_student_map": {},
    "recognized_faces": [],
    "unknown_faces": [],
    "person_detections": [],
    "session_id": None,
    "started_at": None,
    "frame_counter": 0,
    "behavior_states": {},
    "object_detections": [],
    "last_object_detection_time": 0.0,
    "student_identity_cache": {},
    "exam_heuristic_state": {},
    "sleep_heuristic_state": {},
    "demo_face_votes": {},
    "demo_unknown_tracks": {},
    "exam_vote_history": {},
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
        while state["evidence"] and now - state["evidence"][0]["time"] > 2.50:
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



class ExamBehaviorStabilizer:
    """
    Stable exam-mode state machine.

    Normal state: non_cheating
    Alert state: cheating
    """

    def __init__(self):
        self.states = {}

    def reset(self):
        self.states.clear()

    def _state(self, student_id):
        sid = str(student_id)
        if sid not in self.states:
            self.states[sid] = {
                "current": "non_cheating",
                "confidence": 1.0,
                "history": deque(maxlen=40),
                "last_cheating": 0.0,
            }
        return self.states[sid]

    def update(self, student_id, raw_label, confidence, now):
        state = self._state(student_id)
        label = normalize_behavior(raw_label)
        confidence = float(confidence or 0.0)

        # Store only exam labels.
        if label in {"cheating", "non_cheating"}:
            state["history"].append({
                "label": label,
                "confidence": confidence,
                "time": now,
            })

        # Keep only recent evidence.
        while (
            state["history"]
            and now - state["history"][0]["time"] > 2.5
        ):
            state["history"].popleft()

        cheating_samples = [
            item
            for item in state["history"]
            if item["label"] == "cheating"
            and now - item["time"] <= CHEATING_EVIDENCE_WINDOW
        ]

        if cheating_samples:
            cheating_avg = (
                sum(item["confidence"] for item in cheating_samples)
                / len(cheating_samples)
            )
        else:
            cheating_avg = 0.0

        if (
            len(cheating_samples) >= CHEATING_CONFIRM_FRAMES
            and cheating_avg >= CHEATING_MIN_AVERAGE_CONFIDENCE
        ):
            state["current"] = "cheating"
            state["confidence"] = cheating_avg
            state["last_cheating"] = now
            return state["current"], state["confidence"]

        # Hold cheating briefly so one missed frame does not flicker.
        if (
            state["current"] == "cheating"
            and now - state["last_cheating"] <= ALERT_HOLD_SECONDS
        ):
            return state["current"], state["confidence"]

        non_samples = [
            item
            for item in state["history"]
            if item["label"] == "non_cheating"
            and now - item["time"] <= 1.0
        ]

        if non_samples:
            non_avg = (
                sum(item["confidence"] for item in non_samples)
                / len(non_samples)
            )
            state["current"] = "non_cheating"
            state["confidence"] = non_avg
        else:
            # No cheating confirmed = normal exam state.
            state["current"] = "non_cheating"
            state["confidence"] = 1.0

        return state["current"], state["confidence"]


exam_behavior_stabilizer = ExamBehaviorStabilizer()



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
            _yolo_cache[phone_path] = YOLO(phone_path)
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
    elif label == "non_cheating":
        stats["non_cheating_sec"] += elapsed
    elif label in {"attentive", "person"}:
        stats["attentive_sec"] += elapsed
    else:
        stats["not_attentive_sec"] += elapsed

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

        # Balanced fallback for known students:
        # keep an uncertain face Unknown unless the SVM's direct class agrees
        # AND the probability/margin are still reasonably strong.
        direct_prediction = face_svm.predict(embedding)
        if len(direct_prediction) > 0:
            direct_index = int(direct_prediction[0])
            direct_label = str(
                label_encoder.inverse_transform([direct_index])[0]
            )

            if (
                best_confidence >= 0.50
                and margin >= 0.03
                and direct_label == predicted_label
            ):
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


def update_unknown_face_cache(new_faces):
    now = time.time()
    current = [
        face for face in new_faces
        if face.get("student_id") == "Unknown"
    ]
    existing = [
        face for face in active_ai_session.get("unknown_faces", [])
        if now - face.get("last_seen", 0.0) <= 1.0
    ]
    active_ai_session["unknown_faces"] = current if current else existing
    return active_ai_session["unknown_faces"]


def get_current_unknown_faces():
    now = time.time()
    valid = [
        face for face in active_ai_session.get("unknown_faces", [])
        if now - face.get("last_seen", 0.0) <= 1.0
    ]
    active_ai_session["unknown_faces"] = valid
    return valid


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
        source_type = active_ai_session.get("source_type", "camera")

        person_conf = (
            DEMO_PERSON_CONFIDENCE
            if source_type == "demo"
            else PERSON_DETECTION_CONFIDENCE
        )

        detector_imgsz = (
            DEMO_PERSON_IMGSZ
            if source_type == "demo"
            else 640
        )

        results = model.track(
            frame,
            persist=True,
            tracker="bytetrack.yaml",
            conf=min(person_conf, OBJECT_PHONE_CONFIDENCE),
            classes=[0, 67],
            imgsz=detector_imgsz,
            iou=0.50,
            verbose=False,
        )
    except Exception as e:
        print("PERSON/PHONE OBJECT DETECTOR ERROR:", repr(e))
        return persons, phones

    for result in results:
        boxes = result.boxes
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
                    source_type = active_ai_session.get("source_type", "camera")
                    required_person_conf = (
                        DEMO_PERSON_CONFIDENCE
                        if source_type == "demo"
                        else PERSON_DETECTION_CONFIDENCE
                    )

                    if confidence < required_person_conf:
                        continue

                    # In demo videos, distant students can have smaller person
                    # boxes than the webcam case.
                    min_w = 32 if source_type == "demo" else MIN_PERSON_WIDTH
                    min_h = 60 if source_type == "demo" else MIN_PERSON_HEIGHT

                    if x2 - x1 < min_w or y2 - y1 < min_h:
                        continue

                    track_id = None
                    try:
                        if box.id is not None:
                            track_id = int(box.id[0])
                    except Exception:
                        track_id = None

                    persons.append({
                        "box": mapped,
                        "center": box_center(mapped),
                        "confidence": confidence,
                        "track_id": track_id,
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




def _demo_face_candidate(face_image):
    """
    Return the best SVM identity candidate even when normal one-frame
    recognition is not confident enough. Used only for repeated DEMO voting.
    """
    if (
        face_image is None
        or face_image.size == 0
        or embedder is None
        or face_svm is None
        or label_encoder is None
    ):
        return None, 0.0, 0.0

    try:
        rgb_face = cv2.cvtColor(face_image, cv2.COLOR_BGR2RGB)
        resized = cv2.resize(
            rgb_face,
            (160, 160),
            interpolation=cv2.INTER_CUBIC,
        )

        embedding = embedder.embeddings([resized])
        embedding = np.asarray(embedding, dtype=np.float32)

        if embedding.ndim == 1:
            embedding = np.expand_dims(embedding, axis=0)

        if (
            embedding.ndim != 2
            or embedding.shape[1] != 512
            or not np.all(np.isfinite(embedding))
        ):
            return None, 0.0, 0.0

        probabilities = np.asarray(
            face_svm.predict_proba(embedding)[0],
            dtype=float,
        )

        if probabilities.size == 0:
            return None, 0.0, 0.0

        order = np.argsort(probabilities)[::-1]
        best_index = int(order[0])
        best_conf = float(probabilities[best_index])
        second_conf = (
            float(probabilities[int(order[1])])
            if len(order) > 1
            else 0.0
        )

        margin = best_conf - second_conf
        label = str(
            label_encoder.inverse_transform([best_index])[0]
        )

        return label, best_conf, margin

    except Exception as exc:
        print("DEMO FACE CANDIDATE ERROR:", repr(exc))
        return None, 0.0, 0.0


def _demo_face_vote(person_box, label, confidence, margin, now):
    """
    Accept a difficult/far face only after the same candidate repeats on the
    same body. This protects genuine unknown people from one weak SVM guess.
    """
    if not label:
        return None, 0.0

    votes = active_ai_session.setdefault("demo_face_votes", {})

    best_key = None
    best_iou = 0.0

    for key, state in votes.items():
        old_box = state.get("person_box")
        if old_box is None:
            continue

        overlap = calculate_iou(person_box, old_box)
        if overlap > best_iou:
            best_iou = overlap
            best_key = key

    if best_key is None or best_iou < 0.20:
        best_key = str(uuid.uuid4())
        votes[best_key] = {
            "person_box": person_box,
            "samples": deque(maxlen=10),
            "last_seen": now,
        }

    state = votes[best_key]
    state["person_box"] = person_box
    state["last_seen"] = now
    state["samples"].append({
        "label": str(label),
        "confidence": float(confidence),
        "margin": float(margin),
        "time": now,
    })

    # Remove stale body/candidate tracks.
    for key in list(votes.keys()):
        if now - float(votes[key].get("last_seen", 0.0)) > 4.0:
            votes.pop(key, None)

    samples = [
        sample
        for sample in state["samples"]
        if now - float(sample["time"]) <= 3.5
    ]

    same = [
        sample
        for sample in samples
        if sample["label"] == str(label)
    ]

    if len(same) < DEMO_FACE_CANDIDATE_CONFIRMATIONS:
        return None, 0.0

    avg_conf = sum(s["confidence"] for s in same) / len(same)
    avg_margin = sum(s["margin"] for s in same) / len(same)

    if (
        avg_conf >= DEMO_FACE_CANDIDATE_MIN_CONFIDENCE
        and avg_margin >= DEMO_FACE_CANDIDATE_MIN_MARGIN
    ):
        return str(label), float(avg_conf)

    return None, 0.0


def recover_demo_faces_from_person_crops(frame, persons, existing_faces):
    """
    DEMO ONLY:
    Retry face detection/recognition inside each person's upper-body crop.

    This is especially important for students farther from the camera, whose
    faces are too small in the full-frame MTCNN pass.
    """
    if active_ai_session.get("source_type") != "demo":
        return []

    if detector is None or not persons:
        return []

    frame_h, frame_w = frame.shape[:2]
    now = time.time()
    recovered = []

    for person in persons:
        person_box = person["box"]

        # A good known face is already inside this person.
        if any(
            face.get("student_id") != "Unknown"
            and face.get("center") is not None
            and point_inside_box(face["center"], person_box)
            for face in existing_faces
        ):
            continue

        px1, py1, px2, py2 = person_box
        pw = max(1, px2 - px1)
        ph = max(1, py2 - py1)

        x1 = max(0, int(px1 - 0.08 * pw))
        x2 = min(frame_w, int(px2 + 0.08 * pw))
        y1 = max(0, int(py1 - 0.08 * ph))
        y2 = min(frame_h, int(py1 + 0.78 * ph))

        crop = frame[y1:y2, x1:x2]

        if crop.size == 0:
            continue

        ch, cw = crop.shape[:2]
        largest = max(ch, cw)

        if largest < 420:
            scale = 3.0
        elif largest < 700:
            scale = 2.2
        else:
            scale = 1.5

        enlarged = cv2.resize(
            crop,
            None,
            fx=scale,
            fy=scale,
            interpolation=cv2.INTER_CUBIC,
        )

        try:
            rgb = cv2.cvtColor(enlarged, cv2.COLOR_BGR2RGB)
            detections = detector.detect_faces(rgb)
        except Exception as exc:
            print("DEMO CROP FACE DETECTION ERROR:", repr(exc))
            continue

        best_recovered = None

        for detection in detections:
            det_conf = float(detection.get("confidence", 0.0))
            if det_conf < DEMO_FACE_DETECTION_CONFIDENCE:
                continue

            raw_box = detection.get("box")
            if not raw_box or len(raw_box) < 4:
                continue

            dx, dy, dw, dh = raw_box

            fx1 = x1 + int(dx / scale)
            fy1 = y1 + int(dy / scale)
            fx2 = x1 + int((dx + dw) / scale)
            fy2 = y1 + int((dy + dh) / scale)

            face_box = clamp_box(
                (fx1, fy1, fx2, fy2),
                frame_w,
                frame_h,
            )

            if face_box is None:
                continue

            ax1, ay1, ax2, ay2 = face_box

            if ax2 - ax1 < 14 or ay2 - ay1 < 14:
                continue

            face_crop = frame[ay1:ay2, ax1:ax2]

            # First apply the exact original recognition method.
            student_id, identity_conf = recognize_face(face_crop)

            # Second verifier for small/far trained faces:
            # compare against the original stored FaceNet training embeddings.
            if student_id == "Unknown":
                emb_label, emb_score, emb_gap = demo_embedding_identity(
                    face_crop
                )

                if emb_label != "Unknown":
                    voted_id, voted_conf = _demo_face_vote(
                        person_box,
                        emb_label,
                        emb_score,
                        max(emb_gap, 0.03),
                        now,
                    )

                    if voted_id is not None:
                        student_id = voted_id
                        identity_conf = voted_conf

            # Final fallback: repeated SVM candidate voting.
            if student_id == "Unknown":
                label, conf, margin = _demo_face_candidate(face_crop)

                voted_id, voted_conf = _demo_face_vote(
                    person_box,
                    label,
                    conf,
                    margin,
                    now,
                )

                if voted_id is not None:
                    student_id = voted_id
                    identity_conf = voted_conf

            item = {
                "box": face_box,
                "center": box_center(face_box),
                "student_id": student_id,
                "confidence": float(identity_conf),
                "face_detection_confidence": det_conf,
                "area": box_area(face_box),
                "last_seen": now,
                "source": "demo_person_crop_face",
            }

            if best_recovered is None:
                best_recovered = item
            elif (
                best_recovered.get("student_id") == "Unknown"
                and student_id != "Unknown"
            ):
                best_recovered = item
            elif (
                student_id == best_recovered.get("student_id")
                and identity_conf > best_recovered.get("confidence", 0.0)
            ):
                best_recovered = item

        if best_recovered is not None:
            recovered.append(best_recovered)

    return recovered


def match_faces_to_persons_demo(persons, faces):
    """
    DEMO-only one-to-one face/person assignment.

    A large foreground person box can contain a background student's face.
    The original person->face search can therefore select the wrong face.
    Here each face chooses the most plausible person, and each person/ID is
    used once.
    """
    if not persons or not faces:
        return []

    candidate_pairs = []

    for face in faces:
        if face.get("student_id") == "Unknown":
            continue

        center = face.get("center")
        face_box = face.get("box")

        if center is None or face_box is None:
            continue

        for person_index, person in enumerate(persons):
            person_box = person["box"]

            if not point_inside_box(center, person_box):
                continue

            px1, py1, px2, py2 = person_box
            person_h = max(1.0, float(py2 - py1))
            person_w = max(1.0, float(px2 - px1))

            rel_x = (center[0] - px1) / person_w
            rel_y = (center[1] - py1) / person_h

            # A face should normally be in the upper/central part of its person.
            if not (0.10 <= rel_x <= 0.90 and 0.02 <= rel_y <= 0.62):
                continue

            # Prefer smaller/tighter person boxes around the face.
            score = (
                box_area(person_box)
                - 200000.0 * float(face.get("confidence", 0.0))
            )

            candidate_pairs.append(
                (
                    score,
                    person_index,
                    face,
                )
            )

    candidate_pairs.sort(key=lambda item: item[0])

    used_persons = set()
    used_students = set()
    students = []

    for _, person_index, face in candidate_pairs:
        sid = str(face["student_id"])

        if person_index in used_persons or sid in used_students:
            continue

        person = persons[person_index]

        students.append({
            "person_box": person["box"],
            "person_confidence": person.get("confidence", 0.0),
            "face_box": face["box"],
            "student_id": sid,
            "face_confidence": float(face.get("confidence", 0.0)),
            "center": person["center"],
        })

        used_persons.add(person_index)
        used_students.add(sid)

    return students


def get_demo_unidentified_people(persons, known_students, now):
    """
    DEMO ONLY:
    Every person should eventually have a visible frame.

    If a person is not matched to a known student, keep an IoU-based unknown
    track. Show UNKNOWN only after it remains unmatched long enough, preventing
    momentary face-recognition misses from flashing UNKNOWN.
    """
    if active_ai_session.get("source_type") != "demo":
        return []

    tracks = active_ai_session.setdefault("demo_unknown_tracks", {})
    known_boxes = [student["person_box"] for student in known_students]

    # Also include recently verified body locations. A trained student should
    # not flash UNKNOWN just because one demo face frame is weak.
    for cached in active_ai_session.get("student_identity_cache", {}).values():
        cached_box = cached.get("person_box")
        last_person_seen = float(cached.get("last_person_seen", 0.0))

        if (
            cached_box is not None
            and now - last_person_seen <= 4.0
        ):
            known_boxes.append(cached_box)

    unmatched = []

    for person in persons:
        box = person["box"]

        if any(calculate_iou(box, known_box) > 0.25 for known_box in known_boxes):
            continue

        unmatched.append(person)

    seen_keys = set()

    for person in unmatched:
        box = person["box"]

        best_key = None
        best_iou = 0.0

        for key, state in tracks.items():
            old_box = state.get("box")
            if old_box is None:
                continue

            overlap = calculate_iou(box, old_box)
            if overlap > best_iou:
                best_iou = overlap
                best_key = key

        if best_key is None or best_iou < 0.20:
            best_key = str(uuid.uuid4())
            tracks[best_key] = {
                "box": box,
                "first_seen": now,
                "last_seen": now,
                "confidence": person.get("confidence", 0.0),
            }
        else:
            tracks[best_key]["box"] = box
            tracks[best_key]["last_seen"] = now
            tracks[best_key]["confidence"] = person.get("confidence", 0.0)

        seen_keys.add(best_key)

    for key in list(tracks.keys()):
        if now - float(tracks[key].get("last_seen", 0.0)) > DEMO_UNKNOWN_TRACK_TTL:
            tracks.pop(key, None)

    result = []

    for key, state in tracks.items():
        if key not in seen_keys:
            continue

        if now - float(state.get("first_seen", now)) < DEMO_UNKNOWN_CONFIRM_SECONDS:
            continue

        # Recheck against current known boxes before drawing.
        if any(calculate_iou(state["box"], kb) > 0.20 for kb in known_boxes):
            continue

        result.append({
            "person_box": state["box"],
            "person_confidence": state.get("confidence", 0.0),
            "face_box": None,
        })

    return result


# ============================================================
# PERSISTENT STUDENT IDENTITY
# ============================================================

def _person_match_score(old_box, new_box):
    """Lower score means a better body match."""
    iou = calculate_iou(old_box, new_box)

    ocx, ocy = box_center(old_box)
    ncx, ncy = box_center(new_box)

    distance = ((ocx - ncx) ** 2 + (ocy - ncy) ** 2) ** 0.5

    ow = max(1, old_box[2] - old_box[0])
    oh = max(1, old_box[3] - old_box[1])
    scale = max(100.0, (ow * ow + oh * oh) ** 0.5)

    # Reject a clearly different person.  This is only the fallback when a
    # stable ByteTrack person ID is unavailable.  Keep it conservative so an
    # identity cannot jump to a nearby student in a crowded scene.
    if iou < 0.05 and distance > scale * 0.50:
        return None

    return (1.0 - iou) + 0.50 * (distance / scale)


def update_persistent_students(persons, recognized_faces, now):
    """
    Face recognition is used to VERIFY identity.
    After that, the verified student ID can stay attached to the same
    detected body while the face is temporarily hidden.

    This is important for sleeping/head-on-desk situations.
    """
    cache = active_ai_session.setdefault("student_identity_cache", {})

    if active_ai_session.get("source_type") == "demo":
        fresh_students = match_faces_to_persons_demo(
            persons,
            recognized_faces,
        )
    else:
        # Preserve the original working live-camera association.
        fresh_students = match_faces_to_persons(
            persons,
            recognized_faces,
        )

    used_person_indices = set()

    # Fresh face match has highest authority.
    for student in fresh_students:
        sid = str(student["student_id"])

        best_idx = None
        best_iou = -1.0

        for idx, person in enumerate(persons):
            iou = calculate_iou(student["person_box"], person["box"])
            if iou > best_iou:
                best_iou = iou
                best_idx = idx

        if best_idx is not None:
            used_person_indices.add(best_idx)

        cached = dict(student)
        if best_idx is not None:
            cached["person_track_id"] = persons[best_idx].get("track_id")
        cached["last_face_seen"] = now
        cached["last_person_seen"] = now
        cached["identity_source"] = "face"

        cache[sid] = cached

    # Continue following the body when the face disappears.
    for sid, cached in list(cache.items()):
        if any(str(s["student_id"]) == sid for s in fresh_students):
            continue

        last_face_seen = float(cached.get("last_face_seen", 0.0))
        if now - last_face_seen > IDENTITY_HOLD_SECONDS:
            continue

        old_box = cached.get("person_box")
        if old_box is None:
            continue

        best_idx = None
        best_score = None

        # Prefer the same ByteTrack PERSON id.  This prevents an identified
        # student from being transferred to a neighbouring body box.
        cached_track_id = cached.get("person_track_id")
        if cached_track_id is not None:
            for idx, person in enumerate(persons):
                if idx in used_person_indices:
                    continue
                if person.get("track_id") == cached_track_id:
                    best_idx = idx
                    break

        # If ByteTrack temporarily has no ID, use conservative spatial matching.
        if best_idx is None:
            for idx, person in enumerate(persons):
                if idx in used_person_indices:
                    continue

                score = _person_match_score(old_box, person["box"])
                if score is None:
                    continue

                if best_score is None or score < best_score:
                    best_score = score
                    best_idx = idx

        if best_idx is not None:
            person = persons[best_idx]
            used_person_indices.add(best_idx)

            cached["person_box"] = person["box"]
            cached["person_confidence"] = person["confidence"]
            cached["center"] = person["center"]
            if person.get("track_id") is not None:
                cached["person_track_id"] = person.get("track_id")
            cached["last_person_seen"] = now
            cached["identity_source"] = "body_track"

    active_students = []

    for sid, cached in list(cache.items()):
        if now - float(cached.get("last_face_seen", 0.0)) > IDENTITY_HOLD_SECONDS:
            cache.pop(sid, None)
            continue

        # Body must still be present recently.
        body_hold = (
            3.5
            if active_ai_session.get("source_type") == "demo"
            else 2.0
        )

        if now - float(cached.get("last_person_seen", 0.0)) <= body_hold:
            active_students.append({
                "person_box": cached["person_box"],
                "person_confidence": cached.get("person_confidence", 0.0),
                "face_box": cached.get("face_box", cached["person_box"]),
                "student_id": sid,
                "face_confidence": cached.get("face_confidence", 0.0),
                "center": cached.get("center", box_center(cached["person_box"])),
                "identity_source": cached.get("identity_source", "body_track"),
            })

    return active_students


def match_unknown_faces_to_persons(persons, unknown_faces, known_students):
    unknown_people = []
    known_boxes = [s["person_box"] for s in known_students]

    for person in persons:
        person_box = person["box"]

        if any(calculate_iou(person_box, kb) > 0.45 for kb in known_boxes):
            continue

        faces = [
            f for f in unknown_faces
            if point_inside_box(f["center"], person_box)
        ]
        if not faces:
            continue

        faces.sort(
            key=lambda f: (
                f.get("face_detection_confidence", 0.0),
                f.get("area", 0),
            ),
            reverse=True,
        )

        unknown_people.append({
            "person_box": person_box,
            "face_box": faces[0]["box"],
        })

    return unknown_people


def draw_unknown_person_boxes(frame, unknown_people):
    for item in unknown_people:
        x1, y1, x2, y2 = item["person_box"]
        color = (0, 165, 255)
        label = "UNKNOWN"

        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 3)
        cv2.rectangle(
            frame,
            (x1, max(0, y1 - 32)),
            (min(frame.shape[1] - 1, x1 + 150), y1),
            color,
            -1,
        )
        cv2.putText(
            frame,
            label,
            (x1 + 6, y1 - 8),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.70,
            (255, 255, 255),
            2,
            cv2.LINE_AA,
        )


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




def _exam_heuristic_state(student_id):
    states = active_ai_session.setdefault("exam_heuristic_state", {})
    sid = str(student_id)

    if sid not in states:
        states[sid] = {
            "head_turn_count": 0,
            "face_missing_since": None,
            "last_suspicious": 0.0,
        }

    return states[sid]


def exam_head_movement_evidence(student, now):
    """
    Return (is_suspicious, score, reason).

    Hybrid fallback for the Exam Proctor preset:
      - strong lateral face displacement relative to the body
      - or the face becomes hidden for a sustained period while the body
        remains tracked after prior identity verification

    This is intentionally conservative and only runs in exam mode.
    """
    sid = str(student["student_id"])
    state = _exam_heuristic_state(sid)

    person_box = student["person_box"]
    px1, py1, px2, py2 = person_box
    person_width = max(1.0, float(px2 - px1))
    person_center_x = (px1 + px2) / 2.0

    identity_source = student.get("identity_source", "face")

    # Face is currently visible.
    if identity_source == "face":
        state["face_missing_since"] = None

        face_box = student.get("face_box")
        if face_box is None:
            state["head_turn_count"] = max(0, state["head_turn_count"] - 1)
            return False, 0.0, "no_face_box"

        fx1, fy1, fx2, fy2 = face_box
        face_center_x = (fx1 + fx2) / 2.0

        lateral_ratio = abs(face_center_x - person_center_x) / person_width

        if lateral_ratio >= EXAM_HEAD_TURN_RATIO:
            state["head_turn_count"] += 1
        else:
            state["head_turn_count"] = max(0, state["head_turn_count"] - 1)

        if state["head_turn_count"] >= EXAM_HEAD_TURN_CONFIRM_FRAMES:
            state["last_suspicious"] = now
            score = min(0.95, 0.55 + lateral_ratio)
            return True, score, f"lateral_head_turn:{lateral_ratio:.2f}"

        if (
            float(state.get("last_suspicious", 0.0)) > 0.0
            and now - float(state.get("last_suspicious", 0.0))
            <= EXAM_HEURISTIC_HOLD_SECONDS
        ):
            return True, 0.70, "confirmed_head_turn_hold"

        return False, lateral_ratio, "face_centered"

    # Face-hidden alone is NOT cheating. However, if a sustained lateral
    # head turn was already confirmed less than a moment ago, keep that
    # confirmed signal briefly while MTCNN temporarily loses the face.
    if state["face_missing_since"] is None:
        state["face_missing_since"] = now

    if (
        float(state.get("last_suspicious", 0.0)) > 0.0
        and now - float(state.get("last_suspicious", 0.0))
        <= EXAM_HEURISTIC_HOLD_SECONDS
    ):
        return True, 0.72, "confirmed_head_turn_hold"

    return False, 0.0, "face_hidden_no_cheating_rule"


def fuse_exam_model_and_head_movement(raw_exam_behaviors, students, now):
    """
    LIVE CAMERA EXAM fallback only.

    Keep exam_model.pt as the primary detector. If the model misses a
    sustained, clearly lateral head turn, use repeated face/body geometry
    as supplementary cheating evidence.

    Demo video is intentionally excluded from this heuristic.
    """
    fused = dict(raw_exam_behaviors)

    if active_ai_session.get("source_type", "camera") != "camera":
        return fused

    for student in students:
        sid = student["student_id"]
        raw = fused.get(
            sid,
            {
                "label": "non_cheating",
                "box": student["person_box"],
                "confidence": 1.0,
                "track_id": None,
                "source": "exam_default",
            },
        )

        # If YOLO already says cheating, keep it.
        if normalize_behavior(raw.get("label")) == "cheating":
            continue

        suspicious, score, reason = exam_head_movement_evidence(
            student,
            now,
        )

        if suspicious:
            fused[sid] = {
                "label": "cheating",
                "box": student["person_box"],
                "confidence": max(CHEATING_RAW_CONFIDENCE, float(score)),
                "track_id": raw.get("track_id"),
                "source": f"exam_head_movement:{reason}",
            }

            print(
                f"LIVE EXAM HEURISTIC: student={sid}, "
                f"cheating_score={score:.3f}, reason={reason}"
            )

    return fused



def _sleep_heuristic_state(student_id):
    states = active_ai_session.setdefault("sleep_heuristic_state", {})
    sid = str(student_id)

    if sid not in states:
        states[sid] = {
            "face_missing_since": None,
            "low_head_count": 0,
            "last_sleep_signal": 0.0,
        }

    return states[sid]


def classroom_sleeping_evidence(student, now):
    """
    Return (is_sleeping, score, reason).

    Intended for the classroom preset only.

    Sleeping evidence is produced when:
      1. A previously verified student's face disappears while the body
         remains tracked for a short continuous period, OR
      2. The visible face/head is very low inside the person's body box.

    This supplements classroom_model.pt rather than replacing it.
    """
    sid = str(student["student_id"])
    state = _sleep_heuristic_state(sid)

    person_box = student["person_box"]
    px1, py1, px2, py2 = person_box
    person_height = max(1.0, float(py2 - py1))

    identity_source = student.get("identity_source", "face")

    # --------------------------------------------------------
    # Case 1: face currently visible
    # --------------------------------------------------------
    if identity_source == "face":
        state["face_missing_since"] = None

        face_box = student.get("face_box")
        if face_box is None:
            state["low_head_count"] = 0
            state["last_sleep_signal"] = 0.0
            return False, 0.0, "no_face_box"

        fx1, fy1, fx2, fy2 = face_box
        face_center_y = (fy1 + fy2) / 2.0
        head_low_ratio = (face_center_y - py1) / person_height

        # Visible upright faces must not become sleeping.
        if head_low_ratio < SLEEP_HEAD_LOW_RATIO:
            state["low_head_count"] = 0
            state["last_sleep_signal"] = 0.0
            return False, head_low_ratio, "visible_upright"

        state["low_head_count"] += 1

        if state["low_head_count"] >= 4:
            state["last_sleep_signal"] = now
            score = min(
                0.90,
                SLEEP_HEURISTIC_CONFIDENCE
                + max(0.0, head_low_ratio - SLEEP_HEAD_LOW_RATIO),
            )
            return True, score, f"head_very_low:{head_low_ratio:.2f}"

        return False, head_low_ratio, "head_low_not_confirmed"

    # --------------------------------------------------------
    # Case 2: face hidden, but the already-identified body is
    # still tracked. This is the common head-on-desk case.
    # --------------------------------------------------------
    if state["face_missing_since"] is None:
        state["face_missing_since"] = now

    missing_for = now - state["face_missing_since"]

    # When a previously VERIFIED student's face disappears while the same
    # body is still being tracked for a sustained period, treat it as a
    # sleeping fallback. Phone-use is filtered before this function is used.
    if missing_for >= SLEEP_FACE_MISSING_SECONDS:
        state["last_sleep_signal"] = now
        score = min(
            0.82,
            SLEEP_HEURISTIC_CONFIDENCE
            + min(missing_for, 2.0) * 0.06,
        )
        return True, score, f"verified_face_hidden:{missing_for:.2f}s"

    return False, 0.0, "face_temporarily_hidden"


def validate_native_sleeping(student, raw_label):
    """Suppress obvious native YOLO sleeping false positives."""
    if normalize_behavior(raw_label) != "sleeping":
        return True

    if student.get("identity_source") != "face":
        return True

    face_box = student.get("face_box")
    person_box = student.get("person_box")
    if face_box is None or person_box is None:
        return True

    px1, py1, px2, py2 = person_box
    fx1, fy1, fx2, fy2 = face_box

    person_height = max(1.0, float(py2 - py1))
    face_center_y = (fy1 + fy2) / 2.0
    head_low_ratio = (face_center_y - py1) / person_height

    return head_low_ratio >= 0.58


def fuse_classroom_sleeping(
    raw_student_behaviors,
    students,
    physical_phone_assignments,
    now,
):
    """
    Fuse classroom_model.pt output with a posture/face-loss sleeping fallback.

    Important:
    - A real physical phone near the student prevents the sleeping fallback
      from overriding phone_use.
    - Native YOLO sleeping remains valid and is kept.
    """
    fused = dict(raw_student_behaviors)

    for student in students:
        sid = student["student_id"]

        raw = fused.get(
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

        raw_label = normalize_behavior(raw.get("label", "attentive"))

        # Never reinterpret an actual phone-use event as sleeping.
        if sid in physical_phone_assignments or raw_label == "phone_use":
            continue

        # Native sleeping must also be posture-plausible.
        if raw_label == "sleeping":
            source_type = active_ai_session.get("source_type", "camera")

            if source_type == "demo":
                raw_conf = float(raw.get("confidence", 0.0))

                face_box = student.get("face_box")
                person_box = student.get("person_box")
                identity_source = student.get("identity_source", "face")

                posture_ok = False

                if identity_source == "face" and face_box is not None and person_box is not None:
                    px1, py1, px2, py2 = person_box
                    fx1, fy1, fx2, fy2 = face_box
                    person_h = max(1.0, float(py2 - py1))
                    face_center_y = (fy1 + fy2) / 2.0
                    head_low_ratio = (face_center_y - py1) / person_h

                    # Writing students often look down. Require a much lower
                    # head position in demo video before accepting sleeping.
                    posture_ok = head_low_ratio >= 0.68

                elif identity_source == "body_track":
                    # If the face is genuinely hidden, native YOLO sleeping can
                    # still be accepted, but require stronger confidence.
                    posture_ok = raw_conf >= 0.55

                if not (posture_ok and raw_conf >= 0.50):
                    fused[sid] = {
                        "label": "attentive",
                        "box": student["person_box"],
                        "priority": live_behavior_priority("attentive"),
                        "confidence": 1.0,
                        "source": "demo_sleep_false_positive_suppressed",
                        "track_id": raw.get("track_id"),
                    }
                    continue

                # Strong native sleeping + plausible posture: keep it.
                continue

            # LIVE CAMERA: preserve the original working logic.
            if validate_native_sleeping(student, raw_label):
                continue

            fused[sid] = {
                "label": "attentive",
                "box": student["person_box"],
                "priority": live_behavior_priority("attentive"),
                "confidence": 1.0,
                "source": "sleep_false_positive_suppressed",
                "track_id": raw.get("track_id"),
            }
            print(
                f"SLEEP SUPPRESSED: student={sid}, "
                "reason=face_visible_upright"
            )
            continue

        # DEMO: do not manufacture sleeping merely because a face is lost.
        # LIVE: keep the original head-down fallback that already works.
        if active_ai_session.get("source_type") == "demo":
            is_sleeping, score, reason = False, 0.0, "demo_no_sleep_heuristic"
        else:
            is_sleeping, score, reason = classroom_sleeping_evidence(
                student,
                now,
            )

        if is_sleeping:
            fused[sid] = {
                "label": "sleeping",
                "box": student["person_box"],
                "priority": live_behavior_priority("sleeping"),
                "confidence": max(SLEEPING_RAW_CONFIDENCE, float(score)),
                "source": f"sleep_posture_fallback:{reason}",
                "track_id": raw.get("track_id"),
            }

            print(
                f"SLEEP HEURISTIC: student={sid}, "
                f"score={score:.3f}, reason={reason}"
            )

    return fused



def detect_exam_student_crop_behaviors(frame, exam_model, students, confidence):
    """
    Exam-only second pass.

    Each recognized student's body is analyzed separately, so:
      * a small cheating action has more pixels,
      * a behavior cannot easily be assigned to a neighboring student.
    """
    if not students:
        return []

    frame_h, frame_w = frame.shape[:2]
    detections = []

    for student in students:
        source_type = active_ai_session.get("source_type", "camera")

        if source_type == "camera":
            # Live exam: include more shoulder/head/hand context.
            # This helps the exam model see head turns, side glances,
            # hand movement and nearby cheating cues.
            crop_box = expand_box(
                student["person_box"],
                frame_w,
                frame_h,
                left=0.16,
                right=0.16,
                top=0.10,
                bottom=0.12,
            )
        else:
            # Preserve the already-working demo crop.
            crop_box = expand_box(
                student["person_box"],
                frame_w,
                frame_h,
                left=0.05,
                right=0.05,
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
            crop_imgsz = (
                704
                if active_ai_session.get("source_type") == "camera"
                else 448
            )

            results = exam_model.predict(
                crop,
                conf=confidence,
                imgsz=crop_imgsz,
                iou=0.45,
                verbose=False,
            )
        except Exception as exc:
            print("EXAM STUDENT CROP ERROR:", repr(exc))
            continue

        best_by_label = {}

        for result in results:
            if result.boxes is None:
                continue

            for box in result.boxes:
                try:
                    cls_id = int(box.cls[0])
                    names = exam_model.names
                    raw_label = names[cls_id] if cls_id in names else ""
                    label = normalize_behavior(raw_label)

                    if label not in {"cheating", "non_cheating"}:
                        continue

                    conf = float(box.conf[0]) if box.conf is not None else 0.0

                    if conf < confidence:
                        continue

                    bx1, by1, bx2, by2 = box.xyxy[0].tolist()

                    mapped = clamp_box(
                        (
                            x1 + bx1,
                            y1 + by1,
                            x1 + bx2,
                            y1 + by2,
                        ),
                        frame_w,
                        frame_h,
                    )

                    if mapped is None:
                        continue

                    previous = best_by_label.get(label)

                    if previous is None or conf > previous["confidence"]:
                        best_by_label[label] = {
                            "box": mapped,
                            "label": label,
                            "confidence": conf,
                            "track_id": None,
                            "student_hint": student["student_id"],
                            "source": "exam_student_crop",
                        }

                except Exception:
                    continue

        detections.extend(best_by_label.values())

    return detections


def _choose_exam_observation_for_student(
    student,
    behavior_detections,
):
    """
    Choose one raw exam observation for one student.

    LIVE camera:
      - cheating is allowed through when the exam model repeatedly produces
        even moderate cheating evidence.
      - this improves cheating recall.

    DEMO video:
      - non_cheating wins unless cheating is clearly stronger.
      - this reduces false cheating in multi-student prerecorded scenes.
    """
    sid = str(student["student_id"])
    source_type = active_ai_session.get("source_type", "camera")

    crop_candidates = []
    full_candidates = []

    for detection in behavior_detections:
        label = normalize_behavior(detection.get("label"))
        confidence = float(detection.get("confidence", 0.0))

        if label not in {"cheating", "non_cheating"}:
            continue

        hint = detection.get("student_hint")

        if hint is not None:
            if str(hint) == sid:
                crop_candidates.append(detection)
            continue

        matched = find_best_student_for_behavior(
            detection["box"],
            label,
            [student],
            None,
        )

        if matched is not None:
            full_candidates.append(detection)

    # Student crop is much safer than full-frame assignment.
    candidates = crop_candidates if crop_candidates else full_candidates

    if not candidates:
        return {
            "label": None,
            "box": student["person_box"],
            "confidence": 0.0,
            "track_id": None,
            "source": "no_observation",
        }

    best_cheating = None
    best_normal = None

    for candidate in candidates:
        label = normalize_behavior(candidate["label"])
        conf = float(candidate["confidence"])

        if label == "cheating":
            if best_cheating is None or conf > float(best_cheating["confidence"]):
                best_cheating = candidate
        else:
            if best_normal is None or conf > float(best_normal["confidence"]):
                best_normal = candidate

    if best_cheating is not None and best_normal is not None:
        cheating_conf = float(best_cheating["confidence"])
        normal_conf = float(best_normal["confidence"])

        if source_type == "camera":
            # Live exam: do not throw away moderate cheating evidence merely
            # because non_cheating is slightly stronger in the same frame.
            # Temporal voting below decides whether it is real.
            if cheating_conf >= 0.10:
                best = best_cheating
            else:
                best = best_normal
        else:
            # Demo: require cheating to clearly beat non_cheating.
            if cheating_conf >= max(0.30, normal_conf + 0.08):
                best = best_cheating
            else:
                best = best_normal

    elif best_cheating is not None:
        cheating_conf = float(best_cheating["confidence"])

        if source_type == "camera":
            best = best_cheating if cheating_conf >= 0.10 else None
        else:
            best = best_cheating if cheating_conf >= 0.30 else None

        if best is None:
            return {
                "label": None,
                "box": student["person_box"],
                "confidence": 0.0,
                "track_id": None,
                "source": "no_observation",
            }

    else:
        best = best_normal

    return {
        "label": normalize_behavior(best["label"]),
        "box": best["box"],
        "confidence": float(best["confidence"]),
        "track_id": best.get("track_id"),
        "source": best.get("source", "exam_model"),
    }


def stabilize_exam_model_votes(raw_exam_behaviors, students, now):
    """
    Model-only temporal exam decision.

    IMPORTANT:
      * Only real exam_model.pt observations enter the vote history.
      * A missed detection is NOT converted into a synthetic 1.0 non_cheating vote.
      * Existing live/demo thresholds are preserved.
    """
    histories = active_ai_session.setdefault("exam_vote_history", {})
    source_type = active_ai_session.get("source_type", "camera")

    if source_type == "demo":
        min_samples = EXAM_CHEATING_MIN_SAMPLES_DEMO
        min_ratio = EXAM_CHEATING_MIN_RATIO_DEMO
        min_avg = EXAM_CHEATING_MIN_AVG_DEMO
    else:
        min_samples = EXAM_CHEATING_MIN_SAMPLES_LIVE
        min_ratio = EXAM_CHEATING_MIN_RATIO_LIVE
        min_avg = EXAM_CHEATING_MIN_AVG_LIVE

    final = {}

    for student in students:
        sid = str(student["student_id"])
        raw = raw_exam_behaviors.get(student["student_id"])

        history = histories.setdefault(sid, deque(maxlen=40))

        raw_label = None
        raw_confidence = 0.0
        raw_box = student["person_box"]
        raw_source = "no_observation"
        raw_track_id = None

        if raw is not None:
            raw_box = raw.get("box", student["person_box"])
            raw_source = raw.get("source", "exam_model")
            raw_track_id = raw.get("track_id")

            value = raw.get("label")
            if value is not None:
                normalized = normalize_behavior(value)
                if normalized in {"cheating", "non_cheating"}:
                    raw_label = normalized
                    raw_confidence = float(raw.get("confidence", 0.0))

        # Add ONLY a real model observation.
        if raw_label in {"cheating", "non_cheating"}:
            history.append({
                "label": raw_label,
                "confidence": raw_confidence,
                "time": now,
            })

        while (
            history
            and now - float(history[0]["time"]) > EXAM_VOTE_WINDOW_SECONDS
        ):
            history.popleft()

        recent = list(history)
        cheating_samples = [
            item for item in recent if item["label"] == "cheating"
        ]
        normal_samples = [
            item for item in recent if item["label"] == "non_cheating"
        ]

        total = len(cheating_samples) + len(normal_samples)
        cheating_ratio = (
            len(cheating_samples) / total if total > 0 else 0.0
        )
        cheating_avg = (
            sum(item["confidence"] for item in cheating_samples)
            / len(cheating_samples)
            if cheating_samples
            else 0.0
        )

        strong_live_cheating = (
            source_type == "camera"
            and raw_label == "cheating"
            and raw_confidence >= EXAM_CHEATING_IMMEDIATE_LIVE
        )

        if strong_live_cheating:
            # A very strong current live-camera cheating prediction can alert
            # immediately; moderate predictions still require temporal evidence.
            final_label = "cheating"
            final_conf = raw_confidence
        elif (
            len(cheating_samples) >= min_samples
            and cheating_ratio >= min_ratio
            and cheating_avg >= min_avg
        ):
            final_label = "cheating"
            final_conf = cheating_avg
        else:
            final_label = "non_cheating"
            final_conf = (
                sum(item["confidence"] for item in normal_samples)
                / len(normal_samples)
                if normal_samples
                else 0.0
            )

        final[student["student_id"]] = {
            "label": final_label,
            "confidence": float(final_conf),
            "phone_state": None,
            "box": raw_box,
            "source": raw_source,
            "track_id": raw_track_id,
        }

        print(
            f"FINAL EXAM BEHAVIOR: student={sid}, "
            f"behavior={final_label}, conf={final_conf:.3f}, "
            f"raw={raw_label}:{raw_confidence:.3f}, "
            f"samples={len(recent)}, cheating_ratio={cheating_ratio:.2f}"
        )

    return final

def assign_exam_behaviors_to_students(behavior_detections, students):
    result = {}

    for student in students:
        result[student["student_id"]] = _choose_exam_observation_for_student(
            student,
            behavior_detections,
        )

    return result


def stabilize_exam_behaviors(raw_exam_behaviors, students, now):
    final = {}

    for student in students:
        sid = student["student_id"]

        raw = raw_exam_behaviors.get(
            sid,
            {
                "label": "non_cheating",
                "confidence": 1.0,
                "box": student["person_box"],
                "track_id": None,
                "source": "exam_default",
            },
        )

        final_label, final_confidence = exam_behavior_stabilizer.update(
            sid,
            raw["label"],
            raw["confidence"],
            now,
        )

        final[sid] = {
            "label": final_label,
            "confidence": final_confidence,
            "phone_state": None,
            "box": raw.get("box", student["person_box"]),
            "source": raw.get("source", "exam_default"),
            "track_id": raw.get("track_id"),
        }

        print(
            f"FINAL EXAM BEHAVIOR: student={sid}, "
            f"behavior={final_label}, "
            f"conf={final_confidence:.3f}, "
            f"raw={raw['label']}:{float(raw['confidence']):.3f}"
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

    if DRAW_FACE_DEBUG_BOX and student.get("identity_source") == "face":
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
    source_type = active_ai_session.get("source_type", "camera")
    source_fps = float(active_ai_session.get("source_fps", 0.0) or 0.0)
    frame_interval = (1.0 / source_fps) if source_type == "demo" and source_fps > 0 else 0.0
    print("Loading behavior YOLO model...")

    try:
        behavior_yolo = get_yolo_model(mode)
        phone_yolo = None  # classroom_model.pt already contains phone_use
    except Exception as e:
        print("YOLO LOAD ERROR:", repr(e))
        active_ai_session["is_running"] = False
        return

    print("AI VIDEO STREAM STARTED")
    print("INPUT SOURCE:", source_type.upper())
    print("MAIN STUDENT BOX: YOLO PERSON DETECTION")
    print("FACE BOX: recognition + UNKNOWN support")
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
    if mode == "classroom":
        print("ACTIVE PRESET: CLASSROOM")
        print("CLASSROOM BEHAVIORS: attentive, not_attentive, phone_use, sleeping")
        print("PHONE SOURCES: classroom_model.pt + yolov8n cell-phone class")
    else:
        print("ACTIVE PRESET: EXAM")
        print("EXAM BEHAVIORS: cheating, non_cheating")
    print("OBJECT DETECTOR INTERVAL:", OBJECT_DETECTION_INTERVAL)
    print("PHYSICAL PHONE CONFIDENCE:", OBJECT_PHONE_CONFIDENCE)
    try:
        print("ACTIVE BEHAVIOR CLASSES:", behavior_yolo.names)
    except Exception:
        pass

    frame_counter = 0
    last_phone_debug_time = 0.0

    try:
        while active_ai_session["is_running"]:
            loop_started = time.time()

            ret, frame = cap.read()

            if not ret or frame is None:
                if source_type == "demo":
                    print("DEMO VIDEO ENDED - RESTARTING FROM BEGINNING")
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

                    behavior_stabilizer.reset()
                    try:
                        exam_behavior_stabilizer.reset()
                    except Exception:
                        pass

                    active_ai_session["recognized_faces"] = []
                    active_ai_session["unknown_faces"] = []
                    active_ai_session["person_detections"] = []
                    active_ai_session["object_detections"] = []
                    active_ai_session["student_identity_cache"] = {}
                    active_ai_session["exam_heuristic_state"] = {}
                    active_ai_session["sleep_heuristic_state"] = {}
                    active_ai_session["demo_face_votes"] = {}
                    active_ai_session["demo_unknown_tracks"] = {}
                    active_ai_session["exam_vote_history"] = {}

                    ret, frame = cap.read()

                    if not ret or frame is None:
                        print("DEMO VIDEO RESTART FAILED")
                        break
                else:
                    print("CAMERA FRAME ERROR")
                    break

            current_time = time.time()
            timestamp = datetime.now()
            frame_counter += 1
            active_ai_session["frame_counter"] = frame_counter

            # --------------------------------------------------
            # 1. BEHAVIOR YOLO + BYTETRACK
            # --------------------------------------------------
            # Restore the original working architecture: YOLO tracking with
            # ByteTrack. The behavior model produces student-level boxes, so
            # those boxes are passed directly to student association.
            behavior_detections = []

            try:
                # Live Exam mode needs a lower raw gate because cheating
                # can be a subtle head/hand action. Other modes keep their
                # existing thresholds and image size.
                if mode == "exam" and source_type == "camera":
                    behavior_track_conf = 0.10
                    behavior_track_imgsz = 704
                else:
                    behavior_track_conf = min(
                        BEHAVIOR_RAW_CONFIDENCE,
                        PHONE_RAW_CONFIDENCE,
                        SLEEPING_RAW_CONFIDENCE,
                        CHEATING_RAW_CONFIDENCE,
                    )
                    behavior_track_imgsz = (
                        DEMO_BEHAVIOR_IMGSZ
                        if source_type == "demo"
                        else 640
                    )

                results = behavior_yolo.track(
                    frame,
                    persist=True,
                    tracker="bytetrack.yaml",
                    conf=behavior_track_conf,
                    imgsz=behavior_track_imgsz,
                    iou=0.45,
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

                        raw_required = minimum_raw_confidence(canonical)

                        if (
                            mode == "exam"
                            and source_type == "camera"
                            and canonical == "cheating"
                        ):
                            raw_required = 0.10

                        if confidence < raw_required:
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
            effective_face_interval = (
                DEMO_FACE_RECOGNITION_INTERVAL
                if source_type == "demo"
                else FACE_RECOGNITION_INTERVAL
            )

            face_recognition_due = (
                frame_counter == 1
                or frame_counter % effective_face_interval == 0
            )

            new_faces = []

            if face_recognition_due:
                new_faces = detect_and_recognize_faces(frame)
                update_face_cache(new_faces)
                update_unknown_face_cache(new_faces)

            recognized_faces = get_current_recognized_faces()
            unknown_faces = get_current_unknown_faces()

            # --------------------------------------------------
            # 3. PERSON DETECTION
            # --------------------------------------------------
            # One YOLOv8n pass handles BOTH person + physical cell phone.
            effective_object_interval = (
                DEMO_OBJECT_DETECTION_INTERVAL
                if source_type == "demo"
                else OBJECT_DETECTION_INTERVAL
            )

            if (
                frame_counter == 1
                or frame_counter % effective_object_interval == 0
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

            # DEMO ONLY:
            # retry small/distant faces inside person crops.
            if (
                source_type == "demo"
                and face_recognition_due
                and persons
            ):
                recovered_demo_faces = recover_demo_faces_from_person_crops(
                    frame,
                    persons,
                    new_faces,
                )

                if recovered_demo_faces:
                    update_face_cache(recovered_demo_faces)

                recognized_faces = get_current_recognized_faces()

            students = update_persistent_students(
                persons,
                recognized_faces,
                current_time,
            )

            if source_type == "demo":
                # Build UNKNOWN from unmatched PERSON tracks instead of relying
                # only on an Unknown MTCNN face. This ensures every visible
                # student gets a frame after a short confirmation period.
                unknown_people = get_demo_unidentified_people(
                    persons,
                    students,
                    current_time,
                )
            else:
                # Preserve original live UNKNOWN behavior.
                unknown_people = match_unknown_faces_to_persons(
                    persons,
                    unknown_faces,
                    students,
                )

            for tracked_student in students:
                if tracked_student.get("identity_source") == "body_track":
                    print(
                        f"IDENTITY HELD: student={tracked_student['student_id']} "
                        f"(face hidden, body detected)"
                    )

            # --------------------------------------------------
            # 5. PRESET-SPECIFIC BEHAVIOR PIPELINE
            # --------------------------------------------------
            if mode == "exam":
                # Exam Protector Preset:
                # exam_model.pt only -> cheating / non_cheating.
                #
                # Run a student-specific crop pass so small cheating actions
                # are easier to see and cannot be assigned to the neighbor.
                exam_crop_due = (
                    frame_counter == 1
                    or (
                        source_type == "camera"
                        and frame_counter % 2 == 0
                    )
                    or (
                        source_type == "demo"
                        and frame_counter % 4 == 0
                    )
                )

                if students and exam_crop_due:
                    crop_conf = (
                        EXAM_CROP_CONFIDENCE_LIVE
                        if source_type == "camera"
                        else EXAM_CROP_CONFIDENCE_DEMO
                    )

                    exam_crop_detections = detect_exam_student_crop_behaviors(
                        frame,
                        behavior_yolo,
                        students,
                        crop_conf,
                    )

                    if exam_crop_detections:
                        behavior_detections.extend(exam_crop_detections)

                        if source_type == "camera":
                            for item in exam_crop_detections:
                                print(
                                    "LIVE EXAM CROP:",
                                    f"student={item.get('student_hint')}",
                                    f"label={item.get('label')}",
                                    f"conf={float(item.get('confidence', 0.0)):.3f}",
                                )

                raw_student_behaviors = assign_exam_behaviors_to_students(
                    behavior_detections,
                    students,
                )

                # LIVE CAMERA ONLY:
                # Keep exam_model.pt as the primary detector, but supplement
                # it with repeated lateral head-turn evidence when the model
                # misses an obvious suspicious turn.
                #
                # Demo mode is NOT changed by this fallback.
                if source_type == "camera":
                    raw_student_behaviors = fuse_exam_model_and_head_movement(
                        raw_student_behaviors,
                        students,
                        current_time,
                    )

                student_behaviors = stabilize_exam_model_votes(
                    raw_student_behaviors,
                    students,
                    current_time,
                )

            else:
                # Smart Classroom Preset:
                # classroom_model.pt -> attentive / not_attentive /
                # phone_use / sleeping
                raw_student_behaviors = assign_behaviors_to_students(
                    behavior_detections,
                    students,
                    frame.shape,
                )

                physical_phone_assignments = assign_physical_phones_to_students(
                    object_phones,
                    students,
                    frame.shape,
                )

                raw_student_behaviors = fuse_final_behaviors(
                    raw_student_behaviors,
                    physical_phone_assignments,
                    students,
                )

                # Add a classroom sleeping fallback for the common case where
                # the student lays the head down and the face disappears.
                raw_student_behaviors = fuse_classroom_sleeping(
                    raw_student_behaviors,
                    students,
                    physical_phone_assignments,
                    current_time,
                )

                for phone_student_id, phone_info in physical_phone_assignments.items():
                    print(
                        f"PHYSICAL PHONE: student={phone_student_id}, "
                        f"conf={phone_info['confidence']:.3f}, "
                        f"box={phone_info['box']}"
                    )

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

            draw_unknown_person_boxes(frame, unknown_people)

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
            ret, buffer = cv2.imencode(
                ".jpg",
                frame,
                [int(cv2.IMWRITE_JPEG_QUALITY), 80],
            )
            if not ret:
                continue

            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n"
                + buffer.tobytes()
                + b"\r\n"
            )

            # DEMO REAL-TIME PLAYBACK:
            # If AI inference is faster than the source FPS, sleep normally.
            # If inference is slower, drop a few undecoded source frames so the
            # prerecorded video stays close to real-time instead of slow motion.
            if frame_interval > 0:
                elapsed = time.time() - loop_started
                remaining = frame_interval - elapsed

                if remaining > 0:
                    time.sleep(remaining)
                else:
                    frames_behind = int(elapsed / frame_interval) - 1
                    frames_to_drop = max(
                        0,
                        min(DEMO_MAX_CATCHUP_FRAMES, frames_behind),
                    )

                    for _ in range(frames_to_drop):
                        if not cap.grab():
                            break

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
    """
    Start a Student360 AI session.

    JSON:
      {
        "mode": "classroom" | "exam",
        "source_type": "camera" | "demo"
      }

    Demo files:
      backend/demo_videos/classroom_demo.mp4
      backend/demo_videos/exam_demo.mp4
    """
    global active_ai_session

    with camera_lock:
        if active_ai_session["is_running"]:
            raise HTTPException(
                status_code=400,
                detail="An AI session is already running",
            )

        mode = str(data.get("mode", "classroom")).strip().lower()
        source_type = str(
            data.get("source_type", "camera")
        ).strip().lower()

        if mode not in {"classroom", "exam"}:
            raise HTTPException(
                status_code=400,
                detail="Invalid monitoring mode",
            )

        if source_type not in {"camera", "demo"}:
            raise HTTPException(
                status_code=400,
                detail="Invalid input source",
            )

        source_path = None

        if source_type == "camera":
            print("INITIALIZING STUDENT360 LIVE CAMERA...")

            cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)

            try:
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            except Exception:
                pass

            if not cap.isOpened():
                cap.release()
                cap = cv2.VideoCapture(0)

                try:
                    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                except Exception:
                    pass

            if not cap.isOpened():
                cap.release()
                raise HTTPException(
                    status_code=500,
                    detail="Unable to open webcam",
                )

            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        else:
            demo_filename = (
                "classroom_demo.mp4"
                if mode == "classroom"
                else "exam_demo.mp4"
            )

            source_path = os.path.abspath(
                os.path.join(
                    DEMO_VIDEOS_DIR,
                    demo_filename,
                )
            )

            if not os.path.exists(source_path):
                raise HTTPException(
                    status_code=404,
                    detail=(
                        f"Demo video not found: {demo_filename}. "
                        f"Place it inside {DEMO_VIDEOS_DIR}"
                    ),
                )

            print(
                "INITIALIZING STUDENT360 DEMO VIDEO:",
                source_path,
            )

            cap = cv2.VideoCapture(source_path)

            if not cap.isOpened():
                cap.release()
                raise HTTPException(
                    status_code=500,
                    detail=f"Unable to open demo video: {demo_filename}",
                )

        ret, test_frame = cap.read()

        if not ret or test_frame is None:
            cap.release()
            raise HTTPException(
                status_code=500,
                detail=(
                    "Input source opened but failed to read the first frame"
                ),
            )

        # Reset demo file back to frame 0 because we consumed one frame for validation.
        if source_type == "demo":
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

        source_fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)

        if source_type == "demo" and (
            source_fps <= 0.0
            or source_fps > 120.0
        ):
            source_fps = 30.0

        session_id = str(uuid.uuid4())
        started_at = datetime.now()

        behavior_stabilizer.reset()

        try:
            exam_behavior_stabilizer.reset()
        except Exception:
            pass

        active_ai_session.update({
            "cap": cap,
            "is_running": True,
            "mode": mode,
            "source_type": source_type,
            "source_path": source_path,
            "source_fps": source_fps,
            "student_stats": {},
            "tracker_to_student_map": {},
            "recognized_faces": [],
            "unknown_faces": [],
            "person_detections": [],
            "session_id": session_id,
            "started_at": started_at,
            "frame_counter": 0,
            "behavior_states": {},
            "object_detections": [],
            "last_object_detection_time": 0.0,
            "student_identity_cache": {},
            "exam_heuristic_state": {},
            "sleep_heuristic_state": {},
            "demo_face_votes": {},
            "demo_unknown_tracks": {},
            "exam_vote_history": {},
        })

        print("================================")
        print("AI SESSION STARTED")
        print("SESSION ID:", session_id)
        print("MODE:", mode)
        print("SOURCE TYPE:", source_type)

        if source_type == "camera":
            print("INPUT: LIVE CAMERA")
        else:
            print("INPUT: PRE-RECORDED AI DEMO")
            print("DEMO FILE:", source_path)
            print("DEMO FPS:", source_fps)

        print("================================")

        return {
            "status": "success",
            "session_id": session_id,
            "mode": mode,
            "source_type": source_type,
            "source_path": (
                os.path.basename(source_path)
                if source_path
                else None
            ),
            "message": (
                "Live AI camera initialized successfully"
                if source_type == "camera"
                else "AI demo video initialized successfully"
            ),
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
    exam_behavior_stabilizer.reset()

    active_ai_session.update({
        "cap": None,
        "is_running": False,
        "mode": None,
        "source_type": "camera",
        "source_path": None,
        "source_fps": 0.0,
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
        "student_identity_cache": {},
        "exam_heuristic_state": {},
        "sleep_heuristic_state": {},
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
        load_demo_training_embeddings()

        active_ai_session["tracker_to_student_map"] = {}
        active_ai_session["recognized_faces"] = []
        active_ai_session["unknown_faces"] = []
        active_ai_session["student_identity_cache"] = {}
        active_ai_session["exam_heuristic_state"] = {}
        active_ai_session["sleep_heuristic_state"] = {}
        behavior_stabilizer.reset()
        exam_behavior_stabilizer.reset()

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