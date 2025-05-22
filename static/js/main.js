document.addEventListener('DOMContentLoaded', function() {
    // DOM elements
    const transcriptionForm = document.getElementById('transcription-form');
    const progressSection = document.getElementById('progress-section');
    const resultsSection = document.getElementById('results-section');
    const errorSection = document.getElementById('error-section');
    const statusMessage = document.getElementById('status-message');
    const progressBar = document.getElementById('progress-bar');
    const downloadButtons = document.getElementById('download-buttons');
    const transcriptionPreview = document.getElementById('transcription-preview');
    const errorMessage = document.getElementById('error-message');
    const restartButton = document.getElementById('restart-button');
    
    // WebSocket connection
    let socket = null;
    // Current job ID
    let currentJobId = null;
    // Download interval timer
    let downloadTimer = null;
    
    // Form submission
    transcriptionForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        // Get form values
        const youtubeUrl = document.getElementById('youtube-url').value;
        const transcriptionMode = document.getElementById('transcription-mode').value;
        const language = document.getElementById('language').value;
        
        // Hide any previous results or errors
        progressSection.classList.remove('d-none');
        resultsSection.classList.add('d-none');
        errorSection.classList.add('d-none');
        
        // Reset progress
        updateProgress('Submitting request...', 0);
        
        try {
            // Submit transcription request
            const response = await fetch('/api/transcribe', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    url: youtubeUrl,
                    mode: transcriptionMode,
                    lang: language
                })
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Failed to start transcription');
            }
            
            const data = await response.json();
            currentJobId = data.job_id;
            
            // Check if transcription is already complete (cached)
            if (data.status === 'complete') {
                updateProgress('Transcription complete (from cache)', 100);
                showResults(data.download_links);
                return;
            }
            
            // Connect to WebSocket for progress updates
            connectWebSocket(data.job_id);
            
            // Start checking for completion
            startDownloadCheck(data.job_id);
            
        } catch (error) {
            showError(error.message);
        }
    });
    
    // Connect to WebSocket for progress updates
    function connectWebSocket(jobId) {
        // Close existing socket if any
        if (socket) {
            socket.close();
        }
        
        // Create new WebSocket connection
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/api/ws/progress/${jobId}`;
        socket = new WebSocket(wsUrl);
        
        // Connection opened
        socket.addEventListener('open', function(event) {
            console.log('WebSocket connection established');
        });
        
        // Listen for messages
        socket.addEventListener('message', function(event) {
            try {
                const data = JSON.parse(event.data);
                
                if (data.error) {
                    showError(data.error);
                    return;
                }
                
                // Update progress
                let statusText = 'Processing...';
                
                switch (data.status) {
                    case 'downloading':
                        statusText = 'Downloading video...';
                        break;
                    case 'transcribing':
                        statusText = 'Transcribing audio...';
                        break;
                    case 'complete':
                        statusText = 'Transcription complete!';
                        break;
                    case 'error':
                        showError(data.error || 'An error occurred during transcription');
                        return;
                }
                
                updateProgress(statusText, data.percent);
                
                // If complete, check download
                if (data.status === 'complete') {
                    checkDownload(jobId);
                }
                
            } catch (error) {
                console.error('Error parsing WebSocket message:', error);
            }
        });
        
        // Connection closed
        socket.addEventListener('close', function(event) {
            console.log('WebSocket connection closed');
        });
        
        // Connection error
        socket.addEventListener('error', function(event) {
            console.error('WebSocket error:', event);
            showError('WebSocket connection error. Please try again.');
        });
    }
    
    // Start checking for download availability
    function startDownloadCheck(jobId) {
        if (downloadTimer) {
            clearInterval(downloadTimer);
        }
        
        downloadTimer = setInterval(() => {
            checkDownload(jobId);
        }, 5000); // Check every 5 seconds
    }
    
    // Check if download is available
    async function checkDownload(jobId) {
        try {
            const response = await fetch(`/api/job/${jobId}/status`);
            
            if (!response.ok) {
                if (response.status === 404) {
                    showError('Transcription job not found');
                } else {
                    const errorData = await response.json();
                    throw new Error(errorData.detail || 'Failed to check job status');
                }
                return;
            }
            
            const data = await response.json();
            
            if (data.status === 'complete') {
                // Stop checking
                if (downloadTimer) {
                    clearInterval(downloadTimer);
                    downloadTimer = null;
                }
                
                // Check download availability
                const downloadResponse = await fetch(`/api/download/${jobId}?format=txt`);
                
                if (downloadResponse.ok) {
                    // Show download links
                    const downloadLinks = {
                        txt: `/api/download/${jobId}?format=txt`,
                        srt: `/api/download/${jobId}?format=srt`,
                        vtt: `/api/download/${jobId}?format=vtt`
                    };
                    
                    showResults(downloadLinks);
                    
                    // Show preview
                    const text = await downloadResponse.text();
                    transcriptionPreview.textContent = text;
                } else {
                    // Handle error
                    const errorData = await downloadResponse.json();
                    throw new Error(errorData.detail || 'Failed to download transcription');
                }
            } else if (data.status === 'error') {
                // Stop checking
                if (downloadTimer) {
                    clearInterval(downloadTimer);
                    downloadTimer = null;
                }
                
                showError(data.error || 'An error occurred during transcription');
            }
            
        } catch (error) {
            console.error('Error checking download:', error);
        }
    }
    
    // Update progress display
    function updateProgress(message, percent) {
        statusMessage.textContent = message;
        progressBar.style.width = `${percent}%`;
        progressBar.setAttribute('aria-valuenow', percent);
        progressBar.textContent = `${percent}%`;
    }
    
    // Show results
    function showResults(downloadLinks) {
        // Update UI
        progressSection.classList.add('d-none');
        resultsSection.classList.remove('d-none');
        
        // Clear download buttons
        downloadButtons.innerHTML = '';
        
        // Add download buttons
        if (downloadLinks.txt) {
            addDownloadButton('Text (.txt)', downloadLinks.txt, 'text-file');
        }
        if (downloadLinks.srt) {
            addDownloadButton('Subtitles (.srt)', downloadLinks.srt, 'file-text');
        }
        if (downloadLinks.vtt) {
            addDownloadButton('WebVTT (.vtt)', downloadLinks.vtt, 'file-text');
        }
        
        // Close WebSocket if open
        if (socket && socket.readyState === WebSocket.OPEN) {
            socket.close();
        }
    }
    
    // Add download button
    function addDownloadButton(label, url, icon) {
        const button = document.createElement('a');
        button.href = url;
        button.className = 'btn btn-outline-primary me-2 mb-2';
        button.setAttribute('download', '');
        button.innerHTML = `
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather feather-download me-1"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>
            ${label}
        `;
        downloadButtons.appendChild(button);
    }
    
    // Show error
    function showError(message) {
        // Update UI
        progressSection.classList.add('d-none');
        resultsSection.classList.add('d-none');
        errorSection.classList.remove('d-none');
        
        // Set error message
        errorMessage.textContent = message;
        
        // Close WebSocket if open
        if (socket && socket.readyState === WebSocket.OPEN) {
            socket.close();
        }
        
        // Stop download check
        if (downloadTimer) {
            clearInterval(downloadTimer);
            downloadTimer = null;
        }
    }
    
    // Restart button
    restartButton.addEventListener('click', function() {
        // Reset form
        transcriptionForm.reset();
        
        // Hide sections
        progressSection.classList.add('d-none');
        resultsSection.classList.add('d-none');
        errorSection.classList.add('d-none');
        
        // Reset progress
        updateProgress('Starting transcription...', 0);
        
        // Close WebSocket if open
        if (socket && socket.readyState === WebSocket.OPEN) {
            socket.close();
        }
        
        // Stop download check
        if (downloadTimer) {
            clearInterval(downloadTimer);
            downloadTimer = null;
        }
    });
});
