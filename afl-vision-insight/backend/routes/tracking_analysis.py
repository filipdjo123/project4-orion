from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from scipy.ndimage import gaussian_filter
from PIL import Image
import io
import os
import json
from typing import Dict, List, Optional
import math
from datetime import datetime
import uuid

router = APIRouter()

# Global storage for generated heatmaps
HEATMAP_DIR = "heatmap_outputs"
os.makedirs(HEATMAP_DIR, exist_ok=True)

class PlayerTrackingData:
    def __init__(self, csv_data: str):
        """Initialize with CSV data string"""
        self.df = pd.read_csv(io.StringIO(csv_data))
        self.process_data()
    
    def process_data(self):
        """Process and validate the tracking data"""
        # Ensure required columns exist
        required_columns = ['frame_id', 'player_id', 'timestamp_s', 'x1', 'y1', 'x2', 'y2', 'cx', 'cy', 'w', 'h', 'confidence']
        missing_columns = [col for col in required_columns if col not in self.df.columns]
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")
        
        # Sort by frame_id and timestamp for proper sequence
        self.df = self.df.sort_values(['frame_id', 'timestamp_s', 'player_id'])
        
        # Calculate center coordinates if not present
        if 'cx' not in self.df.columns or 'cy' not in self.df.columns:
            self.df['cx'] = (self.df['x1'] + self.df['x2']) / 2
            self.df['cy'] = (self.df['y1'] + self.df['y2']) / 2
    
    def get_player_stats(self) -> Dict:
        """Calculate comprehensive statistics for each player"""
        stats = {}
        
        for player_id in self.df['player_id'].unique():
            player_id_int = int(player_id)  # Convert numpy.int64 to Python int
            player_data = self.df[self.df['player_id'] == player_id].copy()
            player_data = player_data.sort_values(['frame_id', 'timestamp_s'])
            
            # Basic counts
            frame_count = len(player_data)
            total_time = float(player_data['timestamp_s'].max() - player_data['timestamp_s'].min())
            
            # Distance calculations
            distances = []
            speeds = []
            
            for i in range(1, len(player_data)):
                prev_pos = (player_data.iloc[i-1]['cx'], player_data.iloc[i-1]['cy'])
                curr_pos = (player_data.iloc[i]['cx'], player_data.iloc[i]['cy'])
                
                # Calculate distance in pixels
                distance = float(math.sqrt((curr_pos[0] - prev_pos[0])**2 + (curr_pos[1] - prev_pos[1])**2))
                distances.append(distance)
                
                # Calculate speed (pixels per second)
                time_diff = float(player_data.iloc[i]['timestamp_s'] - player_data.iloc[i-1]['timestamp_s'])
                if time_diff > 0:
                    speed = float(distance / time_diff)
                    speeds.append(speed)
            
            # Statistics
            total_distance = float(sum(distances)) if distances else 0.0
            avg_speed = float(np.mean(speeds)) if speeds else 0.0
            max_speed = float(max(speeds)) if speeds else 0.0
            
            # Heatmap participation (time presence)
            participation_score = float(frame_count / self.df['frame_id'].max()) if self.df['frame_id'].max() > 0 else 0.0
            
            # Intensity score (average confidence)
            intensity_score = float(player_data['confidence'].mean())
            
            stats[player_id_int] = {
                "frame_count": int(frame_count),
                "total_time": float(total_time),
                "total_distance_pixels": float(total_distance),
                "average_speed_pixels_per_sec": float(avg_speed),
                "max_speed_pixels_per_sec": float(max_speed),
                "participation_score": float(participation_score),
                "intensity_score": float(intensity_score),
                "confidence_avg": float(player_data['confidence'].mean()),
                "confidence_min": float(player_data['confidence'].min()),
                "confidence_max": float(player_data['confidence'].max())
            }
        
        return stats
    
    def generate_heatmap(self, player_id: int, field_length: float = 165, field_width: float = 135, 
                         nx: int = 200, ny: int = 150, sigma: float = 2.0) -> str:
        """Generate heatmap for a specific player"""
        player_data = self.df[self.df['player_id'] == player_id].copy()
        
        if len(player_data) == 0:
            raise ValueError(f"No data found for player {player_id}")
        
        # Scale coordinates to field dimensions
        x_min, x_max = float(self.df['cx'].min()), float(self.df['cx'].max())
        y_min, y_max = float(self.df['cy'].min()), float(self.df['cy'].max())
        
        # Create 2D grid
        x_bins = np.linspace(0, field_length, nx).tolist()
        y_bins = np.linspace(0, field_width, ny).tolist()
        
        # Initialize heatmap grid
        heatmap = np.zeros((ny, nx)).tolist()
        
        # Bin the positions
        for _, row in player_data.iterrows():
            # Scale coordinates
            x_scaled = (row['cx'] - x_min) / (x_max - x_min) * field_length
            y_scaled = (row['cy'] - y_min) / (y_max - y_min) * field_width
            
            # Find bin indices
            x_idx = int(np.digitize(x_scaled, x_bins)) - 1
            y_idx = int(np.digitize(y_scaled, y_bins)) - 1
            
            # Ensure indices are within bounds
            if 0 <= x_idx < nx and 0 <= y_idx < ny:
                # Weight by confidence
                heatmap[y_idx][x_idx] += float(row['confidence'])
        
        # Convert back to numpy for Gaussian smoothing
        heatmap = np.array(heatmap)
        
        # Apply Gaussian smoothing
        heatmap = gaussian_filter(heatmap, sigma=sigma)
        
        # Normalize
        max_val = float(heatmap.max())
        if max_val > 0:
            heatmap = (heatmap / max_val).tolist()
        
        # Create visualization
        fig, ax = plt.subplots(figsize=(10, 8))
        
        # Create field outline
        field_rect = patches.Rectangle((0, 0), field_length, field_width, 
                                     linewidth=2, edgecolor='white', facecolor='none')
        ax.add_patch(field_rect)
        
        # Convert back to numpy for matplotlib
        heatmap_array = np.array(heatmap)
        
        # Plot heatmap
        im = ax.imshow(heatmap_array, extent=[0, field_length, 0, field_width], 
                       origin='lower', cmap='hot', alpha=0.8)
        
        # Add colorbar
        plt.colorbar(im, ax=ax, label='Intensity')
        
        # Labels and title
        ax.set_xlabel('Field Length (m)')
        ax.set_ylabel('Field Width (m)')
        ax.set_title(f'Player {player_id} Movement Heatmap')
        ax.grid(True, alpha=0.3)
        
        # Save heatmap
        filename = f"heatmap_{player_id}_{uuid.uuid4().hex[:8]}.png"
        filepath = os.path.join(HEATMAP_DIR, filename)
        plt.savefig(filepath, dpi=150, bbox_inches='tight', facecolor='black')
        plt.close()
        
        return filepath
    
    def get_player_movement_path(self, player_id: int) -> Dict:
        """Get movement path data for a specific player"""
        player_data = self.df[self.df['player_id'] == player_id].copy()
        player_data = player_data.sort_values(['frame_id', 'timestamp_s'])
        
        if len(player_data) == 0:
            raise ValueError(f"No data found for player {player_id}")
        
        # Extract path coordinates
        path_data = []
        for _, row in player_data.iterrows():
            path_data.append({
                "frame_id": int(row['frame_id']),
                "timestamp": float(row['timestamp_s']),
                "x": int(row['cx']),
                "y": int(row['cy']),
                "confidence": float(row['confidence'])
            })
        
        return {
            "player_id": int(player_id),
            "total_frames": int(len(path_data)),
            "path_data": path_data
        }

