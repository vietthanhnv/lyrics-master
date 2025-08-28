"""
Tests for core data models.
"""

import pytest
from src.models.data_models import (
    ProcessingOptions, Segment, WordSegment, AlignmentData,
    AudioFile, SubtitleFile, ProcessingResult, BatchResult, ProcessingStatus,
    ModelSize, ExportFormat, TranslationService
)


class TestProcessingOptions:
    """Test ProcessingOptions data model."""
    
    def test_default_initialization(self):
        """Test default initialization of ProcessingOptions."""
        options = ProcessingOptions()
        assert options.model_size == ModelSize.BASE
        assert options.export_formats == [ExportFormat.SRT]
        assert options.word_level_srt is True
        assert options.karaoke_mode is False
        assert options.translation_enabled is False
    
    def test_validation_success(self):
        """Test successful validation."""
        options = ProcessingOptions(
            output_directory="/test/path",
            export_formats=[ExportFormat.SRT, ExportFormat.VTT]
        )
        errors = options.validate()
        assert len(errors) == 0
    
    def test_validation_errors(self):
        """Test validation with errors."""
        options = ProcessingOptions(
            translation_enabled=True,
            export_formats=[],
            output_directory=""
        )
        errors = options.validate()
        assert len(errors) > 0
        assert any("Target language" in error for error in errors)
        assert any("export format" in error for error in errors)
        assert any("Output directory" in error for error in errors)


class TestSegment:
    """Test Segment data model."""
    
    def test_valid_segment(self):
        """Test valid segment creation."""
        segment = Segment(
            start_time=1.0,
            end_time=3.0,
            text="Hello world",
            confidence=0.95
        )
        assert segment.duration() == 2.0
        assert len(segment.validate()) == 0
    
    def test_invalid_segment(self):
        """Test invalid segment validation."""
        segment = Segment(
            start_time=-1.0,
            end_time=1.0,
            text="",
            confidence=1.5
        )
        errors = segment.validate()
        assert len(errors) > 0
        assert any("negative" in error for error in errors)
        assert any("empty" in error for error in errors)
        assert any("between 0 and 1" in error for error in errors)


class TestWordSegment:
    """Test WordSegment data model."""
    
    def test_valid_word_segment(self):
        """Test valid word segment creation."""
        word_segment = WordSegment(
            word="Hello",
            start_time=1.0,
            end_time=2.0,
            confidence=0.95,
            segment_id=0
        )
        assert word_segment.duration() == 1.0
        assert len(word_segment.validate()) == 0
    
    def test_invalid_word_segment(self):
        """Test invalid word segment validation."""
        word_segment = WordSegment(
            word="",
            start_time=-1.0,
            end_time=0.5,
            confidence=2.0,
            segment_id=0
        )
        errors = word_segment.validate()
        assert len(errors) > 0
        assert any("empty" in error for error in errors)
        assert any("negative" in error for error in errors)
        assert any("between 0 and 1" in error for error in errors)


class TestAlignmentData:
    """Test AlignmentData data model."""
    
    def test_valid_alignment_data(self):
        """Test valid alignment data."""
        segment = Segment(1.0, 3.0, "Hello", 0.9)
        word_segment = WordSegment("Hello", 1.0, 3.0, 0.9, 0)
        
        alignment = AlignmentData(
            segments=[segment],
            word_segments=[word_segment],
            confidence_scores=[0.9],
            audio_duration=10.0
        )
        
        assert len(alignment.validate()) == 0
        assert alignment.get_average_confidence() == 0.9
    
    def test_empty_alignment_data(self):
        """Test alignment data validation with empty data."""
        alignment = AlignmentData(
            segments=[],
            word_segments=[],
            confidence_scores=[],
            audio_duration=0.0
        )
        
        errors = alignment.validate()
        assert len(errors) > 0
        assert any("segment is required" in error for error in errors)
        assert any("word segment is required" in error for error in errors)
        assert any("duration must be positive" in error for error in errors)
    
    def test_alignment_data_with_invalid_segments(self):
        """Test alignment data with invalid segments."""
        invalid_segment = Segment(-1.0, 0.5, "", 2.0)
        invalid_word_segment = WordSegment("", -1.0, 0.5, 2.0, 0)
        
        alignment = AlignmentData(
            segments=[invalid_segment],
            word_segments=[invalid_word_segment],
            confidence_scores=[0.9],
            audio_duration=10.0
        )
        
        errors = alignment.validate()
        assert len(errors) > 0
        assert any("Segment 0:" in error for error in errors)
        assert any("Word segment 0:" in error for error in errors)
    
    def test_average_confidence_empty(self):
        """Test average confidence with empty scores."""
        alignment = AlignmentData(
            segments=[Segment(1.0, 2.0, "test", 0.9)],
            word_segments=[WordSegment("test", 1.0, 2.0, 0.9, 0)],
            confidence_scores=[],
            audio_duration=10.0
        )
        assert alignment.get_average_confidence() == 0.0


