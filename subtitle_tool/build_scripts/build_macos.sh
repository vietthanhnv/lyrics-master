#!/bin/bash
# macOS build script for Lyric-to-Subtitle App
# This script builds a standalone macOS application bundle using PyInstaller

set -e  # Exit on any error

echo "🍎 Building Lyric-to-Subtitle App for macOS..."
echo

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 is not installed or not in PATH"
    echo "Please install Python 3.9 or later using Homebrew:"
    echo "  brew install python@3.11"
    exit 1
fi

# Check Python version
python_version=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "🐍 Using Python $python_version"

# Check if we're in a virtual environment (recommended)
if [[ -z "$VIRTUAL_ENV" ]]; then
    echo "⚠️  Warning: Not running in a virtual environment"
    echo "It's recommended to use a virtual environment for building"
    echo
fi

# Install build dependencies if needed
echo "🔍 Checking build dependencies..."
if ! python3 -c "import PyInstaller" &> /dev/null; then
    echo "📦 Installing PyInstaller..."
    pip3 install pyinstaller
fi

# Check for Xcode command line tools (needed for some dependencies)
if ! xcode-select -p &> /dev/null; then
    echo "⚠️  Warning: Xcode command line tools not found"
    echo "Some dependencies may fail to build. Install with:"
    echo "  xcode-select --install"
fi

# Run the build script
echo
echo "🔨 Starting build process..."
python3 build_scripts/build.py "$@"

if [ $? -eq 0 ]; then
    echo
    echo "✅ Build completed successfully!"
    echo
    echo "📱 The application bundle is available in the 'dist' folder:"
    echo "   dist/LyricToSubtitleApp.app"
    echo
    echo "🚀 To test the application:"
    echo "   open dist/LyricToSubtitleApp.app"
    echo
    echo "📦 To create a DMG installer (optional):"
    echo "   hdiutil create -volname 'Lyric-to-Subtitle App' -srcfolder dist/LyricToSubtitleApp.app -ov -format UDZO LyricToSubtitleApp.dmg"
    echo
else
    echo
    echo "❌ Build failed! Check the error messages above."
    exit 1
fi