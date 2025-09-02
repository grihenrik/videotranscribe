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
        
        // Submit to API
        fetch('/api/transcribe', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                url: youtubeUrl,
                mode: transcriptionMode,
                lang: language
            })
        })
        .then(response => {
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
            console.error('Error:', error);
            alert('Failed to start transcription: ' + error.message);
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
    
    function checkTranscriptionStatus(jobId) {
        console.log('Checking transcription status for job:', jobId);
        
        const checkInterval = setInterval(() => {
            fetch(`/api/download/${jobId}?format=txt`)
                .then(response => {
                    if (response.ok) {
                        // Transcription is ready, enable buttons
                        enableDownloadButtons();
                        clearInterval(checkInterval);
                        
                        // Update status
                        const statusBadge = document.getElementById('job-status');
                        if (statusBadge) {
                            statusBadge.textContent = 'Completed';
                            statusBadge.className = 'badge bg-success';
                        }
                        
                        console.log('Transcription completed, download buttons enabled');
                    }
                })
                .catch(error => {
                    console.log('Still processing...', error.message);
                });
        }, 3000); // Check every 3 seconds
        
        // Stop checking after 5 minutes
        setTimeout(() => {
            clearInterval(checkInterval);
            console.log('Stopped checking transcription status (timeout)');
        }, 300000);
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

console.log('JavaScript file loaded completely');