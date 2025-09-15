# Product Overview

## Karaoke Video Renderer

A web-based karaoke video creation application that allows users to add animated subtitle effects to videos. The application features a client-server architecture designed to handle videos of any length without memory limitations.

### Key Features

- **Video Upload & Processing**: Upload video files and add karaoke-style subtitle effects
- **Real-time Preview**: Live preview of subtitle effects using HTML5 Canvas
- **Multiple Rendering Modes**: Various performance-optimized rendering engines (streaming, parallel, GPU-accelerated)
- **Memory Optimization**: File-based processing prevents browser memory crashes on long videos
- **Professional Export**: FFmpeg-based server rendering for production-quality output
- **WebSocket Progress**: Real-time progress updates during server-side rendering
- **Effect Customization**: Comprehensive text styling, animations, and karaoke highlight effects

### Architecture

- **Client**: Browser-based editor with Canvas preview and effect controls
- **Server**: Node.js backend with FFmpeg integration for memory-efficient video processing
- **Processing**: Hybrid approach - client for preview, server for final rendering

### Target Use Cases

- Creating karaoke videos with synchronized text highlighting
- Adding animated subtitles to videos
- Professional video production with custom text effects
- Educational content with timed text overlays
