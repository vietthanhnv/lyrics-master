/**
 * Server Render Test Script
 * Tests the complete server-side video rendering pipeline
 */

const fs = require("fs");
const path = require("path");
const FormData = require("form-data");
const WebSocket = require("ws");

// Import fetch for Node.js
const fetch = (...args) =>
  import("node-fetch").then(({ default: fetch }) => fetch(...args));

class ServerRenderTester {
  constructor() {
    this.serverUrl = "http://localhost:3001";
    this.wsUrl = "ws://localhost:3005";
    this.testVideoPath = null;
    this.testSubtitles = null;
    this.testWordSegments = null;
  }

  /**
   * Run complete server render test
   */
  async runTest() {
    console.log("🧪 Starting Server Render Test...\n");

    try {
      // Step 1: Check server health
      await this.testServerHealth();

      // Step 2: Find test video file
      await this.findTestVideo();

      // Step 3: Load test subtitles
      await this.loadTestSubtitles();

      // Step 4: Upload video to server
      const videoId = await this.testVideoUpload();

      // Step 5: Start render job
      const jobId = await this.testRenderStart(videoId);

      // Step 6: Monitor render progress
      await this.testRenderProgress(jobId);

      console.log(
        "✅ All tests passed! Server rendering is working correctly."
      );
    } catch (error) {
      console.error("❌ Test failed:", error.message);
      process.exit(1);
    }
  }

  /**
   * Test server health endpoint
   */
  async testServerHealth() {
    console.log("1️⃣ Testing server health...");

    const response = await fetch(`${this.serverUrl}/health`);
    const data = await response.json();

    if (data.status !== "healthy") {
      throw new Error("Server is not healthy");
    }

    console.log(
      `   ✅ Server is healthy (Memory: ${Math.round(
        data.memory.heapUsed / 1024 / 1024
      )}MB)`
    );
    console.log(`   📊 Active jobs: ${data.activeJobs}\n`);
  }

  /**
   * Find a test video file
   */
  async findTestVideo() {
    console.log("2️⃣ Finding test video file...");

    // Look for video files in common locations
    const possiblePaths = [
      "test_video.mp4",
      "sample_video.mp4",
      "test_sample.mp4",
      path.join("server", "uploads"),
    ];

    // Check uploads directory for existing files
    const uploadsDir = path.join("server", "uploads");
    if (fs.existsSync(uploadsDir)) {
      const files = fs.readdirSync(uploadsDir);
      const videoFiles = files.filter((f) => f.endsWith(".mp4"));
      if (videoFiles.length > 0) {
        this.testVideoPath = path.join(uploadsDir, videoFiles[0]);
        console.log(`   ✅ Found existing video: ${videoFiles[0]}\n`);
        return;
      }
    }

    // Create a minimal test video if none found
    console.log("   📹 No test video found, creating minimal test video...");
    await this.createTestVideo();
  }

  /**
   * Create a minimal test video using FFmpeg
   */
  async createTestVideo() {
    const ffmpeg = require("fluent-ffmpeg");
    const ffmpegStatic = require("ffmpeg-static");

    ffmpeg.setFfmpegPath(ffmpegStatic);

    this.testVideoPath = "test_video.mp4";

    return new Promise((resolve, reject) => {
      ffmpeg()
        .input("color=c=blue:size=1280x720:duration=5")
        .inputFormat("lavfi")
        .videoCodec("libx264")
        .fps(30)
        .output(this.testVideoPath)
        .on("end", () => {
          console.log("   ✅ Created test video (5 seconds, 1280x720)\n");
          resolve();
        })
        .on("error", reject)
        .run();
    });
  }

