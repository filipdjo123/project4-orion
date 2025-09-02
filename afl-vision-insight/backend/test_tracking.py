#!/usr/bin/env python3
"""
Test script for the Player Tracking Analysis System
Run this to verify all endpoints are working correctly
"""

import requests
import json
import os

# Configuration
BASE_URL = "http://localhost:8000"
SAMPLE_CSV = "sample_tracking.csv"

def test_upload_csv():
    """Test CSV upload endpoint"""
    print("🧪 Testing CSV Upload...")
    
    if not os.path.exists(SAMPLE_CSV):
        print(f"❌ Sample CSV file not found: {SAMPLE_CSV}")
        return False
    
    try:
        with open(SAMPLE_CSV, 'rb') as f:
            files = {'file': (SAMPLE_CSV, f, 'text/csv')}
            response = requests.post(f"{BASE_URL}/api/v1/tracking/upload-csv", files=files)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Upload successful: {data['message']}")
            print(f"   Players: {data['total_players']}, Frames: {data['total_frames']}")
            return True
        else:
            print(f"❌ Upload failed: {response.status_code} - {response.text}")
            return False
    
    except Exception as e:
        print(f"❌ Upload error: {str(e)}")
        return False

def test_player_stats():
    """Test player statistics endpoint"""
    print("\n🧪 Testing Player Statistics...")
    
    try:
        with open(SAMPLE_CSV, 'rb') as f:
            files = {'file': (SAMPLE_CSV, f, 'text/csv')}
            response = requests.post(f"{BASE_URL}/api/v1/tracking/player-stats", files=files)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Stats generated: {data['message']}")
            print(f"   Total players: {data['total_players']}")
            
            # Show first player stats
            if data['statistics']:
                first_player = list(data['statistics'].keys())[0]
                stats = data['statistics'][first_player]
                print(f"   Player {first_player} sample stats:")
                print(f"     Frames: {stats['frame_count']}")
                print(f"     Distance: {stats['total_distance_pixels']:.2f} pixels")
                print(f"     Avg Speed: {stats['average_speed_pixels_per_sec']:.2f} px/s")
            return True
        else:
            print(f"❌ Stats failed: {response.status_code} - {response.text}")
            return False
    
    except Exception as e:
        print(f"❌ Stats error: {str(e)}")
        return False

def test_available_players():
    """Test available players endpoint"""
    print("\n🧪 Testing Available Players...")
    
    try:
        with open(SAMPLE_CSV, 'rb') as f:
            files = {'file': (SAMPLE_CSV, f, 'text/csv')}
            response = requests.post(f"{BASE_URL}/api/v1/tracking/available-players", files=files)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Players retrieved: {data['message']}")
            print(f"   Available player IDs: {data['player_ids']}")
            return data['player_ids']
        else:
            print(f"❌ Players failed: {response.status_code} - {response.text}")
            return []
    
    except Exception as e:
        print(f"❌ Players error: {str(e)}")
        return []

def test_heatmap_generation(player_ids):
    """Test heatmap generation endpoint"""
    if not player_ids:
        print("\n❌ Skipping heatmap test - no player IDs available")
        return False
    
    print(f"\n🧪 Testing Heatmap Generation for Player {player_ids[0]}...")
    
    try:
        with open(SAMPLE_CSV, 'rb') as f:
            files = {
                'file': (SAMPLE_CSV, f, 'text/csv'),
                'player_id': (None, str(player_ids[0])),
                'field_length': (None, '165'),
                'field_width': (None, '135'),
                'nx': (None, '200'),
                'ny': (None, '150'),
                'sigma': (None, '2.0')
            }
            response = requests.post(f"{BASE_URL}/api/v1/tracking/generate-heatmap", files=files)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Heatmap generated: {data['message']}")
            print(f"   Filename: {data['filename']}")
            
            # Test retrieving the heatmap
            heatmap_response = requests.get(f"{BASE_URL}/api/v1/tracking/heatmap/{data['filename']}")
            if heatmap_response.status_code == 200:
                print(f"✅ Heatmap retrieved successfully")
                return True
            else:
                print(f"❌ Heatmap retrieval failed: {heatmap_response.status_code}")
                return False
        else:
            print(f"❌ Heatmap generation failed: {response.status_code} - {response.text}")
            return False
    
    except Exception as e:
        print(f"❌ Heatmap error: {str(e)}")
        return False

def test_movement_path(player_ids):
    """Test movement path endpoint"""
    if not player_ids:
        print("\n❌ Skipping movement test - no player IDs available")
        return False
    
    print(f"\n🧪 Testing Movement Path for Player {player_ids[0]}...")
    
    try:
        with open(SAMPLE_CSV, 'rb') as f:
            files = {'file': (SAMPLE_CSV, f, 'text/csv')}
            response = requests.post(f"{BASE_URL}/api/v1/tracking/player-movement/{player_ids[0]}", files=files)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Movement data retrieved: {data['message']}")
            print(f"   Total frames: {data['data']['total_frames']}")
            print(f"   Path data points: {len(data['data']['path_data'])}")
            return True
        else:
            print(f"❌ Movement failed: {response.status_code} - {response.text}")
            return False
    
    except Exception as e:
        print(f"❌ Movement error: {str(e)}")
        return False

def test_cleanup():
    """Test cleanup endpoint"""
    print("\n🧪 Testing Cleanup...")
    
    try:
        response = requests.delete(f"{BASE_URL}/api/v1/tracking/cleanup-heatmaps")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Cleanup completed: {data['message']}")
            print(f"   Files removed: {data['files_removed']}")
            return True
        else:
            print(f"❌ Cleanup failed: {response.status_code} - {response.text}")
            return False
    
    except Exception as e:
        print(f"❌ Cleanup error: {str(e)}")
        return False

def main():
    """Run all tests"""
    print("🚀 Starting Player Tracking Analysis System Tests")
    print("=" * 60)
    
    # Check if server is running
    try:
        response = requests.get(f"{BASE_URL}/")
        if response.status_code != 200:
            print(f"❌ Server not responding: {response.status_code}")
            print("   Make sure to start the backend server first:")
            print("   cd afl-vision-insight/backend")
            print("   uvicorn main:app --reload")
            return
        print("✅ Server is running")
    except Exception as e:
        print(f"❌ Cannot connect to server: {str(e)}")
        print("   Make sure to start the backend server first:")
        print("   cd afl-vision-insight/backend")
        print("   uvicorn main:app --reload")
        return
    
    # Run tests
    tests = [
        ("CSV Upload", test_upload_csv),
        ("Player Statistics", test_player_stats),
        ("Available Players", lambda: test_available_players()),
        ("Heatmap Generation", lambda: test_heatmap_generation(test_available_players())),
        ("Movement Path", lambda: test_movement_path(test_available_players())),
        ("Cleanup", test_cleanup)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} test crashed: {str(e)}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Test Results Summary")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The tracking system is working correctly.")
    else:
        print("⚠️  Some tests failed. Check the output above for details.")

if __name__ == "__main__":
    main()
