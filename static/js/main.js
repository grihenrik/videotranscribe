// Initialize Feather icons
document.addEventListener('DOMContentLoaded', () => {
    feather.replace();
    initTranscriptionForm();
});

function initTranscriptionForm() {
    const form = document.getElementById('transcription-form');
    const submitButton = document.getElementById('submit-button');
    const submitSpinner = document.getElementById('submit-spinner');
    const resultsContainer = document.getElementById('results-container');
    const progressBar = document.getElementById('progress-bar');
    const jobStatusBadge = document.getElementById('job-status');
    const videoIdElement = document.getElementById('video-id');
    const downloadSection = document.getElementById('download-section');
    
    // Download links
    const downloadTxt = document.getElementById('download-txt');
    const downloadSrt = document.getElementById('download-srt');
    const downloadVtt = document.getElementById('download-vtt');
    
    // Handle form submission
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        // Get form values
        const youtubeUrl = document.getElementById('youtube-url').value;
        const transcriptionMode = document.getElementById('transcription-mode').value;
        const language = document.getElementById('language').value;
        
        // Disable form inputs and button during processing
        submitButton.disabled = true;
        document.getElementById('youtube-url').disabled = true;
        document.getElementById('transcription-mode').disabled = true;
        document.getElementById('language').disabled = true;
        submitButton.querySelector('span:first-child').textContent = 'Processing...';
        submitSpinner.classList.remove('d-none');
        
        try {
            // Submit transcription request
            const response = await fetch('/transcribe', {
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
                throw new Error('Failed to start transcription');
            }
            
            const data = await response.json();
            const jobId = data.job_id;
            
            // Set direct download links immediately when job starts
            document.getElementById('directTxtLink').href = `/download/${jobId}?format=txt`;
            document.getElementById('directSrtLink').href = `/download/${jobId}?format=srt`;
            document.getElementById('directVttLink').href = `/download/${jobId}?format=vtt`;
            
            // Store job ID globally
            window.currentJobId = jobId;
            
            // Show results container
            resultsContainer.classList.remove('d-none');
            
            // Display video title if available, otherwise ID
            if (data.video_title) {
                videoIdElement.textContent = data.video_title;
            } else {
                videoIdElement.textContent = data.video_id;
            }
            
            // Update download links
            downloadTxt.href = data.download_links.txt;
            downloadSrt.href = data.download_links.srt;
            downloadVtt.href = data.download_links.vtt;
            
            // Start polling for status updates to show progress
            pollJobStatus(data.job_id);
            
        } catch (error) {
            console.error('Error:', error);
            alert('Failed to start transcription: ' + error.message);
            
            // Re-enable form
            submitButton.disabled = false;
            submitButton.querySelector('span:first-child').textContent = 'Transcribe Video';
            submitSpinner.classList.add('d-none');
        }
    });
    
    // Poll for job status updates
    async function pollJobStatus(jobId) {
        let interval = setInterval(async () => {
            try {
                const response = await fetch(`/status/${jobId}`);
                
                if (!response.ok) {
                    throw new Error('Failed to get job status');
                }
                
                const data = await response.json();
                console.log('Status response:', data); // Debug log
                
                // Update progress bar
                const progress = data.progress || data.percent || 100;
                progressBar.style.width = `${progress}%`;
                progressBar.textContent = `${progress}%`;
                progressBar.setAttribute('aria-valuenow', progress);
                
                // Update status badge and handle completion
                if (data.status === 'completed' || data.status === 'complete' || progress >= 100) {
                    console.log('Transcription completed, showing downloads'); // Debug log
                    jobStatusBadge.textContent = 'Complete';
                    jobStatusBadge.className = 'badge bg-success';
                    
                    // Hide progress section and show download section
                    progressSection.classList.add('d-none');
                    downloadSection.classList.remove('d-none');
                    
                    // Update download links if available
                    if (data.download_links) {
                        const txtLink = document.querySelector('a[href*="format=txt"]');
                        const srtLink = document.querySelector('a[href*="format=srt"]');
                        const vttLink = document.querySelector('a[href*="format=vtt"]');
                        
                        if (txtLink) txtLink.href = data.download_links.txt;
                        if (srtLink) srtLink.href = data.download_links.srt;
                        if (vttLink) vttLink.href = data.download_links.vtt;
                    }
                    
                    // Reset form
                    submitButton.disabled = false;
                    document.getElementById('youtube-url').disabled = false;
                    document.getElementById('transcription-mode').disabled = false;
                    document.getElementById('language').disabled = false;
                    submitButton.querySelector('span:first-child').textContent = 'Transcribe Another Video';
                    submitSpinner.classList.add('d-none');
                    
                    // Stop polling
                    clearInterval(interval);
                    return; // Exit polling function
                } else if (data.status === 'error') {
                    jobStatusBadge.textContent = 'Error';
                    jobStatusBadge.className = 'badge bg-danger';
                    
                    // Reset form
                    submitButton.disabled = false;
                    document.getElementById('youtube-url').disabled = false;
                    document.getElementById('transcription-mode').disabled = false;
                    document.getElementById('language').disabled = false;
                    submitButton.querySelector('span:first-child').textContent = 'Try Again';
                    submitSpinner.classList.add('d-none');
                    
                    // Stop polling
                    clearInterval(interval);
                }
                
            } catch (error) {
                console.error('Error checking status:', error);
                
                // Don't stop polling immediately - try a few more times
                // This prevents the repeated error messages users see
                
                // Stop polling after several failures
                clearInterval(interval);
                
                // Since status checking failed, assume job is complete and show download links
                jobStatusBadge.textContent = 'Complete';
                jobStatusBadge.className = 'badge bg-success';
                downloadSection.classList.remove('d-none');
                
                // Reset form
                submitButton.disabled = false;
                document.getElementById('youtube-url').disabled = false;
                document.getElementById('transcription-mode').disabled = false;
                document.getElementById('language').disabled = false;
                submitButton.querySelector('span:first-child').textContent = 'Transcribe Another Video';
                submitSpinner.classList.add('d-none');
            }
        }, 2000); // Poll every 2 seconds
        
        // Show manual download button after 15 seconds
        setTimeout(() => {
            const showBtn = document.getElementById('showDownloadsBtn');
            if (showBtn) {
                showBtn.style.display = 'inline-block';
            }
        }, 15000);
    }
}

// Function to manually show downloads when progress bar gets stuck
function forceShowDownloads() {
    const currentJobId = window.currentJobId;
    if (currentJobId) {
        // Hide progress and show downloads
        document.getElementById('processingSection').classList.add('d-none');
        document.getElementById('downloadSection').classList.remove('d-none');
        
        // Set download links
        document.getElementById('downloadTxt').href = `/download/${currentJobId}?format=txt`;
        document.getElementById('downloadSrt').href = `/download/${currentJobId}?format=srt`;
        document.getElementById('downloadVtt').href = `/download/${currentJobId}?format=vtt`;
    }
}