# Testing Image + Audio Mode - Step by Step

## Prerequisites

1. Server must be running on port 3001
2. Client must be running on port 3000 (or served statically)
3. You need test files: one image and one audio file

## Test Steps

### 1. Start the Server

```bash
cd server
npm start
```

Wait for the message: "🎤 Karaoke Render Server running on port 3001"

### 2. Open the Application

Open your browser and go to: `http://localhost:3000`

### 3. Switch to Image + Audio Mode

- Look for the input mode selector at the top
- Select "🖼️ Image + Audio Mode" radio button
- The interface should switch to show "Load Image" and "Load Audio" buttons

### 4. Load Files

1. Click "Load Image" and select an image file (JPG, PNG, etc.)
   - You should see a success message: "Image loaded: [filename]"
   - The image should appear on the canvas
2. Click "Load Audio" and select an audio file (MP3, WAV, etc.)
   - You should see a success message: "Audio loaded: [filename] ([duration]s)"
3. Wait for upload completion
   - You should see: "Image and audio uploaded successfully"
   - Check browser console for: "Uploaded video ID: [some-id]"

### 5. Load Subtitles (Optional)

- Click "Load Subtitles" and select a JSON subtitle file
- Or use the default subtitles that come with the app

### 6. Test Rendering

1. Scroll down to the "Export Video" section
2. Make sure "Render Mode" is set to "🖥️ Server (No Memory Limits)"
3. Click "🎬 Start Render"

### Expected Results

- Render should start without the "No video uploaded to server" error
- Progress bar should appear and show rendering progress
- Server console should show video processing messages

## Debugging Steps

### If Upload Fails

1. Check server console for error messages
2. Verify file formats are supported
3. Check file sizes (should be under 2GB total)
4. Try with smaller test files

### If Render Fails

1. Open browser console (F12) and check for errors
2. Look for the debug messages we added:
   ```
   Starting render with state: {...}
   renderVideoOnServer called with: {...}
   ```
3. Check if `uploadedVideoId` is null or undefined

### Debug Pages

- Use `debug-image-audio.html` for isolated testing
- Use `test_image_audio.html` for component testing

## Common Issues and Solutions

### "No video uploaded to server"

This means `uploadedVideoId` is null. Possible causes:

1. Files not uploaded yet - wait for upload completion
2. Upload failed - check server logs
3. Wrong input mode - make sure you're in Image+Audio mode

### "Server not available"

1. Check if server is running on port 3001
2. Try accessing http://localhost:3001/health directly
3. Check firewall/antivirus blocking the connection

### Files not loading

1. Check file formats are supported
2. Try with smaller files first
3. Check browser console for detailed errors

## Test Files

For testing, you can use:

- **Image**: Any JPG or PNG file (preferably 1920x1080 or similar)
- **Audio**: Any MP3 or WAV file (a few seconds is fine for testing)
- **Subtitles**: Use the included `test_subtitles.json` or create a simple one:

```json
{
  "segments": [
    {
      "start_time": 0,
      "end_time": 5,
      "text": "Test subtitle"
    }
  ],
  "word_segments": [
    {
      "word": "Test",
      "start_time": 0,
      "end_time": 2.5
    },
    {
      "word": "subtitle",
      "start_time": 2.5,
      "end_time": 5
    }
  ]
}
```

## Success Indicators

✅ Image appears on canvas  
✅ Audio duration is detected  
✅ "Image and audio uploaded successfully" message  
✅ Console shows "Uploaded video ID: [id]"  
✅ Render starts without errors  
✅ Progress bar shows rendering progress  
✅ Final video file is generated

If all these work, the image+audio mode is functioning correctly!
