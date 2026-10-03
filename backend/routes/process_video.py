
# ============================================================
# STUDENT360 - LIVE AI SURVEILLANCE ENGINE
# ============================================================

from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse

import shutil
import subprocess
import os
import cv2
import time
import joblib
import numpy as np
import pandas as pd
import uuid
import threading

from datetime import datetime
from ultralytics import YOLO
from mtcnn import MTCNN
from keras_facenet import FaceNet

from database import (
    attendance_collection,
    behavior_collection,
    evidence_collection,
    sessions_collection
)

# ============================================================
# ROUTER
# ============================================================

router = APIRouter()

# ============================================================
# DIRECTORY CONFIGURATION
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")

SESSION_LOGS_FOLDER = os.path.join(
    UPLOAD_FOLDER,
    "session_logs"
)

EVIDENCE_FOLDER = os.path.join(
    UPLOAD_FOLDER,
    "evidence"
)

ATTENDANCE_FOLDER = os.path.join(
    BASE_DIR,
    "attendance"
)

MODELS_DIR = os.path.join(
    BASE_DIR,
    "models"
)

AI_ENGINE_MODELS_DIR = os.path.abspath(
    os.path.join(BASE_DIR, "../ai_engine/models")
)

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(SESSION_LOGS_FOLDER, exist_ok=True)
os.makedirs(EVIDENCE_FOLDER, exist_ok=True)
os.makedirs(ATTENDANCE_FOLDER, exist_ok=True)

# ============================================================
# MODEL PATH RESOLUTION
# ============================================================

def resolve_model_file(filename):

    paths = [
        os.path.join(MODELS_DIR, filename),
        os.path.join(AI_ENGINE_MODELS_DIR, filename),
        os.path.join(BASE_DIR, "models", filename)
    ]

    for path in paths:

        if os.path.exists(path):
            return path

    return filename


# ============================================================
# LOAD FACE RECOGNITION MODELS
# ============================================================

print("Loading Student360 AI Recognition Engine...")

try:

    detector = MTCNN()

    embedder = FaceNet()

    face_svm = joblib.load(
        resolve_model_file("face_model.pkl")
    )

    label_encoder = joblib.load(
        resolve_model_file("label_encoder.pkl")
    )

    print("FaceNet and SVM loaded successfully")

except Exception as e:

    print("FACE RECOGNITION ERROR:", repr(e))

    detector = None
    embedder = None
    face_svm = None
    label_encoder = None


# ============================================================
# GLOBAL SESSION STATE
# ============================================================

active_ai_session = {

    "is_running": False,

    "mode": None,

    "cap": None,

    "student_stats": {},

    "tracker_to_student_map": {},

    "session_id": None,

    "started_at": None

}

# Prevent simultaneous camera initialization
camera_lock = threading.Lock()


# ============================================================
# YOLO MODEL
# ============================================================

def get_yolo_model(mode):

    if mode == "classroom":

        target = "classroom_model.pt"

    else:

        target = "exam_model.pt"

    model_path = resolve_model_file(target)

    if os.path.exists(model_path):

        print("Loading custom YOLO model:", model_path)

        return YOLO(model_path)

    print("Custom model not found. Using YOLOv8n fallback.")

    return YOLO("yolov8n.pt")


# ============================================================
# INITIALIZE STUDENT STATISTICS
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

            "last_evidence_time": 0.0

        }

        print("NEW STUDENT DETECTED:", student_id)

    return stats[student_id]


# ============================================================
# NORMALIZE BEHAVIOUR LABELS
# ============================================================

def normalize_behavior(label):

    label = str(label).strip().lower()

    label = label.replace(" ", "_").replace("-", "_")

    return label


# ============================================================
# UPDATE STUDENT BEHAVIOUR STATISTICS
# ============================================================

