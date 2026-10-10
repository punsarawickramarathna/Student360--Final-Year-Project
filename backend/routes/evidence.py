from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from database import evidence_collection
import os
import shutil
from datetime import datetime
import re

router = APIRouter()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads", "evidence")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@router.post("/upload-evidence")
async def upload_evidence(
    student_id: str = Form(...),
    behavior: str = Form(...),
    file: UploadFile = File(...)
):
    try:
        filename = f"{student_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        filepath = os.path.join(UPLOAD_FOLDER, filename)

        with open(filepath, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        evidence_collection.insert_one({
            "student_id": student_id,
            "behavior": behavior,
            "image": filename,
            "image_path": f"evidence/{filename}",
            "date": datetime.now(),
            "mode": "classroom",
            "source": "live_surveillance"
        })

        return {"status": "success", "message": "Evidence saved", "filename": filename}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Route handles both direct and api-prefixed calls explicitly
@router.get("/evidence/{student_id}")
@router.get("/api/evidence/{student_id}")
def get_evidence(student_id: str):
    try:
        # Case-insensitive exact match
        regex_query = {"$regex": f"^{re.escape(student_id.strip())}$", "$options": "i"}
        records = list(evidence_collection.find({"student_id": regex_query}).sort("date", -1))

        formatted_data = []
        for r in records:
            filename = r.get("image", "")
            raw_date = r.get("date")
            
            # Format datetime safely
            if isinstance(raw_date, datetime):
                date_str = raw_date.strftime("%Y-%m-%d %H:%M:%S")
            else:
                date_str = str(raw_date or "N/A")

            formatted_data.append({
                "student_id": r.get("student_id"),
                "behavior": r.get("behavior", "violation"),
                "filename": filename,
                "image_url": f"http://localhost:8000/uploads/evidence/{filename}",
                "date": date_str,
                "mode": r.get("mode", "classroom"),
                "source": r.get("source", "live_surveillance")
            })

        return {
            "status": "success",
            "count": len(formatted_data),
            "data": formatted_data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))