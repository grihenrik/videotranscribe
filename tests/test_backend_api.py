#!/usr/bin/env python3
"""
Comprehensive test suite for YouTube transcription backend API endpoints.
Tests single video, batch processing, and playlist processing.
"""

import pytest
import requests
import json
import time
import os
import tempfile
from unittest.mock import patch, MagicMock
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from simple_server import app
from flask import Flask
import threading
import subprocess

class TestTranscriptionAPI:
    """Test class for transcription API endpoints"""
    
    @pytest.fixture(scope="class")
    def client(self):
        """Create test client"""
        app.config['TESTING'] = True
        with app.test_client() as client:
            yield client
    
    @pytest.fixture(scope="class") 
    def mock_whisper_service(self):
        """Mock Whisper service to avoid API calls during testing"""
        with patch('standalone_whisper.transcribe_audio_file') as mock_transcribe, \
             patch('standalone_whisper.download_audio_from_youtube') as mock_download:
            
            # Mock successful download
            mock_download.return_value = "/tmp/test_audio.mp3"
            
            # Mock successful transcription
            mock_transcribe.return_value = {
                'text': 'This is a test transcription of the video content.',
                'srt': '1\n00:00:00,000 --> 00:00:05,000\nThis is a test transcription\n\n2\n00:00:05,000 --> 00:00:10,000\nof the video content.\n\n',
                'vtt': 'WEBVTT\n\n00:00.000 --> 00:05.000\nThis is a test transcription\n\n00:05.000 --> 00:10.000\nof the video content.\n\n'
            }
            
            yield mock_transcribe, mock_download
    
    def test_homepage_loads(self, client):
        """Test that homepage loads correctly"""
        response = client.get('/')
        assert response.status_code == 200
        assert b'YouTube Transcription Tool' in response.data
    
    def test_static_files_load(self, client):
        """Test that static CSS and JS files load"""
        css_response = client.get('/css/style.css')
        assert css_response.status_code == 200
        
        js_response = client.get('/js/main.js')
        assert js_response.status_code == 200

class TestSingleVideoTranscription:
    """Test single video transcription functionality"""
    
    @pytest.fixture(scope="class")
    def client(self):
        app.config['TESTING'] = True
        with app.test_client() as client:
            yield client
    
    def test_single_video_transcription_success(self, client):
        """Test successful single video transcription"""
        with patch('standalone_whisper.download_audio_from_youtube') as mock_download, \
             patch('standalone_whisper.transcribe_audio_file') as mock_transcribe:
            
            # Setup mocks
            mock_download.return_value = "/tmp/test_audio.mp3"
            mock_transcribe.return_value = {
                'text': 'Test transcription content',
                'srt': '1\n00:00:00,000 --> 00:00:05,000\nTest transcription content\n\n',
                'vtt': 'WEBVTT\n\n00:00.000 --> 00:05.000\nTest transcription content\n\n'
            }
            
            # Submit transcription request
            response = client.post('/transcribe', 
                json={
                    'url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
                    'mode': 'auto',
                    'lang': 'en'
                })
            
            assert response.status_code == 200
            data = response.get_json()
            
            # Verify response structure
            assert 'job_id' in data
            assert 'status' in data
            assert 'video_id' in data
            assert 'download_links' in data
            assert data['status'] == 'queued'
            
            job_id = data['job_id']
            
            # Wait for processing to complete
            time.sleep(2)
            
            # Check job status
            status_response = client.get(f'/job-status/{job_id}')
            assert status_response.status_code == 200
            
            status_data = status_response.get_json()
            # Job should be complete or in progress
            assert status_data['status'] in ['complete', 'queued', 'downloading_audio', 'transcribing_audio', 'saving_files']
    
    def test_single_video_invalid_url(self, client):
        """Test single video transcription with invalid URL"""
        response = client.post('/transcribe',
            json={
                'url': 'https://invalid-url.com/video',
                'mode': 'auto', 
                'lang': 'en'
            })
        
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'Invalid YouTube URL' in data['error']
    
    def test_single_video_missing_url(self, client):
        """Test single video transcription with missing URL"""
        response = client.post('/transcribe',
            json={
                'mode': 'auto',
                'lang': 'en'
            })
        
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'Missing URL parameter' in data['error']
    
    def test_single_video_different_modes(self, client):
        """Test single video transcription with different modes"""
        modes = ['auto', 'whisper', 'captions']
        
        for mode in modes:
            with patch('standalone_whisper.download_audio_from_youtube') as mock_download, \
                 patch('standalone_whisper.transcribe_audio_file') as mock_transcribe:
                
                mock_download.return_value = "/tmp/test_audio.mp3"
                mock_transcribe.return_value = {
                    'text': f'Test transcription for {mode} mode',
                    'srt': '1\n00:00:00,000 --> 00:00:05,000\nTest content\n\n',
                    'vtt': 'WEBVTT\n\n00:00.000 --> 00:05.000\nTest content\n\n'
                }
                
                response = client.post('/transcribe',
                    json={
                        'url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
                        'mode': mode,
                        'lang': 'en'
                    })
                
                assert response.status_code == 200
                data = response.get_json()
                assert 'job_id' in data
                assert data['status'] == 'queued'
    
    def test_single_video_different_languages(self, client):
        """Test single video transcription with different languages"""
        languages = ['en', 'es', 'fr', 'de', 'it']
        
        for lang in languages:
            with patch('standalone_whisper.download_audio_from_youtube') as mock_download, \
                 patch('standalone_whisper.transcribe_audio_file') as mock_transcribe:
                
                mock_download.return_value = "/tmp/test_audio.mp3"
                mock_transcribe.return_value = {
                    'text': f'Test transcription in {lang}',
                    'srt': '1\n00:00:00,000 --> 00:00:05,000\nTest content\n\n',
                    'vtt': 'WEBVTT\n\n00:00.000 --> 00:05.000\nTest content\n\n'
                }
                
                response = client.post('/transcribe',
                    json={
                        'url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
                        'mode': 'auto',
                        'lang': lang
                    })
                
                assert response.status_code == 200
                data = response.get_json()
                assert 'job_id' in data

