#!/usr/bin/env python3
"""
Test with known working public YouTube playlists
"""

import os
from standalone_whisper import extract_playlist_videos, get_proxy_config

def test_working_playlists():
    """Test with playlists that should definitely work"""
    
    # These are known public playlists that should be accessible
    test_playlists = [
        # Official YouTube channels with public playlists
        ("https://www.youtube.com/watch?v=dQw4w9WgXcQ&list=PLa-zfMI3bF5aKKh_3cW0d8hhTzm9w6Qar", "Rick Roll playlist"),
        ("https://www.youtube.com/playlist?list=PLBCF2DAC6FFB574DE", "Original popular songs"),
        # Let's try a single video with a playlist parameter to see if that works
        ("https://www.youtube.com/watch?v=jNQXAC9IVRw&list=PLrAXtmRdnEQy6nuLMv9-WIexWSmn78H-4", "Single video with playlist"),
    ]
    
    proxy = get_proxy_config()
    print(f"🎬 Testing with known public playlists (proxy: {'Yes' if proxy else 'No'})...")
    
    for playlist_url, description in test_playlists:
        print(f"\n📋 Testing: {description}")
        print(f"   URL: {playlist_url}")
        try:
            videos = extract_playlist_videos(playlist_url, proxy)
            if videos:
                print(f"✅ Success! Found {len(videos)} videos:")
                for i, video in enumerate(videos[:3]):  # Show first 3
                    print(f"   {i+1}. {video['title']}")
                if len(videos) > 3:
                    print(f"   ... and {len(videos) - 3} more")
                return True  # Found a working playlist
            else:
                print("❌ No videos found")
        except Exception as e:
            print(f"❌ Failed: {e}")
    
    return False

def test_single_video():
    """Test with a single video to see if yt-dlp is working at all"""
    print(f"\n🎥 Testing single video extraction...")
    
    # Rick Roll - this should definitely exist and be public
    test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    
    try:
        # Use yt-dlp directly to get video info
        import subprocess
        
        cmd = [
            'yt-dlp',
            '--print', '%(id)s|%(title)s|%(webpage_url)s',
            '--no-playlist',
            test_url
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        if result.stdout.strip():
            parts = result.stdout.strip().split('|', 2)
            if len(parts) >= 3:
                print(f"✅ Single video works!")
                print(f"   ID: {parts[0]}")
                print(f"   Title: {parts[1]}")
                print(f"   URL: {parts[2]}")
                return True
        
    except Exception as e:
        print(f"❌ Single video failed: {e}")
    
    return False

def test_playlist_with_different_format():
    """Try different playlist URL formats"""
    
    # Let's create a simple test playlist URL from YouTube Music or other sources
    test_formats = [
        "https://www.youtube.com/playlist?list=PLFgquLnL59alCl_2TQvOiD5Vgm1hCaGSI",  # Public playlist
        "https://youtube.com/playlist?list=PLFgquLnL59alCl_2TQvOiD5Vgm1hCaGSI",   # Without www
    ]
    
    proxy = get_proxy_config()
    print(f"\n🎵 Testing different playlist formats...")
    
    for playlist_url in test_formats:
        print(f"\n📋 Testing: {playlist_url}")
        try:
            videos = extract_playlist_videos(playlist_url, proxy)
            if videos:
                print(f"✅ Success! Found {len(videos)} videos")
                return True
            else:
                print("❌ No videos found")
        except Exception as e:
            print(f"❌ Failed: {e}")
    
    return False

def diagnose_issue():
    """Try to diagnose what's going wrong"""
    print(f"\n🔧 Diagnostic tests...")
    
    # Test 1: Check yt-dlp version
    try:
        import subprocess
        result = subprocess.run(['yt-dlp', '--version'], capture_output=True, text=True)
        print(f"yt-dlp version: {result.stdout.strip()}")
    except Exception as e:
        print(f"❌ yt-dlp not found or not working: {e}")
        return
    
    # Test 2: Try with verbose output
    print("\n🔍 Trying with verbose output...")
    try:
        cmd = [
            'yt-dlp',
            '--flat-playlist',
            '--print', '%(id)s|%(title)s',
            '-v',  # Verbose
            'https://www.youtube.com/watch?v=dQw4w9WgXcQ'  # Single video, no playlist
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        print(f"Return code: {result.returncode}")
        if result.stdout:
            print(f"Output: {result.stdout[:500]}...")
        if result.stderr:
            print(f"Errors: {result.stderr[:500]}...")
            
    except Exception as e:
        print(f"❌ Verbose test failed: {e}")

if __name__ == "__main__":
    print("YouTube Playlist Diagnosis")
    print("=" * 50)
    
    # Test 1: Try known working playlists
    working = test_working_playlists()
    
    if not working:
        # Test 2: Try single video
        single_works = test_single_video()
        
        if not single_works:
            # Test 3: Diagnose the issue
            diagnose_issue()
        else:
            # Single video works, try different playlist formats
            test_playlist_with_different_format()
    
    print("\n" + "=" * 50)
    if not working:
        print("💡 It seems like there might be:")
        print("1. Network restrictions blocking YouTube")
        print("2. yt-dlp needs updating")
        print("3. YouTube has changed their API")
        print("4. The test playlists are all private/deleted")
        print("\n🔧 Try:")
        print("1. Update yt-dlp: pip install -U yt-dlp")
        print("2. Test with a fresh public playlist")
        print("3. Try with a proxy/VPN")
    else:
        print("✅ Playlist extraction is working!")
