/**
 * Emotion Capture Module
 * Handles video recording and image capture for patient assessments
 * Used by both PHQ-9 and Open Questions assessments
 */

class EmotionCapture {
    constructor(config) {
        console.log('🏗️ EmotionCapture constructor called with:', config);
        console.log('🏗️ Config type:', typeof config);
        console.log('🏗️ Config keys:', config ? Object.keys(config) : 'config is null/undefined');
        
        this.config = config;
        this.cameraStream = null;
        this.mediaRecorder = null;
        this.isRecording = false;
        this.recordedChunks = [];
        this.imageCaptureInterval = null;
        this.startTime = Date.now();
        
        console.log('🎬 EmotionCapture initialized with config:', this.config);
    }

    /**
     * Initialize camera and start recording based on mode
     */
    async initialize() {
        try {
            console.log('🔍 Initialize called - this.config:', this.config);
            console.log('🔍 this.config type:', typeof this.config);
            console.log('🔍 this.config keys:', this.config ? Object.keys(this.config) : 'config is null/undefined');
            
            if (!this.config) {
                throw new Error('Config is null or undefined in initialize method');
            }
            
            console.log(`📹 Initializing emotion capture - Mode: ${this.config.mode}, Enabled: ${this.config.enabled}`);
            
            if (!this.config.enabled) {
                console.log('📹 Emotion capture disabled in settings');
                this.updateStatus('Recording Disabled');
                return false;
            }

            // Get camera stream
            await this.initializeCamera();
            
            // Start recording based on mode
            if (this.config.mode === 'video') {
                await this.startVideoRecording();
            } else {
                this.startPeriodicImageCapture();
            }
            
            return true;
            
        } catch (error) {
            console.error('📹 Failed to initialize emotion capture:', error);
            this.updateStatus('Camera Error');
            return false;
        }
    }

    /**
     * Initialize camera stream
     */
    async initializeCamera() {
        const [width, height] = this.config.resolution.split('x').map(n => parseInt(n));
        
        console.log(`📹 Requesting camera access - Resolution: ${width}x${height}`);
        
        const stream = await navigator.mediaDevices.getUserMedia({
            video: {
                width: { ideal: width },
                height: { ideal: height },
                facingMode: 'user'
            },
            audio: false // No audio for emotion capture
        });
        
        // Ensure only video tracks
        const videoTracks = stream.getVideoTracks();
        const audioTracks = stream.getAudioTracks();
        
        console.log('📹 Stream tracks - Video:', videoTracks.length, 'Audio:', audioTracks.length);
        
        // Remove any audio tracks
        audioTracks.forEach(track => {
            stream.removeTrack(track);
            track.stop();
        });
        
        this.cameraStream = stream;
        
        // Set video preview if element exists
        const videoElement = document.getElementById('cameraPreview');
        if (videoElement) {
            videoElement.srcObject = stream;
        }
        
        return stream;
    }

    /**
     * Start video recording (continuous)
     */
    async startVideoRecording() {
        if (!this.cameraStream || this.isRecording) return;
        
        try {
            this.recordedChunks = [];
            
            // Determine best supported codec
            const codecOptions = [
                `video/${this.config.video_format};codecs=vp9`,
                `video/${this.config.video_format};codecs=vp8`,
                `video/${this.config.video_format}`,
                'video/webm;codecs=vp9',
                'video/webm;codecs=vp8', 
                'video/webm',
                'video/mp4'
            ];
            
            let selectedMimeType = null;
            for (const mimeType of codecOptions) {
                if (MediaRecorder.isTypeSupported(mimeType)) {
                    selectedMimeType = mimeType;
                    console.log(`📹 Selected video format: ${mimeType}`);
                    break;
                }
            }
            
            if (!selectedMimeType) {
                throw new Error('No supported video format found');
            }
            
            // Create MediaRecorder
            this.mediaRecorder = new MediaRecorder(this.cameraStream, {
                mimeType: selectedMimeType
            });
            
            this.mediaRecorder.ondataavailable = (event) => {
                console.log('📹 Video data available, size:', event.data.size);
                if (event.data.size > 0) {
                    this.recordedChunks.push(event.data);
                }
            };
            
            this.mediaRecorder.onstop = () => {
                console.log('📹 Video recording stopped, chunks:', this.recordedChunks.length);
                const blob = new Blob(this.recordedChunks, { type: selectedMimeType });
                console.log('📹 Created video blob, size:', blob.size);
                this.saveVideoCapture(blob);
            };
            
            // Start recording
            this.mediaRecorder.start();
            this.isRecording = true;
            
            this.updateStatus('Recording Video');
            this.showRecordingIndicator(true);
            
            console.log('📹 Video recording started successfully');
            
        } catch (error) {
            console.error('📹 Failed to start video recording:', error);
            throw error;
        }
    }

