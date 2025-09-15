/**
 * Parallel Rendering System for Karaoke Video Export
 * Uses Web Workers and simultaneous processing for maximum speed
 */

class ParallelRenderer {
  constructor(karaokeApp) {
    this.app = karaokeApp;
    this.workers = [];
    this.maxWorkers = navigator.hardwareConcurrency || 4;
    this.frameQueue = [];
    this.completedFrames = new Map();
    this.isRendering = false;

    // Performance tracking
    this.stats = {
      totalFrames: 0,
      processedFrames: 0,
      startTime: 0,
      estimatedCompletion: 0,
    };
  }

  /**
   * Initialize Web Workers for parallel processing
   */
  async initializeWorkers() {
    // Create worker pool
    for (let i = 0; i < this.maxWorkers; i++) {
      const worker = new Worker(
        URL.createObjectURL(
          new Blob([this.getWorkerCode()], {
            type: "application/javascript",
          })
        )
      );

      worker.onmessage = (e) => this.handleWorkerMessage(e, i);
      worker.onerror = (e) => console.error(`Worker ${i} error:`, e);

      this.workers.push({
        worker,
        id: i,
        busy: false,
        currentFrame: null,
      });
    }

    console.log(`Initialized ${this.maxWorkers} parallel workers`);
  }

