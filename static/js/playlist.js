// Initialize Feather icons
document.addEventListener('DOMContentLoaded', () => {
    feather.replace();
    initPlaylistForm();
});

function initPlaylistForm() {
    const form = document.getElementById('playlist-form');
    const submitButton = document.getElementById('submit-button');
    const submitSpinner = document.getElementById('submit-spinner');
    const loadingContainer = document.getElementById('loading-container');
    const batchResults = document.getElementById('batch-results');
    const batchProgressBar = document.getElementById('batch-progress-bar');
    const batchStatusBadge = document.getElementById('batch-status');
    const playlistTitleElement = document.getElementById('playlist-title');
    const totalVideosElement = document.getElementById('total-videos');
    const completedVideosElement = document.getElementById('completed-videos');
    const jobItems = document.getElementById('job-items');
    
    // Handle form submission
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        // Get form values
        const playlistUrl = document.getElementById('playlist-url').value;
        const transcriptionMode = document.getElementById('transcription-mode').value;
        const language = document.getElementById('language').value;
        
        if (!playlistUrl || !playlistUrl.includes('playlist') && !playlistUrl.includes('list=')) {
            alert('Please enter a valid YouTube playlist URL');
            return;
        }
        
        // Disable form inputs and button during processing
        submitButton.disabled = true;
        document.getElementById('playlist-url').disabled = true;
        document.getElementById('transcription-mode').disabled = true;
        document.getElementById('language').disabled = true;
        submitButton.querySelector('span:first-child').textContent = 'Loading Playlist...';
        submitSpinner.classList.remove('d-none');
        
        // Show loading container
        loadingContainer.classList.remove('d-none');
        batchResults.classList.add('d-none');
        
        try {
            // First, fetch videos from the playlist
            const fetchResponse = await fetch('/api/playlist/videos', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    playlist_url: playlistUrl
                })
            });
            
            if (!fetchResponse.ok) {
                throw new Error('Failed to fetch playlist videos');
            }
            
            const playlistData = await fetchResponse.json();
            
            if (!playlistData.videos || playlistData.videos.length === 0) {
                throw new Error('No videos found in the playlist or playlist is private');
            }
            
            // Hide loading container
            loadingContainer.classList.add('d-none');
            
            // Now submit the batch processing request with the playlist videos
            const batchResponse = await fetch('/api/batch', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    urls: playlistData.videos,
                    mode: transcriptionMode,
                    lang: language,
                    playlist_title: playlistData.title || 'YouTube Playlist'
                })
            });
            
            if (!batchResponse.ok) {
                throw new Error('Failed to start batch transcription');
            }
            
            const batchData = await batchResponse.json();
            
            // Show results container
            batchResults.classList.remove('d-none');
            playlistTitleElement.textContent = playlistData.title || 'YouTube Playlist';
            totalVideosElement.textContent = batchData.total;
            
            // Create job items
            jobItems.innerHTML = '';
            batchData.jobs.forEach((jobId, index) => {
                const jobItem = document.createElement('div');
                jobItem.className = 'list-group-item d-flex justify-content-between align-items-center';
                jobItem.id = `job-${jobId}`;
                
                const jobTitle = document.createElement('div');
                jobTitle.className = 'job-title';
                
                // Use actual video title if available
                if (playlistData.video_details && playlistData.video_details[index]) {
                    jobTitle.textContent = `${index + 1}. ${playlistData.video_details[index].title}`;
                } else {
                    jobTitle.textContent = `Video ${index + 1}: ${getVideoTitle(playlistData.videos[index])}`;
                }
                
                const jobStatus = document.createElement('span');
                jobStatus.className = 'badge bg-secondary';
                jobStatus.textContent = 'Queued';
                
                jobItem.appendChild(jobTitle);
                jobItem.appendChild(jobStatus);
                jobItems.appendChild(jobItem);
            });
            
            // Update button text
            submitButton.querySelector('span:first-child').textContent = 'Processing Playlist...';
            
            // Start polling for batch status updates
            pollBatchStatus(batchData.batch_id);
            
        } catch (error) {
            console.error('Error:', error);
            alert('Failed to process playlist: ' + error.message);
            
            // Hide loading container
            loadingContainer.classList.add('d-none');
            
            // Re-enable form
            submitButton.disabled = false;
            document.getElementById('playlist-url').disabled = false;
            document.getElementById('transcription-mode').disabled = false;
            document.getElementById('language').disabled = false;
            submitButton.querySelector('span:first-child').textContent = 'Process Playlist';
            submitSpinner.classList.add('d-none');
        }
    });
    
    // Get a simplified video title from URL
    function getVideoTitle(url) {
        try {
            const videoId = url.includes('v=') 
                ? url.split('v=')[1].split('&')[0] 
                : url.includes('youtu.be/') 
                    ? url.split('youtu.be/')[1].split('?')[0]
                    : 'Unknown';
            return `Video ID: ${videoId}`;
        } catch (e) {
            return 'YouTube Video';
        }
    }
    
    // Poll for batch status updates
    async function pollBatchStatus(batchId) {
        let interval = setInterval(async () => {
            try {
                const response = await fetch(`/api/batch/${batchId}/status`);
                
                if (!response.ok) {
                    throw new Error('Failed to get batch status');
                }
                
                const data = await response.json();
                
                // Update progress bar
                batchProgressBar.style.width = `${data.percent}%`;
                batchProgressBar.textContent = `${data.percent}%`;
                batchProgressBar.setAttribute('aria-valuenow', data.percent);
                
                // Update completed count
                completedVideosElement.textContent = data.completed;
                
                // Update job statuses
                updateJobStatuses(data.jobs);
                
                // Update status badge
                if (data.status === 'complete') {
                    batchStatusBadge.textContent = 'Complete';
                    batchStatusBadge.className = 'badge bg-success';
                    
                    // Add download all as ZIP button if it doesn't exist
                    if (!document.getElementById('download-playlist-zip')) {
                        const downloadContainer = document.createElement('div');
                        downloadContainer.className = 'text-center mt-3 mb-2';
                        
                        const downloadBtn = document.createElement('a');
                        downloadBtn.id = 'download-playlist-zip';
                        downloadBtn.href = `/api/batch/${batchId}/download`;
                        downloadBtn.className = 'btn btn-primary';
                        downloadBtn.innerHTML = '<i data-feather="download"></i> Download All Transcriptions as ZIP';
                        
                        downloadContainer.appendChild(downloadBtn);
                        batchResults.querySelector('.card-body').appendChild(downloadContainer);
                        
                        // Initialize the Feather icon
                        feather.replace();
                    }
                    
                    // Reset form
                    submitButton.disabled = false;
                    document.getElementById('playlist-url').disabled = false;
                    document.getElementById('transcription-mode').disabled = false;
                    document.getElementById('language').disabled = false;
                    submitButton.querySelector('span:first-child').textContent = 'Process Another Playlist';
                    submitSpinner.classList.add('d-none');
                    
                    // Stop polling
                    clearInterval(interval);
                } else if (data.completed + data.failed === data.total) {
                    // All jobs are either completed or failed
                    batchStatusBadge.textContent = 'Complete (with errors)';
                    batchStatusBadge.className = 'badge bg-warning';
                    
                    // Reset form
                    submitButton.disabled = false;
                    document.getElementById('playlist-url').disabled = false;
                    document.getElementById('transcription-mode').disabled = false;
                    document.getElementById('language').disabled = false;
                    submitButton.querySelector('span:first-child').textContent = 'Process Another Playlist';
                    submitSpinner.classList.add('d-none');
                    
                    // Stop polling
                    clearInterval(interval);
                }
                
            } catch (error) {
                console.error('Error polling batch status:', error);
                
                // Stop polling on error
                clearInterval(interval);
                
                // Reset form
                submitButton.disabled = false;
                document.getElementById('playlist-url').disabled = false;
                document.getElementById('transcription-mode').disabled = false;
                document.getElementById('language').disabled = false;
                submitButton.querySelector('span:first-child').textContent = 'Process Playlist';
                submitSpinner.classList.add('d-none');
            }
        }, 3000); // Poll every 3 seconds
    }
    
    // Update job statuses
    async function updateJobStatuses(jobIds) {
        for (const jobId of jobIds) {
            try {
                const response = await fetch(`/api/job/${jobId}/status`);
                
                if (!response.ok) {
                    continue;
                }
                
                const data = await response.json();
                const jobElement = document.getElementById(`job-${jobId}`);
                
                if (!jobElement) {
                    continue;
                }
                
                const jobStatus = jobElement.querySelector('.badge');
                let statusColor = 'bg-secondary';
                
                // Update job status badge
                switch (data.status) {
                    case 'queued':
                        jobStatus.textContent = 'Queued';
                        break;
                    case 'downloading':
                        jobStatus.textContent = 'Downloading';
                        statusColor = 'bg-info';
                        break;
                    case 'processing':
                        jobStatus.textContent = 'Processing';
                        statusColor = 'bg-info';
                        break;
                    case 'transcribing':
                        jobStatus.textContent = 'Transcribing';
                        statusColor = 'bg-primary';
                        break;
                    case 'finalizing':
                        jobStatus.textContent = 'Finalizing';
                        statusColor = 'bg-info';
                        break;
                    case 'complete':
                        jobStatus.textContent = 'Complete';
                        statusColor = 'bg-success';
                        
                        // Add download links
                        if (!jobElement.querySelector('.download-links')) {
                            const downloadLinks = document.createElement('div');
                            downloadLinks.className = 'download-links mt-2';
                            
                            const txtLink = document.createElement('a');
                            txtLink.href = `/api/download/${jobId}?format=txt`;
                            txtLink.className = 'btn btn-sm btn-outline-primary me-1';
                            txtLink.textContent = 'TXT';
                            
                            const srtLink = document.createElement('a');
                            srtLink.href = `/api/download/${jobId}?format=srt`;
                            srtLink.className = 'btn btn-sm btn-outline-primary me-1';
                            srtLink.textContent = 'SRT';
                            
                            const vttLink = document.createElement('a');
                            vttLink.href = `/api/download/${jobId}?format=vtt`;
                            vttLink.className = 'btn btn-sm btn-outline-primary';
                            vttLink.textContent = 'VTT';
                            
                            downloadLinks.appendChild(txtLink);
                            downloadLinks.appendChild(srtLink);
                            downloadLinks.appendChild(vttLink);
                            
                            jobElement.appendChild(downloadLinks);
                        }
                        break;
                    case 'error':
                        jobStatus.textContent = 'Error';
                        statusColor = 'bg-danger';
                        
                        // Show error message
                        if (data.error && !jobElement.querySelector('.error-message')) {
                            const errorMessage = document.createElement('div');
                            errorMessage.className = 'error-message text-danger mt-2 small';
                            errorMessage.textContent = data.error;
                            jobElement.appendChild(errorMessage);
                        }
                        break;
                }
                
                jobStatus.className = `badge ${statusColor}`;
                
            } catch (error) {
                console.error(`Error updating job ${jobId} status:`, error);
            }
        }
    }
}