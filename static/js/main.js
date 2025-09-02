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
        
        // Set download links
        const txtLink = document.getElementById('download-txt');
        const srtLink = document.getElementById('download-srt');
        const vttLink = document.getElementById('download-vtt');
        
        if (txtLink && data.download_links?.txt) txtLink.href = data.download_links.txt;
        if (srtLink && data.download_links?.srt) srtLink.href = data.download_links.srt;
        if (vttLink && data.download_links?.vtt) vttLink.href = data.download_links.vtt;
        
        // Show downloads after delay
        setTimeout(() => {
            const downloadSection = document.getElementById('download-section');
            if (downloadSection) {
                downloadSection.classList.remove('d-none');
            }
        }, 3000);
        
        alert(`✅ Transcription started successfully!\nJob ID: ${data.job_id}\nDownload links will appear in a few seconds.`);
    }
});

console.log('JavaScript file loaded completely');