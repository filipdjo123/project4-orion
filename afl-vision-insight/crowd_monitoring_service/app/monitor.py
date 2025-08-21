# crowd_monitoring_service/app/monitor.py
import time, random, os, uuid
import numpy as np
from PIL import Image

class CrowdMonitor:
    def analyze_frame_np(self, frame_bgr: "np.ndarray") -> dict:
        """
        Replace this dummy with your real per-frame inference.
        frame_bgr: np.ndarray (H, W, 3) in BGR (OpenCV default)
        Returns: {"count": int, "heatmap_path": str(optional), ...}
        """
        time.sleep(3)  # ~3s per frame as per your pipeline

        # Fake count
        count = random.randint(50, 500)

        # (Optional) write a heatmap for this frame if you want a file to view
        # Convert to PIL for easy overlay demo
        img = Image.fromarray(frame_bgr[:, :, ::-1])  # BGR->RGB
        overlay = Image.new("RGBA", img.size, (255, 0, 0, 60))
        img = img.convert("RGBA")
        img = Image.alpha_composite(img, overlay).convert("RGB")

        os.makedirs("heatmaps", exist_ok=True)
        fname = f"heatmap_{uuid.uuid4().hex[:8]}.jpg"
        heatmap_path = os.path.join("heatmaps", fname)
        img.save(heatmap_path, quality=85)

        return {"count": count, "heatmap_path": heatmap_path}
