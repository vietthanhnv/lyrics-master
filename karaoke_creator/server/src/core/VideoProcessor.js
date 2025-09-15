/**
 * Video Processor - Handles video analysis and rendering with file-based streaming
 */

const { createCanvas, loadImage, registerFont } = require("canvas");
const ffmpeg = require("fluent-ffmpeg");
const ffmpegStatic = require("ffmpeg-static");
const fs = require("fs-extra");
const path = require("path");
const { v4: uuidv4 } = require("uuid");
const UnifiedTextRenderer = require("../../../src/core/UnifiedTextRenderer");

// Set FFmpeg path
ffmpeg.setFfmpegPath(ffmpegStatic);

class VideoProcessor {
  constructor() {
    this.tempDir = path.join(__dirname, "../../temp");
    this.outputDir = path.join(__dirname, "../../downloads");
    this.fontsDir = path.join(__dirname, "../../fonts");
    this.registeredFonts = new Map(); // Track registered fonts

    // Ensure directories exist
    fs.ensureDirSync(this.tempDir);
    fs.ensureDirSync(this.outputDir);
    fs.ensureDirSync(this.fontsDir);

    // Register default system fonts
    this.registerDefaultFonts();
  }

  /**
   * Register default system fonts for server rendering
   */
  registerDefaultFonts() {
    // Try to register common system fonts
    const systemFonts = [
      {
        name: "Arial",
        paths: [
          "C:/Windows/Fonts/arial.ttf",
          "/System/Library/Fonts/Arial.ttf",
          "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ],
      },
      {
        name: "Times New Roman",
        paths: [
          "C:/Windows/Fonts/times.ttf",
          "/System/Library/Fonts/Times.ttc",
        ],
      },
      {
        name: "Helvetica",
        paths: [
          "/System/Library/Fonts/Helvetica.ttc",
          "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        ],
      },
      {
        name: "Impact",
        paths: [
          "C:/Windows/Fonts/impact.ttf",
          "/System/Library/Fonts/Impact.ttf",
        ],
      },
    ];

    systemFonts.forEach((font) => {
      for (const fontPath of font.paths) {
        if (fs.existsSync(fontPath)) {
          try {
            registerFont(fontPath, { family: font.name });
            this.registeredFonts.set(font.name, fontPath);
            console.log(`Registered system font: ${font.name}`);
            break;
          } catch (error) {
            // Continue to next path
          }
        }
      }
    });
  }

  /**
   * Register a custom font for server rendering
   */
  async registerFont(fontName, fontPath) {
    try {
      // Copy font to fonts directory for persistence
      const permanentPath = path.join(this.fontsDir, `${fontName}.ttf`);
      await fs.copy(fontPath, permanentPath);

      // Register with canvas
      registerFont(permanentPath, { family: fontName });
      this.registeredFonts.set(fontName, permanentPath);

      console.log(`Registered custom font: ${fontName} from ${fontPath}`);
      return fontName;
    } catch (error) {
      console.error(`Failed to register font ${fontName}:`, error);
      throw error;
    }
  }

  /**
   * Analyze video file to get metadata
   */
  async analyzeVideo(videoPath) {
    return new Promise((resolve, reject) => {
      ffmpeg.ffprobe(videoPath, (err, metadata) => {
        if (err) {
          reject(new Error(`Video analysis failed: ${err.message}`));
          return;
        }

        const videoStream = metadata.streams.find(
          (s) => s.codec_type === "video"
        );
        const audioStream = metadata.streams.find(
          (s) => s.codec_type === "audio"
        );

        if (!videoStream) {
          reject(new Error("No video stream found"));
          return;
        }

        resolve({
          duration: parseFloat(metadata.format.duration),
          width: videoStream.width,
          height: videoStream.height,
          frameRate: this.parseFrameRate(videoStream.r_frame_rate),
          hasAudio: !!audioStream,
          format: metadata.format.format_name,
          size: metadata.format.size,
        });
      });
    });
  }

  /**
   * Analyze audio file to get metadata
   */
  async analyzeAudio(audioPath) {
    return new Promise((resolve, reject) => {
      ffmpeg.ffprobe(audioPath, (err, metadata) => {
        if (err) {
          reject(new Error(`Audio analysis failed: ${err.message}`));
          return;
        }

        const audioStream = metadata.streams.find(
          (s) => s.codec_type === "audio"
        );

        if (!audioStream) {
          reject(new Error("No audio stream found"));
          return;
        }

        resolve({
          duration: parseFloat(metadata.format.duration),
          sampleRate: audioStream.sample_rate,
          channels: audioStream.channels,
          format: metadata.format.format_name,
          size: metadata.format.size,
        });
      });
    });
  }

  /**
   * Create a video file from image and audio
   */
  async createVideoFromImageAudio(imagePath, audioPath) {
    const videoId = `${uuidv4()}-image-audio.mp4`;
    const outputPath = path.join(__dirname, "../../uploads", videoId);

    try {
      // Get audio duration to determine video length
      const audioInfo = await this.analyzeAudio(audioPath);
      const duration = audioInfo.duration;

      console.log(
        `Creating video from image and audio, duration: ${duration}s`
      );

      // Create video from image and audio using FFmpeg
      await new Promise((resolve, reject) => {
        ffmpeg()
          .input(imagePath)
          .inputOptions([
            "-loop",
            "1", // Loop the image
            "-t",
            duration.toString(), // Set duration to match audio
          ])
          .input(audioPath)
          .outputOptions([
            "-c:v",
            "libx264",
            "-tune",
            "stillimage",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-pix_fmt",
            "yuv420p",
            "-shortest", // End when shortest input ends
            "-vf",
            "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:black", // Scale and pad to 1920x1080
          ])
          .output(outputPath)
          .on("start", (commandLine) => {
            console.log("FFmpeg command:", commandLine);
          })
          .on("progress", (progress) => {
            console.log(`Video creation progress: ${progress.percent}%`);
          })
          .on("end", () => {
            console.log("Video created successfully from image and audio");
            resolve();
          })
          .on("error", (error) => {
            console.error("Video creation failed:", error);
            reject(error);
          })
          .run();
      });

      // Analyze the created video
      const videoInfo = await this.analyzeVideo(outputPath);

      return {
        videoId,
        info: videoInfo,
      };
    } catch (error) {
      console.error("Failed to create video from image and audio:", error);
      throw error;
    }
  }

  /**
   * Process video with karaoke effects using file-based streaming
   */
  async processVideo(job, progressCallback) {
    const jobId = job.id;
    let videoPath = path.join(__dirname, "../../uploads", job.videoId);

    // Determine output format and extension
    const format = job.renderSettings.format || "mp4";
    const extension = format === "webm" ? "webm" : "mp4";
    const outputPath = path.join(this.outputDir, `${jobId}.${extension}`);

    // Debug: Log complete job data to verify effects are received
    console.log("Processing video with job data:", {
      jobId,
      videoId: job.videoId,
      videoPath,
      effectsKeys: Object.keys(job.effects || {}),
      effects: job.effects,
      renderSettings: job.renderSettings,
    });

    try {
      progressCallback({ percent: 0, message: "Analyzing input..." });

      // Check if this is an image-audio combo
      const infoPath = path.join(
        __dirname,
        "../../uploads",
        `${job.videoId}.json`
      );
      if (fs.existsSync(infoPath)) {
        console.log("Detected image-audio combo, creating video first...");
        progressCallback({
          percent: 5,
          message: "Creating video from image and audio...",
        });

        // Read the stored image-audio info
        const imageAudioInfo = JSON.parse(await fs.readFile(infoPath, "utf8"));

        // Create the video from image and audio
        const createdVideoInfo = await this.createVideoFromImageAudio(
          imageAudioInfo.imagePath,
          imageAudioInfo.audioPath
        );

        // Update the video path to the newly created video
        videoPath = path.join(
          __dirname,
          "../../uploads",
          createdVideoInfo.videoId
        );

        progressCallback({
          percent: 15,
          message: "Video created, analyzing...",
        });
      }

      // Check if video file exists
      if (!fs.existsSync(videoPath)) {
        throw new Error(`Video file not found at path: ${videoPath}`);
      }

      // Get video info
      const videoInfo = await this.analyzeVideo(videoPath);
      const { width, height, duration, frameRate } = videoInfo;

      // Calculate render parameters
      const renderWidth = this.getRenderWidth(
        job.renderSettings.resolution,
        width
      );
      const renderHeight = this.getRenderHeight(
        job.renderSettings.resolution,
        height
      );
      const targetFrameRate = job.renderSettings.frameRate || frameRate;
      const totalFrames = Math.ceil(duration * targetFrameRate);

      progressCallback({
        percent: 5,
        message: `Processing ${totalFrames} frames...`,
      });

      // Create temporary directory for this job
      const jobTempDir = path.join(this.tempDir, jobId);
      fs.ensureDirSync(jobTempDir);

      try {
        // Extract frames and render karaoke effects
        await this.renderFramesWithEffects(
          videoPath,
          jobTempDir,
          job,
          renderWidth,
          renderHeight,
          targetFrameRate,
          totalFrames,
          progressCallback
        );

        progressCallback({ percent: 85, message: "Encoding final video..." });

        // Combine frames back to video
        await this.combineFramesToVideo(
          jobTempDir,
          videoPath,
          outputPath,
          targetFrameRate,
          job.renderSettings,
          progressCallback
        );

        progressCallback({ percent: 100, message: "Render completed!" });

        return outputPath;
      } finally {
        // Cleanup temporary files
        await fs.remove(jobTempDir);
      }
    } catch (error) {
      console.error(`Video processing failed for job ${jobId}:`, error);
      throw error;
    }
  }

  /**
   * Render frames with karaoke effects using file-based processing
   */
  async renderFramesWithEffects(
    videoPath,
    tempDir,
    job,
    width,
    height,
    frameRate,
    totalFrames,
    progressCallback
  ) {
    const frameInterval = 1 / frameRate;
    const batchSize = 200; // Increased batch size for better performance

    // Extract video frames in batches
    for (
      let batchStart = 0;
      batchStart < totalFrames;
      batchStart += batchSize
    ) {
      const batchEnd = Math.min(batchStart + batchSize, totalFrames);
      const batchFrames = batchEnd - batchStart;

      // Extract frames for this batch
      const batchDir = path.join(tempDir, `batch_${batchStart}`);
      fs.ensureDirSync(batchDir);

      await this.extractFrameBatch(
        videoPath,
        batchDir,
        batchStart,
        batchFrames,
        frameRate
      );

      // Verify frames were extracted
      const extractedFiles = await fs.readdir(batchDir);
      console.log(
        `Extracted ${extractedFiles.length} files in batch ${batchStart}`
      );

      // Process each frame in the batch
      for (let i = 0; i < batchFrames; i++) {
        const frameIndex = batchStart + i;
        const timestamp = frameIndex * frameInterval;

        const inputFramePath = path.join(
          batchDir,
          `frame_${String(i).padStart(6, "0")}.png`
        );
        const outputFramePath = path.join(
          tempDir,
          `output_${String(frameIndex).padStart(6, "0")}.png`
        );

        // Check if input frame exists
        if (!(await fs.pathExists(inputFramePath))) {
          console.warn(`Frame ${inputFramePath} not found, skipping...`);
          // Create a black frame as fallback
          await this.createBlackFrame(outputFramePath, width, height);
          continue;
        }

        // Skip rendering if no active subtitle (performance optimization)
        const hasActiveSubtitle = job.subtitles.some(
          (sub) => timestamp >= sub.start_time && timestamp <= sub.end_time
        );

        if (hasActiveSubtitle) {
          // Render karaoke effects on this frame
          await this.renderKaraokeFrame(
            inputFramePath,
            outputFramePath,
            timestamp,
            job.effects,
            job.subtitles,
            job.wordSegments,
            width,
            height
          );
        } else {
          // Just copy the frame without processing
          await fs.copy(inputFramePath, outputFramePath);
        }

        // Update progress
        const progress = 5 + ((frameIndex + 1) / totalFrames) * 75;
        progressCallback({
          percent: progress,
          message: `Processing frame ${frameIndex + 1}/${totalFrames}`,
        });
      }

      // Clean up batch directory to save space
      await fs.remove(batchDir);

      // Force garbage collection if available
      if (global.gc) {
        global.gc();
      }
    }
  }

  /**
   * Extract a batch of frames from video (optimized)
   */
  async extractFrameBatch(
    videoPath,
    outputDir,
    startFrame,
    frameCount,
    frameRate
  ) {
    return new Promise((resolve, reject) => {
      const startTime = startFrame / frameRate;
      const duration = frameCount / frameRate;

      // Ensure output directory exists
      fs.ensureDirSync(outputDir);

      console.log(
        `Extracting ${frameCount} frames starting at ${startTime}s to ${outputDir}`
      );

      ffmpeg(videoPath)
        .seekInput(startTime)
        .inputOptions([
          "-t",
          duration.toString(),
          "-threads",
          "0", // Use all available CPU threads
        ])
        .fps(frameRate)
        .size("1920x1080")
        .output(path.join(outputDir, "frame_%06d.png"))
        .outputOptions([
          "-start_number",
          "0",
          "-q:v",
          "2", // High quality but fast PNG compression
          "-pix_fmt",
          "rgb24", // Optimize pixel format for PNG
          "-preset",
          "ultrafast", // Fastest extraction preset
        ])
        .on("start", (commandLine) => {
          console.log("FFmpeg command:", commandLine);
        })
        .on("progress", (progress) => {
          if (progress.frames) {
            console.log(`Frame extraction progress: ${progress.frames} frames`);
          }
        })
        .on("end", () => {
          console.log(
            `Frame extraction completed for batch starting at frame ${startFrame}`
          );
          resolve();
        })
        .on("error", (error) => {
          console.error(`Frame extraction failed:`, error);
          reject(error);
        })
        .run();
    });
  }

  /**
   * Render karaoke effects on a single frame (optimized)
   */
  async renderKaraokeFrame(
    inputPath,
    outputPath,
    timestamp,
    effects,
    subtitles,
    wordSegments,
    width,
    height
  ) {
    try {
      // Load the video frame
      const image = await loadImage(inputPath);

      // Create canvas with optimized settings
      const canvas = createCanvas(width, height);
      const ctx = canvas.getContext("2d");

      // Optimize canvas for performance
      ctx.imageSmoothingEnabled = false; // Disable antialiasing for speed
      ctx.textRenderingOptimization = "speed";

      // Draw video frame
      ctx.drawImage(image, 0, 0, width, height);

      // Find active subtitle
      const activeSubtitle = subtitles.find(
        (sub) => timestamp >= sub.start_time && timestamp <= sub.end_time
      );

      if (activeSubtitle) {
        // Get words for this subtitle
        const words = wordSegments.filter(
          (word) =>
            word.start_time >= activeSubtitle.start_time &&
            word.end_time <= activeSubtitle.end_time
        );

        if (words.length > 0) {
          // Use unified text renderer with pre-calculated gradients
          const textRenderer = new UnifiedTextRenderer(ctx, effects);
          textRenderer.preCalculateGradientColors();
          textRenderer.renderKaraokeText(words, timestamp, width, height);
        }
      }

      // Save with optimized PNG compression
      const buffer = canvas.toBuffer("image/png", {
        compressionLevel: 1, // Faster compression
        filters: canvas.PNG_FILTER_NONE,
      });
      await fs.writeFile(outputPath, buffer);
    } catch (error) {
      console.error(`Error rendering frame at ${timestamp}s:`, error);
      // Copy original frame if rendering fails
      await fs.copy(inputPath, outputPath);
    }
  }

  /**
   * Render karaoke text effects on canvas (matching client-side implementation)
   */
  renderKaraokeText(
    ctx,
    words,
    currentTime,
    effects,
    canvasWidth,
    canvasHeight
  ) {
    // Setup text rendering with custom font support (exactly matching client)
    const fontFamily = this.getFontFamily(effects);

    // Match client font setup exactly
    ctx.font = `${effects.fontWeight} ${effects.fontSize}px ${fontFamily}`;
    ctx.textAlign = "left";
    ctx.textBaseline = "middle";

    // Debug: Log complete effects comparison
    console.log("Server rendering effects:", {
      fontFamily: effects.fontFamily,
      customFontName: effects.customFontName,
      fontSize: effects.fontSize,
      fontWeight: effects.fontWeight,
      enableBorder: effects.enableBorder,
      enableShadow: effects.enableShadow,
      borderWidth: effects.borderWidth,
      borderColor: effects.borderColor,
      glowIntensity: effects.glowIntensity,
      karaokeMode: effects.karaokeMode,
      resolvedFont: fontFamily,
    });

    // Apply base text effects
    this.applyTextEffects(ctx, effects);

    // Break words into lines if auto-break is enabled
    const lines = effects.autoBreak
      ? this.breakIntoLines(words, ctx, effects)
      : [words];

    // Calculate position
    const centerX = effects.positionX || canvasWidth / 2;
    const baseY = effects.positionY || canvasHeight - 150;

    // Calculate total height for centering
    const lineHeight = (effects.fontSize || 60) * (effects.lineHeight || 1.2);
    const totalHeight = lines.length * lineHeight;
    let currentY = baseY - totalHeight / 2 + lineHeight / 2;

    // Render each line
    lines.forEach((lineWords) => {
      // Calculate total width for centering this line
      const wordWidths = lineWords.map(
        (word) => ctx.measureText(word.word).width
      );
      const totalSpacing = (lineWords.length - 1) * (effects.wordSpacing || 10);
      const totalWidth =
        wordWidths.reduce((sum, width) => sum + width, 0) + totalSpacing;

      let currentX = centerX - totalWidth / 2;

      // Render each word in the line
      lineWords.forEach((word, index) => {
        const progress = this.getWordProgress(
          word,
          currentTime,
          effects.animationSpeed || 1
        );

        // Render word with effects based on karaoke mode
        this.renderWordWithEffects(
          ctx,
          word,
          currentX,
          currentY,
          progress,
          effects
        );

        currentX += wordWidths[index] + (effects.wordSpacing || 10);
      });

      currentY += lineHeight;
    });
  }

  /**
   * Break words into lines based on maxLineWidth
   */
  breakIntoLines(words, ctx, effects) {
    if (!effects.autoBreak || !effects.maxLineWidth) {
      return [words];
    }

    const lines = [];
    let currentLine = [];
    let currentWidth = 0;
    const wordSpacing = effects.wordSpacing || 10;

    words.forEach((word) => {
      const wordWidth = ctx.measureText(word.word).width;
      const spaceWidth = currentLine.length > 0 ? wordSpacing : 0;

      if (
        currentWidth + spaceWidth + wordWidth > effects.maxLineWidth &&
        currentLine.length > 0
      ) {
        // Start new line
        lines.push(currentLine);
        currentLine = [word];
        currentWidth = wordWidth;
      } else {
        // Add to current line
        currentLine.push(word);
        currentWidth += spaceWidth + wordWidth;
      }
    });

    if (currentLine.length > 0) {
      lines.push(currentLine);
    }

    return lines.length > 0 ? lines : [words];
  }

  /**
   * Render a single word with all effects
   */
  renderWordWithEffects(ctx, word, x, y, progress, effects) {
    const karaokeMode = effects.karaokeMode || "highlight";

    switch (karaokeMode) {
      case "highlight":
        this.renderHighlightWord(ctx, word, x, y, progress, effects);
        break;
      case "gradient":
        this.renderGradientWord(ctx, word, x, y, progress, effects);
        break;
      case "fill":
        this.renderFillWord(ctx, word, x, y, progress, effects);
        break;
      case "bounce":
        this.renderBounceWord(ctx, word, x, y, progress, effects);
        break;
      default:
        this.renderHighlightWord(ctx, word, x, y, progress, effects);
    }
  }

  /**
   * Render word with highlight effect
   */
  renderHighlightWord(ctx, word, x, y, progress, effects) {
    const isHighlighted = progress > 0 && progress < 1;
    const color = isHighlighted ? effects.highlightColor : effects.primaryColor;

    // Add glow for highlighted words
    if (isHighlighted && effects.glowIntensity > 0) {
      this.renderTextWithGlow(
        ctx,
        word.word,
        x,
        y,
        color,
        effects.glowIntensity,
        effects.highlightColor,
        effects
      );
    } else {
      this.renderTextWithEffects(ctx, word.word, x, y, color, effects);
    }
  }

  /**
   * Render word with gradient effect
   */
  renderGradientWord(ctx, word, x, y, progress, effects) {
    // Interpolate between primary and highlight colors
    const primaryColor = this.hexToRgb(effects.primaryColor || "#ffffff");
    const highlightColor = this.hexToRgb(effects.highlightColor || "#ffff00");

    const r = Math.round(
      primaryColor.r + (highlightColor.r - primaryColor.r) * progress
    );
    const g = Math.round(
      primaryColor.g + (highlightColor.g - primaryColor.g) * progress
    );
    const b = Math.round(
      primaryColor.b + (highlightColor.b - primaryColor.b) * progress
    );

    const color = `rgb(${r}, ${g}, ${b})`;

    // Add glow based on progress
    if (progress > 0 && effects.glowIntensity > 0) {
      this.renderTextWithGlow(
        ctx,
        word.word,
        x,
        y,
        color,
        effects.glowIntensity * progress,
        color,
        effects
      );
    } else {
      this.renderTextWithEffects(ctx, word.word, x, y, color, effects);
    }
  }

  /**
   * Render word with fill effect
   */
  renderFillWord(ctx, word, x, y, progress, effects) {
    // Draw unfilled part
    this.renderTextWithEffects(
      ctx,
      word.word,
      x,
      y,
      effects.primaryColor,
      effects
    );

    if (progress > 0) {
      // Draw filled part with clipping
      ctx.save();

      const wordWidth = ctx.measureText(word.word).width;
      const fillWidth = wordWidth * progress;

      ctx.beginPath();
      ctx.rect(
        x,
        y - (effects.fontSize || 60) / 2,
        fillWidth,
        effects.fontSize || 60
      );
      ctx.clip();

      // Add glow for filled part
      if (effects.glowIntensity > 0) {
        this.renderTextWithGlow(
          ctx,
          word.word,
          x,
          y,
          effects.highlightColor,
          effects.glowIntensity,
          effects.highlightColor,
          effects
        );
      } else {
        this.renderTextWithEffects(
          ctx,
          word.word,
          x,
          y,
          effects.highlightColor,
          effects
        );
      }

      ctx.restore();
    }
  }

  /**
   * Render word with bounce effect
   */
  renderBounceWord(ctx, word, x, y, progress, effects) {
    ctx.save();

    // Calculate bounce offset
    const bounceHeight =
      (effects.bounceHeight || 10) * Math.sin(progress * Math.PI);
    const bounceY = y - bounceHeight;

    const color = progress > 0 ? effects.highlightColor : effects.primaryColor;

    // Add glow for bouncing words
    if (progress > 0 && effects.glowIntensity > 0) {
      this.renderTextWithGlow(
        ctx,
        word.word,
        x,
        bounceY,
        color,
        effects.glowIntensity,
        effects.highlightColor,
        effects
      );
    } else {
      this.renderTextWithEffects(ctx, word.word, x, bounceY, color, effects);
    }

    ctx.restore();
  }

  /**
   * Render text with glow effect (matching client)
   */
  renderTextWithGlow(
    ctx,
    text,
    x,
    y,
    color,
    glowIntensity,
    glowColor,
    effects
  ) {
    const originalShadowBlur = ctx.shadowBlur;
    const originalShadowColor = ctx.shadowColor;

    ctx.shadowColor = glowColor || color;
    ctx.shadowBlur = glowIntensity;

    // Single glow pass for better performance (matching optimized client)
    ctx.fillStyle = color;
    ctx.fillText(text, x, y);

    // Only draw border if explicitly enabled
    if (effects.enableBorder && ctx.lineWidth > 0) {
      ctx.strokeText(text, x, y);
    }

    // Restore original shadow settings
    ctx.shadowBlur = originalShadowBlur;
    ctx.shadowColor = originalShadowColor;
  }

  /**
   * Render text with basic effects (matching client exactly)
   */
  renderTextWithEffects(ctx, text, x, y, color, effects) {
    ctx.fillStyle = color;
    ctx.fillText(text, x, y);

    // Only draw border if explicitly enabled (matching client logic)
    if (effects.enableBorder && ctx.lineWidth > 0) {
      ctx.strokeText(text, x, y);
    }
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
   * Get the appropriate font family for rendering
   */
  getFontFamily(effects) {
    // Check for custom font first
    if (effects.fontFamily === "custom" && effects.customFontName) {
      if (this.registeredFonts.has(effects.customFontName)) {
        return effects.customFontName;
      } else {
        console.warn(
          `Custom font ${effects.customFontName} not registered, falling back to Arial`
        );
        return "Arial";
      }
    }

    // Check if requested font is registered
    if (effects.fontFamily && this.registeredFonts.has(effects.fontFamily)) {
      return effects.fontFamily;
    }

    // Fallback to Arial (should always be available)
    return "Arial";
  }

  /**
   * Apply text effects to canvas context (matching client exactly)
   */
  applyTextEffects(ctx, effects) {
    // Reset effects (matching client)
    ctx.shadowBlur = 0;
    ctx.shadowOffsetX = 0;
    ctx.shadowOffsetY = 0;
    ctx.lineWidth = 0; // Reset line width

    // Apply shadow if enabled (matching client)
    if (effects.enableShadow) {
      ctx.shadowColor = effects.shadowColor || "#000000";
      ctx.shadowBlur = effects.shadowBlur || 4;
      ctx.shadowOffsetX = effects.shadowOffsetX || 2;
      ctx.shadowOffsetY = effects.shadowOffsetY || 2;
    }

    // Apply border if enabled (matching client)
    if (effects.enableBorder) {
      ctx.strokeStyle = effects.borderColor || "#000000";
      ctx.lineWidth = effects.borderWidth || 2;
    } else {
      // Explicitly disable border
      ctx.lineWidth = 0;
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
   * Combine rendered frames back to video
   */
  async combineFramesToVideo(
    framesDir,
    originalVideoPath,
    outputPath,
    frameRate,
    renderSettings,
    progressCallback
  ) {
    return new Promise((resolve, reject) => {
      const inputPattern = path.join(framesDir, "output_%06d.png");

      let command = ffmpeg()
        .input(inputPattern)
        .inputFPS(frameRate)
        .videoCodec("libx264")
        .fps(frameRate);

      // Add original audio if available
      command = command.input(originalVideoPath);

      // Set quality and Windows compatibility settings
      const qualitySettings = {
        high: [
          "-crf",
          "18",
          "-preset",
          "medium",
          "-profile:v",
          "high",
          "-level",
          "4.0",
          "-pix_fmt",
          "yuv420p",
          "-movflags",
          "+faststart",
        ],
        medium: [
          "-crf",
          "23",
          "-preset",
          "medium",
          "-profile:v",
          "high",
          "-level",
          "4.0",
          "-pix_fmt",
          "yuv420p",
          "-movflags",
          "+faststart",
        ],
        low: [
          "-crf",
          "28",
          "-preset",
          "fast",
          "-profile:v",
          "main",
          "-level",
          "3.1",
          "-pix_fmt",
          "yuv420p",
          "-movflags",
          "+faststart",
        ],
      };

      // Get optimal encoding settings for Windows compatibility
      const format = renderSettings.format || "mp4";
      const quality = renderSettings.quality || "medium";
      const encodingSettings = this.getEncodingSettings(format, quality);

      command = command.outputOptions(encodingSettings);

      // Map video and audio streams
      command = command
        .outputOptions(["-map", "0:v:0", "-map", "1:a:0?"])
        .output(outputPath);

      command
        .on("progress", (progress) => {
          if (progress.percent) {
            const percent = 85 + progress.percent * 0.15;
            progressCallback({
              percent,
              message: `Encoding video: ${Math.round(progress.percent)}%`,
            });
          }
        })
        .on("end", resolve)
        .on("error", reject)
        .run();
    });
  }

  /**
   * Get optimal encoding settings for different formats
   */
  getEncodingSettings(format, quality) {
    const settings = {
      mp4: {
        high: [
          "-c:v",
          "libx264",
          "-crf",
          "18",
          "-preset",
          "medium",
          "-profile:v",
          "high",
          "-level",
          "4.0",
          "-pix_fmt",
          "yuv420p",
          "-c:a",
          "aac",
          "-b:a",
          "192k",
          "-movflags",
          "+faststart",
        ],
        medium: [
          "-c:v",
          "libx264",
          "-crf",
          "23",
          "-preset",
          "medium",
          "-profile:v",
          "high",
          "-level",
          "4.0",
          "-pix_fmt",
          "yuv420p",
          "-c:a",
          "aac",
          "-b:a",
          "128k",
          "-movflags",
          "+faststart",
        ],
        low: [
          "-c:v",
          "libx264",
          "-crf",
          "28",
          "-preset",
          "fast",
          "-profile:v",
          "main",
          "-level",
          "3.1",
          "-pix_fmt",
          "yuv420p",
          "-c:a",
          "aac",
          "-b:a",
          "96k",
          "-movflags",
          "+faststart",
        ],
      },
      webm: {
        high: [
          "-c:v",
          "libvpx-vp9",
          "-crf",
          "30",
          "-b:v",
          "0",
          "-c:a",
          "libopus",
          "-b:a",
          "128k",
        ],
        medium: [
          "-c:v",
          "libvpx-vp9",
          "-crf",
          "35",
          "-b:v",
          "0",
          "-c:a",
          "libopus",
          "-b:a",
          "96k",
        ],
        low: [
          "-c:v",
          "libvpx-vp9",
          "-crf",
          "40",
          "-b:v",
          "0",
          "-c:a",
          "libopus",
          "-b:a",
          "64k",
        ],
      },
    };

    return settings[format]?.[quality] || settings.mp4.medium;
  }

  /**
   * Get render width based on resolution setting
   */
  getRenderWidth(resolution, originalWidth) {
    const resolutions = {
      "720p": 1280,
      "1080p": 1920,
      "4k": 3840,
    };
    return resolutions[resolution] || originalWidth;
  }

  /**
   * Get render height based on resolution setting
   */
  getRenderHeight(resolution, originalHeight) {
    const resolutions = {
      "720p": 720,
      "1080p": 1080,
      "4k": 2160,
    };
    return resolutions[resolution] || originalHeight;
  }

  /**
   * Create a black frame as fallback
   */
  async createBlackFrame(outputPath, width, height) {
    const canvas = createCanvas(width, height);
    const ctx = canvas.getContext("2d");

    // Fill with black
    ctx.fillStyle = "#000000";
    ctx.fillRect(0, 0, width, height);

    // Save the black frame
    const buffer = canvas.toBuffer("image/png");
    await fs.writeFile(outputPath, buffer);
  }

  /**
   * Parse frame rate from FFmpeg format
   */
  parseFrameRate(frameRateStr) {
    if (!frameRateStr) return 30;

    const parts = frameRateStr.split("/");
    if (parts.length === 2) {
      return parseFloat(parts[0]) / parseFloat(parts[1]);
    }
    return parseFloat(frameRateStr) || 30;
  }
}

module.exports = VideoProcessor;
