import cv2
import numpy as np
import joblib
import os
import time
import pandas as pd
from datetime import datetime
from ultralytics import YOLO
from mtcnn import MTCNN
from keras_facenet import FaceNet
import matplotlib.pyplot as plt  
import requests

print("🚀 Starting Student360 Ultimate Engine with ByteTrack...")
student_stats = {}
tracker_to_student_map = {}
# ==========================================
# 1. Load All Models
# ==========================================
print("Loading YOLO Behavior Model...")
yolo_model = YOLO("models/classroom_model.pt") # Change to classroom_model.pt if needed

print("Loading Face Detection & Embedding Models...")
detector = MTCNN()
embedder = FaceNet()

print("Loading Face Recognition SVM Model...")
face_svm = joblib.load("models/face_model.pkl")
label_encoder = joblib.load("models/label_encoder.pkl")

print("✅ All Models Loaded Successfully!\n")

# ==========================================
# 2. Setup Data Dictionaries & Folders
# ==========================================
student_stats = {}

# --- ALUTH BYTETRACK MEMORY DICTIONARY ---
tracker_to_student_map = {} 
# -----------------------------------------

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
            }
        )
        print("Session created:", response.json())
    except Exception as e:
        print("Session creation failed:", e)

create_session()
# ==========================================
# 3. Start Video Processing
# ==========================================
video_path = "data/test_video.mp4" 
cap = cv2.VideoCapture(video_path)

cv2.namedWindow("Student360 Unified Engine", cv2.WINDOW_NORMAL)
cv2.resizeWindow("Student360 Unified Engine", 1280, 720) 

