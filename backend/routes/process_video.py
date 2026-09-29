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
from datetime import datetime
from ultralytics import YOLO
from mtcnn import MTCNN
from keras_facenet import FaceNet

router = APIRouter()

UPLOAD_FOLDER = "uploads"
SESSION_LOGS_FOLDER = "uploads/session_logs"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(SESSION_LOGS_FOLDER, exist_ok=True)
os.makedirs("attendance", exist_ok=True)
os.makedirs("evidence", exist_ok=True)

# Path to the models folder inside backend
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_DIR = os.path.join(BASE_DIR, "models")
AI_ENGINE_MODELS_DIR = os.path.abspath(os.path.join(BASE_DIR, "../ai_engine/models"))

def resolve_model_file(filename):
    p1 = os.path.join(MODELS_DIR, filename)
    p2 = os.path.join(AI_ENGINE_MODELS_DIR, filename)
    p3 = os.path.join("models", filename)
    for p in [p1, p2, p3]:
        if os.path.exists(p):
            return p
    return filename

print("🚀 Loading Student360 AI Recognition Engine...")

# Load FaceNet & SVM Models
try:
    detector = MTCNN()
    embedder = FaceNet()
    face_svm = joblib.load(resolve_model_file("face_model.pkl"))
    label_encoder = joblib.load(resolve_model_file("label_encoder.pkl"))
    print("✅ FaceNet and SVM Classifier Loaded!")
except Exception as e:
    print(f"⚠️ Face recognition load warning: {e}")
    detector, embedder, face_svm, label_encoder = None, None, None, None

active_ai_session = {
    "is_running": False,
    "mode": None,  # "classroom" or "exam"
    "cap": None,
    "student_stats": {},
    "tracker_to_student_map": {}
}

def get_yolo_model(mode: str):
    target = "classroom_model.pt" if mode == "classroom" else "exam_model.pt"
    resolved = resolve_model_file(target)
    if os.path.exists(resolved):
        print(f"✅ Loading custom trained YOLO model: {resolved}")
        return YOLO(resolved)
    print(f"⚠️ Model {target} not found at {resolved}. Using default fallback.")
    return YOLO("yolov8n.pt")