    /**
     * Stop video recording
     */
    stopVideoRecording() {
        console.log('🛑 Stopping video recording');
        if (!this.isRecording || !this.mediaRecorder) return;
        
        this.mediaRecorder.stop();
        this.isRecording = false;
        this.showRecordingIndicator(false);
        this.updateStatus('Video Saved');
        
        console.log('🛑 Video recording stopped');
    }

    /**
     * Start periodic image capture
     */
    startPeriodicImageCapture() {
        if (!this.cameraStream) return;
        
        const intervalMs = this.config.interval * 1000;
        console.log(`📸 Starting periodic image capture every ${this.config.interval} seconds`);
        
        this.updateStatus('Capturing Images');
        this.showRecordingIndicator(true);
        
        // Capture first image immediately
        this.captureImage();
        
        // Then capture at intervals
        this.imageCaptureInterval = setInterval(() => {
            this.captureImage();
        }, intervalMs);
    }

    /**
     * Stop periodic image capture
     */
    stopPeriodicImageCapture() {
        console.log('🛑 Stopping periodic image capture');
        if (this.imageCaptureInterval) {
            clearInterval(this.imageCaptureInterval);
            this.imageCaptureInterval = null;
        }
        this.showRecordingIndicator(false);
        this.updateStatus('Image Capture Complete');
    }

    /**
     * Capture a single image
     */
    async captureImage() {
        if (!this.cameraStream) return;
        
        try {
            const videoElement = document.getElementById('cameraPreview');
            const canvas = document.getElementById('captureCanvas') || this.createCanvas();
            const context = canvas.getContext('2d');
            
            // Set canvas size to match video
            canvas.width = videoElement.videoWidth;
            canvas.height = videoElement.videoHeight;
            
            // Draw current frame
            context.drawImage(videoElement, 0, 0, canvas.width, canvas.height);
            
            // Convert to blob
            const blob = await new Promise(resolve => {
                canvas.toBlob(resolve, 'image/jpeg', this.config.image_quality);
            });
            
            console.log('📸 Image captured, size:', blob.size);
            this.saveImageCapture(blob);
            
        } catch (error) {
            console.error('📸 Failed to capture image:', error);
        }
    }

    /**
     * Save video capture to server
     */
    async saveVideoCapture(blob) {
        console.log('💾 Saving video capture, blob size:', blob.size);
        
        try {
            const reader = new FileReader();
            const base64Data = await new Promise((resolve) => {
                reader.onload = () => resolve(reader.result);
                reader.readAsDataURL(blob);
            });
            
            const captureTimestamp = Date.now();
            const sessionDuration = captureTimestamp - this.startTime;
            
            const payload = {
                assessment_type: this.config.assessment_type,
                question_identifier: this.config.assessment_type === 'phq9' ? 'full_phq9_session' : 'full_session',
                media_type: 'video',
                file_data: base64Data,
                duration_ms: sessionDuration,
                filename: `${this.config.assessment_type}_session_${captureTimestamp}.${this.config.video_format}`,
                capture_timestamp: captureTimestamp,
                conversation_elapsed_ms: sessionDuration,
                recording_settings: {
                    mode: this.config.mode,
                    video_quality: this.config.video_quality,
                    video_format: this.config.video_format,
                    resolution: this.config.resolution
                }
            };
            
            console.log('💾 Sending video to server');
            
            const response = await fetch('/patient/capture-emotion', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            
            if (response.ok) {
                const result = await response.json();
                console.log('💾 Video saved successfully:', result);
            } else {
                const errorText = await response.text();
                console.error('💾 Failed to save video:', response.status, errorText);
            }
            
        } catch (error) {
            console.error('💾 Error saving video:', error);
        }
    }

    /**
     * Save image capture to server
     */
    async saveImageCapture(blob) {
        try {
            const reader = new FileReader();
            const base64Data = await new Promise((resolve) => {
                reader.onload = () => resolve(reader.result);
                reader.readAsDataURL(blob);
            });
            
            const captureTimestamp = Date.now();
            const timeElapsed = captureTimestamp - this.startTime;
            
            const payload = {
                assessment_type: this.config.assessment_type,
                question_identifier: this.config.assessment_type === 'phq9' 
                    ? `interval_${captureTimestamp}` 
                    : `chat_${captureTimestamp}`,
                media_type: 'image',
                file_data: base64Data,
                duration_ms: 0,
                filename: `${this.config.assessment_type}_image_${captureTimestamp}.jpg`,
                capture_timestamp: captureTimestamp,
                conversation_elapsed_ms: timeElapsed,
                recording_settings: {
                    mode: this.config.mode,
                    interval_seconds: this.config.interval,
                    resolution: this.config.resolution,
                    image_quality: this.config.image_quality
                }
            };
            
            const response = await fetch('/patient/capture-emotion', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            
            if (response.ok) {
                console.log('📸 Image saved successfully');
            } else {
                console.error('📸 Failed to save image:', response.status);
            }
            
        } catch (error) {
            console.error('📸 Error saving image:', error);
        }
    }

    /**
     * Stop all recording and cleanup
     */
    stop() {
        console.log('🛑 Stopping emotion capture');
        
        if (this.config.mode === 'video' && this.isRecording) {
            this.stopVideoRecording();
        } else {
            this.stopPeriodicImageCapture();
        }
        
        this.cleanup();
    }

    /**
     * Cleanup resources
     */
    cleanup() {
        if (this.cameraStream) {
            this.cameraStream.getTracks().forEach(track => track.stop());
            this.cameraStream = null;
        }
        
        if (this.imageCaptureInterval) {
            clearInterval(this.imageCaptureInterval);
            this.imageCaptureInterval = null;
        }
        
        this.isRecording = false;
        this.mediaRecorder = null;
        this.recordedChunks = [];
        
        console.log('🧹 Emotion capture cleanup complete');
    }

    /**
     * Update status text
     */
    updateStatus(text) {
        const statusElement = document.getElementById('camera-status-text');
        if (statusElement) {
            statusElement.textContent = text;
        }
    }

    /**
     * Show/hide recording indicator
     */
    showRecordingIndicator(show) {
        const indicator = document.getElementById('recording-indicator');
        const status = document.getElementById('recording-status');
        
        if (indicator) {
            if (show) {
                indicator.classList.remove('hidden');
            } else {
                indicator.classList.add('hidden');
            }
        }
        
        if (status) {
            if (show) {
                status.classList.remove('hidden');
            } else {
                status.classList.add('hidden');
            }
        }
    }

    /**
     * Create canvas element if it doesn't exist
     */
    createCanvas() {
        const canvas = document.createElement('canvas');
        canvas.id = 'captureCanvas';
        canvas.style.display = 'none';
        document.body.appendChild(canvas);
        return canvas;
    }
}

// Global emotion capture instance
window.emotionCapture = null;

/**
 * Initialize emotion capture for assessment
 * @param {Object} config - Recording configuration from server
 */
window.initializeEmotionCapture = async function(config) {
    try {
        console.log('🚀 initializeEmotionCapture called with config:', config);
        
        // Cleanup any existing instance
        if (window.emotionCapture) {
            console.log('🧹 Cleaning up existing emotion capture instance');
            window.emotionCapture.cleanup();
        }
        
        // Create new instance
        console.log('🏗️ Creating new EmotionCapture instance');
        window.emotionCapture = new EmotionCapture(config);
        
        // Initialize
        console.log('⚡ Initializing emotion capture...');
        const success = await window.emotionCapture.initialize();
        
        if (!success) {
            console.error('❌ Failed to initialize emotion capture');
        } else {
            console.log('✅ Emotion capture initialized successfully');
        }
        
        return success;
        
    } catch (error) {
        console.error('💥 Error initializing emotion capture:', error);
        console.error('💥 Error stack:', error.stack);
        return false;
    }
};

/**
 * Stop emotion capture
 */
window.stopEmotionCapture = function() {
    if (window.emotionCapture) {
        window.emotionCapture.stop();
    }
};

/**
 * Cleanup emotion capture on page unload
 */
window.addEventListener('beforeunload', function() {
    if (window.emotionCapture) {
        window.emotionCapture.cleanup();
    }
});