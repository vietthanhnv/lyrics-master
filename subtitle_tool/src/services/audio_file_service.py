"""
Audio file validation and metadata extraction service.

This module provides functionality to validate audio file formats and extract
metadata such as duration, sample rate, and channel information using librosa.
"""

import os
from pathlib import Path
from typing import List, Optional, Tuple
import librosa
import soundfile as sf
from src.models.data_models import AudioFile


class AudioFileService:
    """Service for audio file validation and metadata extraction."""
    
    # Supported audio formats
    SUPPORTED_FORMATS = {'.mp3', '.wav', '.flac', '.ogg', '.m4a', '.aac'}
    
    def __init__(self):
        """Initialize the audio file service."""
        pass
    
    def validate_file_format(self, file_path: str) -> bool:
        """
        Validate if the file format is supported.
        
        Args:
            file_path: Path to the audio file
            
        Returns:
            True if format is supported, False otherwise
        """
        if not file_path:
            return False
            
        file_extension = Path(file_path).suffix.lower()
        return file_extension in self.SUPPORTED_FORMATS
    
    def file_exists(self, file_path: str) -> bool:
        """
        Check if the file exists and is accessible.
        
        Args:
            file_path: Path to the audio file
            
        Returns:
            True if file exists and is accessible, False otherwise
        """
        try:
            return os.path.isfile(file_path) and os.access(file_path, os.R_OK)
        except (OSError, IOError):
            return False
    
    def extract_metadata(self, file_path: str) -> Optional[AudioFile]:
        """
        Extract metadata from an audio file.
        
        Args:
            file_path: Path to the audio file
            
        Returns:
            AudioFile object with metadata, or None if extraction fails
        """
        if not self.file_exists(file_path):
            return None
            
        if not self.validate_file_format(file_path):
            return None
        
        try:
            # Get file size
            file_size = os.path.getsize(file_path)
            
            # Extract audio metadata using librosa
            # Load only the first few seconds to get metadata quickly
            y, sr = librosa.load(file_path, sr=None, duration=0.1)
            
            # Get full duration using soundfile for better accuracy
            with sf.SoundFile(file_path) as f:
                duration = len(f) / f.samplerate
                channels = f.channels
                sample_rate = f.samplerate
            
            # Get file format
            file_format = Path(file_path).suffix.lower().lstrip('.')
            
            return AudioFile(
                path=file_path,
                format=file_format,
                duration=duration,
                sample_rate=sample_rate,
                channels=channels,
                file_size=file_size
            )
            
        except Exception as e:
            # Log the error in a real application
            print(f"Error extracting metadata from {file_path}: {e}")
            return None
    
    def validate_audio_file(self, file_path: str) -> Tuple[bool, List[str]]:
        """
        Comprehensive validation of an audio file.
        
        Args:
            file_path: Path to the audio file
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        # Check if file path is provided
        if not file_path:
            errors.append("File path cannot be empty")
            return False, errors
        
        # Check if file exists
        if not self.file_exists(file_path):
            errors.append(f"File does not exist or is not accessible: {file_path}")
            return False, errors
        
        # Check file format
        if not self.validate_file_format(file_path):
            supported = ', '.join(sorted(self.SUPPORTED_FORMATS))
            errors.append(f"Unsupported file format. Supported formats: {supported}")
            return False, errors
        
        # Try to extract metadata to ensure file is valid
        audio_file = self.extract_metadata(file_path)
        if audio_file is None:
            errors.append("Unable to read audio file - file may be corrupted")
            return False, errors
        
        # Validate extracted metadata
        validation_errors = audio_file.validate()
        if validation_errors:
            errors.extend(validation_errors)
            return False, errors
        
        # Additional validation checks
        if audio_file.duration < 0.1:
            errors.append("Audio file is too short (minimum 0.1 seconds)")
        
        if audio_file.duration > 7200:  # 2 hours
            errors.append("Audio file is too long (maximum 2 hours)")
        
        if audio_file.sample_rate < 8000:
            errors.append("Sample rate too low (minimum 8000 Hz)")
        
        if audio_file.channels > 8:
            errors.append("Too many channels (maximum 8)")
        
        return len(errors) == 0, errors
    
    def get_supported_formats(self) -> List[str]:
        """
        Get list of supported audio formats.
        
        Returns:
            List of supported file extensions (without dots)
        """
        return [fmt.lstrip('.') for fmt in sorted(self.SUPPORTED_FORMATS)]
    
    def is_format_supported(self, format_or_path: str) -> bool:
        """
        Check if a format or file path has a supported format.
        
        Args:
            format_or_path: Either a file extension (e.g., 'mp3') or file path
            
        Returns:
            True if format is supported, False otherwise
        """
        if '.' in format_or_path and len(format_or_path) > 4:
            # Assume it's a file path
            return self.validate_file_format(format_or_path)
        else:
            # Assume it's a format
            format_with_dot = f".{format_or_path.lstrip('.')}"
            return format_with_dot.lower() in self.SUPPORTED_FORMATS