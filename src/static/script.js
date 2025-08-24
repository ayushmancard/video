// Global variables
let currentUploadId = null;
let progressInterval = null;

// DOM elements
const uploadArea = document.getElementById('uploadArea');
const videoInput = document.getElementById('videoInput');
const uploadContainer = document.getElementById('uploadContainer');
const optionsPanel = document.getElementById('optionsPanel');
const progressSection = document.getElementById('progressSection');
const resultsSection = document.getElementById('resultsSection');
const errorSection = document.getElementById('errorSection');

const processBtn = document.getElementById('processBtn');
const downloadBtn = document.getElementById('downloadBtn');
const newVideoBtn = document.getElementById('newVideoBtn');
const retryBtn = document.getElementById('retryBtn');

const progressFill = document.getElementById('progressFill');
const progressText = document.getElementById('progressText');
const progressPercent = document.getElementById('progressPercent');
const errorMessage = document.getElementById('errorMessage');

// Utility functions
function scrollToUpload() {
    document.getElementById('upload').scrollIntoView({ behavior: 'smooth' });
}

function scrollToFeatures() {
    document.getElementById('features').scrollIntoView({ behavior: 'smooth' });
}

function showSection(section) {
    // Hide all sections
    uploadContainer.style.display = 'none';
    optionsPanel.style.display = 'none';
    progressSection.style.display = 'none';
    resultsSection.style.display = 'none';
    errorSection.style.display = 'none';
    
    // Show the specified section
    section.style.display = 'block';
}

function showError(message) {
    errorMessage.textContent = message;
    showSection(errorSection);
}

function resetToUpload() {
    currentUploadId = null;
    if (progressInterval) {
        clearInterval(progressInterval);
        progressInterval = null;
    }
    videoInput.value = '';
    showSection(uploadContainer);
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function isValidVideoFile(file) {
    const validTypes = ['video/mp4', 'video/avi', 'video/mov', 'video/quicktime', 'video/x-msvideo', 'video/webm', 'video/x-flv', 'video/x-matroska'];
    return validTypes.includes(file.type) || file.name.match(/\.(mp4|avi|mov|mkv|webm|flv)$/i);
}

// File upload handling
function handleFileSelect(file) {
    if (!file) return;
    
    // Validate file type
    if (!isValidVideoFile(file)) {
        showError('Please select a valid video file (MP4, AVI, MOV, MKV, WebM, FLV).');
        return;
    }
    
    // Validate file size (500MB limit)
    const maxSize = 500 * 1024 * 1024; // 500MB
    if (file.size > maxSize) {
        showError(`File size (${formatFileSize(file.size)}) exceeds the maximum limit of 500MB.`);
        return;
    }
    
    // Show options panel
    showSection(optionsPanel);
    
    // Store the file for later upload
    uploadArea.selectedFile = file;
    
    // Update UI to show selected file
    const uploadIcon = uploadArea.querySelector('.upload-icon');
    const uploadTitle = uploadArea.querySelector('h3');
    const uploadDesc = uploadArea.querySelector('p');
    
    uploadIcon.innerHTML = '<i class="fas fa-check-circle"></i>';
    uploadTitle.textContent = file.name;
    uploadDesc.textContent = `${formatFileSize(file.size)} - Ready to enhance`;
    
    uploadArea.style.borderColor = '#22c55e';
    uploadArea.style.background = 'rgba(34, 197, 94, 0.05)';
}

// Drag and drop functionality
uploadArea.addEventListener('click', () => {
    videoInput.click();
});

uploadArea.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadArea.classList.add('dragover');
});

uploadArea.addEventListener('dragleave', () => {
    uploadArea.classList.remove('dragover');
});

uploadArea.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadArea.classList.remove('dragover');
    
    const files = e.dataTransfer.files;
    if (files.length > 0) {
        handleFileSelect(files[0]);
    }
});

videoInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) {
        handleFileSelect(e.target.files[0]);
    }
});

