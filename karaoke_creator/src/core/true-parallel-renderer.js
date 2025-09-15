/**
 * True Parallel Karaoke Renderer
 * Uses Web Workers for genuine simultaneous processing
 */

class TrueParallelRenderer {
  constructor(karaokeApp) {
    this.app = karaokeApp;
    this.workers = [];
    this.maxWorkers = Math.min(navigator.hardwareConcurrency || 2, 4);
    this.isRendering = false;
    this.completedFrames = new Map();
    this.totalFrames = 0;
    this.processedFrames = 0;
  }

  /**
   * Render video with true parallel processing
   */
  async renderVideoTrueParallel(
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

      this.totalFrames = totalFrames;
      this.processedFrames = 0;
      this.completedFrames.clear();

      progressCallback(
        0,
        `Initializing ${this.maxWorkers} parallel workers...`
      );

      // Initialize Web Workers
      await this.initializeWorkers();

      progressCallback(
        5,
        `Processing ${totalFrames} frames in true parallel...`
      );

      // Create frame processing queue
      const frameQueue = [];
      for (let i = 0; i < totalFrames; i++) {
        frameQueue.push({
          index: i,
          timestamp: i * frameInterval,
          width,
          height,
          effects: { ...this.app.effects },
          subtitles: [...this.app.subtitles],
          wordSegments: [...this.app.wordSegments],
        });
      }

      // Process frames in parallel using Web Workers
      await this.processFramesInParallel(frameQueue, progressCallback);

      progressCallback(85, "Assembling parallel-processed video...");

      // Assemble final video from parallel results
      const videoBlob = await this.assembleParallelVideo(
        frameRate,
        quality,
        format,
        (progress) => {
          progressCallback(85 + progress * 0.15, "Encoding final video...");
        }
      );

      // Download result
      this.app.downloadVideo(videoBlob);

      progressCallback(
        100,
        `True parallel render complete! ${this.maxWorkers} workers processed ${totalFrames} frames`
      );

      return videoBlob;
    } finally {
      this.cleanup();
      this.isRendering = false;
    }
  }

  /**
   * Initialize Web Workers for parallel processing
   */
  async initializeWorkers() {
    // Terminate existing workers
    this.cleanup();

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
   * Process frames using all workers in parallel
   */
  async processFramesInParallel(frameQueue, progressCallback) {
    return new Promise((resolve, reject) => {
      let queueIndex = 0;
      let activeWorkers = 0;

      const assignNextFrame = (workerIndex) => {
        if (queueIndex >= frameQueue.length) {
          // No more frames to process
          if (activeWorkers === 0) {
            resolve();
          }
          return;
        }

        const frame = frameQueue[queueIndex++];
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
          this.completedFrames.set(result.frameIndex, result.frameData);
          this.processedFrames++;

          // Update progress
          const progress = 5 + (this.processedFrames / this.totalFrames) * 80;
          progressCallback(
            progress,
            `Parallel processing: ${this.processedFrames}/${
              this.totalFrames
            } frames (Worker ${workerIndex + 1})`
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
   * Assemble video from parallel-processed frames
   */
  async assembleParallelVideo(frameRate, quality, format, progressCallback) {
    // Create canvas for video assembly
    const canvas = document.createElement("canvas");
    const firstFrame = this.completedFrames.get(0);

    if (!firstFrame) {
      throw new Error("No frames were successfully processed");
    }

    canvas.width = firstFrame.width;
    canvas.height = firstFrame.height;
    const ctx = canvas.getContext("2d");

    // Setup MediaRecorder
    const stream = canvas.captureStream(frameRate);
    const qualitySettings = {
      high: { videoBitsPerSecond: 6000000 },
      medium: { videoBitsPerSecond: 3000000 },
      low: { videoBitsPerSecond: 1500000 },
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
    const frameInterval = 1000 / frameRate;
    let frameIndex = 0;

    return new Promise((resolve, reject) => {
      mediaRecorder.onstop = () => {
        const blob = new Blob(chunks, { type: mimeType });
        resolve(blob);
      };

      const playNextFrame = () => {
        if (frameIndex >= this.totalFrames) {
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
        progressCallback(frameIndex / this.totalFrames);

        setTimeout(playNextFrame, frameInterval);
      };

      playNextFrame();
    });
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
   * Web Worker code for parallel frame rendering
   */
  getWorkerCode() {
    return `
      // Web Worker for true parallel frame rendering
      class ParallelFrameRenderer {
        constructor() {
          this.canvas = new OffscreenCanvas(1920, 1080);
          this.ctx = this.canvas.getContext('2d');
        }

        async renderFrame(frameData) {
          try {
            // Set canvas size
            this.canvas.width = frameData.width;
            this.canvas.height = frameData.height;

            // Clear canvas with black background
            this.ctx.fillStyle = '#000000';
            this.ctx.fillRect(0, 0, frameData.width, frameData.height);

            // Render karaoke effects for this timestamp
            await this.renderKaraokeEffects(frameData);

            // Get image data
            const imageData = this.ctx.getImageData(0, 0, frameData.width, frameData.height);

            return {
              success: true,
              frameIndex: frameData.index,
              frameData: {
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

          if (words.length === 0) return;

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
          // Calculate total width for centering
          const wordWidths = words.map(word => this.ctx.measureText(word.word).width);
          const totalSpacing = (words.length - 1) * effects.wordSpacing;
          const totalWidth = wordWidths.reduce((sum, width) => sum + width, 0) + totalSpacing;

          let currentX = centerX - totalWidth / 2;

          // Render each word
          words.forEach((word, index) => {
            const progress = this.getWordProgress(word, currentTime, effects.animationSpeed);
            
            // Apply karaoke effect based on mode
            let color;
            switch (effects.karaokeMode) {
              case 'highlight':
                const isHighlighted = progress > 0 && progress < 1;
                color = isHighlighted ? effects.highlightColor : effects.primaryColor;
                break;
              case 'gradient':
                const primary = this.hexToRgb(effects.primaryColor);
                const highlight = this.hexToRgb(effects.highlightColor);
                const r = Math.round(primary.r + (highlight.r - primary.r) * progress);
                const g = Math.round(primary.g + (highlight.g - primary.g) * progress);
                const b = Math.round(primary.b + (highlight.b - primary.b) * progress);
                color = \`rgb(\${r}, \${g}, \${b})\`;
                break;
              default:
                color = effects.primaryColor;
            }

            this.ctx.fillStyle = color;
            this.ctx.fillText(word.word, currentX, baseY);

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
      const renderer = new ParallelFrameRenderer();

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
    this.completedFrames.clear();
    this.isRendering = false;
  }
}

// Export for use in main application
if (typeof module !== "undefined" && module.exports) {
  module.exports = TrueParallelRenderer;
} else if (typeof window !== "undefined") {
  window.TrueParallelRenderer = TrueParallelRenderer;
}
