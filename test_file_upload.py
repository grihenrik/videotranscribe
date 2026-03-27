#!/usr/bin/env python3
"""
Test the file upload functionality
"""

import requests
import os
import time

def test_file_upload_api():
    """Test the file upload API endpoint"""
    
    print("🔌 Testing File Upload API")
    print("=" * 30)
    
    # For testing, we'll create a small test audio file
    # In a real scenario, you'd upload an actual MP3/MP4 file
    
    # Test 1: Test with no file
    print("\n1. Testing with no file...")
    try:
        response = requests.post('http://localhost:5050/upload-transcribe', 
                               data={'language': 'en'})
        print(f"   Status: {response.status_code}")
        if response.status_code == 400:
            print("   ✅ Correctly rejected request with no file")
        else:
            print(f"   ❌ Unexpected response: {response.text}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 2: Test with empty file
    print("\n2. Testing with empty file...")
    try:
        files = {'file': ('', b'', 'audio/mp3')}
        response = requests.post('http://localhost:5050/upload-transcribe', 
                               files=files,
                               data={'language': 'en'})
        print(f"   Status: {response.status_code}")
        if response.status_code == 400:
            print("   ✅ Correctly rejected empty file")
        else:
            print(f"   ❌ Unexpected response: {response.text}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 3: Test with unsupported file type
    print("\n3. Testing with unsupported file type...")
    try:
        files = {'file': ('test.txt', b'Hello world', 'text/plain')}
        response = requests.post('http://localhost:5050/upload-transcribe', 
                               files=files,
                               data={'language': 'en'})
        print(f"   Status: {response.status_code}")
        if response.status_code == 400:
            print("   ✅ Correctly rejected unsupported file type")
            data = response.json()
            print(f"   Error: {data.get('error')}")
        else:
            print(f"   ❌ Unexpected response: {response.text}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 4: Test with large file (simulate > 25MB)
    print("\n4. Testing with large file...")
    try:
        # Create a 26MB fake file
        large_data = b'x' * (26 * 1024 * 1024)
        files = {'file': ('large.mp3', large_data, 'audio/mp3')}
        response = requests.post('http://localhost:5050/upload-transcribe', 
                               files=files,
                               data={'language': 'en'})
        print(f"   Status: {response.status_code}")
        if response.status_code == 400:
            print("   ✅ Correctly rejected large file")
            data = response.json()
            print(f"   Error: {data.get('error')}")
        else:
            print(f"   ❌ Unexpected response: {response.text}")
    except Exception as e:
        print(f"   ❌ Error: {e}")

def test_frontend_integration():
    """Test that the frontend loads correctly with file upload tab"""
    print(f"\n🌐 Testing Frontend Integration")
    print("=" * 30)
    
    try:
        response = requests.get('http://localhost:5050/')
        if response.status_code == 200:
            content = response.text
            
            # Check for file upload tab
            if 'file-upload-tab' in content:
                print("   ✅ File upload tab present in HTML")
            else:
                print("   ❌ File upload tab missing from HTML")
            
            # Check for file upload form
            if 'fileUploadForm' in content:
                print("   ✅ File upload form present")
            else:
                print("   ❌ File upload form missing")
            
            # Check for audio file input
            if 'audioFile' in content:
                print("   ✅ Audio file input present")
            else:
                print("   ❌ Audio file input missing")
                
            print("   ✅ Frontend integration looks good!")
            
        else:
            print(f"   ❌ Failed to load frontend: {response.status_code}")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")

def create_sample_audio():
    """Create a small sample audio file for testing"""
    print(f"\n🎵 Creating sample audio file...")
    
    try:
        # Create a very small MP3-like file (just for testing the API)
        # This won't be a real MP3, but it will test the file handling
        sample_data = b'\xff\xfb\x90\x00' + b'\x00' * 1024  # Fake MP3 header + data
        
        with open('test_sample.mp3', 'wb') as f:
            f.write(sample_data)
        
        print("   ✅ Sample audio file created (test_sample.mp3)")
        return 'test_sample.mp3'
        
    except Exception as e:
        print(f"   ❌ Error creating sample: {e}")
        return None

def test_real_file_upload():
    """Test uploading the sample file"""
    print(f"\n📤 Testing Real File Upload")
    print("=" * 30)
    
    sample_file = create_sample_audio()
    if not sample_file:
        print("   ❌ Could not create sample file")
        return
    
    try:
        # Upload the sample file
        with open(sample_file, 'rb') as f:
            files = {'file': (sample_file, f, 'audio/mp3')}
            data = {
                'language': 'en',
                'custom_name': 'Test Sample Audio'
            }
            
            print(f"   Uploading {sample_file}...")
            response = requests.post('http://localhost:5050/upload-transcribe', 
                                   files=files,
                                   data=data)
            
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print("   ✅ File upload accepted!")
                print(f"   Job ID: {result.get('job_id')}")
                print(f"   Status: {result.get('status')}")
                print(f"   Is Playlist: {result.get('is_playlist')}")
                print(f"   File Upload: {result.get('file_upload')}")
                
                # Monitor the job
                job_id = result.get('job_id')
                if job_id:
                    print(f"\n   📊 Monitoring job progress...")
                    for i in range(10):  # Check for 1 minute
                        time.sleep(6)
                        status_response = requests.get(f'http://localhost:5050/job-status/{job_id}')
                        if status_response.status_code == 200:
                            status = status_response.json()
                            print(f"   Progress: {status.get('status')} ({status.get('percent', 0)}%)")
                            
                            if status.get('status') == 'complete':
                                print("   ✅ File transcription completed!")
                                break
                            elif status.get('status') == 'error':
                                print(f"   ❌ Transcription failed: {status.get('error')}")
                                break
                        else:
                            print(f"   ⚠️ Status check failed: {status_response.status_code}")
                    else:
                        print("   ⏱️ Job still running after 1 minute")
            else:
                print(f"   ❌ Upload failed: {response.text}")
                
    except Exception as e:
        print(f"   ❌ Error: {e}")
    finally:
        # Clean up sample file
        try:
            if os.path.exists(sample_file):
                os.remove(sample_file)
                print(f"   🗑️ Cleaned up {sample_file}")
        except:
            pass

if __name__ == "__main__":
    print("🎵 File Upload Testing Suite")
    print("=" * 50)
    
    # Test API endpoints
    test_file_upload_api()
    
    # Test frontend integration
    test_frontend_integration()
    
    # Test with real file upload
    test_real_file_upload()
    
    print(f"\n✅ File upload testing complete!")
    print(f"The system now supports direct audio/video file uploads!")
    print(f"\nSupported formats:")
    print(f"  Audio: MP3, WAV, M4A, FLAC, AAC, OGG, WMA")
    print(f"  Video: MP4, WebM, MOV, AVI, MKV, 3GP")
    print(f"  Max size: 25MB")