class TestAudioFile:
    """Test AudioFile data model."""
    
    def test_valid_audio_file(self):
        """Test valid audio file creation."""
        audio_file = AudioFile(
            path="/path/to/audio.mp3",
            format="mp3",
            duration=180.5,
            sample_rate=44100,
            channels=2,
            file_size=5242880
        )
        assert len(audio_file.validate()) == 0
    
    def test_invalid_audio_file(self):
        """Test invalid audio file validation."""
        audio_file = AudioFile(
            path="",
            format="",
            duration=-1.0,
            sample_rate=0,
            channels=0
        )
        errors = audio_file.validate()
        assert len(errors) > 0
        assert any("path cannot be empty" in error for error in errors)
        assert any("format cannot be empty" in error for error in errors)
        assert any("Duration must be positive" in error for error in errors)
        assert any("Sample rate must be positive" in error for error in errors)
        assert any("Channel count must be positive" in error for error in errors)


class TestSubtitleFile:
    """Test SubtitleFile data model."""
    
    def test_valid_subtitle_file(self):
        """Test valid subtitle file creation."""
        subtitle_file = SubtitleFile(
            path="/path/to/output.srt",
            format=ExportFormat.SRT,
            content="1\n00:00:01,000 --> 00:00:03,000\nHello world\n",
            word_count=2,
            duration=180.5
        )
        assert len(subtitle_file.validate()) == 0
    
    def test_invalid_subtitle_file(self):
        """Test invalid subtitle file validation."""
        subtitle_file = SubtitleFile(
            path="",
            format=ExportFormat.SRT,
            content="",
            word_count=-1,
            duration=-1.0
        )
        errors = subtitle_file.validate()
        assert len(errors) > 0
        assert any("path cannot be empty" in error for error in errors)
        assert any("Content cannot be empty" in error for error in errors)
        assert any("Word count cannot be negative" in error for error in errors)
        assert any("Duration must be positive" in error for error in errors)


class TestProcessingResult:
    """Test ProcessingResult data model."""
    
    def test_processing_result_initialization(self):
        """Test ProcessingResult initialization."""
        result = ProcessingResult(
            success=True,
            output_files=["/path/to/output.srt"],
            processing_time=45.2
        )
        assert result.success is True
        assert len(result.output_files) == 1
        assert result.processing_time == 45.2
        assert result.error_message is None
        assert result.alignment_data is None
    
    def test_processing_result_with_none_output_files(self):
        """Test ProcessingResult with None output_files."""
        result = ProcessingResult(
            success=False,
            output_files=None,
            processing_time=0.0,
            error_message="Processing failed"
        )
        assert result.output_files == []


class TestBatchResult:
    """Test BatchResult data model."""
    
    def test_batch_result_success_rate(self):
        """Test BatchResult success rate calculation."""
        result1 = ProcessingResult(True, ["/path/1.srt"], 10.0)
        result2 = ProcessingResult(False, [], 0.0, "Error")
        result3 = ProcessingResult(True, ["/path/3.srt"], 15.0)
        
        batch_result = BatchResult(
            total_files=3,
            successful_files=2,
            failed_files=1,
            processing_results=[result1, result2, result3],
            total_processing_time=25.0
        )
        
        assert abs(batch_result.success_rate() - 66.66666666666667) < 0.0001
    
    def test_batch_result_zero_files(self):
        """Test BatchResult with zero files."""
        batch_result = BatchResult(
            total_files=0,
            successful_files=0,
            failed_files=0,
            processing_results=[],
            total_processing_time=0.0
        )
        
        assert batch_result.success_rate() == 0.0


class TestProcessingStatus:
    """Test ProcessingStatus data model."""
    
    def test_processing_status_initialization(self):
        """Test ProcessingStatus initialization."""
        status = ProcessingStatus(
            is_active=True,
            current_file="/path/to/current.mp3",
            progress_percentage=45.5,
            current_operation="Vocal separation",
            estimated_time_remaining=120.0
        )
        
        assert status.is_active is True
        assert status.current_file == "/path/to/current.mp3"
        assert status.progress_percentage == 45.5
        assert status.current_operation == "Vocal separation"
        assert status.estimated_time_remaining == 120.0