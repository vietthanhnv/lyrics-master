# Karaoke Video Creator Suite

A complete end-to-end solution for creating professional karaoke videos from audio files. This suite combines AI-powered subtitle extraction with advanced video rendering to produce high-quality karaoke content.

## 🎯 Overview

The Karaoke Video Creator Suite consists of two integrated tools:

1. **Subtitle Tool** - AI-powered subtitle extraction from audio files
2. **Karaoke Creator** - Professional karaoke video rendering with animated effects

### Complete Workflow

```
Audio File → [Subtitle Tool] → Synchronized Subtitles → [Karaoke Creator] → Karaoke Video
    ↓              ↓                      ↓                    ↓              ↓
  MP3/WAV     AI Processing         JSON/SRT/ASS         Video Rendering    MP4 Output
```

## 🚀 Quick Start

### Prerequisites

- **Python 3.9+** (for Subtitle Tool)
- **Node.js 16+** (for Karaoke Creator)
- **4GB+ RAM** (8GB+ recommended)
- **FFmpeg** (automatically handled by tools)

### Installation

1. **Clone the repository:**

   ```bash
   git clone <repository-url>
   cd karaoke-video-creator-suite
   ```

2. **Setup Subtitle Tool:**

   ```bash
   cd subtitle_tool
   pip install -r requirements.txt
   ```

3. **Setup Karaoke Creator:**
   ```bash
   cd ../karaoke_creator
   npm install
   ```

### Basic Usage

1. **Extract Subtitles:**

   ```bash
   cd subtitle_tool
   python run_app.py
   # Load your audio file and generate subtitles
   ```

2. **Create Karaoke Video:**
   ```bash
   cd ../karaoke_creator
   # Start the server
   cd server && npm start
   # Open index.html in browser
   # Load video/image + generated subtitles
   ```

## 📋 Detailed Features

### Subtitle Tool Features

- **🎵 AI-Powered Processing**

  - Demucs vocal separation
  - WhisperX speech recognition
  - Word-level timing synchronization

- **📝 Multiple Output Formats**

  - SRT (SubRip)
  - ASS (Advanced SubStation Alpha with karaoke effects)
  - VTT (WebVTT)
  - JSON (for Karaoke Creator)

- **🌍 Translation Support**

  - DeepL integration
  - Google Translate support
  - Bilingual subtitle generation

- **⚡ Batch Processing**
  - Process multiple files simultaneously
  - Offline operation after model download
  - Cross-platform desktop interface

### Karaoke Creator Features

- **🎬 Multiple Input Modes**

  - Video files (.mp4, .avi, .mov)
  - Image + Audio combinations
  - Static backgrounds with music

- **✨ Advanced Subtitle Effects**

  - Word-by-word highlighting
  - Fade in/out animations
  - Slide transitions (all directions)
  - Zoom effects
  - Particle burst animations
  - Color progression (karaoke style)

- **🖥️ Dual Rendering Modes**

  - **Browser Mode**: Real-time preview and fast rendering
  - **Server Mode**: Professional quality, unlimited video length

- **📊 Professional Output**
  - Multiple resolutions (720p/1080p/4K)
  - Various frame rates (24/30/60 fps)
  - High-quality audio preservation
  - Multiple codec support (VP9, VP8, H.264)

## 🔧 Technical Architecture

### Subtitle Tool (Python/PyQt6)

```
Audio Input → Vocal Separation → Speech Recognition → Timing Alignment → Subtitle Export
     ↓              ↓                    ↓                  ↓              ↓
   MP3/WAV      Demucs AI           WhisperX AI        Word-level      SRT/ASS/JSON
```

**Key Technologies:**

- **Demucs**: Facebook's AI model for vocal separation
- **WhisperX**: Enhanced Whisper with forced alignment
- **PyQt6**: Cross-platform desktop interface
- **Librosa**: Audio processing and analysis

### Karaoke Creator (Node.js/JavaScript)

```
Video/Image + Subtitles → Canvas Rendering → Effect Processing → Video Export
       ↓                        ↓                  ↓              ↓
   MP4 + JSON              HTML5 Canvas      Animated Effects    MP4 Output
```

**Key Technologies:**

- **Node.js**: Server-side video processing
- **FFmpeg**: Professional video manipulation
- **HTML5 Canvas**: Real-time rendering engine
- **WebSocket**: Real-time progress updates
- **MediaRecorder API**: Browser-based video capture

## 📖 Usage Guide

### Step 1: Extract Subtitles from Audio

1. **Launch Subtitle Tool:**

   ```bash
   cd subtitle_tool
   python run_app.py
   ```

2. **Process Audio File:**

   - Select your audio file (MP3, WAV, FLAC, OGG)
   - Choose AI model size (larger = more accurate, slower)
   - Select output formats (include JSON for karaoke)
   - Click "Generate Subtitles"

3. **Review Output:**
   - Check generated subtitle files
   - Verify timing accuracy
   - Edit if necessary

### Step 2: Create Karaoke Video

1. **Start Karaoke Creator:**

   ```bash
   cd karaoke_creator
   # Start server (recommended for best quality)
   cd server && npm start
   # Open client in browser
   open http://localhost:3000
   ```

2. **Load Media:**

   - **Video Mode**: Upload video file
   - **Image + Audio Mode**: Upload image and audio separately

