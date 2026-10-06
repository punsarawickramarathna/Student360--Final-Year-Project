import cv2
import numpy as np
import joblib
import os
import sys
import time
import threading
import pandas as pd
from datetime import datetime
import torch
from ultralytics import YOLO
from mtcnn import MTCNN
from keras_facenet import FaceNet
import matplotlib.pyplot as plt  
import requests
from typing import Any

# ============================================================
# 1. HARDWARE ACCELERATION & DEVICE CONFIGURATION
# ============================================================
print("============================================================")
print("🚀 Student360 Ultimate Engine - Hardware Acceleration Setup")
print("============================================================")

CUDA_AVAILABLE = torch.cuda.is_available()
if CUDA_AVAILABLE:
    gpu_name = torch.cuda.get_device_name(0)
    DEVICE = torch.device("cuda:0")
    YOLO_DEVICE = 0
    USE_FP16 = True
    HW_BADGE = f"CUDA GPU: {gpu_name} (FP16)"
    print(f"✅ Hardware Acceleration: NVIDIA GPU DETECTED -> {gpu_name}")
    print("⚡ FP16 Half-Precision inference enabled (device=0, half=True)")
    try:
        torch.cuda.init()
    except Exception as e:
        print(f"CUDA init note: {e}")
else:
    DEVICE = torch.device("cpu")
    YOLO_DEVICE = "cpu"
    USE_FP16 = False
    HW_BADGE = "CPU Fallback (Intel i7)"
    print("⚠️ Hardware Acceleration: CUDA not available. Running on CPU.")

print(f"Status Badge: {HW_BADGE}")
print("============================================================\n")


# ============================================================
# 2. NON-BLOCKING THREADED CAMERA CAPTURE CLASS
# ============================================================
class ThreadedCamera:
    """
    High-Performance Non-Blocking Threaded Camera Feed.
    - Captures in a background daemon thread to drop stale frames and eliminate latency.
    - Utilizes cv2.CAP_DSHOW on Windows for instantaneous initialization.
    - Caps capture resolution to 1280x720 / 640x480 @ 30 FPS.
    - Thread-safe frame reading and clean resource release.
    """
    def __init__(self, src=0, width=1280, height=720, fps=30):
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
            # Use DirectShow on Windows for instant camera initialization and lowest latency
            self.cap = cv2.VideoCapture(cam_idx, cv2.CAP_DSHOW)
            if not self.cap or not self.cap.isOpened():
                if self.cap:
                    self.cap.release()
                self.cap = cv2.VideoCapture(cam_idx)
        else:
            self.cap = cv2.VideoCapture(self.src)

        if self.cap is not None and self.cap.isOpened():
            # Constrain to performant capture standard
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
                    # Video file has finished
                    with self.lock:
                        self.grabbed = False
                    break
                time.sleep(0.005)
                continue

            with self.lock:
                self.latest_frame = frame
                self.grabbed = True

            # If reading from a recorded video file, pace at target FPS
            if not self.is_camera:
                time.sleep(1.0 / max(1, self.fps))

    def read(self):
        """Thread-safe acquisition of the freshest frame."""
        with self.lock:
            if not self.grabbed or self.latest_frame is None:
                return False, None
            return True, self.latest_frame.copy()

    def isOpened(self):
        return self.cap is not None and self.cap.isOpened() and not self.stopped

    def release(self):
        """Gracefully release camera resources and join capture thread."""
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


# ============================================================
# 3. LOAD ALL MODELS WITH HARDWARE ACCELERATION
# ============================================================
print("Loading YOLO Behavior Model...")
model_path = "models/classroom_model.pt"
if not os.path.exists(model_path):
    # Fallback to local or parent model path
    alt_path = os.path.join(os.path.dirname(__file__), "models", "classroom_model.pt")
    if os.path.exists(alt_path):
        model_path = alt_path

yolo_model = YOLO(model_path)
if CUDA_AVAILABLE:
    try:
        yolo_model.to("cuda")
        print("✅ YOLO Model successfully offloaded to NVIDIA GPU via CUDA")
    except Exception as e:
        print(f"⚠️ YOLO GPU offload note: {e}")

print("Loading Face Detection & Embedding Models...")
detector = MTCNN()
embedder = FaceNet()

