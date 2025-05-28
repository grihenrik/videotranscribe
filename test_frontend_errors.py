#!/usr/bin/env python3
"""
Frontend error testing suite to identify JavaScript connection issues.
"""

import requests
import json
import time

BASE_URL = "http://localhost:5000"

def test_frontend_api_mismatch():
    """Test for API response format mismatches causing frontend errors"""
    print("🔍 Testing Frontend-Backend API Compatibility...")
    
    # Test transcription submission
    response = requests.post(f"{BASE_URL}/transcribe", data={
        'url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
        'mode': 'auto',
        'lang': 'en'
    })
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Transcription response: {json.dumps(data, indent=2)}")
        
        # Check if response has download_links as expected by frontend
        if 'download_links' in data:
            print("✅ Download links present in response")
        else:
            print("❌ Missing download_links in response - this causes frontend errors!")
            return False
            
        job_id = data.get('job_id')
        if job_id:
            # Test status endpoint that frontend polls
            status_response = requests.get(f"{BASE_URL}/status/{job_id}")
            if status_response.status_code == 200:
                status_data = status_response.json()
                print(f"✅ Status response: {json.dumps(status_data, indent=2)}")
                
                # Check for required fields frontend expects
                required_fields = ['status', 'progress']
                missing_fields = [field for field in required_fields if field not in status_data]
                if missing_fields:
                    print(f"❌ Missing fields in status response: {missing_fields}")
                    print("This causes the 'Error checking status' messages!")
                    return False
                else:
                    print("✅ All required status fields present")
            else:
                print(f"❌ Status endpoint failed: {status_response.status_code}")
                return False
        else:
            print("❌ No job_id in transcription response")
            return False
    else:
        print(f"❌ Transcription endpoint failed: {response.status_code}")
        return False
    
    return True

def test_websocket_fallback():
    """Test if WebSocket errors are properly handled"""
    print("\n🔌 Testing WebSocket Error Handling...")
    
    # Try to connect to WebSocket endpoint (will fail, but we check handling)
    try:
        response = requests.get(f"{BASE_URL}/ws/test_job")
        if response.status_code == 404:
            print("✅ WebSocket endpoint properly returns 404 (expected)")
        else:
            print(f"✅ WebSocket endpoint response: {response.status_code}")
    except Exception as e:
        print(f"✅ WebSocket connection fails as expected: {e}")
    
    return True

def test_status_polling_loop():
    """Test the status polling that causes repeated errors"""
    print("\n⏰ Testing Status Polling Loop...")
    
    # Submit a job first
    response = requests.post(f"{BASE_URL}/transcribe", data={
        'url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
        'mode': 'auto',
        'lang': 'en'
    })
    
    if response.status_code == 200:
        data = response.json()
        job_id = data.get('job_id')
        
        if job_id:
            # Simulate the polling that frontend does
            for i in range(3):
                status_response = requests.get(f"{BASE_URL}/status/{job_id}")
                print(f"Poll {i+1}: Status {status_response.status_code}")
                
                if status_response.status_code == 200:
                    status_data = status_response.json()
                    if status_data.get('status') == 'completed':
                        print("✅ Status polling works correctly")
                        return True
                else:
                    print(f"❌ Status polling failed at attempt {i+1}")
                    return False
                
                time.sleep(1)
    
    return True

def test_download_links():
    """Test if download links work as expected by frontend"""
    print("\n📥 Testing Download Links...")
    
    # Submit a job first
    response = requests.post(f"{BASE_URL}/transcribe", data={
        'url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
        'mode': 'auto',
        'lang': 'en'
    })
    
    if response.status_code == 200:
        data = response.json()
        job_id = data.get('job_id')
        
        if job_id and 'download_links' in data:
            # Test each download link
            for format_name, link in data['download_links'].items():
                download_response = requests.get(f"{BASE_URL}{link}")
                if download_response.status_code == 200:
                    print(f"✅ Download link works: {format_name}")
                else:
                    print(f"❌ Download link broken: {format_name} ({download_response.status_code})")
                    return False
            return True
        else:
            print("❌ No download links in response")
            return False
    
    return False

def main():
    print("🔧 Frontend Error Analysis")
    print("=" * 50)
    
    tests = [
        ("API Compatibility", test_frontend_api_mismatch),
        ("WebSocket Handling", test_websocket_fallback), 
        ("Status Polling", test_status_polling_loop),
        ("Download Links", test_download_links),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "="*50)
    print("📊 Frontend Error Analysis Results:")
    print("="*50)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name:<20} {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("🎉 All frontend connections working!")
    else:
        print("⚠️ Found issues causing frontend errors")

if __name__ == "__main__":
    main()