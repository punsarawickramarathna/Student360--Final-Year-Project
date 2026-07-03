from fastapi import APIRouter, UploadFile, File
import pandas as pd

from database import attendance_collection
from database import behavior_collection

router = APIRouter()


@router.post("/upload-session")
async def upload_session(file: UploadFile = File(...)):

    df = pd.read_csv(file.file)

    inserted = 0

    for _, row in df.iterrows():

        attendance_collection.insert_one({

            "student_id": row["Student_ID"],

            "date": row["Date"],

            "arrival_time": row["Arrival_Time"]

        })

        behavior_collection.insert_one({

            "student_id": row["Student_ID"],

            "cheating": row["cheating_sec"],

            "non_cheating": row["non_cheating_sec"],

            "attentive": row["attentive_sec"],

            "sleeping": row["sleeping_sec"],

            "phone_use": row["phone_use_sec"],

            "not_attentive": row["not_attentive_sec"]

        })

        inserted += 1

    return {

        "message": "Upload Successful",

        "students": inserted

    }