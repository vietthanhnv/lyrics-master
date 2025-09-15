class KaraokeApp {
  constructor() {
    this.video = document.getElementById("videoPlayer");
    this.canvas = document.getElementById("renderCanvas");
    this.ctx = this.canvas.getContext("2d");

    this.subtitles = [];
    this.wordSegments = [];
    this.currentTime = 0;
    this.isPlaying = false;
    this.animationId = null;

    // Performance tracking
    this.performanceMode = "auto"; // auto, fast, quality
    this.frameTimeHistory = [];
    this.avgFrameTime = 16.67;

    this.effects = {
      fontFamily: "Arial",
      customFontName: "",
      fontSize: 60,
      fontWeight: "bold",
      textPosition: "bottom",
      verticalPosition: 85,
      positionX: 960,
      positionY: 930,
      karaokeMode: "highlight",
      primaryColor: "#ffffff",
      highlightColor: "#ffff00",
      animationSpeed: 1,
      glowIntensity: 20,
      glowColor: "#ffff00",
      glowOpacity: 0.8,
      wordSpacing: 10,
      maxLineWidth: 1200,
      lineHeight: 1.2,
      autoBreak: true,
      // New text effects
      enableBorder: false,
      borderWidth: 2,
      borderColor: "#000000",
      enableShadow: false,
      shadowBlur: 4,
      shadowColor: "#000000",
      shadowOffsetX: 2,
      shadowOffsetY: 2,
    };

    this.loadedFonts = new Set();
    this.currentEditingLine = null;
    this.selectedWord = null;
    this.originalSubtitleData = null;
    this.presets = new Map();
    this.builtinPresets = this.createBuiltinPresets();

    // Initialize advanced rendering systems
    this.batchProcessor = null;
    this.parallelRenderer = null;
    this.gpuRenderer = null;
    this.memoryOptimizedRenderer = null;
    this.fixedMemoryRenderer = null;
    this.trueParallelRenderer = null;
    this.serverRenderer = null;

    // Server-based rendering
    this.uploadedVideoId = null;
    this.isServerAvailable = false;
    this.currentVideoFile = null;

    // Image + Audio mode
    this.inputMode = "video"; // "video" or "imageAudio"
    this.currentImageFile = null;
    this.currentAudioFile = null;
    this.loadedImage = null;
    this.audioDuration = 0;

    // Status display
    this.statusDisplay = document.getElementById("statusDisplay");

    this.initializeEventListeners();
    this.setupCanvas();
    this.loadDefaultSubtitles();
    this.initializeCollapsibleSections();
    this.initializePresets();
    this.initializeAdvancedRendering();

    // Initialize unified text renderer for consistent preview/server rendering
    this.textRenderer = new UnifiedTextRenderer(this.ctx, this.effects);
    this.textRenderer.preCalculateGradientColors();
  }

  initializeEventListeners() {
    // Tab switching
    document.querySelectorAll(".tab-button").forEach((button) => {
      button.addEventListener("click", (e) =>
        this.switchTab(e.target.dataset.tab)
      );
    });

    // File inputs
    document
      .getElementById("videoInput")
      .addEventListener("change", (e) => this.loadVideo(e));
    document
      .getElementById("imageInput")
      .addEventListener("change", (e) => this.loadImage(e));
    document
      .getElementById("audioInput")
      .addEventListener("change", (e) => this.loadAudio(e));
    document
      .getElementById("subtitleInput")
      .addEventListener("change", (e) => this.loadSubtitles(e));

    // Playback controls
    document
      .getElementById("playPauseBtn")
      .addEventListener("click", () => this.togglePlayPause());
    document
      .getElementById("seekBar")
      .addEventListener("input", (e) => this.seek(e));

    // Effects controls
    document.getElementById("fontFamily").addEventListener("change", (e) => {
      this.effects.fontFamily = e.target.value;
      const customFontGroup = document.getElementById("customFontGroup");
      customFontGroup.style.display =
        e.target.value === "custom" ? "block" : "none";
    });

    document.getElementById("fontFile").addEventListener("change", (e) => {
      this.loadCustomFont(e);
    });

    document.getElementById("fontSize").addEventListener("input", (e) => {
      this.effects.fontSize = parseInt(e.target.value);
      document.getElementById("fontSizeValue").textContent =
        e.target.value + "px";
    });

    document.getElementById("textPosition").addEventListener("change", (e) => {
      this.effects.textPosition = e.target.value;
      const customGroup = document.getElementById("customPositionGroup");
      customGroup.style.display =
        e.target.value === "custom" ? "block" : "none";

      // Update position coordinates based on preset
      if (e.target.value !== "custom") {
        this.updateTextPositionPreset(e.target.value);
      } else {
        // When switching to custom mode, sync vertical position slider with current positionY
        const canvasHeight = 1080;
        const currentPercentage = Math.round(
          (this.effects.positionY / canvasHeight) * 100
        );
        this.effects.verticalPosition = currentPercentage;
        document.getElementById("verticalPosition").value = currentPercentage;
        document.getElementById("verticalValue").textContent =
          currentPercentage + "%";
      }
    });

    document
      .getElementById("verticalPosition")
      .addEventListener("input", (e) => {
        this.effects.verticalPosition = parseInt(e.target.value);
        document.getElementById("verticalValue").textContent =
          e.target.value + "%";

        // Convert percentage to actual Y coordinate when in custom mode
        if (this.effects.textPosition === "custom") {
          const canvasHeight = 1080; // Default canvas height
          this.effects.positionY = Math.round(
            (this.effects.verticalPosition / 100) * canvasHeight
          );
          document.getElementById("positionY").value = this.effects.positionY;
        }
      });

    document.getElementById("karaokeMode").addEventListener("change", (e) => {
      this.effects.karaokeMode = e.target.value;
    });

    document.getElementById("primaryColor").addEventListener("change", (e) => {
      this.effects.primaryColor = e.target.value;
      if (this.textRenderer) {
        this.textRenderer.preCalculateGradientColors();
      }
    });

    document
      .getElementById("highlightColor")
      .addEventListener("change", (e) => {
        this.effects.highlightColor = e.target.value;
        if (this.textRenderer) {
          this.textRenderer.preCalculateGradientColors();
        }
      });

    document.getElementById("animationSpeed").addEventListener("input", (e) => {
      this.effects.animationSpeed = parseFloat(e.target.value);
      document.getElementById("speedValue").textContent = e.target.value + "x";
    });

    document.getElementById("glowIntensity").addEventListener("input", (e) => {
      this.effects.glowIntensity = parseInt(e.target.value);
      document.getElementById("glowValue").textContent = e.target.value + "px";
    });

    document.getElementById("glowColor").addEventListener("change", (e) => {
      this.effects.glowColor = e.target.value;
    });

    document.getElementById("glowOpacity").addEventListener("input", (e) => {
      this.effects.glowOpacity = parseFloat(e.target.value);
      document.getElementById("glowOpacityValue").textContent = e.target.value;
    });

    document.getElementById("wordSpacing").addEventListener("input", (e) => {
      this.effects.wordSpacing = parseInt(e.target.value);
      document.getElementById("spacingValue").textContent =
        e.target.value + "px";
    });

    document.getElementById("positionX").addEventListener("input", (e) => {
      this.effects.positionX = parseInt(e.target.value);
    });

    document.getElementById("positionY").addEventListener("input", (e) => {
      this.effects.positionY = parseInt(e.target.value);

      // Update vertical position slider when in custom mode
      if (this.effects.textPosition === "custom") {
        const canvasHeight = 1080;
        const percentage = Math.round(
          (this.effects.positionY / canvasHeight) * 100
        );
        this.effects.verticalPosition = percentage;
        document.getElementById("verticalPosition").value = percentage;
        document.getElementById("verticalValue").textContent = percentage + "%";
      }
    });

    document.getElementById("centerPosition").addEventListener("click", () => {
      this.effects.positionX = 960; // Center X for 1920px width
      this.effects.positionY = 930; // Bottom area for 1080px height
      document.getElementById("positionX").value = 960;
      document.getElementById("positionY").value = 930;
    });

    document.getElementById("maxLineWidth").addEventListener("input", (e) => {
      this.effects.maxLineWidth = parseInt(e.target.value);
    });

    document.getElementById("lineHeight").addEventListener("input", (e) => {
      this.effects.lineHeight = parseFloat(e.target.value);
      document.getElementById("lineHeightValue").textContent =
        e.target.value + "x";
    });

    document.getElementById("autoBreak").addEventListener("change", (e) => {
      this.effects.autoBreak = e.target.checked;
    });

    // New text styling controls
    document.getElementById("fontWeight").addEventListener("change", (e) => {
      this.effects.fontWeight = e.target.value;
    });

    document.getElementById("enableBorder").addEventListener("change", (e) => {
      this.effects.enableBorder = e.target.checked;
      document.getElementById("borderControls").style.display = e.target.checked
        ? "block"
        : "none";
    });

    document.getElementById("borderWidth").addEventListener("input", (e) => {
      this.effects.borderWidth = parseInt(e.target.value);
      document.getElementById("borderWidthValue").textContent =
        e.target.value + "px";
    });

    document.getElementById("borderColor").addEventListener("change", (e) => {
      this.effects.borderColor = e.target.value;
    });

    document.getElementById("enableShadow").addEventListener("change", (e) => {
      this.effects.enableShadow = e.target.checked;
      document.getElementById("shadowControls").style.display = e.target.checked
        ? "block"
        : "none";
    });

    document.getElementById("shadowBlur").addEventListener("input", (e) => {
      this.effects.shadowBlur = parseInt(e.target.value);
      document.getElementById("shadowBlurValue").textContent =
        e.target.value + "px";
    });

    document.getElementById("shadowColor").addEventListener("change", (e) => {
      this.effects.shadowColor = e.target.value;
    });

    document.getElementById("shadowOffsetX").addEventListener("input", (e) => {
      this.effects.shadowOffsetX = parseInt(e.target.value);
      document.getElementById("shadowOffsetXValue").textContent =
        e.target.value + "px";
    });

    document.getElementById("shadowOffsetY").addEventListener("input", (e) => {
      this.effects.shadowOffsetY = parseInt(e.target.value);
      document.getElementById("shadowOffsetYValue").textContent =
        e.target.value + "px";
    });

    // Render button
    document
      .getElementById("renderBtn")
      .addEventListener("click", () => this.startRender());

    // Transcript controls
    document
      .getElementById("resetSubtitle")
      .addEventListener("click", () => this.resetToOriginal());
    document
      .getElementById("saveSubtitle")
      .addEventListener("click", () => this.saveSubtitle());
    document
      .getElementById("saveAsCopy")
      .addEventListener("click", () => this.saveAsCopy());
    document
      .getElementById("addLine")
      .addEventListener("click", () => this.addNewLine());

    // Video events
    this.video.addEventListener("loadedmetadata", () => this.onVideoLoaded());
    this.video.addEventListener("timeupdate", () => this.onTimeUpdate());
  }

  setupCanvas() {
    // Set canvas size for HD rendering
    this.canvas.width = 1920;
    this.canvas.height = 1080;
    this.startRenderLoop();
  }

  async loadDefaultSubtitles() {
    try {
      const response = await fetch("test_subtitles.json");
      const data = await response.json();
      this.subtitles = data.segments || [];
      this.wordSegments = data.word_segments || [];
      this.originalSubtitleData = { ...data };
      console.log("Loaded subtitles:", this.subtitles.length, "segments");
      console.log("Loaded word segments:", this.wordSegments.length, "words");
      this.populateTranscript();
    } catch (error) {
      console.log("No default subtitles found, starting with empty data");
      this.populateTranscript();
    }
  }

  /**
   * Show status message to user
   */
  showStatus(message, type = "info", duration = 5000, showRetryButton = false) {
    if (!this.statusDisplay) return;

    this.statusDisplay.innerHTML = message;
    this.statusDisplay.className = `status-display ${type}`;
    this.statusDisplay.style.display = "block";

    // Add retry button for server upload errors
    if (showRetryButton && this.currentVideoFile) {
      const retryButton = document.createElement("button");
      retryButton.textContent = "Retry Upload";
      retryButton.style.marginLeft = "10px";
      retryButton.style.padding = "5px 10px";
      retryButton.style.border = "1px solid currentColor";
      retryButton.style.background = "transparent";
      retryButton.style.color = "inherit";
      retryButton.style.borderRadius = "4px";
      retryButton.style.cursor = "pointer";
      retryButton.onclick = () => this.retryVideoUpload();
      this.statusDisplay.appendChild(retryButton);
    }

    // Auto-hide after duration (except for errors)
    if (type !== "error" && duration > 0) {
      setTimeout(() => {
        this.statusDisplay.style.display = "none";
      }, duration);
    }
  }

  /**
   * Hide status message
   */
  hideStatus() {
    if (this.statusDisplay) {
      this.statusDisplay.style.display = "none";
    }
  }

  /**
   * Retry uploading media to server
   */
  async retryVideoUpload() {
    if (this.inputMode === "video") {
      if (!this.currentVideoFile) {
        this.showStatus(
          "No video file to upload. Please load a video first.",
          "error"
        );
        return false;
      }

      if (!this.isServerAvailable || !this.serverRenderer) {
        this.showStatus(
          "Server not available. Please check if the server is running.",
          "error"
        );
        return false;
      }

      try {
        this.showStatus("Retrying video upload to server...", "info");
        const uploadResult = await this.serverRenderer.uploadVideo(
          this.currentVideoFile
        );
        this.uploadedVideoId = uploadResult.videoId;
        console.log("Video re-uploaded to server:", uploadResult);
        this.showStatus("Video uploaded to server successfully", "success");
        return true;
      } catch (error) {
        console.error("Failed to re-upload video to server:", error);
        this.showStatus(`Failed to upload video: ${error.message}`, "error", 0);
        return false;
      }
    } else if (this.inputMode === "imageAudio") {
      if (!this.currentImageFile || !this.currentAudioFile) {
        this.showStatus(
          "No image and audio files to upload. Please load both files first.",
          "error"
        );
        return false;
      }

      if (!this.isServerAvailable || !this.serverRenderer) {
        this.showStatus(
          "Server not available. Please check if the server is running.",
          "error"
        );
        return false;
      }

      try {
        this.showStatus("Retrying image and audio upload to server...", "info");
        const uploadResult = await this.serverRenderer.uploadImageAudio(
          this.currentImageFile,
          this.currentAudioFile
        );
        this.uploadedVideoId = uploadResult.videoId;
        console.log("Image and audio re-uploaded to server:", uploadResult);
        this.showStatus(
          "Image and audio uploaded to server successfully",
          "success"
        );
        return true;
      } catch (error) {
        console.error("Failed to re-upload image and audio to server:", error);
        this.showStatus(`Failed to upload files: ${error.message}`, "error", 0);
        return false;
      }
    }

    return false;
  }

  /**
   * Get cached gradient color for better performance
   */
  getGradientColor(progress) {
    // Cache key based on progress (rounded to reduce cache size)
    const progressKey = Math.round(progress * 100);
    const cacheKey = `${this.effects.primaryColor}-${this.effects.highlightColor}-${progressKey}`;

    // Check cache first
    if (!this.gradientColorCache) {
      this.gradientColorCache = new Map();
    }

    if (this.gradientColorCache.has(cacheKey)) {
      return this.gradientColorCache.get(cacheKey);
    }

    // Calculate gradient color
    const primary = this.hexToRgb(this.effects.primaryColor);
    const highlight = this.hexToRgb(this.effects.highlightColor);

    const r = Math.round(primary.r + (highlight.r - primary.r) * progress);
    const g = Math.round(primary.g + (highlight.g - primary.g) * progress);
    const b = Math.round(primary.b + (highlight.b - primary.b) * progress);

    const color = `rgb(${r}, ${g}, ${b})`;

    // Cache the result (limit cache size)
    if (this.gradientColorCache.size > 200) {
      this.gradientColorCache.clear();
    }
    this.gradientColorCache.set(cacheKey, color);

    return color;
  }

  /**
   * Fallback text renderer for when no word segments are available
   */
  renderFallbackText(text) {
    const fontFamily =
      this.effects.fontFamily === "custom" && this.effects.customFontName
        ? this.effects.customFontName
        : this.effects.fontFamily;

    this.ctx.font = `${this.effects.fontWeight} ${this.effects.fontSize}px ${fontFamily}`;
    this.ctx.textAlign = "center";
    this.ctx.textBaseline = "middle";
    this.ctx.fillStyle = this.effects.primaryColor;

    const x = this.effects.positionX || this.canvas.width / 2;
    const y = this.effects.positionY || this.canvas.height - 150;

    this.ctx.fillText(text, x, y);
  }

  /**
   * Pre-calculate all gradient colors for ultra-fast lookup
   */
  preCalculateGradientColors() {
    if (!this.gradientColors) {
      this.gradientColors = new Array(101); // 0-100 progress values
    }

    const primary = this.hexToRgb(this.effects.primaryColor);
    const highlight = this.hexToRgb(this.effects.highlightColor);

    // Pre-calculate all 101 gradient steps
    for (let i = 0; i <= 100; i++) {
      const progress = i / 100;
      const r = Math.round(primary.r + (highlight.r - primary.r) * progress);
      const g = Math.round(primary.g + (highlight.g - primary.g) * progress);
      const b = Math.round(primary.b + (highlight.b - primary.b) * progress);
      this.gradientColors[i] = `rgb(${r}, ${g}, ${b})`;
    }
  }

  /**
   * Update gradient colors when effects change
   */
  updateGradientColors() {
    this.preCalculateGradientColors();
  }

  /**
   * Show current effects settings for debugging
   */
  showCurrentEffects() {
    console.log("=== CLIENT EFFECTS COMPARISON ===");
    console.log("Raw effects object:", this.effects);

    const effectsInfo = {
      Font: `${this.effects.fontFamily} ${this.effects.fontSize}px ${this.effects.fontWeight}`,
      "Custom Font": this.effects.customFontName || "None",
      Colors: `Primary: ${this.effects.primaryColor}, Highlight: ${this.effects.highlightColor}`,
      "Karaoke Mode": this.effects.karaokeMode,
      "Glow Intensity": this.effects.glowIntensity,
      "Auto Break": this.effects.autoBreak,
      "Max Line Width": this.effects.maxLineWidth,
      "Word Spacing": this.effects.wordSpacing,
      Position: `X: ${this.effects.positionX}, Y: ${this.effects.positionY}`,
      Shadow: this.effects.enableShadow
        ? `ENABLED: ${this.effects.shadowBlur}px ${this.effects.shadowColor}`
        : "DISABLED",
      Border: this.effects.enableBorder
        ? `ENABLED: ${this.effects.borderWidth}px ${this.effects.borderColor}`
        : "DISABLED",
    };

    console.table(effectsInfo);

    // Show critical settings for server comparison
    console.log("=== CRITICAL SETTINGS FOR SERVER COMPARISON ===");
    console.log("enableBorder:", this.effects.enableBorder);
    console.log("enableShadow:", this.effects.enableShadow);
    console.log("fontWeight:", this.effects.fontWeight);
    console.log("karaokeMode:", this.effects.karaokeMode);

    alert(
      "Effects logged to console. Check browser console for server comparison."
    );
  }

  /**
   * Upload font file to server for server-side rendering
   */
  async uploadFontToServer(fontFile) {
    const formData = new FormData();
    formData.append("font", fontFile);

    const response = await fetch("http://localhost:3001/upload/font", {
      method: "POST",
      body: formData,
    });

    const data = await response.json();

    if (!data.success) {
      throw new Error(data.error || "Font upload failed");
    }

    return data.fontName;
  }

  /**
   * Switch between video mode and image+audio mode
   */
  switchTab(tabName) {
    // Update input mode
    this.inputMode = tabName === "video" ? "video" : "imageAudio";

    // Update tab buttons
    document.querySelectorAll(".tab-button").forEach((button) => {
      button.classList.remove("active");
    });
    document.querySelector(`[data-tab="${tabName}"]`).classList.add("active");

    // Update tab panels
    document.querySelectorAll(".tab-panel").forEach((panel) => {
      panel.classList.remove("active");
    });

    if (tabName === "video") {
      document.getElementById("videoTab").classList.add("active");
      this.showStatus("Switched to Video Mode", "info", 3000);
    } else {
      document.getElementById("imageAudioTab").classList.add("active");
      this.showStatus("Switched to Image + Audio Mode", "info", 3000);
      this.updateImageAudioStatus();
    }

    // Clear current media
    this.clearCurrentMedia();
  }

  /**
   * Clear current loaded media
   */
  clearCurrentMedia() {
    this.video.src = "";
    this.currentVideoFile = null;
    this.currentImageFile = null;
    this.currentAudioFile = null;
    this.loadedImage = null;
    this.audioDuration = 0;
    this.uploadedVideoId = null;

    // Clear canvas
    this.ctx.fillStyle = "#000000";
    this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);

    // Update status indicators
    this.updateImageAudioStatus();
    this.updateVideoStatus();
  }

  /**
   * Update image+audio status indicators
   */
  updateImageAudioStatus() {
    // Show/hide status grid
    const statusGrid = document.getElementById("imageAudioStatus");
    if (statusGrid) {
      statusGrid.style.display =
        this.currentImageFile || this.currentAudioFile ? "grid" : "none";
    }

    // Update image status
    const imageIcon = document.getElementById("imageStatusIcon");
    const imageText = document.getElementById("imageStatusText");
    if (imageIcon && imageText) {
      if (this.currentImageFile) {
        imageIcon.textContent = "✅";
        imageText.textContent = this.currentImageFile.name;
      } else {
        imageIcon.textContent = "❌";
        imageText.textContent = "No image selected";
      }
    }

    // Update audio status
    const audioIcon = document.getElementById("audioStatusIcon");
    const audioText = document.getElementById("audioStatusText");
    if (audioIcon && audioText) {
      if (this.currentAudioFile) {
        audioIcon.textContent = "✅";
        audioText.textContent = `${
          this.currentAudioFile.name
        } (${this.audioDuration.toFixed(1)}s)`;
      } else {
        audioIcon.textContent = "❌";
        audioText.textContent = "No audio selected";
      }
    }

    // Update server upload status
    const uploadIcon = document.getElementById("uploadStatusIcon");
    const uploadText = document.getElementById("uploadStatusText");
    if (uploadIcon && uploadText) {
      if (this.uploadedVideoId) {
        uploadIcon.textContent = "✅";
        uploadText.textContent = "Ready to render";
      } else if (this.currentImageFile && this.currentAudioFile) {
        uploadIcon.textContent = "⏳";
        uploadText.textContent = "Uploading...";
      } else {
        uploadIcon.textContent = "⏳";
        uploadText.textContent = "Not uploaded";
      }
    }
  }

  /**
   * Update video status indicator
   */
  updateVideoStatus() {
    const videoStatus = document.getElementById("videoStatus");
    const videoFileName = document.getElementById("videoFileName");
    const videoDetails = document.getElementById("videoDetails");

    if (this.currentVideoFile && videoStatus && videoFileName && videoDetails) {
      videoStatus.style.display = "flex";
      videoFileName.textContent = this.currentVideoFile.name;

      if (this.uploadedVideoId) {
        videoDetails.textContent = "Uploaded and ready for processing";
      } else {
        videoDetails.textContent = "Uploading to server...";
      }
    } else if (videoStatus) {
      videoStatus.style.display = "none";
    }
  }

  async loadVideo(event) {
    const file = event.target.files[0];
    if (file) {
      // Store the file for potential re-upload
      this.currentVideoFile = file;
      console.log(
        "Loading video file:",
        file.name,
        "Size:",
        file.size,
        "Type:",
        file.type
      );

      // Load video for preview
      const url = URL.createObjectURL(file);
      this.video.src = url;
      this.video.load();

      this.video.onerror = (e) => {
        console.error("Video loading error:", e);
        alert(
          "Error loading video file. Please make sure it's a valid video format."
        );
      };

      this.video.oncanplay = () => {
        console.log("Video ready to play");
        this.updateVideoStatus();
      };

      // Upload to server if available
      if (this.isServerAvailable && this.serverRenderer) {
        try {
          console.log("Uploading video to server...");
          this.showStatus("Uploading video to server...", "info");
          const uploadResult = await this.serverRenderer.uploadVideo(file);
          this.uploadedVideoId = uploadResult.videoId;
          console.log("Video uploaded to server:", uploadResult);
          this.showStatus("Video uploaded to server successfully", "success");
          this.updateVideoStatus();
        } catch (error) {
          console.error("Failed to upload video to server:", error);
          this.uploadedVideoId = null;
          this.showStatus(
            "Failed to upload video to server. Server rendering unavailable.",
            "error",
            0,
            true
          );
        }
      } else {
        this.showStatus(
          "Server not available. Only client-side rendering available.",
          "warning"
        );
      }
    }
  }

  /**
   * Load image file for image+audio mode
   */
  async loadImage(event) {
    const file = event.target.files[0];
    if (file) {
      this.currentImageFile = file;
      console.log(
        "Loading image file:",
        file.name,
        "Size:",
        file.size,
        "Type:",
        file.type
      );

      try {
        // Load image for preview
        const url = URL.createObjectURL(file);
        const img = new Image();

        img.onload = () => {
          this.loadedImage = img;
          console.log("Image loaded:", img.width, "x", img.height);
          this.showStatus(`Image loaded: ${file.name}`, "success", 3000);

          // Update status indicators
          this.updateImageAudioStatus();

          // Draw image on canvas immediately
          this.drawImageOnCanvas();

          // Upload to server if available and we have both image and audio
          this.uploadImageAudioToServer();
        };

        img.onerror = () => {
          console.error("Image loading error");
          this.showStatus("Error loading image file", "error");
        };

        img.src = url;
      } catch (error) {
        console.error("Image loading error:", error);
        this.showStatus("Error loading image file", "error");
      }
    }
  }

  /**
   * Load audio file for image+audio mode
   */
  async loadAudio(event) {
    const file = event.target.files[0];
    if (file) {
      this.currentAudioFile = file;
      console.log(
        "Loading audio file:",
        file.name,
        "Size:",
        file.size,
        "Type:",
        file.type
      );

      try {
        // Create audio element to get duration
        const audio = new Audio();
        const url = URL.createObjectURL(file);

        audio.onloadedmetadata = () => {
          this.audioDuration = audio.duration;
          console.log("Audio loaded, duration:", this.audioDuration, "seconds");
          this.showStatus(
            `Audio loaded: ${file.name} (${this.audioDuration.toFixed(1)}s)`,
            "success",
            3000
          );

          // Update status indicators
          this.updateImageAudioStatus();

          // Set up video element to use audio for timing
          this.setupAudioForTiming(url);

          // Upload to server if available and we have both image and audio
          this.uploadImageAudioToServer();
        };

        audio.onerror = () => {
          console.error("Audio loading error");
          this.showStatus("Error loading audio file", "error");
        };

        audio.src = url;
      } catch (error) {
        console.error("Audio loading error:", error);
        this.showStatus("Error loading audio file", "error");
      }
    }
  }

  /**
   * Draw the loaded image on canvas
   */
  drawImageOnCanvas() {
    if (!this.loadedImage) return;

    // Clear canvas
    this.ctx.fillStyle = "#000000";
    this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);

    // Calculate scaling to fit image in canvas while maintaining aspect ratio
    const canvasAspect = this.canvas.width / this.canvas.height;
    const imageAspect = this.loadedImage.width / this.loadedImage.height;

    let drawWidth, drawHeight, drawX, drawY;

    if (imageAspect > canvasAspect) {
      // Image is wider than canvas
      drawWidth = this.canvas.width;
      drawHeight = this.canvas.width / imageAspect;
      drawX = 0;
      drawY = (this.canvas.height - drawHeight) / 2;
    } else {
      // Image is taller than canvas
      drawHeight = this.canvas.height;
      drawWidth = this.canvas.height * imageAspect;
      drawX = (this.canvas.width - drawWidth) / 2;
      drawY = 0;
    }

    this.ctx.drawImage(this.loadedImage, drawX, drawY, drawWidth, drawHeight);
  }

  /**
   * Set up audio for timing in image+audio mode
   */
  setupAudioForTiming(audioUrl) {
    // Use the video element to play audio for timing
    this.video.src = audioUrl;
    this.video.load();

    this.video.onloadedmetadata = () => {
      console.log("Audio set up for timing, duration:", this.video.duration);
    };
  }

  /**
   * Upload image and audio to server for processing
   */
  async uploadImageAudioToServer() {
    if (!this.currentImageFile || !this.currentAudioFile) {
      return; // Need both files
    }

    if (!this.isServerAvailable || !this.serverRenderer) {
      this.showStatus(
        "Server not available for image+audio processing",
        "warning"
      );
      return;
    }

    try {
      this.showStatus("Uploading image and audio to server...", "info");

      // Upload both files
      const uploadResult = await this.serverRenderer.uploadImageAudio(
        this.currentImageFile,
        this.currentAudioFile
      );

      this.uploadedVideoId = uploadResult.videoId;
      console.log("Image and audio uploaded to server:", uploadResult);
      console.log("Uploaded video ID:", this.uploadedVideoId);
      this.showStatus("Image and audio uploaded successfully", "success");

      // Update status indicators
      this.updateImageAudioStatus();
    } catch (error) {
      console.error("Failed to upload image and audio to server:", error);
      this.uploadedVideoId = null;
      this.showStatus(
        "Failed to upload files to server. Server rendering unavailable.",
        "error",
        0,
        true
      );
    }
  }

  loadSubtitles(event) {
    const file = event.target.files[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = (e) => {
        try {
          const data = JSON.parse(e.target.result);
          this.subtitles = data.segments || [];
          this.wordSegments = data.word_segments || [];
          this.originalSubtitleData = { ...data };
          console.log(
            "Loaded new subtitles:",
            this.subtitles.length,
            "segments"
          );
          console.log(
            "Loaded new word segments:",
            this.wordSegments.length,
            "words"
          );
          this.populateTranscript();
        } catch (error) {
          alert("Error loading subtitle file: " + error.message);
        }
      };
      reader.readAsText(file);
    }
  }

  onVideoLoaded() {
    const seekBar = document.getElementById("seekBar");
    seekBar.max = this.video.duration;
    this.updateTimeDisplay();
  }

  onTimeUpdate() {
    if (!this.video.paused) {
      this.currentTime = this.video.currentTime;
      const seekBar = document.getElementById("seekBar");
      seekBar.value = this.currentTime;
      this.updateTimeDisplay();
    }
  }

  togglePlayPause() {
    const btn = document.getElementById("playPauseBtn");
    if (this.video.paused) {
      this.video.play();
      btn.textContent = "⏸️";
      this.isPlaying = true;
    } else {
      this.video.pause();
      btn.textContent = "▶️";
      this.isPlaying = false;
    }
  }

  seek(event) {
    const time = parseFloat(event.target.value);
    this.video.currentTime = time;
    this.currentTime = time;
    this.updateTimeDisplay();
  }

  updateTimeDisplay() {
    const current = this.formatTime(this.currentTime);
    const duration = this.formatTime(this.video.duration || 0);
    document.getElementById(
      "timeDisplay"
    ).textContent = `${current} / ${duration}`;
  }

  formatTime(seconds) {
    // Keep decimal seconds for easier editing
    return seconds.toFixed(3);
  }

  updateTextPositionPreset(position) {
    // Update position coordinates based on preset
    switch (position) {
      case "bottom":
        this.effects.positionX = 960; // Center X for 1920px width
        this.effects.positionY = 930; // Bottom area for 1080px height
        break;
      case "center":
        this.effects.positionX = 960; // Center X for 1920px width
        this.effects.positionY = 540; // Center Y for 1080px height
        break;
      case "top":
        this.effects.positionX = 960; // Center X for 1920px width
        this.effects.positionY = 150; // Top area for 1080px height
        break;
    }

    // Update the UI inputs to reflect the new values
    document.getElementById("positionX").value = this.effects.positionX;
    document.getElementById("positionY").value = this.effects.positionY;
  }

  startRenderLoop() {
    let lastFrameTime = 0;
    const targetFPS = 60; // Limit to 60 FPS for smooth performance
    const frameInterval = 1000 / targetFPS;

    const render = (currentTime) => {
      // Frame rate limiting
      if (currentTime - lastFrameTime >= frameInterval) {
        this.renderFrame();
        lastFrameTime = currentTime;
      }
      this.animationId = requestAnimationFrame(render);
    };
    render(0);
  }

  renderFrame() {
    // Performance monitoring
    const frameStart = performance.now();

    // Clear canvas with black background
    this.ctx.fillStyle = "#000000";
    this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);

    // Draw background based on input mode
    if (this.inputMode === "video" && this.video.videoWidth > 0) {
      // Draw video frame
      this.ctx.drawImage(
        this.video,
        0,
        0,
        this.canvas.width,
        this.canvas.height
      );
    } else if (this.inputMode === "imageAudio" && this.loadedImage) {
      // Draw static image
      this.drawImageOnCanvas();
    }

    // Render karaoke subtitles
    this.renderKaraokeSubtitles();

    // Performance monitoring and adaptive quality
    const frameEnd = performance.now();
    const frameTime = frameEnd - frameStart;

    // Track frame time history
    this.frameTimeHistory.push(frameTime);
    if (this.frameTimeHistory.length > 10) {
      this.frameTimeHistory.shift();
    }

    // Calculate average frame time
    this.avgFrameTime =
      this.frameTimeHistory.reduce((a, b) => a + b, 0) /
      this.frameTimeHistory.length;

    // Auto-adjust performance mode
    if (this.performanceMode === "auto") {
      if (this.avgFrameTime > 33) {
        // Less than 30 FPS
        this.performanceMode = "fast";
        console.log("🚀 Switching to fast mode for better performance");
      } else if (this.avgFrameTime < 16 && this.performanceMode === "fast") {
        this.performanceMode = "quality";
        console.log("🎨 Switching back to quality mode");
      }
    }
  }

  renderKaraokeSubtitles() {
    const activeSubtitle = this.getActiveSubtitle();
    if (!activeSubtitle) return;

    // Get words for this subtitle
    const words = this.getWordsForSubtitle(activeSubtitle);

    if (words.length === 0) {
      // Fallback: render entire subtitle text
      this.renderFallbackText(activeSubtitle.text);
      return;
    }

    // Update unified renderer with current effects
    this.textRenderer.updateEffects(this.effects);

    // Use unified renderer (same as server)
    this.textRenderer.renderKaraokeText(
      words,
      this.currentTime,
      this.canvas.width,
      this.canvas.height
    );
  }

  getWordProgress(wordData) {
    if (this.currentTime < wordData.start_time) return 0;
    if (this.currentTime > wordData.end_time) return 1;

    const duration = wordData.end_time - wordData.start_time;
    const elapsed = this.currentTime - wordData.start_time;
    return Math.min(1, (elapsed / duration) * this.effects.animationSpeed);
  }

  applyTextEffects() {
    // Reset effects
    this.ctx.shadowBlur = 0;
    this.ctx.shadowOffsetX = 0;
    this.ctx.shadowOffsetY = 0;
    this.ctx.strokeStyle = "transparent";
    this.ctx.lineWidth = 0;

    // Apply shadow if enabled
    if (this.effects.enableShadow) {
      this.ctx.shadowColor = this.effects.shadowColor;
      this.ctx.shadowBlur = this.effects.shadowBlur;
      this.ctx.shadowOffsetX = this.effects.shadowOffsetX;
      this.ctx.shadowOffsetY = this.effects.shadowOffsetY;
    }

    // Apply border if enabled
    if (this.effects.enableBorder) {
      this.ctx.strokeStyle = this.effects.borderColor;
      this.ctx.lineWidth = this.effects.borderWidth;
    }
  }

  renderTextWithEffects(text, x, y, color) {
    // Ultra-simple text rendering - just set color and draw
    this.ctx.fillStyle = color;
    this.ctx.fillText(text, x, y);

    // Only draw border if absolutely necessary
    if (this.effects.enableBorder && this.ctx.lineWidth > 0) {
      this.ctx.strokeText(text, x, y);
    }
  }

  renderHighlightMode(wordData, x, y, progress) {
    const isHighlighted = progress > 0 && progress < 1;
    const color = isHighlighted
      ? this.effects.highlightColor
      : this.effects.primaryColor;

    // Ultra-fast glow - minimal canvas operations
    if (isHighlighted && this.effects.glowIntensity > 0) {
      this.ctx.shadowColor = this.effects.highlightColor;
      this.ctx.shadowBlur = this.effects.glowIntensity;
      this.ctx.fillStyle = color;
      this.ctx.fillText(wordData.word, x, y);
      this.ctx.shadowBlur = 0; // Reset immediately
    } else {
      this.ctx.fillStyle = color;
      this.ctx.fillText(wordData.word, x, y);
    }
  }

  renderGradientMode(wordData, x, y, progress) {
    // Performance-adaptive rendering
    if (this.performanceMode === "fast") {
      // Ultra-fast mode: no glow, simple color change
      const color =
        progress > 0.5
          ? this.effects.highlightColor
          : this.effects.primaryColor;
      this.ctx.fillStyle = color;
      this.ctx.fillText(wordData.word, x, y);
      return;
    }

    // Quality mode: full gradient with optimized glow
    const colorIndex = Math.floor(progress * 100);
    const color = this.gradientColors[colorIndex] || this.effects.primaryColor;

    // Optimized glow rendering
    if (progress > 0 && this.effects.glowIntensity > 0) {
      this.ctx.shadowColor = color;
      this.ctx.shadowBlur = this.effects.glowIntensity;
      this.ctx.fillStyle = color;
      this.ctx.fillText(wordData.word, x, y);
      this.ctx.shadowBlur = 0;
    } else {
      this.ctx.fillStyle = color;
      this.ctx.fillText(wordData.word, x, y);
    }
  }

  renderFillMode(wordData, x, y, progress) {
    const wordWidth = this.ctx.measureText(wordData.word).width;

    // Draw unfilled part first
    this.renderTextWithEffects(wordData.word, x, y, this.effects.primaryColor);

    // Draw filled part with clipping
    if (progress > 0) {
      this.ctx.save();

      // Create clipping region
      this.ctx.beginPath();
      this.ctx.rect(
        x,
        y - this.effects.fontSize / 2,
        wordWidth * progress,
        this.effects.fontSize
      );
      this.ctx.clip();

      // Optimized glow for filled part
      if (this.effects.glowIntensity > 0) {
        this.ctx.shadowColor = this.effects.highlightColor;
        this.ctx.shadowBlur = this.effects.glowIntensity;
        this.ctx.shadowOffsetX = 0;
        this.ctx.shadowOffsetY = 0;
      }

      // Single render of filled part
      this.renderTextWithEffects(
        wordData.word,
        x,
        y,
        this.effects.highlightColor
      );

      this.ctx.restore();
    }
  }

  renderBounceMode(wordData, x, y, progress) {
    // Calculate bounce effect
    const bounceHeight = progress > 0 ? Math.sin(progress * Math.PI) * 20 : 0;
    const scale = progress > 0 ? 1 + Math.sin(progress * Math.PI) * 0.3 : 1;

    this.ctx.save();

    // Get word width for proper centering during scale
    const wordWidth = this.ctx.measureText(wordData.word).width;

    // Translate to word center, apply effects, then translate back
    this.ctx.translate(x + wordWidth / 2, y - bounceHeight);
    this.ctx.scale(scale, scale);
    this.ctx.translate(-wordWidth / 2, 0);

    const color =
      progress > 0 ? this.effects.highlightColor : this.effects.primaryColor;

    // Optimized glow for bouncing words
    if (progress > 0 && this.effects.glowIntensity > 0) {
      this.ctx.shadowColor = this.effects.highlightColor;
      this.ctx.shadowBlur = this.effects.glowIntensity;
      this.ctx.shadowOffsetX = 0;
      this.ctx.shadowOffsetY = 0;

      // Single render with glow
      this.renderTextWithEffects(wordData.word, 0, 0, color);
    } else {
      // No glow, direct render
      this.renderTextWithEffects(wordData.word, 0, 0, color);
    }

    this.ctx.restore();
  }

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

  breakIntoLines(words) {
    if (!this.effects.autoBreak) return [words];

    const lines = [];
    let currentLine = [];
    let currentWidth = 0;

    words.forEach((word, index) => {
      const wordWidth = this.ctx.measureText(word.word).width;
      const spaceWidth = index > 0 ? this.effects.wordSpacing : 0;

      // Check if adding this word would exceed max width
      if (
        currentWidth + spaceWidth + wordWidth > this.effects.maxLineWidth &&
        currentLine.length > 0
      ) {
        // Start new line
        lines.push([...currentLine]);
        currentLine = [word];
        currentWidth = wordWidth;
      } else {
        // Add to current line
        currentLine.push(word);
        currentWidth += spaceWidth + wordWidth;
      }
    });

    // Add the last line
    if (currentLine.length > 0) {
      lines.push(currentLine);
    }

    return lines.length > 0 ? lines : [words];
  }

  renderLine(words, centerX, y) {
    // Calculate individual word widths and total width for this line
    const wordWidths = words.map(
      (word) => this.ctx.measureText(word.word).width
    );
    const totalSpacing = (words.length - 1) * this.effects.wordSpacing;
    const totalWidth =
      wordWidths.reduce((sum, width) => sum + width, 0) + totalSpacing;

    // Start position for left-aligned text, centered as a group
    let currentX = centerX - totalWidth / 2;

    // Render each word with advanced karaoke effects
    words.forEach((wordData, index) => {
      const wordProgress = this.getWordProgress(wordData);

      // Apply karaoke mode effects
      switch (this.effects.karaokeMode) {
        case "highlight":
          this.renderHighlightMode(wordData, currentX, y, wordProgress);
          break;
        case "gradient":
          this.renderGradientMode(wordData, currentX, y, wordProgress);
          break;
        case "fill":
          this.renderFillMode(wordData, currentX, y, wordProgress);
          break;
        case "bounce":
          this.renderBounceMode(wordData, currentX, y, wordProgress);
          break;
      }

      // Move to next word position using pre-calculated width
      currentX += wordWidths[index] + this.effects.wordSpacing;
    });
  }

  renderMultiLineText(text, centerX, baseY, words) {
    // Simple fallback for text without word timing
    const lines = this.effects.autoBreak
      ? this.breakTextIntoLines(text)
      : [text];

    const lineSpacing = this.effects.fontSize * this.effects.lineHeight;
    const totalHeight = (lines.length - 1) * lineSpacing;
    const startY = baseY - totalHeight / 2;

    this.ctx.textAlign = "center";
    this.ctx.fillStyle = this.effects.primaryColor;

    lines.forEach((line, index) => {
      const y = startY + index * lineSpacing;
      this.ctx.fillText(line, centerX, y);
    });
  }

  breakTextIntoLines(text) {
    if (!this.effects.autoBreak) return [text];

    const words = text.split(" ");
    const lines = [];
    let currentLine = "";

    words.forEach((word) => {
      const testLine = currentLine ? `${currentLine} ${word}` : word;
      const testWidth = this.ctx.measureText(testLine).width;

      if (testWidth > this.effects.maxLineWidth && currentLine) {
        lines.push(currentLine);
        currentLine = word;
      } else {
        currentLine = testLine;
      }
    });

    if (currentLine) {
      lines.push(currentLine);
    }

    return lines.length > 0 ? lines : [text];
  }

  async loadCustomFont(event) {
    const file = event.target.files[0];
    if (!file) return;

    const fontStatus = document.getElementById("fontStatus");
    fontStatus.textContent = "Loading font...";
    fontStatus.style.color = "#FFA500";

    try {
      // Create a unique font name
      const fontName = `CustomFont_${Date.now()}`;

      // Create font face for client-side preview
      const fontFace = new FontFace(
        fontName,
        `url(${URL.createObjectURL(file)})`
      );

      // Load the font in browser
      await fontFace.load();

      // Add to document fonts
      document.fonts.add(fontFace);

      // Upload font to server for server-side rendering
      if (this.isServerAvailable && this.serverRenderer) {
        try {
          fontStatus.textContent = "Uploading font to server...";
          fontStatus.style.color = "#FFA500";

          const serverFontName = await this.uploadFontToServer(file);

          // Use server font name for consistency
          this.effects.customFontName = serverFontName;
          this.loadedFonts.add(serverFontName);

          fontStatus.textContent = `✓ ${file.name} loaded (client + server)`;
          fontStatus.style.color = "#4CAF50";

          console.log(`Font loaded on client and server: ${serverFontName}`);
        } catch (serverError) {
          console.warn(
            "Server font upload failed, using client-only:",
            serverError
          );

          // Fallback to client-only font
          this.effects.customFontName = fontName;
          this.loadedFonts.add(fontName);

          fontStatus.textContent = `✓ ${file.name} loaded (client only)`;
          fontStatus.style.color = "#FFA500";
        }
      } else {
        // Server not available, client-only
        this.effects.customFontName = fontName;
        this.loadedFonts.add(fontName);

        fontStatus.textContent = `✓ ${file.name} loaded (client only)`;
        fontStatus.style.color = "#FFA500";
      }
    } catch (error) {
      console.error("Font loading error:", error);
      fontStatus.textContent = `✗ Failed to load ${file.name}`;
      fontStatus.style.color = "#FF6B6B";
      alert(
        "Failed to load font. Please make sure it's a valid font file (.ttf, .otf, .woff, .woff2)"
      );
    }
  }

  getActiveSubtitle() {
    return this.subtitles.find(
      (sub) =>
        this.currentTime >= sub.start_time && this.currentTime <= sub.end_time
    );
  }

  getWordsForSubtitle(subtitle) {
    return this.wordSegments.filter(
      (word) =>
        word.start_time >= subtitle.start_time &&
        word.end_time <= subtitle.end_time
    );
  }

  async startRender() {
    // Debug: Log current state
    console.log("Starting render with state:", {
      inputMode: this.inputMode,
      hasVideo: !!this.video.src,
      hasImageFile: !!this.currentImageFile,
      hasAudioFile: !!this.currentAudioFile,
      uploadedVideoId: this.uploadedVideoId,
      isServerAvailable: this.isServerAvailable,
    });

    // Check if we have the required media based on input mode
    if (this.inputMode === "video" && !this.video.src) {
      alert("Please load a video file first!");
      return;
    } else if (
      this.inputMode === "imageAudio" &&
      (!this.currentImageFile || !this.currentAudioFile)
    ) {
      alert("Please load both image and audio files first!");
      return;
    }

    // Check browser compatibility
    if (!this.checkRenderSupport()) {
      return;
    }

    const renderBtn = document.getElementById("renderBtn");
    const progressDiv = document.getElementById("renderProgress");
    const progressFill = document.getElementById("progressFill");
    const progressText = document.getElementById("progressText");

    if (!progressFill || !progressText) {
      alert("Progress bar elements not found. Please refresh the page.");
      return;
    }

    // Get render settings
    const resolution = document.getElementById("renderResolution").value;
    const frameRate = parseInt(
      document.getElementById("renderFrameRate").value
    );
    const quality = document.getElementById("renderQuality").value;
    const format = document.getElementById("renderFormat").value;
    const renderMode = document.getElementById("renderMode").value;

    // Disable render button and show progress
    renderBtn.disabled = true;
    renderBtn.textContent = "🎬 Rendering...";
    progressDiv.style.display = "block";

    // Initialize progress display
    progressFill.style.width = "0%";
    progressText.textContent = "Initializing render...";

    try {
      // Choose rendering method based on mode
      switch (renderMode) {
        case "server":
          await this.renderVideoOnServer(
            resolution,
            frameRate,
            quality,
            format,
            (progress, status) => {
              // Update progress bar
              if (progressFill && progressText) {
                progressFill.style.width = progress + "%";
                progressText.textContent = status;
              }
            }
          );
          break;
        default: // realtime
          await this.renderVideoRealtime(
            resolution,
            frameRate,
            quality,
            format,
            (progress, status) => {
              progressFill.style.width = progress + "%";
              progressText.textContent = status;
            }
          );
      }
    } catch (error) {
      console.error("Render error:", error);

      // Try fallback method for unsupported browsers
      if (
        error.message.includes("MediaRecorder") ||
        error.message.includes("captureStream")
      ) {
        alert(
          "Your browser doesn't support direct video recording. Trying alternative method..."
        );
        try {
          // Use realtime fallback for all client-side rendering
          await this.renderVideoRealtimeFallback(
            resolution,
            frameRate,
            quality,
            format,
            (progress, status) => {
              progressFill.style.width = progress + "%";
              progressText.textContent = status;
            }
          );
        } catch (fallbackError) {
          console.error("Fallback render error:", fallbackError);
          alert(
            "Video export failed. Please try using a modern browser like Chrome, Firefox, or Edge."
          );
        }
      } else {
        alert("Render failed: " + error.message);
      }
    } finally {
      // Only reset UI for non-server renders
      // Server renders will reset UI when they complete via the progress callback
      if (renderMode !== "server") {
        renderBtn.disabled = false;
        renderBtn.textContent = "🎬 Start Render";
        progressDiv.style.display = "none";
      }
    }
  }

  checkRenderSupport() {
    // Check for required APIs
    const hasMediaRecorder = typeof MediaRecorder !== "undefined";
    const hasCaptureStream = HTMLCanvasElement.prototype.captureStream;

    if (!hasMediaRecorder || !hasCaptureStream) {
      const missingFeatures = [];
      if (!hasMediaRecorder) missingFeatures.push("MediaRecorder API");
      if (!hasCaptureStream) missingFeatures.push("Canvas captureStream");

      alert(`⚠️ Browser Compatibility Issue

Your browser is missing support for: ${missingFeatures.join(", ")}

For best results, please use:
• Chrome 47+ 
• Firefox 29+
• Edge 79+
• Safari 14.1+

The app will attempt to use a fallback method, but video quality may be reduced.`);

      return true; // Still allow fallback attempt
    }

    return true;
  }

  async renderVideo(resolution, frameRate, quality, format, progressCallback) {
    // Get resolution dimensions
    const resolutions = {
      "720p": { width: 1280, height: 720 },
      "1080p": { width: 1920, height: 1080 },
      "4k": { width: 3840, height: 2160 },
    };

    const { width, height } = resolutions[resolution];
    const duration = this.video.duration;
    const totalFrames = Math.ceil(duration * frameRate);
    const frameInterval = 1 / frameRate;

    progressCallback(0, "Preparing fast frame-by-frame render...");

    // Create offscreen canvas for rendering (IDENTICAL to preview canvas)
    const offscreenCanvas = document.createElement("canvas");
    offscreenCanvas.width = width;
    offscreenCanvas.height = height;
    const offscreenCtx = offscreenCanvas.getContext("2d");

    // Store original canvas context and video state
    const originalCtx = this.ctx;
    const originalCanvas = this.canvas;
    const originalTime = this.video.currentTime;
    const originalPaused = this.video.paused;

    // Temporarily use offscreen canvas (SAME rendering pipeline as preview)
    this.canvas = offscreenCanvas;
    this.ctx = offscreenCtx;

    progressCallback(5, "Capturing frames...");

    const frames = [];
    let audioBlob = null;

    // Extract audio first (if available)
    try {
      audioBlob = await this.extractAudioTrack();
      console.log("Audio extracted successfully");
    } catch (error) {
      console.warn("Could not extract audio:", error);
    }

    // Fast frame-by-frame capture
    for (let i = 0; i < totalFrames; i++) {
      const targetTime = i * frameInterval;

      // Seek to exact frame position
      this.video.currentTime = targetTime;
      this.currentTime = targetTime; // Update app time to match

      // Wait for video to seek to exact position
      await this.waitForPreciseSeek(targetTime);

      // Render frame using IDENTICAL pipeline as preview
      this.renderFrame(); // Same method used for preview!

      // Capture frame as high-quality image
      const frameBlob = await new Promise((resolve) => {
        offscreenCanvas.toBlob(
          resolve,
          "image/png", // PNG for lossless quality
          1.0 // Maximum quality
        );
      });

      frames.push(frameBlob);

      // Update progress
      const progress = 5 + (i / totalFrames) * 80;
      progressCallback(
        progress,
        `Capturing frame ${i + 1}/${totalFrames} (${this.formatTime(
          targetTime
        )})`
      );
    }

    progressCallback(85, "Encoding video...");

    // Create video from frames using fast encoding
    const videoBlob = await this.encodeFramesToVideo(
      frames,
      frameRate,
      quality,
      format,
      audioBlob,
      (progress) => {
        progressCallback(85 + progress * 0.15, "Encoding video...");
      }
    );

    // Restore original state
    this.canvas = originalCanvas;
    this.ctx = originalCtx;
    this.video.currentTime = originalTime;
    this.currentTime = originalTime;
    if (originalPaused) {
      this.video.pause();
    }

    // Download the result
    this.downloadVideo(videoBlob);

    progressCallback(
      100,
      `Fast render complete! ${totalFrames} frames processed`
    );
  }

  async renderVideoRealtime(
    resolution,
    frameRate,
    quality,
    format,
    progressCallback
  ) {
    // Get resolution dimensions
    const resolutions = {
      "720p": { width: 1280, height: 720 },
      "1080p": { width: 1920, height: 1080 },
      "4k": { width: 3840, height: 2160 },
    };

    const { width, height } = resolutions[resolution];
    const duration = this.video.duration;

    progressCallback(0, "Preparing real-time render...");

    // Create offscreen canvas for rendering
    const offscreenCanvas = document.createElement("canvas");
    offscreenCanvas.width = width;
    offscreenCanvas.height = height;
    const offscreenCtx = offscreenCanvas.getContext("2d");

    // Store original canvas context
    const originalCtx = this.ctx;
    const originalCanvas = this.canvas;

    // Temporarily use offscreen canvas
    this.canvas = offscreenCanvas;
    this.ctx = offscreenCtx;

    progressCallback(10, "Setting up video recording...");

    // Create MediaRecorder for video export with audio
    const videoStream = offscreenCanvas.captureStream(frameRate);
    let combinedStream = videoStream;

    // Try to capture audio from the video element
    try {
      if (this.video.captureStream) {
        const audioStream = this.video.captureStream();
        const audioTracks = audioStream.getAudioTracks();

        if (audioTracks.length > 0) {
          // Combine video and audio streams
          combinedStream = new MediaStream([
            ...videoStream.getVideoTracks(),
            ...audioTracks,
          ]);
          console.log("Audio track added to export");
        }
      }
    } catch (error) {
      console.warn("Could not capture audio:", error);
      // Continue with video-only export
    }

    const chunks = [];

    // Set quality based on user selection
    const qualitySettings = {
      high: { videoBitsPerSecond: 8000000, audioBitsPerSecond: 128000 },
      medium: { videoBitsPerSecond: 4000000, audioBitsPerSecond: 96000 },
      low: { videoBitsPerSecond: 2000000, audioBitsPerSecond: 64000 },
    };

    // Get the best supported video format
    const mimeType = this.getSupportedVideoFormat(format);

    const mediaRecorder = new MediaRecorder(combinedStream, {
      mimeType: mimeType,
      ...qualitySettings[quality],
    });

    // Collect video chunks
    mediaRecorder.ondataavailable = (event) => {
      if (event.data.size > 0) {
        chunks.push(event.data);
      }
    };

    // Handle recording completion
    const recordingComplete = new Promise((resolve) => {
      mediaRecorder.onstop = () => {
        const blob = new Blob(chunks, { type: mimeType });
        this.downloadVideo(blob);
        resolve();
      };
    });

    // Start recording
    mediaRecorder.start();
    progressCallback(20, "Recording video in real-time...");

    // Store original video time and state
    const originalTime = this.video.currentTime;
    const originalPaused = this.video.paused;
    const originalPlaybackRate = this.video.playbackRate;

    // Start video playback from beginning
    this.video.currentTime = 0;
    this.currentTime = 0;

    // Play the video and let it render naturally
    await new Promise((resolve) => {
      this.video.onended = resolve;
      this.video.ontimeupdate = () => {
        this.currentTime = this.video.currentTime;
        const progress = 20 + (this.currentTime / duration) * 60;
        progressCallback(
          progress,
          `Recording: ${this.formatTime(this.currentTime)} / ${this.formatTime(
            duration
          )}`
        );
      };
      this.video.play();
    });

    progressCallback(85, "Finalizing video...");

    // Stop recording
    mediaRecorder.stop();

    // Wait for recording to complete
    await recordingComplete;

    // Restore original video state
    this.video.currentTime = originalTime;
    this.currentTime = originalTime;
    this.video.playbackRate = originalPlaybackRate;
    if (originalPaused) {
      this.video.pause();
    }

    // Restore original canvas
    this.canvas = originalCanvas;
    this.ctx = originalCtx;

    progressCallback(100, `Real-time render complete! Format: ${mimeType}`);
  }

  async renderVideoFallback(
    resolution,
    frameRate,
    quality,
    format,
    progressCallback
  ) {
    // Fallback method: capture frames and create image sequence
    const resolutions = {
      "720p": { width: 1280, height: 720 },
      "1080p": { width: 1920, height: 1080 },
      "4k": { width: 3840, height: 2160 },
    };

    const { width, height } = resolutions[resolution];
    const duration = this.video.duration;
    const totalFrames = Math.ceil(duration * frameRate);

    progressCallback(0, "Preparing fallback render...");

    // Create offscreen canvas for rendering
    const offscreenCanvas = document.createElement("canvas");
    offscreenCanvas.width = width;
    offscreenCanvas.height = height;
    const offscreenCtx = offscreenCanvas.getContext("2d");

    // Store original canvas context
    const originalCtx = this.ctx;
    const originalCanvas = this.canvas;

    // Temporarily use offscreen canvas
    this.canvas = offscreenCanvas;
    this.ctx = offscreenCtx;

    const frames = [];
    const frameInterval = 1 / frameRate;

    progressCallback(10, "Capturing frames...");

    // Capture frames
    for (let i = 0; i < totalFrames; i++) {
      const currentTime = i * frameInterval;

      // Set video time
      this.video.currentTime = currentTime;
      this.currentTime = currentTime;

      // Wait for video to seek
      await new Promise((resolve) => {
        const checkSeek = () => {
          if (Math.abs(this.video.currentTime - currentTime) < 0.1) {
            resolve();
          } else {
            setTimeout(checkSeek, 10);
          }
        };
        checkSeek();
      });

      // Render frame
      this.renderFrame();

      // Capture frame as blob
      const frameBlob = await new Promise((resolve) => {
        offscreenCanvas.toBlob(
          resolve,
          "image/jpeg",
          quality === "high" ? 0.95 : quality === "medium" ? 0.8 : 0.6
        );
      });
      frames.push(frameBlob);

      // Update progress
      const progress = 10 + (i / totalFrames) * 70;
      progressCallback(progress, `Capturing frame ${i + 1}/${totalFrames}`);
    }

    // Restore original canvas
    this.canvas = originalCanvas;
    this.ctx = originalCtx;

    progressCallback(85, "Creating image sequence download...");

    // Create ZIP file with all frames
    await this.downloadFrameSequence(frames, frameRate);

    progressCallback(100, "Frame sequence export complete!");
  }

  async downloadFrameSequence(frames, frameRate) {
    // Since we can't create a video directly, we'll download the first few frames as samples
    // and provide instructions for creating video with external tools

    const timestamp = new Date().toISOString().replace(/[:.]/g, "-");

    // Download first frame as sample
    const firstFrameUrl = URL.createObjectURL(frames[0]);
    const link = document.createElement("a");
    link.href = firstFrameUrl;
    link.download = `karaoke-frame-001-${timestamp}.jpg`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    // Download middle frame as sample
    if (frames.length > 1) {
      const midFrame = frames[Math.floor(frames.length / 2)];
      const midFrameUrl = URL.createObjectURL(midFrame);
      const midLink = document.createElement("a");
      midLink.href = midFrameUrl;
      midLink.download = `karaoke-frame-mid-${timestamp}.jpg`;
      document.body.appendChild(midLink);
      midLink.click();
      document.body.removeChild(midLink);
    }

    // Clean up URLs
    setTimeout(() => {
      URL.revokeObjectURL(firstFrameUrl);
    }, 1000);

    // Show completion message with instructions
    setTimeout(() => {
      alert(`📸 Frame Sequence Export Complete!

Sample frames downloaded: 
• karaoke-frame-001-${timestamp}.jpg
• karaoke-frame-mid-${timestamp}.jpg

Total frames captured: ${frames.length}
Frame rate: ${frameRate} FPS

To create a full video:
1. Use video editing software like:
   • FFmpeg (command line)
   • DaVinci Resolve (free)
   • Adobe Premiere Pro
   • Any video editor that supports image sequences

2. Import the frame sequence at ${frameRate} FPS
3. Add your original audio track
4. Export as MP4 or your preferred format

Note: For direct video export, please use a modern browser with MediaRecorder support.`);
    }, 500);
  }

  downloadVideo(blob) {
    // Create download link
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;

    // Generate filename with timestamp and correct extension
    const timestamp = new Date().toISOString().replace(/[:.]/g, "-");
    const extension = this.getFileExtension(blob.type);
    link.download = `karaoke-video-${timestamp}.${extension}`;

    // Trigger download
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    // Clean up URL
    setTimeout(() => {
      URL.revokeObjectURL(url);
    }, 1000);

    // Show completion message
    setTimeout(() => {
      alert(`🎉 Video Export Complete!

Your karaoke video has been downloaded as: karaoke-video-${timestamp}.${extension}

The video includes:
✅ Full video with synchronized karaoke effects
✅ Original audio track preserved
✅ All your custom styling and animations
✅ High-quality rendering at your selected resolution
✅ Format: ${blob.type}

You can now share your karaoke video or convert it to other formats if needed!`);
    }, 500);
  }

  populateTranscript() {
    const transcriptList = document.getElementById("transcriptList");
    transcriptList.innerHTML = "";

    this.subtitles.forEach((subtitle, index) => {
      const lineElement = this.createTranscriptLine(subtitle, index);
      transcriptList.appendChild(lineElement);
    });
  }

  createTranscriptLine(subtitle, index) {
    const lineDiv = document.createElement("div");
    lineDiv.className = "transcript-line";
    lineDiv.dataset.index = index;

    lineDiv.innerHTML = `
      <div class="line-header">
        <div class="line-times">
          <div>
            <label>Start:</label>
            <input type="number" class="time-input start-time" step="0.001" value="${subtitle.start_time}" />
          </div>
          <div>
            <label>End:</label>
            <input type="number" class="time-input end-time" step="0.001" value="${subtitle.end_time}" />
          </div>
        </div>
        <button class="delete-line">🗑️</button>
      </div>
      <div class="line-content">
        <div class="content-display">${subtitle.text}</div>
      </div>
      <div class="word-editor" style="display: none;">
        <div class="word-editor-header">
          <span>Edit Words:</span>
          <div class="word-editor-controls">
            <button class="add-word-btn">➕ Add Word</button>
            <button class="save-words-btn">✅ Save</button>
            <button class="cancel-edit-btn">❌ Cancel</button>
          </div>
        </div>
        <div class="word-blocks"></div>
        <div class="word-timing" style="display: none;">
          <div class="word-timing-inputs">
            <label>Word:</label>
            <input type="text" class="word-text-input" />
            <label>Start:</label>
            <input type="number" class="word-start-time time-input" step="0.001" />
            <label>End:</label>
            <input type="number" class="word-end-time time-input" step="0.001" />
            <button class="apply-word-timing">Apply</button>
            <button class="delete-word-btn">🗑️ Delete</button>
          </div>
        </div>
      </div>
    `;

    this.addTranscriptLineListeners(lineDiv, subtitle, index);
    return lineDiv;
  }

  addTranscriptLineListeners(lineDiv, subtitle, index) {
    // Double-click to enter word editing mode
    lineDiv.addEventListener("dblclick", () => {
      this.jumpToSubtitle(subtitle);
      this.enterWordEditMode(lineDiv, index);
    });

    const startTimeInput = lineDiv.querySelector(".start-time");
    const endTimeInput = lineDiv.querySelector(".end-time");

    startTimeInput.addEventListener("change", () => {
      const newStartTime = this.parseTime(startTimeInput.value);
      this.updateSubtitleTiming(index, newStartTime, subtitle.end_time);
    });

    endTimeInput.addEventListener("change", () => {
      const newEndTime = this.parseTime(endTimeInput.value);
      this.updateSubtitleTiming(index, subtitle.start_time, newEndTime);
    });

    const deleteBtn = lineDiv.querySelector(".delete-line");
    deleteBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      this.deleteSubtitleLine(index);
    });

    // Word editor controls
    const addWordBtn = lineDiv.querySelector(".add-word-btn");
    const saveWordsBtn = lineDiv.querySelector(".save-words-btn");
    const cancelEditBtn = lineDiv.querySelector(".cancel-edit-btn");

    addWordBtn.addEventListener("click", () => this.addNewWord(lineDiv, index));
    saveWordsBtn.addEventListener("click", () =>
      this.saveWordChanges(lineDiv, index)
    );
    cancelEditBtn.addEventListener("click", () =>
      this.cancelWordEdit(lineDiv, index)
    );
  }

  enterWordEditMode(lineDiv, subtitleIndex) {
    // Clear other editing states
    document.querySelectorAll(".transcript-line").forEach((line) => {
      line.classList.remove("editing");
      line.querySelector(".word-editor").style.display = "none";
    });

    lineDiv.classList.add("editing");
    this.currentEditingLine = subtitleIndex;

    const wordEditor = lineDiv.querySelector(".word-editor");
    const wordBlocks = lineDiv.querySelector(".word-blocks");

    wordEditor.style.display = "block";
    wordBlocks.innerHTML = "";

    const subtitle = this.subtitles[subtitleIndex];
    const words = this.getWordsForSubtitle(subtitle);

    // Create editable word blocks
    words.forEach((word, wordIndex) => {
      this.createWordBlock(wordBlocks, word, wordIndex, subtitleIndex);
    });

    // If no words exist, create from text
    if (words.length === 0) {
      this.createWordsFromText(wordBlocks, subtitle, subtitleIndex);
    }
  }

  createWordBlock(container, wordData, wordIndex, subtitleIndex) {
    const wordBlock = document.createElement("div");
    wordBlock.className = "word-block";
    wordBlock.textContent = wordData.word;
    wordBlock.dataset.wordIndex = wordIndex;
    wordBlock.draggable = true;

    wordBlock.addEventListener("click", () => {
      this.selectWordForEdit(wordBlock, wordData, subtitleIndex, wordIndex);
    });

    // Add drag and drop for reordering
    wordBlock.addEventListener("dragstart", (e) => {
      e.dataTransfer.setData("text/plain", wordIndex);
      wordBlock.classList.add("dragging");
    });

    wordBlock.addEventListener("dragend", () => {
      wordBlock.classList.remove("dragging");
    });

    wordBlock.addEventListener("dragover", (e) => {
      e.preventDefault();
    });

    wordBlock.addEventListener("drop", (e) => {
      e.preventDefault();
      const draggedIndex = parseInt(e.dataTransfer.getData("text/plain"));
      this.reorderWords(subtitleIndex, draggedIndex, wordIndex);
    });

    container.appendChild(wordBlock);
  }

  createWordsFromText(container, subtitle, subtitleIndex) {
    const words = subtitle.text.split(/\s+/).filter((word) => word.trim());
    const duration = subtitle.end_time - subtitle.start_time;
    const wordDuration = duration / words.length;

    words.forEach((word, index) => {
      const wordData = {
        word: word,
        start_time: subtitle.start_time + index * wordDuration,
        end_time: subtitle.start_time + (index + 1) * wordDuration,
      };

      // Add to word segments
      this.wordSegments.push(wordData);
      this.createWordBlock(
        container,
        wordData,
        this.wordSegments.length - 1,
        subtitleIndex
      );
    });
  }

  selectWordForEdit(wordBlock, wordData, subtitleIndex, wordIndex) {
    document.querySelectorAll(".word-block").forEach((block) => {
      block.classList.remove("selected");
    });

    wordBlock.classList.add("selected");
    this.selectedWord = { wordData, subtitleIndex, wordIndex };

    const wordTiming = wordBlock
      .closest(".word-editor")
      .querySelector(".word-timing");
    const textInput = wordTiming.querySelector(".word-text-input");
    const startInput = wordTiming.querySelector(".word-start-time");
    const endInput = wordTiming.querySelector(".word-end-time");

    textInput.value = wordData.word;
    startInput.value = wordData.start_time;
    endInput.value = wordData.end_time;

    wordTiming.style.display = "block";

    const applyBtn = wordTiming.querySelector(".apply-word-timing");
    const deleteBtn = wordTiming.querySelector(".delete-word-btn");

    applyBtn.onclick = () => {
      const newText = textInput.value.trim();
      const newStartTime = this.parseTime(startInput.value);
      const newEndTime = this.parseTime(endInput.value);
      this.updateWordData(
        subtitleIndex,
        wordIndex,
        newText,
        newStartTime,
        newEndTime
      );
    };

    deleteBtn.onclick = () => {
      this.deleteWord(subtitleIndex, wordIndex);
    };
  }

  addNewWord(lineDiv, subtitleIndex) {
    const subtitle = this.subtitles[subtitleIndex];
    const words = this.getWordsForSubtitle(subtitle);

    const newWordData = {
      word: "new",
      start_time: subtitle.end_time - 1,
      end_time: subtitle.end_time,
    };

    this.wordSegments.push(newWordData);

    const wordBlocks = lineDiv.querySelector(".word-blocks");
    this.createWordBlock(
      wordBlocks,
      newWordData,
      this.wordSegments.length - 1,
      subtitleIndex
    );
  }

  saveWordChanges(lineDiv, subtitleIndex) {
    // Rebuild line text from words
    const words = this.getWordsForSubtitle(this.subtitles[subtitleIndex]);
    const newText = words.map((w) => w.word).join(" ");

    this.subtitles[subtitleIndex].text = newText;

    // Update display
    const contentDisplay = lineDiv.querySelector(".content-display");
    contentDisplay.textContent = newText;

    // Exit edit mode
    this.exitWordEditMode(lineDiv);

    console.log(`Saved changes for line ${subtitleIndex}: "${newText}"`);
  }

  cancelWordEdit(lineDiv, subtitleIndex) {
    // Just exit without saving
    this.exitWordEditMode(lineDiv);
  }

  exitWordEditMode(lineDiv) {
    lineDiv.classList.remove("editing");
    lineDiv.querySelector(".word-editor").style.display = "none";
    lineDiv.querySelector(".word-timing").style.display = "none";
    this.currentEditingLine = null;
    this.selectedWord = null;
  }

  updateWordData(subtitleIndex, wordIndex, newText, newStartTime, newEndTime) {
    const words = this.getWordsForSubtitle(this.subtitles[subtitleIndex]);
    const targetWord = words[wordIndex];

    if (!targetWord) return;

    const globalWordIndex = this.wordSegments.findIndex(
      (w) => w === targetWord
    );
    if (globalWordIndex === -1) return;

    // Update word data
    this.wordSegments[globalWordIndex].word = newText;
    this.wordSegments[globalWordIndex].start_time = newStartTime;
    this.wordSegments[globalWordIndex].end_time = newEndTime;

    // Update the word block display
    const lineDiv = document.querySelector(`[data-index="${subtitleIndex}"]`);
    const wordBlocks = lineDiv.querySelector(".word-blocks");
    const wordBlock = wordBlocks.children[wordIndex];
    if (wordBlock) {
      wordBlock.textContent = newText;
    }

    // Hide timing panel
    lineDiv.querySelector(".word-timing").style.display = "none";

    console.log(`Updated word: "${newText}" ${newStartTime}s - ${newEndTime}s`);
  }

  deleteWord(subtitleIndex, wordIndex) {
    if (confirm("Delete this word?")) {
      const words = this.getWordsForSubtitle(this.subtitles[subtitleIndex]);
      const targetWord = words[wordIndex];

      if (!targetWord) return;

      const globalWordIndex = this.wordSegments.findIndex(
        (w) => w === targetWord
      );
      if (globalWordIndex !== -1) {
        this.wordSegments.splice(globalWordIndex, 1);
      }

      // Refresh word editor
      const lineDiv = document.querySelector(`[data-index="${subtitleIndex}"]`);
      this.enterWordEditMode(lineDiv, subtitleIndex);
    }
  }

  reorderWords(subtitleIndex, fromIndex, toIndex) {
    const words = this.getWordsForSubtitle(this.subtitles[subtitleIndex]);
    if (
      fromIndex === toIndex ||
      fromIndex >= words.length ||
      toIndex >= words.length
    )
      return;

    // Move word in wordSegments array
    const wordToMove = words[fromIndex];
    const globalFromIndex = this.wordSegments.findIndex(
      (w) => w === wordToMove
    );

    if (globalFromIndex === -1) return;

    // Remove from old position
    this.wordSegments.splice(globalFromIndex, 1);

    // Find new position
    const targetWord = words[toIndex];
    const globalToIndex = this.wordSegments.findIndex((w) => w === targetWord);

    // Insert at new position
    this.wordSegments.splice(globalToIndex, 0, wordToMove);

    // Refresh display
    const lineDiv = document.querySelector(`[data-index="${subtitleIndex}"]`);
    this.enterWordEditMode(lineDiv, subtitleIndex);
  }

  updateSubtitleTiming(subtitleIndex, newStartTime, newEndTime) {
    const subtitle = this.subtitles[subtitleIndex];
    const oldDuration = subtitle.end_time - subtitle.start_time;
    const newDuration = newEndTime - newStartTime;

    subtitle.start_time = newStartTime;
    subtitle.end_time = newEndTime;

    const words = this.getWordsForSubtitle(subtitle);
    words.forEach((word) => {
      const wordIndex = this.wordSegments.findIndex((w) => w === word);
      if (wordIndex !== -1) {
        const relativeStart =
          (word.start_time - subtitle.start_time) / oldDuration;
        const relativeEnd = (word.end_time - subtitle.start_time) / oldDuration;

        this.wordSegments[wordIndex].start_time =
          newStartTime + relativeStart * newDuration;
        this.wordSegments[wordIndex].end_time =
          newStartTime + relativeEnd * newDuration;
      }
    });
  }

  updateWordTiming(subtitleIndex, wordIndex, newStartTime, newEndTime) {
    const subtitle = this.subtitles[subtitleIndex];
    const words = this.getWordsForSubtitle(subtitle);
    const targetWord = words[wordIndex];

    if (!targetWord) return;

    const globalWordIndex = this.wordSegments.findIndex(
      (w) => w === targetWord
    );
    if (globalWordIndex === -1) return;

    const timeDelta = newStartTime - targetWord.start_time;

    this.wordSegments[globalWordIndex].start_time = newStartTime;
    this.wordSegments[globalWordIndex].end_time = newEndTime;

    words.forEach((word, idx) => {
      if (idx !== wordIndex) {
        const globalIdx = this.wordSegments.findIndex((w) => w === word);
        if (globalIdx !== -1) {
          const factor = idx < wordIndex ? 0.3 : 0.3;
          this.wordSegments[globalIdx].start_time += timeDelta * factor;
          this.wordSegments[globalIdx].end_time += timeDelta * factor;
        }
      }
    });

    this.showWordEditor(
      document.querySelector(`[data-index="${subtitleIndex}"]`),
      subtitleIndex
    );
  }

  jumpToSubtitle(subtitle) {
    this.video.currentTime = subtitle.start_time;
    this.currentTime = subtitle.start_time;
    this.updateTimeDisplay();

    document.querySelectorAll(".transcript-line").forEach((line) => {
      line.classList.remove("active");
    });

    const activeIndex = this.subtitles.findIndex((s) => s === subtitle);
    if (activeIndex !== -1) {
      const activeLine = document.querySelector(
        `[data-index="${activeIndex}"]`
      );
      if (activeLine) {
        activeLine.classList.add("active");
        activeLine.scrollIntoView({ behavior: "smooth", block: "center" });
      }
    }
  }

  addNewLine() {
    const newSubtitle = {
      start_time: this.currentTime,
      end_time: this.currentTime + 3,
      text: "New subtitle line",
    };

    this.subtitles.push(newSubtitle);
    this.subtitles.sort((a, b) => a.start_time - b.start_time);
    this.populateTranscript();
  }

  deleteSubtitleLine(index) {
    if (confirm("Are you sure you want to delete this subtitle line?")) {
      const subtitle = this.subtitles[index];
      const wordsToRemove = this.getWordsForSubtitle(subtitle);

      wordsToRemove.forEach((word) => {
        const wordIndex = this.wordSegments.findIndex((w) => w === word);
        if (wordIndex !== -1) {
          this.wordSegments.splice(wordIndex, 1);
        }
      });

      this.subtitles.splice(index, 1);
      this.populateTranscript();
    }
  }

  parseTime(timeString) {
    // Parse decimal seconds directly
    return parseFloat(timeString) || 0;
  }

  saveSubtitle() {
    const data = {
      segments: this.subtitles,
      word_segments: this.wordSegments,
    };

    this.downloadJSON(data, "subtitles.json");
    alert("Subtitle saved as subtitles.json");
  }

  saveAsCopy() {
    const data = {
      segments: this.subtitles,
      word_segments: this.wordSegments,
    };

    const timestamp = new Date().toISOString().replace(/[:.]/g, "-");
    this.downloadJSON(data, `subtitles_copy_${timestamp}.json`);
    alert(`Subtitle copy saved as subtitles_copy_${timestamp}.json`);
  }

  resetToOriginal() {
    if (
      confirm(
        "Are you sure you want to reset all changes and restore the original subtitle file?"
      )
    ) {
      if (this.originalSubtitleData) {
        this.subtitles = [...(this.originalSubtitleData.segments || [])];
        this.wordSegments = [
          ...(this.originalSubtitleData.word_segments || []),
        ];
        this.populateTranscript();
        alert("Subtitles reset to original version");
      } else {
        alert("No original subtitle data available to reset to");
      }
    }
  }

  initializeCollapsibleSections() {
    // Add click handlers for collapsible headers
    document.querySelectorAll(".collapsible-header").forEach((header) => {
      header.addEventListener("click", () => {
        const section = header.dataset.section;
        const content = document.getElementById(`${section}-content`);
        const isCollapsed = header.classList.contains("collapsed");

        if (isCollapsed) {
          // Expand
          content.style.maxHeight = content.scrollHeight + "px";
          header.classList.remove("collapsed");
          setTimeout(() => {
            content.style.maxHeight = "1000px"; // Allow for dynamic content
          }, 300);
        } else {
          // Collapse
          content.style.maxHeight = content.scrollHeight + "px";
          setTimeout(() => {
            content.style.maxHeight = "0px";
            header.classList.add("collapsed");
          }, 10);
        }
      });
    });

    // Set default collapsed state (keep Typography open by default)
    const defaultCollapsed = ["effects", "layout", "presets"];
    defaultCollapsed.forEach((section) => {
      const content = document.getElementById(`${section}-content`);
      const header = document.querySelector(`[data-section="${section}"]`);
      if (content && header) {
        content.style.maxHeight = "0px";
        header.classList.add("collapsed");
      }
    });

    // Ensure open sections have proper height
    const defaultOpen = ["typography"];
    defaultOpen.forEach((section) => {
      const content = document.getElementById(`${section}-content`);
      if (content) {
        content.style.maxHeight = "1000px";
      }
    });
  }

  initializePresets() {
    // Load saved presets from localStorage
    this.loadPresetsFromStorage();

    // Add preset event listeners
    document
      .getElementById("savePreset")
      .addEventListener("click", () => this.saveCurrentPreset());
    document
      .getElementById("loadPreset")
      .addEventListener("click", () => this.loadSelectedPreset());
    document
      .getElementById("deletePreset")
      .addEventListener("click", () => this.deleteSelectedPreset());
    document
      .getElementById("exportPresets")
      .addEventListener("click", () => this.exportAllPresets());
    document
      .getElementById("importPresetsBtn")
      .addEventListener("click", () => {
        document.getElementById("importPresets").click();
      });
    document
      .getElementById("importPresets")
      .addEventListener("change", (e) => this.importPresets(e));
    document
      .getElementById("resetPresets")
      .addEventListener("click", () => this.resetAllPresets());

    // Built-in preset buttons
    document.querySelectorAll(".builtin-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        const presetName = btn.dataset.preset;
        this.loadBuiltinPreset(presetName);
      });
    });

    // Update preset list and add to collapsed sections
    this.updatePresetList();
  }

  createBuiltinPresets() {
    return {
      classic: {
        name: "Classic Karaoke",
        fontFamily: "Arial",
        fontSize: 48,
        fontWeight: "bold",
        primaryColor: "#ffffff",
        highlightColor: "#ffff00",
        karaokeMode: "highlight",
        enableBorder: true,
        borderWidth: 2,
        borderColor: "#000000",
        enableShadow: true,
        shadowBlur: 4,
        shadowColor: "#000000",
        shadowOffsetX: 2,
        shadowOffsetY: 2,
        glowIntensity: 15,
        animationSpeed: 1,
      },
      modern: {
        name: "Modern Glow",
        fontFamily: "Impact",
        fontSize: 56,
        fontWeight: "bold",
        primaryColor: "#ffffff",
        highlightColor: "#00ffff",
        karaokeMode: "gradient",
        enableBorder: false,
        enableShadow: true,
        shadowBlur: 8,
        shadowColor: "#0066cc",
        shadowOffsetX: 0,
        shadowOffsetY: 0,
        glowIntensity: 25,
        animationSpeed: 1.2,
      },
      retro: {
        name: "Retro Style",
        fontFamily: "Georgia",
        fontSize: 52,
        fontWeight: "bold",
        primaryColor: "#ff6b9d",
        highlightColor: "#ffd93d",
        karaokeMode: "bounce",
        enableBorder: true,
        borderWidth: 3,
        borderColor: "#8b00ff",
        enableShadow: true,
        shadowBlur: 6,
        shadowColor: "#ff1493",
        shadowOffsetX: 3,
        shadowOffsetY: 3,
        glowIntensity: 20,
        animationSpeed: 0.8,
      },
      minimal: {
        name: "Minimal Clean",
        fontFamily: "Verdana",
        fontSize: 44,
        fontWeight: "normal",
        primaryColor: "#333333",
        highlightColor: "#007acc",
        karaokeMode: "fill",
        enableBorder: false,
        enableShadow: false,
        glowIntensity: 0,
        animationSpeed: 1.5,
      },
    };
  }

  getCurrentSettings() {
    return {
      fontFamily: this.effects.fontFamily,
      customFontName: this.effects.customFontName,
      fontSize: this.effects.fontSize,
      fontWeight: this.effects.fontWeight,
      textPosition: this.effects.textPosition,
      verticalPosition: this.effects.verticalPosition,
      positionX: this.effects.positionX,
      positionY: this.effects.positionY,
      karaokeMode: this.effects.karaokeMode,
      primaryColor: this.effects.primaryColor,
      highlightColor: this.effects.highlightColor,
      animationSpeed: this.effects.animationSpeed,
      glowIntensity: this.effects.glowIntensity,
      glowColor: this.effects.glowColor,
      glowOpacity: this.effects.glowOpacity,
      wordSpacing: this.effects.wordSpacing,
      maxLineWidth: this.effects.maxLineWidth,
      lineHeight: this.effects.lineHeight,
      autoBreak: this.effects.autoBreak,
      enableBorder: this.effects.enableBorder,
      borderWidth: this.effects.borderWidth,
      borderColor: this.effects.borderColor,
      enableShadow: this.effects.enableShadow,
      shadowBlur: this.effects.shadowBlur,
      shadowColor: this.effects.shadowColor,
      shadowOffsetX: this.effects.shadowOffsetX,
      shadowOffsetY: this.effects.shadowOffsetY,
    };
  }

  applySettings(settings) {
    // Apply all settings to effects object
    Object.keys(settings).forEach((key) => {
      if (key in this.effects) {
        this.effects[key] = settings[key];
      }
    });

    // Update UI controls
    this.updateUIFromSettings(settings);
  }

  updateUIFromSettings(settings) {
    // Update all form controls to match the settings
    const controls = {
      fontFamily: "fontFamily",
      fontSize: "fontSize",
      fontWeight: "fontWeight",
      textPosition: "textPosition",
      verticalPosition: "verticalPosition",
      positionX: "positionX",
      positionY: "positionY",
      karaokeMode: "karaokeMode",
      primaryColor: "primaryColor",
      highlightColor: "highlightColor",
      animationSpeed: "animationSpeed",
      glowIntensity: "glowIntensity",
      wordSpacing: "wordSpacing",
      maxLineWidth: "maxLineWidth",
      lineHeight: "lineHeight",
      autoBreak: "autoBreak",
      enableBorder: "enableBorder",
      borderWidth: "borderWidth",
      borderColor: "borderColor",
      enableShadow: "enableShadow",
      shadowBlur: "shadowBlur",
      shadowColor: "shadowColor",
      shadowOffsetX: "shadowOffsetX",
      shadowOffsetY: "shadowOffsetY",
    };

    Object.entries(controls).forEach(([setting, elementId]) => {
      const element = document.getElementById(elementId);
      if (element && settings[setting] !== undefined) {
        if (element.type === "checkbox") {
          element.checked = settings[setting];
        } else {
          element.value = settings[setting];
        }

        // Trigger change event to update displays
        element.dispatchEvent(new Event("change"));
        element.dispatchEvent(new Event("input"));
      }
    });
  }

  saveCurrentPreset() {
    const presetName = document.getElementById("presetName").value.trim();
    if (!presetName) {
      alert("Please enter a preset name");
      return;
    }

    const settings = this.getCurrentSettings();
    settings.name = presetName;
    settings.timestamp = new Date().toISOString();

    this.presets.set(presetName, settings);
    this.savePresetsToStorage();
    this.updatePresetList();

    document.getElementById("presetName").value = "";
    alert(`Preset "${presetName}" saved successfully!`);
  }

  loadSelectedPreset() {
    const presetName = document.getElementById("presetSelect").value;
    if (!presetName) {
      alert("Please select a preset to load");
      return;
    }

    const preset = this.presets.get(presetName);
    if (preset) {
      this.applySettings(preset);
      alert(`Preset "${presetName}" loaded successfully!`);
    }
  }

  loadBuiltinPreset(presetName) {
    const preset = this.builtinPresets[presetName];
    if (preset) {
      this.applySettings(preset);
      alert(`Built-in preset "${preset.name}" loaded successfully!`);
    }
  }

  deleteSelectedPreset() {
    const presetName = document.getElementById("presetSelect").value;
    if (!presetName) {
      alert("Please select a preset to delete");
      return;
    }

    if (confirm(`Are you sure you want to delete preset "${presetName}"?`)) {
      this.presets.delete(presetName);
      this.savePresetsToStorage();
      this.updatePresetList();
      alert(`Preset "${presetName}" deleted successfully!`);
    }
  }

  updatePresetList() {
    const select = document.getElementById("presetSelect");
    select.innerHTML = '<option value="">Select a preset...</option>';

    this.presets.forEach((preset, name) => {
      const option = document.createElement("option");
      option.value = name;
      option.textContent = `${name} (${new Date(
        preset.timestamp
      ).toLocaleDateString()})`;
      select.appendChild(option);
    });
  }

  savePresetsToStorage() {
    const presetsObj = Object.fromEntries(this.presets);
    localStorage.setItem("karaokePresets", JSON.stringify(presetsObj));
  }

  loadPresetsFromStorage() {
    try {
      const stored = localStorage.getItem("karaokePresets");
      if (stored) {
        const presetsObj = JSON.parse(stored);
        this.presets = new Map(Object.entries(presetsObj));
      }
    } catch (error) {
      console.error("Error loading presets from storage:", error);
    }
  }

  exportAllPresets() {
    const presetsObj = Object.fromEntries(this.presets);
    const data = {
      presets: presetsObj,
      exportDate: new Date().toISOString(),
      version: "1.0",
    };

    this.downloadJSON(data, "karaoke-presets.json");
    alert("Presets exported successfully!");
  }

  importPresets(event) {
    const file = event.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const data = JSON.parse(e.target.result);
        if (data.presets) {
          const importedCount = Object.keys(data.presets).length;
          Object.entries(data.presets).forEach(([name, preset]) => {
            this.presets.set(name, preset);
          });

          this.savePresetsToStorage();
          this.updatePresetList();
          alert(`Successfully imported ${importedCount} presets!`);
        } else {
          alert("Invalid preset file format");
        }
      } catch (error) {
        alert("Error importing presets: " + error.message);
      }
    };
    reader.readAsText(file);

    // Reset file input
    event.target.value = "";
  }

  resetAllPresets() {
    if (
      confirm(
        "Are you sure you want to delete all saved presets? This cannot be undone."
      )
    ) {
      this.presets.clear();
      this.savePresetsToStorage();
      this.updatePresetList();
      alert("All presets have been reset!");
    }
  }

  downloadJSON(data, filename) {
    const blob = new Blob([JSON.stringify(data, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  }

  getSupportedVideoFormat(preferredFormat = "auto") {
    // Define format groups
    const mp4Formats = [
      "video/mp4;codecs=h264,aac",
      "video/mp4;codecs=avc1.42E01E,mp4a.40.2",
      "video/mp4",
    ];

    const webmFormats = [
      "video/webm;codecs=vp9,opus",
      "video/webm;codecs=vp8,vorbis",
      "video/webm;codecs=vp9",
      "video/webm;codecs=vp8",
      "video/webm",
    ];

    let formats;

    // Choose format order based on preference
    if (preferredFormat === "mp4") {
      formats = [...mp4Formats, ...webmFormats];
    } else if (preferredFormat === "webm") {
      formats = [...webmFormats, ...mp4Formats];
    } else {
      // Auto: prefer MP4 for better compatibility
      formats = [...mp4Formats, ...webmFormats];
    }

    for (const format of formats) {
      if (MediaRecorder.isTypeSupported(format)) {
        console.log(`Using video format: ${format}`);
        return format;
      }
    }

    console.warn("No supported video format found, using fallback");
    return "video/webm"; // fallback
  }

  getFileExtension(mimeType) {
    if (mimeType.includes("mp4")) return "mp4";
    if (mimeType.includes("webm")) return "webm";
    return "webm"; // fallback
  }

  // Fast rendering helper methods
  async waitForPreciseSeek(targetTime) {
    return new Promise((resolve) => {
      const checkSeek = () => {
        const currentTime = this.video.currentTime;
        const timeDiff = Math.abs(currentTime - targetTime);

        // Accept if within 1/60th of a second (frame precision)
        if (timeDiff < 0.016 || this.video.readyState >= 2) {
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

  async extractAudioTrack() {
    // For now, we'll skip audio extraction in fast mode
    // This could be implemented using Web Audio API or FFmpeg.js
    console.log("Audio extraction not implemented in fast mode");
    return null;
  }

  async encodeFramesToVideo(
    frames,
    frameRate,
    quality,
    format,
    audioBlob,
    progressCallback
  ) {
    // Use MediaRecorder with a synthetic video stream from frames
    return new Promise(async (resolve, reject) => {
      try {
        // Create a temporary canvas for frame playback
        const tempCanvas = document.createElement("canvas");
        tempCanvas.width = this.canvas.width;
        tempCanvas.height = this.canvas.height;
        const tempCtx = tempCanvas.getContext("2d");

        // Create stream from canvas
        const stream = tempCanvas.captureStream(frameRate);
        const chunks = [];

        // Set quality settings
        const qualitySettings = {
          high: { videoBitsPerSecond: 8000000 },
          medium: { videoBitsPerSecond: 4000000 },
          low: { videoBitsPerSecond: 2000000 },
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

        mediaRecorder.onstop = () => {
          const blob = new Blob(chunks, { type: mimeType });
          resolve(blob);
        };

        mediaRecorder.onerror = (error) => {
          reject(error);
        };

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
      } catch (error) {
        reject(error);
      }
    });
  }

  /**
   * Initialize advanced rendering systems
   */
  async initializeAdvancedRendering() {
    try {
      // Initialize server renderer
      this.serverRenderer = new ServerRenderer(this);

      // Check if server is available
      this.isServerAvailable = await this.serverRenderer.checkServerHealth();

      if (this.isServerAvailable) {
        await this.serverRenderer.initializeWebSocket();
        console.log("Server-based rendering available");
      } else {
        console.log("Server not available, using client-side rendering");
      }

      // Initialize batch processor (includes parallel and GPU rendering)
      this.batchProcessor = new BatchProcessor(this);
      console.log("Advanced rendering systems initialized");
    } catch (error) {
      console.warn("Advanced rendering not available:", error.message);
    }
  }

  /**
   * Ultra-fast rendering using batch processing with GPU acceleration
   */
  async renderVideoUltraFast(
    resolution,
    frameRate,
    quality,
    format,
    progressCallback
  ) {
    // Use fixed memory-optimized renderer
    if (!this.fixedMemoryRenderer) {
      this.fixedMemoryRenderer = new FixedMemoryRenderer(this);
    }

    progressCallback(
      0,
      "Initializing memory-optimized ultra-fast rendering..."
    );

    try {
      return await this.fixedMemoryRenderer.renderVideoMemoryOptimized(
        resolution,
        frameRate,
        quality,
        format,
        progressCallback
      );
    } catch (error) {
      console.error("Ultra-fast rendering failed:", error);
      // Fallback to regular fast rendering
      return await this.renderVideo(
        resolution,
        frameRate,
        quality,
        format,
        progressCallback
      );
    }
  }

  /**
   * Parallel rendering using Web Workers
   */
  async renderVideoParallel(
    resolution,
    frameRate,
    quality,
    format,
    progressCallback
  ) {
    // Use true parallel renderer for genuine simultaneous processing
    if (!this.trueParallelRenderer) {
      this.trueParallelRenderer = new TrueParallelRenderer(this);
    }

    progressCallback(0, "Initializing true parallel rendering...");

    try {
      return await this.trueParallelRenderer.renderVideoTrueParallel(
        resolution,
        frameRate,
        quality,
        format,
        progressCallback
      );
    } catch (error) {
      console.error("Parallel rendering failed:", error);
      // Fallback to regular fast rendering
      return await this.renderVideo(
        resolution,
        frameRate,
        quality,
        format,
        progressCallback
      );
    }
  }

  /**
   * GPU-accelerated rendering using WebGL
   */
  async renderVideoGPU(
    resolution,
    frameRate,
    quality,
    format,
    progressCallback
  ) {
    if (!this.gpuRenderer) {
      this.gpuRenderer = new GPURenderer(this);
      await this.gpuRenderer.initialize();
    }

    const resolutions = {
      "720p": { width: 1280, height: 720 },
      "1080p": { width: 1920, height: 1080 },
      "4k": { width: 3840, height: 2160 },
    };

    const { width, height } = resolutions[resolution];
    const duration = this.video.duration;
    const totalFrames = Math.ceil(duration * frameRate);
    const frameInterval = 1 / frameRate;

    progressCallback(0, "Initializing GPU rendering...");

    const frames = [];

    // Render frames using GPU
    for (let i = 0; i < totalFrames; i++) {
      const timestamp = i * frameInterval;

      const frameData = await this.gpuRenderer.renderFrameGPU(
        timestamp,
        this.effects,
        this.subtitles,
        this.wordSegments,
        width,
        height
      );

      frames.push(frameData);

      const progress = (i / totalFrames) * 80;
      progressCallback(progress, `GPU rendering frame ${i + 1}/${totalFrames}`);
    }

    progressCallback(85, "Assembling GPU-rendered video...");

    // Assemble video from GPU-rendered frames
    const videoBlob = await this.assembleFramesToVideo(
      frames,
      frameRate,
      quality,
      format,
      (progress) => {
        progressCallback(85 + progress * 0.15, "Encoding GPU video...");
      }
    );

    this.downloadVideo(videoBlob);
    progressCallback(100, "GPU rendering complete!");

    return videoBlob;
  }

  /**
   * Assemble frames into video (helper method)
   */
  async assembleFramesToVideo(
    frames,
    frameRate,
    quality,
    format,
    progressCallback
  ) {
    if (frames.length === 0) {
      throw new Error("No frames to assemble");
    }

    // Create canvas for video assembly
    const canvas = document.createElement("canvas");
    const firstFrame = frames[0];

    canvas.width = firstFrame.width;
    canvas.height = firstFrame.height;
    const ctx = canvas.getContext("2d");

    // Setup MediaRecorder
    const stream = canvas.captureStream(frameRate);
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
    const frameInterval = 1000 / frameRate;
    let frameIndex = 0;

    return new Promise((resolve, reject) => {
      mediaRecorder.onstop = () => {
        const blob = new Blob(chunks, { type: mimeType });
        resolve(blob);
      };

      const playNextFrame = () => {
        if (frameIndex >= frames.length) {
          mediaRecorder.stop();
          return;
        }

        const frameData = frames[frameIndex];
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
        progressCallback(frameIndex / frames.length);

        setTimeout(playNextFrame, frameInterval);
      };

      playNextFrame();
    });
  }

  /**
   * Server-based rendering for memory-free processing
   */
  async renderVideoOnServer(
    resolution,
    frameRate,
    quality,
    format,
    progressCallback
  ) {
    console.log("renderVideoOnServer called with:", {
      inputMode: this.inputMode,
      uploadedVideoId: this.uploadedVideoId,
      hasImageFile: !!this.currentImageFile,
      hasAudioFile: !!this.currentAudioFile,
      hasVideoFile: !!this.currentVideoFile,
    });

    if (!this.isServerAvailable || !this.serverRenderer) {
      throw new Error(
        "Server rendering not available. Please start the render server."
      );
    }

    if (!this.uploadedVideoId) {
      // Try to re-upload based on current input mode
      if (this.inputMode === "video") {
        // Video mode: re-upload video file
        if (this.video && this.video.src && this.currentVideoFile) {
          try {
            progressCallback(0, "Re-uploading video to server...");
            const uploadResult = await this.serverRenderer.uploadVideo(
              this.currentVideoFile
            );
            this.uploadedVideoId = uploadResult.videoId;
            console.log("Video re-uploaded to server:", uploadResult);
          } catch (error) {
            this.showStatus(
              "Failed to upload video to server. Please try again.",
              "error",
              0,
              true
            );
            throw new Error(
              "Video upload failed. Please try again or reload the video file."
            );
          }
        } else {
          this.showStatus(
            "Video not uploaded to server. Please reload the video file.",
            "error",
            0,
            true
          );
          throw new Error(
            "Video not uploaded to server. Please reload the video file."
          );
        }
      } else if (this.inputMode === "imageAudio") {
        // Image+Audio mode: re-upload image and audio files
        if (this.currentImageFile && this.currentAudioFile) {
          try {
            progressCallback(0, "Re-uploading image and audio to server...");
            const uploadResult = await this.serverRenderer.uploadImageAudio(
              this.currentImageFile,
              this.currentAudioFile
            );
            this.uploadedVideoId = uploadResult.videoId;
            console.log("Image and audio re-uploaded to server:", uploadResult);
          } catch (error) {
            this.showStatus(
              "Failed to upload image and audio to server. Please try again.",
              "error",
              0,
              true
            );
            throw new Error(
              "Image and audio upload failed. Please try again or reload the files."
            );
          }
        } else {
          this.showStatus(
            "Image and audio not uploaded to server. Please reload both files.",
            "error",
            0,
            true
          );
          throw new Error(
            "Image and audio not uploaded to server. Please reload both files."
          );
        }
      } else {
        throw new Error(
          "No media uploaded to server. Please load media files first."
        );
      }
    }

    progressCallback(0, "Starting server-based rendering...");

    try {
      await this.serverRenderer.renderVideoOnServer(
        this.uploadedVideoId,
        resolution,
        frameRate,
        quality,
        format,
        progressCallback
      );
    } catch (error) {
      console.error("Server rendering failed:", error);
      throw error;
    }
  }
}

// Initialize the app when DOM is loaded
document.addEventListener("DOMContentLoaded", () => {
  window.karaokeApp = new KaraokeApp();
  console.log("🎤 Karaoke Word Effects App initialized!");
});