// Process video
async function processVideo() {
    const file = uploadArea.selectedFile;
    if (!file) {
        showError('No file selected.');
        return;
    }
    
    try {
        // Show progress section
        showSection(progressSection);
        updateProgress(0, 'Uploading video...');
        
        // Upload file
        const formData = new FormData();
        formData.append('video', file);
        
        const uploadResponse = await fetch('/api/video/upload', {
            method: 'POST',
            body: formData
        });
        
        if (!uploadResponse.ok) {
            const errorData = await uploadResponse.json();
            throw new Error(errorData.error || 'Upload failed');
        }
        
        const uploadResult = await uploadResponse.json();
        currentUploadId = uploadResult.upload_id;
        
        updateProgress(20, 'Upload complete. Starting processing...');
        
        // Get enhancement options
        const options = {
            scale: parseInt(document.getElementById('scaleSelect').value),
            denoise: document.getElementById('denoiseCheck').checked,
            sharpen: document.getElementById('sharpenCheck').checked,
            enhance_colors: document.getElementById('enhanceColorsCheck').checked
        };
        
        // Start processing
        const processResponse = await fetch(`/api/video/process/${currentUploadId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(options)
        });
        
        if (!processResponse.ok) {
            const errorData = await processResponse.json();
            throw new Error(errorData.error || 'Processing failed to start');
        }
        
        // Start polling for progress
        startProgressPolling();
        
    } catch (error) {
        console.error('Error processing video:', error);
        showError(error.message || 'An error occurred while processing your video.');
    }
}

function updateProgress(percent, message) {
    progressFill.style.width = `${percent}%`;
    progressPercent.textContent = `${percent}%`;
    progressText.textContent = message;
}

function startProgressPolling() {
    if (progressInterval) {
        clearInterval(progressInterval);
    }
    
    progressInterval = setInterval(async () => {
        try {
            const response = await fetch(`/api/video/status/${currentUploadId}`);
            if (!response.ok) {
                throw new Error('Failed to get status');
            }
            
            const status = await response.json();
            
            updateProgress(status.progress, status.message);
            
            if (status.status === 'completed') {
                clearInterval(progressInterval);
                progressInterval = null;
                showSection(resultsSection);
            } else if (status.status === 'error') {
                clearInterval(progressInterval);
                progressInterval = null;
                showError(status.message || 'Processing failed');
            }
            
        } catch (error) {
            console.error('Error polling status:', error);
            clearInterval(progressInterval);
            progressInterval = null;
            showError('Lost connection to server. Please try again.');
        }
    }, 2000); // Poll every 2 seconds
}

async function downloadVideo() {
    if (!currentUploadId) {
        showError('No video to download.');
        return;
    }
    
    try {
        // Create a temporary link to download the file
        const downloadUrl = `/api/video/download/${currentUploadId}`;
        const link = document.createElement('a');
        link.href = downloadUrl;
        link.download = ''; // Let the server determine the filename
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        
    } catch (error) {
        console.error('Error downloading video:', error);
        showError('Failed to download the enhanced video.');
    }
}

async function cleanupFiles() {
    if (!currentUploadId) return;
    
    try {
        await fetch(`/api/video/cleanup/${currentUploadId}`, {
            method: 'DELETE'
        });
    } catch (error) {
        console.error('Error cleaning up files:', error);
    }
}

// Event listeners
processBtn.addEventListener('click', processVideo);
downloadBtn.addEventListener('click', downloadVideo);
newVideoBtn.addEventListener('click', () => {
    cleanupFiles();
    resetToUpload();
});
retryBtn.addEventListener('click', resetToUpload);

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (progressInterval) {
        clearInterval(progressInterval);
    }
    cleanupFiles();
});

// Smooth scrolling for navigation links
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            target.scrollIntoView({
                behavior: 'smooth',
                block: 'start'
            });
        }
    });
});

// Add loading animation to buttons
function addButtonLoading(button) {
    const originalText = button.innerHTML;
    button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing...';
    button.disabled = true;
    
    return () => {
        button.innerHTML = originalText;
        button.disabled = false;
    };
}

// Enhanced error handling with retry logic
let retryCount = 0;
const maxRetries = 3;

async function fetchWithRetry(url, options = {}, retries = maxRetries) {
    try {
        const response = await fetch(url, options);
        retryCount = 0; // Reset on success
        return response;
    } catch (error) {
        if (retries > 0 && (error.name === 'TypeError' || error.message.includes('fetch'))) {
            console.log(`Retrying request to ${url}. Attempts left: ${retries}`);
            await new Promise(resolve => setTimeout(resolve, 1000 * (maxRetries - retries + 1)));
            return fetchWithRetry(url, options, retries - 1);
        }
        throw error;
    }
}

// Initialize the application
document.addEventListener('DOMContentLoaded', () => {
    console.log('VideoEnhance Pro initialized');
    
    // Show upload section by default
    showSection(uploadContainer);
    
    // Add some visual feedback for better UX
    const buttons = document.querySelectorAll('.btn');
    buttons.forEach(button => {
        button.addEventListener('mouseenter', () => {
            button.style.transform = 'translateY(-2px)';
        });
        
        button.addEventListener('mouseleave', () => {
            button.style.transform = 'translateY(0)';
        });
    });
});

