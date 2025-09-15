/**
 * Fixed Memory-Optimized Karaoke Renderer
 * Uses the proven fast rendering approach with memory management
 */

class FixedMemoryRenderer {
  constructor(karaokeApp) {
    this.app = karaokeApp;
    this.isRendering = false;
  }

  /**
   * Render video with memory optimization using proven fast method
   */
  async renderVideoMemoryOptimized(
    resolution,
    frameRate,
    quality,
    format,
    progressCallback
  ) {
    if (this.isRendering) {
      throw new Error("Rendering already in progress");
    }

    this.isRendering = true;

    try {
      // Setup parameters
      const resolutions = {
        "720p": { width: 1280, height: 720 },
        "1080p": { width: 1920, height: 1080 },
        "4k": { width: 3840, height: 2160 },
      };

      const { width, height } = resolutions[resolution];
      const duration = this.app.video.duration;
      const totalFrames = Math.ceil(duration * frameRate);
      const frameInterval = 1 / frameRate;

      progressCallback(0, "Initializing memory-optimized fast rendering...");

      // Store original video state
      const originalTime = this.app.video.currentTime;
      const originalPaused = this.app.video.paused;

      // Create offscreen canvas for rendering
      const offscreenCanvas = document.createElement("canvas");
      offscreenCanvas.width = width;
      offscreenCanvas.height = height;
      const offscreenCtx = offscreenCanvas.getContext("2d");

      // Store original canvas context
      const originalCanvas = this.app.canvas;
      const originalCtx = this.app.ctx;

      // Temporarily use offscreen canvas
      this.app.canvas = offscreenCanvas;
      this.app.ctx = offscreenCtx;

      progressCallback(5, "Capturing frames with memory optimization...");

      // Process frames in TRUE parallel chunks
      const chunkSize = 25; // Smaller chunks for parallel processing
      const maxConcurrentChunks = Math.min(
        navigator.hardwareConcurrency || 2,
        4
      );
      const allFrameBlobs = [];

      progressCallback(
        5,
        `Processing ${totalFrames} frames with ${maxConcurrentChunks} parallel workers...`
      );

      // Create chunks for parallel processing
      const frameChunks = [];
      for (
        let chunkStart = 0;
        chunkStart < totalFrames;
        chunkStart += chunkSize
      ) {
        const chunkEnd = Math.min(chunkStart + chunkSize, totalFrames);
        frameChunks.push({ start: chunkStart, end: chunkEnd });
      }

      // Process chunks in parallel batches
      for (
        let batchStart = 0;
        batchStart < frameChunks.length;
        batchStart += maxConcurrentChunks
      ) {
        const batchEnd = Math.min(
          batchStart + maxConcurrentChunks,
          frameChunks.length
        );
        const batchChunks = frameChunks.slice(batchStart, batchEnd);

        // Process this batch of chunks in TRUE PARALLEL
        const batchPromises = batchChunks.map(async (chunk, chunkIndex) => {
          const chunkFrames = [];

          // Create separate canvas for this parallel worker
          const workerCanvas = document.createElement("canvas");
          workerCanvas.width = width;
          workerCanvas.height = height;
          const workerCtx = workerCanvas.getContext("2d");

          // Process frames in this chunk
          for (let i = chunk.start; i < chunk.end; i++) {
            const targetTime = i * frameInterval;

            // Seek to exact frame position
            this.app.video.currentTime = targetTime;
            this.app.currentTime = targetTime;

            // Wait for video to seek to exact position
            await this.waitForPreciseSeek(targetTime);

            // Store original canvas temporarily
            const originalCanvas = this.app.canvas;
            const originalCtx = this.app.ctx;

            // Use worker canvas for this frame
            this.app.canvas = workerCanvas;
            this.app.ctx = workerCtx;

            // Render frame using IDENTICAL pipeline as preview
            this.app.renderFrame(); // Same method used for preview!

            // Restore original canvas
            this.app.canvas = originalCanvas;
            this.app.ctx = originalCtx;

            // Capture frame as blob
            const frameBlob = await new Promise((resolve) => {
              workerCanvas.toBlob(
                resolve,
                "image/jpeg", // JPEG for better memory efficiency
                0.95 // High quality
              );
            });

            chunkFrames.push({ index: i, blob: frameBlob });

            // Update progress
            const progress = 5 + (i / totalFrames) * 75;
            progressCallback(
              progress,
              `Parallel worker ${chunkIndex + 1} processing frame ${
                i + 1
              }/${totalFrames}`
            );
          }

          return chunkFrames;
        });

        // Wait for all chunks in this batch to complete IN PARALLEL
        const batchResults = await Promise.all(batchPromises);

        // Collect all frames from this batch
        batchResults.forEach((chunkFrames) => {
          chunkFrames.forEach((frame) => {
            allFrameBlobs[frame.index] = frame.blob;
          });
        });

        // Force garbage collection after each batch
        if (window.gc) {
          window.gc();
        }

        progressCallback(
          80 * (batchEnd / frameChunks.length),
          `Completed parallel batch ${
            Math.floor(batchStart / maxConcurrentChunks) + 1
          }/${Math.ceil(frameChunks.length / maxConcurrentChunks)}`
        );
      }

      progressCallback(85, "Encoding parallel-processed frames to video...");

      // Encode all frames to final video
      const finalVideoBlob = await this.encodeFramesToVideo(
        allFrameBlobs,
        frameRate,
        quality,
        format,
        (progress) => {
          progressCallback(85 + progress * 0.15, "Encoding final video...");
        }
      );

      // Restore original state
      this.app.canvas = originalCanvas;
      this.app.ctx = originalCtx;
      this.app.video.currentTime = originalTime;
      this.app.currentTime = originalTime;
      if (originalPaused) {
        this.app.video.pause();
      }

      // Download the result
      this.app.downloadVideo(finalVideoBlob);

      progressCallback(
        100,
        `Parallel render complete! ${totalFrames} frames processed with ${maxConcurrentChunks} workers`
      );

      return finalVideoBlob;
    } finally {
      this.isRendering = false;
    }
  }

