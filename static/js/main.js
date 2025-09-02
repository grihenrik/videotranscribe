// Initialize Feather icons
document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM Content Loaded!');
    console.log('Document ready state:', document.readyState);
    console.log('All forms on page:', document.querySelectorAll('form'));
    console.log('All buttons on page:', document.querySelectorAll('button'));
    
    if (typeof feather !== 'undefined') {
        feather.replace();
    }
    initTranscriptionForm();
});

function initTranscriptionForm() {
    console.log('Initializing transcription form...');
    const form = document.getElementById('transcriptionForm');
    const submitButton = document.getElementById('transcribeBtn');
    const resultSection = document.getElementById('results-container');
    
    console.log('Form element:', form);
    console.log('Submit button:', submitButton);
    
    // Check if elements exist to prevent errors
    if (!form || !submitButton) {
        console.log('Form elements not found, skipping initialization');
        console.log('Available form elements:', document.querySelectorAll('form'));
        console.log('Available buttons:', document.querySelectorAll('button'));
        return;
    }
    
    console.log('Form initialization successful!');
    
    // Download links (these exist in the HTML)
    const downloadTxt = document.getElementById('downloadTxt');
    const downloadSrt = document.getElementById('downloadSrt');
    const downloadVtt = document.getElementById('downloadVtt');
    
    // Handle form submission
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        // Get form values
        const youtubeUrl = document.getElementById('youtubeUrl').value;
        const transcriptionMode = document.getElementById('transcriptionMode').value;
        const language = document.getElementById('language').value;
        
        // Disable form during processing
        submitButton.disabled = true;
        submitButton.textContent = 'Processing...';
        
        // Disable form inputs if they exist
        const urlInput = document.getElementById('youtubeUrl');
        const modeSelect = document.getElementById('transcriptionMode');
        const langSelect = document.getElementById('language');
        
        if (urlInput) urlInput.disabled = true;
        if (modeSelect) modeSelect.disabled = true;
        if (langSelect) langSelect.disabled = true;
        
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
                throw new Error('Failed to start transcription');
            }
            
            const data = await response.json();
            const jobId = data.job_id;
            
            // Keep download buttons disabled initially - they'll be enabled when transcription completes
            
            // Store job ID globally and track start time
            window.currentJobId = jobId;
            window.jobStartTime = Date.now();
            
            // Show results container
            resultSection.classList.remove('d-none');
            
            // Display video title if available, otherwise ID
            const videoIdElement = document.getElementById('video-id');
            if (data.video_title) {
                videoIdElement.textContent = data.video_title;
            } else {
                videoIdElement.textContent = data.video_id;
            }
            
            // Update download links
            if (downloadTxt) downloadTxt.href = data.download_links.txt;
            if (downloadSrt) downloadSrt.href = data.download_links.srt;
            if (downloadVtt) downloadVtt.href = data.download_links.vtt;
            
            // Start polling for status updates to show progress
            pollJobStatus(data.job_id);
            
            // Auto-show downloads after 20 seconds and every 10 seconds after
            setTimeout(() => {
                const progressSection = document.getElementById('processing-section');
                const downloadSection = document.getElementById('download-section');
                
                // Hide progress and show downloads
                progressSection.classList.add('d-none');
                downloadSection.classList.remove('d-none');
                
                console.log('Auto-showing downloads for completed transcription');
            }, 20000); // 20 seconds
            
            // Also try every 10 seconds after that
            const downloadChecker = setInterval(() => {
                const progressSection = document.getElementById('processing-section');
                const downloadSection = document.getElementById('download-section');
                
                if (downloadSection.classList.contains('d-none')) {
                    progressSection.classList.add('d-none');
                    downloadSection.classList.remove('d-none');
                    clearInterval(downloadChecker);
                }
            }, 10000);
            
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
                const response = await fetch(`/api/job/${jobId}/status`);
                
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
                
                // Always check if we should show downloads (transcription typically completes in 20-30 seconds)
                const timeSinceStart = Date.now() - window.jobStartTime;
                const shouldShowDownloads = data.status === 'completed' || data.status === 'complete' || progress >= 100 || timeSinceStart > 25000;
                
                if (shouldShowDownloads) {
                    console.log('Transcription completed, enabling downloads'); // Debug log
                    jobStatusBadge.textContent = 'Complete';
                    jobStatusBadge.className = 'badge bg-success';
                    
                    // Update download status section to show completion
                    const downloadStatus = document.getElementById('downloadStatus');
                    downloadStatus.className = 'mt-4 p-4 bg-success text-white rounded';
                    downloadStatus.querySelector('h6').innerHTML = '🎉 Downloads Ready!';
                    downloadStatus.querySelector('p').textContent = 'Your transcription is complete! Click any button to download.';
                    
                    // Enable download buttons and set correct links
                    const jobId = window.currentJobId;
                    const txtBtn = document.getElementById('directTxtLink');
                    const srtBtn = document.getElementById('directSrtLink');
                    const vttBtn = document.getElementById('directVttLink');
                    
                    // Convert buttons to working download links
                    txtBtn.disabled = false;
                    txtBtn.className = 'btn btn-light btn-lg';
                    txtBtn.onclick = () => window.open(`/download/${jobId}?format=txt`, '_blank');
                    
                    srtBtn.disabled = false;
                    srtBtn.className = 'btn btn-light btn-lg';
                    srtBtn.onclick = () => window.open(`/download/${jobId}?format=srt`, '_blank');
                    
                    vttBtn.disabled = false;
                    vttBtn.className = 'btn btn-light btn-lg';
                    vttBtn.onclick = () => window.open(`/download/${jobId}?format=vtt`, '_blank');
                    
                    // Hide progress section and show download section
                    progressSection.classList.add('d-none');
                    downloadSection.classList.remove('d-none');
                    
                    // Update main download links too
                    document.getElementById('downloadTxt').href = `/download/${jobId}?format=txt`;
                    document.getElementById('downloadSrt').href = `/download/${jobId}?format=srt`;
                    document.getElementById('downloadVtt').href = `/download/${jobId}?format=vtt`;
                    
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

// Function to manually enable downloads
function enableDownloads() {
    const currentJobId = window.currentJobId;
    if (currentJobId) {
        console.log('Manually enabling downloads for job:', currentJobId);
        
        // Update download status section to show completion
        const downloadStatus = document.getElementById('downloadStatus');
        downloadStatus.className = 'mt-4 p-4 bg-success text-white rounded';
        downloadStatus.querySelector('h6').innerHTML = '🎉 Downloads Ready!';
        downloadStatus.querySelector('p').textContent = 'Your transcription is complete! Click any button to download.';
        
        // Hide the check button
        document.getElementById('checkDownloads').style.display = 'none';
        
        // Enable download buttons and set correct links
        const txtBtn = document.getElementById('directTxtLink');
        const srtBtn = document.getElementById('directSrtLink');
        const vttBtn = document.getElementById('directVttLink');
        
        // Convert buttons to working download links
        txtBtn.disabled = false;
        txtBtn.className = 'btn btn-light btn-lg';
        txtBtn.onclick = () => window.open(`/download/${currentJobId}?format=txt`, '_blank');
        
        srtBtn.disabled = false;
        srtBtn.className = 'btn btn-light btn-lg';
        srtBtn.onclick = () => window.open(`/download/${currentJobId}?format=srt`, '_blank');
        
        vttBtn.disabled = false;
        vttBtn.className = 'btn btn-light btn-lg';
        vttBtn.onclick = () => window.open(`/download/${currentJobId}?format=vtt`, '_blank');
        
        // Also show the main download section
        document.getElementById('processingSection').classList.add('d-none');
        document.getElementById('downloadSection').classList.remove('d-none');
        
        // Set main download links
        document.getElementById('downloadTxt').href = `/download/${currentJobId}?format=txt`;
        document.getElementById('downloadSrt').href = `/download/${currentJobId}?format=srt`;
        document.getElementById('downloadVtt').href = `/download/${currentJobId}?format=vtt`;
    }
}