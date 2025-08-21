# app/models.py

from pydantic import BaseModel
from typing import Dict

class CrowdMonitoringResponse(BaseModel):
    message: str
    heatmap_image: str
    crowd_estimates: Dict[str, int]
