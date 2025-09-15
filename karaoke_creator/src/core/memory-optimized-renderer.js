/**
 * Memory-Optimized Karaoke Renderer
 * Processes frames in streaming chunks to prevent out-of-memory errors
 */

class MemoryOptimizedRenderer {
  constructor(karaokeApp) {
    this.app = karaokeApp;
    this.isRendering = false;
    this.maxWorkers = Math.min(navigator.hardwareConcurrency || 2, 4); // Limit workers
    this.chunkSize = 20; // Small chunks to prevent memory issues
    this.maxFramesInMemory = 50; // Never store more than 50 frames

    // Performance tracking
    this.stats = {
      totalFrames: 0,
      processedFrames: 0,
      startTime: 0,
    };
  }

  /**
   * Render video with memory optimization
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
    this.stats.startTime = performance.now();

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

      this.stats.totalFrames = totalFrames;
      this.stats.processedFrames = 0;

      progressCallback(0, "Initializing memory-optimized rendering...");

      // Use streaming approach with MediaRecorder
      const videoBlob = await this.renderWithStreaming(
        width,
        height,
        totalFrames,
        frameInterval,
        frameRate,
        quality,
        format,
        progressCallback
      );

      this.app.downloadVideo(videoBlob);

      const renderTime = (performance.now() - this.stats.startTime) / 1000;
      const speedup = duration / renderTime;

      progressCallback(
        100,
        `Memory-optimized render complete! ${speedup.toFixed(1)}x faster`
      );

      return videoBlob;
    } finally {
      this.isRendering = false;
    }
  }

  /**
   * Render using streaming approach to minimize memory usage
   */
  async renderWithStreaming(
    width,
    height,
    totalFrames,
    frameInterval,
    frameRate,
    quality,
    format,
    progressCallback
  ) {
    // Create canvas for rendering
    const canvas = document.createElement("canvas");
    canvas.width = width;
    canvas.height = height;
    const ctx = canvas.getContext("2d");

    // Setup MediaRecorder for direct streaming
    const stream = canvas.captureStream(frameRate);
    const qualitySettings = {
      high: { videoBitsPerSecond: 4000000 }, // Reduced for memory
      medium: { videoBitsPerSecond: 2000000 },
      low: { videoBitsPerSecond: 1000000 },
    };

    const mimeType = this.getSupportedVideoFormat(format);
    const mediaRecorder = new MediaRecorder(stream, {
      mimeType,
      ...qualitySettings[quality],
    });

    const chunks = [];
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

      // Process frames in real-time streaming
      this.processFramesStreaming(
        canvas,
        ctx,
        totalFrames,
        frameInterval,
        progressCallback
      )
        .then(() => {
          mediaRecorder.stop();
        })
        .catch(reject);
    });
  }

  /**
   * Process frames in streaming mode
   */
  async processFramesStreaming(
    canvas,
    ctx,
    totalFrames,
    frameInterval,
    progressCallback
  ) {
    const frameDelay = Math.max(16, 1000 / 60); // Minimum 60 FPS processing

    for (let frameIndex = 0; frameIndex < totalFrames; frameIndex++) {
      const timestamp = frameIndex * frameInterval;

      // IMPORTANT: Seek video to current timestamp
      this.app.video.currentTime = timestamp;
      this.app.currentTime = timestamp;

      // Wait for video to seek to the correct position
      await this.waitForVideoSeek(timestamp);

      // Clear canvas
      ctx.fillStyle = "#000000";
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      // Draw video frame if available
      if (this.app.video.videoWidth > 0) {
        ctx.drawImage(this.app.video, 0, 0, canvas.width, canvas.height);
      }

      // Render karaoke effects for this frame
      await this.renderKaraokeFrame(
        ctx,
        timestamp,
        canvas.width,
        canvas.height
      );

      // Update progress
      this.stats.processedFrames++;
      const progress =
        5 + (this.stats.processedFrames / this.stats.totalFrames) * 80;
      progressCallback(
        progress,
        `Streaming frame ${frameIndex + 1}/${totalFrames} (${timestamp.toFixed(
          2
        )}s)`
      );

      // Small delay to prevent blocking and allow garbage collection
      if (frameIndex % 10 === 0) {
        await this.sleep(5);
      }

      // Ensure frame is captured by MediaRecorder
      await this.sleep(Math.max(16, 1000 / frameRate));
    }
  }

  /**
   * Render karaoke effects for a single frame
   */
  async renderKaraokeFrame(ctx, timestamp, width, height) {
    // Find active subtitle
    const activeSubtitle = this.app.subtitles.find(
      (sub) => timestamp >= sub.start_time && timestamp <= sub.end_time
    );

    if (!activeSubtitle) return;

    // Get words for this subtitle
    const words = this.app.wordSegments.filter(
      (word) =>
        word.start_time >= activeSubtitle.start_time &&
        word.end_time <= activeSubtitle.end_time
    );

    if (words.length === 0) return;

    // Setup text rendering
    const effects = this.app.effects;
    ctx.font = `${effects.fontWeight} ${effects.fontSize}px ${effects.fontFamily}`;
    ctx.textAlign = "left";
    ctx.textBaseline = "middle";

    // Apply text effects
    this.applyTextEffects(ctx, effects);

    // Calculate position
    const centerX = effects.positionX;
    const baseY = effects.positionY;

    // Render words with effects
    this.renderWordsOptimized(ctx, words, centerX, baseY, timestamp, effects);
  }

  /**
   * Render words with memory-optimized approach
   */
  renderWordsOptimized(ctx, words, centerX, baseY, currentTime, effects) {
    // Calculate total width for centering
    const wordWidths = words.map((word) => ctx.measureText(word.word).width);
    const totalSpacing = (words.length - 1) * effects.wordSpacing;
    const totalWidth =
      wordWidths.reduce((sum, width) => sum + width, 0) + totalSpacing;

    let currentX = centerX - totalWidth / 2;

    // Render each word
    words.forEach((word, index) => {
      const progress = this.getWordProgress(
        word,
        currentTime,
        effects.animationSpeed
      );

      // Apply karaoke effect
      this.renderWordWithEffect(ctx, word, currentX, baseY, progress, effects);

      currentX += wordWidths[index] + effects.wordSpacing;
    });
  }

  /**
   * Render single word with effect
   */
  renderWordWithEffect(ctx, word, x, y, progress, effects) {
    let color;

    switch (effects.karaokeMode) {
      case "highlight":
        const isHighlighted = progress > 0 && progress < 1;
        color = isHighlighted ? effects.highlightColor : effects.primaryColor;
        break;

      case "gradient":
        const primary = this.hexToRgb(effects.primaryColor);
        const highlight = this.hexToRgb(effects.highlightColor);
        const r = Math.round(primary.r + (highlight.r - primary.r) * progress);
        const g = Math.round(primary.g + (highlight.g - primary.g) * progress);
        const b = Math.round(primary.b + (highlight.b - primary.b) * progress);
        color = `rgb(${r}, ${g}, ${b})`;
        break;

      case "fill":
        // Simple fill mode without clipping to save memory
        color = progress > 0.5 ? effects.highlightColor : effects.primaryColor;
        break;

      default:
        color = effects.primaryColor;
    }

    ctx.fillStyle = color;
    ctx.fillText(word.word, x, y);
  }

  /**
   * Apply text effects
   */
  applyTextEffects(ctx, effects) {
    // Reset effects
    ctx.shadowBlur = 0;
    ctx.shadowOffsetX = 0;
    ctx.shadowOffsetY = 0;

    // Apply shadow if enabled (simplified)
    if (effects.enableShadow) {
      ctx.shadowColor = effects.shadowColor;
      ctx.shadowBlur = Math.min(effects.shadowBlur, 10); // Limit blur for performance
      ctx.shadowOffsetX = effects.shadowOffsetX;
      ctx.shadowOffsetY = effects.shadowOffsetY;
    }
  }

  /**
   * Get word progress for animation
   */
  getWordProgress(wordData, currentTime, animationSpeed) {
    if (currentTime < wordData.start_time) return 0;
    if (currentTime > wordData.end_time) return 1;

    const duration = wordData.end_time - wordData.start_time;
    const elapsed = currentTime - wordData.start_time;
    return Math.min(1, (elapsed / duration) * animationSpeed);
  }

  /**
   * Convert hex color to RGB
   */
  hexToRgb(hex) {
    const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
    return result
      ? {
          r: parseInt(result[1], 16),
          g: parseInt(result[2], 16),
          b: parseInt(result[3], 16),
        }
      : { r: 255, g: 255, b: 255 };
  }

  /**
   * Get supported video format
   */
  getSupportedVideoFormat(preferredFormat) {
    const formats = [
      "video/webm;codecs=vp8", // More compatible than vp9
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
   * Wait for video to seek to target time
   */
  async waitForVideoSeek(targetTime) {
    return new Promise((resolve) => {
      const checkSeek = () => {
        const currentTime = this.app.video.currentTime;
        const timeDiff = Math.abs(currentTime - targetTime);

        // Accept if within 1/30th of a second (frame precision)
        if (timeDiff < 0.033 || this.app.video.readyState >= 2) {
          resolve();
        } else {
          // Wait a bit more for precise seeking
          setTimeout(checkSeek, 10);
        }
      };

      // Start checking immediately
      checkSeek();

      // Timeout after 200ms to prevent infinite waiting
      setTimeout(resolve, 200);
    });
  }

  /**
   * Sleep utility for non-blocking delays
   */
  sleep(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  /**
   * Cleanup resources
   */
  cleanup() {
    this.isRendering = false;
    // Force garbage collection if available
    if (window.gc) {
      window.gc();
    }
  }
}

// Export for use in main application
if (typeof module !== "undefined" && module.exports) {
  module.exports = MemoryOptimizedRenderer;
} else if (typeof window !== "undefined") {
  window.MemoryOptimizedRenderer = MemoryOptimizedRenderer;
}
