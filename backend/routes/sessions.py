from fastapi import APIRouter
from database import sessions_collection

router = APIRouter()

# ==========================================
# Create New Lecture Session
# ==========================================
@router.post("/create-session")
def create_session(data: dict):

    sessions_collection.insert_one(data)

    return {
        "message": "Session Created"
    }

# ==========================================
# Get All Sessions
# ==========================================
@router.get("/sessions")
def get_sessions():

    sessions = list(
        sessions_collection.find({}, {"_id": 0})
    )

    return {
        "count": len(sessions),
        "data": sessions
    }