from fastapi import APIRouter, UploadFile, File, Form
from database import evidence_collection
import os
import shutil
from datetime import datetime

router = APIRouter()

UPLOAD_FOLDER = "uploads/evidence"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@router.post("/upload-evidence")
async def upload_evidence(
    student_id: str = Form(...),
    behavior: str = Form(...),
    file: UploadFile = File(...)
):

    filename = f"{student_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"

    filepath = os.path.join(UPLOAD_FOLDER, filename)

    with open(filepath, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    evidence_collection.insert_one({

        "student_id": student_id,
        "behavior": behavior,
        "image": filename,
        "date": datetime.now()

    })

    return {
        "message":"Evidence saved"
    }

@router.get("/evidence/{student_id}")

def get_evidence(student_id:str):

    data=list(

        evidence_collection.find(

            {"student_id":student_id},

            {"_id":0}

        )

    )

    return {

        "count":len(data),

        "data":data

    }