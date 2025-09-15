/**
 * Karaoke Video Renderer Server
 * Handles video processing with file-based streaming to prevent memory issues
 */

const express = require("express");
const cors = require("cors");
const WebSocket = require("ws");
const multer = require("multer");
const path = require("path");
const fs = require("fs-extra");
const { v4: uuidv4 } = require("uuid");

const VideoProcessor = require("./src/core/VideoProcessor");
const RenderJobManager = require("./src/core/RenderJobManager");
const FileManager = require("./src/core/FileManager");

class KaraokeRenderServer {
  constructor() {
    this.app = express();
    this.port = process.env.PORT || 3001;
    this.videoProcessor = new VideoProcessor();
    this.jobManager = new RenderJobManager();
    this.fileManager = new FileManager();

    this.setupMiddleware();
    this.setupRoutes();
    this.setupWebSocket();
  }

  setupMiddleware() {
    // CORS configuration - Allow all origins for development
    this.app.use(
      cors({
        origin: true, // Allow all origins
        credentials: true,
      })
    );

    this.app.use(express.json({ limit: "20gb" }));
    this.app.use(express.urlencoded({ extended: true, limit: "20gb" }));

    // File upload configuration
    const storage = multer.diskStorage({
      destination: (req, file, cb) => {
        const uploadDir = path.join(__dirname, "uploads");
        fs.ensureDirSync(uploadDir);
        cb(null, uploadDir);
      },
      filename: (req, file, cb) => {
        const uniqueName = `${uuidv4()}-${file.originalname}`;
        cb(null, uniqueName);
      },
    });

    this.upload = multer({
      storage,
      limits: {
        fileSize: 20 * 1024 * 1024 * 1024, // 20GB limit
        fieldSize: 20 * 1024 * 1024 * 1024, // 20GB field limit
      },
    });

    // Serve static files
    this.app.use(
      "/downloads",
      express.static(path.join(__dirname, "downloads"))
    );

    // Serve client application files from parent directory
    this.app.use(express.static(path.join(__dirname, "..")));
  }