print("Loading Face Recognition SVM Model...")
face_model_path = "models/face_model.pkl"
label_encoder_path = "models/label_encoder.pkl"
if not os.path.exists(face_model_path):
    face_model_path = os.path.join(os.path.dirname(__file__), "models", "face_model.pkl")
if not os.path.exists(label_encoder_path):
    label_encoder_path = os.path.join(os.path.dirname(__file__), "models", "label_encoder.pkl")

face_svm = joblib.load(face_model_path)
label_encoder = joblib.load(label_encoder_path)

print("✅ All Models Loaded Successfully!\n")


# ============================================================
# 4. SETUP DATA STRUCTURES & SESSION
# ============================================================
student_stats: dict[str, dict[str, Any]] = {}
tracker_to_student_map = {}
last_face_scan_time = {}  # track_id -> timestamp to throttle MTCNN retries
FACE_RETRY_INTERVAL = 1.5  # Seconds between face detection retries for unverified tracks
FACE_INTERVAL_FRAMES = 4   # Only run face detection pass every 4 frames to ensure 30 FPS

os.makedirs("attendance", exist_ok=True)
os.makedirs("evidence", exist_ok=True)

def create_session():
    try:
        response = requests.post(
            "http://127.0.0.1:8000/create-session",
            json={
                "date": datetime.now().strftime("%Y-%m-%d"),
                "year": "Y2",
                "semester": "2",
                "subject": "Computer Vision",
                "group": "A"
            },
            timeout=2.0
        )
        print("Session created:", response.json())
    except Exception as e:
        print("Session creation notice:", e)

create_session()


# ============================================================
# 5. INITIALIZE VIDEO / CAMERA SOURCE
# ============================================================
source = "data/test_video.mp4"
if len(sys.argv) > 1:
    arg_src = sys.argv[1]
    if arg_src.isdigit():
        source = int(arg_src)
    else:
        source = arg_src

# If default video doesn't exist, fall back to camera 0
if isinstance(source, str) and not os.path.exists(source) and not source.startswith("rtsp://") and not source.startswith("http"):
    print(f"File {source} not found, defaulting to live camera 0.")
    source = 0

print(f"Connecting to source: {source} (type: {'Webcam/Camera' if isinstance(source, int) else 'Video file'})")
cap = ThreadedCamera(src=source, width=1280, height=720, fps=30).start()
time.sleep(0.2)  # Give daemon thread a moment to grab initial frame

cv2.namedWindow("Student360 Unified Engine", cv2.WINDOW_NORMAL)
cv2.resizeWindow("Student360 Unified Engine", 1280, 720)

frame_idx = 0
fps_history = []
last_frame_timestamp = time.time()

print("⚡ Starting Real-Time Video Processing Loop...")