  /**
   * Start parallel rendering process
   */
  async renderVideoParallel(
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
      // Initialize workers if not already done
      if (this.workers.length === 0) {
        await this.initializeWorkers();
      }

      // Setup rendering parameters
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

      progressCallback(0, "Initializing parallel rendering...");

      // Create frame processing queue
      this.frameQueue = [];
      this.completedFrames.clear();

      for (let i = 0; i < totalFrames; i++) {
        this.frameQueue.push({
          index: i,
          timestamp: i * frameInterval,
          width,
          height,
          effects: { ...this.app.effects },
          subtitles: [...this.app.subtitles],
          wordSegments: [...this.app.wordSegments],
        });
      }

      progressCallback(
        5,
        `Processing ${totalFrames} frames with ${this.maxWorkers} workers...`
      );

      // Start parallel processing
      await this.processFramesInParallel(progressCallback);

      progressCallback(85, "Assembling video from parallel frames...");

      // Assemble final video
      const videoBlob = await this.assembleParallelFrames(
        frameRate,
        quality,
        format,
        (progress) => {
          progressCallback(85 + progress * 0.15, "Encoding final video...");
        }
      );

      // Download result
      this.app.downloadVideo(videoBlob);

      const renderTime = (performance.now() - this.stats.startTime) / 1000;
      const speedup = duration / renderTime;

      progressCallback(
        100,
        `Parallel render complete! ${speedup.toFixed(1)}x faster than real-time`
      );

      return videoBlob;
    } finally {
      this.isRendering = false;
    }
  }

  /**
   * Process frames using all available workers simultaneously
   */
  async processFramesInParallel(progressCallback) {
    return new Promise((resolve, reject) => {
      let activeWorkers = 0;
      let queueIndex = 0;

      const assignNextFrame = (workerIndex) => {
        if (queueIndex >= this.frameQueue.length) {
          // No more frames to process
          if (activeWorkers === 0) {
            resolve();
          }
          return;
        }

        const frame = this.frameQueue[queueIndex++];
        const worker = this.workers[workerIndex];

        worker.busy = true;
        worker.currentFrame = frame;
        activeWorkers++;

        // Send frame data to worker
        worker.worker.postMessage({
          type: "RENDER_FRAME",
          frame: frame,
        });
      };

      // Handle worker completion
      this.onWorkerComplete = (workerIndex, result) => {
        const worker = this.workers[workerIndex];

        if (result.success) {
          this.completedFrames.set(result.frameIndex, result.imageData);
          this.stats.processedFrames++;

          // Update progress
          const progress =
            5 + (this.stats.processedFrames / this.stats.totalFrames) * 80;
          const eta = this.calculateETA();
          progressCallback(
            progress,
            `Frame ${this.stats.processedFrames}/${this.stats.totalFrames} (ETA: ${eta}s)`
          );
        } else {
          console.error(`Worker ${workerIndex} failed:`, result.error);
        }

        worker.busy = false;
        worker.currentFrame = null;
        activeWorkers--;

        // Assign next frame or finish
        assignNextFrame(workerIndex);
      };

      // Start all workers
      for (let i = 0; i < this.maxWorkers; i++) {
        assignNextFrame(i);
      }
    });
  }

  /**
   * Handle messages from Web Workers
   */
  handleWorkerMessage(event, workerIndex) {
    const { type, ...data } = event.data;

    switch (type) {
      case "FRAME_COMPLETE":
        this.onWorkerComplete(workerIndex, data);
        break;
      case "WORKER_ERROR":
        console.error(`Worker ${workerIndex} error:`, data.error);
        break;
      default:
        console.warn(`Unknown worker message type: ${type}`);
    }
  }

  /**
   * Calculate estimated time to completion
   */
  calculateETA() {
    if (this.stats.processedFrames === 0) return "∞";

    const elapsed = (performance.now() - this.stats.startTime) / 1000;
    const rate = this.stats.processedFrames / elapsed;
    const remaining = this.stats.totalFrames - this.stats.processedFrames;

    return Math.ceil(remaining / rate);
  }

  /**
   * Assemble frames into final video
   */
  async assembleParallelFrames(frameRate, quality, format, progressCallback) {
    // Create temporary canvas for video assembly
    const canvas = document.createElement("canvas");
    const firstFrame = this.completedFrames.get(0);

    if (!firstFrame) {
      throw new Error("No frames were successfully rendered");
    }

    // Set canvas dimensions from first frame
    canvas.width = firstFrame.width;
    canvas.height = firstFrame.height;

    const ctx = canvas.getContext("2d");
    const stream = canvas.captureStream(frameRate);

    // Setup MediaRecorder
    const qualitySettings = {
      high: { videoBitsPerSecond: 8000000 },
      medium: { videoBitsPerSecond: 4000000 },
      low: { videoBitsPerSecond: 2000000 },
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

    // Start recording
    mediaRecorder.start();

    // Play frames in sequence
    const frameInterval = 1000 / frameRate; // ms per frame
    let frameIndex = 0;

    return new Promise((resolve, reject) => {
      mediaRecorder.onstop = () => {
        const blob = new Blob(chunks, { type: mimeType });
        resolve(blob);
      };

      const playNextFrame = () => {
        if (frameIndex >= this.stats.totalFrames) {
          mediaRecorder.stop();
          return;
        }

        const frameData = this.completedFrames.get(frameIndex);
        if (frameData) {
          // Draw frame to canvas
          const imageData = new ImageData(
            new Uint8ClampedArray(frameData.data),
            frameData.width,
            frameData.height
          );
          ctx.putImageData(imageData, 0, 0);
        }

        frameIndex++;
        progressCallback(frameIndex / this.stats.totalFrames);

        setTimeout(playNextFrame, frameInterval);
      };

      playNextFrame();
    });
  }

  /**
   * Get supported video format for the browser
   */
  getSupportedVideoFormat(preferredFormat) {
    const formats = [
      "video/webm;codecs=vp9",
      "video/webm;codecs=vp8",
      "video/mp4;codecs=h264",
      "video/webm",
    ];

    for (const format of formats) {
      if (MediaRecorder.isTypeSupported(format)) {
        return format;
      }
    }

    return "video/webm"; // Fallback
  }

  /**
   * Web Worker code for parallel frame rendering
   */
  getWorkerCode() {
    return `
      // Web Worker for parallel frame rendering
      class FrameRenderer {
        constructor() {
          this.canvas = new OffscreenCanvas(1920, 1080);
          this.ctx = this.canvas.getContext('2d');
        }

        async renderFrame(frameData) {
          try {
            // Set canvas size
            this.canvas.width = frameData.width;
            this.canvas.height = frameData.height;

            // Clear canvas
            this.ctx.fillStyle = '#000000';
            this.ctx.fillRect(0, 0, frameData.width, frameData.height);

            // Render karaoke effects for this timestamp
            await this.renderKaraokeEffects(frameData);

            // Get image data
            const imageData = this.ctx.getImageData(0, 0, frameData.width, frameData.height);

            return {
              success: true,
              frameIndex: frameData.index,
              imageData: {
                data: Array.from(imageData.data),
                width: imageData.width,
                height: imageData.height
              }
            };

          } catch (error) {
            return {
              success: false,
              frameIndex: frameData.index,
              error: error.message
            };
          }
        }

        async renderKaraokeEffects(frameData) {
          const { timestamp, effects, subtitles, wordSegments } = frameData;

          // Find active subtitle
          const activeSubtitle = subtitles.find(sub => 
            timestamp >= sub.start_time && timestamp <= sub.end_time
          );

          if (!activeSubtitle) return;

          // Get words for this subtitle
          const words = wordSegments.filter(word =>
            word.start_time >= activeSubtitle.start_time &&
            word.end_time <= activeSubtitle.end_time
          );

          // Setup text rendering
          this.ctx.font = \`\${effects.fontWeight} \${effects.fontSize}px \${effects.fontFamily}\`;
          this.ctx.textAlign = 'left';
          this.ctx.textBaseline = 'middle';

          // Calculate position
          const centerX = effects.positionX;
          const baseY = effects.positionY;

          // Render words with karaoke effects
          this.renderWordsWithEffects(words, centerX, baseY, timestamp, effects);
        }

        renderWordsWithEffects(words, centerX, baseY, currentTime, effects) {
          if (words.length === 0) return;

          // Calculate total width for centering
          const wordWidths = words.map(word => this.ctx.measureText(word.word).width);
          const totalSpacing = (words.length - 1) * effects.wordSpacing;
          const totalWidth = wordWidths.reduce((sum, width) => sum + width, 0) + totalSpacing;

          let currentX = centerX - totalWidth / 2;

          // Render each word
          words.forEach((word, index) => {
            const progress = this.getWordProgress(word, currentTime, effects.animationSpeed);
            
            // Apply karaoke effect based on mode
            switch (effects.karaokeMode) {
              case 'highlight':
                this.renderHighlightMode(word, currentX, baseY, progress, effects);
                break;
              case 'gradient':
                this.renderGradientMode(word, currentX, baseY, progress, effects);
                break;
              case 'fill':
                this.renderFillMode(word, currentX, baseY, progress, effects);
                break;
              case 'bounce':
                this.renderBounceMode(word, currentX, baseY, progress, effects);
                break;
            }

            currentX += wordWidths[index] + effects.wordSpacing;
          });
        }

        getWordProgress(wordData, currentTime, animationSpeed) {
          if (currentTime < wordData.start_time) return 0;
          if (currentTime > wordData.end_time) return 1;

          const duration = wordData.end_time - wordData.start_time;
          const elapsed = currentTime - wordData.start_time;
          return Math.min(1, (elapsed / duration) * animationSpeed);
        }

        renderHighlightMode(wordData, x, y, progress, effects) {
          const isHighlighted = progress > 0 && progress < 1;
          const color = isHighlighted ? effects.highlightColor : effects.primaryColor;

          this.ctx.fillStyle = color;
          this.ctx.fillText(wordData.word, x, y);
        }

        renderGradientMode(wordData, x, y, progress, effects) {
          const primary = this.hexToRgb(effects.primaryColor);
          const highlight = this.hexToRgb(effects.highlightColor);

          const r = Math.round(primary.r + (highlight.r - primary.r) * progress);
          const g = Math.round(primary.g + (highlight.g - primary.g) * progress);
          const b = Math.round(primary.b + (highlight.b - primary.b) * progress);

          this.ctx.fillStyle = \`rgb(\${r}, \${g}, \${b})\`;
          this.ctx.fillText(wordData.word, x, y);
        }

        renderFillMode(wordData, x, y, progress, effects) {
          const wordWidth = this.ctx.measureText(wordData.word).width;

          // Draw unfilled part
          this.ctx.fillStyle = effects.primaryColor;
          this.ctx.fillText(wordData.word, x, y);

          // Draw filled part
          if (progress > 0) {
            this.ctx.save();
            this.ctx.beginPath();
            this.ctx.rect(x, y - effects.fontSize / 2, wordWidth * progress, effects.fontSize);
            this.ctx.clip();

            this.ctx.fillStyle = effects.highlightColor;
            this.ctx.fillText(wordData.word, x, y);
            this.ctx.restore();
          }
        }

        renderBounceMode(wordData, x, y, progress, effects) {
          const bounceHeight = progress > 0 ? Math.sin(progress * Math.PI) * 20 : 0;
          const scale = progress > 0 ? 1 + Math.sin(progress * Math.PI) * 0.3 : 1;

          this.ctx.save();
          
          const wordWidth = this.ctx.measureText(wordData.word).width;
          this.ctx.translate(x + wordWidth / 2, y - bounceHeight);
          this.ctx.scale(scale, scale);
          this.ctx.translate(-wordWidth / 2, 0);

          const color = progress > 0 ? effects.highlightColor : effects.primaryColor;
          this.ctx.fillStyle = color;
          this.ctx.fillText(wordData.word, 0, 0);
          
          this.ctx.restore();
        }

        hexToRgb(hex) {
          const result = /^#?([a-f\\d]{2})([a-f\\d]{2})([a-f\\d]{2})$/i.exec(hex);
          return result ? {
            r: parseInt(result[1], 16),
            g: parseInt(result[2], 16),
            b: parseInt(result[3], 16)
          } : { r: 255, g: 255, b: 255 };
        }
      }

      // Worker message handler
      const renderer = new FrameRenderer();

      self.onmessage = async function(e) {
        const { type, frame } = e.data;

        if (type === 'RENDER_FRAME') {
          const result = await renderer.renderFrame(frame);
          self.postMessage({
            type: 'FRAME_COMPLETE',
            ...result
          });
        }
      };
    `;
  }

  /**
   * Cleanup workers and resources
   */
  cleanup() {
    this.workers.forEach(({ worker }) => {
      worker.terminate();
    });
    this.workers = [];
    this.frameQueue = [];
    this.completedFrames.clear();
    this.isRendering = false;
  }
}

// Export for use in main application
if (typeof module !== "undefined" && module.exports) {
  module.exports = ParallelRenderer;
} else if (typeof window !== "undefined") {
  window.ParallelRenderer = ParallelRenderer;
}
