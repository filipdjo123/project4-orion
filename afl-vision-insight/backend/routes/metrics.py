from fastapi import APIRouter
from fastapi.responses import JSONResponse
from routes import metrics_store
 
router = APIRouter()
 
@router.get("/")
async def get_metrics():
    metrics_data = {
        "player_tracking": {
            "calls": metrics_store.player_tracking_calls,
            "last_output": metrics_store.last_player_tracking_output
        },
        "crowd_monitoring": {
            "calls": metrics_store.crowd_monitoring_calls,
            "last_output": metrics_store.last_crowd_monitoring_output
        }
    }
    return JSONResponse(content=metrics_data)