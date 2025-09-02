from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
import csv
import io
import os
import json
from typing import Dict, List
import math
from datetime import datetime
import uuid

router = APIRouter()

# Global storage for generated heatmaps
HEATMAP_DIR = "heatmap_outputs"
os.makedirs(HEATMAP_DIR, exist_ok=True)

class SimplePlayerTrackingData:
    def __init__(self, csv_data: str):
        """Initialize with CSV data string using basic CSV reader"""
        self.data = []
        csv_reader = csv.DictReader(io.StringIO(csv_data))
        for row in csv_reader:
            # Convert all numeric values to proper types
            processed_row = {
                'frame_id': int(row['frame_id']),
                'player_id': int(row['player_id']),
                'timestamp_s': float(row['timestamp_s']),
                'x1': int(row['x1']),
                'y1': int(row['y1']),
                'x2': int(row['x2']),
                'y2': int(row['y2']),
                'cx': int(row['cx']),
                'cy': int(row['cy']),
                'w': int(row['w']),
                'h': int(row['h']),
                'confidence': float(row['confidence'])
            }
            self.data.append(processed_row)
        
        # Sort by frame_id and timestamp
        self.data.sort(key=lambda x: (x['frame_id'], x['timestamp_s'], x['player_id']))
    
    def get_player_stats(self) -> Dict:
        """Calculate basic statistics for each player"""
        stats = {}
        player_ids = set(row['player_id'] for row in self.data)
        
        for player_id in player_ids:
            player_data = [row for row in self.data if row['player_id'] == player_id]
            
            # Basic counts
            frame_count = len(player_data)
            total_time = player_data[-1]['timestamp_s'] - player_data[0]['timestamp_s']
            
            # Distance calculations
            distances = []
            speeds = []
            
            for i in range(1, len(player_data)):
                prev_pos = (player_data[i-1]['cx'], player_data[i-1]['cy'])
                curr_pos = (player_data[i]['cx'], player_data[i]['cy'])
                
                # Calculate distance in pixels
                distance = math.sqrt((curr_pos[0] - prev_pos[0])**2 + (curr_pos[1] - prev_pos[1])**2)
                distances.append(distance)
                
                # Calculate speed (pixels per second)
                time_diff = player_data[i]['timestamp_s'] - player_data[i-1]['timestamp_s']
                if time_diff > 0:
                    speed = distance / time_diff
                    speeds.append(speed)
            
            # Statistics
            total_distance = sum(distances) if distances else 0.0
            avg_speed = sum(speeds) / len(speeds) if speeds else 0.0
            max_speed = max(speeds) if speeds else 0.0
            
            # Heatmap participation (time presence)
            max_frame = max(row['frame_id'] for row in self.data)
            participation_score = frame_count / max_frame if max_frame > 0 else 0.0
            
            # Intensity score (average confidence)
            confidence_values = [row['confidence'] for row in player_data]
            intensity_score = sum(confidence_values) / len(confidence_values)
            
            stats[player_id] = {
                "frame_count": frame_count,
                "total_time": total_time,
                "total_distance_pixels": total_distance,
                "average_speed_pixels_per_sec": avg_speed,
                "max_speed_pixels_per_sec": max_speed,
                "participation_score": participation_score,
                "intensity_score": intensity_score,
                "confidence_avg": intensity_score,
                "confidence_min": min(confidence_values),
                "confidence_max": max(confidence_values)
            }
        
        return stats
    
    def get_player_movement_path(self, player_id: int) -> Dict:
        """Get movement path data for a specific player"""
        player_data = [row for row in self.data if row['player_id'] == player_id]
        
        if len(player_data) == 0:
            raise ValueError(f"No data found for player {player_id}")
        
        # Extract path coordinates
        path_data = []
        for row in player_data:
            path_data.append({
                "frame_id": row['frame_id'],
                "timestamp": row['timestamp_s'],
                "x": row['cx'],
                "y": row['cy'],
                "confidence": row['confidence']
            })
        
        return {
            "player_id": player_id,
            "total_frames": len(path_data),
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
        tracking_data = SimplePlayerTrackingData(content_str)
        
        # Get basic info
        player_ids = set(row['player_id'] for row in tracking_data.data)
        total_players = len(player_ids)
        total_frames = max(row['frame_id'] for row in tracking_data.data)
        
        return {
            "message": "CSV uploaded and processed successfully",
            "filename": file.filename,
            "total_players": total_players,
            "total_frames": total_frames,
            "data_shape": [len(tracking_data.data), 12]
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing CSV: {str(e)}")

@router.post("/player-stats")
async def get_player_statistics(file: UploadFile = File(...)):
    """Get comprehensive statistics for all players"""
    try:
        content = await file.read()
        content_str = content.decode('utf-8')
        
        tracking_data = SimplePlayerTrackingData(content_str)
        stats = tracking_data.get_player_stats()
        
        return {
            "message": "Player statistics generated successfully",
            "total_players": len(stats),
            "statistics": stats
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating statistics: {str(e)}")

@router.post("/player-movement/{player_id}")
async def get_player_movement(player_id: int, file: UploadFile = File(...)):
    """Get movement path data for a specific player"""
    try:
        content = await file.read()
        content_str = content.decode('utf-8')
        
        tracking_data = SimplePlayerTrackingData(content_str)
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
        
        tracking_data = SimplePlayerTrackingData(content_str)
        players = sorted(set(row['player_id'] for row in tracking_data.data))
        
        return {
            "message": "Available players retrieved successfully",
            "total_players": len(players),
            "player_ids": players
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving player list: {str(e)}")

@router.post("/generate-heatmap")
async def generate_player_heatmap(player_id: int, file: UploadFile = File(...),
                                field_length: float = 165, field_width: float = 135,
                                nx: int = 200, ny: int = 150, sigma: float = 2.0):
    """Generate heatmap for a specific player"""
    try:
        content = await file.read()
        content_str = content.decode('utf-8')
        
        tracking_data = SimplePlayerTrackingData(content_str)
        
        # Get player data
        player_data = [row for row in tracking_data.data if row['player_id'] == player_id]
        
        if len(player_data) == 0:
            raise HTTPException(status_code=404, detail=f"No data found for player {player_id}")
        
        # Create a simple text-based heatmap representation
        # This is a basic version without matplotlib - we'll create a data structure
        # that can be used to generate visualizations later
        
        # Get coordinate ranges
        x_coords = [row['cx'] for row in player_data]
        y_coords = [row['cy'] for row in player_data]
        
        x_min, x_max = min(x_coords), max(x_coords)
        y_min, y_max = min(y_coords), max(y_coords)
        
        # Create a simple grid representation
        grid_data = {
            "player_id": player_id,
            "field_dimensions": {
                "length": field_length,
                "width": field_width,
                "grid_size": {"nx": nx, "ny": ny}
            },
            "coordinate_ranges": {
                "x_min": x_min,
                "x_max": x_max,
                "y_min": y_min,
                "y_max": y_max
            },
            "player_positions": [
                {
                    "frame_id": row['frame_id'],
                    "timestamp": row['timestamp_s'],
                    "x": row['cx'],
                    "y": row['cy'],
                    "confidence": row['confidence']
                }
                for row in player_data
            ],
            "total_positions": len(player_data),
            "sigma": sigma
        }
        
        # Save the heatmap data as JSON for later visualization
        filename = f"heatmap_data_{player_id}_{uuid.uuid4().hex[:8]}.json"
        filepath = os.path.join(HEATMAP_DIR, filename)
        
        with open(filepath, 'w') as f:
            json.dump(grid_data, f, indent=2)
        
        return {
            "message": f"Heatmap data generated for player {player_id}",
            "player_id": player_id,
            "heatmap_data_file": filename,
            "total_positions": len(player_data),
            "field_coverage": {
                "x_range": x_max - x_min,
                "y_range": y_max - y_min,
                "area_covered": (x_max - x_min) * (y_max - y_min)
            }
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating heatmap: {str(e)}")

@router.get("/heatmap-data/{filename}")
async def get_heatmap_data(filename: str):
    """Retrieve generated heatmap data"""
    filepath = os.path.join(HEATMAP_DIR, filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Heatmap data not found")
    
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading heatmap data: {str(e)}")

@router.delete("/cleanup-heatmaps")
async def cleanup_heatmaps():
    """Clean up generated heatmap files"""
    try:
        files_removed = 0
        for filename in os.listdir(HEATMAP_DIR):
            if filename.endswith('.png') or filename.endswith('.json'):
                os.remove(os.path.join(HEATMAP_DIR, filename))
                files_removed += 1
        
        return {
            "message": "Heatmap cleanup completed",
            "files_removed": files_removed
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error during cleanup: {str(e)}")