  /**
   * Load test subtitles
   */
  async loadTestSubtitles() {
    console.log("3️⃣ Loading test subtitles...");

    // Look for existing subtitle files
    const subtitleFiles = ["test_subtitles.json", "sample_subtitles.json"];

    for (const file of subtitleFiles) {
      if (fs.existsSync(file)) {
        const data = JSON.parse(fs.readFileSync(file, "utf8"));
        this.testSubtitles = data.segments || [];
        this.testWordSegments = data.word_segments || [];
        console.log(
          `   ✅ Loaded ${file}: ${this.testSubtitles.length} segments, ${this.testWordSegments.length} words\n`
        );
        return;
      }
    }

    // Create minimal test subtitles
    console.log("   📝 Creating minimal test subtitles...");
    this.testSubtitles = [
      {
        start_time: 1.0,
        end_time: 3.0,
        text: "Hello World Test",
      },
      {
        start_time: 3.5,
        end_time: 5.0,
        text: "Server Render Test",
      },
    ];

    this.testWordSegments = [
      { start_time: 1.0, end_time: 1.5, word: "Hello" },
      { start_time: 1.5, end_time: 2.0, word: "World" },
      { start_time: 2.0, end_time: 3.0, word: "Test" },
      { start_time: 3.5, end_time: 4.0, word: "Server" },
      { start_time: 4.0, end_time: 4.5, word: "Render" },
      { start_time: 4.5, end_time: 5.0, word: "Test" },
    ];

    console.log("   ✅ Created test subtitles: 2 segments, 6 words\n");
  }

  /**
   * Test video upload
   */
  async testVideoUpload() {
    console.log("4️⃣ Testing video upload...");

    if (!fs.existsSync(this.testVideoPath)) {
      throw new Error(`Test video not found: ${this.testVideoPath}`);
    }

    const formData = new FormData();
    formData.append("video", fs.createReadStream(this.testVideoPath));

    const response = await fetch(`${this.serverUrl}/upload/video`, {
      method: "POST",
      body: formData,
    });

    const data = await response.json();

    if (!data.success) {
      throw new Error(`Upload failed: ${data.error}`);
    }

    console.log(`   ✅ Video uploaded successfully`);
    console.log(`   📹 Video ID: ${data.videoId}`);
    console.log(
      `   📊 Video Info: ${data.videoInfo.width}x${data.videoInfo.height}, ${data.videoInfo.duration}s\n`
    );

    return data.videoId;
  }

  /**
   * Test render job start
   */
  async testRenderStart(videoId) {
    console.log("5️⃣ Starting render job...");

    const renderData = {
      videoId,
      subtitles: this.testSubtitles,
      wordSegments: this.testWordSegments,
      effects: {
        fontFamily: "Arial",
        fontSize: 60,
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

    const response = await fetch(`${this.serverUrl}/render/start`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(renderData),
    });

    const data = await response.json();

    if (!data.success) {
      throw new Error(`Render start failed: ${data.error}`);
    }

    console.log(`   ✅ Render job started`);
    console.log(`   🆔 Job ID: ${data.jobId}\n`);

    return data.jobId;
  }

  /**
   * Test render progress monitoring
   */
  async testRenderProgress(jobId) {
    console.log("6️⃣ Monitoring render progress...");

    return new Promise((resolve, reject) => {
      const ws = new WebSocket(this.wsUrl);
      let progressCount = 0;
      const maxWaitTime = 120000; // 2 minutes max

      const timeout = setTimeout(() => {
        ws.close();
        reject(new Error("Render timeout - job took too long"));
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
            progressCount++;
            console.log(
              `   📈 Progress: ${message.percent || 0}% - ${
                message.message || "Processing..."
              }`
            );

            if (message.status === "completed") {
              clearTimeout(timeout);
              console.log("   ✅ Render completed successfully!");
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
          console.error("   ⚠️ WebSocket message error:", error);
        }
      });

      ws.on("error", (error) => {
        clearTimeout(timeout);
        reject(new Error(`WebSocket error: ${error.message}`));
      });

      ws.on("close", () => {
        console.log("   🔌 WebSocket disconnected");
      });

      // Also poll status as backup
      const pollInterval = setInterval(async () => {
        try {
          const response = await fetch(
            `${this.serverUrl}/render/status/${jobId}`
          );
          const status = await response.json();

          if (status.status === "completed" || status.status === "failed") {
            clearInterval(pollInterval);
          }
        } catch (error) {
          // Ignore polling errors, WebSocket is primary
        }
      }, 5000);
    });
  }
}

// Run the test if this file is executed directly
if (require.main === module) {
  const tester = new ServerRenderTester();
  tester.runTest().catch(console.error);
}

module.exports = ServerRenderTester;
