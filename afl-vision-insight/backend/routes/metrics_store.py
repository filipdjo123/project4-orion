# backend/routes/metrics_store.py
import time
from threading import RLock

class MetricsStore:
    def __init__(self):
        self._lock = RLock()
        self._data = {
            "player": {"calls": 0, "total_ms": 0.0, "last_output": None},
            "crowd":  {"calls": 0, "total_ms": 0.0, "last_output": None},
        }

    def record(self, model: str, ms: float, last_output):
        with self._lock:
            m = self._data[model]
            m["calls"] += 1
            m["total_ms"] += ms
            m["last_output"] = last_output

    def snapshot(self):
        with self._lock:
            out = {}
            for k, v in self._data.items():
                avg = (v["total_ms"] / v["calls"]) if v["calls"] else 0.0
                out[k] = {
                    "calls": v["calls"],
                    "avg_latency_ms": round(avg, 2),
                    "last_output": v["last_output"]
                }
            return out

metrics = MetricsStore()
