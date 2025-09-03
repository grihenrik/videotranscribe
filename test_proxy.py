#!/usr/bin/env python3
"""
Test proxy functionality with YouTube playlists
"""

import os
import requests
from standalone_whisper import extract_playlist_videos, get_proxy_config

def test_direct_access():
    """Test direct access to YouTube"""
    print("🔍 Testing direct YouTube access...")
    try:
        response = requests.get('https://www.youtube.com/', timeout=10)
        if response.status_code == 200:
            print("✅ Direct YouTube access: Working")
            return True
        else:
            print(f"❌ Direct YouTube access: Failed (Status: {response.status_code})")
            return False
    except Exception as e:
        print(f"❌ Direct YouTube access: Failed ({e})")
        return False

def test_with_proxy():
    """Test access through proxy"""
    proxy = get_proxy_config()
    if not proxy:
        print("⚠️ No proxy configured")
        return False
        
    print(f"🔍 Testing proxy access: {proxy}")
    try:
        proxies = {
            'http': proxy,
            'https': proxy
        }
        response = requests.get('https://www.youtube.com/', proxies=proxies, timeout=15)
        if response.status_code == 200:
            print("✅ Proxy YouTube access: Working")
            return True
        else:
            print(f"❌ Proxy YouTube access: Failed (Status: {response.status_code})")
            return False
    except Exception as e:
        print(f"❌ Proxy YouTube access: Failed ({e})")
        return False

def test_playlist_extraction():
    """Test playlist extraction with known working playlists"""
    test_playlists = [
        # TED Talks (usually public and stable)
        "https://www.youtube.com/playlist?list=PL70DEC2B0568B5469",
        # Python tutorials (public)
        "https://www.youtube.com/playlist?list=PLZlA0Gpn_vH_uq6y1_5oF5-6bjz9g8V-t",
        # The one you provided (might be private)
        "https://www.youtube.com/playlist?list=PLl7bF1DNa5BWB__nvu-Nzbe3sZbn--qK4"
    ]
    
    proxy = get_proxy_config()
    print(f"\n🎬 Testing playlist extraction (proxy: {'Yes' if proxy else 'No'})...")
    
    for i, playlist_url in enumerate(test_playlists, 1):
        print(f"\n📋 Test {i}: {playlist_url}")
        try:
            videos = extract_playlist_videos(playlist_url, proxy)
            if videos:
                print(f"✅ Found {len(videos)} videos")
                # Show first few videos
                for j, video in enumerate(videos[:3]):
                    print(f"   {j+1}. {video['title']}")
                if len(videos) > 3:
                    print(f"   ... and {len(videos) - 3} more")
            else:
                print("❌ No videos found (playlist might be private/empty)")
        except Exception as e:
            print(f"❌ Failed: {e}")

def test_specific_playlist():
    """Test the specific playlist you mentioned"""
    playlist_url = "https://www.youtube.com/playlist?list=PLl7bF1DNa5BWB__nvu-Nzbe3sZbn--qK4"
    proxy = get_proxy_config()
    
    print(f"\n🎯 Testing your specific playlist...")
    print(f"   URL: {playlist_url}")
    print(f"   Proxy: {proxy if proxy else 'None'}")
    
    try:
        videos = extract_playlist_videos(playlist_url, proxy)
        if videos:
            print(f"✅ Success! Found {len(videos)} videos:")
            for i, video in enumerate(videos):
                print(f"   {i+1}. {video['title']}")
                print(f"      ID: {video['id']}")
                print(f"      URL: {video['url']}")
        else:
            print("❌ No videos found. This playlist might be:")
            print("   - Private or unlisted")
            print("   - Deleted or unavailable") 
            print("   - Region-blocked")
            print("   - Requiring authentication")
    except Exception as e:
        print(f"❌ Error: {e}")
        if "private" in str(e).lower() or "unavailable" in str(e).lower():
            print("💡 Try setting up a proxy to bypass restrictions")

if __name__ == "__main__":
    print("YouTube Proxy Test Suite")
    print("=" * 50)
    
    # Test 1: Direct access
    direct_works = test_direct_access()
    
    # Test 2: Proxy access (if configured)
    proxy_works = test_with_proxy()
    
    # Test 3: Playlist extraction
    test_playlist_extraction()
    
    # Test 4: Your specific playlist
    test_specific_playlist()
    
    print("\n" + "=" * 50)
    print("📋 Summary:")
    print(f"Direct access: {'✅ Working' if direct_works else '❌ Failed'}")
    print(f"Proxy access: {'✅ Working' if proxy_works else '❌ Failed/Not configured'}")
    
    if not direct_works and not proxy_works:
        print("\n💡 Recommendations:")
        print("1. Try setting up a proxy: export YOUTUBE_PROXY='socks5://proxy:port'")
        print("2. Use a VPN service")
        print("3. Try from a different network/location")
        print("4. Check if YouTube is blocked in your region")
        print("\nFor proxy setup instructions, run: python proxy_config.py")
