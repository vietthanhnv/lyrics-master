# Karaoke Subtitle Video Application (Canvas-Based)

## Core Principle

- Both preview and final rendering use the same HTML5 Canvas (2D or WebGL) engine.
- Guarantees consistency: what you see in preview is identical to the exported .mp4.

## Input

- Video file (.mp4) loaded into the app.
- Subtitle file (.json) with timing and text data (line or word level). (Example: test_subtitles.json)

## Timeline Editor

- Visual track showing video duration.
- Subtitle entries aligned on the timeline.
- User can:
  - Adjust subtitle start/end times by dragging
  - Split or merge lines
  - Add or delete subtitle entries
  - Zoom in/out timeline for fine adjustments

## Subtitle Effects Engine (Canvas)

- Each subtitle is drawn as a text layer with customizable effects:
  - Fade in/out
  - Slide (left/right/up/down)
  - Zoom in/out
  - Word-by-word particle burst
  - Color progression (karaoke highlight effect)
  - Font/size change during playback
- Effects applied via Canvas animations (requestAnimationFrame) for preview and identical frame rendering for export.

## Preview Mode

- Real-time video playback with subtitle effects rendered on canvas.
- Playback controls: play/pause, scrub timeline, jump to subtitle.
- Editable in timeline: adjust timing and instantly reflect changes in preview.

## Export Mode ✅ IMPLEMENTED

1. Choose export settings:
   - Resolution: 720p / 1080p / 4K
   - Frame rate: 24/30/60 fps
   - Quality presets: High/Medium/Low
2. Render pipeline:
   - Uses MediaRecorder API with Canvas.captureStream()
   - Records video with synchronized karaoke effects in real-time
   - Captures audio from original video automatically
   - Supports multiple codecs (VP9, VP8, H.264) with fallback
3. Output: .webm or .mp4 file with embedded animated subtitles

### Browser Compatibility

- **Primary method**: MediaRecorder API (Chrome 47+, Firefox 29+, Edge 79+, Safari 14.1+)
- **Fallback method**: Frame sequence export for older browsers
- **Audio support**: Automatic audio capture from source video

## Tech Stack Recommendation (consistent Canvas flow)

- Front-end UI: HTML5 + JavaScript (React optional for UI panels)
- Rendering: Canvas 2D API or WebGL for more complex particle effects

## This architecture ensures

- Single rendering logic → no mismatch between preview and export
- Timeline editor → full control over subtitle accuracy
- Canvas effects engine → flexible animations, extensible later (glow, beat sync, etc.)

## New Features (Recently Implemented)

### ✅ Full Video Export

- **Real video export**: No longer just sample frames - exports complete video files
- **Audio preservation**: Automatically includes audio from source video
- **Multiple formats**: Supports WebM (VP9/VP8) and MP4 (H.264) with automatic codec detection
- **Quality control**: High/Medium/Low quality presets with appropriate bitrates
- **Progress tracking**: Real-time progress indicator during export
- **Error handling**: Graceful fallback for unsupported browsers

### ✅ Enhanced Compatibility

- **Modern browsers**: Full MediaRecorder API support for direct video recording
- **Legacy support**: Frame sequence export fallback for older browsers
- **Cross-platform**: Works on Windows, macOS, and Linux
- **Mobile friendly**: Responsive design works on tablets and phones

### ✅ Improved User Experience

- **One-click export**: Simple button click starts the entire export process
- **Visual feedback**: Progress bar and status messages keep users informed
- **Automatic naming**: Generated filenames with timestamps prevent overwrites
- **Error recovery**: Clear error messages and alternative export methods