  setupRoutes() {
    // Health check
    this.app.get("/health", (req, res) => {
      res.json({
        status: "healthy",
        timestamp: new Date().toISOString(),
        memory: process.memoryUsage(),
        activeJobs: this.jobManager.getActiveJobCount(),
      });
    });

    // Upload video file
    this.app.post(
      "/upload/video",
      (req, res, next) => {
        this.upload.single("video")(req, res, (err) => {
          if (err) {
            console.error("Multer upload error:", err);
            if (err.code === "LIMIT_FILE_SIZE") {
              return res.status(413).json({
                error: "File too large. Maximum size is 2GB.",
                code: "FILE_TOO_LARGE",
              });
            }
            return res.status(400).json({
              error: `Upload failed: ${err.message}`,
              code: err.code || "UPLOAD_ERROR",
            });
          }
          next();
        });
      },
      async (req, res) => {
        try {
          if (!req.file) {
            return res.status(400).json({ error: "No video file uploaded" });
          }

          const videoInfo = await this.videoProcessor.analyzeVideo(
            req.file.path
          );

          res.json({
            success: true,
            videoId: req.file.filename,
            videoInfo,
            message: "Video uploaded successfully",
          });
        } catch (error) {
          console.error("Video upload error:", error);
          res.status(500).json({ error: error.message });
        }
      }
    );

    // Upload image and audio files for karaoke video creation
    this.app.post(
      "/upload/image-audio",
      (req, res, next) => {
        this.upload.fields([
          { name: "image", maxCount: 1 },
          { name: "audio", maxCount: 1 },
        ])(req, res, (err) => {
          if (err) {
            console.error("Multer upload error:", err);
            if (err.code === "LIMIT_FILE_SIZE") {
              return res.status(413).json({
                error: "Files too large. Maximum size is 2GB total.",
                code: "FILE_TOO_LARGE",
              });
            }
            return res.status(400).json({
              error: `Upload failed: ${err.message}`,
              code: err.code || "UPLOAD_ERROR",
            });
          }
          next();
        });
      },
      async (req, res) => {
        try {
          console.log("Processing image+audio upload request...");

          if (!req.files || !req.files.image || !req.files.audio) {
            console.error("Missing files in request:", {
              hasFiles: !!req.files,
              hasImage: !!(req.files && req.files.image),
              hasAudio: !!(req.files && req.files.audio),
            });
            return res.status(400).json({
              error: "Both image and audio files are required",
            });
          }

          const imageFile = req.files.image[0];
          const audioFile = req.files.audio[0];

          console.log("Files received:", {
            image: {
              name: imageFile.originalname,
              size: imageFile.size,
              path: imageFile.path,
            },
            audio: {
              name: audioFile.originalname,
              size: audioFile.size,
              path: audioFile.path,
            },
          });

          // Just analyze audio to get duration, don't create video yet
          console.log("Analyzing audio file...");
          const audioInfo = await this.videoProcessor.analyzeAudio(
            audioFile.path
          );

          // Create a unique identifier for this image+audio combination
          const videoId = `${uuidv4()}-image-audio-combo`;

          // Store the file paths and info for later processing during render
          const imageAudioInfo = {
            type: "image-audio",
            imagePath: imageFile.path,
            audioPath: audioFile.path,
            imageInfo: {
              originalname: imageFile.originalname,
              size: imageFile.size,
            },
            audioInfo: {
              originalname: audioFile.originalname,
              size: audioFile.size,
              duration: audioInfo.duration,
            },
          };

          // Store this info in a simple JSON file for later retrieval
          const infoPath = path.join(__dirname, "uploads", `${videoId}.json`);
          await fs.writeFile(infoPath, JSON.stringify(imageAudioInfo, null, 2));

          console.log("Image+audio info stored successfully:", videoId);

          res.json({
            success: true,
            videoId: videoId,
            videoInfo: {
              duration: audioInfo.duration,
              width: 1920,
              height: 1080,
              frameRate: 30,
              hasAudio: true,
              format: "image-audio-combo",
              size: imageFile.size + audioFile.size,
            },
            message: "Image and audio uploaded successfully",
          });
        } catch (error) {
          console.error("Image+Audio upload error:", error);
          console.error("Error stack:", error.stack);

          // Ensure we always send a response
          if (!res.headersSent) {
            res.status(500).json({
              error: error.message || "Unknown error occurred",
              details: "Check server logs for more information",
            });
          }
        }
      }
    );

    // Upload font file
    this.app.post(
      "/upload/font",
      (req, res, next) => {
        this.upload.single("font")(req, res, (err) => {
          if (err) {
            console.error("Font upload error:", err);
            return res.status(400).json({
              error: `Font upload failed: ${err.message}`,
              code: err.code || "FONT_UPLOAD_ERROR",
            });
          }
          next();
        });
      },
      async (req, res) => {
        try {
          if (!req.file) {
            return res.status(400).json({ error: "No font file uploaded" });
          }

          // Register font with the server's canvas
          const fontName = `CustomFont_${Date.now()}`;
          const fontPath = req.file.path;

          try {
            // Register font for server-side rendering
            await this.videoProcessor.registerFont(fontName, fontPath);

            res.json({
              success: true,
              fontName: fontName,
              originalName: req.file.originalname,
              message: "Font uploaded and registered successfully",
            });
          } catch (fontError) {
            console.error("Font registration error:", fontError);
            res.status(500).json({
              error: "Failed to register font for server rendering",
              details: fontError.message,
            });
          }
        } catch (error) {
          console.error("Font upload error:", error);
          res.status(500).json({ error: error.message });
        }
      }
    );

    // Start render job
    this.app.post("/render/start", async (req, res) => {
      try {
        const { videoId, subtitles, wordSegments, effects, renderSettings } =
          req.body;

        if (!videoId || !subtitles || !wordSegments) {
          return res.status(400).json({ error: "Missing required parameters" });
        }

        const jobId = await this.jobManager.createJob({
          videoId,
          subtitles,
          wordSegments,
          effects,
          renderSettings,
        });

        // Start processing asynchronously
        this.processRenderJob(jobId);

        res.json({
          success: true,
          jobId,
          message: "Render job started",
        });
      } catch (error) {
        console.error("Render start error:", error);
        res.status(500).json({ error: error.message });
      }
    });

    // Get job status
    this.app.get("/render/status/:jobId", (req, res) => {
      try {
        const { jobId } = req.params;
        const status = this.jobManager.getJobStatus(jobId);

        if (!status) {
          return res.status(404).json({ error: "Job not found" });
        }

        res.json(status);
      } catch (error) {
        console.error("Status check error:", error);
        res.status(500).json({ error: error.message });
      }
    });

    // Download rendered video
    this.app.get("/download/:jobId", (req, res) => {
      try {
        const { jobId } = req.params;
        const job = this.jobManager.getJob(jobId);

        if (!job || job.status !== "completed") {
          return res
            .status(404)
            .json({ error: "Video not ready for download" });
        }

        const filePath = job.outputPath;
        if (!fs.existsSync(filePath)) {
          return res.status(404).json({ error: "Output file not found" });
        }

        res.download(filePath, `karaoke-video-${jobId}.mp4`, (err) => {
          if (err) {
            console.error("Download error:", err);
          }
        });
      } catch (error) {
        console.error("Download error:", error);
        res.status(500).json({ error: error.message });
      }
    });

    // Cancel render job
    this.app.post("/render/cancel/:jobId", (req, res) => {
      try {
        const { jobId } = req.params;
        const success = this.jobManager.cancelJob(jobId);

        res.json({
          success,
          message: success
            ? "Job cancelled"
            : "Job not found or cannot be cancelled",
        });
      } catch (error) {
        console.error("Cancel job error:", error);
        res.status(500).json({ error: error.message });
      }
    });

    // List active jobs
    this.app.get("/jobs", (req, res) => {
      try {
        const jobs = this.jobManager.getAllJobs();
        res.json({ jobs });
      } catch (error) {
        console.error("List jobs error:", error);
        res.status(500).json({ error: error.message });
      }
    });

    // Cleanup old files
    this.app.post("/cleanup", async (req, res) => {
      try {
        const cleaned = await this.fileManager.cleanupOldFiles();
        res.json({ success: true, cleaned });
      } catch (error) {
        console.error("Cleanup error:", error);
        res.status(500).json({ error: error.message });
      }
    });
  }

