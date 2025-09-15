"""
Tests for the BatchProcessor service.

This module contains comprehensive tests for batch processing functionality,
including queue management, progress tracking, error handling, and cancellation.
"""

import pytest
import os
import tempfile
import time
from unittest.mock import Mock, MagicMock, patch
from typing import List

from src.services.batch_processor import (
    BatchProcessor, BatchFileStatus, BatchFileItem, BatchProcessingState
)
from src.models.data_models import (
    ProcessingOptions, ProcessingResult, BatchResult, ProcessingStatus,
    ModelSize, ExportFormat, AlignmentData, Segment, WordSegment
)
from src.services.interfaces import ProcessingError


class TestBatchFileItem:
    """Test BatchFileItem data class."""
    
    def test_batch_file_item_creation(self):
        """Test creating a BatchFileItem."""
        item = BatchFileItem(file_path="/test/audio.wav")
        
        assert item.file_path == "/test/audio.wav"
        assert item.status == BatchFileStatus.PENDING
        assert item.result is None
        assert item.error_message is None
        assert item.start_time is None
        assert item.end_time is None
    
    def test_processing_time_calculation(self):
        """Test processing time calculation."""
        item = BatchFileItem(file_path="/test/audio.wav")
        
        # No times set
        assert item.processing_time == 0.0
        
        # Set times
        item.start_time = 100.0
        item.end_time = 105.5
        assert item.processing_time == 5.5


class TestBatchProcessingState:
    """Test BatchProcessingState data class."""
    
    def test_state_creation(self):
        """Test creating a BatchProcessingState."""
        state = BatchProcessingState()
        
        assert state.total_files == 0
        assert state.completed_files == 0
        assert state.failed_files == 0
        assert state.current_file_index == 0
        assert state.current_file_path is None
        assert state.is_active is False
        assert state.is_cancelled is False
        assert state.start_time is None
        assert state.end_time is None
        assert len(state.files) == 0
    
    def test_progress_percentage_calculation(self):
        """Test progress percentage calculation."""
        state = BatchProcessingState()
        
        # No files
        assert state.progress_percentage == 0.0
        
        # With files
        state.total_files = 10
        state.completed_files = 3
        state.failed_files = 2
        assert state.progress_percentage == 50.0
    
    def test_estimated_time_remaining(self):
        """Test estimated time remaining calculation."""
        state = BatchProcessingState()
        
        # No start time or completed files
        assert state.estimated_time_remaining is None
        
        # With start time but no completed files
        state.start_time = time.time() - 10
        assert state.estimated_time_remaining is None
        
        # With completed files
        state.total_files = 10
        state.completed_files = 2
        state.failed_files = 1
        
        # Should calculate based on average time per file
        estimated = state.estimated_time_remaining
        assert estimated is not None
        assert estimated > 0


