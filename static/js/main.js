// YouTube Transcription Tool - Clean Implementation

console.log("JavaScript loading...");

// Configuration cache
let appConfig = null;

// Load configuration from API
async function loadConfig() {
  try {
    const response = await fetch("/api/config");
    if (response.ok) {
      appConfig = await response.json();
      console.log("Application config loaded:", appConfig);
      // Update file input max size in HTML if it exists
      const fileInput = document.getElementById("audioFile");
      if (fileInput) {
        fileInput.setAttribute("data-max-size", appConfig.max_file_size_mb * 1024 * 1024);
      }
    }
  } catch (error) {
    console.error("Failed to load config:", error);
    // Use defaults if config fails to load
    appConfig = {
      max_file_size_mb: 1000,
      max_whisper_file_size_mb: 25,
      allowed_extensions: ['.mp3', '.mp4', '.wav', '.m4a', '.flac', '.aac', '.ogg', '.webm', '.mov', '.avi', '.mkv', '.wma', '.3gp', '.amr']
    };
  }
  return appConfig;
}

document.addEventListener("DOMContentLoaded", function () {
  console.log("DOM loaded, initializing...");

  // Load configuration first and then initialize the app
  loadConfig().then(() => {
    console.log("Configuration loaded, initializing app...");
    initializeApp();
  }).catch(error => {
    console.error("Failed to initialize app:", error);
    // Try to initialize anyway with defaults
    initializeApp();
  });
});

