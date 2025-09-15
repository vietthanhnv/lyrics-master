#!/bin/bash

echo "🎤 Starting Karaoke Renderer Server..."
echo

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed or not in PATH"
    echo "Please install Node.js from https://nodejs.org/"
    exit 1
fi

# Check if we're in the server directory
if [ ! -f package.json ]; then
    echo "❌ package.json not found"
    echo "Please run this script from the server directory"
    exit 1
fi

# Install dependencies if node_modules doesn't exist
if [ ! -d node_modules ]; then
    echo "📦 Installing dependencies..."
    npm install
    if [ $? -ne 0 ]; then
        echo "❌ Failed to install dependencies"
        exit 1
    fi
fi

# Create required directories
mkdir -p uploads downloads temp data/jobs

echo "✅ Starting server..."
echo
echo "🌐 Server will be available at: http://localhost:3001"
echo "🔌 WebSocket server at: ws://localhost:3002"
echo "📊 Health check: http://localhost:3001/health"
echo
echo "Press Ctrl+C to stop the server"
echo

# Start the server
npm start