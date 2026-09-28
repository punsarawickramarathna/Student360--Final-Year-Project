from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
import shutil
import subprocess
import os
import cv2
import time

router = APIRouter()

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Global session tracker
active_ai_session = {
    "is_running": False,
    "mode": None,  # "classroom" or "exam"
    "cap": None
}

def generate_video_stream():
    global active_ai_session
    cap = cv2.VideoCapture(0)
    active_ai_session["cap"] = cap

    while active_ai_session["is_running"]:
        success, frame = cap.read()
        if not success:
            break

        mode = active_ai_session.get("mode", "classroom")
        color = (0, 255, 0) if mode == "classroom" else (0, 0, 255)

        # Live overlay indicator for preview
        cv2.putText(
            frame,
            f"STUDENT360 LIVE: {mode.upper()} MODE",
            (20, 35),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            color,
            2
        )
        cv2.putText(
            frame,
            f"Status: Tracking Active | {time.strftime('%H:%M:%S')}",
            (20, 70),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (255, 255, 255),
            1
        )

        # TODO: Methanata FaceNet + YOLOv8 inference frame-by-frame inject wewi

        # Encode frame to JPEG
        ret, buffer = cv2.imencode('.jpg', frame)
        if not ret:
            continue

        frame_bytes = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

    cap.release()

@router.get("/video-feed")
async def video_feed():
    """Live MJPEG video stream endpoint for the frontend preview."""
    if not active_ai_session["is_running"]:
        raise HTTPException(status_code=400, detail="Camera session is not active")
    return StreamingResponse(
        generate_video_stream(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )

@router.post("/start-camera")
async def start_camera(data: dict):
    global active_ai_session
    mode = data.get("mode", "classroom")
    active_ai_session["is_running"] = True
    active_ai_session["mode"] = mode
    return {"status": "success", "mode": mode, "message": f"{mode.capitalize()} mode started"}

@router.post("/stop-camera")
async def stop_camera():
    global active_ai_session
    active_ai_session["is_running"] = False
    if active_ai_session["cap"]:
        active_ai_session["cap"].release()
    mode = active_ai_session["mode"]
    active_ai_session["mode"] = None
    return {"status": "success", "message": "Session ended and behavior log recorded"}

@router.post("/process-video")
async def process_video(file: UploadFile = File(...)):
    filepath = os.path.join(UPLOAD_FOLDER, file.filename)
    with open(filepath, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    subprocess.run(["python", "../ai_engine/unified_pipeline.py", filepath])
    return {"message": "Video Processed"}