class TestBatchProcessor:
    """Test BatchProcessor class."""
    
    @pytest.fixture
    def mock_audio_processor(self):
        """Create a mock audio processor."""
        processor = Mock()
        processor.validate_audio_file.return_value = Mock(
            path="/test/audio.wav",
            format="wav",
            duration=180.0,
            sample_rate=44100,
            channels=2
        )
        processor.separate_vocals.return_value = "/tmp/vocals.wav"
        processor.transcribe_with_alignment.return_value = AlignmentData(
            segments=[Segment(0.0, 5.0, "Test text", 0.95, 0)],
            word_segments=[WordSegment("Test", 0.0, 1.0, 0.95, 0)],
            confidence_scores=[0.95],
            audio_duration=180.0
        )
        return processor
    
    @pytest.fixture
    def batch_processor(self, mock_audio_processor):
        """Create a BatchProcessor instance."""
        return BatchProcessor(audio_processor=mock_audio_processor)
    
    @pytest.fixture
    def temp_audio_files(self):
        """Create temporary audio files for testing."""
        files = []
        for i in range(3):
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
                f.write(b"fake audio data")
                files.append(f.name)
        
        yield files
        
        # Cleanup
        for file_path in files:
            try:
                os.unlink(file_path)
            except FileNotFoundError:
                pass
    
    def test_initialization(self, mock_audio_processor):
        """Test BatchProcessor initialization."""
        processor = BatchProcessor(
            audio_processor=mock_audio_processor,
            max_concurrent_files=2
        )
        
        assert processor.audio_processor == mock_audio_processor
        assert processor.max_concurrent_files == 2
        assert processor.state.total_files == 0
        assert processor.progress_callback is None
        assert processor.file_progress_callback is None
    
    def test_set_progress_callbacks(self, batch_processor):
        """Test setting progress callbacks."""
        progress_callback = Mock()
        file_progress_callback = Mock()
        
        batch_processor.set_progress_callback(progress_callback)
        batch_processor.set_file_progress_callback(file_progress_callback)
        
        assert batch_processor.progress_callback == progress_callback
        assert batch_processor.file_progress_callback == file_progress_callback
    
    def test_add_files_to_queue(self, batch_processor, temp_audio_files):
        """Test adding files to the processing queue."""
        batch_processor.add_files_to_queue(temp_audio_files)
        
        assert batch_processor.state.total_files == len(temp_audio_files)
        assert len(batch_processor.state.files) == len(temp_audio_files)
        
        for i, file_path in enumerate(temp_audio_files):
            assert batch_processor.state.files[i].file_path == file_path
            assert batch_processor.state.files[i].status == BatchFileStatus.PENDING
    
    def test_add_files_invalid_paths(self, batch_processor):
        """Test adding files with invalid paths."""
        invalid_files = ["/nonexistent/file1.wav", "/nonexistent/file2.wav"]
        
        batch_processor.add_files_to_queue(invalid_files)
        
        # Should skip invalid files
        assert batch_processor.state.total_files == 0
        assert len(batch_processor.state.files) == 0
    
    def test_add_files_unsupported_formats(self, batch_processor):
        """Test adding files with unsupported formats."""
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as f:
            f.write(b"not audio")
            txt_file = f.name
        
        try:
            batch_processor.add_files_to_queue([txt_file])
            
            # Should skip unsupported formats
            assert batch_processor.state.total_files == 0
            assert len(batch_processor.state.files) == 0
        finally:
            os.unlink(txt_file)
    
    def test_add_files_while_processing(self, batch_processor, temp_audio_files):
        """Test adding files while processing is active."""
        batch_processor.state.is_active = True
        
        with pytest.raises(ValueError, match="Cannot add files while batch processing is active"):
            batch_processor.add_files_to_queue(temp_audio_files)
    
    def test_clear_queue(self, batch_processor, temp_audio_files):
        """Test clearing the processing queue."""
        batch_processor.add_files_to_queue(temp_audio_files)
        assert batch_processor.state.total_files > 0
        
        batch_processor.clear_queue()
        
        assert batch_processor.state.total_files == 0
        assert len(batch_processor.state.files) == 0
    
    def test_clear_queue_while_processing(self, batch_processor):
        """Test clearing queue while processing is active."""
        batch_processor.state.is_active = True
        
        with pytest.raises(ValueError, match="Cannot clear queue while batch processing is active"):
            batch_processor.clear_queue()
    
    def test_process_batch_no_files(self, batch_processor):
        """Test processing batch with no files."""
        options = ProcessingOptions(
            model_size=ModelSize.BASE,
            export_formats=[ExportFormat.SRT],
            output_directory="/tmp"
        )
        
        with pytest.raises(ValueError, match="No files in processing queue"):
            batch_processor.process_batch(options)
    
    def test_process_batch_already_active(self, batch_processor, temp_audio_files):
        """Test processing batch when already active."""
        batch_processor.add_files_to_queue(temp_audio_files)
        batch_processor.state.is_active = True
        
        options = ProcessingOptions(
            model_size=ModelSize.BASE,
            export_formats=[ExportFormat.SRT],
            output_directory="/tmp"
        )
        
        with pytest.raises(ValueError, match="Batch processing is already active"):
            batch_processor.process_batch(options)
    
    def test_process_batch_successful(self, batch_processor, temp_audio_files):
        """Test successful batch processing."""
        batch_processor.add_files_to_queue(temp_audio_files)
        
        options = ProcessingOptions(
            model_size=ModelSize.BASE,
            export_formats=[ExportFormat.SRT],
            output_directory="/tmp"
        )
        
        # Mock successful processing
        with patch.object(batch_processor, '_process_single_file') as mock_process:
            mock_process.return_value = ProcessingResult(
                success=True,
                output_files=["/tmp/output.srt"],
                processing_time=1.0
            )
            
            result = batch_processor.process_batch(options)
        
        assert isinstance(result, BatchResult)
        assert result.total_files == len(temp_audio_files)
        assert result.successful_files == len(temp_audio_files)
        assert result.failed_files == 0
        assert len(result.processing_results) == len(temp_audio_files)
        
        # Check that all files were marked as completed
        for file_item in batch_processor.state.files:
            assert file_item.status == BatchFileStatus.COMPLETED
    
    def test_process_batch_with_failures(self, batch_processor, temp_audio_files):
        """Test batch processing with some failures."""
        batch_processor.add_files_to_queue(temp_audio_files)
        
        options = ProcessingOptions(
            model_size=ModelSize.BASE,
            export_formats=[ExportFormat.SRT],
            output_directory="/tmp"
        )
        
        # Mock mixed success/failure
        def mock_process_side_effect(file_path, options):
            if file_path == temp_audio_files[0]:  # First file fails
                return ProcessingResult(
                    success=False,
                    output_files=[],
                    processing_time=0.5,
                    error_message="Processing failed"
                )
            else:
                return ProcessingResult(
                    success=True,
                    output_files=["/tmp/output.srt"],
                    processing_time=1.0
                )
        
        with patch.object(batch_processor, '_process_single_file', side_effect=mock_process_side_effect):
            result = batch_processor.process_batch(options)
        
        assert result.total_files == len(temp_audio_files)
        assert result.successful_files == len(temp_audio_files) - 1
        assert result.failed_files == 1
        
        # Check file statuses
        failed_count = sum(1 for item in batch_processor.state.files if item.status == BatchFileStatus.FAILED)
        completed_count = sum(1 for item in batch_processor.state.files if item.status == BatchFileStatus.COMPLETED)
        
        assert failed_count == 1
        assert completed_count == len(temp_audio_files) - 1
    
    def test_cancel_processing(self, batch_processor, temp_audio_files):
        """Test cancelling batch processing."""
        batch_processor.add_files_to_queue(temp_audio_files)
        batch_processor.state.is_active = True
        
        result = batch_processor.cancel_processing()
        
        assert result is True
        assert batch_processor.state.is_cancelled is True
    
    def test_cancel_processing_not_active(self, batch_processor):
        """Test cancelling when not processing."""
        result = batch_processor.cancel_processing()
        
        assert result is False
    
    def test_get_processing_status(self, batch_processor, temp_audio_files):
        """Test getting processing status."""
        batch_processor.add_files_to_queue(temp_audio_files)
        
        # Initial status
        status = batch_processor.get_processing_status()
        assert isinstance(status, ProcessingStatus)
        assert status.is_active is False
        assert status.current_file is None
        assert status.progress_percentage == 0.0
        
        # Active status
        batch_processor.state.is_active = True
        batch_processor.state.current_file_path = temp_audio_files[0]
        batch_processor.state.current_file_index = 0
        
        status = batch_processor.get_processing_status()
        assert status.is_active is True
        assert status.current_file == temp_audio_files[0]
        assert "Processing file 1/" in status.current_operation
    
    def test_get_queue_status(self, batch_processor, temp_audio_files):
        """Test getting detailed queue status."""
        batch_processor.add_files_to_queue(temp_audio_files)
        
        status = batch_processor.get_queue_status()
        
        assert status["total_files"] == len(temp_audio_files)
        assert status["completed_files"] == 0
        assert status["failed_files"] == 0
        assert status["pending_files"] == len(temp_audio_files)
        assert status["is_active"] is False
        assert status["is_cancelled"] is False
        assert status["progress_percentage"] == 0.0
        assert len(status["files"]) == len(temp_audio_files)
        
        # Check file details
        for i, file_info in enumerate(status["files"]):
            assert file_info["file_path"] == temp_audio_files[i]
            assert file_info["status"] == "pending"
            assert file_info["processing_time"] == 0.0
            assert file_info["error_message"] is None
    
    def test_progress_callbacks_called(self, batch_processor, temp_audio_files):
        """Test that progress callbacks are called during processing."""
        batch_processor.add_files_to_queue(temp_audio_files[:1])  # Just one file for simplicity
        
        progress_callback = Mock()
        file_progress_callback = Mock()
        
        batch_processor.set_progress_callback(progress_callback)
        batch_processor.set_file_progress_callback(file_progress_callback)
        
        options = ProcessingOptions(
            model_size=ModelSize.BASE,
            export_formats=[ExportFormat.SRT],
            output_directory="/tmp"
        )
        
        with patch.object(batch_processor, '_process_single_file') as mock_process:
            mock_process.return_value = ProcessingResult(
                success=True,
                output_files=["/tmp/output.srt"],
                processing_time=1.0
            )
            
            batch_processor.process_batch(options)
        
        # Progress callback should be called
        assert progress_callback.called
        
        # Check that audio processor's progress callback was set
        assert batch_processor.audio_processor.set_progress_callback.called
    
    def test_process_single_file_success(self, batch_processor, temp_audio_files):
        """Test processing a single file successfully."""
        options = ProcessingOptions(
            model_size=ModelSize.BASE,
            export_formats=[ExportFormat.SRT],
            output_directory="/tmp"
        )
        
        result = batch_processor._process_single_file(temp_audio_files[0], options)
        
        assert isinstance(result, ProcessingResult)
        assert result.success is True
        assert result.alignment_data is not None
        assert result.processing_time > 0
        assert len(result.output_files) > 0
    
    def test_process_single_file_failure(self, batch_processor, temp_audio_files):
        """Test processing a single file with failure."""
        # Mock audio processor to raise exception
        batch_processor.audio_processor.validate_audio_file.side_effect = Exception("Validation failed")
        
        options = ProcessingOptions(
            model_size=ModelSize.BASE,
            export_formats=[ExportFormat.SRT],
            output_directory="/tmp"
        )
        
        result = batch_processor._process_single_file(temp_audio_files[0], options)
        
        assert isinstance(result, ProcessingResult)
        assert result.success is False
        assert result.error_message == "Validation failed"
        assert result.processing_time > 0
        assert len(result.output_files) == 0
    
    def test_generate_output_files(self, batch_processor):
        """Test generating output file paths."""
        alignment_data = AlignmentData(
            segments=[Segment(0.0, 5.0, "Test", 0.95, 0)],
            word_segments=[WordSegment("Test", 0.0, 1.0, 0.95, 0)],
            confidence_scores=[0.95],
            audio_duration=5.0
        )
        
        options = ProcessingOptions(
            export_formats=[ExportFormat.SRT, ExportFormat.VTT],
            output_directory="/tmp"
        )
        
        output_files = batch_processor._generate_output_files(
            "/path/to/audio.wav", alignment_data, options
        )
        
        assert len(output_files) == 2
        assert "/tmp/audio.srt" in output_files
        assert "/tmp/audio.vtt" in output_files