def update_student_statistics(student_id, behavior_label, current_time, timestamp):

    stats = initialize_student_stats(
        student_id,
        timestamp
    )

    elapsed = max(
        0.0,
        min(current_time - stats["last_seen_time"], 1.0)
    )

    stats["last_seen_time"] = current_time

    label = normalize_behavior(behavior_label)

    if label in ["cheating", "malpractice"]:

        stats["cheating_sec"] += elapsed

    elif label in ["sleeping", "sleep"]:

        stats["sleeping_sec"] += elapsed

        stats["not_attentive_sec"] += elapsed

    elif label in ["phone_use", "phone", "using_phone"]:

        stats["phone_use_sec"] += elapsed

        stats["not_attentive_sec"] += elapsed

    elif label in ["attentive", "normal", "person"]:

        stats["attentive_sec"] += elapsed

    else:

        stats["non_cheating_sec"] += elapsed

    return stats


# ============================================================
# EVIDENCE CAPTURE
# ============================================================

def save_evidence(student_id, behavior_label, frame):

    current_time = time.time()

    stats = active_ai_session["student_stats"][student_id]

    last_time = stats["last_evidence_time"]

    if current_time - last_time < 15:

        return

    timestamp = datetime.now()

    filename = (
        f"{student_id}_{behavior_label}_"
        f"{timestamp.strftime('%Y%m%d_%H%M%S_%f')}.jpg"
    )

    evidence_path = os.path.join(
        EVIDENCE_FOLDER,
        filename
    )

    try:

        image_saved = cv2.imwrite(
            evidence_path,
            frame
        )

        if not image_saved:

            raise IOError("Failed to write evidence image")

        evidence_record = {

            "student_id": str(student_id),

            "behavior": str(behavior_label),

            "image": filename,

            "image_path": f"evidence/{filename}",

            "date": timestamp,

            "session_id": active_ai_session["session_id"],

            "mode": active_ai_session["mode"],

            "source": "live_surveillance"

        }

        result = evidence_collection.insert_one(
            evidence_record
        )

        stats["last_evidence_time"] = current_time

        print("EVIDENCE SAVED:", evidence_path)

        print("EVIDENCE MONGODB ID:", result.inserted_id)

    except Exception as e:

        print("EVIDENCE ERROR:", repr(e))


# ============================================================
# LIVE VIDEO GENERATOR
# ============================================================