  setupWebSocket() {
    this.wss = new WebSocket.Server({ port: 3005 });

    this.wss.on("connection", (ws) => {
      console.log("WebSocket client connected");

      ws.on("message", (message) => {
        try {
          const data = JSON.parse(message);
          this.handleWebSocketMessage(ws, data);
        } catch (error) {
          console.error("WebSocket message error:", error);
        }
      });

      ws.on("close", () => {
        console.log("WebSocket client disconnected");
      });
    });

    console.log("WebSocket server listening on port 3005");
  }

  handleWebSocketMessage(ws, data) {
    switch (data.type) {
      case "subscribe":
        // Subscribe to job updates
        ws.jobId = data.jobId;
        break;
      case "ping":
        ws.send(JSON.stringify({ type: "pong" }));
        break;
    }
  }

  broadcastJobUpdate(jobId, update) {
    this.wss.clients.forEach((client) => {
      if (client.readyState === WebSocket.OPEN && client.jobId === jobId) {
        client.send(
          JSON.stringify({
            type: "jobUpdate",
            jobId,
            ...update,
          })
        );
      }
    });
  }

  async processRenderJob(jobId) {
    try {
      const job = this.jobManager.getJob(jobId);
      if (!job) {
        throw new Error("Job not found");
      }

      console.log("Processing render job:", {
        jobId,
        videoId: job.videoId,
        hasSubtitles: !!job.subtitles,
        hasWordSegments: !!job.wordSegments,
        hasEffects: !!job.effects,
      });

      // Update job status
      this.jobManager.updateJobStatus(
        jobId,
        "processing",
        "Starting render process..."
      );
      this.broadcastJobUpdate(jobId, {
        status: "processing",
        message: "Starting render process...",
      });

      // Process video with file-based streaming
      const outputPath = await this.videoProcessor.processVideo(
        job,
        (progress) => {
          this.jobManager.updateJobProgress(
            jobId,
            progress.percent,
            progress.message
          );
          this.broadcastJobUpdate(jobId, progress);
        }
      );

      // Mark job as completed
      this.jobManager.completeJob(jobId, outputPath);
      this.broadcastJobUpdate(jobId, {
        status: "completed",
        message: "Render completed successfully",
        downloadUrl: `/download/${jobId}`,
      });
    } catch (error) {
      console.error(`Job ${jobId} failed:`, error);
      this.jobManager.failJob(jobId, error.message);
      this.broadcastJobUpdate(jobId, {
        status: "failed",
        message: error.message,
      });
    }
  }

  start() {
    this.app.listen(this.port, () => {
      console.log(`🎤 Karaoke Render Server running on port ${this.port}`);
      console.log(`📊 Health check: http://localhost:${this.port}/health`);
      console.log(`🔌 WebSocket server: ws://localhost:3005`);
    });

    // Graceful shutdown
    process.on("SIGTERM", () => {
      console.log("Shutting down server...");
      this.jobManager.cancelAllJobs();
      process.exit(0);
    });
  }
}

// Start server
const server = new KaraokeRenderServer();
server.start();

module.exports = KaraokeRenderServer;
