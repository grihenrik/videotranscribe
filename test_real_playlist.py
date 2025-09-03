#!/usr/bin/env python3
"""
Test the playlist functionality with a real playlist URL
"""

import requests
import json
import time

def test_playlist_processing():
    """Test playlist processing with the provided URL"""
    
    # Test with a known working public playlist (Python programming tutorials)
    playlist_url = "https://www.youtube.com/playlist?list=PLsyeobzWxl7poL9JTVyndKe62ieoN-MZ3"
    
    # Also test the user's original URL to show the error handling
    user_playlist_url = "https://www.youtube.com/playlist?list=PLl7bF1DNa5BWB__nvu-Nzbe3sZbn--qK4"
    
    print(f"🎬 Testing playlist functionality with:")
    print(f"Working playlist URL: {playlist_url}")
    print(f"User's playlist URL: {user_playlist_url}")
    print("-" * 50)
    
    # Test both URLs
    for test_name, test_url in [("Working Playlist", playlist_url), ("User's Playlist", user_playlist_url)]:
        print(f"\n🧪 Testing {test_name}: {test_url}")
        
        # First, let's test the playlist detection in standalone_whisper
        print("1️⃣ Testing playlist detection...")
        try:
            import sys
            sys.path.append('/Users/henrikgripenberg/Development/yt/videotranscribe')
            from standalone_whisper import is_playlist_url, extract_playlist_videos
            
            is_playlist = is_playlist_url(test_url)
            print(f"✅ Playlist detected: {is_playlist}")
            
            if is_playlist:
                print("\n2️⃣ Extracting playlist videos...")
                videos = extract_playlist_videos(test_url)
                print(f"✅ Found {len(videos)} videos in playlist:")
                for i, video in enumerate(videos[:3], 1):  # Show first 3
                    print(f"   {i}. {video['title']}")
                    print(f"      URL: {video['url']}")
                if len(videos) > 3:
                    print(f"   ... and {len(videos) - 3} more videos")
                    
                # Only test API with working playlist to save time
                if test_name == "Working Playlist":
                    print(f"\n3️⃣ Testing API endpoint with working playlist...")
                    try:
                        # Prepare the request data
                        data = {
                            'url': test_url,
                            'format': 'txt'
                        }
                        
                        print(f"Making POST request to http://127.0.0.1:5000/transcribe")
                        print(f"Data: {data}")
                        
                        # Make the request
                        response = requests.post(
                            'http://127.0.0.1:5000/transcribe',
                            json=data,
                            timeout=30  # Short timeout for testing
                        )
                        
                        print(f"✅ Response status: {response.status_code}")
                        print(f"✅ Response headers: {dict(response.headers)}")
                        
                        if response.status_code == 200:
                            try:
                                result = response.json()
                                print(f"✅ JSON Response: {json.dumps(result, indent=2)}")
                                
                                if result.get('is_playlist'):
                                    print(f"\n🎉 Playlist processing initiated!")
                                    print(f"Job ID: {result.get('job_id')}")
                                    print(f"Total videos: {result.get('total_videos')}")
                                    print(f"Download URL will be: {result.get('download_url')}")
                                else:
                                    print(f"⚠️  Not detected as playlist by API")
                                    
                            except json.JSONDecodeError:
                                print(f"⚠️  Non-JSON response: {response.text[:200]}...")
                        else:
                            print(f"❌ Request failed: {response.text}")
                            
                    except requests.exceptions.RequestException as e:
                        print(f"❌ Request error: {e}")
                    except Exception as e:
                        print(f"❌ Unexpected error: {e}")
                        
        except Exception as e:
            print(f"❌ Error in playlist detection: {e}")
            if "does not exist" in str(e):
                print(f"   → This playlist may be private, deleted, or the URL is incorrect")
            continue

if __name__ == "__main__":
    test_playlist_processing()
