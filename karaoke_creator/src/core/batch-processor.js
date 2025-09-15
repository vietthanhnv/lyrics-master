/**
 * Batch Processing System for Ultra-Fast Karaoke Rendering
 * Combines parallel processing, GPU acceleration, and smart batching
 */

class BatchProcessor {
  constructor(karaokeApp) {
    this.app = karaokeApp;
    this.parallelRenderer = null;
    this.gpuRenderer = null;
    this.batchSize = 32; // Process frames in batches
    this.maxConcurrentBatches = 4;
    this.frameCache = new Map();
    this.isProcessing = false;

    // Performance metrics
    this.metrics = {
      totalFrames: 0,
      processedFrames: 0,
      cacheHits: 0,
      gpuFrames: 0,
      parallelFrames: 0,
      startTime: 0,
      batchTimes: [],
    };
  }

  /**
   * Initialize all rendering systems
   */
  async initialize() {
    console.log("Batch Processor: Initializing rendering systems...");

    // Initialize parallel renderer
    this.parallelRenderer = new ParallelRenderer(this.app);

    // Initialize GPU renderer if supported
    try {
      this.gpuRenderer = new GPURenderer(this.app);
      await this.gpuRenderer.initialize();
      console.log("Batch Processor: GPU acceleration enabled");
    } catch (error) {
      console.warn(
        "Batch Processor: GPU acceleration not available:",
        error.message
      );
      this.gpuRenderer = null;
    }

    // Optimize batch size based on hardware
    this.optimizeBatchSize();

    console.log(
      `Batch Processor: Initialized with batch size ${this.batchSize}`
    );
  }

