from fastapi import APIRouter, UploadFile, File
from database import attendance_collection, behavior_collection
import pandas as pd
from io import StringIO
from datetime import datetime

router = APIRouter()


@router.post("/upload-video-session")
async def upload_session(file: UploadFile = File(...)):

    contents = await file.read()

    df = pd.read_csv(StringIO(contents.decode("utf-8")))

    inserted = 0

    for _, row in df.iterrows():

        attendance_collection.insert_one({

            "student_id": row["Student_ID"],
            "date": row["Date"],
            "arrival_time": row["Arrival_Time"],
            "created_at": datetime.utcnow()

        })

        behavior_collection.insert_one({

            "student_id": row["Student_ID"],
            "date": row["Date"],
            "cheating": row["cheating_sec"],
            "attentive": row["attentive_sec"],
            "sleeping": row["sleeping_sec"],
            "phone_use": row["phone_use_sec"],
            "not_attentive": row["not_attentive_sec"],
            "created_at": datetime.utcnow()

        })

        inserted += 1

    return {
        "message": "Session uploaded successfully",
        "students": inserted
    }