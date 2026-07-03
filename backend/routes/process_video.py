from fastapi import APIRouter
from fastapi import UploadFile
from fastapi import File

import shutil
import subprocess
import os

router = APIRouter()


UPLOAD_FOLDER = "uploads"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


@router.post("/process-video")

async def process_video(file: UploadFile = File(...)):

    filepath = os.path.join(

        UPLOAD_FOLDER,

        file.filename

    )

    with open(filepath, "wb") as buffer:

        shutil.copyfileobj(

            file.file,

            buffer

        )

    subprocess.run([

        "python",

        "../ai_engine/unified_pipeline.py",

        filepath

    ])

    return {

        "message": "Video Processed"

    }