function initializeApp() {
  // Find form elements
  const form = document.getElementById("transcriptionForm");
  const button = document.getElementById("transcribeBtn");

  console.log("Form element:", form);
  console.log("Button element:", button);

  if (!form || !button) {
    console.error("Required form elements not found!");
    return;
  }

  console.log("✅ Form elements found, setting up handlers...");

  // Prevent default form submission
  form.addEventListener("submit", function (e) {
    e.preventDefault();
    e.stopPropagation();
    console.log("Form submission intercepted");
    handleSubmission();
    return false;
  });

  // Handle button clicks
  button.addEventListener("click", function (e) {
    e.preventDefault();
    e.stopPropagation();
    console.log("Button click intercepted");
    handleSubmission();
    return false;
  });
}

  // Batch form handlers
  const batchForm = document.getElementById("batchForm");
  const batchButton = document.getElementById("batchBtn");

  if (batchForm && batchButton) {
    batchForm.addEventListener("submit", function (e) {
      e.preventDefault();
      e.stopPropagation();
      console.log("Batch form submission intercepted");
      handleBatchSubmission();
      return false;
    });

    batchButton.addEventListener("click", function (e) {
      e.preventDefault();
      e.stopPropagation();
      console.log("Batch button click intercepted");
      handleBatchSubmission();
      return false;
    });
  }

  // Playlist form handlers
  const playlistForm = document.getElementById("playlistForm");
  const playlistButton = document.getElementById("playlistBtn");

  if (playlistForm && playlistButton) {
    playlistForm.addEventListener("submit", function (e) {
      e.preventDefault();
      e.stopPropagation();
      console.log("Playlist form submission intercepted");
      handlePlaylistSubmission();
      return false;
    });

    playlistButton.addEventListener("click", function (e) {
      e.preventDefault();
      e.stopPropagation();
      console.log("Playlist button click intercepted");
      handlePlaylistSubmission();
      return false;
    });
  }

  // File upload form handlers
  const fileUploadForm = document.getElementById("fileUploadForm");
  const uploadButton = document.getElementById("uploadBtn");
  const fileInput = document.getElementById("audioFile");

  if (fileUploadForm && uploadButton && fileInput) {
    // File preview functionality
    fileInput.addEventListener("change", function (e) {
      const file = e.target.files[0];
      if (file) {
        showFilePreview(file);
      } else {
        hideFilePreview();
      }
    });

    fileUploadForm.addEventListener("submit", function (e) {
      e.preventDefault();
      e.stopPropagation();
      console.log("File upload form submission intercepted");
      handleFileUpload();
      return false;
    });

    uploadButton.addEventListener("click", function (e) {
      e.preventDefault();
      e.stopPropagation();
      console.log("File upload button click intercepted");
      handleFileUpload();
      return false;
    });
  }

  function handleSubmission() {
    console.log("Processing transcription request...");

    // Get form values
    const urlInput = document.getElementById("youtubeUrl");
    const modeSelect = document.getElementById("transcriptionMode");
    const langSelect = document.getElementById("language");

    const youtubeUrl = urlInput.value.trim();
    const transcriptionMode = modeSelect.value;
    const language = langSelect.value;

    console.log("Form data:", { youtubeUrl, transcriptionMode, language });

    // Validate
    if (!youtubeUrl) {
      alert("Please enter a YouTube URL");
      return;
    }

    if (
      !youtubeUrl.includes("youtube.com") &&
      !youtubeUrl.includes("youtu.be")
    ) {
      alert("Please enter a valid YouTube URL");
      return;
    }

    // Disable form
    button.disabled = true;
    button.textContent = "Processing...";
    urlInput.disabled = true;
    modeSelect.disabled = true;
    langSelect.disabled = true;

    // Submit to API with timeout
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 30000); // 30 second timeout

    fetch("/transcribe", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        url: youtubeUrl,
        mode: transcriptionMode,
        lang: language,
      }),
      signal: controller.signal,
    })
      .then((response) => {
        clearTimeout(timeoutId);
        console.log("Response status:", response.status);
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }
        return response.json();
      })
      .then((data) => {
        console.log("API Response:", data);

        if (data.job_id) {
          showSuccess(data);
        } else {
          throw new Error(data.error || "Unknown error");
        }
      })
      .catch((error) => {
        clearTimeout(timeoutId);
        console.error("Error:", error);

        let errorMessage = "Failed to start transcription: ";
        if (error.name === "AbortError") {
          errorMessage +=
            "Request timed out. The server may be busy or the video may not be accessible.";
        } else if (error.message.includes("403")) {
          errorMessage +=
            "YouTube blocked access to this video. Try a different video or try again later.";
        } else if (error.message.includes("404")) {
          errorMessage +=
            "Video not found. Please check the URL and try again.";
        } else {
          errorMessage += error.message;
        }

        alert(errorMessage);
      })
      .finally(() => {
        // Re-enable form
        button.disabled = false;
        button.textContent = "Transcribe Video";
        urlInput.disabled = false;
        modeSelect.disabled = false;
        langSelect.disabled = false;
      });
  }

  function showSuccess(data) {
    console.log("Showing success with data:", data);

    // Show results section
    const resultsContainer = document.getElementById("results-container");
    if (resultsContainer) {
      resultsContainer.classList.remove("d-none");
    }

    // Update info based on type (playlist vs single video)
    const videoIdElement = document.getElementById("video-id");
    if (videoIdElement) {
      if (data.is_playlist) {
        videoIdElement.textContent = "Playlist Processing...";
      } else {
        videoIdElement.textContent = data.video_id || "Processing...";
      }
    }

    // Set up download buttons (initially disabled)
    setupDownloadButtons(data.download_links, data.job_id, data.is_playlist);

    // Show downloads section immediately but with disabled buttons
    const downloadSection = document.getElementById("download-section");
    if (downloadSection) {
      downloadSection.classList.remove("d-none");
    }

    // Start checking for completion
    checkTranscriptionStatus(data.job_id);

    const successMessage = data.is_playlist
      ? `✅ Playlist transcription started successfully!\nJob ID: ${data.job_id}\nDownload button will be enabled when all videos are processed.`
      : `✅ Transcription started successfully!\nJob ID: ${data.job_id}\nDownload buttons will be enabled when ready.`;

    alert(successMessage);
  }

  function setupDownloadButtons(downloadLinks, jobId, isPlaylist) {
    const txtBtn = document.getElementById("download-txt");
    const srtBtn = document.getElementById("download-srt");
    const vttBtn = document.getElementById("download-vtt");

    if (isPlaylist) {
      // For playlists, hide individual format buttons and show/create ZIP download button
      [txtBtn, srtBtn, vttBtn].forEach((btn) => {
        if (btn) {
          btn.style.display = "none";
        }
      });

      // Create or update ZIP download button
      let zipBtn = document.getElementById("download-zip");
      if (!zipBtn) {
        zipBtn = document.createElement("button");
        zipBtn.id = "download-zip";
        zipBtn.className = "btn btn-success disabled";
        zipBtn.innerHTML = '<i class="fas fa-download"></i> Download All (ZIP)';
        zipBtn.style.pointerEvents = "none";
        zipBtn.style.opacity = "0.5";

        // Add to download section
        const downloadSection = document.getElementById("download-section");
        if (downloadSection) {
          downloadSection.appendChild(zipBtn);
        }
      }

      // Set up ZIP download handler
      if (downloadLinks?.zip) {
        zipBtn.addEventListener("click", (e) => {
          e.preventDefault();
          downloadFile(
            downloadLinks.zip,
            `playlist_transcriptions_${jobId}.zip`,
          );
        });
      }
    } else {
      // For single videos, show individual format buttons and hide ZIP button
      [txtBtn, srtBtn, vttBtn].forEach((btn) => {
        if (btn) {
          btn.style.display = "inline-block";
          btn.classList.add("disabled");
          btn.style.pointerEvents = "none";
          btn.style.opacity = "0.5";
          btn.href = "#"; // Reset until enabled
        }
      });

      // Hide ZIP button if it exists
      const zipBtn = document.getElementById("download-zip");
      if (zipBtn) {
        zipBtn.style.display = "none";
      }
      // href will be set when enableDownloadButtons(jobId) is called on completion
    }
  }

  function downloadFile(url, filename) {
    console.log("Downloading file:", filename);

    fetch(url)
      .then((response) => {
        if (!response.ok) {
          throw new Error("Download failed");
        }
        return response.blob();
      })
      .then((blob) => {
        const downloadUrl = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = downloadUrl;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(downloadUrl);
        console.log("File downloaded successfully");
      })
      .catch((error) => {
        console.error("Download error:", error);
        alert("Download failed. The transcription may not be ready yet.");
      });
  }

  // Global variable to track active polling
  let activePollingInterval = null;
  let isPolling = false;

  function checkTranscriptionStatus(jobId) {
    console.log("Checking transcription status for job:", jobId);

    // Clear any existing polling to prevent multiple intervals
    if (activePollingInterval) {
      clearInterval(activePollingInterval);
      console.log("Cleared existing polling interval");
    }

    // Prevent multiple concurrent polling
    if (isPolling) {
      console.log("Already polling, skipping new poll request");
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
        console.log("Stopped polling: Maximum poll count reached");

        const statusBadge = document.getElementById("job-status");
        if (statusBadge && !statusBadge.textContent.includes("Completed")) {
          statusBadge.textContent = "Timeout";
          statusBadge.className = "badge bg-warning";
        }
        return;
      }

      fetch(`/job-status/${jobId}`)
        .then((response) => response.json())
        .then((status) => {
          console.log("Job status:", status);

          const statusBadge = document.getElementById("job-status");
          const progressBar = document.getElementById("progress-bar");

          if (status.status === "complete") {
            // Transcription completed successfully
            clearInterval(activePollingInterval);
            activePollingInterval = null;
            isPolling = false;

            enableDownloadButtons(jobId);

            if (statusBadge) {
              statusBadge.textContent = "Completed";
              statusBadge.className = "badge bg-success";
            }
            if (progressBar) {
              progressBar.style.width = "100%";
              progressBar.textContent = "100%";
            }

            console.log("✅ Transcription completed, polling stopped");
          } else if (status.status === "error") {
            // Transcription failed - STOP POLLING IMMEDIATELY
            clearInterval(activePollingInterval);
            activePollingInterval = null;
            isPolling = false;

            if (statusBadge) {
              statusBadge.textContent = "Failed";
              statusBadge.className = "badge bg-danger";
            }

            const errorMsg = status.error || "Unknown error";
            console.log("❌ Transcription failed, polling stopped:", errorMsg);

            // Show error message only once
            alert(
              `Transcription failed: ${errorMsg}\n\nThis may be due to YouTube access restrictions. Try a different video.`,
            );
          } else {
            // Still processing - update progress
            if (statusBadge) {
              statusBadge.textContent = status.status || "Processing";
              statusBadge.className = "badge bg-primary";
            }
            if (progressBar && status.percent) {
              progressBar.style.width = status.percent + "%";
              progressBar.textContent = status.percent + "%";
            }

            console.log(
              `⏳ Still processing: ${status.status} (${status.percent || 0}%)`,
            );
          }
        })
        .catch((error) => {
          console.log("⚠️ Error checking status:", error.message);

          // Stop polling on fetch errors too
          clearInterval(activePollingInterval);
          activePollingInterval = null;
          isPolling = false;
          console.log("Polling stopped due to fetch error");
        });
    }, 3000); // Check every 3 seconds
  }

  function handleBatchSubmission() {
    alert(
      "Batch processing is not yet implemented in the API. This feature is coming soon!",
    );
    console.log("Batch processing placeholder");
  }

  function handlePlaylistSubmission() {
    alert(
      "Playlist processing is not yet implemented in the API. This feature is coming soon!",
    );
    console.log("Playlist processing placeholder");
  }

  function enableDownloadButtons(jobId) {
    const txtBtn = document.getElementById("download-txt");
    const srtBtn = document.getElementById("download-srt");
    const vttBtn = document.getElementById("download-vtt");
    const zipBtn = document.getElementById("download-zip");

    // Set href for direct download (more reliable than fetch)
    if (jobId) {
      if (txtBtn) {
        txtBtn.href = `/download/${jobId}?format=txt`;
        txtBtn.download = `transcription-${jobId}.txt`;
      }
      if (srtBtn) {
        srtBtn.href = `/download/${jobId}?format=srt`;
        srtBtn.download = `transcription-${jobId}.srt`;
      }
      if (vttBtn) {
        vttBtn.href = `/download/${jobId}?format=vtt`;
        vttBtn.download = `transcription-${jobId}.vtt`;
      }
    }

    // Enable all visible buttons
    [txtBtn, srtBtn, vttBtn, zipBtn].forEach((btn) => {
      if (btn && btn.style.display !== "none") {
        btn.classList.remove("disabled");
        btn.style.pointerEvents = "auto";
        btn.style.opacity = "1";
      }
    });
  }

  // File upload functions
  function showFilePreview(file) {
    const preview = document.getElementById("filePreview");
    const fileName = document.getElementById("previewFileName");
    const fileSize = document.getElementById("previewFileSize");
    const fileType = document.getElementById("previewFileType");
    const duration = document.getElementById("previewDuration");

    fileName.textContent = file.name;
    fileSize.textContent = formatFileSize(file.size);
    fileType.textContent = file.type || "Unknown";

    // Try to get duration for audio/video files
    if (file.type.startsWith("audio/") || file.type.startsWith("video/")) {
      const url = URL.createObjectURL(file);
      const media = file.type.startsWith("video/")
        ? document.createElement("video")
        : document.createElement("audio");

      media.addEventListener("loadedmetadata", function () {
        duration.textContent = formatDuration(media.duration);
        URL.revokeObjectURL(url);
      });

      media.addEventListener("error", function () {
        duration.textContent = "Unable to determine";
        URL.revokeObjectURL(url);
      });

      media.src = url;
    } else {
      duration.textContent = "N/A";
    }

    preview.classList.remove("d-none");
  }

  function hideFilePreview() {
    const preview = document.getElementById("filePreview");
    preview.classList.add("d-none");
  }

  function formatFileSize(bytes) {
    if (bytes === 0) return "0 Bytes";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
  }

  function formatDuration(seconds) {
    if (isNaN(seconds)) return "Unknown";
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);

    if (hours > 0) {
      return `${hours}:${minutes.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
    } else {
      return `${minutes}:${secs.toString().padStart(2, "0")}`;
    }
  }

  function handleFileUpload() {
    console.log("Processing file upload...");

    const fileInput = document.getElementById("audioFile");
    const languageSelect = document.getElementById("fileLanguage");
    const fileNameInput = document.getElementById("fileName");
    const uploadBtn = document.getElementById("uploadBtn");

    const file = fileInput.files[0];
    const language = languageSelect.value;
    const customName = fileNameInput.value.trim();

    console.log("File upload data:", {
      fileName: file?.name,
      fileSize: file?.size,
      language,
      customName,
    });

    // Validate
    if (!file) {
      alert("Please select a file to upload");
      return;
    }

    // Check file size using configuration
    const maxSize = (appConfig?.max_file_size_mb || 1000) * 1024 * 1024; // MB to bytes
    if (file.size > maxSize) {
      alert(`File size too large. Maximum allowed size is ${appConfig?.max_file_size_mb || 1000}MB.`);
      return;
    }

    // Disable form
    uploadBtn.disabled = true;
    uploadBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Uploading...';
    fileInput.disabled = true;
    languageSelect.disabled = true;
    fileNameInput.disabled = true;

    // Create FormData
    const formData = new FormData();
    formData.append("file", file);
    formData.append("language", language);
    if (customName) {
      formData.append("custom_name", customName);
    }

    // Submit to API
    fetch("/upload-transcribe", {
      method: "POST",
      body: formData,
    })
      .then((response) => {
        console.log("Upload response status:", response.status);
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }
        return response.json();
      })
      .then((data) => {
        console.log("Upload API Response:", data);

        if (data.job_id) {
          showSuccess(data);
        } else {
          throw new Error(data.error || "Unknown error occurred");
        }
      })
      .catch((error) => {
        console.error("Upload error:", error);
        if (typeof showError === "function") {
          showError("Upload failed: " + error.message);
        } else {
          alert("Upload failed: " + error.message);
        }

        // Re-enable form
        uploadBtn.disabled = false;
        uploadBtn.innerHTML =
          '<i class="fas fa-upload"></i> Upload & Transcribe';
        fileInput.disabled = false;
        languageSelect.disabled = false;
        fileNameInput.disabled = false;
      });
  }

console.log("JavaScript file loaded completely (v2025090204)");