def generate_video_stream():
    global active_ai_session
    cap = cv2.VideoCapture(0)
    active_ai_session["cap"] = cap

    mode = active_ai_session.get("mode", "classroom")
    yolo = get_yolo_model(mode)
    
    tracker_to_student_map = active_ai_session["tracker_to_student_map"]
    student_stats = active_ai_session["student_stats"]

    while active_ai_session["is_running"]:
        ret, frame = cap.read()
        if not ret:
            break

        current_time = time.time()

        # 1. ByteTrack Tracking with YOLO
        try:
            results = yolo.track(frame, persist=True, tracker="bytetrack.yaml", conf=0.45, verbose=False)
        except Exception:
            results = yolo(frame, conf=0.45, verbose=False)

        for result in results:
            boxes = result.boxes
            if boxes is None:
                continue

            for box in boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                cls_id = int(box.cls[0])
                behavior_label = yolo.names[cls_id] if hasattr(yolo, "names") and cls_id in yolo.names else "person"
                track_id = int(box.id[0]) if box.id is not None else None

                student_id = "Unknown"
                confidence_str = ""

                # 2. Identity Caching (Fast Face Recognition)
                if track_id is not None and track_id in tracker_to_student_map:
                    student_id = tracker_to_student_map[track_id]
                else:
                    person_crop = frame[max(0, y1):max(0, y2), max(0, x1):max(0, x2)]
                    if person_crop.size > 0 and person_crop.shape[0] >= 20 and person_crop.shape[1] >= 20 and detector and face_svm:
                        rgb = cv2.cvtColor(person_crop, cv2.COLOR_BGR2RGB)
                        try:
                            faces = detector.detect_faces(rgb)
                        except Exception:
                            faces = []

                        if faces:
                            fx, fy, fw, fh = faces[0]['box']
                            fx, fy = max(0, fx), max(0, fy)
                            face_img = rgb[fy:fy+fh, fx:fx+fw]

                            if face_img.shape[0] >= 20 and face_img.shape[1] >= 20:
                                face_resized = cv2.resize(face_img, (160, 160))
                                embedding = embedder.embeddings([face_resized])

                                probs = face_svm.predict_proba(embedding)
                                confidence = np.max(probs)
                                pred = np.argmax(probs)

                                THRESHOLD = 0.70
                                if confidence >= THRESHOLD:
                                    student_id = label_encoder.inverse_transform([pred])[0]
                                    confidence_str = f"({confidence:.2f})"
                                    if track_id is not None:
                                        tracker_to_student_map[track_id] = student_id

                # 3. Update Statistics
                if student_id != "Unknown":
                    if student_id not in student_stats:
                        student_stats[student_id] = {
                            "Date": datetime.now().strftime("%Y-%m-%d"),
                            "Arrival_Time": datetime.now().strftime("%H:%M:%S"),
                            "cheating_sec": 0.0,
                            "non_cheating_sec": 0.0,
                            "attentive_sec": 0.0,
                            "sleeping_sec": 0.0,
                            "phone_use_sec": 0.0,
                            "not_attentive_sec": 0.0,
                            "last_seen_time": current_time,
                            "last_evidence_time": 0.0
                        }

                    time_diff = current_time - student_stats[student_id]["last_seen_time"]
                    if time_diff < 2.0:
                        key = f"{behavior_label}_sec"
                        if key in student_stats[student_id]:
                            student_stats[student_id][key] += time_diff

                    student_stats[student_id]["last_seen_time"] = current_time

                # 4. Draw Exact Colored Bounding Boxes
                is_alert = behavior_label in ["cheating", "sleeping", "phone_use"]
                box_color = (0, 0, 255) if is_alert else (0, 255, 0)

                cv2.rectangle(frame, (x1, y1), (x2, y2), box_color, 2)
                t_str = f"[T{track_id}] " if track_id is not None else ""
                label_text = f"{t_str}{student_id} {confidence_str} | {behavior_label}"
                
                (w, h), _ = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 2)
                cv2.rectangle(frame, (x1, max(0, y1 - 25)), (x1 + w + 10, max(0, y1)), box_color, -1)
                cv2.putText(frame, label_text, (x1 + 5, max(0, y1 - 7)), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)

                # Capture Evidence on alert behavior
                if student_id != "Unknown" and is_alert:
                    if (current_time - student_stats[student_id]["last_evidence_time"]) > 15.0:
                        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                        ev_path = f"evidence/{student_id}_{behavior_label}_{ts}.jpg"
                        cv2.imwrite(ev_path, frame)
                        student_stats[student_id]["last_evidence_time"] = current_time

        ret, buffer = cv2.imencode('.jpg', frame)
        if not ret:
            continue

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

    cap.release()

@router.get("/video-feed")
async def video_feed():
    if not active_ai_session["is_running"]:
        raise HTTPException(status_code=400, detail="Camera session is not active")
    return StreamingResponse(
        generate_video_stream(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )

@router.post("/start-camera")
async def start_camera(data: dict):
    global active_ai_session
    mode = data.get("mode", "classroom")
    active_ai_session["is_running"] = True
    active_ai_session["mode"] = mode
    active_ai_session["student_stats"] = {}
    active_ai_session["tracker_to_student_map"] = {}
    return {"status": "success", "mode": mode, "message": f"{mode.capitalize()} mode started"}

@router.post("/stop-camera")
async def stop_camera():
    global active_ai_session
    if not active_ai_session["is_running"]:
        return {"status": "warning", "message": "No active session to stop."}

    active_ai_session["is_running"] = False
    if active_ai_session["cap"]:
        active_ai_session["cap"].release()

    mode = active_ai_session["mode"]
    stats = active_ai_session["student_stats"]
    date_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    csv_filename = f"session_summary_{mode}_{date_str}.csv"
    csv_path = os.path.join(SESSION_LOGS_FOLDER, csv_filename)

    if len(stats) > 0:
        df = pd.DataFrame.from_dict(stats, orient='index')
        df.index.name = 'Student_ID'
        df.reset_index(inplace=True)
        df.drop(columns=['last_seen_time', 'last_evidence_time'], inplace=True, errors='ignore')
        df = df.round(2)
        df.to_csv(csv_path, index=False)
        df.to_csv(os.path.join("attendance", csv_filename), index=False)
        print(f"✅ Session report saved: {csv_path}")

    active_ai_session["mode"] = None
    return {"status": "success", "message": f"Session closed. Saved to {csv_filename}"}

@router.post("/process-video")
async def process_video(file: UploadFile = File(...)):
    filepath = os.path.join(UPLOAD_FOLDER, file.filename)
    with open(filepath, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    subprocess.run(["python", "../ai_engine/unified_pipeline.py", filepath])
    return {"message": "Video Processed"}