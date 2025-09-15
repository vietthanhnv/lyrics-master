"""
Integration tests for audio file processing with data models.
"""

import pytest
import os
import tempfile
import numpy as np
import soundfile as sf
from src.services.audio_file_service import AudioFileService
from src.models.data_models import AudioFile, ProcessingOptions, ExportFormat


class TestAudioIntegration:
    """Integration tests for audio file processing."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.service = AudioFileService()
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def create_test_audio_file(self, filename: str, duration: float = 2.0) -> str:
        """Create a test audio file."""
        file_path = os.path.join(self.temp_dir, filename)
        
        # Generate test audio data (sine wave)
        sample_rate = 44100
        samples = int(duration * sample_rate)
        data = np.sin(2 * np.pi * 440 * np.linspace(0, duration, samples))
        
        # Write the audio file
        sf.write(file_path, data, sample_rate)
        return file_path
    
    def test_audio_file_workflow(self):
        """Test complete audio file processing workflow."""
        # Create test audio file
        test_file = self.create_test_audio_file("test_song.wav", duration=3.0)
        
        # Step 1: Validate the file
        is_valid, errors = self.service.validate_audio_file(test_file)
        assert is_valid is True
        assert len(errors) == 0
        
        # Step 2: Extract metadata
        audio_file = self.service.extract_metadata(test_file)
        assert audio_file is not None
        assert isinstance(audio_file, AudioFile)
        
        # Step 3: Validate the AudioFile data model
        validation_errors = audio_file.validate()
        assert len(validation_errors) == 0
        
        # Step 4: Verify metadata is correct
        assert audio_file.format == "wav"
        assert abs(audio_file.duration - 3.0) < 0.1
        assert audio_file.sample_rate == 44100
        assert audio_file.channels == 1
        assert audio_file.file_size > 0
    
    def test_processing_options_with_audio_file(self):
        """Test ProcessingOptions validation with audio file context."""
        # Create test audio file
        test_file = self.create_test_audio_file("test.mp3", duration=1.5)
        
        # Create processing options
        options = ProcessingOptions(
            export_formats=[ExportFormat.SRT, ExportFormat.VTT],
            word_level_srt=True,
            karaoke_mode=False,
            output_directory=self.temp_dir
        )
        
        # Validate options
        errors = options.validate()
        assert len(errors) == 0
        
        # Validate audio file
        is_valid, audio_errors = self.service.validate_audio_file(test_file)
        assert is_valid is True
        
        # This demonstrates how the components work together
        audio_file = self.service.extract_metadata(test_file)
        assert audio_file is not None
        
        # In a real workflow, we would pass both audio_file and options
        # to the next processing stage
        assert audio_file.duration > 0
        assert len(options.export_formats) == 2
    
    def test_multiple_audio_formats(self):
        """Test processing multiple audio formats."""
        formats_to_test = ["wav", "flac"]  # Limited to formats we can easily create
        
        for fmt in formats_to_test:
            test_file = self.create_test_audio_file(f"test.{fmt}", duration=1.0)
            
            # Validate format support
            assert self.service.is_format_supported(fmt) is True
            
            # Validate file
            is_valid, errors = self.service.validate_audio_file(test_file)
            assert is_valid is True, f"Failed to validate {fmt} file: {errors}"
            
            # Extract metadata
            audio_file = self.service.extract_metadata(test_file)
            assert audio_file is not None, f"Failed to extract metadata from {fmt} file"
            assert audio_file.format == fmt
    
    def test_error_handling_integration(self):
        """Test error handling across components."""
        # Test with non-existent file
        is_valid, errors = self.service.validate_audio_file("nonexistent.wav")
        assert is_valid is False
        assert len(errors) > 0
        
        # Test with invalid processing options
        options = ProcessingOptions(
            export_formats=[],  # Empty formats
            output_directory=""  # Empty directory
        )
        
        validation_errors = options.validate()
        assert len(validation_errors) > 0
        assert any("export format" in error for error in validation_errors)
        assert any("Output directory" in error for error in validation_errors)