# 🎤 Karaoke Renderer Server

A Node.js server for processing karaoke videos with file-based streaming to prevent memory issues.

## 🚀 Features

- **File-based Processing**: No memory limits, processes any video length
- **Real-time Progress**: WebSocket updates with live progress
- **Concurrent Jobs**: Process multiple videos simultaneously
- **Automatic Cleanup**: Manages temporary files and old downloads
- **FFmpeg Integration**: Professional video processing with audio preservation
- **Job Management**: Queue, cancel, and monitor render jobs

## 📋 Prerequisites

- Node.js 16+
- FFmpeg (automatically installed via ffmpeg-static)
- Canvas dependencies for text rendering

### Installing Canvas Dependencies

**Ubuntu/Debian:**

```bash
sudo apt-get install build-essential libcairo2-dev libpango1.0-dev libjpeg-dev libgif-dev librsvg2-dev
```

**macOS:**

```bash
brew install pkg-config cairo pango libpng jpeg giflib librsvg
```

**Windows:**
Canvas should install automatically. If issues occur, install Visual Studio Build Tools.

## 🛠️ Installation

1. **Install dependencies:**

```bash
cd server
npm install
```

2. **Start the server:**

```bash
npm start
```

Or for development with auto-restart:

```bash
npm run dev
```

## 🔧 Configuration

The server runs on:

- **HTTP Server**: `http://localhost:3001`
- **WebSocket**: `ws://localhost:3002`

### Environment Variables

```bash
PORT=3001                    # HTTP server port
WS_PORT=3002                # WebSocket port
MAX_CONCURRENT_JOBS=3       # Maximum concurrent render jobs
CLEANUP_INTERVAL=3600000    # File cleanup interval (1 hour)
MAX_FILE_AGE=86400000      # Max file age before cleanup (24 hours)
```

## 📁 Directory Structure

```
server/
├── uploads/          # Uploaded video files
├── downloads/        # Rendered output videos
├── temp/            # Temporary processing files
├── data/            # Job persistence
└── src/
    └── core/
        ├── VideoProcessor.js    # Video processing logic
        ├── RenderJobManager.js  # Job lifecycle management
        └── FileManager.js       # File operations
```

## 🔌 API Endpoints

### Health Check

```http
GET /health
```

Returns server status and memory usage.

### Upload Video

```http
POST /upload/video
Content-Type: multipart/form-data

{
  "video": <file>
}
```

### Start Render Job

```http
POST /render/start
Content-Type: application/json

{
  "videoId": "uploaded-video-id",
  "subtitles": [...],
  "wordSegments": [...],
  "effects": {...},
  "renderSettings": {
    "resolution": "1080p",
    "frameRate": 30,
    "quality": "high",
    "format": "mp4"
  }
}
```

### Get Job Status

```http
GET /render/status/:jobId
```

### Download Video

```http
GET /download/:jobId
```

### Cancel Job

```http
POST /render/cancel/:jobId
```

## 🔄 WebSocket Events

### Client → Server

```javascript
{
  "type": "subscribe",
  "jobId": "job-uuid"
}
```

### Server → Client

```javascript
{
  "type": "jobUpdate",
  "jobId": "job-uuid",
  "status": "processing",
  "percent": 45,
  "message": "Processing frame 1247/9000"
}
```

## 🎯 Processing Flow

1. **Upload**: Client uploads video to server
2. **Job Creation**: Server creates render job and queues it
3. **Frame Extraction**: FFmpeg extracts video frames in batches
4. **Karaoke Rendering**: Canvas renders text effects on each frame
5. **Video Assembly**: FFmpeg combines frames back to video with audio
6. **Download**: Client downloads completed video

## 📊 Memory Management

### File-based Processing

- Processes frames in batches of 100
- Immediately deletes temporary files after processing
- Never stores all frames in memory simultaneously
- Automatic garbage collection between batches

### Storage Cleanup

- Automatic cleanup of old files (24 hours)
- Temporary files cleaned aggressively (1 hour)
- Downloads kept longer (7 days)
- Manual cleanup endpoint available

## 🚀 Performance

### Concurrent Processing

- Up to 3 simultaneous render jobs
- Job queuing system for overflow
- Automatic load balancing

### Optimization Features

- FFmpeg hardware acceleration (when available)
- Efficient frame batching
- Memory-mapped file operations
- Progressive JPEG for temporary frames

## 🔍 Monitoring

### Health Endpoint

```bash
curl http://localhost:3001/health
```

Returns:

```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00.000Z",
  "memory": {
    "rss": 45678912,
    "heapTotal": 23456789,
    "heapUsed": 12345678
  },
  "activeJobs": 2
}
```

### Job Listing

```bash
curl http://localhost:3001/jobs
```

## 🧪 Testing

Run tests:

```bash
npm test
```

Test server health:

```bash
curl http://localhost:3001/health
```

## 🐛 Troubleshooting

### Common Issues

**Canvas installation fails:**

- Install system dependencies (see Prerequisites)
- Use Node.js 16+ (Canvas compatibility)

**FFmpeg not found:**

- FFmpeg is included via ffmpeg-static
- Check if antivirus is blocking the binary

**Out of disk space:**

- Check `/temp` directory cleanup
- Adjust `MAX_FILE_AGE` environment variable
- Run manual cleanup: `POST /cleanup`

**WebSocket connection fails:**

- Check if port 3002 is available
- Verify firewall settings
- Check browser WebSocket support

### Logs

Server logs include:

- Job creation and completion
- File operations
- Error details with stack traces
- Performance metrics

## 🔒 Security Considerations

- File upload size limits (500MB)
- Automatic file cleanup prevents disk filling
- No file execution, only processing
- Temporary directories isolated per job

## 📈 Scaling

For production deployment:

- Use PM2 for process management
- Add Redis for job queue persistence
- Implement horizontal scaling with load balancer
- Add authentication and rate limiting
- Use cloud storage for file management

## 🎉 Benefits

✅ **No Memory Limits**: Process videos of any length  
✅ **Professional Quality**: FFmpeg-based processing  
✅ **Real-time Updates**: Live progress via WebSocket  
✅ **Concurrent Processing**: Multiple jobs simultaneously  
✅ **Automatic Cleanup**: No manual file management  
✅ **Audio Preservation**: Maintains original audio quality  
✅ **Cross-platform**: Works on Windows, macOS, Linux
