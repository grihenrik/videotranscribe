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
    
    // Batch form handlers
    const batchForm = document.getElementById('batchForm');
    const batchButton = document.getElementById('batchBtn');
    
    if (batchForm && batchButton) {
        batchForm.addEventListener('submit', function(e) {
            e.preventDefault();
            e.stopPropagation();
            console.log('Batch form submission intercepted');
            handleBatchSubmission();
            return false;
        });
        
        batchButton.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            console.log('Batch button click intercepted');
            handleBatchSubmission();
            return false;
        });
    }
    
    // Playlist form handlers
    const playlistForm = document.getElementById('playlistForm');
    const playlistButton = document.getElementById('playlistBtn');
    
    if (playlistForm && playlistButton) {
        playlistForm.addEventListener('submit', function(e) {
            e.preventDefault();
            e.stopPropagation();
            console.log('Playlist form submission intercepted');
            handlePlaylistSubmission();
            return false;
        });
        
        playlistButton.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            console.log('Playlist button click intercepted');
            handlePlaylistSubmission();
            return false;
        });
    }
    
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
        
        fetch('/transcribe', {
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
        
        // Update info based on type (playlist vs single video)
        const videoIdElement = document.getElementById('video-id');
        if (videoIdElement) {
            if (data.is_playlist) {
                videoIdElement.textContent = 'Playlist Processing...';
            } else {
                videoIdElement.textContent = data.video_id || 'Processing...';
            }
        }
        
        // Set up download buttons (initially disabled)
        setupDownloadButtons(data.download_links, data.job_id, data.is_playlist);
        
        // Show downloads section immediately but with disabled buttons
        const downloadSection = document.getElementById('download-section');
        if (downloadSection) {
            downloadSection.classList.remove('d-none');
        }
        
        // Start checking for completion
        checkTranscriptionStatus(data.job_id);
        
        const successMessage = data.is_playlist 
            ? `✅ Playlist transcription started successfully!\nJob ID: ${data.job_id}\nDownload button will be enabled when all videos are processed.`
            : `✅ Transcription started successfully!\nJob ID: ${data.job_id}\nDownload buttons will be enabled when ready.`;
        
        alert(successMessage);
    }
    
    function setupDownloadButtons(downloadLinks, jobId, isPlaylist) {
        const txtBtn = document.getElementById('download-txt');
        const srtBtn = document.getElementById('download-srt');
        const vttBtn = document.getElementById('download-vtt');
        
        if (isPlaylist) {
            // For playlists, hide individual format buttons and show/create ZIP download button
            [txtBtn, srtBtn, vttBtn].forEach(btn => {
                if (btn) {
                    btn.style.display = 'none';
                }
            });
            
            // Create or update ZIP download button
            let zipBtn = document.getElementById('download-zip');
            if (!zipBtn) {
                zipBtn = document.createElement('button');
                zipBtn.id = 'download-zip';
                zipBtn.className = 'btn btn-success disabled';
                zipBtn.innerHTML = '<i class="fas fa-download"></i> Download All (ZIP)';
                zipBtn.style.pointerEvents = 'none';
                zipBtn.style.opacity = '0.5';
                
                // Add to download section
                const downloadSection = document.getElementById('download-section');
                if (downloadSection) {
                    downloadSection.appendChild(zipBtn);
                }
            }
            
            // Set up ZIP download handler
            if (downloadLinks?.zip) {
                zipBtn.addEventListener('click', (e) => {
                    e.preventDefault();
                    downloadFile(downloadLinks.zip, `playlist_transcriptions_${jobId}.zip`);
                });
            }
        } else {
            // For single videos, show individual format buttons and hide ZIP button
            [txtBtn, srtBtn, vttBtn].forEach(btn => {
                if (btn) {
                    btn.style.display = 'inline-block';
                    btn.classList.add('disabled');
                    btn.style.pointerEvents = 'none';
                    btn.style.opacity = '0.5';
                }
            });
            
            // Hide ZIP button if it exists
            const zipBtn = document.getElementById('download-zip');
            if (zipBtn) {
                zipBtn.style.display = 'none';
            }
            
            // Set up click handlers for individual format downloads
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
            
            fetch(`/job-status/${jobId}`)
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
    
    function handleBatchSubmission() {
        alert('Batch processing is not yet implemented in the API. This feature is coming soon!');
        console.log('Batch processing placeholder');
    }
    
    function handlePlaylistSubmission() {
        alert('Playlist processing is not yet implemented in the API. This feature is coming soon!');
        console.log('Playlist processing placeholder');
    }
    
    function enableDownloadButtons() {
        const txtBtn = document.getElementById('download-txt');
        const srtBtn = document.getElementById('download-srt');
        const vttBtn = document.getElementById('download-vtt');
        const zipBtn = document.getElementById('download-zip');
        
        // Enable all visible buttons
        [txtBtn, srtBtn, vttBtn, zipBtn].forEach(btn => {
            if (btn && btn.style.display !== 'none') {
                btn.classList.remove('disabled');
                btn.style.pointerEvents = 'auto';
                btn.style.opacity = '1';
            }
        });
    }
});

console.log('JavaScript file loaded completely (v2025090203)');