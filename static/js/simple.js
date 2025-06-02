// Simple JavaScript for YouTube Transcription Platform
// This version avoids WebSocket errors and provides a stable user experience

document.addEventListener('DOMContentLoaded', function() {
    console.log('Simple transcription interface loaded');

    // Handle form submission
    const transcribeForm = document.getElementById('transcribeForm');
    if (transcribeForm) {
        transcribeForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            // Show processing section
            const processingSection = document.getElementById('processingSection');
            const formSection = document.getElementById('formSection');
            
            if (processingSection && formSection) {
                formSection.classList.add('d-none');
                processingSection.classList.remove('d-none');
            }

            // Submit the form
            const formData = new FormData(transcribeForm);
            
            fetch('/transcribe', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.job_id) {
                    console.log('Job started:', data.job_id);
                    
                    // Start simple polling instead of WebSocket
                    pollJobStatus(data.job_id);
                } else {
                    showError('Failed to start transcription');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showError('Network error occurred');
            });
        });
    }

    // Simple polling function (no WebSocket)
    function pollJobStatus(jobId) {
        const pollInterval = setInterval(() => {
            fetch(`/job-status/${jobId}`)
                .then(response => response.json())
                .then(data => {
                    console.log('Job status:', data);
                    
                    if (data.status === 'completed') {
                        clearInterval(pollInterval);
                        showDownloads(jobId);
                    } else if (data.status === 'failed') {
                        clearInterval(pollInterval);
                        showError('Transcription failed');
                    }
                    // Keep polling if status is 'processing' or 'pending'
                })
                .catch(error => {
                    console.error('Polling error:', error);
                    // Continue polling even on error
                });
        }, 3000); // Poll every 3 seconds

        // Stop polling after 10 minutes
        setTimeout(() => {
            clearInterval(pollInterval);
            showTimeoutMessage(jobId);
        }, 600000);
    }

    // Show downloads when ready
    function showDownloads(jobId) {
        const processingSection = document.getElementById('processingSection');
        const resultSection = document.getElementById('resultSection');
        
        if (processingSection) processingSection.classList.add('d-none');
        if (resultSection) resultSection.classList.remove('d-none');

        // Update download links
        const txtLink = document.getElementById('directTxtLink');
        const srtLink = document.getElementById('directSrtLink');
        const vttLink = document.getElementById('directVttLink');

        if (txtLink) {
            txtLink.href = `/download/${jobId}?format=txt`;
            txtLink.disabled = false;
            txtLink.className = 'btn btn-light btn-lg';
        }
        if (srtLink) {
            srtLink.href = `/download/${jobId}?format=srt`;
            srtLink.disabled = false;
            srtLink.className = 'btn btn-light btn-lg';
        }
        if (vttLink) {
            vttLink.href = `/download/${jobId}?format=vtt`;
            vttLink.disabled = false;
            vttLink.className = 'btn btn-light btn-lg';
        }

        // Show success message
        alert('Your transcription is ready! You can now download the files.');
    }

    // Show timeout message with manual check option
    function showTimeoutMessage(jobId) {
        const processingSection = document.getElementById('processingSection');
        if (processingSection) {
            processingSection.innerHTML = `
                <div class="card shadow">
                    <div class="card-header bg-warning text-dark">
                        <h4 class="mb-0">Still Processing</h4>
                    </div>
                    <div class="card-body text-center">
                        <p>Your transcription is taking longer than expected but may still be processing.</p>
                        <div class="d-grid gap-2">
                            <button type="button" class="btn btn-primary" onclick="checkManually('${jobId}')">
                                Check Status Manually
                            </button>
                            <a href="/downloads" class="btn btn-outline-secondary">
                                View All Downloads
                            </a>
                            <button type="button" class="btn btn-outline-info" onclick="location.reload()">
                                Start Over
                            </button>
                        </div>
                    </div>
                </div>
            `;
        }
    }

    // Manual check function
    window.checkManually = function(jobId) {
        fetch(`/api/job-status/${jobId}`)
            .then(response => response.json())
            .then(data => {
                if (data.status === 'completed') {
                    showDownloads(jobId);
                } else if (data.status === 'failed') {
                    showError('Transcription failed');
                } else {
                    alert(`Status: ${data.status}. Please wait and try again.`);
                }
            })
            .catch(error => {
                console.error('Manual check error:', error);
                alert('Unable to check status. Please try the Downloads page.');
            });
    };

    // Show error function
    function showError(message) {
        const processingSection = document.getElementById('processingSection');
        const errorSection = document.getElementById('errorSection');
        
        if (processingSection) processingSection.classList.add('d-none');
        if (errorSection) {
            errorSection.classList.remove('d-none');
            const errorMessage = document.getElementById('errorMessage');
            if (errorMessage) errorMessage.textContent = message;
        } else {
            alert(`Error: ${message}`);
        }
    }

    // Try again button
    const tryAgainBtn = document.getElementById('tryAgainBtn');
    if (tryAgainBtn) {
        tryAgainBtn.addEventListener('click', function() {
            location.reload();
        });
    }

    console.log('Simple transcription interface ready');
});