from fastapi import APIRouter, HTTPException
from database import db # Oyage database connection eka import karanna
from bson import ObjectId

router = APIRouter()

@router.post("/retrain")
async def retrain_ai_model():
    try:
        # 1. is_model_trained: False kiyala thiyena students lawa ganna
        untrained_students = list(db.students.find({"is_model_trained": False}))
        
        if not untrained_students:
            return {"message": "All students are already trained. No new data found."}

        trained_count = 0
        
        # 2. Eken eka video eka aran FaceNet vectors extract karanna
        for student in untrained_students:
            video_path = student.get("video_path")
            student_id = student.get("student_id")
            
            # TODO: Methanata oyage FaceNet/YOLOv8 video frame extraction code eka enna one
            print(f"Training model for {student_id} using video at {video_path}...")
            
            # 3. Train wela iwara unama database record eka True karanna
            db.students.update_one(
                {"_id": ObjectId(student["_id"])},
                {"$set": {"is_model_trained": True}}
            )
            trained_count += 1
            
        return {
            "status": "success",
            "message": f"Successfully retrained AI model for {trained_count} students.",
            "trained_count": trained_count
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))