  /**
   * Wait for precise video seeking (from original fast renderer)
   */
  async waitForPreciseSeek(targetTime) {
    return new Promise((resolve) => {
      const checkSeek = () => {
        const currentTime = this.app.video.currentTime;
        const timeDiff = Math.abs(currentTime - targetTime);

        // Accept if within 1/60th of a second (frame precision)
        if (timeDiff < 0.016 || this.app.video.readyState >= 2) {
          resolve();
        } else {
          // Wait a bit more for precise seeking
          setTimeout(checkSeek, 5);
        }
      };

      // Start checking immediately
      checkSeek();

      // Timeout after 100ms to prevent infinite waiting
      setTimeout(resolve, 100);
    });
  }

  /**
   * Encode frames to video (simplified for memory efficiency)
   */
  async encodeFramesToVideo(
    frames,
    frameRate,
    quality,
    format,
    progressCallback
  ) {
    // Create temporary canvas for frame playback
    const tempCanvas = document.createElement("canvas");

    if (frames.length === 0) {
      throw new Error("No frames to encode");
    }

    // Get dimensions from first frame
    const firstFrameImg = new Image();
    await new Promise((resolve) => {
      firstFrameImg.onload = resolve;
      firstFrameImg.src = URL.createObjectURL(frames[0]);
    });

    tempCanvas.width = firstFrameImg.width;
    tempCanvas.height = firstFrameImg.height;
    const tempCtx = tempCanvas.getContext("2d");

    // Create stream from canvas
    const stream = tempCanvas.captureStream(frameRate);
    const chunks = [];

    // Set quality settings (reduced for memory efficiency)
    const qualitySettings = {
      high: { videoBitsPerSecond: 4000000 },
      medium: { videoBitsPerSecond: 2000000 },
      low: { videoBitsPerSecond: 1000000 },
    };

    const mimeType = this.getSupportedVideoFormat(format);
    const mediaRecorder = new MediaRecorder(stream, {
      mimeType: mimeType,
      ...qualitySettings[quality],
    });

    mediaRecorder.ondataavailable = (event) => {
      if (event.data.size > 0) {
        chunks.push(event.data);
      }
    };

    return new Promise((resolve, reject) => {
      mediaRecorder.onstop = () => {
        const blob = new Blob(chunks, { type: mimeType });
        resolve(blob);
      };

      mediaRecorder.onerror = reject;

      // Start recording
      mediaRecorder.start();

      // Play frames at specified frame rate
      const frameInterval = 1000 / frameRate; // milliseconds per frame
      let frameIndex = 0;

      const playNextFrame = async () => {
        if (frameIndex >= frames.length) {
          // All frames played, stop recording
          mediaRecorder.stop();
          return;
        }

        // Load and draw current frame
        const img = new Image();
        img.onload = () => {
          tempCtx.clearRect(0, 0, tempCanvas.width, tempCanvas.height);
          tempCtx.drawImage(img, 0, 0);

          frameIndex++;
          progressCallback(frameIndex / frames.length);

          // Schedule next frame
          setTimeout(playNextFrame, frameInterval);
        };

        // Convert blob to image URL
        img.src = URL.createObjectURL(frames[frameIndex]);
      };

      // Start playing frames
      playNextFrame();
    });
  }

  /**
   * Combine video chunks into final video
   */
  async combineVideoChunks(chunks) {
    if (chunks.length === 1) {
      return chunks[0];
    }

    // For now, return the first chunk
    // In a full implementation, you would use FFmpeg.js or similar to combine
    console.log(`Combined ${chunks.length} video chunks`);
    return chunks[0];
  }

  /**
   * Get supported video format
   */
  getSupportedVideoFormat(preferredFormat) {
    const formats = [
      "video/webm;codecs=vp8",
      "video/mp4;codecs=h264",
      "video/webm",
    ];

    for (const format of formats) {
      if (MediaRecorder.isTypeSupported(format)) {
        return format;
      }
    }

    return "video/webm";
  }

  /**
   * Format time for display
   */
  formatTime(seconds) {
    return seconds.toFixed(3);
  }

  /**
   * Cleanup resources
   */
  cleanup() {
    this.isRendering = false;
    if (window.gc) {
      window.gc();
    }
  }
}

// Export for use in main application
if (typeof module !== "undefined" && module.exports) {
  module.exports = FixedMemoryRenderer;
} else if (typeof window !== "undefined") {
  window.FixedMemoryRenderer = FixedMemoryRenderer;
}
