# Requirements Document

## Introduction

The Lyric-to-Subtitle App is a desktop application that automatically generates word-level synchronized subtitles from music files. The application combines AI-powered vocal separation using Demucs and speech-to-text alignment using WhisperX to produce high-quality subtitles suitable for karaoke videos, lyric videos, and accessibility purposes. The app operates entirely offline once models are downloaded, supporting multiple audio formats and subtitle export options.

## Requirements

### Requirement 1: Audio File Processing

**User Story:** As a content creator, I want to load various audio file formats into the application, so that I can generate subtitles from any music file in my collection.

#### Acceptance Criteria

1. WHEN a user selects an audio file THEN the system SHALL accept .mp3, .wav, .flac, and .ogg formats
2. WHEN an unsupported file format is selected THEN the system SHALL display an error message indicating supported formats
3. WHEN a valid audio file is loaded THEN the system SHALL display the file name and duration in the interface
4. IF a pre-existing lyric file (.txt or .lrc) is available THEN the system SHALL allow optional import for reference

### Requirement 2: Vocal Extraction

**User Story:** As a user processing music with mixed audio tracks, I want the application to automatically separate vocals from instrumental tracks, so that speech recognition can focus on the vocal content.

#### Acceptance Criteria

1. WHEN audio processing begins THEN the system SHALL use Demucs model to extract vocals from the input audio
2. WHEN vocal extraction is complete THEN the system SHALL generate a vocals.wav file for further processing
3. WHEN vocal extraction is running THEN the system SHALL display progress indicators to the user
4. IF vocal extraction fails THEN the system SHALL provide error details and allow retry options

### Requirement 3: Speech Recognition and Word Alignment

**User Story:** As a user creating karaoke content, I want precise word-level timestamps for each lyric, so that I can create synchronized highlighting effects.

#### Acceptance Criteria

1. WHEN vocals.wav is processed THEN the system SHALL use WhisperX for transcription with forced alignment
2. WHEN transcription is complete THEN the system SHALL provide word-level timestamps for each recognized word
3. WHEN processing speech recognition THEN the system SHALL allow model selection (tiny/base/small/medium/large)
4. IF transcription confidence is low THEN the system SHALL flag uncertain segments for user review

### Requirement 4: Subtitle Format Generation

**User Story:** As a video editor, I want to export subtitles in multiple standard formats, so that I can use them with different video editing software and media players.

#### Acceptance Criteria

1. WHEN subtitle generation is requested THEN the system SHALL support .srt, .ass, and .vtt export formats
2. WHEN generating .srt files THEN the system SHALL create both sentence-level and word-level subtitle options
3. WHEN generating .ass files THEN the system SHALL include karaoke-style formatting with word-by-word highlighting capabilities
4. WHEN exporting subtitles THEN the system SHALL allow users to choose the destination folder

### Requirement 5: Translation Support

**User Story:** As a content creator serving international audiences, I want to generate bilingual subtitles, so that I can provide content in multiple languages.

#### Acceptance Criteria

1. WHEN internet connection is available THEN the system SHALL offer integration with translation APIs (DeepL/Google Translate)
2. WHEN translation is enabled THEN the system SHALL generate bilingual subtitle files
3. WHEN translation fails THEN the system SHALL continue with original language subtitles and notify the user
4. IF no internet connection is detected THEN the system SHALL disable translation features gracefully

### Requirement 6: Batch Processing

**User Story:** As a user with multiple audio files, I want to process several songs simultaneously, so that I can efficiently generate subtitles for entire albums or playlists.

#### Acceptance Criteria

1. WHEN multiple files are selected THEN the system SHALL queue them for sequential processing
2. WHEN batch processing is active THEN the system SHALL display overall progress and current file status
3. WHEN a file in the batch fails THEN the system SHALL continue processing remaining files and report errors
4. WHEN batch processing completes THEN the system SHALL provide a summary report of successful and failed conversions

### Requirement 7: Offline Operation

**User Story:** As a user in environments with limited internet access, I want the application to work completely offline, so that I can generate subtitles without depending on internet connectivity.

#### Acceptance Criteria

1. WHEN the application starts THEN the system SHALL check for required models (Demucs, WhisperX) locally
2. WHEN models are missing THEN the system SHALL provide download options and progress tracking
3. WHEN all models are available locally THEN the system SHALL operate without internet connection
4. IF model downloads fail THEN the system SHALL provide clear error messages and retry options

### Requirement 8: User Interface and Experience

**User Story:** As a non-technical user, I want an intuitive desktop interface, so that I can easily navigate the subtitle generation process.

#### Acceptance Criteria

1. WHEN the application launches THEN the system SHALL display a clean PyQt6-based interface with clear navigation
2. WHEN processing is active THEN the system SHALL show real-time progress indicators and estimated completion times
3. WHEN errors occur THEN the system SHALL display user-friendly error messages with suggested solutions
4. WHEN processing completes THEN the system SHALL provide clear success notifications and file location information

### Requirement 9: Advanced Output Options

**User Story:** As an advanced user, I want access to detailed alignment data, so that I can perform custom processing or integration with other tools.

#### Acceptance Criteria

1. WHEN subtitle generation completes THEN the system SHALL optionally export JSON files with detailed alignment data
2. WHEN karaoke mode is selected THEN the system SHALL generate .ass files with gradual word highlighting effects
3. WHEN exporting advanced formats THEN the system SHALL allow customization of timing offsets and styling options
4. IF custom styling is applied THEN the system SHALL preview the effects before final export

### Requirement 10: Application Distribution

**User Story:** As an end user, I want to install and run the application easily on my desktop, so that I don't need to manage Python environments or dependencies.

#### Acceptance Criteria

1. WHEN the application is built THEN the system SHALL use PyInstaller to create standalone executables
2. WHEN the executable is distributed THEN the system SHALL include all necessary dependencies except AI models
3. WHEN first launched THEN the system SHALL guide users through initial model download and setup
4. IF system requirements are not met THEN the system SHALL provide clear guidance on necessary hardware/software requirements
