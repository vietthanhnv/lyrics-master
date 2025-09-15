/**
 * Server Renderer - Client-side interface for server-based rendering
 */

class ServerRenderer {
  constructor(karaokeApp) {
    this.app = karaokeApp;
    this.serverUrl = "http://localhost:3001";
    this.wsUrl = "ws://localhost:3005";
    this.ws = null;
    this.currentJobId = null;
    this.isConnected = false;
  }

  /**
   * Initialize WebSocket connection for real-time updates
   */
  async initializeWebSocket() {
    return new Promise((resolve, reject) => {
      try {
        this.ws = new WebSocket(this.wsUrl);

        this.ws.onopen = () => {
          console.log("Connected to render server");
          this.isConnected = true;
          resolve();
        };

        this.ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            this.handleServerMessage(data);
          } catch (error) {
            console.error("WebSocket message error:", error);
          }
        };

        this.ws.onclose = () => {
          console.log("Disconnected from render server");
          this.isConnected = false;
          // Attempt to reconnect after 3 seconds
          setTimeout(() => this.initializeWebSocket(), 3000);
        };

        this.ws.onerror = (error) => {
          console.error("WebSocket error:", error);
          reject(error);
        };
      } catch (error) {
        reject(error);
      }
    });
  }

  /**
   * Handle messages from server
   */
  handleServerMessage(data) {
    switch (data.type) {
      case "jobUpdate":
        if (data.jobId === this.currentJobId) {
          this.updateProgress(data);
        }
        break;
      case "pong":
        // Keep-alive response
        break;
    }
  }

  /**
   * Update progress from server
   */
  updateProgress(data) {
    if (this.progressCallback) {
      this.progressCallback(data.percent || 0, data.message || "");
    }

    // Handle completion
    if (data.status === "completed") {
      this.handleRenderComplete(data);
    } else if (data.status === "failed") {
      this.handleRenderError(data);
    }
  }

  /**
   * Handle render completion
   */
  handleRenderComplete(data) {
    if (this.progressCallback) {
      this.progressCallback(100, "Render completed! Preparing download...");
    }

    // Trigger download
    if (data.downloadUrl) {
      const downloadUrl = `${this.serverUrl}${data.downloadUrl}`;
      this.downloadFile(downloadUrl, `karaoke-video-${this.currentJobId}.mp4`);
    }

    // Reset UI after a short delay to show completion
    setTimeout(() => {
      this.resetRenderUI();
    }, 3000);

    this.currentJobId = null;
  }

  /**
   * Handle render error
   */
  handleRenderError(data) {
    console.error("Server render failed:", data.message);
    alert(`Render failed: ${data.message}`);
    this.resetRenderUI();
    this.currentJobId = null;
  }

  /**
   * Reset the render UI elements
   */
  resetRenderUI() {
    const renderBtn = document.getElementById("renderBtn");
    const progressDiv = document.getElementById("renderProgress");

    if (renderBtn) {
      renderBtn.disabled = false;
      renderBtn.textContent = "🎬 Start Render";
    }

    if (progressDiv) {
      progressDiv.style.display = "none";
    }
  }

  /**
   * Check server health
   */
  async checkServerHealth() {
    try {
      const response = await fetch(`${this.serverUrl}/health`);
      const data = await response.json();
      return data.status === "healthy";
    } catch (error) {
      console.error("Server health check failed:", error);
      return false;
    }
  }

  /**
   * Upload video to server
   */
  async uploadVideo(videoFile) {
    const formData = new FormData();
    formData.append("video", videoFile);

    try {
      const response = await fetch(`${this.serverUrl}/upload/video`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));

        if (response.status === 413 || errorData.code === "FILE_TOO_LARGE") {
          throw new Error(
            "Video file is too large. Maximum size is 2GB. Please use a smaller file or compress your video."
          );
        }

        throw new Error(
          errorData.error || `Upload failed with status ${response.status}`
        );
      }

      const data = await response.json();

      if (!data.success) {
        throw new Error(data.error || "Upload failed");
      }

      return data;
    } catch (error) {
      console.error("Video upload failed:", error);

      // Provide user-friendly error messages
      if (error.message.includes("fetch")) {
        throw new Error(
          "Cannot connect to server. Please make sure the server is running."
        );
      }

      throw error;
    }
  }

  /**
   * Upload image and audio files to server for karaoke video creation
   */
  async uploadImageAudio(imageFile, audioFile) {
    const formData = new FormData();
    formData.append("image", imageFile);
    formData.append("audio", audioFile);

    try {
      const response = await fetch(`${this.serverUrl}/upload/image-audio`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));

        if (response.status === 413 || errorData.code === "FILE_TOO_LARGE") {
          throw new Error(
            "Files are too large. Maximum size is 2GB total. Please use smaller files."
          );
        }

        throw new Error(
          errorData.error || `Upload failed with status ${response.status}`
        );
      }

      const data = await response.json();

      if (!data.success) {
        throw new Error(data.error || "Upload failed");
      }

      return data;
    } catch (error) {
      console.error("Image+Audio upload failed:", error);

      // Provide user-friendly error messages
      if (error.message.includes("fetch")) {
        throw new Error(
          "Cannot connect to server. Please make sure the server is running."
        );
      }

      throw error;
    }
  }

  /**
   * Start server-based rendering
   */
  async renderVideoOnServer(
    videoId,
    resolution,
    frameRate,
    quality,
    format,
    progressCallback
  ) {
    // Create a robust progress callback wrapper
    this.progressCallback = (percent, message) => {
      // Ensure we're in the main thread context
      if (typeof requestAnimationFrame !== "undefined") {
        requestAnimationFrame(() => {
          try {
            progressCallback(percent, message);
          } catch (error) {
            console.error("Progress callback error:", error);
          }
        });
      } else {
        // Fallback to setTimeout
        setTimeout(() => {
          try {
            progressCallback(percent, message);
          } catch (error) {
            console.error("Progress callback error:", error);
          }
        }, 0);
      }
    };

    try {
      // Ensure WebSocket connection
      if (!this.isConnected) {
        await this.initializeWebSocket();
      }

      this.progressCallback(0, "Starting server render...");

      // Prepare render data
      const renderData = {
        videoId,
        subtitles: this.app.subtitles,
        wordSegments: this.app.wordSegments,
        effects: this.app.effects,
        renderSettings: {
          resolution,
          frameRate,
          quality,
          format,
        },
      };

      // Debug: Log effects being sent to server
      console.log("Sending effects to server:", {
        effectsKeys: Object.keys(this.app.effects),
        effects: this.app.effects,
      });

      // Start render job
      const response = await fetch(`${this.serverUrl}/render/start`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(renderData),
      });

      const data = await response.json();

      if (!data.success) {
        throw new Error(data.error || "Failed to start render");
      }

      this.currentJobId = data.jobId;

      // Subscribe to job updates
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        this.ws.send(
          JSON.stringify({
            type: "subscribe",
            jobId: this.currentJobId,
          })
        );
      }

      progressCallback(5, "Render job started on server...");

      // Poll for status updates as backup
      this.pollJobStatus();
    } catch (error) {
      console.error("Server render failed:", error);
      throw error;
    }
  }

  /**
   * Poll job status (backup to WebSocket)
   */
  async pollJobStatus() {
    if (!this.currentJobId) return;

    try {
      const response = await fetch(
        `${this.serverUrl}/render/status/${this.currentJobId}`
      );
      const data = await response.json();

      if (data.status === "completed" || data.status === "failed") {
        this.updateProgress(data);
        return;
      }

      // Continue polling
      setTimeout(() => this.pollJobStatus(), 2000);
    } catch (error) {
      console.error("Status polling error:", error);
      // Retry polling
      setTimeout(() => this.pollJobStatus(), 5000);
    }
  }

  /**
   * Cancel current render job
   */
  async cancelRender() {
    if (!this.currentJobId) return false;

    try {
      const response = await fetch(
        `${this.serverUrl}/render/cancel/${this.currentJobId}`,
        {
          method: "POST",
        }
      );

      const data = await response.json();

      if (data.success) {
        this.currentJobId = null;
        if (this.progressCallback) {
          this.progressCallback(0, "Render cancelled");
        }
      }

      return data.success;
    } catch (error) {
      console.error("Cancel render failed:", error);
      return false;
    }
  }

  /**
   * Download file from server
   */
  downloadFile(url, filename) {
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }

  /**
   * Get server statistics
   */
  async getServerStats() {
    try {
      const response = await fetch(`${this.serverUrl}/jobs`);
      const data = await response.json();
      return data;
    } catch (error) {
      console.error("Failed to get server stats:", error);
      return null;
    }
  }

  /**
   * Cleanup resources
   */
  cleanup() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.currentJobId = null;
    this.isConnected = false;
  }
}

// Export for use in main application
if (typeof module !== "undefined" && module.exports) {
  module.exports = ServerRenderer;
} else if (typeof window !== "undefined") {
  window.ServerRenderer = ServerRenderer;
}
