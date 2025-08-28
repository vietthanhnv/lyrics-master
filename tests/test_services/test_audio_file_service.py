"""
Tests for audio file service.
"""

import pytest
import os
import tempfile
import numpy as np
import soundfile as sf
from unittest.mock import patch, MagicMock
from src.services.audio_file_service import AudioFileService
from src.models.data_models import AudioFile


class TestAudioFileService:
    """Test AudioFileService functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.service = AudioFileService()
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """Clean up test fixtures."""
        # Clean up temp files if they exist
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def create_test_audio_file(self, filename: str, duration: float = 1.0, 
                              sample_rate: int = 44100, channels: int = 1) -> str:
        """Create a test audio file."""
        file_path = os.path.join(self.temp_dir, filename)
        
        # Generate test audio data
        samples = int(duration * sample_rate)
        if channels == 1:
            data = np.sin(2 * np.pi * 440 * np.linspace(0, duration, samples))
        else:
            data = np.zeros((samples, channels))
            for ch in range(channels):
                data[:, ch] = np.sin(2 * np.pi * (440 + ch * 100) * np.linspace(0, duration, samples))
        
        # Write the audio file
        sf.write(file_path, data, sample_rate)
        return file_path
    
    def test_validate_file_format_supported(self):
        """Test validation of supported file formats."""
        assert self.service.validate_file_format("test.mp3") is True
        assert self.service.validate_file_format("test.wav") is True
        assert self.service.validate_file_format("test.flac") is True
        assert self.service.validate_file_format("test.ogg") is True
        assert self.service.validate_file_format("TEST.MP3") is True  # Case insensitive
    
    def test_validate_file_format_unsupported(self):
        """Test validation of unsupported file formats."""
        assert self.service.validate_file_format("test.txt") is False
        assert self.service.validate_file_format("test.mp4") is False
        assert self.service.validate_file_format("test.avi") is False
        assert self.service.validate_file_format("") is False
        assert self.service.validate_file_format("test") is False
    
    def test_file_exists(self):
        """Test file existence checking."""
        # Create a test file
        test_file = self.create_test_audio_file("test.wav")
        
        assert self.service.file_exists(test_file) is True
        assert self.service.file_exists("nonexistent.wav") is False
        assert self.service.file_exists("") is False
    
    def test_extract_metadata_valid_file(self):
        """Test metadata extraction from valid audio file."""
        test_file = self.create_test_audio_file("test.wav", duration=2.0, channels=2)
        
        audio_file = self.service.extract_metadata(test_file)
        
        assert audio_file is not None
        assert audio_file.path == test_file
        assert audio_file.format == "wav"
        assert abs(audio_file.duration - 2.0) < 0.1  # Allow small tolerance
        assert audio_file.sample_rate == 44100
        assert audio_file.channels == 2
        assert audio_file.file_size > 0
    
    def test_extract_metadata_nonexistent_file(self):
        """Test metadata extraction from nonexistent file."""
        audio_file = self.service.extract_metadata("nonexistent.wav")
        assert audio_file is None
    
    def test_extract_metadata_unsupported_format(self):
        """Test metadata extraction from unsupported format."""
        # Create a text file with audio extension
        text_file = os.path.join(self.temp_dir, "fake.txt")
        with open(text_file, 'w') as f:
            f.write("This is not an audio file")
        
        audio_file = self.service.extract_metadata(text_file)
        assert audio_file is None
    
    def test_validate_audio_file_valid(self):
        """Test comprehensive validation of valid audio file."""
        test_file = self.create_test_audio_file("test.wav", duration=1.5)
        
        is_valid, errors = self.service.validate_audio_file(test_file)
        
        assert is_valid is True
        assert len(errors) == 0
    
    def test_validate_audio_file_empty_path(self):
        """Test validation with empty file path."""
        is_valid, errors = self.service.validate_audio_file("")
        
        assert is_valid is False
        assert len(errors) > 0
        assert any("empty" in error.lower() for error in errors)
    
    def test_validate_audio_file_nonexistent(self):
        """Test validation of nonexistent file."""
        is_valid, errors = self.service.validate_audio_file("nonexistent.wav")
        
        assert is_valid is False
        assert len(errors) > 0
        assert any("does not exist" in error for error in errors)
    
    def test_validate_audio_file_unsupported_format(self):
        """Test validation of unsupported format."""
        # Create a text file
        text_file = os.path.join(self.temp_dir, "test.txt")
        with open(text_file, 'w') as f:
            f.write("Not an audio file")
        
        is_valid, errors = self.service.validate_audio_file(text_file)
        
        assert is_valid is False
        assert len(errors) > 0
        assert any("Unsupported file format" in error for error in errors)
    
    def test_validate_audio_file_too_short(self):
        """Test validation of very short audio file."""
        test_file = self.create_test_audio_file("short.wav", duration=0.05)
        
        is_valid, errors = self.service.validate_audio_file(test_file)
        
        assert is_valid is False
        assert any("too short" in error for error in errors)
    
    def test_validate_audio_file_too_long(self):
        """Test validation of very long audio file."""
        # Mock the metadata extraction to return a very long duration
        with patch.object(self.service, 'extract_metadata') as mock_extract:
            mock_audio = AudioFile(
                path="long.wav",
                format="wav", 
                duration=8000.0,  # Over 2 hours
                sample_rate=44100,
                channels=1,
                file_size=1000000
            )
            mock_extract.return_value = mock_audio
            
            with patch.object(self.service, 'file_exists', return_value=True):
                with patch.object(self.service, 'validate_file_format', return_value=True):
                    is_valid, errors = self.service.validate_audio_file("long.wav")
            
            assert is_valid is False
            assert any("too long" in error for error in errors)
    
    def test_get_supported_formats(self):
        """Test getting list of supported formats."""
        formats = self.service.get_supported_formats()
        
        assert isinstance(formats, list)
        assert len(formats) > 0
        assert "mp3" in formats
        assert "wav" in formats
        assert "flac" in formats
        assert "ogg" in formats
    
    def test_is_format_supported_extension(self):
        """Test format support checking with extensions."""
        assert self.service.is_format_supported("mp3") is True
        assert self.service.is_format_supported(".mp3") is True
        assert self.service.is_format_supported("wav") is True
        assert self.service.is_format_supported("txt") is False
    
    def test_is_format_supported_filepath(self):
        """Test format support checking with file paths."""
        assert self.service.is_format_supported("/path/to/file.mp3") is True
        assert self.service.is_format_supported("/path/to/file.wav") is True
        assert self.service.is_format_supported("/path/to/file.txt") is False
    
    @patch('librosa.load')
    @patch('soundfile.SoundFile')
    def test_extract_metadata_librosa_error(self, mock_sf, mock_librosa):
        """Test metadata extraction when librosa fails."""
        # Create a real file first
        test_file = self.create_test_audio_file("test.wav")
        
        # Mock librosa to raise an exception
        mock_librosa.side_effect = Exception("Librosa error")
        
        audio_file = self.service.extract_metadata(test_file)
        assert audio_file is None
    
    def test_validate_audio_file_corrupted(self):
        """Test validation of corrupted audio file."""
        # Create a file with audio extension but invalid content
        corrupted_file = os.path.join(self.temp_dir, "corrupted.wav")
        with open(corrupted_file, 'wb') as f:
            f.write(b"This is not valid audio data")
        
        is_valid, errors = self.service.validate_audio_file(corrupted_file)
        
        assert is_valid is False
        assert len(errors) > 0
        assert any("corrupted" in error.lower() for error in errors)