import os
import cv2
import joblib
import numpy as np
from mtcnn import MTCNN
from keras_facenet import FaceNet
from sklearn.svm import SVC
from sklearn.preprocessing import LabelEncoder

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET_DIR = os.path.join(BASE_DIR, "dataset")
MODELS_DIR = os.path.join(BASE_DIR, "models")
AI_ENGINE_MODELS_DIR = os.path.abspath(os.path.join(BASE_DIR, "../ai_engine/models"))

def extract_frames_from_video(video_path, output_dir, max_frames=30):
    """Student video clip eken faces thiyena frames extract kirima."""
    os.makedirs(output_dir, exist_ok=True)
    cap = cv2.VideoCapture(video_path)
    count = 0
    saved = 0
    while cap.isOpened() and saved < max_frames:
        ret, frame = cap.read()
        if not ret:
            break
        # Frame 5n 5ta eka frame ekak save karanawa
        if count % 5 == 0:
            frame_path = os.path.join(output_dir, f"frame_{saved}.jpg")
            cv2.imwrite(frame_path, frame)
            saved += 1
        count += 1
    cap.release()
    print(f"📸 Extracted {saved} frames from {os.path.basename(video_path)}")

def train_face_recognition_model():
    print("🚀 Starting FaceNet Feature Extraction & Retraining Pipeline...")
    os.makedirs(MODELS_DIR, exist_ok=True)
    os.makedirs(AI_ENGINE_MODELS_DIR, exist_ok=True)

    if not os.path.exists(DATASET_DIR):
        os.makedirs(DATASET_DIR, exist_ok=True)
        return {"status": "error", "message": f"Dataset directory '{DATASET_DIR}' was empty or not found."}

    detector = MTCNN()
    embedder = FaceNet()

    X = []
    y = []

    for student_folder in os.listdir(DATASET_DIR):
        student_path = os.path.join(DATASET_DIR, student_folder)
        if not os.path.isdir(student_path):
            continue

        student_id = student_folder
        print(f"🔍 Processing student dataset: {student_id}")

        for item in os.listdir(student_path):
            item_path = os.path.join(student_path, item)

            # 1. Video file ekak thiyenawa nam frames extract karanawa
            if item.lower().endswith(('.mp4', '.avi', '.mov', '.mkv')):
                frames_dir = os.path.join(student_path, "extracted_frames")
                extract_frames_from_video(item_path, frames_dir)
                if os.path.exists(frames_dir):
                    for f_name in os.listdir(frames_dir):
                        f_path = os.path.join(frames_dir, f_name)
                        img = cv2.imread(f_path)
                        if img is not None:
                            rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                            try:
                                faces = detector.detect_faces(rgb)
                            except Exception:
                                faces = []
                            if faces:
                                fx, fy, fw, fh = faces[0]["box"]
                                fx, fy = max(0, fx), max(0, fy)
                                face_img = rgb[fy:fy + fh, fx:fx + fw]
                                if face_img.shape[0] >= 20 and face_img.shape[1] >= 20:
                                    face_resized = cv2.resize(face_img, (160, 160))
                                    emb = embedder.embeddings([face_resized])[0]
                                    X.append(emb)
                                    y.append(student_id)

            # 2. Direct photos thiyenawa nam
            elif item.lower().endswith(('.jpg', '.jpeg', '.png')):
                img = cv2.imread(item_path)
                if img is not None:
                    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                    try:
                        faces = detector.detect_faces(rgb)
                    except Exception:
                        faces = []
                    if faces:
                        fx, fy, fw, fh = faces[0]["box"]
                        fx, fy = max(0, fx), max(0, fy)
                        face_img = rgb[fy:fy + fh, fx:fx + fw]
                        if face_img.shape[0] >= 20 and face_img.shape[1] >= 20:
                            face_resized = cv2.resize(face_img, (160, 160))
                            emb = embedder.embeddings([face_resized])[0]
                            X.append(emb)
                            y.append(student_id)

    if len(X) == 0:
        print("⚠️ No face samples found in dataset to retrain.")
        return {"status": "warning", "message": "No valid face samples found for retraining."}

    # SVM Classifier eka train kirima
    encoder = LabelEncoder()
    y_encoded = encoder.fit_transform(y)

    svm = SVC(kernel="linear", probability=True)
    svm.fit(X, y_encoded)

    # backend/models saha ai_engine/models dekema save kirima
    for target_dir in [MODELS_DIR, AI_ENGINE_MODELS_DIR]:
        os.makedirs(target_dir, exist_ok=True)
        joblib.dump(svm, os.path.join(target_dir, "face_model.pkl"))
        joblib.dump(encoder, os.path.join(target_dir, "label_encoder.pkl"))

    print(f"✅ Retraining complete with {len(X)} samples across {len(encoder.classes_)} students!")
    return {
        "status": "success",
        "samples": len(X),
        "students": [str(c) for c in encoder.classes_],
        "message": f"Successfully retrained model with {len(encoder.classes_)} students."
    }

if __name__ == "__main__":
    train_face_recognition_model()