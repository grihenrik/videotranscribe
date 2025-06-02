// Simple JavaScript for YouTube transcription platform
document.addEventListener('DOMContentLoaded', () => {
    // Initialize Feather icons
    if (typeof feather !== 'undefined') {
        feather.replace();
    }
    
    // Initialize transcription functionality
    initTranscription();
});

function initTranscription() {
    const form = document.getElementById('transcriptionForm');
    if (!form) return;
    
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        try {
            const formData = new FormData(form);
            const button = form.querySelector('button[type="submit"]');
            
            // Disable button during processing
            button.disabled = true;
            button.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Processing...';
            
            // Submit form
            const response = await fetch('/transcribe', {
                method: 'POST',
                body: formData
            });
            
            if (response.ok) {
                // Show result section
                const resultSection = document.getElementById('resultSection');
                if (resultSection) {
                    resultSection.classList.remove('d-none');
                }
                
                // Handle the response
                const data = await response.json();
                console.log('Transcription started:', data);
                
                // Re-enable button
                button.disabled = false;
                button.innerHTML = '<i data-feather="mic"></i> Transcribe Video';
                feather.replace();
            } else {
                throw new Error('Failed to start transcription');
            }
            
        } catch (error) {
            console.error('Error:', error);
            alert('Failed to start transcription. Please try again.');
            
            // Re-enable button
            const button = form.querySelector('button[type="submit"]');
            button.disabled = false;
            button.innerHTML = '<i data-feather="mic"></i> Transcribe Video';
            feather.replace();
        }
    });
}

// Function to enable downloads manually
function enableDownloads() {
    console.log('Enabling downloads...');
    
    // Show download section
    const downloadSection = document.getElementById('downloadSection');
    if (downloadSection) {
        downloadSection.classList.remove('d-none');
    }
    
    // Show result section
    const resultSection = document.getElementById('resultSection');
    if (resultSection) {
        resultSection.classList.remove('d-none');
    }
    
    alert('Downloads are now available! Check the download section.');
}