"""
Tests for the SpeechRecognizer service.

This module contains comprehensive tests for speech recognition and alignment functionality,
including success cases, error handling, and confidence scoring.
"""

import pytest
import os
import tempfile
import shutil
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from src.services.speech_recognizer import SpeechRecognizer, TranscriptionResult
from src.models.data_models import ModelSize, AlignmentData, Segment, WordSegment
from src.services.interfaces import ProcessingError


class TestSpeechRecognizer:
    """Test cases for SpeechRecognizer class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.recognizer = SpeechRecognizer(device="cpu", compute_type="float32")
        
        # Create a mock audio file
        self.test_audio_path = os.path.join(self.temp_dir, "test_audio.wav")
        with open(self.test_audio_path, 'wb') as f:
            f.write(b"fake audio data")
    
    def teardown_method(self):
        """Clean up test fixtures."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_init_default_device(self):
        """Test SpeechRecognizer initialization with default device."""
        recognizer = SpeechRecognizer()
        # Device should be determined automatically
        assert recognizer.device in ["cpu", "cuda"]
        assert recognizer.compute_type == "float16"
        assert recognizer.progress_callback is None
    
    def test_init_custom_settings(self):
        """Test SpeechRecognizer initialization with custom settings."""
        recognizer = SpeechRecognizer(device="cpu", compute_type="float32")
        assert recognizer.device == "cpu"
        assert recognizer.compute_type == "float32"
    
    def test_determine_device_auto_with_cuda(self):
        """Test device determination when CUDA is available."""
        with patch('torch.cuda.is_available', return_value=True):
            device = self.recognizer._determine_device("auto")
            assert device == "cuda"
    
    def test_determine_device_auto_without_cuda(self):
        """Test device determination when CUDA is not available."""
        with patch('torch.cuda.is_available', return_value=False):
            device = self.recognizer._determine_device("auto")
            assert device == "cpu"
    
    def test_determine_device_no_torch(self):
        """Test device determination when torch is not available."""
        with patch('builtins.__import__', side_effect=ImportError):
            device = self.recognizer._determine_device("auto")
            assert device == "cpu"
    
    def test_determine_device_explicit(self):
        """Test explicit device specification."""
        assert self.recognizer._determine_device("cpu") == "cpu"
        assert self.recognizer._determine_device("cuda") == "cuda"
    
    def test_set_progress_callback(self):
        """Test setting progress callback."""
        callback = Mock()
        self.recognizer.set_progress_callback(callback)
        assert self.recognizer.progress_callback == callback
    
    def test_set_confidence_thresholds(self):
        """Test setting confidence thresholds."""
        self.recognizer.set_confidence_thresholds(0.7, 0.8)
        assert self.recognizer.low_confidence_threshold == 0.7
        assert self.recognizer.word_confidence_threshold == 0.8
        
        # Test boundary values
        self.recognizer.set_confidence_thresholds(-0.1, 1.5)
        assert self.recognizer.low_confidence_threshold == 0.0
        assert self.recognizer.word_confidence_threshold == 1.0
    
    def test_get_whisper_model_name(self):
        """Test Whisper model name mapping."""
        assert self.recognizer._get_whisper_model_name(ModelSize.TINY) == "tiny"
        assert self.recognizer._get_whisper_model_name(ModelSize.BASE) == "base"
        assert self.recognizer._get_whisper_model_name(ModelSize.SMALL) == "small"
        assert self.recognizer._get_whisper_model_name(ModelSize.MEDIUM) == "medium"
        assert self.recognizer._get_whisper_model_name(ModelSize.LARGE) == "large-v2"
    
    def test_update_progress_with_callback(self):
        """Test progress updates when callback is set."""
        callback = Mock()
        self.recognizer.set_progress_callback(callback)
        
        self.recognizer._update_progress(50.0, "Test message")
        
        callback.assert_called_once_with(50.0, "Test message")
    
    def test_update_progress_without_callback(self):
        """Test progress updates when no callback is set."""
        # Should not raise any exception
        self.recognizer._update_progress(50.0, "Test message")
    
    def test_get_supported_languages(self):
        """Test getting supported languages."""
        languages = self.recognizer.get_supported_languages()
        assert isinstance(languages, list)
        assert len(languages) > 0
        assert "en" in languages
        assert "es" in languages
        assert "fr" in languages
    
    def test_estimate_processing_time(self):
        """Test processing time estimation."""
        duration = 60.0  # 1 minute
        
        tiny_time = self.recognizer.estimate_processing_time(duration, ModelSize.TINY)
        base_time = self.recognizer.estimate_processing_time(duration, ModelSize.BASE)
        large_time = self.recognizer.estimate_processing_time(duration, ModelSize.LARGE)
        
        # Tiny should be fastest, large should be slowest
        assert tiny_time < base_time < large_time
        
        # All should be positive
        assert tiny_time > 0
        assert base_time > 0
        assert large_time > 0
    
    def test_transcribe_file_not_found(self):
        """Test transcription with non-existent file."""
        result = self.recognizer.transcribe_with_alignment("/nonexistent/file.wav")
        
        assert not result.success
        assert "Input audio file not found" in result.error_message
        assert result.alignment_data is None
    
    def test_transcribe_whisperx_not_available(self):
        """Test transcription when WhisperX is not installed."""
        with patch.object(self.recognizer, '_check_whisperx_availability', 
                         side_effect=ProcessingError("WhisperX is not installed")):
            result = self.recognizer.transcribe_with_alignment(self.test_audio_path)
        
        assert not result.success
        assert "WhisperX is not installed" in result.error_message
    
    def test_transcribe_success(self):
        """Test successful transcription and alignment."""
        # Mock WhisperX components
        mock_whisper_result = {
            "language": "en",
            "segments": [
                {
                    "start": 0.0,
                    "end": 2.5,
                    "text": " Hello world",
                    "avg_logprob": -0.2
                }
            ]
        }
        
        mock_aligned_result = {
            "segments": [
                {
                    "start": 0.0,
                    "end": 2.5,
                    "text": " Hello world",
                    "avg_logprob": -0.2,
                    "words": [
                        {"word": " Hello", "start": 0.0, "end": 1.0, "score": 0.9},
                        {"word": " world", "start": 1.0, "end": 2.5, "score": 0.8}
                    ]
                }
            ]
        }
        
        with patch.object(self.recognizer, '_check_whisperx_availability'), \
             patch.object(self.recognizer, '_load_whisper_model') as mock_load_whisper, \
             patch.object(self.recognizer, '_transcribe_audio', return_value=mock_whisper_result), \
             patch.object(self.recognizer, '_load_alignment_model', return_value=(Mock(), Mock())) as mock_load_align, \
             patch.object(self.recognizer, '_perform_alignment', return_value=mock_aligned_result):
            
            # Mock progress callback
            callback = Mock()
            self.recognizer.set_progress_callback(callback)
            
            result = self.recognizer.transcribe_with_alignment(
                self.test_audio_path, ModelSize.BASE
            )
            
            assert result.success
            assert result.alignment_data is not None
            assert result.error_message is None
            assert result.processing_time > 0
            
            # Check alignment data structure
            alignment_data = result.alignment_data
            assert len(alignment_data.segments) == 1
            assert len(alignment_data.word_segments) == 2
            assert alignment_data.audio_duration == 2.5
            assert alignment_data.source_file == self.test_audio_path
            
            # Check segment data
            segment = alignment_data.segments[0]
            assert segment.text == "Hello world"
            assert segment.start_time == 0.0
            assert segment.end_time == 2.5
            
            # Check word segments
            words = alignment_data.word_segments
            assert words[0].word == "Hello"
            assert words[1].word == "world"
            
            # Verify progress callbacks were made
            assert callback.call_count > 0
    
    def test_transcribe_with_language_specified(self):
        """Test transcription with specific language."""
        mock_whisper_result = {"language": "es", "segments": []}
        mock_aligned_result = {"segments": []}
        
        with patch.object(self.recognizer, '_check_whisperx_availability'), \
             patch.object(self.recognizer, '_load_whisper_model'), \
             patch.object(self.recognizer, '_transcribe_audio', return_value=mock_whisper_result), \
             patch.object(self.recognizer, '_load_alignment_model', return_value=(Mock(), Mock())) as mock_load_align, \
             patch.object(self.recognizer, '_perform_alignment', return_value=mock_aligned_result):
            
            result = self.recognizer.transcribe_with_alignment(
                self.test_audio_path, ModelSize.BASE, language="es"
            )
            
            # Verify alignment model was loaded with specified language
            mock_load_align.assert_called_once_with("es")
    
    def test_transcribe_model_loading_error(self):
        """Test transcription with model loading error."""
        with patch.object(self.recognizer, '_check_whisperx_availability'), \
             patch.object(self.recognizer, '_load_whisper_model', 
                         side_effect=ProcessingError("Failed to load model")):
            
            result = self.recognizer.transcribe_with_alignment(self.test_audio_path)
            
            assert not result.success
            assert "Failed to load model" in result.error_message
    
    def test_transcribe_transcription_error(self):
        """Test transcription with transcription error."""
        with patch.object(self.recognizer, '_check_whisperx_availability'), \
             patch.object(self.recognizer, '_load_whisper_model'), \
             patch.object(self.recognizer, '_transcribe_audio', 
                         side_effect=ProcessingError("Transcription failed")):
            
            result = self.recognizer.transcribe_with_alignment(self.test_audio_path)
            
            assert not result.success
            assert "Transcription failed" in result.error_message
    
    def test_transcribe_alignment_error(self):
        """Test transcription with alignment error."""
        mock_whisper_result = {"language": "en", "segments": []}
        
        with patch.object(self.recognizer, '_check_whisperx_availability'), \
             patch.object(self.recognizer, '_load_whisper_model'), \
             patch.object(self.recognizer, '_transcribe_audio', return_value=mock_whisper_result), \
             patch.object(self.recognizer, '_load_alignment_model', return_value=(Mock(), Mock())), \
             patch.object(self.recognizer, '_perform_alignment', 
                         side_effect=ProcessingError("Alignment failed")):
            
            result = self.recognizer.transcribe_with_alignment(self.test_audio_path)
            
            assert not result.success
            assert "Alignment failed" in result.error_message
    
    def test_convert_to_alignment_data_empty(self):
        """Test conversion with empty results."""
        empty_result = {"segments": []}
        
        alignment_data = self.recognizer._convert_to_alignment_data(
            empty_result, self.test_audio_path
        )
        
        assert len(alignment_data.segments) == 0
        assert len(alignment_data.word_segments) == 0
        assert alignment_data.audio_duration == 0.0
        assert alignment_data.source_file == self.test_audio_path
    
    def test_convert_to_alignment_data_with_data(self):
        """Test conversion with actual data."""
        whisperx_result = {
            "segments": [
                {
                    "start": 0.0,
                    "end": 3.0,
                    "text": " Test segment",
                    "avg_logprob": -0.1,
                    "words": [
                        {"word": " Test", "start": 0.0, "end": 1.5, "score": 0.95},
                        {"word": " segment", "start": 1.5, "end": 3.0, "score": 0.88}
                    ]
                }
            ]
        }
        
        alignment_data = self.recognizer._convert_to_alignment_data(
            whisperx_result, self.test_audio_path
        )
        
        assert len(alignment_data.segments) == 1
        assert len(alignment_data.word_segments) == 2
        assert alignment_data.audio_duration == 3.0
        
        # Check segment
        segment = alignment_data.segments[0]
        assert segment.text == "Test segment"
        assert segment.start_time == 0.0
        assert segment.end_time == 3.0
        assert segment.confidence == -0.1
        
        # Check words
        words = alignment_data.word_segments
        assert words[0].word == "Test"
        assert words[0].confidence == 0.95
        assert words[1].word == "segment"
        assert words[1].confidence == 0.88
    
    def test_flag_uncertain_segments(self):
        """Test flagging of low-confidence segments and words."""
        # Create alignment data with mixed confidence scores
        segments = [
            Segment(0.0, 2.0, "High confidence", 0.9, 0),
            Segment(2.0, 4.0, "Low confidence", 0.3, 1)  # Below threshold
        ]
        
        word_segments = [
            WordSegment("High", 0.0, 1.0, 0.95, 0),
            WordSegment("confidence", 1.0, 2.0, 0.85, 0),
            WordSegment("Low", 2.0, 3.0, 0.4, 1),  # Below threshold
            WordSegment("confidence", 3.0, 4.0, 0.2, 1)  # Below threshold
        ]
        
        alignment_data = AlignmentData(
            segments=segments,
            word_segments=word_segments,
            confidence_scores=[0.9, 0.3],
            audio_duration=4.0
        )
        
        # This should log warnings but not raise exceptions
        self.recognizer._flag_uncertain_segments(alignment_data)
    
    def test_cleanup_models(self):
        """Test model cleanup."""
        # Set some mock models
        self.recognizer._whisper_model = Mock()
        self.recognizer._align_model = Mock()
        self.recognizer._align_metadata = Mock()
        
        self.recognizer.cleanup_models()
        
        assert self.recognizer._whisper_model is None
        assert self.recognizer._align_model is None
        assert self.recognizer._align_metadata is None
    
    def test_cleanup_models_with_cuda(self):
        """Test model cleanup with CUDA device."""
        recognizer = SpeechRecognizer(device="cuda")
        
        with patch('torch.cuda.empty_cache') as mock_empty_cache:
            recognizer.cleanup_models()
            mock_empty_cache.assert_called_once()


class TestTranscriptionResult:
    """Test cases for TranscriptionResult class."""
    
    def test_success_result(self):
        """Test creating a successful result."""
        alignment_data = AlignmentData([], [], [], 0.0)
        result = TranscriptionResult(
            success=True,
            alignment_data=alignment_data,
            processing_time=10.5
        )
        
        assert result.success is True
        assert result.alignment_data == alignment_data
        assert result.error_message is None
        assert result.processing_time == 10.5
    
    def test_error_result(self):
        """Test creating an error result."""
        result = TranscriptionResult(
            success=False,
            error_message="Recognition failed",
            processing_time=2.0
        )
        
        assert result.success is False
        assert result.alignment_data is None
        assert result.error_message == "Recognition failed"
        assert result.processing_time == 2.0
    
    def test_default_values(self):
        """Test default values in result."""
        result = TranscriptionResult(success=True)
        
        assert result.success is True
        assert result.alignment_data is None
        assert result.error_message is None
        assert result.processing_time == 0.0