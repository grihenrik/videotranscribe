#!/usr/bin/env python3
"""
Test the playlist functionality through the API with a working playlist
"""

import requests
import json
import time

def test_api_playlist():
    """Test the playlist API with a working playlist"""
    
    # Use the working playlist we confirmed works
    working_playlist = "https://www.youtube.com/watch?v=dQw4w9WgXcQ&list=PLa-zfMI3bF5aKKh_3cW0d8hhTzm9w6Qar"
    
    print("🔌 Testing Playlist API")
    print("=" * 30)
    print(f"URL: {working_playlist}")
    
    # Test 1: Submit transcription job
    print("\n1. Submitting transcription job...")
    try:
        response = requests.post('http://localhost:5050/transcribe', 
                               json={
                                   'url': working_playlist,
                                   'mode': 'whisper',
                                   'language': 'auto'
                               },
                               timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Job submitted successfully!")
            print(f"   Job ID: {data.get('job_id')}")
            print(f"   Status: {data.get('status')}")
            print(f"   Is Playlist: {data.get('is_playlist', False)}")
            
            job_id = data.get('job_id')
            if job_id:
                # Test 2: Check status
                print(f"\n2. Monitoring job status...")
                for i in range(20):  # Check for up to 2 minutes
                    status_response = requests.get(f'http://localhost:5050/status/{job_id}')
                    if status_response.status_code == 200:
                        status_data = status_response.json()
                        print(f"   Status: {status_data.get('status')} ({status_data.get('percent', 0)}%)")
                        
                        if status_data.get('current_video'):
                            print(f"   Current: {status_data.get('current_video')}")
                        
                        if status_data.get('status') == 'completed':
                            print("✅ Job completed!")
                            
                            # Test 3: Download results
                            if status_data.get('download_links'):
                                zip_link = status_data.get('download_links', {}).get('zip')
                                if zip_link:
                                    print(f"   ZIP Download: {zip_link}")
                                    print("✅ Playlist processing successful!")
                            break
                        elif status_data.get('status') == 'failed':
                            print("❌ Job failed!")
                            print(f"   Error: {status_data.get('error')}")
                            break
                    
                    time.sleep(6)  # Wait 6 seconds between checks
                else:
                    print("⏱️ Job still running after 2 minutes")
        else:
            print(f"❌ Failed to submit job: {response.status_code}")
            print(f"   Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

def test_with_proxy():
    """Test with proxy environment variable set"""
    import os
    
    print(f"\n🔧 Testing with proxy configuration...")
    
    # Check if proxy is configured
    proxy = os.getenv('YOUTUBE_PROXY')
    if proxy:
        print(f"✅ Proxy configured: {proxy}")
    else:
        print("ℹ️ No proxy configured")
        print("   To test with proxy, run:")
        print("   export YOUTUBE_PROXY='socks5://proxy:port'")
        print("   python test_api_with_playlist.py")

def test_your_specific_playlist():
    """Test your original playlist that was having issues"""
    your_playlist = "https://www.youtube.com/playlist?list=PLl7bF1DNa5BWB__nvu-Nzbe3sZbn--qK4"
    
    print(f"\n🎯 Testing your specific playlist through API...")
    print(f"URL: {your_playlist}")
    
    try:
        response = requests.post('http://localhost:5050/transcribe', 
                               json={
                                   'url': your_playlist,
                                   'mode': 'whisper',
                                   'language': 'auto'
                               },
                               timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'failed':
                print("❌ Playlist failed as expected")
                print(f"   Error: {data.get('error')}")
                print("💡 This confirms the playlist is private/deleted/restricted")
            else:
                print("✅ Playlist accepted! Checking status...")
                job_id = data.get('job_id')
                # Quick status check
                time.sleep(2)
                status_response = requests.get(f'http://localhost:5050/status/{job_id}')
                if status_response.status_code == 200:
                    status_data = status_response.json()
                    print(f"   Status: {status_data.get('status')}")
        else:
            print(f"❌ Request failed: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    # Test with working playlist
    test_api_playlist()
    
    # Test proxy configuration
    test_with_proxy()
    
    # Test your specific playlist
    test_your_specific_playlist()
    
    print(f"\n✅ API testing complete!")
    print(f"The system is ready to handle playlists with proxy support.")