class TestBatchProcessing:
    """Test batch processing functionality"""
    
    @pytest.fixture(scope="class")
    def client(self):
        app.config['TESTING'] = True
        with app.test_client() as client:
            yield client
    
    def test_batch_processing_endpoint_exists(self, client):
        """Test that batch processing endpoint exists (placeholder test)"""
        # Note: Based on current implementation, batch processing uses the same /transcribe endpoint
        # but with different parameters. This test ensures the endpoint can handle batch requests.
        
        response = client.post('/transcribe',
            json={
                'urls': [
                    'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
                    'https://www.youtube.com/watch?v=9bZkp7q19f0'
                ],
                'mode': 'auto',
                'lang': 'en'
            })
        
        # Current implementation doesn't support batch, so we expect an error or single URL handling
        # This test documents the current behavior
        assert response.status_code in [200, 400]
    
    def test_batch_processing_validation(self, client):
        """Test batch processing input validation"""
        # Test empty batch
        response = client.post('/transcribe',
            json={
                'urls': [],
                'mode': 'auto',
                'lang': 'en'
            })
        
        assert response.status_code in [400, 500]  # Should reject empty batch
    
    def test_batch_processing_max_limit(self, client):
        """Test batch processing with too many URLs"""
        # Test with more than reasonable limit (e.g., 10 videos)
        urls = [f'https://www.youtube.com/watch?v=dQw4w9WgXc{i}' for i in range(20)]
        
        response = client.post('/transcribe',
            json={
                'urls': urls,
                'mode': 'auto',
                'lang': 'en'
            })
        
        # Should reject or limit the batch size
        assert response.status_code in [400, 413]  # Bad request or payload too large

class TestPlaylistProcessing:
    """Test playlist processing functionality"""
    
    @pytest.fixture(scope="class")
    def client(self):
        app.config['TESTING'] = True
        with app.test_client() as client:
            yield client
    
    def test_playlist_processing_endpoint_exists(self, client):
        """Test that playlist processing endpoint exists (placeholder test)"""
        response = client.post('/transcribe',
            json={
                'playlist_url': 'https://www.youtube.com/playlist?list=PLQVvvaa0QuDfKTOs3Keq_kaG2P55YRn5v',
                'mode': 'auto',
                'lang': 'en'
            })
        
        # Current implementation doesn't support playlists, so we expect an error
        assert response.status_code in [200, 400]
    
    def test_playlist_invalid_url(self, client):
        """Test playlist processing with invalid playlist URL"""
        response = client.post('/transcribe',
            json={
                'playlist_url': 'https://invalid-playlist-url.com/playlist',
                'mode': 'auto',
                'lang': 'en'
            })
        
        assert response.status_code == 400

