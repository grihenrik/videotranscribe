// YouTube Transcription Tool - Main JavaScript

// Wait for the page to fully load
window.addEventListener('load', function() {
    console.log('Page fully loaded, initializing...');
    
    // Find form elements
    const form = document.getElementById('transcriptionForm');
    const button = document.getElementById('transcribeBtn');
    
    console.log('Form found:', !!form);
    console.log('Button found:', !!button);
    
    if (form && button) {
        console.log('SUCCESS: Setting up transcription form');
        setupTranscriptionForm(form, button);
    } else {
        console.log('FAILED: Form elements not found');
        // Try alternative approach
        const forms = document.getElementsByTagName('form');
        const buttons = document.getElementsByTagName('button');
        
        if (forms.length > 0 && buttons.length > 0) {
            console.log('Using alternative method to find elements');
            setupTranscriptionForm(forms[0], buttons[0]);
        } else {
            console.log('No form elements found at all');
        }
    }
    
    // Initialize Feather icons if available
    if (typeof feather !== 'undefined') {
        try {
            feather.replace();
        } catch (e) {
            console.log('Feather icons initialization failed:', e);
        }
    }
});

function setupTranscriptionForm(form, button) {
    console.log('Setting up form functionality...');
    
    // Prevent default form submission
    form.addEventListener('submit', function(e) {
        e.preventDefault();
        e.stopPropagation();
        console.log('Form submitted via event listener');
        handleTranscription();
        return false;
    });
    
    // Handle button clicks
    button.addEventListener('click', function(e) {
        e.preventDefault();
        e.stopPropagation();
        console.log('Button clicked');
        handleTranscription();
        return false;
    });
    
    // Add onsubmit as backup
    form.onsubmit = function() {
        console.log('Form submitted via onsubmit');
        handleTranscription();
        return false;
    };
    
    function handleTranscription() {
        console.log('Processing transcription request...');
        
        // Get form values
        const urlInput = document.getElementById('youtubeUrl');
        const modeSelect = document.getElementById('transcriptionMode');
        const langSelect = document.getElementById('language');
        
        const youtubeUrl = urlInput ? urlInput.value.trim() : '';
        const transcriptionMode = modeSelect ? modeSelect.value : 'auto';
        const language = langSelect ? langSelect.value : 'en';
        
        console.log('Form data:', { youtubeUrl, transcriptionMode, language });
        
        // Validate input
        if (!youtubeUrl) {
            alert('Please enter a YouTube URL');
            return;
        }
        
        if (!youtubeUrl.includes('youtube.com') && !youtubeUrl.includes('youtu.be')) {
            alert('Please enter a valid YouTube URL');
            return;
        }
        
        // Disable form during processing
        button.disabled = true;
        button.textContent = 'Processing...';
        if (urlInput) urlInput.disabled = true;
        if (modeSelect) modeSelect.disabled = true;
        if (langSelect) langSelect.disabled = true;
        
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
            console.log('API response status:', response.status);
            return response.json();
        })
        .then(data => {
            console.log('API response data:', data);
            
            if (data.job_id) {
                // Show success message
                alert('Transcription started successfully! Job ID: ' + data.job_id);
                
                // Show results section
                const resultsContainer = document.getElementById('results-container');
                if (resultsContainer) {
                    resultsContainer.classList.remove('d-none');
                }
                
                // Update video information
                const videoIdElement = document.getElementById('video-id');
                if (videoIdElement) {
                    videoIdElement.textContent = data.video_id || 'Processing...';
                }
                
                // Set up download links
                updateDownloadLinks(data.download_links);
                
                // Show download section after a few seconds
                setTimeout(() => {
                    showDownloadSection();
                }, 3000);
                
            } else {
                alert('Error starting transcription: ' + (data.error || 'Unknown error'));
            }
        })
        .catch(error => {
            console.error('Network error:', error);
            alert('Failed to connect to the server. Please try again.');
        })
        .finally(() => {
            // Re-enable form
            button.disabled = false;
            button.textContent = 'Transcribe Video';
            if (urlInput) urlInput.disabled = false;
            if (modeSelect) modeSelect.disabled = false;
            if (langSelect) langSelect.disabled = false;
        });
    }
}

function updateDownloadLinks(downloadLinks) {
    if (!downloadLinks) return;
    
    const txtLink = document.getElementById('download-txt');
    const srtLink = document.getElementById('download-srt');
    const vttLink = document.getElementById('download-vtt');
    
    if (txtLink && downloadLinks.txt) txtLink.href = downloadLinks.txt;
    if (srtLink && downloadLinks.srt) srtLink.href = downloadLinks.srt;
    if (vttLink && downloadLinks.vtt) vttLink.href = downloadLinks.vtt;
}

function showDownloadSection() {
    const downloadSection = document.getElementById('download-section');
    if (downloadSection) {
        downloadSection.classList.remove('d-none');
        console.log('Download section shown');
    }
}