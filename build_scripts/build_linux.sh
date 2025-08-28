#!/bin/bash
# Linux build script for Lyric-to-Subtitle App
# This script builds a standalone Linux executable using PyInstaller

set -e  # Exit on any error

echo "🐧 Building Lyric-to-Subtitle App for Linux..."
echo

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 is not installed or not in PATH"
    echo "Please install Python 3.9 or later:"
    echo "  Ubuntu/Debian: sudo apt update && sudo apt install python3 python3-pip python3-venv"
    echo "  Fedora/RHEL:   sudo dnf install python3 python3-pip"
    echo "  Arch Linux:    sudo pacman -S python python-pip"
    exit 1
fi

# Check Python version
python_version=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "🐍 Using Python $python_version"

# Check if we're in a virtual environment (recommended)
if [[ -z "$VIRTUAL_ENV" ]]; then
    echo "⚠️  Warning: Not running in a virtual environment"
    echo "It's recommended to use a virtual environment for building"
    echo "Create one with: python3 -m venv venv && source venv/bin/activate"
    echo
fi

# Check for required system dependencies
echo "🔍 Checking system dependencies..."

# Check for development tools
if ! command -v gcc &> /dev/null; then
    echo "⚠️  Warning: GCC not found. Some Python packages may fail to build."
    echo "Install with: sudo apt install build-essential (Ubuntu/Debian)"
fi

# Check for audio libraries
missing_libs=()
for lib in libasound2-dev libportaudio2 libsndfile1; do
    if ! dpkg -l | grep -q "$lib" 2>/dev/null && ! rpm -q "$lib" 2>/dev/null; then
        missing_libs+=("$lib")
    fi
done

if [ ${#missing_libs[@]} -gt 0 ]; then
    echo "⚠️  Warning: Some audio libraries may be missing: ${missing_libs[*]}"
    echo "Install with: sudo apt install ${missing_libs[*]} (Ubuntu/Debian)"
fi

# Install build dependencies if needed
echo "📦 Checking build dependencies..."
if ! python3 -c "import PyInstaller" &> /dev/null; then
    echo "Installing PyInstaller..."
    pip3 install pyinstaller
fi

# Run the build script
echo
echo "🔨 Starting build process..."
python3 build_scripts/build.py "$@"

if [ $? -eq 0 ]; then
    echo
    echo "✅ Build completed successfully!"
    echo
    echo "📁 The executable is available in the 'dist' folder:"
    echo "   dist/LyricToSubtitleApp/LyricToSubtitleApp"
    echo
    echo "🚀 To test the application:"
    echo "   cd dist/LyricToSubtitleApp"
    echo "   ./LyricToSubtitleApp"
    echo
    echo "📦 To create a portable archive:"
    echo "   cd dist"
    echo "   tar -czf LyricToSubtitleApp-linux.tar.gz LyricToSubtitleApp/"
    echo
    echo "🔧 To create a .desktop file for system integration:"
    echo "   See build_scripts/create_desktop_file.sh"
    echo
else
    echo
    echo "❌ Build failed! Check the error messages above."
    exit 1
fi