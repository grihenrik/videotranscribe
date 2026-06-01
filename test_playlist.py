#!/usr/bin/env python3
"""
Test script for playlist functionality
"""
import requests
import json
import time

# Test playlist URL detection
test_urls = [
    "https://www.youtube.com/watch?v=89LwxWDmoEU&list=PLl7bF1DNa5BWB__nvu-Nzbe3sZbn--qK4",
    "https://www.youtube.com/playlist?list=PLl7bF1DNa5BWB__nvu-Nzbe3sZbn--qK4",
    "https://www.youtube.com/watch?v=dQw4w9WgXcQ"  # Regular video
]

BASE_URL = "http://localhost:5050"

def test_playlist_detection():
    """Test if playlist URLs are detected correctly"""
    from standalone_whisper import is_playlist_url
    
    print("Testing playlist URL detection:")
    for url in test_urls:
        is_playlist = is_playlist_url(url)
        print(f"  {url} -> {'PLAYLIST' if is_playlist else 'SINGLE VIDEO'}")
    print()

def test_playlist_extraction():
    """Test playlist video extraction"""
    from standalone_whisper import extract_playlist_videos
    
    # Use the same playlist from the user's example
    playlist_url = "https://www.youtube.com/watch?v=89LwxWDmoEU&list=PLl7bF1DNa5BWB__nvu-Nzbe3sZbn--qK4"
    
    print(f"Testing playlist extraction for: {playlist_url}")
    try:
        videos = extract_playlist_videos(playlist_url)
        print(f"Found {len(videos)} videos:")
        for i, video in enumerate(videos[:5]):  # Show first 5
            print(f"  {i+1}. {video['title']} ({video['id']})")
        if len(videos) > 5:
            print(f"  ... and {len(videos) - 5} more videos")
    except Exception as e:
        print(f"Error: {e}")
    print()

def test_api_endpoint():
    """Test the API endpoint with a playlist URL"""
    playlist_url = test_urls[0]  # The playlist URL
    
    print(f"Testing API endpoint with playlist URL: {playlist_url}")
    
    data = {
        'url': playlist_url,
        'mode': 'auto',
        'lang': 'en'
    }
    
    try:
        response = requests.post(f"{BASE_URL}/transcribe", json=data)
        print(f"Response status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 200:
            job_data = response.json()
            job_id = job_data.get('job_id')
            
            if job_id:
                print(f"\\nMonitoring job {job_id}...")
                for i in range(10):  # Check status for up to 30 seconds
                    time.sleep(3)
                    status_response = requests.get(f"{BASE_URL}/job-status/{job_id}")
                    if status_response.status_code == 200:
                        status = status_response.json()
                        print(f"  Status: {status.get('status')} ({status.get('percent', 0)}%)")
                        
                        if status.get('status') == 'complete':
                            print("  ✅ Playlist transcription completed!")
                            break
                        elif status.get('status') == 'error':
                            print(f"  ❌ Error: {status.get('error')}")
                            break
                    else:
                        print(f"  ⚠️ Status check failed: {status_response.status_code}")
                        break
    
    except Exception as e:
        print(f"Error testing API: {e}")

if __name__ == "__main__":
    print("🎬 Testing Playlist Functionality\\n")
    
    # Test 1: URL detection
    test_playlist_detection()
    
    # Test 2: Playlist extraction
    test_playlist_extraction()
    
    # Test 3: API endpoint (only if server is running)
    try:
        requests.get(BASE_URL, timeout=2)
        test_api_endpoint()
    except:
        print("⚠️ Server not running, skipping API test")
        print("Start the server with: python simple_server.py")
