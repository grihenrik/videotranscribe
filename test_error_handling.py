#!/usr/bin/env python3
"""
Error handling test suite for YouTube transcription platform.
Tests various error scenarios and edge cases.
"""

import requests
import json
import time
import sys

# Configuration
BASE_URL = "http://localhost:5000"

class ErrorHandlingTester:
    def __init__(self, base_url=BASE_URL):
        self.base_url = base_url
        self.session = requests.Session()
        
    def test_invalid_urls(self):
        """Test handling of invalid YouTube URLs"""
        print("🔗 Testing Invalid URL Handling...")
        
        invalid_urls = [
            "not-a-url",
            "https://example.com",
            "https://youtube.com/invalid",
            "",
            "https://www.youtube.com/watch?v=invalid123",
        ]
        
        for url in invalid_urls:
            try:
                response = self.session.post(f"{self.base_url}/transcribe", data={
                    'url': url,
                    'mode': 'auto',
                    'lang': 'en'
                })
                
                if response.status_code == 400:
                    print(f"✅ Invalid URL rejected: {url[:30]}...")
                else:
                    print(f"❌ Invalid URL accepted: {url[:30]}... (Status: {response.status_code})")
                    return False
                    
            except Exception as e:
                print(f"❌ Error testing invalid URL {url}: {e}")
                return False
        
        print("✅ All invalid URLs properly rejected")
        return True
    
    def test_missing_parameters(self):
        """Test handling of missing required parameters"""
        print("\n📝 Testing Missing Parameter Handling...")
        
        test_cases = [
            {},  # No parameters
            {'mode': 'auto'},  # Missing URL
            {'url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'},  # Missing mode and lang
        ]
        
        for i, data in enumerate(test_cases):
            try:
                response = self.session.post(f"{self.base_url}/transcribe", data=data)
                
                if response.status_code in [400, 422]:
                    print(f"✅ Missing parameters test {i+1} handled correctly")
                else:
                    print(f"❌ Missing parameters test {i+1} not handled (Status: {response.status_code})")
                    return False
                    
            except Exception as e:
                print(f"❌ Error in missing parameters test {i+1}: {e}")
                return False
        
        print("✅ All missing parameter cases handled correctly")
        return True
    
    def test_malformed_requests(self):
        """Test handling of malformed requests"""
        print("\n🔧 Testing Malformed Request Handling...")
        
        try:
            # Test invalid JSON
            response = self.session.post(f"{self.base_url}/transcribe", 
                                       data="invalid json",
                                       headers={'Content-Type': 'application/json'})
            
            if response.status_code in [400, 422]:
                print("✅ Invalid JSON handled correctly")
            else:
                print(f"❌ Invalid JSON not handled (Status: {response.status_code})")
                return False
            
            # Test wrong HTTP method
            response = self.session.get(f"{self.base_url}/transcribe")
            
            if response.status_code == 405:
                print("✅ Wrong HTTP method handled correctly")
            else:
                print(f"❌ Wrong HTTP method not handled (Status: {response.status_code})")
                return False
                
        except Exception as e:
            print(f"❌ Error testing malformed requests: {e}")
            return False
        
        print("✅ All malformed requests handled correctly")
        return True
    
    def test_batch_edge_cases(self):
        """Test batch processing edge cases"""
        print("\n📦 Testing Batch Processing Edge Cases...")
        
        edge_cases = [
            "",  # Empty batch
            "\n\n\n",  # Only newlines
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ\n\n\nhttps://www.youtube.com/watch?v=9bZkp7q19f0",  # Mixed valid/empty
            "invalid-url\nhttps://www.youtube.com/watch?v=dQw4w9WgXcQ",  # Mixed invalid/valid
        ]
        
        for i, batch_urls in enumerate(edge_cases):
            try:
                response = self.session.post(f"{self.base_url}/transcribe", data={
                    'video_urls': batch_urls,
                    'mode': 'auto',
                    'lang': 'en'
                })
                
                if batch_urls.strip() == "":
                    if response.status_code == 400:
                        print(f"✅ Empty batch test {i+1} handled correctly")
                    else:
                        print(f"❌ Empty batch test {i+1} not handled (Status: {response.status_code})")
                        return False
                else:
                    if response.status_code == 200:
                        print(f"✅ Batch edge case {i+1} handled correctly")
                    else:
                        print(f"❌ Batch edge case {i+1} not handled (Status: {response.status_code})")
                        return False
                        
            except Exception as e:
                print(f"❌ Error in batch edge case {i+1}: {e}")
                return False
        
        print("✅ All batch edge cases handled correctly")
        return True
    
    def test_nonexistent_endpoints(self):
        """Test handling of requests to nonexistent endpoints"""
        print("\n🔍 Testing Nonexistent Endpoint Handling...")
        
        nonexistent_endpoints = [
            "/api/nonexistent",
            "/transcribe/invalid",
            "/status/nonexistent-job",
            "/download/nonexistent-job",
        ]
        
        for endpoint in nonexistent_endpoints:
            try:
                response = self.session.get(f"{self.base_url}{endpoint}")
                
                if response.status_code == 404:
                    print(f"✅ Nonexistent endpoint handled: {endpoint}")
                else:
                    print(f"❌ Nonexistent endpoint not handled: {endpoint} (Status: {response.status_code})")
                    return False
                    
            except Exception as e:
                print(f"❌ Error testing nonexistent endpoint {endpoint}: {e}")
                return False
        
        print("✅ All nonexistent endpoints handled correctly")
        return True
    
    def test_status_api_consistency(self):
        """Test status API consistency"""
        print("\n📊 Testing Status API Consistency...")
        
        try:
            # Submit a job first
            response = self.session.post(f"{self.base_url}/transcribe", data={
                'url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
                'mode': 'auto',
                'lang': 'en'
            })
            
            if response.status_code != 200:
                print(f"❌ Failed to submit test job (Status: {response.status_code})")
                return False
            
            job_data = response.json()
            job_id = job_data['job_id']
            
            # Test status endpoint
            status_response = self.session.get(f"{self.base_url}/status/{job_id}")
            
            if status_response.status_code == 200:
                status_data = status_response.json()
                
                # Check required fields
                required_fields = ['status', 'progress', 'message']
                for field in required_fields:
                    if field not in status_data:
                        print(f"❌ Missing required field in status response: {field}")
                        return False
                
                print("✅ Status API response format correct")
            else:
                print(f"❌ Status API not working (Status: {status_response.status_code})")
                return False
                
        except Exception as e:
            print(f"❌ Error testing status API: {e}")
            return False
        
        print("✅ Status API consistency verified")
        return True
    
    def test_download_api_robustness(self):
        """Test download API robustness"""
        print("\n📥 Testing Download API Robustness...")
        
        try:
            # Submit a job first
            response = self.session.post(f"{self.base_url}/transcribe", data={
                'url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
                'mode': 'auto',
                'lang': 'en'
            })
            
            if response.status_code != 200:
                print(f"❌ Failed to submit test job (Status: {response.status_code})")
                return False
            
            job_data = response.json()
            job_id = job_data['job_id']
            
            # Test different formats
            formats = ['txt', 'srt', 'vtt', 'invalid_format']
            
            for fmt in formats:
                download_response = self.session.get(f"{self.base_url}/download/{job_id}?format={fmt}")
                
                if fmt == 'invalid_format':
                    # Should default to txt or return error
                    if download_response.status_code in [200, 400]:
                        print(f"✅ Invalid format handled: {fmt}")
                    else:
                        print(f"❌ Invalid format not handled: {fmt} (Status: {download_response.status_code})")
                        return False
                else:
                    if download_response.status_code == 200:
                        print(f"✅ Download format working: {fmt}")
                    else:
                        print(f"❌ Download format not working: {fmt} (Status: {download_response.status_code})")
                        return False
                        
        except Exception as e:
            print(f"❌ Error testing download API: {e}")
            return False
        
        print("✅ Download API robustness verified")
        return True
    
    def run_all_error_tests(self):
        """Run all error handling tests"""
        print("🚨 Starting Error Handling Tests")
        print("=" * 50)
        
        tests = [
            ("Invalid URLs", self.test_invalid_urls),
            ("Missing Parameters", self.test_missing_parameters),
            ("Malformed Requests", self.test_malformed_requests),
            ("Batch Edge Cases", self.test_batch_edge_cases),
            ("Nonexistent Endpoints", self.test_nonexistent_endpoints),
            ("Status API Consistency", self.test_status_api_consistency),
            ("Download API Robustness", self.test_download_api_robustness),
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
        
        # Print summary
        print("\n" + "="*50)
        print("🛡️  Error Handling Test Results:")
        print("="*50)
        
        passed = 0
        total = len(results)
        
        for test_name, result in results:
            status = "✅ PASSED" if result else "❌ FAILED"
            print(f"{test_name:<25} {status}")
            if result:
                passed += 1
        
        print(f"\nOverall: {passed}/{total} error handling tests passed")
        
        if passed == total:
            print("🎉 All error handling is working correctly!")
            print("🛡️  Your platform gracefully handles all edge cases!")
            return True
        else:
            print("⚠️  Some error handling needs improvement.")
            return False

def main():
    """Main test runner"""
    if len(sys.argv) > 1:
        base_url = sys.argv[1]
    else:
        base_url = BASE_URL
    
    print(f"Testing error handling for transcription service at: {base_url}")
    
    tester = ErrorHandlingTester(base_url)
    success = tester.run_all_error_tests()
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()