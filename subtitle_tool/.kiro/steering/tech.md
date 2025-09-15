# Technology Stack

## Current Tech Stack

### Core Framework

- **Python 3.12+** - Main programming language
- **PyQt6** - GUI framework for desktop application
- **PyTorch** - Deep learning framework for AI models

### AI/ML Components

- **audio-separator** - Vocal separation using MDX-Net, VR Arch, Demucs models
- **whisper-cpp-python** - Speech recognition and transcription
- **WhisperX** - Word-level alignment and speaker diarization

### Build System

- **setuptools** - Python package building
- **PyInstaller** - Executable creation for distribution
- **pytest** - Testing framework

### Dependencies Management

- **pip** - Package management
- **requirements.txt** - Production dependencies
- **requirements-dev.txt** - Development dependencies
- **requirements-build.txt** - Build dependencies

## Common Commands

### Development

```bash
# Install dependencies
pip install -r requirements-dev.txt

# Run the application
python run_app.py

# Run in development mode with debug logging
python -m src.main --debug
```

### Testing

```bash
# Run all tests
pytest

# Run specific test suite
pytest tests/test_ui/

# Run tests with coverage
pytest --cov=src --cov-report=html
```

### Building

```bash
# Build executable
python -m PyInstaller lyric_to_subtitle_app.spec

# Build for distribution
python setup.py sdist bdist_wheel
```

### Deployment

```bash
# Create distribution package
python build_scripts/build_executable.py

# Package for Windows
python build_scripts/package_windows.py
```

## Architecture

### Core Components

1. **UI Layer** (`src/ui/`) - PyQt6 interface components
2. **Services Layer** (`src/services/`) - Business logic and AI integration
3. **Models Layer** (`src/models/`) - Data models and structures
4. **Utils Layer** (`src/utils/`) - Configuration and utilities

### Key Services

- **ApplicationController** - Main orchestration and workflow management
- **AudioProcessor** - Audio file processing and vocal separation
- **SpeechRecognizer** - Whisper-based transcription and alignment
- **SubtitleGenerator** - Subtitle file generation (SRT, ASS, VTT, JSON)
- **TranslationService** - Multi-language subtitle translation
- **ModelManager** - AI model downloading and management

## AI Technology Integration

### 1. Vocal Separation

- **Library**: [python-audio-separator](https://github.com/nomadkaraoke/python-audio-separator)
- **Models**: MDX-Net, VR Arch, Demucs, MDXC
- **Purpose**: Separate vocals from instrumental tracks
- **Usage**: Improves speech recognition accuracy

### 2. Speech Recognition

- **Library**: [whisper-cpp-python](https://github.com/carloscdias/whisper-cpp-python)
- **Models**: Whisper (tiny, base, small, medium, large)
- **Purpose**: Transcribe separated vocal audio to text
- **Features**: Word-level timestamps, multiple languages

### 3. Word-Level Alignment

- **Library**: WhisperX
- **Purpose**: Precise word-level timing alignment
- **Features**: Speaker diarization, improved accuracy

## Configuration

### Model Storage

- Models downloaded to: `~/.cache/lyric-to-subtitle-app/models/`
- Temporary files: System temp directory or custom path
- Output files: User-specified directory

### Supported Formats

- **Input Audio**: MP3, WAV, FLAC, OGG, M4A, AAC
- **Input Lyrics**: TXT, LRC (optional reference)
- **Output Subtitles**: SRT, ASS, VTT, JSON

## Performance Considerations

### Hardware Requirements

- **CPU**: Multi-core recommended for faster processing
- **RAM**: 8GB minimum, 16GB recommended for large models
- **GPU**: CUDA-compatible GPU optional but recommended
- **Storage**: 2GB+ for model storage

### Optimization Features

- Batch processing for multiple files
- Model caching to avoid re-downloading
- Progress tracking and cancellation support
- Memory-efficient processing for large audio files

## Test Data

- **Sample Audio**: `data/hello.mp3`
- **Test Cases**: Comprehensive test suite in `tests/`
- **Integration Tests**: End-to-end workflow validation
