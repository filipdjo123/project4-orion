# backend/routes/analytics.py
from __future__ import annotations
from datetime import datetime, timedelta, timezone
from typing import Dict, List
from fastapi import APIRouter, Query
from sqlalchemy import select, desc
from storage import _db, Inference

router = APIRouter() 

def _since(window: str) -> datetime:
    """
    window: "24h", "7d", "90m" etc.
    """
    now = datetime.now(timezone.utc)
    if not window:
        return now - timedelta(hours=24)
    unit = window[-1].lower()
    try:
        val = int(window[:-1])
    except Exception:
        val = 24; unit = "h"
    if unit == "m":
        return now - timedelta(minutes=val)
    if unit == "h":
        return now - timedelta(hours=val)
    if unit == "d":
        return now - timedelta(days=val)
    return now - timedelta(hours=24)

@router.get("/possession", summary="Possession trends (timeseries)")
async def possession_trends(window: str = Query("24h", description="e.g., 24h, 7d"),
                            bucket_minutes: int = Query(5, ge=1, le=120)):
    """
    Naive proxy using count of player detections per time bucket.
    Response: { series: [ { ts: ISO8601, value: int }, ... ] }
    """
    since = _since(window)
    with _db() as db:
        rows = db.execute(
            select(Inference.created_at, Inference.payload)
            .where(Inference.task == "player", Inference.created_at >= since)
            .order_by(Inference.created_at)
        ).all()

    buckets: Dict[str, int] = {}
    for ts, payload in rows:
        dets = (payload or {}).get("detections", [])
        count = len(dets) if isinstance(dets, list) else 0

        minute = ts.replace(second=0, microsecond=0)
        minute = minute - timedelta(minutes=minute.minute % bucket_minutes)
        key = minute.isoformat()
        buckets[key] = buckets.get(key, 0) + count

    series = [{"ts": k, "value": buckets[k]} for k in sorted(buckets.keys())]
    return {"series": series}

@router.get("/team-utilization", summary="Team utilization over time")
async def team_utilization(window: str = "24h"):
    """
    Aggregates per 'team' in detection payloads. If missing, falls back to per task.
    Response: { series: [ { label: str, points: [ {ts, value}, ... ] }, ... ] }
    """
    since = _since(window)
    with _db() as db:
        rows = db.execute(
            select(Inference.created_at, Inference.task, Inference.payload)
            .where(Inference.created_at >= since)
            .order_by(Inference.created_at)
        ).all()

    agg: Dict[str, Dict[str, int]] = {}
    for ts, task, payload in rows:
        p = payload or {}
        dets = p.get("detections", [])
        labels: List[str] = []
        if isinstance(dets, list):
            for d in dets:
                team = d.get("team")
                if team:
                    labels.append(str(team))
        # fallback if no team labels present
        if not labels:
            labels = [task]

        minute = ts.replace(second=0, microsecond=0).isoformat()
        for label in labels:
            agg.setdefault(label, {}).setdefault(minute, 0)
            agg[label][minute] += 1

    series = [
        {"label": label,
         "points": [{"ts": ts, "value": points[ts]} for ts in sorted(points.keys())]
        }
        for label, points in agg.items()
    ]
    return {"series": series}

@router.get("/player-activity", summary="Player activity summary (top N)")
async def player_activity(window: str = "24h", top_n: int = Query(10, ge=1, le=100)):
    """
    Counts occurrences of player ids in detections: payload.detections[].id
    Response: { players: [ { id: str, count: int }, ... ] }
    """
    since = _since(window)
    with _db() as db:
        rows = db.execute(
            select(Inference.payload)
            .where(Inference.task == "player", Inference.created_at >= since)
            .order_by(desc(Inference.created_at))
        ).all()

    counts: Dict[str, int] = {}
    for (payload,) in rows:
        dets = (payload or {}).get("detections", [])
        if isinstance(dets, list):
            for d in dets:
                pid = str(d.get("id", "unknown"))
                counts[pid] = counts.get(pid, 0) + 1

    top = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)[:top_n]
    return {"players": [{"id": pid, "count": c} for pid, c in top]}
