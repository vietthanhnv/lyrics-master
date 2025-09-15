/**
 * Render Job Manager - Manages rendering jobs and their lifecycle
 */

const { v4: uuidv4 } = require("uuid");
const fs = require("fs-extra");
const path = require("path");

class RenderJobManager {
  constructor() {
    this.jobs = new Map();
    this.maxConcurrentJobs = 3; // Limit concurrent jobs to prevent overload
    this.activeJobs = 0;
    this.jobQueue = [];

    // Load persisted jobs on startup
    this.loadPersistedJobs();
  }

  /**
   * Create a new render job
   */
  async createJob(jobData) {
    const jobId = uuidv4();

    const job = {
      id: jobId,
      ...jobData,
      status: "queued",
      progress: 0,
      message: "Job queued",
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };

    this.jobs.set(jobId, job);

    // Add to queue if we're at capacity
    if (this.activeJobs >= this.maxConcurrentJobs) {
      this.jobQueue.push(jobId);
      job.status = "queued";
      job.message = `Queued (${this.jobQueue.length} jobs ahead)`;
    }

    // Persist job
    await this.persistJob(job);

    console.log(
      `Created job ${jobId} (${this.activeJobs}/${this.maxConcurrentJobs} active)`
    );

    return jobId;
  }

  /**
   * Get job by ID
   */
  getJob(jobId) {
    return this.jobs.get(jobId);
  }

  /**
   * Get job status
   */
  getJobStatus(jobId) {
    const job = this.jobs.get(jobId);
    if (!job) return null;

    return {
      id: job.id,
      status: job.status,
      progress: job.progress,
      message: job.message,
      createdAt: job.createdAt,
      updatedAt: job.updatedAt,
      outputPath: job.outputPath,
      error: job.error,
    };
  }

  /**
   * Update job status
   */
  updateJobStatus(jobId, status, message = "") {
    const job = this.jobs.get(jobId);
    if (!job) return false;

    job.status = status;
    job.message = message;
    job.updatedAt = new Date().toISOString();

    // Track active jobs
    if (status === "processing" && job.status !== "processing") {
      this.activeJobs++;
    } else if (
      (status === "completed" ||
        status === "failed" ||
        status === "cancelled") &&
      (job.status === "processing" || job.status === "queued")
    ) {
      this.activeJobs = Math.max(0, this.activeJobs - 1);
      this.processQueue();
    }

    this.persistJob(job);
    return true;
  }

  /**
   * Update job progress
   */
  updateJobProgress(jobId, progress, message = "") {
    const job = this.jobs.get(jobId);
    if (!job) return false;

    job.progress = Math.round(progress);
    if (message) job.message = message;
    job.updatedAt = new Date().toISOString();

    // Don't persist on every progress update to avoid I/O overhead
    // Only persist on significant progress changes
    if (job.progress % 10 === 0 || job.progress >= 100) {
      this.persistJob(job);
    }

    return true;
  }

  /**
   * Complete a job
   */
  completeJob(jobId, outputPath) {
    const job = this.jobs.get(jobId);
    if (!job) return false;

    job.status = "completed";
    job.progress = 100;
    job.message = "Render completed successfully";
    job.outputPath = outputPath;
    job.completedAt = new Date().toISOString();
    job.updatedAt = new Date().toISOString();

    this.activeJobs = Math.max(0, this.activeJobs - 1);
    this.persistJob(job);
    this.processQueue();

    console.log(`Job ${jobId} completed`);
    return true;
  }

  /**
   * Fail a job
   */
  failJob(jobId, error) {
    const job = this.jobs.get(jobId);
    if (!job) return false;

    job.status = "failed";
    job.message = `Render failed: ${error}`;
    job.error = error;
    job.failedAt = new Date().toISOString();
    job.updatedAt = new Date().toISOString();

    this.activeJobs = Math.max(0, this.activeJobs - 1);
    this.persistJob(job);
    this.processQueue();

    console.log(`Job ${jobId} failed: ${error}`);
    return true;
  }

  /**
   * Cancel a job
   */
  cancelJob(jobId) {
    const job = this.jobs.get(jobId);
    if (!job) return false;

    if (job.status === "completed") {
      return false; // Cannot cancel completed jobs
    }

    job.status = "cancelled";
    job.message = "Job cancelled by user";
    job.cancelledAt = new Date().toISOString();
    job.updatedAt = new Date().toISOString();

    // Remove from queue if queued
    const queueIndex = this.jobQueue.indexOf(jobId);
    if (queueIndex > -1) {
      this.jobQueue.splice(queueIndex, 1);
    }

    if (job.status === "processing") {
      this.activeJobs = Math.max(0, this.activeJobs - 1);
    }

    this.persistJob(job);
    this.processQueue();

    console.log(`Job ${jobId} cancelled`);
    return true;
  }