def generate_video_stream():

    global active_ai_session

    cap = active_ai_session["cap"]

    if cap is None or not cap.isOpened():

        print("ERROR: Camera is not initialized")

        active_ai_session["is_running"] = False

        return

    mode = active_ai_session["mode"]

    print("Loading AI detection model...")

    try:

        yolo = get_yolo_model(mode)

    except Exception as e:

        print("YOLO LOAD ERROR:", repr(e))

        active_ai_session["is_running"] = False

        return

    tracker_to_student_map = active_ai_session[
        "tracker_to_student_map"
    ]

    print("LIVE VIDEO STREAM STARTED")

    try:

        while active_ai_session["is_running"]:

            ret, frame = cap.read()

            if not ret or frame is None:

                print("CAMERA FRAME ERROR")

                break

            current_time = time.time()

            timestamp = datetime.now()

            # ==========================================
            # YOLO + BYTETRACK
            # ==========================================

            try:

                results = yolo.track(
                    frame,
                    persist=True,
                    tracker="bytetrack.yaml",
                    conf=0.45,
                    verbose=False
                )

            except Exception as e:

                print("YOLO TRACK ERROR:", repr(e))

                results = yolo(
                    frame,
                    conf=0.45,
                    verbose=False
                )

            # Prevent duplicate duration updates
            updated_students = set()

            for result in results:

                boxes = result.boxes

                if boxes is None:
                    continue

                for box in boxes:

                    x1, y1, x2, y2 = map(
                        int,
                        box.xyxy[0].tolist()
                    )

                    cls_id = int(box.cls[0])

                    behavior_label = (
                        yolo.names[cls_id]
                        if cls_id in yolo.names
                        else "person"
                    )

                    normalized_label = normalize_behavior(
                        behavior_label
                    )

                    is_alert = normalized_label in [
                        "cheating",
                        "malpractice",
                        "sleeping",
                        "sleep",
                        "phone_use",
                        "phone",
                        "using_phone"
                    ]

                    track_id = (
                        int(box.id[0])
                        if box.id is not None
                        else None
                    )

                    student_id = "Unknown"

                    confidence_str = ""

                    # ==================================
                    # FACE RECOGNITION
                    # ==================================

                    if (
                        track_id is not None
                        and track_id in tracker_to_student_map
                    ):

                        student_id = tracker_to_student_map[
                            track_id
                        ]

                    else:

                        person_crop = frame[
                            max(0, y1):max(0, y2),
                            max(0, x1):max(0, x2)
                        ]

                        if (
                            person_crop.size > 0
                            and person_crop.shape[0] >= 20
                            and person_crop.shape[1] >= 20
                            and detector is not None
                            and embedder is not None
                            and face_svm is not None
                            and label_encoder is not None
                        ):

                            rgb = cv2.cvtColor(
                                person_crop,
                                cv2.COLOR_BGR2RGB
                            )

                            try:

                                faces = detector.detect_faces(rgb)

                            except Exception as e:

                                print("FACE DETECTION ERROR:", repr(e))

                                faces = []

                            if faces:

                                fx, fy, fw, fh = faces[0]["box"]

                                fx = max(0, fx)
                                fy = max(0, fy)

                                face_img = rgb[
                                    fy:fy + fh,
                                    fx:fx + fw
                                ]

                                if (
                                    face_img.shape[0] >= 20
                                    and face_img.shape[1] >= 20
                                ):

                                    try:

                                        face_resized = cv2.resize(
                                            face_img,
                                            (160, 160)
                                        )

                                        embedding = embedder.embeddings(
                                            [face_resized]
                                        )

                                        probs = face_svm.predict_proba(
                                            embedding
                                        )

                                        confidence = float(
                                            np.max(probs)
                                        )

                                        pred = int(
                                            np.argmax(probs)
                                        )

                                        THRESHOLD = 0.70

                                        if confidence >= THRESHOLD:

                                            student_id = str(
                                                label_encoder.inverse_transform(
                                                    [pred]
                                                )[0]
                                            )

                                            confidence_str = (
                                                f"({confidence:.2f})"
                                            )

                                            if track_id is not None:

                                                tracker_to_student_map[
                                                    track_id
                                                ] = student_id

                                    except Exception as e:

                                        print(
                                            "FACE RECOGNITION ERROR:",
                                            repr(e)
                                        )

                    # ==================================
                    # STUDENT STATISTICS
                    # ==================================

                    if student_id != "Unknown":

                        if student_id not in updated_students:

                            update_student_statistics(
                                student_id,
                                behavior_label,
                                current_time,
                                timestamp
                            )

                            updated_students.add(student_id)

                        # ==============================
                        # EVIDENCE
                        # ==============================

                        if is_alert:

                            save_evidence(
                                student_id,
                                behavior_label,
                                frame.copy()
                            )

                    # ==================================
                    # DRAW BOUNDING BOX
                    # ==================================

                    box_color = (
                        (0, 0, 255)
                        if is_alert
                        else (0, 255, 0)
                    )

                    cv2.rectangle(
                        frame,
                        (x1, y1),
                        (x2, y2),
                        box_color,
                        2
                    )

                    track_text = (
                        f"[T{track_id}] "
                        if track_id is not None
                        else ""
                    )

                    label_text = (
                        f"{track_text}{student_id} "
                        f"{confidence_str} | {behavior_label}"
                    )

                    (w, h), _ = cv2.getTextSize(
                        label_text,
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.55,
                        2
                    )

                    cv2.rectangle(
                        frame,
                        (x1, max(0, y1 - 25)),
                        (x1 + w + 10, max(0, y1)),
                        box_color,
                        -1
                    )

                    cv2.putText(
                        frame,
                        label_text,
                        (x1 + 5, max(0, y1 - 7)),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.55,
                        (255, 255, 255),
                        2
                    )

            # ==========================================
            # ENCODE FRAME
            # ==========================================

            ret, buffer = cv2.imencode(
                ".jpg",
                frame
            )

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
# VIDEO FEED ENDPOINT
# ============================================================

