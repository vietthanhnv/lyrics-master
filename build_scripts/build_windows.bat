@echo off
REM Windows build script for Lyric-to-Subtitle App
REM This script builds a standalone Windows executable using PyInstaller

echo Building Lyric-to-Subtitle App for Windows...
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    echo Please install Python 3.9 or later and try again
    pause
    exit /b 1
)

REM Check if we're in a virtual environment (recommended)
if not defined VIRTUAL_ENV (
    echo Warning: Not running in a virtual environment
    echo It's recommended to use a virtual environment for building
    echo.
)

REM Install build dependencies if needed
echo Checking build dependencies...
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo Installing PyInstaller...
    pip install pyinstaller
    if errorlevel 1 (
        echo Error: Failed to install PyInstaller
        pause
        exit /b 1
    )
)

REM Run the build script
echo.
echo Starting build process...
python build_scripts\build.py %*

if errorlevel 1 (
    echo.
    echo Build failed! Check the error messages above.
    pause
    exit /b 1
)

echo.
echo Build completed successfully!
echo.
echo The executable is available in the 'dist' folder.
echo You can distribute the entire contents of the dist folder.
echo.
echo To test the executable:
echo   cd dist
echo   LyricToSubtitleApp.exe
echo.
pause