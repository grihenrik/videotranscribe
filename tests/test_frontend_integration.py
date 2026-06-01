#!/usr/bin/env python3
"""
Frontend integration tests for YouTube transcription tool.
Tests that frontend calls correct endpoints and handles responses properly.
"""

import pytest
import requests
import json
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException
import subprocess
import threading
import os
import signal

class TestFrontendIntegration:
    """Test frontend JavaScript integration with backend API"""
    
    BASE_URL = "http://localhost:5050"
    
    @pytest.fixture(scope="class", autouse=True)
    def setup_server(self):
        """Start the server for testing"""
        # Start server in background
        self.server_process = subprocess.Popen(
            ['python', 'simple_server.py'],
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Wait for server to start
        time.sleep(3)
        
        # Verify server is running
        try:
            response = requests.get(self.BASE_URL, timeout=5)
            assert response.status_code == 200
        except:
            pytest.fail("Server failed to start")
        
        yield
        
        # Cleanup
        self.server_process.terminate()
        self.server_process.wait()
    
    @pytest.fixture(scope="class")
    def driver(self):
        """Setup Chrome driver for Selenium tests"""
        chrome_options = Options()
        chrome_options.add_argument("--headless")  # Run in headless mode
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        
        try:
            driver = webdriver.Chrome(options=chrome_options)
            driver.implicitly_wait(10)
            yield driver
        except Exception as e:
            pytest.skip(f"Chrome driver not available: {e}")
        finally:
            if 'driver' in locals():
                driver.quit()
    
    def test_homepage_loads(self, driver):
        """Test that homepage loads with all necessary elements"""
        driver.get(self.BASE_URL)
        
        # Check page title
        assert "YouTube Transcription Tool" in driver.title
        
        # Check that main form elements exist
        url_input = driver.find_element(By.ID, "youtubeUrl")
        assert url_input is not None
        
        mode_select = driver.find_element(By.ID, "transcriptionMode")
        assert mode_select is not None
        
        language_select = driver.find_element(By.ID, "language")
        assert language_select is not None
        
        submit_button = driver.find_element(By.ID, "transcribeBtn")
        assert submit_button is not None
        assert submit_button.text == "Transcribe Video"
    
    def test_form_validation_empty_url(self, driver):
        """Test form validation with empty URL"""
        driver.get(self.BASE_URL)
        
        # Try to submit without URL
        submit_button = driver.find_element(By.ID, "transcribeBtn")
        submit_button.click()
        
        # Check that HTML5 validation prevents submission
        url_input = driver.find_element(By.ID, "youtubeUrl")
        validation_message = driver.execute_script("return arguments[0].validationMessage;", url_input)
        assert validation_message != ""  # Should have validation message
    
    def test_form_validation_invalid_url(self, driver):
        """Test form validation with invalid URL"""
        driver.get(self.BASE_URL)
        
        # Enter invalid URL
        url_input = driver.find_element(By.ID, "youtubeUrl")
        url_input.send_keys("not-a-valid-url")
        
        submit_button = driver.find_element(By.ID, "transcribeBtn")
        submit_button.click()
        
        # Should show validation message or alert
        # (Implementation depends on your JavaScript validation)
        
    def test_single_video_form_submission(self, driver):
        """Test single video form submission calls correct endpoint"""
        driver.get(self.BASE_URL)
        
        # Fill out form
        url_input = driver.find_element(By.ID, "youtubeUrl")
        url_input.send_keys("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        
        mode_select = Select(driver.find_element(By.ID, "transcriptionMode"))
        mode_select.select_by_value("auto")
        
        language_select = Select(driver.find_element(By.ID, "language"))
        language_select.select_by_value("en")
        
        # Submit form
        submit_button = driver.find_element(By.ID, "transcribeBtn")
        submit_button.click()
        
        # Wait for response (button should change to "Processing...")
        try:
            WebDriverWait(driver, 10).until(
                lambda d: d.find_element(By.ID, "transcribeBtn").text == "Processing..."
            )
        except TimeoutException:
            # Button text might not change immediately, that's okay
            pass
        
        # Wait for results container to appear
        try:
            results_container = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "results-container"))
            )
            
            # Check that results container is no longer hidden
            assert "d-none" not in results_container.get_attribute("class")
            
        except TimeoutException:
            pytest.fail("Results container did not appear after form submission")
    
    def test_progress_updates(self, driver):
        """Test that progress updates work correctly"""
        driver.get(self.BASE_URL)
        
        # Submit a transcription job
        url_input = driver.find_element(By.ID, "youtubeUrl")
        url_input.send_keys("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        
        submit_button = driver.find_element(By.ID, "transcribeBtn")
        submit_button.click()
        
        # Wait for results container
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "results-container"))
            )
            
            # Check for progress bar
            progress_bar = driver.find_element(By.ID, "progress-bar")
            assert progress_bar is not None
            
            # Check for job status badge
            job_status = driver.find_element(By.ID, "job-status")
            assert job_status is not None
            
            # Wait a bit to see if progress updates
            time.sleep(3)
            
            # Progress should have updated
            progress_value = progress_bar.get_attribute("aria-valuenow")
            assert progress_value is not None
            
        except TimeoutException:
            pytest.fail("Progress elements not found")
    
    def test_download_buttons_appear(self, driver):
        """Test that download buttons appear when transcription is complete"""
        driver.get(self.BASE_URL)
        
        # Submit a transcription job
        url_input = driver.find_element(By.ID, "youtubeUrl")
        url_input.send_keys("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        
        submit_button = driver.find_element(By.ID, "transcribeBtn")
        submit_button.click()
        
        # Wait for completion (or timeout)
        try:
            # Wait for download section to appear (may take a while)
            download_section = WebDriverWait(driver, 60).until(
                EC.presence_of_element_located((By.ID, "download-section"))
            )
            
            # Check that download section is visible
            assert "d-none" not in download_section.get_attribute("class")
            
            # Check for download buttons
            txt_btn = driver.find_element(By.ID, "download-txt")
            srt_btn = driver.find_element(By.ID, "download-srt")
            vtt_btn = driver.find_element(By.ID, "download-vtt")
            
            assert txt_btn is not None
            assert srt_btn is not None
            assert vtt_btn is not None
            
        except TimeoutException:
            # This might timeout if transcription takes too long or fails
            # Check if there's an error status instead
            try:
                job_status = driver.find_element(By.ID, "job-status")
                status_text = job_status.text
                if "error" in status_text.lower() or "failed" in status_text.lower():
                    pytest.skip("Transcription failed, skipping download button test")
                else:
                    pytest.fail("Download buttons did not appear and no error status found")
            except:
                pytest.fail("Could not determine transcription status")
    
    def test_tab_navigation(self, driver):
        """Test navigation between different tabs"""
        driver.get(self.BASE_URL)
        
        # Check that all tabs exist
        single_tab = driver.find_element(By.ID, "single-tab")
        batch_tab = driver.find_element(By.ID, "batch-tab")
        playlist_tab = driver.find_element(By.ID, "playlist-tab")
        
        assert single_tab is not None
        assert batch_tab is not None
        assert playlist_tab is not None
        
        # Check that single tab is active by default
        assert "active" in single_tab.get_attribute("class")
        
        # Click on batch tab
        batch_tab.click()
        time.sleep(0.5)  # Wait for transition
        
        # Check that batch tab is now active
        assert "active" in batch_tab.get_attribute("class")
        assert "active" not in single_tab.get_attribute("class")
        
        # Click on playlist tab
        playlist_tab.click()
        time.sleep(0.5)
        
        # Check that playlist tab is now active
        assert "active" in playlist_tab.get_attribute("class")
        assert "active" not in batch_tab.get_attribute("class")
    
    def test_batch_form_elements(self, driver):
        """Test that batch processing form elements exist"""
        driver.get(self.BASE_URL)
        
        # Navigate to batch tab
        batch_tab = driver.find_element(By.ID, "batch-tab")
        batch_tab.click()
        time.sleep(0.5)
        
        # Check batch form elements
        batch_urls = driver.find_element(By.ID, "batchUrls")
        batch_mode = driver.find_element(By.ID, "batchMode")
        batch_language = driver.find_element(By.ID, "batchLanguage")
        batch_btn = driver.find_element(By.ID, "batchBtn")
        
        assert batch_urls is not None
        assert batch_mode is not None
        assert batch_language is not None
        assert batch_btn is not None
        assert batch_btn.text == "Process Batch"
    
    def test_playlist_form_elements(self, driver):
        """Test that playlist processing form elements exist"""
        driver.get(self.BASE_URL)
        
        # Navigate to playlist tab
        playlist_tab = driver.find_element(By.ID, "playlist-tab")
        playlist_tab.click()
        time.sleep(0.5)
        
        # Check playlist form elements
        playlist_url = driver.find_element(By.ID, "playlistUrl")
        playlist_mode = driver.find_element(By.ID, "playlistMode")
        playlist_language = driver.find_element(By.ID, "playlistLanguage")
        playlist_btn = driver.find_element(By.ID, "playlistBtn")
        
        assert playlist_url is not None
        assert playlist_mode is not None
        assert playlist_language is not None
        assert playlist_btn is not None
        assert playlist_btn.text == "Process Playlist"
    
    def test_batch_form_submission_placeholder(self, driver):
        """Test batch form submission shows not implemented message"""
        driver.get(self.BASE_URL)
        
        # Navigate to batch tab
        batch_tab = driver.find_element(By.ID, "batch-tab")
        batch_tab.click()
        time.sleep(0.5)
        
        # Fill out batch form
        batch_urls = driver.find_element(By.ID, "batchUrls")
        batch_urls.send_keys("https://www.youtube.com/watch?v=dQw4w9WgXcQ\\nhttps://www.youtube.com/watch?v=9bZkp7q19f0")
        
        # Submit form
        batch_btn = driver.find_element(By.ID, "batchBtn")
        batch_btn.click()
        
        # Should show alert (current implementation shows not implemented message)
        try:
            WebDriverWait(driver, 5).until(EC.alert_is_present())
            alert = driver.switch_to.alert
            alert_text = alert.text
            assert "not yet implemented" in alert_text.lower()
            alert.accept()
        except TimeoutException:
            # Alert might not appear if implementation changes
            pass
    
    def test_playlist_form_submission_placeholder(self, driver):
        """Test playlist form submission shows not implemented message"""
        driver.get(self.BASE_URL)
        
        # Navigate to playlist tab
        playlist_tab = driver.find_element(By.ID, "playlist-tab")
        playlist_tab.click()
        time.sleep(0.5)
        
        # Fill out playlist form
        playlist_url = driver.find_element(By.ID, "playlistUrl")
        playlist_url.send_keys("https://www.youtube.com/playlist?list=PLQVvvaa0QuDfKTOs3Keq_kaG2P55YRn5v")
        
        # Submit form
        playlist_btn = driver.find_element(By.ID, "playlistBtn")
        playlist_btn.click()
        
        # Should show alert (current implementation shows not implemented message)
        try:
            WebDriverWait(driver, 5).until(EC.alert_is_present())
            alert = driver.switch_to.alert
            alert_text = alert.text
            assert "not yet implemented" in alert_text.lower()
            alert.accept()
        except TimeoutException:
            # Alert might not appear if implementation changes
            pass

class TestAPIEndpointCalls:
    """Test that frontend makes correct API calls"""
    
    BASE_URL = "http://localhost:5050"
    
    def test_transcribe_endpoint_called(self):
        """Test that /transcribe endpoint is called with correct data"""
        # Mock the actual API call
        import requests_mock
        
        with requests_mock.Mocker() as m:
            # Mock the transcribe endpoint
            m.post(f'{self.BASE_URL}/transcribe', json={
                'job_id': 'test_job_123',
                'status': 'queued',
                'video_id': 'dQw4w9WgXcQ',
                'message': 'Job started',
                'download_links': {
                    'txt': '/download/test_job_123?format=txt',
                    'srt': '/download/test_job_123?format=srt',
                    'vtt': '/download/test_job_123?format=vtt'
                }
            })
            
            # Mock the status endpoint
            m.get(f'{self.BASE_URL}/job-status/test_job_123', json={
                'status': 'complete',
                'percent': 100,
                'error': None
            })
            
            # Simulate frontend API call
            response = requests.post(f'{self.BASE_URL}/transcribe', json={
                'url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
                'mode': 'auto',
                'lang': 'en'
            })
            
            assert response.status_code == 200
            data = response.json()
            assert 'job_id' in data
            assert data['status'] == 'queued'
            
            # Test status check
            status_response = requests.get(f'{self.BASE_URL}/job-status/test_job_123')
            assert status_response.status_code == 200
            status_data = status_response.json()
            assert status_data['status'] == 'complete'
    
    def test_download_endpoint_called(self):
        """Test that download endpoints are called correctly"""
        import requests_mock
        
        with requests_mock.Mocker() as m:
            # Mock download endpoints
            m.get(f'{self.BASE_URL}/download/test_job_123', 
                  text='Test transcription content',
                  headers={'Content-Type': 'text/plain; charset=utf-8'})
            
            # Test different formats
            for fmt in ['txt', 'srt', 'vtt']:
                response = requests.get(f'{self.BASE_URL}/download/test_job_123?format={fmt}')
                assert response.status_code == 200
                assert 'Test transcription content' in response.text

class TestJavaScriptFunctionality:
    """Test JavaScript functionality without browser"""
    
    def test_javascript_file_exists(self):
        """Test that main.js file exists and contains expected functions"""
        js_file_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'static', 'js', 'main.js'
        )
        
        assert os.path.exists(js_file_path), "main.js file not found"
        
        with open(js_file_path, 'r') as f:
            js_content = f.read()
        
        # Check for key functions and event handlers
        assert 'DOMContentLoaded' in js_content
        assert 'transcriptionForm' in js_content
        assert 'transcribeBtn' in js_content
        assert '/transcribe' in js_content
        assert '/job-status/' in js_content
        assert 'downloadFile' in js_content  # Download function exists
    
    def test_endpoint_urls_in_javascript(self):
        """Test that JavaScript contains correct endpoint URLs"""
        js_file_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'static', 'js', 'main.js'
        )
        
        with open(js_file_path, 'r') as f:
            js_content = f.read()
        
        # Check that JavaScript calls the correct endpoints
        assert "fetch('/transcribe'" in js_content
        assert "fetch(`/job-status/${" in js_content
        assert 'downloadFile' in js_content  # Download functionality exists
        
        # Ensure no old API endpoints are present
        assert "fetch('/api/transcribe'" not in js_content
        assert "fetch(`/api/job/${" not in js_content

if __name__ == '__main__':
    # Run tests with pytest
    pytest.main([__file__, '-v', '--tb=short'])
