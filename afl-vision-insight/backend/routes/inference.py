# routes/inference.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Literal, Dict, Any, Optional
from pathlib import Path
import os
import httpx

# If storage is a sibling module inside backend/, this import is fine.
# If you're packaging, prefer: from backend.storage import get_upload
from storage import get_upload

router = APIRouter()

# -------------------------------
# Service configuration (env vars)
# -------------------------------
PLAYER_SVC_URL  = os.getenv("PLAYER_SVC_URL",  "http://127.0.0.1:8001")
PLAYER_SVC_MODE = os.getenv("PLAYER_SVC_MODE", "path").lower()   # "path" | "upload"

CROWD_SVC_URL   = os.getenv("CROWD_SVC_URL",   "http://127.0.0.1:8002")
CROWD_SVC_MODE  = os.getenv("CROWD_SVC_MODE",  "path").lower()   # "path" | "upload"

# If your backend serves StaticFiles(directory="static") at "/static",
# and heatmaps are stored in static/heatmaps, set this prefix:
HEATMAPS_WEB_PREFIX = "/static/heatmaps"


# -------------------------------
# Request model (unified)
# -------------------------------
class InferenceRequest(BaseModel):
    task: Literal["player", "crowd"] = Field(..., description="Which model to run")
    id: str = Field(..., description="Upload ID returned by /upload")

    # Player-tracking knobs (optional; ignored by crowd)
    location: str = Field("unknown", description="Optional context like stadium/venue")
    sampling_fps: Optional[int] = Field(5, ge=1, le=60, description="(player) downsample video to N FPS")
    conf_threshold: Optional[float] = Field(0.5, ge=0, le=1, description="(player) detection confidence threshold")

    # Crowd-monitoring knob
    sample_every_s: Optional[int] = Field(5, ge=1, description="(crowd) sample one frame every N seconds")


# -------------------------------
# Helpers
# -------------------------------
def _resolve_upload_abs_path(rec: Dict[str, Any]) -> Path:
    """
    rec['path'] is a relative path inside backend/ (e.g., 'uploaded_videos/<id>.mp4').
    Resolve to an absolute path on disk.
    """
    backend_dir = Path(__file__).resolve().parents[1]  # backend/
    return (backend_dir / str(rec["path"]).lstrip("/\\")).resolve()


def _webify_rel_path(relpath: str) -> str:
    """
    Turn 'heatmaps\\file.jpg' or 'heatmaps/file.jpg' -> '/static/heatmaps/file.jpg'
    If relpath already contains 'heatmaps', strip up to it; otherwise just join the basename.
    """
    relpath = (relpath or "").replace("\\", "/")
    if "heatmaps/" in relpath:
        rel_tail = relpath.split("heatmaps/", 1)[1]
    else:
        rel_tail = relpath.rsplit("/", 1)[-1] if "/" in relpath else relpath
    return f"{HEATMAPS_WEB_PREFIX}/{rel_tail}" if rel_tail else ""


def _normalize_crowd_payload(svc_json: Dict[str, Any]) -> Dict[str, Any]:
    """
    Map heatmap_path (disk-ish) -> heatmap_url (web), keep other fields as-is.
    Does not mutate the input.
    """
    results_out = []
    for r in svc_json.get("results", []):
        heatmap_path = r.get("heatmap_path") or ""
        results_out.append({
            "frame_index": r.get("frame_index"),
            "timestamp_s": r.get("timestamp_s"),
            "count": r.get("count"),
            "heatmap_url": _webify_rel_path(str(heatmap_path)) if heatmap_path else None,
            "extras": r.get("extras", {}),
        })

    return {
        "model": svc_json.get("model", "crowd_monitor_v0"),
        "video_info": svc_json.get("video_info", {}),
        "results": results_out,
        "summary": svc_json.get("summary", {}),
    }


# -------------------------------
# Unified inference endpoint
# -------------------------------
@router.post("/", summary="Run inference (player or crowd) for a previously uploaded video")
async def run_inference(req: InferenceRequest):
    # 1) Lookup uploaded file metadata
    rec = get_upload(req.id)
    if not rec:
        raise HTTPException(status_code=404, detail="upload id not found")

    # 2) Resolve absolute path on disk
    abs_path = _resolve_upload_abs_path(rec)
    if not abs_path.exists():
        raise HTTPException(status_code=410, detail="file missing on disk")

    # 3) Fan out to the right microservice
    try:
        async with httpx.AsyncClient(timeout=None) as client:
            if req.task == "player":
                if PLAYER_SVC_MODE == "path":
                    payload = {
                        "video_path": str(abs_path),
                        "location": req.location,
                        "sampling_fps": req.sampling_fps or 5,
                        "conf_threshold": req.conf_threshold or 0.5,
                    }
                    resp = await client.post(f"{PLAYER_SVC_URL}/track-players-by-path", json=payload)
                else:  # upload
                    data = {
                        "location": req.location,
                        "sampling_fps": str(req.sampling_fps or 5),
                        "conf_threshold": str(req.conf_threshold or 0.5),
                    }
                    with abs_path.open("rb") as f:
                        files = {"video": (abs_path.name, f, "video/mp4")}
                        resp = await client.post(f"{PLAYER_SVC_URL}/track-players", files=files, data=data)

            else:  # req.task == "crowd"
                if CROWD_SVC_MODE == "path":
                    payload = {
                        "video_path": str(abs_path),
                        "sample_every_s": req.sample_every_s or 5,
                    }
                    resp = await client.post(f"{CROWD_SVC_URL}/crowd-from-video-by-path", json=payload)
                else:  # upload
                    data = {"sample_every_s": str(req.sample_every_s or 5)}
                    with abs_path.open("rb") as f:
                        files = {"video": (abs_path.name, f, "video/mp4")}
                        resp = await client.post(f"{CROWD_SVC_URL}/crowd-from-video", files=files, data=data)

        if resp.status_code != 200:
            raise HTTPException(status_code=502, detail=f"{req.task} service error: {resp.text}")

        svc_json = resp.json()

        # 4) Normalize/return
        normalized = _normalize_crowd_payload(svc_json) if req.task == "crowd" else svc_json

        return {
            "id": rec["id"],
            "task": req.task,
            "input_path": str(abs_path),
            "status": "ok",
            "model": normalized.get("model", "unknown"),
            "data": normalized,  # full model output (tracks / heatmaps / summary)
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
