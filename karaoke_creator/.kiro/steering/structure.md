# Project Structure & Organization

## Root Directory Layout

```
/
├── app.js                    # Main client application entry point
├── index.html               # Main HTML page
├── styles.css               # Global CSS styles
├── server/                  # Backend server code
├── src/                     # Client-side source code
├── *.md                     # Documentation files
├── test_*                   # Test files and sample data
└── karaoke_sample_frame*    # Sample output images
```

## Client-Side Structure (`/src/`)

```
src/
├── client/
│   └── ServerRenderer.js    # Server communication and rendering coordination
└── core/                    # Rendering engines
    ├── batch-processor.js           # Batch processing utilities
    ├── fixed-memory-renderer.js     # Memory-constrained rendering
    ├── gpu-renderer.js              # GPU-accelerated rendering
    ├── memory-optimized-renderer.js # Memory-efficient streaming
    ├── parallel-renderer.js         # Parallel processing
    └── true-parallel-renderer.js    # Advanced parallel processing
```

## Server-Side Structure (`/server/`)

```
server/
├── server.js                # Main server entry point
├── package.json            # Server dependencies and scripts
├── src/core/               # Core server modules
│   ├── VideoProcessor.js   # Video processing logic
│   ├── RenderJobManager.js # Job lifecycle management
│   └── FileManager.js      # File operations and cleanup
├── uploads/                # Uploaded video files
├── downloads/              # Rendered output videos
├── temp/                   # Temporary processing files
├── data/                   # Job persistence data
└── start-server.*          # Platform-specific startup scripts
```

## File Naming Conventions

### Client Files

- **Main app**: `app.js` (single entry point)
- **Renderers**: `*-renderer.js` (specific rendering implementations)
- **Utilities**: `*-processor.js` (processing utilities)

### Server Files

- **Core modules**: PascalCase (e.g., `VideoProcessor.js`)
- **Entry points**: lowercase (e.g., `server.js`)
- **Scripts**: kebab-case (e.g., `start-server.sh`)

### Documentation

- **Guides**: UPPERCASE with underscores (e.g., `MEMORY_OPTIMIZATION_GUIDE.md`)
- **Architecture**: UPPERCASE with underscores (e.g., `CLIENT_SERVER_ARCHITECTURE.md`)

## Directory Responsibilities

### `/` (Root)

- Main client application files
- Global configuration and documentation
- Test files and sample data

### `/src/client/`

- Client-server communication
- Rendering coordination
- Upload/download management

### `/src/core/`

- Multiple rendering engine implementations
- Performance-optimized processing
- Memory management utilities

### `/server/src/core/`

- Server-side video processing
- Job management and queuing
- File system operations

### `/server/uploads/`, `/server/downloads/`, `/server/temp/`

- File storage with automatic cleanup
- Temporary processing workspace
- Organized by job ID for isolation

## Code Organization Patterns

### Modular Renderers

Each renderer in `/src/core/` implements a specific performance strategy:

- Memory optimization
- Parallel processing
- GPU acceleration
- Batch processing

### Server Components

Server follows separation of concerns:

- **VideoProcessor**: Pure video processing logic
- **RenderJobManager**: Job lifecycle and state management
- **FileManager**: File operations and cleanup policies

### Client-Server Communication

- REST API for job management
- WebSocket for real-time progress
- File upload/download endpoints
- Standardized job status responses
