// YouTube Transcription Tool - Clean Implementation

console.log('JavaScript loading...');

document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM loaded, initializing...');
    
    // Find form elements
    const form = document.getElementById('transcriptionForm');
    const button = document.getElementById('transcribeBtn');
    
    console.log('Form element:', form);
    console.log('Button element:', button);
    
    if (!form || !button) {
        console.error('Required form elements not found!');
        return;
    }
    
    console.log('✅ Form elements found, setting up handlers...');
    
    // Prevent default form submission
    form.addEventListener('submit', function(e) {
        e.preventDefault();
        e.stopPropagation();
        console.log('Form submission intercepted');
        handleSubmission();
        return false;
    });
    
    // Handle button clicks
    button.addEventListener('click', function(e) {
        e.preventDefault();
        e.stopPropagation();
        console.log('Button click intercepted');
        handleSubmission();
        return false;
    });
    
    function handleSubmission() {
        console.log('Processing transcription request...');
        
        // Get form values
        const urlInput = document.getElementById('youtubeUrl');
        const modeSelect = document.getElementById('transcriptionMode');
        const langSelect = document.getElementById('language');
        
        const youtubeUrl = urlInput.value.trim();
        const transcriptionMode = modeSelect.value;
        const language = langSelect.value;
        
        console.log('Form data:', { youtubeUrl, transcriptionMode, language });
        
        // Validate
        if (!youtubeUrl) {
            alert('Please enter a YouTube URL');
            return;
        }
        
        if (!youtubeUrl.includes('youtube.com') && !youtubeUrl.includes('youtu.be')) {
            alert('Please enter a valid YouTube URL');
            return;
        }
        
        // Disable form
        button.disabled = true;
        button.textContent = 'Processing...';
        urlInput.disabled = true;
        modeSelect.disabled = true;
        langSelect.disabled = true;
        
        // Submit to API with timeout
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 30000); // 30 second timeout
        
        fetch('/api/transcribe', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                url: youtubeUrl,
                mode: transcriptionMode,
                lang: language
            }),
            signal: controller.signal
        })
        .then(response => {
            clearTimeout(timeoutId);
            console.log('Response status:', response.status);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            console.log('API Response:', data);
            
            if (data.job_id) {
                showSuccess(data);
            } else {
                throw new Error(data.error || 'Unknown error');
            }
        })
        .catch(error => {
            clearTimeout(timeoutId);
            console.error('Error:', error);
            
            let errorMessage = 'Failed to start transcription: ';
            if (error.name === 'AbortError') {
                errorMessage += 'Request timed out. The server may be busy or the video may not be accessible.';
            } else if (error.message.includes('403')) {
                errorMessage += 'YouTube blocked access to this video. Try a different video or try again later.';
            } else if (error.message.includes('404')) {
                errorMessage += 'Video not found. Please check the URL and try again.';
            } else {
                errorMessage += error.message;
            }
            
            alert(errorMessage);
        })
        .finally(() => {
            // Re-enable form
            button.disabled = false;
            button.textContent = 'Transcribe Video';
            urlInput.disabled = false;
            modeSelect.disabled = false;
            langSelect.disabled = false;
        });
    }
    
    function showSuccess(data) {
        console.log('Showing success with data:', data);
        
        // Show results section
        const resultsContainer = document.getElementById('results-container');
        if (resultsContainer) {
            resultsContainer.classList.remove('d-none');
        }
        
        // Update video info
        const videoIdElement = document.getElementById('video-id');
        if (videoIdElement) {
            videoIdElement.textContent = data.video_id || 'Processing...';
        }
        
        // Set up download buttons (initially disabled)
        setupDownloadButtons(data.download_links, data.job_id);
        
        // Show downloads section immediately but with disabled buttons
        const downloadSection = document.getElementById('download-section');
        if (downloadSection) {
            downloadSection.classList.remove('d-none');
        }
        
        // Start checking for completion
        checkTranscriptionStatus(data.job_id);
        
        alert(`✅ Transcription started successfully!\nJob ID: ${data.job_id}\nDownload buttons will be enabled when ready.`);
    }
    
    function setupDownloadButtons(downloadLinks, jobId) {
        const txtBtn = document.getElementById('download-txt');
        const srtBtn = document.getElementById('download-srt');
        const vttBtn = document.getElementById('download-vtt');
        
        // Initially disable all buttons
        [txtBtn, srtBtn, vttBtn].forEach(btn => {
            if (btn) {
                btn.classList.add('disabled');
                btn.style.pointerEvents = 'none';
                btn.style.opacity = '0.5';
            }
        });
        
        // Set up click handlers for direct download
        if (txtBtn && downloadLinks?.txt) {
            txtBtn.addEventListener('click', (e) => {
                e.preventDefault();
                downloadFile(downloadLinks.txt, `transcription-${jobId}.txt`);
            });
        }
        
        if (srtBtn && downloadLinks?.srt) {
            srtBtn.addEventListener('click', (e) => {
                e.preventDefault();
                downloadFile(downloadLinks.srt, `transcription-${jobId}.srt`);
            });
        }
        
        if (vttBtn && downloadLinks?.vtt) {
            vttBtn.addEventListener('click', (e) => {
                e.preventDefault();
                downloadFile(downloadLinks.vtt, `transcription-${jobId}.vtt`);
            });
        }
    }
    
    function downloadFile(url, filename) {
        console.log('Downloading file:', filename);
        
        fetch(url)
            .then(response => {
                if (!response.ok) {
                    throw new Error('Download failed');
                }
                return response.blob();
            })
            .then(blob => {
                const downloadUrl = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = downloadUrl;
                a.download = filename;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                window.URL.revokeObjectURL(downloadUrl);
                console.log('File downloaded successfully');
            })
            .catch(error => {
                console.error('Download error:', error);
                alert('Download failed. The transcription may not be ready yet.');
            });
    }
    
    // Global variable to track active polling
    let activePollingInterval = null;
    let isPolling = false;
    
    function checkTranscriptionStatus(jobId) {
        console.log('Checking transcription status for job:', jobId);
        
        // Clear any existing polling to prevent multiple intervals
        if (activePollingInterval) {
            clearInterval(activePollingInterval);
            console.log('Cleared existing polling interval');
        }
        
        // Prevent multiple concurrent polling
        if (isPolling) {
            console.log('Already polling, skipping new poll request');
            return;
        }
        
        isPolling = true;
        let pollCount = 0;
        const maxPolls = 100; // Maximum 100 polls (5 minutes at 3-second intervals)
        
        activePollingInterval = setInterval(() => {
            pollCount++;
            
            // Safety check: stop after max polls
            if (pollCount > maxPolls) {
                clearInterval(activePollingInterval);
                activePollingInterval = null;
                isPolling = false;
                console.log('Stopped polling: Maximum poll count reached');
                
                const statusBadge = document.getElementById('job-status');
                if (statusBadge && !statusBadge.textContent.includes('Completed')) {
                    statusBadge.textContent = 'Timeout';
                    statusBadge.className = 'badge bg-warning';
                }
                return;
            }
            
            fetch(`/api/job/${jobId}/status`)
                .then(response => response.json())
                .then(status => {
                    console.log('Job status:', status);
                    
                    const statusBadge = document.getElementById('job-status');
                    const progressBar = document.getElementById('progress-bar');
                    
                    if (status.status === 'complete') {
                        // Transcription completed successfully
                        clearInterval(activePollingInterval);
                        activePollingInterval = null;
                        isPolling = false;
                        
                        enableDownloadButtons();
                        
                        if (statusBadge) {
                            statusBadge.textContent = 'Completed';
                            statusBadge.className = 'badge bg-success';
                        }
                        if (progressBar) {
                            progressBar.style.width = '100%';
                            progressBar.textContent = '100%';
                        }
                        
                        console.log('✅ Transcription completed, polling stopped');
                        
                    } else if (status.status === 'error') {
                        // Transcription failed - STOP POLLING IMMEDIATELY
                        clearInterval(activePollingInterval);
                        activePollingInterval = null;
                        isPolling = false;
                        
                        if (statusBadge) {
                            statusBadge.textContent = 'Failed';
                            statusBadge.className = 'badge bg-danger';
                        }
                        
                        const errorMsg = status.error || 'Unknown error';
                        console.log('❌ Transcription failed, polling stopped:', errorMsg);
                        
                        // Show error message only once
                        alert(`Transcription failed: ${errorMsg}\n\nThis may be due to YouTube access restrictions. Try a different video.`);
                        
                    } else {
                        // Still processing - update progress
                        if (statusBadge) {
                            statusBadge.textContent = status.status || 'Processing';
                            statusBadge.className = 'badge bg-primary';
                        }
                        if (progressBar && status.percent) {
                            progressBar.style.width = status.percent + '%';
                            progressBar.textContent = status.percent + '%';
                        }
                        
                        console.log(`⏳ Still processing: ${status.status} (${status.percent || 0}%)`);
                    }
                })
                .catch(error => {
                    console.log('⚠️ Error checking status:', error.message);
                    
                    // Stop polling on fetch errors too
                    clearInterval(activePollingInterval);
                    activePollingInterval = null;
                    isPolling = false;
                    console.log('Polling stopped due to fetch error');
                });
        }, 3000); // Check every 3 seconds
    }
    
    function enableDownloadButtons() {
        const txtBtn = document.getElementById('download-txt');
        const srtBtn = document.getElementById('download-srt');
        const vttBtn = document.getElementById('download-vtt');
        
        [txtBtn, srtBtn, vttBtn].forEach(btn => {
            if (btn) {
                btn.classList.remove('disabled');
                btn.style.pointerEvents = 'auto';
                btn.style.opacity = '1';
            }
        });
    }
});

console.log('JavaScript file loaded completely (v2025090202)');