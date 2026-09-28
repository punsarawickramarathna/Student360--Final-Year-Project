from fastapi import APIRouter, HTTPException
from database import appeals_collection
from datetime import datetime
from bson import ObjectId

router = APIRouter()

# 1. Student / Admin Appeals Fetch (GET)
@router.get("")
@router.get("/")
def get_all_appeals():
    try:
        appeals = list(appeals_collection.find({}))
        for a in appeals:
            a["_id"] = str(a["_id"])
        return appeals
    except Exception as e:
        return []

# 2. Student Appeal Submit (POST)
@router.post("")
@router.post("/")
def create_appeal(data: dict):
    try:
        data["created_at"] = datetime.utcnow().isoformat()
        data["status"] = data.get("status", "Pending")
        res = appeals_collection.insert_one(data)
        return {"message": "Appeal submitted", "id": str(res.inserted_id)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 3. Admin Decision Update (PUT)
@router.put("/{appeal_id}")
def update_appeal_status(appeal_id: str, data: dict):
    try:
        appeals_collection.update_one(
            {"_id": ObjectId(appeal_id)},
            {"$set": {
                "status": data.get("status", "Approved"),
                "admin_response": data.get("admin_response", ""),
                "reviewed_by": data.get("reviewed_by", "Admin"),
                "updated_at": datetime.utcnow().isoformat()
            }}
        )
        return {"message": "Success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))