# ============================================================
# 6. INFERENCE & STREAMING LOOP (WRAPPED FOR GRACEFUL CLEANUP)
# ============================================================
try:
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret or frame is None:
            # If video file ended, break; if camera, wait briefly
            if not isinstance(source, int):
                print("Video stream finished.")
                break
            time.sleep(0.01)
            continue

        loop_start_time = time.time()
        current_time = loop_start_time
        frame_idx += 1

        # --------------------------------------------------------
        # YOLO TRACKING (CUDA FP16 ACCELERATED)
        # --------------------------------------------------------
        results = yolo_model.track(
            frame,
            persist=True,
            tracker="bytetrack.yaml",
            conf=0.45,
            device=YOLO_DEVICE,
            half=USE_FP16,
            verbose=False
        )

        for result in results:
            boxes = result.boxes
            if boxes is None:
                continue

            for box in boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                cls_id = int(box.cls[0])
                behavior_label = yolo_model.names[cls_id]

                # ByteTrack ID
                track_id = int(box.id[0]) if box.id is not None else None
                if track_id is None:
                    continue

                student_id = "Unknown"
                confidence_str = ""

                # ----------------------------------------------------
                # IDENTITY CACHING & THROTTLED FACE RECOGNITION
                # ----------------------------------------------------
                if track_id in tracker_to_student_map:
                    # Identity already verified: zero MTCNN/FaceNet overhead
                    student_id = tracker_to_student_map[track_id]
                else:
                    # Throttled recognition: only evaluate every N frames and throttle per-track retries
                    time_since_attempt = current_time - last_face_scan_time.get(track_id, 0.0)
                    can_scan_face = (
                        (frame_idx % FACE_INTERVAL_FRAMES == 0)
                        and (time_since_attempt >= FACE_RETRY_INTERVAL)
                    )

                    if can_scan_face:
                        last_face_scan_time[track_id] = current_time
                        person_crop = frame[y1:y2, x1:x2]

                        if person_crop.size > 0 and person_crop.shape[0] >= 30 and person_crop.shape[1] >= 30:
                            rgb_crop = cv2.cvtColor(person_crop, cv2.COLOR_BGR2RGB)
                            try:
                                faces = detector.detect_faces(rgb_crop)
                            except Exception:
                                faces = []

                            if faces:
                                fx, fy, fw, fh = faces[0]['box']
                                fx, fy = max(0, fx), max(0, fy)
                                face_img = rgb_crop[fy:fy + fh, fx:fx + fw]

                                if face_img.shape[0] >= 20 and face_img.shape[1] >= 20:
                                    face_resized = cv2.resize(face_img, (160, 160))
                                    embedding = embedder.embeddings([face_resized])

                                    probs = face_svm.predict_proba(embedding)
                                    confidence = float(np.max(probs))
                                    pred = int(np.argmax(probs))

                                    THRESHOLD = 0.70
                                    if confidence >= THRESHOLD:
                                        student_id = label_encoder.inverse_transform([pred])[0]
                                        confidence_str = f"({confidence:.2f})"
                                        # Bind detected student to ByteTrack ID
                                        tracker_to_student_map[track_id] = student_id
                                        print(f"🎯 Recognized Student: {student_id} (conf: {confidence:.2f}) -> Track {track_id}")

                # ----------------------------------------------------
                # UPDATE DURATION & TIMELINE STATISTICS
                # ----------------------------------------------------
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
                            "timeline": [],
                            "last_behavior": "",
                            "last_seen_time": current_time,
                            "last_evidence_time": 0.0
                        }

                    time_diff = current_time - student_stats[student_id]["last_seen_time"]

                    if student_stats[student_id]["last_behavior"] != behavior_label:
                        current_clock = datetime.now().strftime("%H:%M:%S")
                        student_stats[student_id]["timeline"].append({
                            "time": current_clock,
                            "behavior": behavior_label
                        })
                        student_stats[student_id]["last_behavior"] = behavior_label

                    if 0.0 < time_diff < 2.0:
                        key_name = f"{behavior_label}_sec"
                        if key_name in student_stats[student_id]:
                            current_sec = float(student_stats[student_id].get(key_name, 0.0))
                            student_stats[student_id][key_name] = current_sec + time_diff

                    student_stats[student_id]["last_seen_time"] = current_time

                # ----------------------------------------------------
                # DRAW BOUNDING BOX & LABELS
                # ----------------------------------------------------
                is_alert = behavior_label in ["cheating", "sleeping", "phone_use"]
                color = (0, 0, 255) if is_alert else (0, 255, 0)
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

                final_label = f"[T{track_id}] {student_id} {confidence_str} | {behavior_label}"
                (w, h), _ = cv2.getTextSize(final_label, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 2)
                cv2.rectangle(frame, (x1, max(0, y1 - 25)), (x1 + w + 6, max(25, y1)), color, -1)
                cv2.putText(frame, final_label, (x1 + 3, max(18, y1 - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)

                # ----------------------------------------------------
                # AUTOMATED EVIDENCE CAPTURE
                # ----------------------------------------------------
                if student_id != "Unknown" and is_alert:
                    time_since_last_pic = current_time - student_stats[student_id]["last_evidence_time"]
                    if time_since_last_pic > 15.0:
                        date_string = datetime.now().strftime("%Y%m%d_%H%M%S")
                        evidence_filename = f"evidence/{student_id}_{behavior_label}_{date_string}.jpg"
                        cv2.imwrite(evidence_filename, frame)
                        student_stats[student_id]["last_evidence_time"] = current_time

                        try:
                            with open(evidence_filename, "rb") as img:
                                requests.post(
                                    "http://127.0.0.1:8000/upload-evidence",
                                    files={"file": (os.path.basename(evidence_filename), img, "image/jpeg")},
                                    data={"student_id": student_id, "behavior": behavior_label},
                                    timeout=2.0
                                )
                            print(f"📸 EVIDENCE CAPTURED & DISPATCHED: {evidence_filename}")
                        except Exception as e:
                            print("Evidence upload failed:", e)

        # --------------------------------------------------------
        # REAL-TIME TELEMETRY HUD (FPS, LATENCY, HARDWARE STATUS)
        # --------------------------------------------------------
        compute_ms = (time.time() - loop_start_time) * 1000.0
        frame_time = time.time() - last_frame_timestamp
        last_frame_timestamp = time.time()
        instant_fps = 1.0 / max(0.001, frame_time)
        fps_history.append(instant_fps)
        if len(fps_history) > 30:
            fps_history.pop(0)
        smooth_fps = sum(fps_history) / len(fps_history)

        # Glassmorphism dark badge for HUD overlay
        cv2.rectangle(frame, (10, 10), (450, 48), (20, 20, 20), -1)
        cv2.rectangle(frame, (10, 10), (450, 48), (0, 255, 120), 1)
        hud_text = f"FPS: {smooth_fps:.1f} | Latency: {compute_ms:.1f}ms | {HW_BADGE}"
        cv2.putText(frame, hud_text, (18, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 120), 1, cv2.LINE_AA)

        cv2.imshow("Student360 Unified Engine", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            print("\nUser pressed 'q'. Exiting loop gracefully...")
            break

finally:
    # ============================================================
    # 7. GRACEFUL RESOURCE CLEANUP
    # ============================================================
    print("\nReleasing Camera feed and OpenCV resources...")
    try:
        cap.release()
    except Exception as e:
        print("Camera release notice:", e)

    try:
        cv2.destroyAllWindows()
    except Exception as e:
        print("cv2.destroyAllWindows notice:", e)

    print("✅ Hardware & camera released successfully.\n")


# ============================================================
# 8. SAVE SESSION DATA TO CSV & GENERATE PDF
# ============================================================
print("Saving Session Data...")
date_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
csv_filename = f"attendance/session_summary_{date_str}.csv"
timeline_filename = f"attendance/behavior_timeline_{date_str}.csv"

if len(student_stats) > 0:
    df = pd.DataFrame.from_dict(student_stats, orient='index')
    df.index.name = 'Student_ID'
    df.reset_index(inplace=True)
    df.drop(columns=['last_seen_time', 'last_evidence_time'], inplace=True, errors='ignore')
    df = df.round(2)

    df.to_csv(csv_filename, index=False)

    # Save Behaviour Timeline
    timeline_rows = []
    for student, stats in student_stats.items():
        for event in stats.get("timeline", []):
            timeline_rows.append({
                "Student_ID": student,
                "Time": event["time"],
                "Behavior": event["behavior"]
            })

    timeline_df = pd.DataFrame(timeline_rows)
    timeline_df.to_csv(timeline_filename, index=False)
    print(f"Timeline saved: {timeline_filename}")

    # Generate PDF summary table
    pdf_filename = f"attendance/session_summary_{date_str}.pdf"
    try:
        fig, ax = plt.subplots(figsize=(24, 6))
        ax.axis('tight')
        ax.axis('off')
        plt.title("Student360 Session Summary", fontsize=16, fontweight='bold', pad=20)
        table = ax.table(
            cellText=df.astype(str).values.tolist(),
            colLabels=list(df.columns),
            loc='center',
            cellLoc='center'
        )
        table.auto_set_font_size(False)
        table.set_fontsize(12)
        table.scale(1.2, 1.5)
        plt.savefig(pdf_filename, format='pdf', bbox_inches='tight')
        plt.close()
        print(f"✅ Data saved successfully to: {csv_filename} AND {pdf_filename}")
    except Exception as e:
        print("PDF generation error:", e)

    print(df)

    # Upload CSV to Backend
    try:
        print("Uploading session to backend...")
        with open(csv_filename, "rb") as f:
            resp = requests.post("http://127.0.0.1:8000/upload-session", files={"file": f}, timeout=3.0)
            print("Session upload:", resp.json())
    except Exception as e:
        print("Upload session notice:", e)

    try:
        print("Uploading Behaviour Timeline...")
        with open(timeline_filename, "rb") as f:
            resp = requests.post("http://127.0.0.1:8000/upload-timeline", files={"file": f}, timeout=3.0)
            print("Timeline upload:", resp.json())
    except Exception as e:
        print("Upload timeline notice:", e)

else:
    print("No recognized students found in this session.")

print("Done!")