3. **Load Subtitles:**

   - Import the JSON file from Step 1
   - Verify subtitle timing with preview

4. **Customize Effects:**

   - Choose karaoke style (highlight, fade, slide)
   - Adjust colors and fonts
   - Set animation timing

5. **Render Video:**
   - Select quality settings
   - Choose render mode (Server recommended)
   - Monitor progress via real-time updates
   - Download completed video

## 🎨 Customization Options

### Subtitle Styles

- **Font Selection**: Choose from system fonts
- **Color Schemes**: Customize text and highlight colors
- **Size and Position**: Adjust subtitle placement
- **Animation Speed**: Control effect timing

### Video Effects

- **Karaoke Highlighting**: Word-by-word color changes
- **Entrance Effects**: Fade, slide, zoom animations
- **Background Options**: Static images or video backgrounds
- **Quality Settings**: Resolution and bitrate control

## 🔧 Advanced Configuration

### Subtitle Tool Configuration

Located at:

- Windows: `%APPDATA%/LyricToSubtitleApp/config.yaml`
- macOS: `~/Library/Application Support/LyricToSubtitleApp/config.yaml`
- Linux: `~/.config/lyric-to-subtitle-app/config.yaml`

```yaml
# Example configuration
models:
  whisper_model: "medium" # tiny, base, small, medium, large
  demucs_model: "htdemucs"

output:
  formats: ["srt", "ass", "json"]
  word_level: true

translation:
  enabled: false
  target_language: "es"
  service: "deepl" # or "google"
```

### Karaoke Creator Settings

Server configuration in `karaoke_creator/server/config.json`:

```json
{
  "server": {
    "port": 3001,
    "maxFileSize": "2GB",
    "tempRetention": "1h",
    "downloadRetention": "7d"
  },
  "rendering": {
    "defaultQuality": "high",
    "maxConcurrentJobs": 3,
    "enableHardwareAcceleration": true
  }
}
```

## 🚀 Performance Optimization

### For Large Files

1. **Use Server Mode**: Handles unlimited video length
2. **Optimize Settings**: Balance quality vs. speed
3. **Batch Processing**: Process multiple files efficiently
4. **Hardware Acceleration**: Enable GPU processing when available

### Memory Management

- **Subtitle Tool**: Processes audio in chunks
- **Karaoke Creator**: File-based streaming prevents memory issues
- **Automatic Cleanup**: Temporary files removed automatically

## 🧪 Testing

### Subtitle Tool Testing

```bash
cd subtitle_tool
pytest tests/
```

### Karaoke Creator Testing

```bash
cd karaoke_creator
# Test server functionality
node test_server_simple.js
# Test image+audio workflow
open test_image_audio.html
```

## 📦 Building Standalone Applications

### Subtitle Tool Executable

```bash
cd subtitle_tool
# Windows
build_scripts\build_windows.bat
# macOS
./build_scripts/build_macos.sh
# Linux
./build_scripts/build_linux.sh
```

### Karaoke Creator Distribution

The Karaoke Creator runs in web browsers and doesn't require building. For deployment:

1. **Local Server**: Run Node.js server locally
2. **Cloud Deployment**: Deploy to cloud platforms
3. **Docker**: Use containerization for easy deployment

## 🔍 Troubleshooting

### Common Issues

1. **Subtitle Tool Won't Start**

   - Check Python version (3.9+ required)
   - Install missing dependencies: `pip install -r requirements.txt`
   - Verify PyQt6 installation

2. **Poor Subtitle Accuracy**

   - Use larger Whisper model (medium/large)
   - Ensure good audio quality
   - Check for background noise

3. **Karaoke Creator Server Issues**

   - Verify Node.js installation
   - Check port 3001 availability
   - Install FFmpeg if missing

4. **Video Export Problems**
   - Use Server Mode for large files
   - Check available disk space
   - Verify subtitle timing accuracy

### Performance Issues

- **Slow Processing**: Use smaller AI models or upgrade hardware
- **Memory Errors**: Enable Server Mode for video processing
- **Quality Issues**: Use higher resolution inputs and quality settings

## 🤝 Contributing

We welcome contributions to both tools:

1. **Fork the repository**
2. **Create feature branch**: `git checkout -b feature/amazing-feature`
3. **Make changes and test thoroughly**
4. **Submit pull request with detailed description**

### Development Setup

```bash
# Subtitle Tool development
cd subtitle_tool
pip install -r requirements-dev.txt
pre-commit install

# Karaoke Creator development
cd karaoke_creator
npm install
# No additional setup required
```

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

### Subtitle Tool

- [Demucs](https://github.com/facebookresearch/demucs) by Facebook Research
- [WhisperX](https://github.com/m-bain/whisperX) by Max Bain
- [OpenAI Whisper](https://github.com/openai/whisper) by OpenAI

### Karaoke Creator

- HTML5 Canvas and MediaRecorder APIs
- FFmpeg for professional video processing
- Node.js and Express.js ecosystem

## 📞 Support

For support and questions:

1. **Check Documentation**: Review this README and individual tool guides
2. **Search Issues**: Look for existing solutions in GitHub issues
3. **Create Issue**: Submit detailed bug reports or feature requests
4. **Community**: Join discussions and share your creations

---

**Create professional karaoke videos with AI-powered subtitle extraction and advanced rendering effects!** 🎤✨
