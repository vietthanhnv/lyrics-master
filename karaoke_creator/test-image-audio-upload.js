/**
 * Simple test script to verify image+audio upload functionality
 */

const fs = require("fs");
const path = require("path");
const FormData = require("form-data");
const fetch = require("node-fetch");

async function testImageAudioUpload() {
  console.log("Testing Image+Audio Upload...");

  // Check if server is running
  try {
    const healthResponse = await fetch("http://localhost:3001/health");
    if (!healthResponse.ok) {
      throw new Error("Server not responding");
    }
    console.log("✓ Server is running");
  } catch (error) {
    console.error("✗ Server is not running. Please start the server first.");
    return;
  }

  // Create test files (you'll need to provide actual files)
  const testImagePath = "./test_image.jpg"; // You need to provide this
  const testAudioPath = "./test_audio.mp3"; // You need to provide this

  if (!fs.existsSync(testImagePath)) {
    console.error("✗ Test image file not found:", testImagePath);
    console.log("Please create a test image file or update the path");
    return;
  }

  if (!fs.existsSync(testAudioPath)) {
    console.error("✗ Test audio file not found:", testAudioPath);
    console.log("Please create a test audio file or update the path");
    return;
  }

  try {
    // Create form data
    const formData = new FormData();
    formData.append("image", fs.createReadStream(testImagePath));
    formData.append("audio", fs.createReadStream(testAudioPath));

    console.log("Uploading image and audio files...");

    // Upload files
    const uploadResponse = await fetch(
      "http://localhost:3001/upload/image-audio",
      {
        method: "POST",
        body: formData,
      }
    );

    const uploadResult = await uploadResponse.json();

    if (uploadResult.success) {
      console.log("✓ Upload successful!");
      console.log("Video ID:", uploadResult.videoId);
      console.log("Video Info:", uploadResult.videoInfo);

      // Test render job creation
      const renderData = {
        videoId: uploadResult.videoId,
        subtitles: [
          {
            start_time: 0,
            end_time: 5,
            text: "Test subtitle",
          },
        ],
        wordSegments: [
          {
            word: "Test",
            start_time: 0,
            end_time: 2.5,
          },
          {
            word: "subtitle",
            start_time: 2.5,
            end_time: 5,
          },
        ],
        effects: {
          fontFamily: "Arial",
          fontSize: 60,
          primaryColor: "#ffffff",
          highlightColor: "#ffff00",
        },
        renderSettings: {
          resolution: "1080p",
          frameRate: 30,
          quality: "medium",
          format: "mp4",
        },
      };

      console.log("Testing render job creation...");

      const renderResponse = await fetch("http://localhost:3001/render/start", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(renderData),
      });

      const renderResult = await renderResponse.json();

      if (renderResult.success) {
        console.log("✓ Render job created successfully!");
        console.log("Job ID:", renderResult.jobId);
      } else {
        console.error("✗ Render job creation failed:", renderResult.error);
      }
    } else {
      console.error("✗ Upload failed:", uploadResult.error);
    }
  } catch (error) {
    console.error("✗ Test failed:", error.message);
  }
}

// Run the test
testImageAudioUpload().catch(console.error);