@router.post("/upload-csv")
async def upload_tracking_csv(file: UploadFile = File(...)):
    """Upload and process tracking CSV file"""
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV")
    
    try:
        content = await file.read()
        content_str = content.decode('utf-8')
        
        # Process the data
        tracking_data = PlayerTrackingData(content_str)
        
        # Get basic info
        total_players = tracking_data.df['player_id'].nunique()
        total_frames = tracking_data.df['frame_id'].max()
        
        return {
            "message": "CSV uploaded and processed successfully",
            "filename": file.filename,
            "total_players": int(total_players),
            "total_frames": int(total_frames),
            "data_shape": list(tracking_data.df.shape)
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing CSV: {str(e)}")

@router.post("/player-stats")
async def get_player_statistics(file: UploadFile = File(...)):
    """Get comprehensive statistics for all players"""
    try:
        content = await file.read()
        content_str = content.decode('utf-8')
        
        tracking_data = PlayerTrackingData(content_str)
        stats = tracking_data.get_player_stats()
        
        return {
            "message": "Player statistics generated successfully",
            "total_players": int(len(stats)),
            "statistics": stats
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating statistics: {str(e)}")

@router.post("/generate-heatmap")
async def generate_player_heatmap(player_id: int, file: UploadFile = File(...),
                                field_length: float = 165, field_width: float = 135,
                                nx: int = 200, ny: int = 150, sigma: float = 2.0):
    """Generate heatmap for a specific player"""
    try:
        content = await file.read()
        content_str = content.decode('utf-8')
        
        tracking_data = PlayerTrackingData(content_str)
        heatmap_path = tracking_data.generate_heatmap(
            player_id, field_length, field_width, nx, ny, sigma
        )
        
        return {
            "message": f"Heatmap generated for player {player_id}",
            "player_id": int(player_id),
            "heatmap_path": heatmap_path,
            "filename": os.path.basename(heatmap_path)
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating heatmap: {str(e)}")

@router.get("/heatmap/{filename}")
async def get_heatmap(filename: str):
    """Retrieve a generated heatmap image"""
    filepath = os.path.join(HEATMAP_DIR, filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Heatmap not found")
    
    return FileResponse(filepath, media_type="image/png")

@router.post("/player-movement/{player_id}")
async def get_player_movement(player_id: int, file: UploadFile = File(...)):
    """Get movement path data for a specific player"""
    try:
        content = await file.read()
        content_str = content.decode('utf-8')
        
        tracking_data = PlayerTrackingData(content_str)
        movement_data = tracking_data.get_player_movement_path(player_id)
        
        return {
            "message": f"Movement data retrieved for player {player_id}",
            "data": movement_data
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving movement data: {str(e)}")

@router.post("/available-players")
async def get_available_players(file: UploadFile = File(...)):
    """Get list of available player IDs"""
    try:
        content = await file.read()
        content_str = content.decode('utf-8')
        
        tracking_data = PlayerTrackingData(content_str)
        players = sorted([int(pid) for pid in tracking_data.df['player_id'].unique()])
        
        return {
            "message": "Available players retrieved successfully",
            "total_players": int(len(players)),
            "player_ids": [int(pid) for pid in players]
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving player list: {str(e)}")

@router.delete("/cleanup-heatmaps")
async def cleanup_heatmaps():
    """Clean up generated heatmap files"""
    try:
        files_removed = 0
        for filename in os.listdir(HEATMAP_DIR):
            if filename.endswith('.png'):
                os.remove(os.path.join(HEATMAP_DIR, filename))
                files_removed += 1
        
        return {
            "message": "Heatmap cleanup completed",
            "files_removed": files_removed
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error during cleanup: {str(e)}")
