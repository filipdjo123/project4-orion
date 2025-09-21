# backend/routes/metrics.py
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import func, select, desc
from storage import _db, Inference
from routes.metrics_store import metrics as mem  # in-memory rolling metrics

router = APIRouter()  # main.py sets prefix="/api/v1/metrics"

@router.get("/", summary="Get Metrics")
async def get_metrics():
    # --- DB side: totals, per-task counts, last inference ---
    with _db() as db:
        total = db.query(func.count(Inference.id)).scalar() or 0

        per_task_rows = db.execute(
            select(Inference.task, func.count(Inference.id)).group_by(Inference.task)
        ).all()
        per_task = {task: count for task, count in per_task_rows}

        last = db.execute(
            select(Inference).order_by(desc(Inference.created_at)).limit(1)
        ).scalar_one_or_none()

    last_payload = None
    if last:
        last_payload = {
            "id": str(last.id),
            "upload_id": str(last.upload_id),
            "task": last.task,
            "status": last.status,
            "payload": last.payload,
            "created_at": last.created_at.isoformat(),
        }

    # --- In-memory rolling stats ---
    rolling = mem.snapshot()  # {'player': {...}, 'crowd': {...}}

    return JSONResponse(content={
        "totals": {"inferences": total},
        "per_task": per_task,                  # {"player": 12, "crowd": 9}
        "last_inference": last_payload,        # dict | null
        "rolling": rolling,                    # calls, avg_latency_ms, last_request, last_output
    })
