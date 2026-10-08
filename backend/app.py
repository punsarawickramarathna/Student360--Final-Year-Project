# ============================================================
# STUDENT360 BACKEND - CORE APPLICATION SERVER
# ============================================================

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# Route Imports
from routes.auth_routes import router as auth_router
from routes.students import router as students_router
from routes.attendance import router as attendance_router
from routes.behavior import router as behavior_router
from routes.appeals import router as appeals_router
from routes.upload_session import router as upload_session_router
from routes.dashboard import router as dashboard_router
from routes.process_video import router as process_router
from routes.upload import router as upload_router
from routes.evidence import router as evidence_router
from routes.timeline import router as timeline_router
from routes.sessions import router as sessions_router
from routes.email import router as email_router
from routes.profile import router as profile_router
from routes.users import router as users_router
from routes.register import router as register_router
from routes.model_routes import router as model_router

app = FastAPI(title="Student360 Backend", version="1.0.0")

# ============================================================
# CORS MIDDLEWARE
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# STATIC FILES SERVING (UPLOADS & REAL EVIDENCE SNAPSHOTS)
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
EVIDENCE_DIR = os.path.join(UPLOAD_DIR, "evidence")

# Ensure evidence storage directories exist
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(EVIDENCE_DIR, exist_ok=True)

# Mount both parent /uploads and direct /evidence-images paths
app.mount(
    "/uploads",
    StaticFiles(directory=UPLOAD_DIR),
    name="uploads"
)
app.mount(
    "/evidence-images",
    StaticFiles(directory=EVIDENCE_DIR),
    name="evidence-images"
)

# ============================================================
# BASE ROUTERS
# ============================================================

app.include_router(auth_router)
app.include_router(students_router)
app.include_router(attendance_router)
app.include_router(behavior_router)
app.include_router(upload_session_router)
app.include_router(dashboard_router)

# ============================================================
# STUDENT360 AI ENGINE & PIPELINE ROUTERS
# ============================================================

app.include_router(
    process_router,
    prefix="/api/ai-engine",
    tags=["AI Engine"]
)
app.include_router(upload_router)

# Evidence routes mounted for direct and prefixed API access
app.include_router(evidence_router, tags=["Evidence"])
app.include_router(evidence_router, prefix="/api/evidence", tags=["Evidence API"])

app.include_router(timeline_router)
app.include_router(sessions_router)
app.include_router(email_router)
app.include_router(profile_router)
app.include_router(register_router)

# ============================================================
# PREFIXED API ROUTERS
# ============================================================

app.include_router(users_router, prefix="/api/users", tags=["Users"])
app.include_router(model_router, prefix="/api/model", tags=["Model Training"])

# Appeals Routes
app.include_router(appeals_router, prefix="/api/appeals", tags=["Appeals API"])
app.include_router(appeals_router, prefix="/appeals", tags=["Appeals Direct"])

# ============================================================
# ROOT HEALTH ENDPOINT
# ============================================================

@app.get("/")
def home():
    return {
        "status": "online",
        "service": "Student360 Backend Core",
        "message": "Student360 Backend Running Successfully"
    }