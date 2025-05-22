// Initialize Feather icons
document.addEventListener('DOMContentLoaded', () => {
    feather.replace();
    initBatchForm();
});

function initBatchForm() {
    const form = document.getElementById('batch-form');
    const submitButton = document.getElementById('submit-button');
    const submitSpinner = document.getElementById('submit-spinner');
    const batchResults = document.getElementById('batch-results');
    const batchProgressBar = document.getElementById('batch-progress-bar');
    const batchStatusBadge = document.getElementById('batch-status');
    const batchIdElement = document.getElementById('batch-id');
    const totalVideosElement = document.getElementById('total-videos');
    const completedVideosElement = document.getElementById('completed-videos');
    const jobItems = document.getElementById('job-items');
    
    // Handle form submission
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        // Get form values
        const youtubeUrlsText = document.getElementById('youtube-urls').value;
        const transcriptionMode = document.getElementById('transcription-mode').value;
        const language = document.getElementById('language').value;
        
        // Parse URLs
        const urls = youtubeUrlsText.split('\n')
            .map(url => url.trim())
            .filter(url => url.length > 0 && (url.includes('youtube.com') || url.includes('youtu.be')));
        
        if (urls.length === 0) {
            alert('Please enter at least one valid YouTube URL');
            return;
        }
        
        // Disable form inputs and button during processing
        submitButton.disabled = true;
        document.getElementById('youtube-urls').disabled = true;
        document.getElementById('transcription-mode').disabled = true;
        document.getElementById('language').disabled = true;
        submitButton.querySelector('span:first-child').textContent = 'Processing...';
        submitSpinner.classList.remove('d-none');
        
        try {
            // Submit batch transcription request
            const response = await fetch('/api/batch', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    urls: urls,
                    mode: transcriptionMode,
                    lang: language
                })
            });
            
            if (!response.ok) {
                throw new Error('Failed to start batch transcription');
            }
            
            const data = await response.json();
            
            // Show results container
            batchResults.classList.remove('d-none');
            batchIdElement.textContent = data.batch_id;
            totalVideosElement.textContent = data.total;
            
            // Create job items
            jobItems.innerHTML = '';
            data.jobs.forEach(job => {
                // Check if job is an object with job_id and video_title (new format)
                // or just a string job ID (old format for backward compatibility)
                const jobId = typeof job === 'object' ? job.job_id : job;
                const videoTitle = typeof job === 'object' && job.video_title ? job.video_title : `Video ${jobId}`;
                
                const jobItem = document.createElement('div');
                jobItem.className = 'list-group-item d-flex justify-content-between align-items-center';
                jobItem.id = `job-${jobId}`;
                
                const jobTitle = document.createElement('div');
                jobTitle.className = 'job-title';
                jobTitle.textContent = videoTitle; // Use video title instead of job ID
                
                const jobStatus = document.createElement('span');
                jobStatus.className = 'badge bg-secondary';
                jobStatus.textContent = 'Queued';
                
                jobItem.appendChild(jobTitle);
                jobItem.appendChild(jobStatus);
                jobItems.appendChild(jobItem);
            });
            
            // Start polling for batch status updates
            pollBatchStatus(data.batch_id);
            
        } catch (error) {
            console.error('Error:', error);
            alert('Failed to start batch transcription: ' + error.message);
            
            // Re-enable form
            submitButton.disabled = false;
            document.getElementById('youtube-urls').disabled = false;
            document.getElementById('transcription-mode').disabled = false;
            document.getElementById('language').disabled = false;
            submitButton.querySelector('span:first-child').textContent = 'Process Batch';
            submitSpinner.classList.add('d-none');
        }
    });
    
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
                    
                    // Reset form
                    submitButton.disabled = false;
                    document.getElementById('youtube-urls').disabled = false;
                    document.getElementById('transcription-mode').disabled = false;
                    document.getElementById('language').disabled = false;
                    submitButton.querySelector('span:first-child').textContent = 'Process Another Batch';
                    submitSpinner.classList.add('d-none');
                    
                    // Stop polling
                    clearInterval(interval);
                } else if (data.completed + data.failed === data.total) {
                    // All jobs are either completed or failed
                    batchStatusBadge.textContent = 'Complete (with errors)';
                    batchStatusBadge.className = 'badge bg-warning';
                    
                    // Reset form
                    submitButton.disabled = false;
                    document.getElementById('youtube-urls').disabled = false;
                    document.getElementById('transcription-mode').disabled = false;
                    document.getElementById('language').disabled = false;
                    submitButton.querySelector('span:first-child').textContent = 'Process Another Batch';
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
                document.getElementById('youtube-urls').disabled = false;
                document.getElementById('transcription-mode').disabled = false;
                document.getElementById('language').disabled = false;
                submitButton.querySelector('span:first-child').textContent = 'Process Batch';
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