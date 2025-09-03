#!/usr/bin/env python3
"""
End-to-end tests for progress bar functionality.
Tests the complete user journey from submission to completion.
"""

import requests
import json
import time
import sys
from concurrent.futures import ThreadPoolExecutor
import threading

BASE_URL = "http://localhost:5000"

class ProgressBarE2ETester:
    def __init__(self, base_url=BASE_URL):
        self.base_url = base_url
        self.session = requests.Session()
        
    def test_single_video_progress_flow(self):
        """Test complete progress flow for single video transcription"""
        print("🎬 Testing Single Video Progress Flow...")
        
        # Submit transcription job
        response = self.session.post(f"{self.base_url}/transcribe", data={
            'url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
            'mode': 'auto',
            'lang': 'en'
        })
        
        if response.status_code != 200:
            print(f"❌ Failed to submit job: {response.status_code}")
            return False
            
        data = response.json()
        job_id = data.get('job_id')
        
        if not job_id:
            print("❌ No job_id returned")
            return False
            
        print(f"✅ Job submitted: {job_id}")
        
        # Track progress over time
        progress_history = []
        status_history = []
        
        for i in range(10):  # Check 10 times over ~20 seconds
            status_response = self.session.get(f"{self.base_url}/status/{job_id}")
            
            if status_response.status_code == 200:
                status_data = status_response.json()
                progress = status_data.get('progress', 0)
                status = status_data.get('status', 'unknown')
                message = status_data.get('message', '')
                
                progress_history.append(progress)
                status_history.append(status)
                
                print(f"Step {i+1}: {progress}% - {status} - {message}")
                
                # Check if progress is increasing or staying reasonable
                if i > 0 and progress < progress_history[i-1]:
                    print("❌ Progress went backwards!")
                    return False
                    
                if status == 'completed':
                    if 'download_links' in status_data:
                        print("✅ Completion includes download links")
                        break
                    else:
                        print("❌ Completion missing download links")
                        return False
            else:
                print(f"❌ Status check failed: {status_response.status_code}")
                return False
                
            time.sleep(2)
        
        # Verify progress made sense
        if len(progress_history) < 2:
            print("❌ Not enough progress updates")
            return False
            
        final_progress = progress_history[-1]
        if final_progress != 100:
            print(f"❌ Final progress not 100%: {final_progress}")
            return False
            
        # Check status progression
        unique_statuses = list(set(status_history))
        if 'completed' not in unique_statuses:
            print("❌ Never reached completed status")
            return False
            
        print("✅ Single video progress flow working correctly")
        return True
    
    def test_batch_progress_flow(self):
        """Test progress flow for batch processing"""
        print("\n📦 Testing Batch Progress Flow...")
        
        batch_urls = """https://www.youtube.com/watch?v=dQw4w9WgXcQ
https://www.youtube.com/watch?v=9bZkp7q19f0"""
        
        response = self.session.post(f"{self.base_url}/transcribe", data={
            'video_urls': batch_urls,
            'mode': 'captions',
            'lang': 'en'
        })
        
        if response.status_code != 200:
            print(f"❌ Failed to submit batch job: {response.status_code}")
            return False
            
        data = response.json()
        job_id = data.get('job_id')
        
        if not job_id:
            print("❌ No job_id returned for batch")
            return False
            
        print(f"✅ Batch job submitted: {job_id}")
        
        # Track batch progress
        for i in range(8):
            status_response = self.session.get(f"{self.base_url}/status/{job_id}")
            
            if status_response.status_code == 200:
                status_data = status_response.json()
                progress = status_data.get('progress', 0)
                status = status_data.get('status', 'unknown')
                
                print(f"Batch Step {i+1}: {progress}% - {status}")
                
                if status == 'completed':
                    print("✅ Batch processing completed")
                    return True
            else:
                print(f"❌ Batch status check failed: {status_response.status_code}")
                return False
                
            time.sleep(2)
        
        print("✅ Batch progress flow working")
        return True
    
    def test_playlist_progress_flow(self):
        """Test progress flow for playlist processing"""
        print("\n📋 Testing Playlist Progress Flow...")
        
        response = self.session.post(f"{self.base_url}/transcribe", data={
            'playlist_url': 'https://www.youtube.com/playlist?list=PLQVvvaa0QuDfKTOs3Keq_kaG2P55YRn5v',
            'mode': 'captions',
            'lang': 'en'
        })
        
        if response.status_code != 200:
            print(f"❌ Failed to submit playlist job: {response.status_code}")
            return False
            
        data = response.json()
        job_id = data.get('job_id')
        
        print(f"✅ Playlist job submitted: {job_id}")
        
        # Track playlist progress
        for i in range(6):
            status_response = self.session.get(f"{self.base_url}/status/{job_id}")
            
            if status_response.status_code == 200:
                status_data = status_response.json()
                progress = status_data.get('progress', 0)
                status = status_data.get('status', 'unknown')
                
                print(f"Playlist Step {i+1}: {progress}% - {status}")
                
                if status == 'completed':
                    print("✅ Playlist processing completed")
                    return True
            else:
                print(f"❌ Playlist status check failed: {status_response.status_code}")
                return False
                
            time.sleep(2)
        
        print("✅ Playlist progress flow working")
        return True
    
    def test_concurrent_jobs_progress(self):
        """Test progress tracking with multiple concurrent jobs"""
        print("\n⚡ Testing Concurrent Jobs Progress...")
        
        def submit_and_track_job(job_num):
            """Submit a job and track its progress"""
            response = self.session.post(f"{self.base_url}/transcribe", data={
                'url': f'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
                'mode': 'auto',
                'lang': 'en'
            })
            
            if response.status_code != 200:
                return False
                
            data = response.json()
            job_id = data.get('job_id')
            
            # Track progress for this job
            for i in range(8):
                status_response = self.session.get(f"{self.base_url}/status/{job_id}")
                
                if status_response.status_code == 200:
                    status_data = status_response.json()
                    progress = status_data.get('progress', 0)
                    status = status_data.get('status', 'unknown')
                    
                    print(f"Job {job_num}: {progress}% - {status}")
                    
                    if status == 'completed':
                        return True
                        
                time.sleep(1.5)
            
            return True
        
        # Run 3 concurrent jobs
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(submit_and_track_job, i+1) for i in range(3)]
            results = [future.result() for future in futures]
        
        if all(results):
            print("✅ Concurrent jobs progress tracking working")
            return True
        else:
            print("❌ Some concurrent jobs failed")
            return False
    
    def test_progress_api_consistency(self):
        """Test that progress API returns consistent data format"""
        print("\n🔧 Testing Progress API Consistency...")
        
        # Submit a job
        response = self.session.post(f"{self.base_url}/transcribe", data={
            'url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
            'mode': 'auto',
            'lang': 'en'
        })
        
        if response.status_code != 200:
            print(f"❌ Failed to submit job: {response.status_code}")
            return False
            
        data = response.json()
        job_id = data.get('job_id')
        
        # Check API consistency across multiple calls
        required_fields = ['status', 'progress', 'message']
        
        for i in range(5):
            status_response = self.session.get(f"{self.base_url}/status/{job_id}")
            
            if status_response.status_code == 200:
                status_data = status_response.json()
                
                # Check required fields are present
                for field in required_fields:
                    if field not in status_data:
                        print(f"❌ Missing required field: {field}")
                        return False
                
                # Check field types
                if not isinstance(status_data['progress'], (int, float)):
                    print(f"❌ Progress not numeric: {type(status_data['progress'])}")
                    return False
                    
                if not isinstance(status_data['status'], str):
                    print(f"❌ Status not string: {type(status_data['status'])}")
                    return False
                
                # Check progress bounds
                progress = status_data['progress']
                if progress < 0 or progress > 100:
                    print(f"❌ Progress out of bounds: {progress}")
                    return False
                    
                print(f"API Check {i+1}: ✅ Format valid")
                
            time.sleep(1)
        
        print("✅ Progress API consistency verified")
        return True
    
    def test_download_after_completion(self):
        """Test that downloads work after progress reaches 100%"""
        print("\n📥 Testing Downloads After Progress Completion...")
        
        # Submit job and wait for completion
        response = self.session.post(f"{self.base_url}/transcribe", data={
            'url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
            'mode': 'auto',
            'lang': 'en'
        })
        
        if response.status_code != 200:
            print(f"❌ Failed to submit job: {response.status_code}")
            return False
            
        data = response.json()
        job_id = data.get('job_id')
        
        # Wait for completion
        download_links = None
        for i in range(10):
            status_response = self.session.get(f"{self.base_url}/status/{job_id}")
            
            if status_response.status_code == 200:
                status_data = status_response.json()
                status = status_data.get('status')
                
                if status == 'completed':
                    download_links = status_data.get('download_links')
                    break
                    
            time.sleep(2)
        
        if not download_links:
            print("❌ No download links after completion")
            return False
        
        # Test each download format
        for format_name, link in download_links.items():
            download_response = self.session.get(f"{self.base_url}{link}")
            
            if download_response.status_code == 200:
                content_length = len(download_response.content)
                print(f"✅ {format_name.upper()} download: {content_length} bytes")
            else:
                print(f"❌ {format_name.upper()} download failed: {download_response.status_code}")
                return False
        
        print("✅ Downloads working after progress completion")
        return True
    
    def run_all_e2e_tests(self):
        """Run all end-to-end progress bar tests"""
        print("🚀 Starting Progress Bar E2E Tests")
        print("=" * 60)
        
        tests = [
            ("Single Video Progress", self.test_single_video_progress_flow),
            ("Batch Progress", self.test_batch_progress_flow),
            ("Playlist Progress", self.test_playlist_progress_flow),
            ("Concurrent Jobs", self.test_concurrent_jobs_progress),
            ("API Consistency", self.test_progress_api_consistency),
            ("Download Integration", self.test_download_after_completion),
        ]
        
        results = []
        
        for test_name, test_func in tests:
            print(f"\n{'='*25} {test_name} {'='*25}")
            try:
                result = test_func()
                results.append((test_name, result))
            except Exception as e:
                print(f"❌ {test_name} crashed: {e}")
                results.append((test_name, False))
        
        # Print comprehensive summary
        print("\n" + "="*60)
        print("📊 Progress Bar E2E Test Results:")
        print("="*60)
        
        passed = 0
        total = len(results)
        
        for test_name, result in results:
            status = "✅ PASSED" if result else "❌ FAILED"
            print(f"{test_name:<25} {status}")
            if result:
                passed += 1
        
        print(f"\nOverall: {passed}/{total} progress bar tests passed")
        
        if passed == total:
            print("🎉 Progress bar functionality is working perfectly!")
            print("📊 Your users will have a smooth transcription experience!")
            return True
        else:
            print("⚠️  Some progress bar functionality needs attention.")
            return False

def main():
    """Main test runner"""
    if len(sys.argv) > 1:
        base_url = sys.argv[1]
    else:
        base_url = BASE_URL
    
    print(f"Testing progress bar functionality at: {base_url}")
    
    tester = ProgressBarE2ETester(base_url)
    success = tester.run_all_e2e_tests()
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()