  /**
   * Get all jobs
   */
  getAllJobs() {
    return Array.from(this.jobs.values()).map((job) => ({
      id: job.id,
      status: job.status,
      progress: job.progress,
      message: job.message,
      createdAt: job.createdAt,
      updatedAt: job.updatedAt,
    }));
  }

  /**
   * Get active job count
   */
  getActiveJobCount() {
    return this.activeJobs;
  }

  /**
   * Cancel all jobs
   */
  cancelAllJobs() {
    const activeJobs = Array.from(this.jobs.values()).filter(
      (job) => job.status === "processing" || job.status === "queued"
    );

    activeJobs.forEach((job) => {
      this.cancelJob(job.id);
    });

    console.log(`Cancelled ${activeJobs.length} active jobs`);
  }

  /**
   * Process job queue
   */
  processQueue() {
    if (this.activeJobs < this.maxConcurrentJobs && this.jobQueue.length > 0) {
      const nextJobId = this.jobQueue.shift();
      const job = this.jobs.get(nextJobId);

      if (job && job.status === "queued") {
        job.status = "ready";
        job.message = "Ready to process";
        job.updatedAt = new Date().toISOString();
        this.persistJob(job);

        console.log(`Job ${nextJobId} moved from queue to ready`);
      }
    }

    // Update queue positions
    this.jobQueue.forEach((jobId, index) => {
      const job = this.jobs.get(jobId);
      if (job) {
        job.message = `Queued (${index + 1} jobs ahead)`;
        job.updatedAt = new Date().toISOString();
      }
    });
  }

  /**
   * Persist job to disk
   */
  async persistJob(job) {
    try {
      const jobsDir = path.join(__dirname, "../../data/jobs");
      await fs.ensureDir(jobsDir);

      const jobFile = path.join(jobsDir, `${job.id}.json`);
      await fs.writeJson(jobFile, job, { spaces: 2 });
    } catch (error) {
      console.error(`Failed to persist job ${job.id}:`, error);
    }
  }

  /**
   * Load persisted jobs on startup
   */
  async loadPersistedJobs() {
    try {
      const jobsDir = path.join(__dirname, "../../data/jobs");

      if (!(await fs.pathExists(jobsDir))) {
        return;
      }

      const jobFiles = await fs.readdir(jobsDir);

      for (const file of jobFiles) {
        if (file.endsWith(".json")) {
          try {
            const jobPath = path.join(jobsDir, file);
            const job = await fs.readJson(jobPath);

            // Reset processing jobs to failed on startup
            if (job.status === "processing") {
              job.status = "failed";
              job.message = "Job interrupted by server restart";
              job.error = "Server restart";
            }

            this.jobs.set(job.id, job);
          } catch (error) {
            console.error(`Failed to load job file ${file}:`, error);
          }
        }
      }

      console.log(`Loaded ${this.jobs.size} persisted jobs`);
    } catch (error) {
      console.error("Failed to load persisted jobs:", error);
    }
  }

  /**
   * Clean up old completed/failed jobs
   */
  async cleanupOldJobs(maxAge = 24 * 60 * 60 * 1000) {
    // 24 hours default
    const now = Date.now();
    const jobsToDelete = [];

    for (const [jobId, job] of this.jobs) {
      const jobAge = now - new Date(job.createdAt).getTime();

      if (
        jobAge > maxAge &&
        (job.status === "completed" ||
          job.status === "failed" ||
          job.status === "cancelled")
      ) {
        jobsToDelete.push(jobId);
      }
    }

    for (const jobId of jobsToDelete) {
      this.jobs.delete(jobId);

      // Delete persisted job file
      try {
        const jobFile = path.join(
          __dirname,
          "../../data/jobs",
          `${jobId}.json`
        );
        await fs.remove(jobFile);
      } catch (error) {
        console.error(`Failed to delete job file ${jobId}:`, error);
      }
    }

    console.log(`Cleaned up ${jobsToDelete.length} old jobs`);
    return jobsToDelete.length;
  }
}

module.exports = RenderJobManager;
