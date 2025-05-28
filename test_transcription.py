#!/usr/bin/env python3
"""
Test suite for YouTube transcription functionality.
Tests single video, batch processing, and playlist processing.
"""

import requests
import json
import time
import sys
from urllib.parse import urlparse

# Configuration
BASE_URL = "http://localhost:5000"
TEST_TIMEOUT = 300  # 5 minutes timeout for each test

# Test YouTube URLs - using real, publicly available content
TEST_URLS = {
    'single_video': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',  # Rick Astley - Never Gonna Give You Up
    'batch_videos': [
        'https://www.youtube.com/watch?v=dQw4w9WgXcQ',  # Rick Astley
        'https://www.youtube.com/watch?v=9bZkp7q19f0',  # PSY - Gangnam Style
    ],
    'playlist': 'https://www.youtube.com/playlist?list=PLQVvvaa0QuDfKTOs3Keq_kaG2P55YRn5v'  # Public Python tutorial playlist
}

class TranscriptionTester:
    def __init__(self, base_url=BASE_URL):
        self.base_url = base_url
        self.session = requests.Session()
        
    def test_single_video(self):
        """Test single video transcription"""
        print("🎵 Testing Single Video Transcription...")
        
        data = {
            'url': TEST_URLS['single_video'],
            'mode': 'auto',
            'lang': 'en'
        }
        
        try:
            # Submit transcription job
            response = self.session.post(f"{self.base_url}/transcribe", data=data)
            
            if response.status_code != 200:
                print(f"❌ Failed to submit job: HTTP {response.status_code}")
                print(f"Response: {response.text}")
                return False
                
            result = response.json()
            
            if 'job_id' not in result:
                print(f"❌ No job_id in response: {result}")
                return False
                
            job_id = result['job_id']
            print(f"✅ Job submitted successfully: {job_id}")
            
            # Poll for completion
            if self._wait_for_completion(job_id):
                print("✅ Single video transcription completed successfully!")
                return True
            else:
                print("❌ Single video transcription failed or timed out")
                return False
                
        except Exception as e:
            print(f"❌ Error in single video test: {e}")
            return False
    
    def test_batch_processing(self):
        """Test batch processing of multiple videos"""
        print("\n📦 Testing Batch Processing...")
        
        batch_urls = '\n'.join(TEST_URLS['batch_videos'])
        data = {
            'video_urls': batch_urls,
            'mode': 'captions',  # Use captions for faster testing
            'lang': 'en'
        }
        
        try:
            # Submit batch job
            response = self.session.post(f"{self.base_url}/transcribe", data=data)
            
            if response.status_code != 200:
                print(f"❌ Failed to submit batch job: HTTP {response.status_code}")
                print(f"Response: {response.text}")
                return False
                
            result = response.json()
            
            if 'job_id' not in result:
                print(f"❌ No job_id in batch response: {result}")
                return False
                
            job_id = result['job_id']
            print(f"✅ Batch job submitted successfully: {job_id}")
            
            # Poll for completion
            if self._wait_for_completion(job_id):
                print("✅ Batch processing completed successfully!")
                return True
            else:
                print("❌ Batch processing failed or timed out")
                return False
                
        except Exception as e:
            print(f"❌ Error in batch processing test: {e}")
            return False
    
    def test_playlist_processing(self):
        """Test playlist processing"""
        print("\n📋 Testing Playlist Processing...")
        
        data = {
            'playlist_url': TEST_URLS['playlist'],
            'mode': 'captions',  # Use captions for faster testing
            'lang': 'en'
        }
        
        try:
            # Submit playlist job
            response = self.session.post(f"{self.base_url}/transcribe", data=data)
            
            if response.status_code != 200:
                print(f"❌ Failed to submit playlist job: HTTP {response.status_code}")
                print(f"Response: {response.text}")
                return False
                
            result = response.json()
            
            if 'job_id' not in result:
                print(f"❌ No job_id in playlist response: {result}")
                return False
                
            job_id = result['job_id']
            print(f"✅ Playlist job submitted successfully: {job_id}")
            
            # Poll for completion (playlist might take longer)
            if self._wait_for_completion(job_id, timeout=600):  # 10 minutes for playlist
                print("✅ Playlist processing completed successfully!")
                return True
            else:
                print("❌ Playlist processing failed or timed out")
                return False
                
        except Exception as e:
            print(f"❌ Error in playlist processing test: {e}")
            return False
    
    def _wait_for_completion(self, job_id, timeout=TEST_TIMEOUT):
        """Wait for job completion and check status"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                # Check job status
                status_response = self.session.get(f"{self.base_url}/status/{job_id}")
                
                if status_response.status_code == 200:
                    status_data = status_response.json()
                    status = status_data.get('status', 'unknown')
                    
                    print(f"⏳ Status: {status}", end='')
                    
                    if 'progress' in status_data:
                        print(f" ({status_data['progress']:.1f}%)")
                    else:
                        print()
                    
                    if status == 'completed':
                        # Test download functionality
                        return self._test_download(job_id)
                    elif status == 'failed':
                        error_msg = status_data.get('error', 'Unknown error')
                        print(f"❌ Job failed: {error_msg}")
                        return False
                    
                time.sleep(5)  # Wait 5 seconds before next check
                
            except Exception as e:
                print(f"❌ Error checking status: {e}")
                time.sleep(5)
        
        print(f"❌ Timeout after {timeout} seconds")
        return False
    
    def _test_download(self, job_id):
        """Test download functionality for completed job"""
        print("📥 Testing download functionality...")
        
        # Test different formats
        formats = ['txt', 'srt', 'vtt']
        
        for fmt in formats:
            try:
                download_response = self.session.get(f"{self.base_url}/download/{job_id}?format={fmt}")
                
                if download_response.status_code == 200:
                    content_length = len(download_response.content)
                    print(f"✅ {fmt.upper()} download successful ({content_length} bytes)")
                else:
                    print(f"❌ {fmt.upper()} download failed: HTTP {download_response.status_code}")
                    return False
                    
            except Exception as e:
                print(f"❌ Error downloading {fmt}: {e}")
                return False
        
        return True
    
    def test_server_health(self):
        """Test if server is responsive"""
        print("🏥 Testing Server Health...")
        
        try:
            response = self.session.get(self.base_url)
            
            if response.status_code == 200:
                print("✅ Server is responsive")
                return True
            else:
                print(f"❌ Server returned HTTP {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Server health check failed: {e}")
            return False
    
    def run_all_tests(self):
        """Run all transcription tests"""
        print("🚀 Starting YouTube Transcription Tests")
        print("=" * 50)
        
        # Test server health first
        if not self.test_server_health():
            print("❌ Server health check failed. Aborting tests.")
            return False
        
        results = []
        
        # Run individual tests
        tests = [
            ("Single Video", self.test_single_video),
            ("Batch Processing", self.test_batch_processing),
            ("Playlist Processing", self.test_playlist_processing)
        ]
        
        for test_name, test_func in tests:
            print(f"\n{'='*20} {test_name} {'='*20}")
            try:
                result = test_func()
                results.append((test_name, result))
            except Exception as e:
                print(f"❌ {test_name} crashed: {e}")
                results.append((test_name, False))
        
        # Print summary
        print("\n" + "="*50)
        print("📊 Test Results Summary:")
        print("="*50)
        
        passed = 0
        total = len(results)
        
        for test_name, result in results:
            status = "✅ PASSED" if result else "❌ FAILED"
            print(f"{test_name:<20} {status}")
            if result:
                passed += 1
        
        print(f"\nOverall: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 All transcription features are working correctly!")
            return True
        else:
            print("⚠️  Some transcription features need attention.")
            return False

def main():
    """Main test runner"""
    if len(sys.argv) > 1:
        base_url = sys.argv[1]
    else:
        base_url = BASE_URL
    
    print(f"Testing transcription service at: {base_url}")
    
    tester = TranscriptionTester(base_url)
    success = tester.run_all_tests()
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()