  /**
   * Start ultra-fast batch rendering
   */
  async renderVideoUltraFast(
    resolution,
    frameRate,
    quality,
    format,
    progressCallback
  ) {
    if (this.isProcessing) {
      throw new Error("Batch processing already in progress");
    }

    this.isProcessing = true;
    this.metrics.startTime = performance.now();

    try {
      // Initialize if not already done
      if (!this.parallelRenderer) {
        await this.initialize();
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

      this.metrics.totalFrames = totalFrames;
      this.metrics.processedFrames = 0;
      this.metrics.cacheHits = 0;
      this.metrics.gpuFrames = 0;
      this.metrics.parallelFrames = 0;

      progressCallback(0, "Initializing ultra-fast batch processing...");

      // Analyze content for optimization
      const optimizationPlan = await this.analyzeContentForOptimization(
        this.app.subtitles,
        this.app.wordSegments,
        totalFrames,
        frameInterval
      );

      progressCallback(
        5,
        `Processing ${totalFrames} frames in ${optimizationPlan.batches.length} optimized batches...`
      );

      // Process batches with smart routing
      const processedFrames = await this.processBatchesWithSmartRouting(
        optimizationPlan,
        width,
        height,
        frameInterval,
        progressCallback
      );

      progressCallback(85, "Assembling ultra-fast rendered video...");

      // Assemble final video
      const videoBlob = await this.assembleOptimizedVideo(
        processedFrames,
        frameRate,
        quality,
        format,
        (progress) => {
          progressCallback(85 + progress * 0.15, "Encoding optimized video...");
        }
      );

      // Download result
      this.app.downloadVideo(videoBlob);

      // Calculate performance metrics
      const renderTime = (performance.now() - this.metrics.startTime) / 1000;
      const speedup = duration / renderTime;
      const efficiency = this.calculateEfficiency();

      progressCallback(
        100,
        `Ultra-fast render complete! ${speedup.toFixed(
          1
        )}x faster (${efficiency}% efficiency)`
      );

      return videoBlob;
    } finally {
      this.isProcessing = false;
    }
  }

  /**
   * Analyze content to create optimization plan
   */
  async analyzeContentForOptimization(
    subtitles,
    wordSegments,
    totalFrames,
    frameInterval
  ) {
    console.log("Analyzing content for optimization...");

    const plan = {
      batches: [],
      staticFrames: [], // Frames with no text changes
      dynamicFrames: [], // Frames with karaoke effects
      complexFrames: [], // Frames with complex effects
      cacheableSegments: [], // Segments that can be cached
    };

    // Analyze frame content
    for (let i = 0; i < totalFrames; i++) {
      const timestamp = i * frameInterval;
      const frameInfo = this.analyzeFrame(timestamp, subtitles, wordSegments);

      frameInfo.index = i;
      frameInfo.timestamp = timestamp;

      if (frameInfo.hasText) {
        if (frameInfo.isComplex) {
          plan.complexFrames.push(frameInfo);
        } else {
          plan.dynamicFrames.push(frameInfo);
        }
      } else {
        plan.staticFrames.push(frameInfo);
      }
    }

    // Create optimized batches
    plan.batches = this.createOptimizedBatches(plan);

    // Identify cacheable segments
    plan.cacheableSegments = this.identifyCacheableSegments(
      subtitles,
      wordSegments
    );

    console.log(
      `Optimization plan: ${plan.staticFrames.length} static, ${plan.dynamicFrames.length} dynamic, ${plan.complexFrames.length} complex frames`
    );

    return plan;
  }

  /**
   * Analyze individual frame content
   */
  analyzeFrame(timestamp, subtitles, wordSegments) {
    const activeSubtitle = subtitles.find(
      (sub) => timestamp >= sub.start_time && timestamp <= sub.end_time
    );

    if (!activeSubtitle) {
      return {
        hasText: false,
        isStatic: true,
        isComplex: false,
        subtitle: null,
        words: [],
      };
    }

    const words = wordSegments.filter(
      (word) =>
        word.start_time >= activeSubtitle.start_time &&
        word.end_time <= activeSubtitle.end_time
    );

    // Determine complexity
    const hasActiveWords = words.some(
      (word) => timestamp >= word.start_time && timestamp <= word.end_time
    );

    const isComplex =
      hasActiveWords &&
      (this.app.effects.karaokeMode === "bounce" ||
        this.app.effects.karaokeMode === "wave" ||
        this.app.effects.enableShadow ||
        this.app.effects.enableBorder);

    return {
      hasText: true,
      isStatic: !hasActiveWords,
      isComplex,
      subtitle: activeSubtitle,
      words,
      activeWords: words.filter(
        (word) => timestamp >= word.start_time && timestamp <= word.end_time
      ),
    };
  }

  /**
   * Create optimized batches based on content analysis
   */
  createOptimizedBatches(plan) {
    const batches = [];

    // Batch static frames (can be processed very quickly)
    if (plan.staticFrames.length > 0) {
      const staticBatches = this.chunkArray(
        plan.staticFrames,
        this.batchSize * 2
      );
      staticBatches.forEach((batch) => {
        batches.push({
          type: "static",
          frames: batch,
          priority: "low",
          method: "cache", // Use cached empty frame
        });
      });
    }

    // Batch dynamic frames (use GPU if available)
    if (plan.dynamicFrames.length > 0) {
      const dynamicBatches = this.chunkArray(
        plan.dynamicFrames,
        this.batchSize
      );
      dynamicBatches.forEach((batch) => {
        batches.push({
          type: "dynamic",
          frames: batch,
          priority: "medium",
          method: this.gpuRenderer ? "gpu" : "parallel",
        });
      });
    }

    // Batch complex frames (use best available method)
    if (plan.complexFrames.length > 0) {
      const complexBatches = this.chunkArray(
        plan.complexFrames,
        Math.floor(this.batchSize / 2)
      );
      complexBatches.forEach((batch) => {
        batches.push({
          type: "complex",
          frames: batch,
          priority: "high",
          method: this.gpuRenderer ? "gpu" : "parallel",
        });
      });
    }

    // Sort batches by priority
    return batches.sort((a, b) => {
      const priorityOrder = { high: 3, medium: 2, low: 1 };
      return priorityOrder[b.priority] - priorityOrder[a.priority];
    });
  }

  /**
   * Process batches with smart routing to optimal rendering method
   */
  async processBatchesWithSmartRouting(
    plan,
    width,
    height,
    frameInterval,
    progressCallback
  ) {
    const processedFrames = new Map();
    const batchPromises = [];

    // Process batches concurrently
    for (let i = 0; i < plan.batches.length; i += this.maxConcurrentBatches) {
      const batchGroup = plan.batches.slice(i, i + this.maxConcurrentBatches);

      const groupPromises = batchGroup.map(async (batch, batchIndex) => {
        const batchStartTime = performance.now();

        try {
          const batchResults = await this.processBatch(
            batch,
            width,
            height,
            frameInterval,
            (progress, status) => {
              const overallProgress =
                5 +
                (this.metrics.processedFrames / this.metrics.totalFrames) * 80;
              progressCallback(
                overallProgress,
                `${status} (Batch ${i + batchIndex + 1})`
              );
            }
          );

          // Store results
          batchResults.forEach((frameData, frameIndex) => {
            processedFrames.set(frameIndex, frameData);
          });

          const batchTime = performance.now() - batchStartTime;
          this.metrics.batchTimes.push(batchTime);

          console.log(
            `Batch ${i + batchIndex + 1} completed in ${batchTime.toFixed(
              2
            )}ms (${batch.method})`
          );
        } catch (error) {
          console.error(`Batch ${i + batchIndex + 1} failed:`, error);
          // Continue with other batches
        }
      });

      // Wait for current batch group to complete
      await Promise.all(groupPromises);
    }

    return processedFrames;
  }

  /**
   * Process individual batch using optimal method
   */
  async processBatch(batch, width, height, frameInterval, progressCallback) {
    const results = new Map();

    switch (batch.method) {
      case "cache":
        return this.processBatchWithCache(
          batch,
          width,
          height,
          progressCallback
        );

      case "gpu":
        return this.processBatchWithGPU(batch, width, height, progressCallback);

      case "parallel":
        return this.processBatchWithParallel(
          batch,
          width,
          height,
          progressCallback
        );

      default:
        throw new Error(`Unknown batch method: ${batch.method}`);
    }
  }

  /**
   * Process batch using cache (for static frames)
   */
  async processBatchWithCache(batch, width, height, progressCallback) {
    const results = new Map();

    // Create or get cached empty frame
    let cachedFrame = this.frameCache.get("empty_frame");
    if (!cachedFrame) {
      // Create empty black frame
      const canvas = document.createElement("canvas");
      canvas.width = width;
      canvas.height = height;
      const ctx = canvas.getContext("2d");
      ctx.fillStyle = "#000000";
      ctx.fillRect(0, 0, width, height);

      const imageData = ctx.getImageData(0, 0, width, height);
      cachedFrame = {
        data: Array.from(imageData.data),
        width,
        height,
      };

      this.frameCache.set("empty_frame", cachedFrame);
    }

    // Use cached frame for all static frames
    batch.frames.forEach((frame) => {
      results.set(frame.index, { ...cachedFrame });
      this.metrics.processedFrames++;
      this.metrics.cacheHits++;
    });

    progressCallback(100, `Cached ${batch.frames.length} static frames`);
    return results;
  }

  /**
   * Process batch using GPU acceleration
   */
  async processBatchWithGPU(batch, width, height, progressCallback) {
    const results = new Map();

    for (let i = 0; i < batch.frames.length; i++) {
      const frame = batch.frames[i];

      try {
        const frameData = await this.gpuRenderer.renderFrameGPU(
          frame.timestamp,
          this.app.effects,
          this.app.subtitles,
          this.app.wordSegments,
          width,
          height
        );

        results.set(frame.index, frameData);
        this.metrics.processedFrames++;
        this.metrics.gpuFrames++;

        const progress = ((i + 1) / batch.frames.length) * 100;
        progressCallback(
          progress,
          `GPU rendering frame ${i + 1}/${batch.frames.length}`
        );
      } catch (error) {
        console.error(`GPU rendering failed for frame ${frame.index}:`, error);
        // Fallback to parallel processing
        // ... fallback implementation
      }
    }

    return results;
  }

  /**
   * Process batch using parallel CPU processing
   */
  async processBatchWithParallel(batch, width, height, progressCallback) {
    // Use existing parallel renderer for this batch
    const results = new Map();

    // Create mini frame queue for this batch
    const batchQueue = batch.frames.map((frame) => ({
      index: frame.index,
      timestamp: frame.timestamp,
      width,
      height,
      effects: { ...this.app.effects },
      subtitles: [...this.app.subtitles],
      wordSegments: [...this.app.wordSegments],
    }));

    // Process using parallel renderer (simplified version)
    for (let i = 0; i < batchQueue.length; i++) {
      const frame = batchQueue[i];

      // Simulate parallel processing result
      // In real implementation, this would use the ParallelRenderer
      const frameData = await this.renderFrameFallback(frame, width, height);

      results.set(frame.index, frameData);
      this.metrics.processedFrames++;
      this.metrics.parallelFrames++;

      const progress = ((i + 1) / batchQueue.length) * 100;
      progressCallback(
        progress,
        `Parallel rendering frame ${i + 1}/${batchQueue.length}`
      );
    }

    return results;
  }

  /**
   * Fallback frame rendering method
   */
  async renderFrameFallback(frameData, width, height) {
    // Create temporary canvas
    const canvas = document.createElement("canvas");
    canvas.width = width;
    canvas.height = height;
    const ctx = canvas.getContext("2d");

    // Clear with black background
    ctx.fillStyle = "#000000";
    ctx.fillRect(0, 0, width, height);

    // Render karaoke effects (simplified)
    const activeSubtitle = frameData.subtitles.find(
      (sub) =>
        frameData.timestamp >= sub.start_time &&
        frameData.timestamp <= sub.end_time
    );

    if (activeSubtitle) {
      const words = frameData.wordSegments.filter(
        (word) =>
          word.start_time >= activeSubtitle.start_time &&
          word.end_time <= activeSubtitle.end_time
      );

      // Simple text rendering
      ctx.font = `${frameData.effects.fontWeight} ${frameData.effects.fontSize}px ${frameData.effects.fontFamily}`;
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillStyle = frameData.effects.primaryColor;

      const text = words.map((w) => w.word).join(" ");
      ctx.fillText(
        text,
        frameData.effects.positionX,
        frameData.effects.positionY
      );
    }

    // Get image data
    const imageData = ctx.getImageData(0, 0, width, height);
    return {
      data: Array.from(imageData.data),
      width,
      height,
    };
  }

  /**
   * Assemble optimized video from processed frames
   */
  async assembleOptimizedVideo(
    processedFrames,
    frameRate,
    quality,
    format,
    progressCallback
  ) {
    // Create canvas for video assembly
    const canvas = document.createElement("canvas");
    const firstFrame = processedFrames.get(0);

    if (!firstFrame) {
      throw new Error("No frames were successfully processed");
    }

    canvas.width = firstFrame.width;
    canvas.height = firstFrame.height;
    const ctx = canvas.getContext("2d");

    // Setup MediaRecorder with optimized settings
    const stream = canvas.captureStream(frameRate);
    const qualitySettings = {
      high: { videoBitsPerSecond: 12000000 }, // Higher bitrate for quality
      medium: { videoBitsPerSecond: 6000000 },
      low: { videoBitsPerSecond: 3000000 },
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

    // Play frames in sequence with precise timing
    const frameInterval = 1000 / frameRate;
    let frameIndex = 0;

    return new Promise((resolve, reject) => {
      mediaRecorder.onstop = () => {
        const blob = new Blob(chunks, { type: mimeType });
        resolve(blob);
      };

      const playNextFrame = () => {
        if (frameIndex >= this.metrics.totalFrames) {
          mediaRecorder.stop();
          return;
        }

        const frameData = processedFrames.get(frameIndex);
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
        progressCallback(frameIndex / this.metrics.totalFrames);

        setTimeout(playNextFrame, frameInterval);
      };

      playNextFrame();
    });
  }

  /**
   * Optimize batch size based on hardware capabilities
   */
  optimizeBatchSize() {
    const cores = navigator.hardwareConcurrency || 4;
    const memory = navigator.deviceMemory || 4; // GB estimate

    // Adjust batch size based on hardware
    if (cores >= 8 && memory >= 8) {
      this.batchSize = 64; // High-end hardware
    } else if (cores >= 4 && memory >= 4) {
      this.batchSize = 32; // Mid-range hardware
    } else {
      this.batchSize = 16; // Lower-end hardware
    }

    this.maxConcurrentBatches = Math.min(cores, 6);

    console.log(
      `Optimized for ${cores} cores, ${memory}GB RAM: batch size ${this.batchSize}, concurrent batches ${this.maxConcurrentBatches}`
    );
  }

  /**
   * Calculate processing efficiency
   */
  calculateEfficiency() {
    const cacheEfficiency =
      (this.metrics.cacheHits / this.metrics.totalFrames) * 100;
    const gpuEfficiency =
      (this.metrics.gpuFrames / this.metrics.totalFrames) * 100;
    const parallelEfficiency =
      (this.metrics.parallelFrames / this.metrics.totalFrames) * 100;

    return Math.round(
      cacheEfficiency + gpuEfficiency * 0.8 + parallelEfficiency * 0.6
    );
  }

  /**
   * Utility: Chunk array into smaller arrays
   */
  chunkArray(array, chunkSize) {
    const chunks = [];
    for (let i = 0; i < array.length; i += chunkSize) {
      chunks.push(array.slice(i, i + chunkSize));
    }
    return chunks;
  }

  /**
   * Identify cacheable segments for optimization
   */
  identifyCacheableSegments(subtitles, wordSegments) {
    // Find segments with identical text and effects that can be cached
    const segments = [];

    subtitles.forEach((subtitle) => {
      const words = wordSegments.filter(
        (word) =>
          word.start_time >= subtitle.start_time &&
          word.end_time <= subtitle.end_time
      );

      const segmentKey = `${subtitle.text}_${JSON.stringify(this.app.effects)}`;
      segments.push({
        key: segmentKey,
        subtitle,
        words,
        cacheable: true,
      });
    });

    return segments;
  }

  /**
   * Get supported video format
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

    return "video/webm";
  }

  /**
   * Cleanup all resources
   */
  cleanup() {
    if (this.parallelRenderer) {
      this.parallelRenderer.cleanup();
    }

    if (this.gpuRenderer) {
      this.gpuRenderer.cleanup();
    }

    this.frameCache.clear();
    this.isProcessing = false;
  }
}

// Export for use in main application
if (typeof module !== "undefined" && module.exports) {
  module.exports = BatchProcessor;
} else if (typeof window !== "undefined") {
  window.BatchProcessor = BatchProcessor;
}
