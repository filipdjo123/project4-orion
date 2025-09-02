# backend/storage_simple.py
"""
Simplified storage module without database dependencies
Uses in-memory storage for development/testing
"""
from __future__ import annotations
import os, uuid
from datetime import datetime
from typing import Optional, List, Dict, Any

# In-memory storage (replace with database later)
_uploads = {}
_inferences = {}

def init_db():
    """Initialize storage (no-op for in-memory storage)"""
    pass

def _db():
    """Mock database session (no-op)"""
    class MockDB:
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc_val, exc_tb):
            pass
        def add(self, item):
            pass
        def commit(self):
            pass
        def refresh(self, item):
            pass
        def query(self, model):
            return MockQuery(model)
    
    class MockQuery:
        def __init__(self, model):
            self.model = model
        def filter(self, condition):
            return self
        def one(self):
            return None
        def all(self):
            return []
        def order_by(self, field):
            return self
        def limit(self, limit):
            return []
    
    return MockDB()

def save_upload(path: str, media_type: str, size_bytes: int) -> dict:
    """Save upload info to in-memory storage"""
    upload_id = str(uuid.uuid4())
    upload_data = {
        "id": upload_id,
        "path": path,
        "media_type": media_type,
        "size_bytes": size_bytes,
        "created_at": datetime.now().isoformat()
    }
    _uploads[upload_id] = upload_data
    return upload_data

def get_upload(upload_id: str) -> Optional[dict]:
    """Get upload info from in-memory storage"""
    return _uploads.get(upload_id)

def save_inference(upload_id: str, task: str, status: str, payload: Dict[str, Any]) -> dict:
    """Save inference result to in-memory storage"""
    inference_id = str(uuid.uuid4())
    inference_data = {
        "id": inference_id,
        "upload_id": upload_id,
        "task": task,
        "status": status,
        "payload": payload or {},
        "created_at": datetime.now().isoformat()
    }
    _inferences[inference_id] = inference_data
    return inference_data

def list_inferences(limit: int = 50) -> List[dict]:
    """List recent inferences from in-memory storage"""
    all_inferences = list(_inferences.values())
    all_inferences.sort(key=lambda x: x['created_at'], reverse=True)
    return all_inferences[:limit]

def inferences_summary() -> dict:
    """Get summary of inferences from in-memory storage"""
    total = len(_inferences)
    by_task = {}
    by_status = {}
    
    for inference in _inferences.values():
        task = inference['task']
        status = inference['status']
        
        by_task[task] = by_task.get(task, 0) + 1
        by_status[status] = by_status.get(status, 0) + 1
    
    return {
        "total": total,
        "by_task": by_task,
        "by_status": by_status
    }
