from fastapi import APIRouter
from fastapi.responses import JSONResponse
from routes.metrics_store import metrics  # <- use the singleton

router = APIRouter(prefix="/api/v1", tags=["metrics"])  # optional but recommended

@router.get("/metrics") # GET /api/v1/metrics
async def get_metrics():
    snap = metrics.snapshot()  # {"player": {...}, "crowd": {...}}

    out = {
        "player_tracking": {
            "calls":           snap.get("player", {}).get("calls", 0),
            "avg_latency_ms":  snap.get("player", {}).get("avg_latency_ms", 0.0),
            "last_request":    snap.get("player", {}).get("last_request"),
            "last_output":     snap.get("player", {}).get("last_output"),
        },
        "crowd_monitoring": {
            "calls":           snap.get("crowd", {}).get("calls", 0),
            "avg_latency_ms":  snap.get("crowd", {}).get("avg_latency_ms", 0.0),
            "last_request":    snap.get("crowd", {}).get("last_request"),
            "last_output":     snap.get("crowd", {}).get("last_output"),
        },
    }
    return JSONResponse(content=out)