# Technology Stack & Build System

## Frontend Stack

- **Core**: Vanilla JavaScript (ES6+), HTML5, CSS3
- **Rendering**: HTML5 Canvas 2D API for real-time preview and effects
- **Video**: HTML5 Video API for playback and MediaRecorder API for export
- **UI**: Custom CSS with modern features (flexbox, grid, backdrop-filter)
- **File Handling**: File API for video/subtitle uploads

## Backend Stack

- **Runtime**: Node.js 16+
- **Framework**: Express.js for REST API
- **WebSocket**: ws library for real-time progress updates
- **Video Processing**: FFmpeg (via ffmpeg-static and fluent-ffmpeg)
- **Canvas Rendering**: node-canvas for server-side text rendering
- **File Operations**: fs-extra, multer for uploads, sharp for image processing
- **Utilities**: uuid for job IDs, cors for cross-origin requests

## Key Dependencies

### Server Dependencies

```json
{
  "canvas": "^3.0.0-rc3",
  "express": "^4.21.2",
  "ffmpeg-static": "^5.2.0",
  "fluent-ffmpeg": "^2.1.3",
  "ws": "^8.18.3",
  "multer": "^1.4.5-lts.1",
  "sharp": "^0.32.6"
}
```

### Development Tools

- **Testing**: Jest for unit tests
- **Development**: nodemon for auto-restart
- **Process Management**: PM2 recommended for production

## Build & Development Commands

### Server Setup

```bash
cd server
npm install
npm start          # Production server
npm run dev        # Development with auto-restart
npm test           # Run test suite
```

### Client Setup

No build process required - serves static files directly from root directory.

### System Prerequisites

**Ubuntu/Debian:**

```bash
sudo apt-get install build-essential libcairo2-dev libpango1.0-dev libjpeg-dev libgif-dev librsvg2-dev
```

**macOS:**

```bash
brew install pkg-config cairo pango libpng jpeg giflib librsvg
```

**Windows:**
Canvas dependencies install automatically. If issues occur, install Visual Studio Build Tools.

## Architecture Patterns

- **Client-Server Separation**: Browser handles preview, server handles production rendering
- **Memory Streaming**: File-based processing to prevent memory issues
- **Job Queue System**: Concurrent processing with automatic cleanup
- **WebSocket Communication**: Real-time progress updates
- **Modular Renderers**: Multiple rendering engines for different performance needs

## Performance Considerations

- **Memory Management**: Batch processing (100 frames max in memory)
- **Concurrent Jobs**: Max 3 simultaneous render jobs
- **File Cleanup**: Automatic cleanup of temporary files (1 hour) and downloads (24 hours)
- **Hardware Acceleration**: FFmpeg hardware acceleration when available
