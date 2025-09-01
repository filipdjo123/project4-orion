# backend/routes/metrics_store.py
import time
from threading import RLock
from collections import deque
from datetime import datetime, timezone

ROLLING_WINDOW = 100  # how many recent calls to average over

class MetricsStore:
    def __init__(self):
        self._lock = RLock()
        self._data = {
            "player": {"calls": 0, "total_ms": 0.0, "latencies": deque(maxlen=ROLLING_WINDOW),
                       "last_output": None, "last_request": None},
            "crowd":  {"calls": 0, "total_ms": 0.0, "latencies": deque(maxlen=ROLLING_WINDOW),
                       "last_output": None, "last_request": None},
        }

    def record(self, model: str, ms: float, last_output):
        with self._lock:
            m = self._data[model]
            m["calls"] += 1
            m["total_ms"] += ms
            m["last_output"] = last_output
            m["latencies"].append(ms)
            m["last_request"] = datetime.now(timezone.utc)

    def snapshot(self):
        with self._lock:
            out = {}
            for k, v in self._data.items():
                # rolling average over recent N; fallback to overall avg
                if v["latencies"]:
                    avg = sum(v["latencies"]) / len(v["latencies"])
                else:
                    avg = (v["total_ms"] / v["calls"]) if v["calls"] else 0.0
                out[k] = {
                    "calls": v["calls"],
                    "avg_latency_ms": round(avg, 2),
                    "last_output": v["last_output"],
                    # NEW
                    "last_request": v["last_request"].isoformat() if v["last_request"] else None,
                }
            return out

metrics = MetricsStore()