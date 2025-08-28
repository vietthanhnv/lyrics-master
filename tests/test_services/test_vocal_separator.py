"""
Tests for the VocalSeparator service.

This module contains comprehensive tests for vocal separation functionality,
including success cases, error handling, and progress tracking.
"""

import pytest
import os
import tempfile
import shutil
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from src.services.vocal_separator import VocalSeparator, VocalSeparationResult
from src.models.data_models import ModelSize
from src.services.interfaces import ProcessingError


class TestVocalSeparator:
    """Test cases for VocalSeparator class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.separator = VocalSeparator(temp_dir=self.temp_dir)
        
        # Create a mock audio file
        self.test_audio_path = os.path.join(self.temp_dir, "test_audio.mp3")
        with open(self.test_audio_path, 'wb') as f:
            f.write(b"fake audio data")
    
    def teardown_method(self):
        """Clean up test fixtures."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_init_default_temp_dir(self):
        """Test VocalSeparator initialization with default temp directory."""
        separator = VocalSeparator()
        assert separator.temp_dir == tempfile.gettempdir()
        assert separator.progress_callback is None
        assert separator._temp_files == []
    
    def test_init_custom_temp_dir(self):
        """Test VocalSeparator initialization with custom temp directory."""
        custom_temp = "/custom/temp"
        with patch('os.makedirs') as mock_makedirs:
            separator = VocalSeparator(temp_dir=custom_temp)
            assert separator.temp_dir == custom_temp
            mock_makedirs.assert_called_once_with(custom_temp, exist_ok=True)
    
    def test_set_progress_callback(self):
        """Test setting progress callback."""
        callback = Mock()
        self.separator.set_progress_callback(callback)
        assert self.separator.progress_callback == callback
    
    def test_get_demucs_model_name(self):
        """Test model name mapping for different sizes."""
        assert self.separator._get_demucs_model_name(ModelSize.TINY) == "mdx_extra_q"
        assert self.separator._get_demucs_model_name(ModelSize.BASE) == "htdemucs"
        assert self.separator._get_demucs_model_name(ModelSize.SMALL) == "htdemucs"
        assert self.separator._get_demucs_model_name(ModelSize.MEDIUM) == "htdemucs_ft"
        assert self.separator._get_demucs_model_name(ModelSize.LARGE) == "mdx_extra"
    
    def test_create_temp_output_dir(self):
        """Test temporary output directory creation."""
        with patch('tempfile.mkdtemp') as mock_mkdtemp:
            mock_mkdtemp.return_value = "/fake/temp/dir"
            
            result = self.separator._create_temp_output_dir()
            
            assert result == "/fake/temp/dir"
            assert "/fake/temp/dir" in self.separator._temp_files
            mock_mkdtemp.assert_called_once_with(prefix="demucs_", dir=self.temp_dir)
    
    def test_update_progress_with_callback(self):
        """Test progress updates when callback is set."""
        callback = Mock()
        self.separator.set_progress_callback(callback)
        
        self.separator._update_progress(50.0, "Test message")
        
        callback.assert_called_once_with(50.0, "Test message")
    
    def test_update_progress_without_callback(self):
        """Test progress updates when no callback is set."""
        # Should not raise any exception
        self.separator._update_progress(50.0, "Test message")
    
    def test_get_supported_formats(self):
        """Test getting supported audio formats."""
        formats = self.separator.get_supported_formats()
        expected_formats = ['.mp3', '.wav', '.flac', '.ogg', '.m4a', '.mp4']
        assert formats == expected_formats
    
    def test_estimate_processing_time(self):
        """Test processing time estimation."""
        # Test with different model sizes
        duration = 60.0  # 1 minute
        
        tiny_time = self.separator.estimate_processing_time(duration, ModelSize.TINY)
        base_time = self.separator.estimate_processing_time(duration, ModelSize.BASE)
        large_time = self.separator.estimate_processing_time(duration, ModelSize.LARGE)
        
        assert tiny_time == 6.0  # 60 * 0.1
        assert base_time == 12.0  # 60 * 0.2
        assert large_time == 30.0  # 60 * 0.5
        
        # Tiny should be fastest, large should be slowest
        assert tiny_time < base_time < large_time
    
    def test_separate_vocals_file_not_found(self):
        """Test vocal separation with non-existent file."""
        result = self.separator.separate_vocals("/nonexistent/file.mp3")
        
        assert not result.success
        assert "Input audio file not found" in result.error_message
        assert result.vocals_path is None
    
    def test_separate_vocals_success(self):
        """Test successful vocal separation."""
        # Mock the availability check and separation method
        with patch.object(self.separator, '_check_demucs_availability'), \
             patch.object(self.separator, '_run_demucs_separation') as mock_run_demucs:
            
            mock_vocals_path = os.path.join(self.temp_dir, "vocals_test_audio.wav")
            mock_run_demucs.return_value = mock_vocals_path
            
            # Create the expected output file
            with open(mock_vocals_path, 'wb') as f:
                f.write(b"fake vocals data")
            
            # Mock progress callback
            callback = Mock()
            self.separator.set_progress_callback(callback)
            
            result = self.separator.separate_vocals(self.test_audio_path, ModelSize.BASE)
            
            assert result.success
            assert result.vocals_path == mock_vocals_path
            assert result.error_message is None
            assert result.processing_time > 0
            
            # Verify Demucs separation was called
            mock_run_demucs.assert_called_once()
            
            # Verify progress callbacks were made
            assert callback.call_count > 0
    
    def test_separate_vocals_demucs_import_error(self):
        """Test vocal separation when Demucs is not installed."""
        # Mock the availability check to raise ImportError
        with patch.object(self.separator, '_check_demucs_availability', side_effect=ProcessingError("Demucs is not installed. Please install it with: pip install demucs")):
            result = self.separator.separate_vocals(self.test_audio_path)
        
        assert not result.success
        assert "Demucs is not installed" in result.error_message
    
    def test_separate_vocals_insufficient_stems(self):
        """Test vocal separation when Demucs returns insufficient stems."""
        with patch.object(self.separator, '_check_demucs_availability'), \
             patch.object(self.separator, '_run_demucs_separation', side_effect=ProcessingError("Unexpected number of stems from Demucs separation")):
            
            result = self.separator.separate_vocals(self.test_audio_path)
            
            assert not result.success
            assert "Unexpected number of stems" in result.error_message
    
    def test_separate_vocals_processing_error(self):
        """Test vocal separation with processing error."""
        with patch.object(self.separator, '_check_demucs_availability'), \
             patch.object(self.separator, '_run_demucs_separation', side_effect=ProcessingError("Demucs separation failed: Processing failed")):
            
            result = self.separator.separate_vocals(self.test_audio_path)
            
            assert not result.success
            assert "Demucs separation failed" in result.error_message
    
    def test_cleanup_temp_files(self):
        """Test cleanup of temporary files."""
        # Create some temporary files and directories
        temp_file = os.path.join(self.temp_dir, "temp_file.txt")
        temp_subdir = os.path.join(self.temp_dir, "temp_subdir")
        
        with open(temp_file, 'w') as f:
            f.write("test")
        os.makedirs(temp_subdir)
        
        # Add them to the temp files list
        self.separator._temp_files = [temp_file, temp_subdir]
        
        # Cleanup
        self.separator.cleanup_temp_files()
        
        # Verify files are removed
        assert not os.path.exists(temp_file)
        assert not os.path.exists(temp_subdir)
        assert self.separator._temp_files == []
    
    def test_cleanup_temp_files_with_errors(self):
        """Test cleanup when some files cannot be removed."""
        # Add non-existent file to temp files list
        self.separator._temp_files = ["/nonexistent/file.txt"]
        
        # Should not raise exception
        self.separator.cleanup_temp_files()
        assert self.separator._temp_files == []
    
    def test_cancel_processing_no_process(self):
        """Test cancelling when no process is running."""
        result = self.separator.cancel_processing()
        assert result is True
    
    def test_cancel_processing_with_process(self):
        """Test cancelling with active process."""
        mock_process = Mock()
        self.separator._current_process = mock_process
        
        result = self.separator.cancel_processing()
        
        assert result is True
        mock_process.terminate.assert_called_once()
    
    def test_cancel_processing_termination_error(self):
        """Test cancelling when process termination fails."""
        mock_process = Mock()
        mock_process.terminate.side_effect = Exception("Termination failed")
        self.separator._current_process = mock_process
        
        result = self.separator.cancel_processing()
        
        assert result is False
    
    def test_separate_vocals_empty_file(self):
        """Test vocal separation with empty input file."""
        # Create an empty file
        empty_file = os.path.join(self.temp_dir, "empty.mp3")
        with open(empty_file, 'wb') as f:
            pass  # Create empty file
        
        result = self.separator.separate_vocals(empty_file)
        
        assert not result.success
        assert "Input audio file is empty" in result.error_message
    
    def test_check_system_resources_insufficient_memory(self):
        """Test system resource check with insufficient memory."""
        with patch('psutil.virtual_memory') as mock_memory:
            # Mock insufficient memory (1GB available, 4GB required for BASE model)
            mock_memory.return_value.available = 1 * 1024**3  # 1GB
            
            # The method should not raise an exception but log a warning
            # This is the correct behavior for production robustness
            with patch('src.services.vocal_separator.logger') as mock_logger:
                self.separator._check_system_resources(self.test_audio_path, ModelSize.BASE)
                
                # Verify warning was logged
                mock_logger.warning.assert_called()
                warning_call = mock_logger.warning.call_args[0][0]
                assert "Insufficient memory" in warning_call
    
    def test_check_system_resources_insufficient_disk(self):
        """Test system resource check with insufficient disk space."""
        with patch('psutil.virtual_memory') as mock_memory, \
             patch('psutil.disk_usage') as mock_disk:
            
            # Mock sufficient memory but insufficient disk space
            mock_memory.return_value.available = 8 * 1024**3  # 8GB
            mock_disk.return_value.free = 0.1 * 1024**3  # 0.1GB
            
            # The method should not raise an exception but log a warning
            with patch('src.services.vocal_separator.logger') as mock_logger:
                self.separator._check_system_resources(self.test_audio_path, ModelSize.BASE)
                
                # Verify warning was logged
                mock_logger.warning.assert_called()
                warning_call = mock_logger.warning.call_args[0][0]
                assert "Insufficient disk space" in warning_call
    
    def test_check_system_resources_success(self):
        """Test successful system resource check."""
        with patch('psutil.virtual_memory') as mock_memory, \
             patch('psutil.disk_usage') as mock_disk:
            
            # Mock sufficient resources
            mock_memory.return_value.available = 8 * 1024**3  # 8GB
            mock_disk.return_value.free = 10 * 1024**3  # 10GB
            
            # Should not raise any exception
            self.separator._check_system_resources(self.test_audio_path, ModelSize.BASE)
    
    def test_check_demucs_availability_missing_torch(self):
        """Test Demucs availability check when torch is missing."""
        with patch('builtins.__import__', side_effect=ImportError("No module named 'torch'")):
            with pytest.raises(ProcessingError) as exc_info:
                self.separator._check_demucs_availability()
            
            assert "torch" in str(exc_info.value)
            assert "pip install demucs torch torchaudio" in str(exc_info.value)


class TestVocalSeparationResult:
    """Test cases for VocalSeparationResult class."""
    
    def test_success_result(self):
        """Test creating a successful result."""
        result = VocalSeparationResult(
            success=True,
            vocals_path="/path/to/vocals.wav",
            processing_time=15.5
        )
        
        assert result.success is True
        assert result.vocals_path == "/path/to/vocals.wav"
        assert result.error_message is None
        assert result.processing_time == 15.5
    
    def test_error_result(self):
        """Test creating an error result."""
        result = VocalSeparationResult(
            success=False,
            error_message="Processing failed",
            processing_time=5.0
        )
        
        assert result.success is False
        assert result.vocals_path is None
        assert result.error_message == "Processing failed"
        assert result.processing_time == 5.0
    
    def test_default_values(self):
        """Test default values in result."""
        result = VocalSeparationResult(success=True)
        
        assert result.success is True
        assert result.vocals_path is None
        assert result.error_message is None
        assert result.processing_time == 0.0