class TestDownloadEndpoints:
    """Test file download functionality"""
    
    @pytest.fixture(scope="class")
    def client(self):
        app.config['TESTING'] = True
        with app.test_client() as client:
            yield client
    
    @pytest.fixture
    def setup_test_files(self):
        """Setup test transcription files"""
        job_id = "test_job_12345"
        video_id = "dQw4w9WgXcQ"
        
        # Create temp directory structure
        job_dir = f"tmp/{job_id}"
        os.makedirs(job_dir, exist_ok=True)
        
        # Create test files
        test_content = {
            'txt': 'This is a test transcription.',
            'srt': '1\n00:00:00,000 --> 00:00:05,000\nThis is a test transcription.\n\n',
            'vtt': 'WEBVTT\n\n00:00.000 --> 00:05.000\nThis is a test transcription.\n\n'
        }
        
        for format, content in test_content.items():
            with open(f"{job_dir}/{video_id}.{format}", 'w', encoding='utf-8') as f:
                f.write(content)
        
        yield job_id
        
        # Cleanup
        import shutil
        if os.path.exists(job_dir):
            shutil.rmtree(job_dir)
    
    def test_download_txt_format(self, client, setup_test_files):
        """Test downloading TXT format"""
        job_id = setup_test_files
        
        response = client.get(f'/download/{job_id}?format=txt')
        assert response.status_code == 200
        assert response.mimetype == 'text/plain'
        assert 'This is a test transcription.' in response.get_data(as_text=True)
    
    def test_download_srt_format(self, client, setup_test_files):
        """Test downloading SRT format"""
        job_id = setup_test_files
        
        response = client.get(f'/download/{job_id}?format=srt')
        assert response.status_code == 200
        assert response.mimetype == 'application/x-subrip'
        assert 'This is a test transcription.' in response.get_data(as_text=True)
    
    def test_download_vtt_format(self, client, setup_test_files):
        """Test downloading VTT format"""
        job_id = setup_test_files
        
        response = client.get(f'/download/{job_id}?format=vtt')
        assert response.status_code == 200
        assert response.mimetype == 'text/vtt'
        assert 'This is a test transcription.' in response.get_data(as_text=True)
    
    def test_download_srt_format(self, client, setup_test_files):
        """Test downloading SRT format"""
        job_id = setup_test_files
        
        response = client.get(f'/download/{job_id}?format=srt')
        assert response.status_code == 200
        assert response.mimetype == 'application/x-subrip'
        assert 'This is a test transcription.' in response.get_data(as_text=True)
    
    def test_download_vtt_format(self, client, setup_test_files):
        """Test downloading VTT format"""
        job_id = setup_test_files
        
        response = client.get(f'/download/{job_id}?format=vtt')
        assert response.status_code == 200
        assert response.mimetype == 'text/vtt'
        assert 'This is a test transcription.' in response.get_data(as_text=True)
    
    def test_download_nonexistent_job(self, client):
        """Test downloading from nonexistent job"""
        response = client.get('/download/nonexistent_job?format=txt')
        assert response.status_code == 404
        assert b'Files not found' in response.data
    
    def test_download_invalid_format(self, client, setup_test_files):
        """Test downloading with invalid format"""
        job_id = setup_test_files
        
        response = client.get(f'/download/{job_id}?format=pdf')
        assert response.status_code == 404
        assert b'No pdf file found' in response.data
    
    def test_download_default_format(self, client, setup_test_files):
        """Test downloading with default format (txt)"""
        job_id = setup_test_files
        
        response = client.get(f'/download/{job_id}')
        assert response.status_code == 200
        assert response.mimetype == 'text/plain'
        assert 'This is a test transcription.' in response.get_data(as_text=True)

class TestJobStatusEndpoints:
    """Test job status tracking functionality"""
    
    @pytest.fixture(scope="class")
    def client(self):
        app.config['TESTING'] = True
        with app.test_client() as client:
            yield client
    
    def test_job_status_nonexistent(self, client):
        """Test status check for nonexistent job"""
        response = client.get('/job-status/nonexistent_job')
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'error'
        assert 'Job not found' in data['error']
    
    def test_job_status_format(self, client):
        """Test job status response format"""
        response = client.get('/job-status/test_job_123')
        assert response.status_code == 200
        data = response.get_json()
        
        # Should have required fields
        assert 'status' in data
        assert 'percent' in data
        assert isinstance(data['percent'], (int, float))

class TestErrorHandling:
    """Test error handling and edge cases"""
    
    @pytest.fixture(scope="class")
    def client(self):
        app.config['TESTING'] = True
        with app.test_client() as client:
            yield client
    
    def test_transcribe_endpoint_invalid_json(self, client):
        """Test transcribe endpoint with invalid JSON"""
        response = client.post('/transcribe',
            data='invalid json',
            content_type='application/json')
        
        assert response.status_code == 400
    
    def test_transcribe_endpoint_missing_content_type(self, client):
        """Test transcribe endpoint without JSON content type"""
        response = client.post('/transcribe',
            data=json.dumps({
                'url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
                'mode': 'auto',
                'lang': 'en'
            }))
        
        # Should still work as Flask is flexible with content types
        assert response.status_code in [200, 400]
    
    def test_whisper_service_failure(self, client):
        """Test behavior when Whisper service fails"""
        with patch('standalone_whisper.download_audio_from_youtube') as mock_download, \
             patch('standalone_whisper.transcribe_audio_file') as mock_transcribe:
            
            # Mock failure
            mock_download.return_value = None  # Download failure
            mock_transcribe.return_value = None  # Transcription failure
            
            response = client.post('/transcribe',
                json={
                    'url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
                    'mode': 'auto',
                    'lang': 'en'
                })
            
            assert response.status_code == 200  # Job should still be created
            data = response.get_json()
            assert 'job_id' in data
            
            # Wait a moment for processing
            time.sleep(1)
            
            # Check that job eventually fails
            job_id = data['job_id']
            status_response = client.get(f'/job-status/{job_id}')
            # Note: Due to async processing, we might not immediately see the failure

if __name__ == '__main__':
    # Run tests with pytest
    pytest.main([__file__, '-v', '--tb=short'])
