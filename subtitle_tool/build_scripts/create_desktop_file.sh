#!/bin/bash
# Create a .desktop file for Linux desktop integration

set -e

APP_NAME="Lyric-to-Subtitle App"
APP_EXEC="LyricToSubtitleApp"
APP_ICON="lyric-to-subtitle-app"
APP_CATEGORIES="AudioVideo;Audio;Video;Qt;"

# Get the installation directory
if [ $# -eq 0 ]; then
    echo "Usage: $0 <installation_directory>"
    echo "Example: $0 /opt/lyric-to-subtitle-app"
    exit 1
fi

INSTALL_DIR="$1"
DESKTOP_FILE="$HOME/.local/share/applications/lyric-to-subtitle-app.desktop"

# Create the desktop file
cat > "$DESKTOP_FILE" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=$APP_NAME
Comment=Generate word-level synchronized subtitles from music files
Exec=$INSTALL_DIR/$APP_EXEC
Icon=$APP_ICON
Terminal=false
Categories=$APP_CATEGORIES
MimeType=audio/mpeg;audio/wav;audio/flac;audio/ogg;
Keywords=subtitles;karaoke;lyrics;audio;music;
StartupNotify=true
StartupWMClass=lyric-to-subtitle-app
EOF

# Make the desktop file executable
chmod +x "$DESKTOP_FILE"

echo "✅ Desktop file created: $DESKTOP_FILE"
echo
echo "The application should now appear in your application menu."
echo "You may need to log out and back in for changes to take effect."
echo
echo "To install system-wide (requires sudo):"
echo "  sudo cp '$DESKTOP_FILE' /usr/share/applications/"