@router.get("/video-feed")
async def video_feed():

    if not active_ai_session["is_running"]:

        raise HTTPException(
            status_code=400,
            detail="Camera session is not active"
        )

    cap = active_ai_session.get("cap")

    if cap is None or not cap.isOpened():

        raise HTTPException(
            status_code=500,
            detail="Camera is not initialized"
        )

    return StreamingResponse(
        generate_video_stream(),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0"
        }
    )


# ============================================================
# START CAMERA
# ============================================================

@router.post("/start-camera")
async def start_camera(data: dict):

    global active_ai_session

    with camera_lock:

        if active_ai_session["is_running"]:

            raise HTTPException(
                status_code=400,
                detail="An AI session is already running"
            )

        mode = data.get("mode", "classroom")

        if mode not in ["classroom", "exam"]:

            raise HTTPException(
                status_code=400,
                detail="Invalid monitoring mode"
            )

        print("INITIALIZING STUDENT360 CAMERA...")

        # Windows camera backend
        cap = cv2.VideoCapture(
            0,
            cv2.CAP_DSHOW
        )

        # Fallback camera backend
        if not cap.isOpened():

            cap.release()

            cap = cv2.VideoCapture(0)

        if not cap.isOpened():

            cap.release()

            raise HTTPException(
                status_code=500,
                detail="Unable to open webcam"
            )

        cap.set(
            cv2.CAP_PROP_FRAME_WIDTH,
            640
        )

        cap.set(
            cv2.CAP_PROP_FRAME_HEIGHT,
            480
        )

        ret, test_frame = cap.read()

        if not ret or test_frame is None:

            cap.release()

            raise HTTPException(
                status_code=500,
                detail="Camera opened but failed to capture frame"
            )

        session_id = str(uuid.uuid4())

        started_at = datetime.now()

        active_ai_session["cap"] = cap

        active_ai_session["is_running"] = True

        active_ai_session["mode"] = mode

        active_ai_session["student_stats"] = {}

        active_ai_session["tracker_to_student_map"] = {}

        active_ai_session["session_id"] = session_id

        active_ai_session["started_at"] = started_at

        print("================================")

        print("AI SESSION STARTED")

        print("SESSION ID:", session_id)

        print("MODE:", mode)

        print("CAMERA INITIALIZED")

        print("================================")

        return {

            "status": "success",

            "session_id": session_id,

            "mode": mode,

            "message": "Camera initialized successfully"

        }


# ============================================================
# STOP CAMERA + EXPORT CSV + MONGODB
# ============================================================

