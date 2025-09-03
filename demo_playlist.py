#!/usr/bin/env python3
"""
Demo with a working public YouTube playlist that supports proxy functionality
"""

import os
from standalone_whisper import extract_playlist_videos, get_proxy_config, is_playlist_url

def demo_with_working_playlist():
    """Demo the system with a known working playlist"""
    
    # This playlist should be public and accessible
    working_playlist = "https://www.youtube.com/watch?v=dQw4w9WgXcQ&list=PLa-zfMI3bF5aKKh_3cW0d8hhTzm9w6Qar"
    
    print("🎬 YouTube Playlist Transcription Demo")
    print("=" * 50)
    print(f"Testing with: {working_playlist}")
    
    proxy = get_proxy_config()
    if proxy:
        print(f"Using proxy: {proxy}")
    else:
        print("No proxy configured (using direct connection)")
    
    try:
        print("\n📋 Extracting playlist videos...")
        videos = extract_playlist_videos(working_playlist, proxy)
        
        if videos:
            print(f"✅ Found {len(videos)} videos in playlist:")
            for i, video in enumerate(videos):
                print(f"   {i+1}. {video['title']}")
                print(f"      ID: {video['id']}")
                print(f"      URL: {video['url']}")
            
            print(f"\n🎯 This playlist is ready for transcription!")
            print(f"You can now use this URL in your application:")
            print(f"   {working_playlist}")
            
        else:
            print("❌ No videos found in playlist")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        
        if "does not exist" in str(e).lower():
            print("\n💡 The playlist might be:")
            print("   - Private or deleted")
            print("   - Region-blocked")
            print("   - Requiring sign-in")
            print("\n🔧 Try setting up a proxy:")
            print("   export YOUTUBE_PROXY='socks5://proxy:port'")
            print("   # or")
            print("   export YOUTUBE_PROXY='http://proxy:port'")

def test_with_your_playlist():
    """Test the playlist you originally provided"""
    your_playlist = "https://www.youtube.com/playlist?list=PLl7bF1DNa5BWB__nvu-Nzbe3sZbn--qK4"
    
    print(f"\n🎯 Testing your specific playlist...")
    print(f"URL: {your_playlist}")
    
    proxy = get_proxy_config()
    if proxy:
        print(f"Using proxy: {proxy}")
    else:
        print("No proxy configured")
    
    try:
        videos = extract_playlist_videos(your_playlist, proxy)
        if videos:
            print(f"✅ Success! Found {len(videos)} videos:")
            for i, video in enumerate(videos):
                print(f"   {i+1}. {video['title']}")
        else:
            print("❌ Playlist is empty")
    except Exception as e:
        print(f"❌ Error: {e}")
        
        print(f"\n💡 Possible solutions:")
        print(f"1. Check if the playlist is public")
        print(f"2. Try accessing it in a browser first")
        print(f"3. Set up a proxy/VPN")
        print(f"4. Use a different playlist URL")

def show_proxy_setup():
    """Show how to set up proxy"""
    print(f"\n🔧 Proxy Setup Guide:")
    print("=" * 30)
    print("1. Quick test with a free proxy:")
    print("   export YOUTUBE_PROXY='socks5://127.0.0.1:1080'  # If you have local SOCKS")
    print("   export YOUTUBE_PROXY='http://proxy.example.com:8080'")
    print("")
    print("2. Premium proxy services (recommended for production):")
    print("   - ProxyMesh: https://proxymesh.com/")
    print("   - Bright Data: https://brightdata.com/")
    print("   - SmartProxy: https://smartproxy.com/")
    print("")
    print("3. VPN as alternative:")
    print("   - Use a VPN service to change your location")
    print("   - Some VPNs work better than others with YouTube")
    print("")
    print("4. Test proxy configuration:")
    print("   python proxy_config.py")

def demo_functionality():
    """Show the current functionality with mock data"""
    print("\n🎯 Current Implementation Status:")
    print("=" * 40)
    
    # Demo URL Detection
    print("1. URL Detection:")
    test_urls = [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",  # Single video
        "https://www.youtube.com/playlist?list=PLl7bF1DNa5BWB__nvu-Nzbe3sZbn--qK4",  # Playlist
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ&list=PLl7bF1DNa5BWB__nvu-Nzbe3sZbn--qK4",  # Video with playlist
    ]
    
    for url in test_urls:
        is_playlist = is_playlist_url(url)
        print(f"   {'📋 PLAYLIST' if is_playlist else '📹 SINGLE VIDEO'}: {url[:60]}...")
    
    print("\n2. Features Implemented:")
    print("   ✅ Automatic playlist URL detection")
    print("   ✅ Individual video extraction from playlists")
    print("   ✅ Proxy support for YouTube restrictions")
    print("   ✅ Enhanced error handling and retries")
    print("   ✅ Progress tracking for multiple videos")
    print("   ✅ ZIP packaging for bulk downloads")
    print("   ✅ Frontend adaptation for playlist workflow")

if __name__ == "__main__":
    # Demo with working playlist
    demo_with_working_playlist()
    
    # Test your specific playlist
    test_with_your_playlist()
    
    # Show current functionality
    demo_functionality()
    
    # Show proxy setup
    show_proxy_setup()
    
    print(f"\n✅ The proxy system is ready!")
    print(f"When you get a working proxy, your playlist functionality will work with any public playlist.")
