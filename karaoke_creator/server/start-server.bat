@echo off
echo 🎤 Starting Karaoke Renderer Server...
echo.

REM Check if Node.js is installed
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Node.js is not installed or not in PATH
    echo Please install Node.js from https://nodejs.org/
    pause
    exit /b 1
)

REM Check if we're in the server directory
if not exist package.json (
    echo ❌ package.json not found
    echo Please run this script from the server directory
    pause
    exit /b 1
)

REM Install dependencies if node_modules doesn't exist
if not exist node_modules (
    echo 📦 Installing dependencies...
    npm install
    if %errorlevel% neq 0 (
        echo ❌ Failed to install dependencies
        pause
        exit /b 1
    )
)

REM Create required directories
if not exist uploads mkdir uploads
if not exist downloads mkdir downloads
if not exist temp mkdir temp
if not exist data mkdir data
if not exist data\jobs mkdir data\jobs

echo ✅ Starting server...
echo.
echo 🌐 Server will be available at: http://localhost:3001
echo 🔌 WebSocket server at: ws://localhost:3002
echo 📊 Health check: http://localhost:3001/health
echo.
echo Press Ctrl+C to stop the server
echo.

REM Start the server
npm start