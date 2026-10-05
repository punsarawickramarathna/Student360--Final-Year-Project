from fastapi import (
    APIRouter,
    HTTPException,
    BackgroundTasks
)

from train_faces import (
    retrain_registered_students,
    get_training_state
)


router = APIRouter()


# ============================================================
# AUTOMATIC / MANUAL FACE MODEL RETRAINING
# ============================================================

@router.post("/retrain")
async def retrain_ai_model(
    background_tasks: BackgroundTasks
):

    try:

        current_state = get_training_state()

        # ----------------------------------------------------
        # Already running
        # ----------------------------------------------------

        if current_state.get("status") == "running":

            return {
                "status": "busy",
                "message": (
                    "Face recognition training "
                    "is already running."
                )
            }

        # ----------------------------------------------------
        # Find untrained students
        # ----------------------------------------------------

        from database import db

        untrained_students = list(
            db.students.find(
                {
                    "is_model_trained": {
                        "$ne": True
                    }
                }
            )
        )

        if not untrained_students:

            return {
                "status": "info",
                "message": (
                    "All registered students are "
                    "already included in the face model."
                ),
                "untrained_count": 0
            }

        student_ids = [
            str(
                student.get(
                    "student_id",
                    ""
                )
            ).strip().upper()

            for student in untrained_students

            if student.get("student_id")
        ]

        # ----------------------------------------------------
        # Mark training as pending
        # ----------------------------------------------------

        for student in untrained_students:

            db.students.update_one(
                {
                    "_id": student["_id"]
                },
                {
                    "$set": {
                        "face_training_status": "pending",
                        "face_training_error": ""
                    }
                }
            )

        # ----------------------------------------------------
        # Start background training
        # ----------------------------------------------------

        background_tasks.add_task(
            retrain_registered_students,
            student_ids
        )

        return {
            "status": "success",
            "message": (
                "Face recognition retraining "
                "started successfully."
            ),
            "untrained_count": len(student_ids),
            "student_ids": student_ids
        }

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# ============================================================
# TRAINING STATUS
# ============================================================

@router.get("/status")
async def get_model_training_status():

    try:

        state = get_training_state()

        return {
            "status": "success",
            "training": state
        }

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )