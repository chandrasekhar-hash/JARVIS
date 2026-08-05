/**
 * CameraController Service (V7).
 * Handles HTML5 camera stream acquisition, permission checking,
 * client-side canvas frame capture, image resizing (max 1280x720),
 * JPEG 80% compression, and clean hardware stream release.
 */

export class CameraController {
  constructor() {
    this.stream = null;
    this.videoElement = null;
    this.canvasElement = null;
    this.active = false;
  }

  /**
   * Checks if camera permission is available or promptable.
   */
  async checkPermission() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      return { supported: false, permission: 'unsupported' };
    }
    try {
      if (navigator.permissions && navigator.permissions.query) {
        const status = await navigator.permissions.query({ name: 'camera' });
        return { supported: true, permission: status.state };
      }
    } catch (_) {
      // Permission query API not supported on all browsers
    }
    return { supported: true, permission: 'prompt' };
  }

  /**
   * Starts camera hardware stream.
   */
  async startCamera(constraints = { video: { width: { ideal: 1280 }, height: { ideal: 720 }, facingMode: 'environment' } }) {
    if (this.active && this.stream) {
      return true;
    }

    try {
      this.stream = await navigator.mediaDevices.getUserMedia(constraints);
      this.videoElement = document.createElement('video');
      this.videoElement.srcObject = this.stream;
      this.videoElement.setAttribute('playsinline', 'true');
      this.videoElement.muted = true;
      await this.videoElement.play();

      this.canvasElement = document.createElement('canvas');
      this.active = true;
      return true;
    } catch (err) {
      console.error('[CameraController] Failed to access camera stream:', err);
      this.stopCamera();
      throw new Error(`Camera access failed: ${err.message || 'Permission denied'}`);
    }
  }

  /**
   * Captures a single frame from the camera stream, downscaling to max 1280x720
   * and encoding to JPEG Blob at 80% quality.
   */
  async captureCompressedFrame(maxDim = 1280, quality = 0.8) {
    if (!this.active || !this.videoElement || this.videoElement.readyState < 2) {
      return null;
    }

    const vw = this.videoElement.videoWidth || 640;
    const vh = this.videoElement.videoHeight || 480;

    let targetWidth = vw;
    let targetHeight = vh;

    if (vw > maxDim || vh > maxDim) {
      if (vw > vh) {
        targetWidth = maxDim;
        targetHeight = Math.round((vh * maxDim) / vw);
      } else {
        targetHeight = maxDim;
        targetWidth = Math.round((vw * maxDim) / vh);
      }
    }

    this.canvasElement.width = targetWidth;
    this.canvasElement.height = targetHeight;

    const ctx = this.canvasElement.getContext('2d');
    ctx.drawImage(this.videoElement, 0, 0, targetWidth, targetHeight);

    return new Promise((resolve) => {
      this.canvasElement.toBlob(
        (blob) => {
          resolve({
            blob,
            width: targetWidth,
            height: targetHeight,
            timestamp: Date.now()
          });
        },
        'image/jpeg',
        quality
      );
    });
  }

  /**
   * Safely stops camera hardware stream and releases all tracks.
   */
  stopCamera() {
    if (this.stream) {
      this.stream.getTracks().forEach((track) => {
        try {
          track.stop();
        } catch (_) {}
      });
      this.stream = null;
    }
    if (this.videoElement) {
      this.videoElement.srcObject = null;
      this.videoElement = null;
    }
    this.canvasElement = null;
    this.active = false;
  }
}

export const cameraController = new CameraController();
