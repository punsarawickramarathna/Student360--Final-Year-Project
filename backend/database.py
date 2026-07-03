from pymongo import MongoClient

MONGO_URL = "mongodb://localhost:27017"

client = MongoClient(MONGO_URL)

db = client["student360"]

students_collection = db["students"]
attendance_collection = db["attendance"]
behavior_collection = db["behavior_logs"]
appeals_collection = db["appeals"]
users_collection = db["users"]
evidence_collection = db["evidence"]
timeline_collection = db["timeline"]
sessions_collection = db["sessions"]