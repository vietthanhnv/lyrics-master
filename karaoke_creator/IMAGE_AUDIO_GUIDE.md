# Image + Audio Karaoke Mode Guide

## Overview

The Karaoke Video Renderer now supports creating karaoke videos from static images and audio files. This feature is perfect when you don't have an existing video but want to create karaoke content with a background image and audio track.

## How It Works

### Input Mode Selection

- **Video Mode**: Traditional mode using video files
- **Image + Audio Mode**: New mode using image + audio files

### Supported File Formats

#### Images

- JPEG (.jpg, .jpeg)
- PNG (.png)
- GIF (.gif)
- WebP (.webp)
- BMP (.bmp)

#### Audio

- MP3 (.mp3)
- WAV (.wav)
- AAC (.aac)
- OGG (.ogg)
- M4A (.m4a)

## Usage Instructions

### 1. Switch to Image + Audio Mode

1. Open the karaoke application
2. In the file controls section, select "🖼️ Image + Audio Mode"
3. The interface will switch to show image and audio file inputs

### 2. Load Your Files

1. Click "Load Image" and select your background image
2. Click "Load Audio" and select your audio track
3. The application will automatically determine the video length based on the audio duration

### 3. Add Subtitles

1. Load your subtitle JSON file as usual
2. The subtitles will be synchronized with the audio timing
3. Edit subtitles in the transcript editor if needed

### 4. Customize Effects

- All karaoke effects work the same as in video mode
- Font styling, colors, animations, and positioning
- Preview effects in real-time on the canvas

### 5. Render Your Video

1. Choose your render settings (resolution, quality, etc.)
2. Select "Server" render mode for best results
3. Click "Start Render" to create your karaoke video

## Technical Details

### Server Processing

When you upload image and audio files, the server:

1. Analyzes the audio duration
2. Creates a video by looping the static image for the audio duration
3. Scales and pads the image to fit 1920x1080 resolution
4. Combines the image and audio into a standard video file
5. Processes karaoke effects frame by frame

### Video Specifications

- **Resolution**: 1920x1080 (Full HD)
- **Frame Rate**: Matches your render settings (24/30/60 FPS)
- **Format**: MP4 with H.264 video and AAC audio
- **Aspect Ratio**: Image is scaled to fit while maintaining aspect ratio

### Performance Considerations

- **Image Size**: Large images are automatically scaled down
- **Audio Length**: Longer audio files create longer videos
- **Memory Usage**: More efficient than video processing
- **Render Time**: Generally faster than video processing

## Use Cases

### 1. Lyric Videos

- Create lyric videos with album artwork
- Use band photos or artistic backgrounds
- Perfect for music releases

### 2. Educational Content

- Language learning with pronunciation guides
- Poetry recitation with relevant imagery
- Historical content with period images

### 3. Karaoke Creation

- Convert audio-only tracks to karaoke videos
- Add custom backgrounds for themed karaoke
- Create practice videos for singers

### 4. Social Media Content

- Instagram/TikTok lyric videos
- YouTube karaoke content
- Facebook video posts

## Tips and Best Practices

### Image Selection

- **High Resolution**: Use images at least 1920x1080 for best quality
- **Aspect Ratio**: 16:9 images work best (no black bars)
- **File Size**: Optimize images to reduce upload time
- **Content**: Choose images that complement your audio

### Audio Quality

- **Bitrate**: Use high-quality audio (192kbps or higher)
- **Format**: MP3 or WAV for best compatibility
- **Length**: Ensure audio length matches your subtitle timing
- **Volume**: Normalize audio levels for consistent playback

### Subtitle Timing

- **Sync**: Ensure subtitle timing matches audio precisely
- **Duration**: Account for the full audio length
- **Breaks**: Add appropriate pauses between lines
- **Testing**: Preview timing before final render

## Troubleshooting

### Common Issues

#### "Files not uploading"

- Check file formats are supported
- Ensure files are not corrupted
- Verify server is running (localhost:3001)
- Check file size limits (2GB total)

#### "Preview not showing"

- Refresh the page and try again
- Check browser console for errors
- Ensure both files are loaded successfully
- Verify image format compatibility

#### "Render fails"

- Check server logs for detailed errors
- Ensure subtitle timing doesn't exceed audio length
- Verify all files are properly uploaded
- Try with smaller/different files

#### "Audio sync issues"

- Check subtitle timing accuracy
- Verify audio file integrity
- Ensure consistent frame rate settings
- Test with shorter audio clips first

### Server Requirements

- Node.js 16+ with FFmpeg support
- Sufficient disk space for temporary files
- Network connectivity for file uploads
- Canvas and image processing libraries

## API Reference

### Client Methods

```javascript
// Switch input modes
app.switchInputMode("imageAudio");

// Load files
app.loadImage(imageFileEvent);
app.loadAudio(audioFileEvent);

// Upload to server
serverRenderer.uploadImageAudio(imageFile, audioFile);
```

### Server Endpoints

```
POST /upload/image-audio
- Accepts: multipart/form-data
- Fields: image (file), audio (file)
- Returns: { success, videoId, videoInfo }
```

## Future Enhancements

### Planned Features

- Multiple image slideshow support
- Image transition effects
- Audio visualization overlays
- Batch processing for multiple files
- Custom image filters and effects

### Community Contributions

- Submit feature requests via GitHub issues
- Contribute code improvements
- Share example projects and templates
- Report bugs and compatibility issues

---

For more information, see the main documentation files:

- [Build Guide](Build_Guide.md)
- [Client-Server Architecture](CLIENT_SERVER_ARCHITECTURE.md)
- [Memory Optimization](MEMORY_OPTIMIZATION_GUIDE.md)
