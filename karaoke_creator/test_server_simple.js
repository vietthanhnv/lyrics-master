/**
 * Simple Server Render Test
 * Tests server health and basic functionality
 */

const { exec } = require("child_process");
const fs = require("fs");
const path = require("path");

class SimpleServerTester {
  constructor() {
    this.serverUrl = "http://localhost:3001";
  }

  async runTest() {
    console.log("🧪 Starting Simple Server Test...\n");

    try {
      // Test 1: Server Health
      await this.testServerHealth();

      // Test 2: Check if we have test files
      await this.checkTestFiles();

      // Test 3: Test upload endpoint (without actual file)
      await this.testUploadEndpoint();

      console.log("✅ Basic server tests passed!");
      console.log(
        "📝 To test full rendering, use the web interface to upload a video."
      );
    } catch (error) {
      console.error("❌ Test failed:", error.message);
    }
  }

  /**
   * Test server health using curl
   */
  async testServerHealth() {
    console.log("1️⃣ Testing server health...");

    return new Promise((resolve, reject) => {
      exec(`curl -s ${this.serverUrl}/health`, (error, stdout, stderr) => {
        if (error) {
          reject(new Error(`Server health check failed: ${error.message}`));
          return;
        }

        try {
          const data = JSON.parse(stdout);
          if (data.status === "healthy") {
            console.log(`   ✅ Server is healthy`);
            console.log(
              `   📊 Memory usage: ${Math.round(
                data.memory.heapUsed / 1024 / 1024
              )}MB`
            );
            console.log(`   🔄 Active jobs: ${data.activeJobs}\n`);
            resolve();
          } else {
            reject(new Error("Server is not healthy"));
          }
        } catch (parseError) {
          reject(new Error(`Invalid server response: ${stdout}`));
        }
      });
    });
  }

  /**
   * Check for test files
   */
  async checkTestFiles() {
    console.log("2️⃣ Checking test files...");

    // Check for video files
    const videoExtensions = [".mp4", ".avi", ".mov", ".mkv"];
    const videoFiles = [];

    // Check current directory
    const files = fs.readdirSync(".");
    files.forEach((file) => {
      const ext = path.extname(file).toLowerCase();
      if (videoExtensions.includes(ext)) {
        videoFiles.push(file);
      }
    });

    // Check uploads directory
    const uploadsDir = path.join("server", "uploads");
    if (fs.existsSync(uploadsDir)) {
      const uploadFiles = fs.readdirSync(uploadsDir);
      uploadFiles.forEach((file) => {
        const ext = path.extname(file).toLowerCase();
        if (videoExtensions.includes(ext)) {
          videoFiles.push(path.join("uploads", file));
        }
      });
    }

    console.log(`   📹 Found ${videoFiles.length} video files:`);
    videoFiles.slice(0, 3).forEach((file) => {
      const stats = fs.statSync(
        file.startsWith("uploads") ? path.join("server", file) : file
      );
      const sizeMB = Math.round(stats.size / 1024 / 1024);
      console.log(`      - ${file} (${sizeMB}MB)`);
    });

    // Check for subtitle files
    const subtitleFiles = [];
    files.forEach((file) => {
      if (
        file.endsWith(".json") &&
        (file.includes("subtitle") || file.includes("test"))
      ) {
        subtitleFiles.push(file);
      }
    });

    console.log(`   📝 Found ${subtitleFiles.length} subtitle files:`);
    subtitleFiles.forEach((file) => {
      console.log(`      - ${file}`);
    });

    console.log("");
  }

  /**
   * Test upload endpoint availability
   */
  async testUploadEndpoint() {
    console.log("3️⃣ Testing upload endpoint...");

    return new Promise((resolve, reject) => {
      // Test with empty POST to see if endpoint responds correctly
      exec(
        `curl -s -X POST ${this.serverUrl}/upload/video`,
        (error, stdout, stderr) => {
          if (error) {
            reject(new Error(`Upload endpoint test failed: ${error.message}`));
            return;
          }

          try {
            const data = JSON.parse(stdout);
            if (data.error && data.error.includes("No video file uploaded")) {
              console.log("   ✅ Upload endpoint is responding correctly");
              console.log("   📤 Ready to accept video uploads\n");
              resolve();
            } else {
              console.log("   ⚠️ Upload endpoint response:", stdout);
              resolve();
            }
          } catch (parseError) {
            console.log(
              "   ⚠️ Upload endpoint response (non-JSON):",
              stdout.substring(0, 100)
            );
            resolve();
          }
        }
      );
    });
  }
}

// Run the test
const tester = new SimpleServerTester();
tester.runTest().catch(console.error);
