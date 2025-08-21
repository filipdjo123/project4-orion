# player_tracking_service/app/models.py

from pydantic import BaseModel
from typing import List

class BBox(BaseModel):
    x1: int
    y1: int
    x2: int
    y2: int

class Center(BaseModel):
    x: int
    y: int

class PlayerDetection(BaseModel):
    player_id: int
    bbox: BBox
    center: Center
    confidence: float
    width: int
    height: int

class FrameTracking(BaseModel):
    frame_number: int
    timestamp: float
    players: List[PlayerDetection]

class VideoInfo(BaseModel):
    duration: float
    fps: int
    total_frames: int
    resolution: List[int]

class PlayerTrackingResponse(BaseModel):
    video_info: VideoInfo
    tracking_results: List[FrameTracking]