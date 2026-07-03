from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes.auth_routes import router as auth_router
from routes.students import router as students_router
from routes.attendance import router as attendance_router
from routes.behavior import router as behavior_router
from routes.appeals import router as appeals_router
from routes.upload_session import router as upload_router
from routes.dashboard import router as dashboard_router
from routes.process_video import router as process_router
from routes.upload import router as upload_router
from routes.evidence import router as evidence_router
from fastapi.staticfiles import StaticFiles
from routes.timeline import router as timeline_router
from routes.sessions import router as sessions_router
from routes.email import router as email_router
from routes.profile import router as profile_router
from routes.users import router as users_router

app = FastAPI(title="Student360 Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(students_router)
app.include_router(attendance_router)
app.include_router(behavior_router)
app.include_router(appeals_router)
app.include_router(upload_router)
app.include_router(dashboard_router)
app.include_router(process_router)
app.include_router(evidence_router)
app.include_router(timeline_router)
app.include_router(sessions_router)
app.include_router(email_router)
app.include_router(profile_router)
app.include_router(users_router)


@app.get("/")
def home():
    return {
        "message": "Student360 Backend Running"
    }

app.mount(
    "/uploads",
    StaticFiles(directory="uploads"),
    name="uploads"
)