import pandas as pd

from fastapi import APIRouter, UploadFile, File

from database import timeline_collection

router = APIRouter()


@router.post("/upload-timeline")

async def upload_timeline(

    file: UploadFile = File(...)

):

    df = pd.read_csv(file.file)

    timeline_collection.insert_many(

        df.to_dict("records")

    )

    return {

        "message": "Timeline Uploaded"

    }


@router.get("/timeline")

def get_timeline():

    data = list(

        timeline_collection.find(

            {},

            {"_id":0}

        )

    )

    return {

        "count": len(data),

        "data": data

    }