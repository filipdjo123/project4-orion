# player_tracking_service/app/main.py

from fastapi import FastAPI, UploadFile, File, Form, Body, HTTPException
from app.tracker import PlayerTracker
from app.models import PlayerTrackingResponse
import os, uuid, shutil

app = FastAPI(title="Player Tracking Microservice")
tracker = PlayerTracker()

UPLOAD_DIR = "uploaded_videos"
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_EXTS = (".mp4", ".mov", ".avi", ".mkv")

@app.get("/health")
async def health():
    return {"status": "ok", "model": "player_tracking", "version": "v0"}

# Option A: Multipart upload (saves ONCE, then runs the model)
@app.post("/track-players", response_model=PlayerTrackingResponse)
async def track_players(
    video: UploadFile = File(...),
    location: str = Form("unknown"),
    sampling_fps: int = Form(5),
    conf_threshold: float = Form(0.5),
):
    # Validate extension
    if not video.filename or not video.filename.lower().endswith(ALLOWED_EXTS):
        raise HTTPException(status_code=400, detail="Unsupported video format")

    file_id = str(uuid.uuid4())
    video_path = os.path.join(UPLOAD_DIR, f"{file_id}_{video.filename}")

    # Save ONCE so OpenCV/FFmpeg can read it
    try:
        with open(video_path, "wb") as f:
            shutil.copyfileobj(video.file, f)
    finally:
        try:
            video.file.close()
        except Exception:
            pass

    # Run the model directly on that saved file (no second save)
    try:
        result = tracker.process_video(
            video_path,
            sampling_fps=sampling_fps,
            conf_threshold=conf_threshold,
            location=location,
        )
        # Ensure helpful metadata in summary
        if hasattr(result, "summary") and isinstance(result.summary, dict):
            result.summary.setdefault("location", location)
            result.summary.setdefault("sampling_fps", sampling_fps)
            result.summary.setdefault("conf_threshold", conf_threshold)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Option B: JSON with shared path (NO saving at all; requires shared volume)
@app.post("/track-players-by-path", response_model=PlayerTrackingResponse)
async def track_players_by_path(
    video_path: str = Body(..., embed=True),
    location: str = Body("unknown"),
    sampling_fps: int = Body(5),
    conf_threshold: float = Body(0.5),
):
    if not os.path.exists(video_path):
        raise HTTPException(status_code=404, detail="video_path not found")

    try:
        result = tracker.process_video(
            video_path,
            sampling_fps=sampling_fps,
            conf_threshold=conf_threshold,
            location=location,
        )
        if hasattr(result, "summary") and isinstance(result.summary, dict):
            result.summary.setdefault("location", location)
            result.summary.setdefault("sampling_fps", sampling_fps)
            result.summary.setdefault("conf_threshold", conf_threshold)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
