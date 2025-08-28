"""
Interface definitions for core application services.

This module defines the abstract interfaces that all service implementations
must follow, ensuring consistent APIs across the application.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Callable, Any
from enum import Enum

from ..models.data_models import (
    ProcessingOptions, ProcessingResult, BatchResult, ProcessingStatus,
    AlignmentData, AudioFile, ModelSize, ExportFormat, TranslationService
)


class ModelType(Enum):
    """Types of AI models used in the application."""
    DEMUCS = "demucs"
    WHISPERX = "whisperx"


class ProcessingError(Exception):
    """Base exception for processing errors."""
    pass


class ModelError(Exception):
    """Exception for model-related errors."""
    pass


class ValidationError(Exception):
    """Exception for validation errors."""
    pass


class IApplicationController(ABC):
    """Interface for the main application controller."""
    
    @abstractmethod
    def process_audio_file(self, file_path: str, options: ProcessingOptions) -> ProcessingResult:
        """Process a single audio file and generate subtitles."""
        pass
    
    @abstractmethod
    def process_batch(self, file_paths: List[str], options: ProcessingOptions) -> BatchResult:
        """Process multiple audio files in batch."""
        pass
    
    @abstractmethod
    def get_processing_status(self) -> ProcessingStatus:
        """Get current processing status."""
        pass
    
    @abstractmethod
    def cancel_processing(self) -> bool:
        """Cancel current processing operation."""
        pass
    
    @abstractmethod
    def set_progress_callback(self, callback: Callable[[float, str], None]) -> None:
        """Set callback for progress updates."""
        pass


class IAudioProcessor(ABC):
    """Interface for audio processing operations."""
    
    @abstractmethod
    def separate_vocals(self, audio_path: str, model_size: ModelSize) -> str:
        """Separate vocals from audio and return path to vocals file."""
        pass
    
    @abstractmethod
    def transcribe_with_alignment(self, vocals_path: str, model_size: ModelSize) -> AlignmentData:
        """Transcribe vocals and generate word-level alignment."""
        pass
    
    @abstractmethod
    def validate_audio_file(self, file_path: str) -> AudioFile:
        """Validate and extract metadata from audio file."""
        pass
    
    @abstractmethod
    def set_progress_callback(self, callback: Callable[[float, str], None]) -> None:
        """Set callback for progress updates."""
        pass


class IModelManager(ABC):
    """Interface for AI model management."""
    
    @abstractmethod
    def check_model_availability(self, model_type: ModelType, model_size: ModelSize) -> bool:
        """Check if a specific model is available locally."""
        pass
    
    @abstractmethod
    def download_model(self, model_type: ModelType, model_size: ModelSize) -> bool:
        """Download a model if not available locally."""
        pass
    
    @abstractmethod
    def get_model_path(self, model_type: ModelType, model_size: ModelSize) -> str:
        """Get the local path to a model."""
        pass
    
    @abstractmethod
    def list_available_models(self) -> Dict[ModelType, List[ModelSize]]:
        """List all locally available models."""
        pass
    
    @abstractmethod
    def set_download_progress_callback(self, callback: Callable[[float, str], None]) -> None:
        """Set callback for download progress updates."""
        pass


class ISubtitleGenerator(ABC):
    """Interface for subtitle generation."""
    
    @abstractmethod
    def generate_srt(self, alignment_data: AlignmentData, word_level: bool = False) -> str:
        """Generate SRT format subtitles."""
        pass
    
    @abstractmethod
    def generate_ass_karaoke(self, alignment_data: AlignmentData, style_options: Dict[str, Any] = None) -> str:
        """Generate ASS format subtitles with karaoke styling."""
        pass
    
    @abstractmethod
    def generate_vtt(self, alignment_data: AlignmentData) -> str:
        """Generate VTT format subtitles."""
        pass
    
    @abstractmethod
    def export_json_alignment(self, alignment_data: AlignmentData) -> str:
        """Export alignment data as JSON."""
        pass
    
    @abstractmethod
    def save_subtitle_file(self, content: str, file_path: str, format_type: ExportFormat) -> bool:
        """Save subtitle content to file."""
        pass
    
    @abstractmethod
    def generate_bilingual_srt(self, alignment_data: AlignmentData, word_level: bool = False,
                             translated_words: List[str] = None, words_per_subtitle: Optional[int] = None) -> str:
        """Generate bilingual SRT format subtitles."""
        pass
    
    @abstractmethod
    def generate_bilingual_ass_karaoke(self, alignment_data: AlignmentData, 
                                     style_options: Dict[str, Any] = None,
                                     sentence_level: bool = False) -> str:
        """Generate bilingual ASS format subtitles with karaoke styling."""
        pass
    
    @abstractmethod
    def generate_bilingual_vtt(self, alignment_data: AlignmentData, word_level: bool = False,
                             translated_words: List[str] = None, words_per_subtitle: Optional[int] = None,
                             include_cues: bool = False, include_speaker_labels: bool = False) -> str:
        """Generate bilingual VTT format subtitles."""
        pass
    
    @abstractmethod
    def export_bilingual_json_alignment(self, alignment_data: AlignmentData, target_language: str,
                                      include_metadata: bool = True, include_statistics: bool = True) -> str:
        """Export bilingual alignment data as JSON."""
        pass


class ITranslationService(ABC):
    """Interface for translation services."""
    
    @abstractmethod
    def translate_text(self, text: str, target_language: str, service: TranslationService) -> str:
        """Translate text to target language."""
        pass
    
    @abstractmethod
    def is_service_available(self, service: TranslationService) -> bool:
        """Check if translation service is available."""
        pass
    
    @abstractmethod
    def generate_bilingual_subtitles(self, alignment_data: AlignmentData, target_language: str, service: TranslationService) -> AlignmentData:
        """Generate bilingual subtitle data."""
        pass
    
    @abstractmethod
    def set_api_key(self, service: TranslationService, api_key: str) -> None:
        """Set API key for translation service."""
        pass


class IFileManager(ABC):
    """Interface for file management operations."""
    
    @abstractmethod
    def validate_input_file(self, file_path: str) -> AudioFile:
        """Validate input audio file."""
        pass
    
    @abstractmethod
    def create_output_directory(self, base_path: str) -> str:
        """Create output directory and return path."""
        pass
    
    @abstractmethod
    def cleanup_temporary_files(self, file_paths: List[str]) -> None:
        """Clean up temporary files."""
        pass
    
    @abstractmethod
    def get_supported_formats(self) -> List[str]:
        """Get list of supported audio formats."""
        pass


class IErrorHandler(ABC):
    """Interface for error handling."""
    
    @abstractmethod
    def handle_processing_error(self, error: Exception, context: str) -> str:
        """Handle processing error and return user-friendly message."""
        pass
    
    @abstractmethod
    def log_error(self, error: Exception, context: str) -> None:
        """Log error with context information."""
        pass
    
    @abstractmethod
    def get_recovery_suggestions(self, error: Exception) -> List[str]:
        """Get suggested recovery actions for error."""
        pass
    
    @abstractmethod
    def should_retry(self, error: Exception) -> bool:
        """Determine if operation should be retried."""
        pass