class TestBatchProcessorIntegration:
    """Integration tests for BatchProcessor."""
    
    @pytest.fixture
    def real_batch_processor(self):
        """Create a BatchProcessor with real dependencies (mocked)."""
        with patch('src.services.batch_processor.AudioProcessor') as mock_audio_processor_class:
            mock_processor = Mock()
            mock_audio_processor_class.return_value = mock_processor
            
            # Configure mock processor
            mock_processor.validate_audio_file.return_value = Mock(
                path="/test/audio.wav",
                format="wav",
                duration=180.0,
                sample_rate=44100,
                channels=2
            )
            mock_processor.separate_vocals.return_value = "/tmp/vocals.wav"
            mock_processor.transcribe_with_alignment.return_value = AlignmentData(
                segments=[Segment(0.0, 5.0, "Test text", 0.95, 0)],
                word_segments=[WordSegment("Test", 0.0, 1.0, 0.95, 0)],
                confidence_scores=[0.95],
                audio_duration=180.0
            )
            
            return BatchProcessor()
    
    @pytest.fixture
    def integration_temp_audio_files(self):
        """Create temporary audio files for integration testing."""
        files = []
        for i in range(2):
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
                f.write(b"fake audio data")
                files.append(f.name)
        
        yield files
        
        # Cleanup
        for file_path in files:
            try:
                os.unlink(file_path)
            except FileNotFoundError:
                pass
    
    def test_full_batch_workflow(self, real_batch_processor, integration_temp_audio_files):
        """Test complete batch processing workflow."""
        # Add files to queue
        real_batch_processor.add_files_to_queue(integration_temp_audio_files)
        
        # Set up progress tracking
        progress_updates = []
        file_progress_updates = []
        
        def progress_callback(percentage, message):
            progress_updates.append((percentage, message))
        
        def file_progress_callback(file_path, percentage, operation):
            file_progress_updates.append((file_path, percentage, operation))
        
        real_batch_processor.set_progress_callback(progress_callback)
        real_batch_processor.set_file_progress_callback(file_progress_callback)
        
        # Process batch
        options = ProcessingOptions(
            model_size=ModelSize.BASE,
            export_formats=[ExportFormat.SRT],
            output_directory="/tmp"
        )
        
        result = real_batch_processor.process_batch(options)
        
        # Verify results
        assert result.total_files == len(integration_temp_audio_files)
        assert result.successful_files == len(integration_temp_audio_files)
        assert result.failed_files == 0
        assert result.success_rate() == 100.0
        
        # Verify progress updates were called
        assert len(progress_updates) > 0
        
        # Verify final state
        status = real_batch_processor.get_processing_status()
        assert status.is_active is False
        assert status.progress_percentage == 100.0


