# Player Tracking Analysis System

This system implements the player tracking logic from the Week 5-6 notebook, providing a comprehensive backend API for analyzing player movement data, generating heatmaps, and computing player statistics.

## Features

### 🎯 **Core Functionality**
- **CSV Upload & Processing**: Handle tracking data in the same format as the notebook
- **Player Statistics**: Calculate distance, speed, participation, and intensity metrics
- **Heatmap Generation**: Create movement heatmaps for individual players
- **Movement Path Analysis**: Extract detailed movement trajectories
- **Real-time Processing**: Fast analysis with configurable parameters

### 📊 **Player Metrics Computed**
- **Frame Count**: Total frames each player appears in
- **Total Distance**: Cumulative movement in pixels
- **Average Speed**: Mean movement speed (pixels/second)
- **Max Speed**: Peak movement speed
- **Participation Score**: Time presence ratio
- **Intensity Score**: Average confidence level
- **Confidence Statistics**: Min, max, and average confidence

### 🗺️ **Heatmap Generation**
- **Field Scaling**: Automatically scales to AFL oval dimensions (165m x 135m)
- **Configurable Grid**: Adjustable resolution (default: 200x150 cells)
- **Gaussian Smoothing**: Configurable sigma for visual appeal
- **Confidence Weighting**: Heatmap intensity based on detection confidence

## API Endpoints

### 📤 **Upload & Processing**
```
POST /api/v1/tracking/upload-csv
```
Upload a tracking CSV file and get basic dataset information.

### 📈 **Player Statistics**
```
POST /api/v1/tracking/player-stats
```
Upload CSV file to get comprehensive statistics for all players in the dataset.

### 🗺️ **Heatmap Generation**
```
POST /api/v1/tracking/generate-heatmap
```
Generate a heatmap for a specific player with configurable parameters.

### 🖼️ **Heatmap Retrieval**
```
GET /api/v1/tracking/heatmap/{filename}
```
Retrieve a generated heatmap image.

### 🏃 **Movement Analysis**
```
POST /api/v1/tracking/player-movement/{player_id}
```
Upload CSV file to get detailed movement path data for a specific player.

### 📋 **Player Information**
```
POST /api/v1/tracking/available-players
```
Upload CSV file to get list of all available player IDs in the dataset.

### 🧹 **Cleanup**
```
DELETE /api/v1/tracking/cleanup-heatmaps
```
Remove all generated heatmap files.

## CSV Format Requirements

The system expects CSV files with the following columns:

| Column | Type | Description |
|--------|------|-------------|
| `frame_id` | int | Frame number from video |
| `player_id` | int | Unique player identifier |
| `timestamp_s` | float | Timestamp in seconds |
| `x1, y1` | int | Top-left bounding box coordinates |
| `x2, y2` | int | Bottom-right bounding box coordinates |
| `cx, cy` | int | Center coordinates (auto-calculated if missing) |
| `w, h` | int | Bounding box width and height |
| `confidence` | float | Detection confidence (0.0-1.0) |

## Usage Examples

### 1. **Upload and Process CSV**
```bash
curl -X POST "http://localhost:8000/api/v1/tracking/upload-csv" \
     -H "Content-Type: multipart/form-data" \
     -F "file=@tracking.csv"
```

### 2. **Get Player Statistics**
```bash
curl -X POST "http://localhost:8000/api/v1/tracking/player-stats" \
     -H "Content-Type: multipart/form-data" \
     -F "file=@tracking.csv"
```

### 3. **Generate Player Heatmap**
```bash
curl -X POST "http://localhost:8000/api/v1/tracking/generate-heatmap" \
     -H "Content-Type: multipart/form-data" \
     -F "player_id=1" \
     -F "file=@tracking.csv" \
     -F "field_length=165" \
     -F "field_width=135" \
     -F "nx=200" \
     -F "ny=150" \
     -F "sigma=2.0"
```

### 4. **Get Movement Path**
```bash
curl -X POST "http://localhost:8000/api/v1/tracking/player-movement/1" \
     -H "Content-Type: multipart/form-data" \
     -F "file=@tracking.csv"
```

## Configuration Options

### **Heatmap Parameters**
- `field_length`: Field length in meters (default: 165)
- `field_width`: Field width in meters (default: 135)
- `nx`: Grid resolution in X direction (default: 200)
- `ny`: Grid resolution in Y direction (default: 150)
- `sigma`: Gaussian smoothing parameter (default: 2.0)

### **Performance Tuning**
- **Grid Resolution**: Higher values (400x300) for detailed analysis, lower (100x75) for faster processing
- **Smoothing**: Higher sigma (3.0-5.0) for smoother visuals, lower (1.0-2.0) for sharper details

## Integration with Frontend

The system is designed to work seamlessly with React frontends:

1. **Upload Interface**: Drag & drop CSV files
2. **Player Selection**: Dropdown with available player IDs
3. **Real-time Analysis**: Instant statistics and heatmap generation
4. **Visual Dashboard**: Display heatmaps, movement paths, and metrics

## Error Handling

The system includes comprehensive error handling for:
- **Invalid CSV Format**: Missing columns or wrong data types
- **File Processing Errors**: Corrupted or unreadable files
- **Player Not Found**: Invalid player ID requests
- **Memory Issues**: Large dataset handling

## Performance Considerations

- **Large Datasets**: Optimized for datasets with 1000+ frames
- **Memory Usage**: Efficient pandas operations with minimal memory overhead
- **Heatmap Generation**: Fast processing with matplotlib optimization
- **File Storage**: Automatic cleanup of generated heatmaps

## Dependencies

- **pandas**: Data processing and analysis
- **numpy**: Numerical computations
- **matplotlib**: Heatmap visualization
- **scipy**: Gaussian filtering
- **PIL**: Image processing
- **fastapi**: Web framework

## Testing

Use the included `sample_tracking.csv` file to test the system:

```bash
# Test with sample data
curl -X POST "http://localhost:8000/api/v1/tracking/upload-csv" \
     -H "Content-Type: multipart/form-data" \
     -F "file=@sample_tracking.csv"
```

## Future Enhancements

- **Batch Processing**: Handle multiple CSV files simultaneously
- **Advanced Analytics**: Acceleration, direction changes, player interactions
- **Real-time Streaming**: Process live video feeds
- **Machine Learning**: Predictive movement patterns
- **Export Formats**: JSON, CSV, and image exports
