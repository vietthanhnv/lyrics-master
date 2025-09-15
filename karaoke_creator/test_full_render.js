/**
 * Full Server Render Test
 * Tests complete video upload and rendering pipeline
 */

const { exec, spawn } = require("child_process");
const fs = require("fs");
const path = require("path");
const WebSocket = require("ws");

class FullRenderTester {
  constructor() {
    this.serverUrl = "http://localhost:3001";
    this.wsUrl = "ws://localhost:3005";
  }

  async runTest() {
    console.log("🎬 Starting Full Render Test...\n");

    try {
      // Find a small test video
      const testVideo = await this.findSmallTestVideo();

      // Load test subtitles
      const subtitles = await this.loadTestSubtitles();

      // Upload video using curl
      const videoId = await this.uploadVideo(testVideo);

      // Start render job
      const jobId = await this.startRenderJob(videoId, subtitles);

      // Monitor progress
      await this.monitorRenderProgress(jobId);

      console.log("🎉 Full render test completed successfully!");
    } catch (error) {
      console.error("❌ Full render test failed:", error.message);
    }
  }

  /**
   * Find a small test video for quick testing
   */
  async findSmallTestVideo() {
    console.log("📹 Finding test video...");

    // Look for small video files (< 100MB)
    const videoFiles = [];

    // Check current directory
    const files = fs.readdirSync(".");
    files.forEach((file) => {
      if (file.endsWith(".mp4")) {
        const stats = fs.statSync(file);
        const sizeMB = stats.size / 1024 / 1024;
        if (sizeMB < 100) {
          videoFiles.push({ path: file, size: sizeMB });
        }
      }
    });

    // Check uploads directory
    const uploadsDir = path.join("server", "uploads");
    if (fs.existsSync(uploadsDir)) {
      const uploadFiles = fs.readdirSync(uploadsDir);
      uploadFiles.forEach((file) => {
        if (file.endsWith(".mp4")) {
          const fullPath = path.join(uploadsDir, file);
          const stats = fs.statSync(fullPath);
          const sizeMB = stats.size / 1024 / 1024;
          if (sizeMB < 100) {
            videoFiles.push({ path: fullPath, size: sizeMB });
          }
        }
      });
    }

    if (videoFiles.length === 0) {
      throw new Error("No small test video files found (< 100MB)");
    }

    // Use the smallest video
    videoFiles.sort((a, b) => a.size - b.size);
    const selectedVideo = videoFiles[0];

    console.log(
      `   ✅ Selected: ${selectedVideo.path} (${Math.round(
        selectedVideo.size
      )}MB)\n`
    );
    return selectedVideo.path;
  }

  /**
   * Load test subtitles
   */
  async loadTestSubtitles() {
    console.log("📝 Loading test subtitles...");

    const subtitleFile = "test_subtitles.json";
    if (!fs.existsSync(subtitleFile)) {
      throw new Error("test_subtitles.json not found");
    }

    const data = JSON.parse(fs.readFileSync(subtitleFile, "utf8"));
    console.log(
      `   ✅ Loaded ${data.segments?.length || 0} segments, ${
        data.word_segments?.length || 0
      } words\n`
    );

    return data;
  }

  /**
   * Upload video using curl
   */
  async uploadVideo(videoPath) {
    console.log("📤 Uploading video to server...");

    return new Promise((resolve, reject) => {
      const curlCommand = `curl -s -X POST -F "video=@${videoPath}" ${this.serverUrl}/upload/video`;

      exec(curlCommand, (error, stdout, stderr) => {
        if (error) {
          reject(new Error(`Upload failed: ${error.message}`));
          return;
        }

        try {
          const response = JSON.parse(stdout);
          if (response.success) {
            console.log(`   ✅ Upload successful`);
            console.log(`   🆔 Video ID: ${response.videoId}`);
            console.log(
              `   📊 Duration: ${response.videoInfo.duration}s, ${response.videoInfo.width}x${response.videoInfo.height}\n`
            );
            resolve(response.videoId);
          } else {
            reject(new Error(`Upload failed: ${response.error}`));
          }
        } catch (parseError) {
          reject(new Error(`Invalid upload response: ${stdout}`));
        }
      });
    });
  }

