"""
Tests for the AudioProcessor service.

This module contains comprehensive tests for the audio processing pipeline,
including vocal separation, speech recognition coordination, and error handling.
"""

import pytest
import os
import tempfile
import shutil
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from src.services.audio_processor import AudioProcessor, AudioProcessingResult
from src.models.data_models import ModelSize, ProcessingOptions, AlignmentData, AudioFile, Segment, WordSegment
from src.services.interfaces import ProcessingError
from src.services.vocal_separator import VocalSeparationResult
from src.services.speech_recognizer import TranscriptionResult


class TestAudioProcessor:
    """Test cases for AudioProcessor class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.processor = AudioProcessor(temp_dir=self.temp_dir, device="cpu")
        
        # Create a mock audio file
        self.test_audio_path = os.path.join(self.temp_dir, "test_audio.wav")
        with open(self.test_audio_path, 'wb') as f:
            f.write(b"fake audio data")
        
        # Create mock processing options
        self.processing_options = ProcessingOptions(
            model_size=ModelSize.BASE,
            output_directory=self.temp_dir
        )
    
    def teardown_method(self):
        """Clean up test fixtures."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_init_default_settings(self):
        """Test AudioProcessor initialization with default settings."""
        processor = AudioProcessor()
        assert processor.temp_dir == tempfile.gettempdir()
        assert processor.device == "auto"
        assert processor.progress_callback is None
        assert not processor._is_processing
    
    def test_init_custom_settings(self):
        """Test AudioProcessor initialization with custom settings."""
        processor = AudioProcessor(temp_dir="/custom/temp", device="cuda")
        assert processor.temp_dir == "/custom/temp"
        assert processor.device == "cuda"  
  
    def test_set_progress_callback(self):
        """Test setting progress callback."""
        callback = Mock()
        self.processor.set_progress_callback(callback)
        assert self.processor.progress_callback == callback
    
    def test_get_supported_audio_formats(self):
        """Test getting supported audio formats."""
        with patch.object(self.processor.audio_file_service, 'get_supported_formats', 
                         return_value=['.mp3', '.wav', '.flac']):
            formats = self.processor.get_supported_audio_formats()
            assert formats == ['.mp3', '.wav', '.flac']
    
    def test_set_confidence_thresholds(self):
        """Test setting confidence thresholds."""
        with patch.object(self.processor.speech_recognizer, 'set_confidence_thresholds') as mock_set:
            self.processor.set_confidence_thresholds(0.7, 0.8)
            mock_set.assert_called_once_with(0.7, 0.8)
    
    def test_get_device_info_cpu(self):
        """Test getting device info for CPU."""
        info = self.processor.get_device_info()
        assert info["device"] == "cpu"
        assert info["temp_dir"] == self.temp_dir
    
    def test_get_device_info_cuda(self):
        """Test getting device info for CUDA."""
        processor = AudioProcessor(device="cuda")
        
        with patch('torch.cuda.is_available', return_value=True), \
             patch('torch.cuda.device_count', return_value=2), \
             patch('torch.cuda.current_device', return_value=0), \
             patch('torch.cuda.get_device_name', return_value="GeForce RTX 3080"):
            
            info = processor.get_device_info()
            assert info["device"] == "cuda"
            assert info["cuda_device_count"] == 2
            assert info["cuda_current_device"] == 0
            assert info["cuda_device_name"] == "GeForce RTX 3080"
    
    def test_get_processing_status(self):
        """Test getting processing status."""
        status = self.processor.get_processing_status()
        assert status["is_processing"] is False
        assert status["current_operation"] == ""
        assert status["temp_files_count"] == 0
    
    def test_validate_audio_file_success(self):
        """Test successful audio file validation."""
        mock_audio_file = AudioFile(
            path=self.test_audio_path,
            format="wav",
            duration=60.0,
            sample_rate=44100,
            channels=2
        )
        
        with patch.object(self.processor.audio_file_service, 'validate_audio_file', 
                         return_value=(True, [])), \
             patch.object(self.processor.audio_file_service, 'extract_metadata', 
                         return_value=mock_audio_file):
            result = self.processor.validate_audio_file(self.test_audio_path)
            assert result == mock_audio_file
    
    def test_validate_audio_file_error(self):
        """Test audio file validation error."""
        with patch.object(self.processor.audio_file_service, 'validate_audio_file', 
                         return_value=(False, ["Invalid file"])):
            with pytest.raises(ProcessingError, match="Audio file validation failed"):
                self.processor.validate_audio_file(self.test_audio_path)    

    def test_separate_vocals_success(self):
        """Test successful vocal separation."""
        vocals_path = os.path.join(self.temp_dir, "vocals.wav")
        mock_result = VocalSeparationResult(
            success=True,
            vocals_path=vocals_path,
            processing_time=10.0
        )
        
        with patch.object(self.processor.vocal_separator, 'separate_vocals', 
                         return_value=mock_result):
            result_path = self.processor.separate_vocals(self.test_audio_path, ModelSize.BASE)
            assert result_path == vocals_path
            assert vocals_path in self.processor._temp_files
    
    def test_separate_vocals_error(self):
        """Test vocal separation error."""
        mock_result = VocalSeparationResult(
            success=False,
            error_message="Separation failed"
        )
        
        with patch.object(self.processor.vocal_separator, 'separate_vocals', 
                         return_value=mock_result):
            with pytest.raises(ProcessingError, match="Separation failed"):
                self.processor.separate_vocals(self.test_audio_path, ModelSize.BASE)
    
    def test_transcribe_with_alignment_success(self):
        """Test successful transcription and alignment."""
        vocals_path = os.path.join(self.temp_dir, "vocals.wav")
        mock_alignment = AlignmentData(
            segments=[Segment(0.0, 2.0, "test", 0.9, 0)],
            word_segments=[WordSegment("test", 0.0, 2.0, 0.9, 0)],
            confidence_scores=[0.9],
            audio_duration=2.0
        )
        mock_result = TranscriptionResult(
            success=True,
            alignment_data=mock_alignment,
            processing_time=15.0
        )
        
        with patch.object(self.processor.speech_recognizer, 'transcribe_with_alignment', 
                         return_value=mock_result):
            result = self.processor.transcribe_with_alignment(vocals_path, ModelSize.BASE)
            assert result == mock_alignment
    
    def test_transcribe_with_alignment_error(self):
        """Test transcription and alignment error."""
        vocals_path = os.path.join(self.temp_dir, "vocals.wav")
        mock_result = TranscriptionResult(
            success=False,
            error_message="Transcription failed"
        )
        
        with patch.object(self.processor.speech_recognizer, 'transcribe_with_alignment', 
                         return_value=mock_result):
            with pytest.raises(ProcessingError, match="Transcription failed"):
                self.processor.transcribe_with_alignment(vocals_path, ModelSize.BASE)
    
    def test_estimate_processing_time(self):
        """Test processing time estimation."""
        duration = 60.0
        
        with patch.object(self.processor.vocal_separator, 'estimate_processing_time', 
                         return_value=12.0), \
             patch.object(self.processor.speech_recognizer, 'estimate_processing_time', 
                         return_value=9.0):
            
            total_time = self.processor.estimate_processing_time(duration, ModelSize.BASE)
            # Should be 12.0 + 9.0 + overhead (60 * 0.02 = 1.2) = 22.2
            assert total_time == 22.2 
   
    def test_process_audio_file_success(self):
        """Test successful complete audio processing."""
        # Mock audio file validation
        mock_audio_file = AudioFile(
            path=self.test_audio_path,
            format="wav",
            duration=60.0,
            sample_rate=44100,
            channels=2
        )
        
        # Mock vocal separation
        vocals_path = os.path.join(self.temp_dir, "vocals.wav")
        mock_vocal_result = VocalSeparationResult(
            success=True,
            vocals_path=vocals_path,
            processing_time=10.0
        )
        
        # Mock transcription
        mock_alignment = AlignmentData(
            segments=[Segment(0.0, 2.0, "test", 0.9, 0)],
            word_segments=[WordSegment("test", 0.0, 2.0, 0.9, 0)],
            confidence_scores=[0.9],
            audio_duration=2.0
        )
        mock_transcription_result = TranscriptionResult(
            success=True,
            alignment_data=mock_alignment,
            processing_time=15.0
        )
        
        with patch.object(self.processor.audio_file_service, 'validate_audio_file', 
                         return_value=(True, [])), \
             patch.object(self.processor.audio_file_service, 'extract_metadata', 
                         return_value=mock_audio_file), \
             patch.object(self.processor.vocal_separator, 'separate_vocals', 
                         return_value=mock_vocal_result), \
             patch.object(self.processor.speech_recognizer, 'transcribe_with_alignment', 
                         return_value=mock_transcription_result):
            
            # Mock progress callback
            callback = Mock()
            self.processor.set_progress_callback(callback)
            
            result = self.processor.process_audio_file(self.test_audio_path, self.processing_options)
            
            assert result.success
            assert result.alignment_data == mock_alignment
            assert result.vocals_path == vocals_path
            assert result.error_message is None
            assert result.processing_time >= 0
            
            # Verify progress callbacks were made
            assert callback.call_count > 0
    
    def test_process_audio_file_validation_error(self):
        """Test audio processing with validation error."""
        with patch.object(self.processor.audio_file_service, 'validate_audio_file', 
                         return_value=(False, ["Invalid file"])):
            
            result = self.processor.process_audio_file(self.test_audio_path, self.processing_options)
            
            assert not result.success
            assert "Audio file validation failed" in result.error_message
            assert result.alignment_data is None
    
    def test_process_audio_file_vocal_separation_error(self):
        """Test audio processing with vocal separation error."""
        mock_audio_file = AudioFile(
            path=self.test_audio_path,
            format="wav",
            duration=60.0,
            sample_rate=44100,
            channels=2
        )
        
        mock_vocal_result = VocalSeparationResult(
            success=False,
            error_message="Vocal separation failed"
        )
        
        with patch.object(self.processor.audio_file_service, 'validate_audio_file', 
                         return_value=(True, [])), \
             patch.object(self.processor.audio_file_service, 'extract_metadata', 
                         return_value=mock_audio_file), \
             patch.object(self.processor.vocal_separator, 'separate_vocals', 
                         return_value=mock_vocal_result):
            
            result = self.processor.process_audio_file(self.test_audio_path, self.processing_options)
            
            assert not result.success
            assert "Vocal separation failed" in result.error_message    

    def test_process_audio_file_transcription_error(self):
        """Test audio processing with transcription error."""
        mock_audio_file = AudioFile(
            path=self.test_audio_path,
            format="wav",
            duration=60.0,
            sample_rate=44100,
            channels=2
        )
        
        vocals_path = os.path.join(self.temp_dir, "vocals.wav")
        mock_vocal_result = VocalSeparationResult(
            success=True,
            vocals_path=vocals_path,
            processing_time=10.0
        )
        
        mock_transcription_result = TranscriptionResult(
            success=False,
            error_message="Transcription failed"
        )
        
        with patch.object(self.processor.audio_file_service, 'validate_audio_file', 
                         return_value=(True, [])), \
             patch.object(self.processor.audio_file_service, 'extract_metadata', 
                         return_value=mock_audio_file), \
             patch.object(self.processor.vocal_separator, 'separate_vocals', 
                         return_value=mock_vocal_result), \
             patch.object(self.processor.speech_recognizer, 'transcribe_with_alignment', 
                         return_value=mock_transcription_result):
            
            result = self.processor.process_audio_file(self.test_audio_path, self.processing_options)
            
            assert not result.success
            assert "Transcription failed" in result.error_message
    
    def test_cancel_processing_not_active(self):
        """Test cancelling when no processing is active."""
        result = self.processor.cancel_processing()
        assert result is True
    
    def test_cancel_processing_during_vocal_separation(self):
        """Test cancelling during vocal separation."""
        self.processor._is_processing = True
        self.processor._current_operation = "vocal_separation"
        
        with patch.object(self.processor.vocal_separator, 'cancel_processing', return_value=True):
            result = self.processor.cancel_processing()
            assert result is True
            assert not self.processor._is_processing
    
    def test_cleanup_temp_files(self):
        """Test cleanup of temporary files."""
        # Create some temporary files
        temp_file = os.path.join(self.temp_dir, "temp_file.txt")
        temp_subdir = os.path.join(self.temp_dir, "temp_subdir")
        
        with open(temp_file, 'w') as f:
            f.write("test")
        os.makedirs(temp_subdir)
        
        # Add them to the temp files list
        self.processor._temp_files = [temp_file, temp_subdir]
        
        with patch.object(self.processor.vocal_separator, 'cleanup_temp_files'), \
             patch.object(self.processor.speech_recognizer, 'cleanup_models'):
            
            self.processor.cleanup_temp_files()
            
            # Verify files are removed
            assert not os.path.exists(temp_file)
            assert not os.path.exists(temp_subdir)
            assert self.processor._temp_files == []
    
    def test_progress_callbacks(self):
        """Test progress callback aggregation."""
        callback = Mock()
        self.processor.set_progress_callback(callback)
        
        # Test vocal progress callback
        self.processor._vocal_progress_callback(50.0, "Separating vocals")
        callback.assert_called_with(27.5, "Vocal separation: Separating vocals")  # 5 + (50 * 0.45)
        
        # Test speech progress callback
        self.processor._speech_progress_callback(75.0, "Transcribing")
        callback.assert_called_with(83.75, "Speech recognition: Transcribing")  # 50 + (75 * 0.45)


class TestAudioProcessingResult:
    """Test cases for AudioProcessingResult class."""
    
    def test_success_result(self):
        """Test creating a successful result."""
        alignment_data = AlignmentData([], [], [], 0.0)
        result = AudioProcessingResult(
            success=True,
            alignment_data=alignment_data,
            processing_time=25.5,
            vocals_path="/path/to/vocals.wav"
        )
        
        assert result.success is True
        assert result.alignment_data == alignment_data
        assert result.error_message is None
        assert result.processing_time == 25.5
        assert result.vocals_path == "/path/to/vocals.wav"
    
    def test_error_result(self):
        """Test creating an error result."""
        result = AudioProcessingResult(
            success=False,
            error_message="Processing failed",
            processing_time=5.0
        )
        
        assert result.success is False
        assert result.alignment_data is None
        assert result.error_message == "Processing failed"
        assert result.processing_time == 5.0
        assert result.vocals_path is None
    
    def test_default_values(self):
        """Test default values in result."""
        result = AudioProcessingResult(success=True)
        
        assert result.success is True
        assert result.alignment_data is None
        assert result.error_message is None
        assert result.processing_time == 0.0
        assert result.vocals_path is None