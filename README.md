# Lyric-to-Subtitle App

A desktop application that automatically generates word-level synchronized subtitles from music files using AI-powered vocal separation and speech recognition.

## Features

- **Automatic Vocal Separation**: Uses Demucs AI model to extract vocals from mixed audio tracks
- **Precise Speech Recognition**: Employs WhisperX for accurate transcription with word-level timing
- **Multiple Subtitle Formats**: Exports to SRT, ASS (with karaoke effects), VTT, and JSON formats
- **Translation Support**: Optional bilingual subtitles using DeepL or Google Translate
- **Batch Processing**: Process multiple audio files simultaneously
- **Offline Operation**: Works completely offline once AI models are downloaded
- **User-Friendly Interface**: Clean PyQt6-based desktop interface

## Supported Audio Formats

- MP3 (.mp3)
- WAV (.wav)
- FLAC (.flac)
- OGG (.ogg)

## System Requirements

- Python 3.9 or higher
- 4GB+ RAM (8GB+ recommended for larger models)
- 2GB+ free disk space for AI models
- Windows, macOS, or Linux

## Installation

### From Source

1. Clone the repository:

```bash
git clone https://github.com/lyric-to-subtitle-app/lyric-to-subtitle-app.git
cd lyric-to-subtitle-app
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Run the application:

```bash
python src/main.py
```

### Development Setup

1. Install development dependencies:

```bash
pip install -r requirements-dev.txt
```

2. Install pre-commit hooks:

```bash
pre-commit install
```

3. Run tests:

```bash
pytest
```

## Usage

1. **Launch the Application**: Run the executable or `python src/main.py`
2. **First Run Setup**: Download required AI models (guided setup)
3. **Select Audio File**: Choose your music file using the file dialog
4. **Configure Options**: Select model size, export formats, and output directory
5. **Process**: Click "Generate Subtitles" and wait for processing to complete
6. **Review Results**: Generated subtitle files will be saved to your chosen directory

## Configuration

The application stores configuration in:

- Windows: `%APPDATA%/LyricToSubtitleApp/config.yaml`
- macOS: `~/Library/Application Support/LyricToSubtitleApp/config.yaml`
- Linux: `~/.config/lyric-to-subtitle-app/config.yaml`

## AI Models

The application uses the following AI models:

- **Demucs**: For vocal separation (Facebook Research)
- **WhisperX**: For speech recognition and alignment (OpenAI Whisper + forced alignment)

Models are automatically downloaded on first use and stored locally for offline operation.

## Building Standalone Executable

To create a standalone executable:

```bash
pip install pyinstaller
pyinstaller --onefile --windowed src/main.py
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- [Demucs](https://github.com/facebookresearch/demucs) by Facebook Research
- [WhisperX](https://github.com/m-bain/whisperX) by Max Bain
- [OpenAI Whisper](https://github.com/openai/whisper) by OpenAI