  /**
   * Start render job using curl
   */
  async startRenderJob(videoId, subtitles) {
    console.log("🎬 Starting render job...");

    const renderData = {
      videoId,
      subtitles: subtitles.segments || [],
      wordSegments: subtitles.word_segments || [],
      effects: {
        fontFamily: "Arial",
        fontSize: 48,
        fontWeight: "bold",
        primaryColor: "#ffffff",
        highlightColor: "#ffff00",
        karaokeMode: "highlight",
        positionX: 640,
        positionY: 600,
        wordSpacing: 10,
      },
      renderSettings: {
        resolution: "720p",
        frameRate: 30,
        quality: "medium",
        format: "mp4",
      },
    };

    return new Promise((resolve, reject) => {
      const tempFile = "temp_render_data.json";
      fs.writeFileSync(tempFile, JSON.stringify(renderData));

      const curlCommand = `curl -s -X POST -H "Content-Type: application/json" -d @${tempFile} ${this.serverUrl}/render/start`;

      exec(curlCommand, (error, stdout, stderr) => {
        // Clean up temp file
        if (fs.existsSync(tempFile)) {
          fs.unlinkSync(tempFile);
        }

        if (error) {
          reject(new Error(`Render start failed: ${error.message}`));
          return;
        }

        try {
          const response = JSON.parse(stdout);
          if (response.success) {
            console.log(`   ✅ Render job started`);
            console.log(`   🆔 Job ID: ${response.jobId}\n`);
            resolve(response.jobId);
          } else {
            reject(new Error(`Render start failed: ${response.error}`));
          }
        } catch (parseError) {
          reject(new Error(`Invalid render response: ${stdout}`));
        }
      });
    });
  }

  /**
   * Monitor render progress via WebSocket
   */
  async monitorRenderProgress(jobId) {
    console.log("📊 Monitoring render progress...");

    return new Promise((resolve, reject) => {
      const ws = new WebSocket(this.wsUrl);
      let lastProgress = 0;
      const startTime = Date.now();
      const maxWaitTime = 300000; // 5 minutes max

      const timeout = setTimeout(() => {
        ws.close();
        reject(new Error("Render timeout - job took too long (5 minutes)"));
      }, maxWaitTime);

      ws.on("open", () => {
        console.log("   🔌 Connected to WebSocket");

        // Subscribe to job updates
        ws.send(
          JSON.stringify({
            type: "subscribe",
            jobId: jobId,
          })
        );
      });

      ws.on("message", (data) => {
        try {
          const message = JSON.parse(data);

          if (message.type === "jobUpdate" && message.jobId === jobId) {
            const progress = Math.round(message.percent || 0);

            // Only log significant progress changes
            if (progress > lastProgress + 5 || progress === 100) {
              const elapsed = Math.round((Date.now() - startTime) / 1000);
              console.log(
                `   📈 ${progress}% - ${
                  message.message || "Processing..."
                } (${elapsed}s)`
              );
              lastProgress = progress;
            }

            if (message.status === "completed") {
              clearTimeout(timeout);
              const totalTime = Math.round((Date.now() - startTime) / 1000);
              console.log(`   ✅ Render completed in ${totalTime} seconds!`);
              console.log(`   📥 Download URL: ${message.downloadUrl}\n`);
              ws.close();
              resolve();
            } else if (message.status === "failed") {
              clearTimeout(timeout);
              ws.close();
              reject(new Error(`Render failed: ${message.message}`));
            }
          }
        } catch (error) {
          console.error("   ⚠️ WebSocket message error:", error.message);
        }
      });

      ws.on("error", (error) => {
        clearTimeout(timeout);
        reject(new Error(`WebSocket error: ${error.message}`));
      });

      ws.on("close", () => {
        console.log("   🔌 WebSocket disconnected");
      });
    });
  }
}

// Run the test
const tester = new FullRenderTester();
tester.runTest().catch(console.error);
