# crowd_monitoring_service/app/main.py
from fastapi import FastAPI, Body, UploadFile, File, HTTPException
from app.monitor import CrowdMonitor
import cv2, os, uuid, shutil, math, time


app = FastAPI(title="Crowd Monitoring Microservice")
monitor = CrowdMonitor()

UPLOAD_DIR = "uploaded_videos"
os.makedirs(UPLOAD_DIR, exist_ok=True)

def _sample_indices(total_frames: int, fps: float, every_s: int):
    step = max(int(round(fps * every_s)), 1)
    return list(range(0, total_frames, step))

def _timestamp(frame_idx: int, fps: float) -> float:
    return round(frame_idx / max(fps, 1.0), 3)

@app.post("/crowd-from-video-by-path")
async def crowd_from_video_by_path(
    video_path: str = Body(..., embed=True),
    sample_every_s: int = Body(5),
):
    if not os.path.exists(video_path):
        raise HTTPException(status_code=404, detail="video_path not found")

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise HTTPException(status_code=400, detail="cannot open video")

    fps = cap.get(cv2.CAP_PROP_FPS) or 0.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    if fps <= 0 or total_frames <= 0:
        cap.release()
        raise HTTPException(status_code=400, detail="invalid video metadata")

    indices = _sample_indices(total_frames, fps, sample_every_s)
    results = []

    for idx in indices:
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ok, frame = cap.read()
        if not ok:
            continue

        # === Pass frame to ML model (in-memory preferred) ===
        out = monitor.analyze_frame_np(frame)   # expects np.ndarray (H,W,C) BGR

        # If your model only accepts file paths, use:
        # tmp_path = f"frame_{uuid.uuid4().hex[:8]}.png"
        # cv2.imwrite(tmp_path, frame)
        # out = monitor.analyze_frame(tmp_path)
        # os.remove(tmp_path)

        results.append({
            "frame_index": idx,
            "timestamp_s": _timestamp(idx, fps),
            "count": int(out.get("count", 0)),
            "heatmap_path": out.get("heatmap_path"),  # optional if you save heatmaps to disk
            "extras": {k: v for k, v in out.items() if k not in {"count", "heatmap_path"}},
        })

    cap.release()

    return {
        "model": "crowd_monitor_v0",
        "video_info": {
            "path": video_path,
            "fps": fps,
            "total_frames": total_frames,
            "duration_s": round(total_frames / max(fps, 1.0), 3),
            "sample_every_s": sample_every_s,
            "frames_processed": len(results),
        },
        "results": results,
        "summary": {
            "avg_count": (sum(r["count"] for r in results) / max(len(results), 1)) if results else 0,
            "max_count": max((r["count"] for r in results), default=0),
            "min_count": min((r["count"] for r in results), default=0),
        },
    }

# Multipart version (when no shared volume): saves once, then reuses the by-path logic
@app.post("/crowd-from-video")
async def crowd_from_video(video: UploadFile = File(...), sample_every_s: int = Body(5)):
    if not video.filename.lower().endswith((".mp4", ".mov", ".avi", ".mkv")):
        raise HTTPException(status_code=400, detail="unsupported video format")

    vid_id = uuid.uuid4().hex
    save_path = os.path.join(UPLOAD_DIR, f"{vid_id}_{video.filename}")
    try:
        with open(save_path, "wb") as f:
            shutil.copyfileobj(video.file, f)
    finally:
        try: video.file.close()
        except Exception: pass

    return await crowd_from_video_by_path(video_path=save_path, sample_every_s=sample_every_s)
