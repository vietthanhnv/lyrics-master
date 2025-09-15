/**
 * File Manager - Handles file operations and cleanup
 */

const fs = require("fs-extra");
const path = require("path");

class FileManager {
  constructor() {
    this.uploadsDir = path.join(__dirname, "../../uploads");
    this.downloadsDir = path.join(__dirname, "../../downloads");
    this.tempDir = path.join(__dirname, "../../temp");

    // Ensure directories exist
    this.ensureDirectories();
  }

  /**
   * Ensure required directories exist
   */
  async ensureDirectories() {
    await fs.ensureDir(this.uploadsDir);
    await fs.ensureDir(this.downloadsDir);
    await fs.ensureDir(this.tempDir);
  }

  /**
   * Clean up old files
   */
  async cleanupOldFiles(maxAge = 24 * 60 * 60 * 1000) {
    // 24 hours default
    const now = Date.now();
    let cleanedCount = 0;

    // Clean uploads
    cleanedCount += await this.cleanupDirectory(this.uploadsDir, maxAge, now);

    // Clean downloads (keep longer - 7 days)
    cleanedCount += await this.cleanupDirectory(
      this.downloadsDir,
      maxAge * 7,
      now
    );

    // Clean temp directory (aggressive - 1 hour)
    cleanedCount += await this.cleanupDirectory(
      this.tempDir,
      60 * 60 * 1000,
      now
    );

    console.log(`Cleaned up ${cleanedCount} old files`);
    return cleanedCount;
  }

  /**
   * Clean up files in a directory
   */
  async cleanupDirectory(dirPath, maxAge, now) {
    let cleanedCount = 0;

    try {
      if (!(await fs.pathExists(dirPath))) {
        return 0;
      }

      const files = await fs.readdir(dirPath);

      for (const file of files) {
        const filePath = path.join(dirPath, file);
        const stats = await fs.stat(filePath);

        const fileAge = now - stats.mtime.getTime();

        if (fileAge > maxAge) {
          await fs.remove(filePath);
          cleanedCount++;
          console.log(`Cleaned up old file: ${filePath}`);
        }
      }
    } catch (error) {
      console.error(`Error cleaning directory ${dirPath}:`, error);
    }

    return cleanedCount;
  }

  /**
   * Get file info
   */
  async getFileInfo(filePath) {
    try {
      const stats = await fs.stat(filePath);
      return {
        size: stats.size,
        created: stats.birthtime,
        modified: stats.mtime,
        exists: true,
      };
    } catch (error) {
      return { exists: false };
    }
  }

  /**
   * Get directory size
   */
  async getDirectorySize(dirPath) {
    let totalSize = 0;

    try {
      if (!(await fs.pathExists(dirPath))) {
        return 0;
      }

      const files = await fs.readdir(dirPath);

      for (const file of files) {
        const filePath = path.join(dirPath, file);
        const stats = await fs.stat(filePath);

        if (stats.isDirectory()) {
          totalSize += await this.getDirectorySize(filePath);
        } else {
          totalSize += stats.size;
        }
      }
    } catch (error) {
      console.error(`Error calculating directory size ${dirPath}:`, error);
    }

    return totalSize;
  }

  /**
   * Get storage statistics
   */
  async getStorageStats() {
    const uploadsSize = await this.getDirectorySize(this.uploadsDir);
    const downloadsSize = await this.getDirectorySize(this.downloadsDir);
    const tempSize = await this.getDirectorySize(this.tempDir);

    return {
      uploads: {
        size: uploadsSize,
        sizeFormatted: this.formatBytes(uploadsSize),
      },
      downloads: {
        size: downloadsSize,
        sizeFormatted: this.formatBytes(downloadsSize),
      },
      temp: {
        size: tempSize,
        sizeFormatted: this.formatBytes(tempSize),
      },
      total: {
        size: uploadsSize + downloadsSize + tempSize,
        sizeFormatted: this.formatBytes(uploadsSize + downloadsSize + tempSize),
      },
    };
  }

  /**
   * Format bytes to human readable format
   */
  formatBytes(bytes) {
    if (bytes === 0) return "0 Bytes";

    const k = 1024;
    const sizes = ["Bytes", "KB", "MB", "GB", "TB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));

    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
  }

  /**
   * Create temporary directory for a job
   */
  async createJobTempDir(jobId) {
    const jobTempDir = path.join(this.tempDir, jobId);
    await fs.ensureDir(jobTempDir);
    return jobTempDir;
  }

  /**
   * Remove temporary directory for a job
   */
  async removeJobTempDir(jobId) {
    const jobTempDir = path.join(this.tempDir, jobId);
    await fs.remove(jobTempDir);
  }

  /**
   * Copy file safely
   */
  async copyFile(source, destination) {
    try {
      await fs.copy(source, destination);
      return true;
    } catch (error) {
      console.error(
        `Failed to copy file from ${source} to ${destination}:`,
        error
      );
      return false;
    }
  }

  /**
   * Move file safely
   */
  async moveFile(source, destination) {
    try {
      await fs.move(source, destination);
      return true;
    } catch (error) {
      console.error(
        `Failed to move file from ${source} to ${destination}:`,
        error
      );
      return false;
    }
  }

  /**
   * Delete file safely
   */
  async deleteFile(filePath) {
    try {
      await fs.remove(filePath);
      return true;
    } catch (error) {
      console.error(`Failed to delete file ${filePath}:`, error);
      return false;
    }
  }

  /**
   * Check if file exists
   */
  async fileExists(filePath) {
    return await fs.pathExists(filePath);
  }

  /**
   * Get available disk space (approximate)
   */
  async getAvailableSpace() {
    try {
      // This is a simple approximation - in production you might want to use a more robust solution
      const stats = await fs.stat(this.tempDir);
      return {
        available: true,
        // You could implement actual disk space checking here
        message: "Disk space check not implemented",
      };
    } catch (error) {
      return {
        available: false,
        message: error.message,
      };
    }
  }
}

module.exports = FileManager;
