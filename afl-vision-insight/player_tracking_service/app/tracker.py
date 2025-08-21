# app/tracker.py

import random
import time
from typing import Optional, Any, Dict

class PlayerTracker:
    def __init__(self):
        pass

    def process_video(
        self,
        video_path: str,
        sampling_fps: int = 5,
        conf_threshold: float = 0.5,
        location: Optional[str] = None,
        **kwargs: Any,  # future-proof
    ) -> Dict[str, Any]:
        """
        Dummy tracker that simulates detections.
        Accepts runtime params to match the gateway/service contract.
        """

        # Simulate processing delay
        time.sleep(1)

        # Simulated video metadata (you can replace with real probe later)
        video_info = {
            "path": video_path,
            "duration": 10.5,
            "fps": 30,
            "total_frames": 315,
            "resolution": [1920, 1080],
        }

        # Simulated tracking per frame
        tracking_results = []
        unique_player_ids = set()

        for frame_number in range(1, 6):  # Simulate 5 frames
            players = []
            # Simulate 1–3 players
            for pid in range(1, random.randint(2, 4)):
                x1 = random.randint(100, 500)
                y1 = random.randint(100, 500)
                width = 100
                height = 333
                x2 = x1 + width
                y2 = y1 + height
                center_x = (x1 + x2) // 2
                center_y = (y1 + y2) // 2

                unique_player_ids.add(pid)

                players.append({
                    "player_id": pid,
                    "bbox": {"x1": x1, "y1": y1, "x2": x2, "y2": y2},
                    "center": {"x": center_x, "y": center_y},
                    "confidence": round(random.uniform(0.85, 0.95), 2),
                    "width": width,
                    "height": height
                })

            tracking_results.append({
                "frame_number": frame_number,
                "timestamp": round(frame_number * (1 / video_info["fps"]), 3),
                "players": players
            })

        # Optional high-level summary (handy for dashboards/metrics)
        summary = {
            "players_detected": len(unique_player_ids),
            "duration_s": video_info["duration"],
            "location": location or "unknown",
            "sampling_fps": sampling_fps,
            "conf_threshold": conf_threshold,
        }

        return {
            "model": "player_tracking_v0",
            "video_info": video_info,
            "tracking_results": tracking_results,
            "summary": summary,
        }