class TestBatchReporting:
    """Test enhanced batch reporting functionality."""
    
    @pytest.fixture
    def mock_audio_processor(self):
        """Create a mock audio processor for reporting tests."""
        processor = Mock()
        processor.validate_audio_file.return_value = Mock(
            path="/test/audio.wav",
            format="wav",
            duration=180.0,
            sample_rate=44100,
            channels=2
        )
        processor.separate_vocals.return_value = "/tmp/vocals.wav"
        processor.transcribe_with_alignment.return_value = AlignmentData(
            segments=[Segment(0.0, 5.0, "Test text", 0.95, 0)],
            word_segments=[WordSegment("Test", 0.0, 1.0, 0.95, 0)],
            confidence_scores=[0.95],
            audio_duration=180.0
        )
        return processor
    
    @pytest.fixture
    def batch_processor_with_reporting(self, mock_audio_processor):
        """Create a BatchProcessor instance for reporting tests."""
        return BatchProcessor(audio_processor=mock_audio_processor)
    
    @pytest.fixture
    def temp_audio_files_reporting(self):
        """Create temporary audio files for reporting tests."""
        files = []
        for i in range(3):
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
                f.write(b"fake audio data for reporting")
                files.append(f.name)
        
        yield files
        
        # Cleanup
        for file_path in files:
            try:
                os.unlink(file_path)
            except FileNotFoundError:
                pass
    
    def test_enhanced_batch_result_creation(self, batch_processor_with_reporting, temp_audio_files_reporting):
        """Test creation of enhanced BatchResult with detailed reporting."""
        batch_processor_with_reporting.add_files_to_queue(temp_audio_files_reporting)
        
        options = ProcessingOptions(
            model_size=ModelSize.BASE,
            export_formats=[ExportFormat.SRT, ExportFormat.VTT],
            output_directory="/tmp"
        )
        
        # Mock successful processing
        with patch.object(batch_processor_with_reporting, '_process_single_file') as mock_process:
            mock_process.return_value = ProcessingResult(
                success=True,
                output_files=["/tmp/output.srt", "/tmp/output.vtt"],
                processing_time=2.5,
                alignment_data=AlignmentData(
                    segments=[Segment(0.0, 5.0, "Test", 0.95, 0)],
                    word_segments=[WordSegment("Test", 0.0, 1.0, 0.95, 0)],
                    confidence_scores=[0.95],
                    audio_duration=180.0
                )
            )
            
            result = batch_processor_with_reporting.process_batch(options)
        
        # Verify enhanced BatchResult
        assert isinstance(result, BatchResult)
        assert len(result.file_reports) == len(temp_audio_files_reporting)
        assert result.summary_stats is not None
        assert result.start_time is not None
        assert result.end_time is not None
        assert result.cancelled_files == 0
        
        # Verify summary stats
        stats = result.summary_stats
        assert stats.total_files == len(temp_audio_files_reporting)
        assert stats.successful_files == len(temp_audio_files_reporting)
        assert stats.failed_files == 0
        assert stats.success_rate == 100.0
        assert stats.total_output_files == len(temp_audio_files_reporting) * 2  # SRT + VTT
        assert stats.average_processing_time > 0
        
        # Verify file reports
        for report in result.file_reports:
            assert report.success is True
            assert report.status == "completed"
            assert len(report.output_files) == 2
            assert report.processing_time > 0
            assert report.error_message is None
            assert report.audio_duration == 180.0
    
    def test_batch_result_with_failures(self, batch_processor_with_reporting, temp_audio_files_reporting):
        """Test BatchResult creation with mixed success/failure results."""
        batch_processor_with_reporting.add_files_to_queue(temp_audio_files_reporting)
        
        options = ProcessingOptions(
            model_size=ModelSize.BASE,
            export_formats=[ExportFormat.SRT],
            output_directory="/tmp"
        )
        
        # Mock mixed results
        def mock_process_side_effect(file_path, options):
            if file_path == temp_audio_files_reporting[0]:  # First file fails
                return ProcessingResult(
                    success=False,
                    output_files=[],
                    processing_time=0.5,
                    error_message="Model loading failed"
                )
            else:
                return ProcessingResult(
                    success=True,
                    output_files=["/tmp/output.srt"],
                    processing_time=2.0,
                    alignment_data=AlignmentData(
                        segments=[Segment(0.0, 5.0, "Test", 0.95, 0)],
                        word_segments=[WordSegment("Test", 0.0, 1.0, 0.95, 0)],
                        confidence_scores=[0.95],
                        audio_duration=120.0
                    )
                )
        
        with patch.object(batch_processor_with_reporting, '_process_single_file', side_effect=mock_process_side_effect):
            result = batch_processor_with_reporting.process_batch(options)
        
        # Verify mixed results
        assert result.successful_files == 2
        assert result.failed_files == 1
        assert abs(result.summary_stats.success_rate - 66.67) < 0.1  # Approximately 66.67%
        
        # Verify error categorization
        failed_report = next(report for report in result.file_reports if not report.success)
        assert failed_report.error_category == "processing"  # "model" keyword
        assert failed_report.status == "failed"
        
        # Verify error breakdown in stats
        assert result.summary_stats.processing_errors == 1
        assert result.summary_stats.validation_errors == 0
    
    def test_error_categorization(self, batch_processor_with_reporting):
        """Test error message categorization."""
        test_cases = [
            ("Unsupported file format", "validation"),
            ("Model loading failed", "processing"),
            ("Permission denied writing output", "export"),
            ("Out of memory", "system"),
            ("Transcription alignment error", "processing"),
            ("Invalid audio file", "validation"),
            ("Disk space insufficient", "export"),
            ("Network timeout", "system"),
            ("Unknown error", "processing")  # Default case
        ]
        
        for error_message, expected_category in test_cases:
            category = batch_processor_with_reporting._categorize_error(error_message)
            assert category == expected_category, f"Error '{error_message}' should be categorized as '{expected_category}', got '{category}'"
    
    def test_batch_summary_generation(self, batch_processor_with_reporting, temp_audio_files_reporting):
        """Test batch summary generation."""
        batch_processor_with_reporting.add_files_to_queue(temp_audio_files_reporting)
        
        options = ProcessingOptions(
            model_size=ModelSize.BASE,
            export_formats=[ExportFormat.SRT],
            output_directory="/tmp"
        )
        
        with patch.object(batch_processor_with_reporting, '_process_single_file') as mock_process:
            mock_process.return_value = ProcessingResult(
                success=True,
                output_files=["/tmp/output.srt"],
                processing_time=1.5
            )
            
            result = batch_processor_with_reporting.process_batch(options)
        
        # Test get_batch_summary method
        summary = batch_processor_with_reporting.get_batch_summary(result)
        
        assert "overview" in summary
        assert "timing" in summary
        assert "output" in summary
        assert "errors" in summary
        assert "files" in summary
        
        # Verify overview section
        overview = summary["overview"]
        assert overview["total_files"] == len(temp_audio_files_reporting)
        assert overview["successful_files"] == len(temp_audio_files_reporting)
        assert overview["success_rate"] == 100.0
        
        # Verify files section
        files = summary["files"]
        assert len(files) == len(temp_audio_files_reporting)
        for file_info in files:
            assert file_info["success"] is True
            assert file_info["output_count"] == 1
            assert file_info["error"] is None
    
    def test_export_batch_report_txt(self, batch_processor_with_reporting, temp_audio_files_reporting):
        """Test exporting batch report in text format."""
        batch_processor_with_reporting.add_files_to_queue(temp_audio_files_reporting)
        
        options = ProcessingOptions(
            model_size=ModelSize.BASE,
            export_formats=[ExportFormat.SRT],
            output_directory="/tmp"
        )
        
        with patch.object(batch_processor_with_reporting, '_process_single_file') as mock_process:
            mock_process.return_value = ProcessingResult(
                success=True,
                output_files=["/tmp/output.srt"],
                processing_time=1.0
            )
            
            result = batch_processor_with_reporting.process_batch(options)
        
        # Export report
        with tempfile.TemporaryDirectory() as temp_dir:
            exported_files = batch_processor_with_reporting.export_batch_report(
                result, temp_dir, formats=['txt']
            )
            
            assert len(exported_files) == 1
            assert exported_files[0].endswith('.txt')
            assert os.path.exists(exported_files[0])
            
            # Verify report content
            with open(exported_files[0], 'r', encoding='utf-8') as f:
                content = f.read()
                assert "BATCH PROCESSING SUMMARY REPORT" in content
                assert "OVERALL STATISTICS" in content
                assert "INDIVIDUAL FILE RESULTS" in content
                assert f"Total Files Processed: {len(temp_audio_files_reporting)}" in content
    
    def test_export_batch_report_json(self, batch_processor_with_reporting, temp_audio_files_reporting):
        """Test exporting batch report in JSON format."""
        batch_processor_with_reporting.add_files_to_queue(temp_audio_files_reporting)
        
        options = ProcessingOptions(
            model_size=ModelSize.BASE,
            export_formats=[ExportFormat.SRT],
            output_directory="/tmp"
        )
        
        with patch.object(batch_processor_with_reporting, '_process_single_file') as mock_process:
            mock_process.return_value = ProcessingResult(
                success=True,
                output_files=["/tmp/output.srt"],
                processing_time=1.0
            )
            
            result = batch_processor_with_reporting.process_batch(options)
        
        # Export report
        with tempfile.TemporaryDirectory() as temp_dir:
            exported_files = batch_processor_with_reporting.export_batch_report(
                result, temp_dir, formats=['json']
            )
            
            assert len(exported_files) == 1
            assert exported_files[0].endswith('.json')
            assert os.path.exists(exported_files[0])
            
            # Verify JSON content
            import json
            with open(exported_files[0], 'r', encoding='utf-8') as f:
                data = json.load(f)
                
                assert "timestamp" in data
                assert "summary_stats" in data
                assert "file_reports" in data
                
                summary_stats = data["summary_stats"]
                assert summary_stats["total_files"] == len(temp_audio_files_reporting)
                assert summary_stats["successful_files"] == len(temp_audio_files_reporting)
                assert summary_stats["success_rate"] == 100.0
                
                file_reports = data["file_reports"]
                assert len(file_reports) == len(temp_audio_files_reporting)
    
    def test_export_batch_report_multiple_formats(self, batch_processor_with_reporting, temp_audio_files_reporting):
        """Test exporting batch report in multiple formats."""
        batch_processor_with_reporting.add_files_to_queue(temp_audio_files_reporting)
        
        options = ProcessingOptions(
            model_size=ModelSize.BASE,
            export_formats=[ExportFormat.SRT],
            output_directory="/tmp"
        )
        
        with patch.object(batch_processor_with_reporting, '_process_single_file') as mock_process:
            mock_process.return_value = ProcessingResult(
                success=True,
                output_files=["/tmp/output.srt"],
                processing_time=1.0
            )
            
            result = batch_processor_with_reporting.process_batch(options)
        
        # Export in both formats
        with tempfile.TemporaryDirectory() as temp_dir:
            exported_files = batch_processor_with_reporting.export_batch_report(
                result, temp_dir, formats=['txt', 'json']
            )
            
            assert len(exported_files) == 2
            
            txt_files = [f for f in exported_files if f.endswith('.txt')]
            json_files = [f for f in exported_files if f.endswith('.json')]
            
            assert len(txt_files) == 1
            assert len(json_files) == 1
            
            for file_path in exported_files:
                assert os.path.exists(file_path)
    
    def test_completion_notification(self, batch_processor_with_reporting, temp_audio_files_reporting):
        """Test batch completion notification."""
        batch_processor_with_reporting.add_files_to_queue(temp_audio_files_reporting)
        
        # Set up progress callback to capture notifications
        notifications = []
        def progress_callback(percentage, message):
            notifications.append((percentage, message))
        
        batch_processor_with_reporting.set_progress_callback(progress_callback)
        
        options = ProcessingOptions(
            model_size=ModelSize.BASE,
            export_formats=[ExportFormat.SRT],
            output_directory="/tmp"
        )
        
        with patch.object(batch_processor_with_reporting, '_process_single_file') as mock_process:
            mock_process.return_value = ProcessingResult(
                success=True,
                output_files=["/tmp/output.srt"],
                processing_time=1.0
            )
            
            batch_processor_with_reporting.process_batch(options)
        
        # Verify completion notification was sent
        completion_notifications = [n for n in notifications if n[0] == 100.0]
        assert len(completion_notifications) > 0
        
        # Check notification message content
        final_notification = completion_notifications[-1]
        assert "completed successfully" in final_notification[1].lower()
        assert str(len(temp_audio_files_reporting)) in final_notification[1]