# ByteTrack ekata digatama frames one nisa apita skip karanna awashya na, 
# mokada face recognition digatama run wenne nathi nisa speed eka hodatama wadi!

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        print("Video ended or cannot read frame.")
        break
        
    current_time = time.time()
    
    # --- ALUTH TRACKING LOGIC EKA (predict wenuwata track use karanawa) ---
    results = yolo_model.track(frame, persist=True, tracker="bytetrack.yaml", conf=0.5, verbose=False)
    
    for result in results:
        boxes = result.boxes
        for box in boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            cls_id = int(box.cls[0])
            behavior_label = yolo_model.names[cls_id]
            
            # ByteTrack eken dena ID eka gannawa
            track_id = int(box.id[0]) if box.id is not None else None
            
            if track_id is None:
                continue # ID ekak set wela nattam next ekata yanawa
            
            student_id = "Unknown"
            confidence_str = ""
            
            # --- IDENTITY CACHING (Patta Speed Optimization eka) ---
            # Kalin me Track ID eka aduragena thiyenawada balanawa
            if track_id in tracker_to_student_map:
                student_id = tracker_to_student_map[track_id]
                # Kalin aduragena nam, aye MTCNN face detection karanne na! (Time saved!)
            else:
                # Aduragena nattam witharak Face Recognition eka run karanawa
                person_crop = frame[y1:y2, x1:x2]
                
                if person_crop.size > 0 and person_crop.shape[0] >= 20 and person_crop.shape[1] >= 20:
                    rgb_crop = cv2.cvtColor(person_crop, cv2.COLOR_BGR2RGB)
                    
                    try:
                        faces = detector.detect_faces(rgb_crop)
                    except Exception as e:
                        faces = []
                    
                    if faces:
                        fx, fy, fw, fh = faces[0]['box']
                        fx, fy = max(0, fx), max(0, fy)
                        face_img = rgb_crop[fy:fy+fh, fx:fx+fw]
                        
                        if face_img.shape[0] >= 20 and face_img.shape[1] >= 20:
                            face_resized = cv2.resize(face_img, (160, 160))
                            embedding = embedder.embeddings([face_resized])
                            
                            probs = face_svm.predict_proba(embedding)
                            confidence = np.max(probs)
                            pred = np.argmax(probs)
                            
                            THRESHOLD = 0.75 
                            if confidence >= THRESHOLD:
                                student_id = label_encoder.inverse_transform([pred])[0]
                                confidence_str = f"({confidence:.2f})"
                                
                                # Aluth lamayawa Tracker ID ekata link karanawa!
                                tracker_to_student_map[track_id] = student_id
            # -----------------------------------------------------------

            # ==========================================
            # 4. Update Time Durations in Dictionary
            # ==========================================
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
                # ==========================================
                # Behaviour Timeline
                # ==========================================

                if student_stats[student_id]["last_behavior"] != behavior_label:

                    current_clock = datetime.now().strftime("%H:%M:%S")

                    student_stats[student_id]["timeline"].append({

                        "time": current_clock,

                        "behavior": behavior_label

                    })

                    student_stats[student_id]["last_behavior"] = behavior_label
                
                if time_diff < 2.0:
                    key_name = f"{behavior_label}_sec"
                    if key_name in student_stats[student_id]:
                        student_stats[student_id][key_name] += time_diff
                
                student_stats[student_id]["last_seen_time"] = current_time

            # ==========================================
            # 5. Draw on Screen & Capture Evidence
            # ==========================================
            color = (0, 0, 255) if behavior_label in ["cheating", "sleeping", "phone_use"] else (0, 255, 0)
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            
            # Tracker ID ekath screen eke pennamu (e.g., [T5] IT0320)
            final_label = f"[T{track_id}] {student_id} {confidence_str} | {behavior_label}"
            (w, h), _ = cv2.getTextSize(final_label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
            cv2.rectangle(frame, (x1, y1 - 25), (x1 + w, y1), color, -1)
            cv2.putText(frame, final_label, (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

            # --- AUTOMATED EVIDENCE CAPTURE ---
            if student_id != "Unknown" and behavior_label in ["cheating", "sleeping", "phone_use"]:
                time_since_last_pic = current_time - student_stats[student_id]["last_evidence_time"]
                
                if time_since_last_pic > 15.0:
                    date_string = datetime.now().strftime("%Y%m%d_%H%M%S")
                    evidence_filename = f"evidence/{student_id}_{behavior_label}_{date_string}.jpg"
                    cv2.imwrite(evidence_filename, frame)
                    try:

                        with open(evidence_filename, "rb") as img:

                            response = requests.post(

                                "http://127.0.0.1:8000/upload-evidence",

                                files={

                                    "file": (

                                        os.path.basename(evidence_filename),
                                        img,
                                        "image/jpeg"

                                    )

                                },

                                data={

                                    "student_id": student_id,

                                    "behavior": behavior_label

                                }

                            )

                        print(response.json())

                    except Exception as e:

                        print("Evidence upload failed:", e)
                    print(f"📸 EVIDENCE CAPTURED: {evidence_filename}")
                    student_stats[student_id]["last_evidence_time"] = current_time

    cv2.imshow("Student360 Unified Engine", frame)
    
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()

# ==========================================
# 6. Save Data to CSV & PDF when closing
# ==========================================
print("\nSaving Session Data...")
if len(student_stats) > 0:
    df = pd.DataFrame.from_dict(student_stats, orient='index')
    df.index.name = 'Student_ID'
    df.reset_index(inplace=True)
    df.drop(columns=['last_seen_time', 'last_evidence_time'], inplace=True, errors='ignore')
    df = df.round(2)
    
    date_str = datetime.now().strftime("%Y-%m-%d_%H-%M")
    
    csv_filename = f"attendance/session_summary_{date_str}.csv"
    df.to_csv(csv_filename, index=False)
    # ==========================================
    # Save Behaviour Timeline
    # ==========================================

    timeline_rows = []

    for student, stats in student_stats.items():

        for event in stats["timeline"]:

            timeline_rows.append({

                "Student_ID": student,

                "Time": event["time"],

                "Behavior": event["behavior"]

            })

    timeline_df = pd.DataFrame(timeline_rows)

    timeline_filename = f"attendance/behavior_timeline_{date_str}.csv"

    timeline_df.to_csv(

        timeline_filename,

        index=False

    )

    print(f"Timeline saved : {timeline_filename}")
    
    pdf_filename = f"attendance/session_summary_{date_str}.pdf"
    fig, ax = plt.subplots(figsize=(24, 6)) 
    ax.axis('tight')
    ax.axis('off')
    plt.title("Session Summary", fontsize=16, fontweight='bold', pad=20)
    table = ax.table(cellText=df.values, colLabels=df.columns, loc='center', cellLoc='center')
    table.auto_set_font_size(False)
    table.set_fontsize(12)
    table.scale(1.2, 1.5)
    plt.savefig(pdf_filename, format='pdf', bbox_inches='tight')
    plt.close()
    
    print(f"✅ Data saved successfully to: {csv_filename} AND {pdf_filename}")
    print(df) 
else:
    print("No recognized students found in this session.")

print("Done!")


# ==========================================
# Upload CSV to Backend
# ==========================================

if len(student_stats) > 0:

    print("Uploading session to backend...")

    with open(csv_filename, "rb") as f:

        response = requests.post(
            "http://127.0.0.1:8000/upload-session",
            files={"file": f}
        )

    print(response.json())

    # -----------------------------
    # Upload Behaviour Timeline
    # -----------------------------
    print("Uploading Behaviour Timeline...")

    with open(timeline_filename, "rb") as f:

        response = requests.post(

            "http://127.0.0.1:8000/upload-timeline",

            files={

                "file": f

            }

        )

    print(response.json())

else:

    print("No CSV generated. Upload skipped.")

    