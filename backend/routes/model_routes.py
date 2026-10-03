from fastapi import APIRouter, HTTPException, BackgroundTasks
from bson import ObjectId
import os
import cv2
import shutil

# Database collections import
from database import db
# Retraining pipeline and live hot-reload imports
from train_faces import train_face_recognition_model, extract_frames_from_video, DATASET_DIR
from routes.process_video import reload_face_models

router = APIRouter()

def execute_full_retraining_workflow():
    """Background task to extract frames, train FaceNet/SVM, reload engine, and update DB."""
    try:
        # 1. MongoDB eken is_model_trained: False thiyena studentslawa gannawa
        untrained_students = list(db.students.find({"is_model_trained": False}))
        
        if not untrained_students:
            print("ℹ️ No untrained students found in database. Retraining skipped.")
            return

        print(f"🚀 Found {len(untrained_students)} untrained student(s). Starting extraction...")

        for student in untrained_students:
            student_id = str(student.get("student_id", "")).strip().upper()
            video_path = student.get("video_path")
            
            if not student_id:
                continue

            # Student ge dataset folder eka hadanawa
            student_folder = os.path.join(DATASET_DIR, student_id)
            os.makedirs(student_folder, exist_ok=True)

            # Video path eka thiyenawanam frames extract karanawa
            if video_path and os.path.exists(video_path):
                frames_dir = os.path.join(student_folder, "extracted_frames")
                extract_frames_from_video(video_path, frames_dir, max_frames=30)
            else:
                # Video file eka direct uploads folder eke thiyeda balanawa
                alt_video = os.path.join("uploads", f"{student_id}.mp4")
                if os.path.exists(alt_video):
                    frames_dir = os.path.join(student_folder, "extracted_frames")
                    extract_frames_from_video(alt_video, frames_dir, max_frames=30)
                else:
                    print(f"⚠️ Video path not found for {student_id}, checking existing dataset...")

        # 2. FaceNet + SVM Retraining Script eka run karanawa
        result = train_face_recognition_model()

        if result.get("status") == "success":
            # 3. Live camera stream ekata aluth model eka hot-reload karanawa
            reload_face_models()

            # 4. Database records tika is_model_trained: True karanawa
            for student in untrained_students:
                db.students.update_one(
                    {"_id": ObjectId(student["_id"])},
                    {"$set": {"is_model_trained": True}}
                )
            print(f"✅ Successfully retrained model and updated database for {len(untrained_students)} students.")
        else:
            print("⚠️ Retraining did not complete:", result.get("message"))

    except Exception as e:
        print("❌ Error during background retraining workflow:", repr(e))


@router.post("/retrain")
async def retrain_ai_model(background_tasks: BackgroundTasks):
    try:
        # Check if there are untrained students in MongoDB
        untrained_count = db.students.count_documents({"is_model_trained": False})
        
        if untrained_count == 0:
            return {
                "status": "info",
                "message": "All students are already trained. No new video data found.",
                "untrained_count": 0
            }

        # Background task ekak vidihata initiate karanawa (Frontend freeze nowee thiyenna)
        background_tasks.add_task(execute_full_retraining_workflow)
        
        return {
            "status": "success",
            "message": f"Retraining pipeline initiated in background for {untrained_count} new student(s).",
            "untrained_count": untrained_count
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))