@router.post("/stop-camera")
async def stop_camera():

    global active_ai_session

    if not active_ai_session["is_running"]:

        return {
            "status": "warning",
            "message": "No active session"
        }

    # ==========================================
    # 1. STOP CAMERA
    # ==========================================

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

    date_str = ended_at.strftime(
        "%Y-%m-%d_%H-%M-%S"
    )

    csv_filename = (
        f"session_summary_{mode}_{date_str}_{session_id[:8]}.csv"
    )

    csv_path = os.path.join(
        SESSION_LOGS_FOLDER,
        csv_filename
    )

    # ==========================================
    # 2. CREATE DATAFRAME
    # ==========================================

    columns = [
        "Student_ID",
        "Date",
        "Arrival_Time",
        "cheating_sec",
        "non_cheating_sec",
        "attentive_sec",
        "sleeping_sec",
        "phone_use_sec",
        "not_attentive_sec"
    ]

    if stats:

        df = pd.DataFrame.from_dict(
            stats,
            orient="index"
        )

        df.index.name = "Student_ID"

        df.reset_index(inplace=True)

        df = df.drop(
            columns=[
                "last_seen_time",
                "last_evidence_time"
            ],
            errors="ignore"
        )

        df = df.reindex(
            columns=columns,
            fill_value=0
        )

        df = df.round(2)

    else:

        print("WARNING: No recognized students found")

        df = pd.DataFrame(columns=columns)

    # ==========================================
    # 3. SAVE CSV
    # ==========================================

    try:

        df.to_csv(
            csv_path,
            index=False
        )

        print("CSV SAVED:", os.path.abspath(csv_path))

    except Exception as e:

        print("CSV ERROR:", repr(e))

        raise HTTPException(
            status_code=500,
            detail=f"CSV saving failed: {str(e)}"
        )

    # ==========================================
    # 4. SAVE ATTENDANCE + BEHAVIOUR
    # ==========================================

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

            "created_at": ended_at

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

            "created_at": ended_at

        }

        # Attendance insert
        try:

            attendance_collection.insert_one(
                attendance_record
            )

            attendance_inserted += 1

            print("ATTENDANCE SAVED:", student_id)

        except Exception as e:

            database_errors.append({

                "collection": "attendance",

                "student_id": student_id,

                "error": str(e)

            })

            print("ATTENDANCE ERROR:", repr(e))

        # Behaviour insert
        try:

            behavior_collection.insert_one(
                behavior_record
            )

            behavior_inserted += 1

            print("BEHAVIOUR SAVED:", student_id)

        except Exception as e:

            database_errors.append({

                "collection": "behavior",

                "student_id": student_id,

                "error": str(e)

            })

            print("BEHAVIOUR ERROR:", repr(e))

    # ==========================================
    # 5. SAVE SESSION METADATA
    # ==========================================

    session_status = (
        "completed"
        if not database_errors
        else "completed_with_errors"
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

            "status": session_status

        })

        print("SESSION REPORT SAVED TO MONGODB")

    except Exception as e:

        database_errors.append({

            "collection": "sessions",

            "error": str(e)

        })

        print("SESSION DATABASE ERROR:", repr(e))

    # ==========================================
    # 6. RESET SESSION
    # ==========================================

    active_ai_session["cap"] = None

    active_ai_session["is_running"] = False

    active_ai_session["mode"] = None

    active_ai_session["student_stats"] = {}

    active_ai_session["tracker_to_student_map"] = {}

    active_ai_session["session_id"] = None

    active_ai_session["started_at"] = None

    # ==========================================
    # 7. RETURN RESULTS
    # ==========================================

    print("================================")

    print("SESSION COMPLETED")

    print("TOTAL STUDENTS:", len(df))

    print("ATTENDANCE:", attendance_inserted)

    print("BEHAVIOUR:", behavior_inserted)

    print("DATABASE ERRORS:", len(database_errors))

    print("CSV:", csv_path)

    print("================================")

    return {

        "status": (
            "success"
            if not database_errors
            else "partial_success"
        ),

        "message": "AI session stopped and report generated",

        "session_id": session_id,

        "csv_file": csv_filename,

        "total_students": len(df),

        "attendance_inserted": attendance_inserted,

        "behavior_inserted": behavior_inserted,

        "database_errors": database_errors

    }


# ============================================================
# EXISTING VIDEO UPLOAD ENDPOINT
# ============================================================

@router.post("/process-video")
async def process_video(file: UploadFile = File(...)):

    filepath = os.path.join(
        UPLOAD_FOLDER,
        file.filename
    )

    try:

        with open(filepath, "wb") as buffer:

            shutil.copyfileobj(
                file.file,
                buffer
            )

        subprocess.run(
            [
                "python",
                "../ai_engine/unified_pipeline.py",
                filepath
            ],
            check=True
        )

        return {
            "status": "success",
            "message": "Video processed successfully"
        }

    except Exception as e:

        print("VIDEO PROCESSING ERROR:", repr(e))

        raise HTTPException(
            status_code=500,
            detail=f"Video processing failed: {str(e)}"
        )
        

# ============================================================
# HOT-RELOAD TRAINED FACE RECOGNITION MODELS
# ============================================================

def reload_face_models():
    """Reloads the updated face recognition model into runtime memory."""
    global face_svm, label_encoder, active_ai_session
    try:
        face_svm = joblib.load(resolve_model_file("face_model.pkl"))
        label_encoder = joblib.load(resolve_model_file("label_encoder.pkl"))
        active_ai_session["tracker_to_student_map"] = {}
        print("✅ Reloaded latest face recognition models into runtime successfully.")
    except Exception as e:
        print("⚠️ Failed to reload face models:", repr(e))