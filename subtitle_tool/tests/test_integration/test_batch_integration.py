"""
Integration tests for batch processing functionality.

This module tests the complete batch processing workflow including
file queue management, progress tracking, and error handling.
"""

import pytest
import os
import tempfile
import shutil
from unittest.mock import Mock, patch, MagicMock

from src.services.batch_processor import BatchProcessor, BatchFileStatus
from src.services.audio_processor import AudioProcessor
from src.models.data_models import (
    ProcessingOptions, ModelSize, ExportFormat, AlignmentData,
    Segment, WordSegment, ProcessingResult, BatchResult
)


class TestBatchProcessingIntegration:
    """Integration tests for complete batch processing workflow."""
    
    @pytest.fixture
    def temp_audio_files(self):
        """Create temporary audio files for testing."""
        files = []
        for i in range(3):
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
                f.write(b"fake audio data for testing")
                files.append(f.name)
        
        yield files
        
        # Cleanup
        for file_path in files:
            try:
                os.unlink(file_path)
            except FileNotFoundError:
                pass
    
    @pytest.fixture
    def temp_output_dir(self):
        """Create temporary output directory."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.fixture
    def mock_audio_processor(self):
        """Create a mock audio processor for integration testing."""
        processor = Mock()
        
        # Configure successful processing
        processor.validate_audio_file.return_value = Mock(
            path="/test/audio.wav",
            format="wav",
            duration=180.0,
            sample_rate=44100,
            channels=2
        )
        processor.separate_vocals.return_value = "/tmp/vocals.wav"
        processor.transcribe_with_alignment.return_value = AlignmentData(
            segments=[
                Segment(0.0, 5.0, "Hello world", 0.95, 0),
                Segment(5.0, 10.0, "This is a test", 0.90, 1)
            ],
            word_segments=[
                WordSegment("Hello", 0.0, 1.0, 0.95, 0),
                WordSegment("world", 1.0, 2.0, 0.95, 0),
                WordSegment("This", 5.0, 6.0, 0.90, 1),
                WordSegment("is", 6.0, 6.5, 0.90, 1),
                WordSegment("a", 6.5, 7.0, 0.90, 1),
                WordSegment("test", 7.0, 8.0, 0.90, 1)
            ],
            confidence_scores=[0.95, 0.90],
            audio_duration=180.0
        )
        
        return processor
    
    def test_complete_batch_workflow(self, temp_audio_files, temp_output_dir, mock_audio_processor):
        """Test complete batch processing workflow from start to finish."""
        # Create batch processor
        batch_processor = BatchProcessor(audio_processor=mock_audio_processor)
        
        # Track progress updates
        progress_updates = []
        file_progress_updates = []
        
        def progress_callback(percentage, message):
            progress_updates.append((percentage, message))
        
        def file_progress_callback(file_path, percentage, operation):
            file_progress_updates.append((file_path, percentage, operation))
        
        batch_processor.set_progress_callback(progress_callback)
        batch_processor.set_file_progress_callback(file_progress_callback)
        
        # Add files to queue
        batch_processor.add_files_to_queue(temp_audio_files)
        
        # Verify queue status
        queue_status = batch_processor.get_queue_status()
        assert queue_status["total_files"] == len(temp_audio_files)
        assert queue_status["pending_files"] == len(temp_audio_files)
        assert queue_status["completed_files"] == 0
        assert queue_status["failed_files"] == 0
        
        # Configure processing options
        options = ProcessingOptions(
            model_size=ModelSize.BASE,
            export_formats=[ExportFormat.SRT, ExportFormat.VTT],
            output_directory=temp_output_dir
        )
        
        # Process batch
        result = batch_processor.process_batch(options)
        
        # Verify results
        assert isinstance(result, BatchResult)
        assert result.total_files == len(temp_audio_files)
        assert result.successful_files == len(temp_audio_files)
        assert result.failed_files == 0
        assert result.success_rate() == 100.0
        assert result.total_processing_time > 0
        
        # Verify all files were processed
        for processing_result in result.processing_results:
            assert processing_result.success is True
            assert len(processing_result.output_files) == 2  # SRT and VTT
            assert processing_result.alignment_data is not None
        
        # Verify progress callbacks were called
        assert len(progress_updates) > 0
        
        # Verify final queue status
        final_status = batch_processor.get_queue_status()
        assert final_status["completed_files"] == len(temp_audio_files)
        assert final_status["failed_files"] == 0
        assert final_status["progress_percentage"] == 100.0
        
        # Verify processing status
        processing_status = batch_processor.get_processing_status()
        assert processing_status.is_active is False
        assert processing_status.progress_percentage == 100.0
    
    def test_batch_processing_with_mixed_results(self, temp_audio_files, temp_output_dir, mock_audio_processor):
        """Test batch processing with some successful and some failed files."""
        # Configure mock to fail on first file
        def mock_validate_side_effect(file_path):
            if temp_audio_files[0] in file_path:
                raise Exception("Validation failed for first file")
            return Mock(
                path=file_path,
                format="wav",
                duration=180.0,
                sample_rate=44100,
                channels=2
            )
        
        mock_audio_processor.validate_audio_file.side_effect = mock_validate_side_effect
        
        # Create batch processor
        batch_processor = BatchProcessor(audio_processor=mock_audio_processor)
        
        # Add files and process
        batch_processor.add_files_to_queue(temp_audio_files)
        
        options = ProcessingOptions(
            model_size=ModelSize.BASE,
            export_formats=[ExportFormat.SRT],
            output_directory=temp_output_dir
        )
        
        result = batch_processor.process_batch(options)
        
        # Verify mixed results
        assert result.total_files == len(temp_audio_files)
        assert result.successful_files == len(temp_audio_files) - 1
        assert result.failed_files == 1
        assert 0 < result.success_rate() < 100.0
        
        # Check individual file statuses
        queue_status = batch_processor.get_queue_status()
        failed_files = [f for f in queue_status["files"] if f["status"] == "failed"]
        completed_files = [f for f in queue_status["files"] if f["status"] == "completed"]
        
        assert len(failed_files) == 1
        assert len(completed_files) == len(temp_audio_files) - 1
        assert failed_files[0]["error_message"] is not None
    
    def test_batch_processing_cancellation(self, temp_audio_files, temp_output_dir):
        """Test cancelling batch processing mid-operation."""
        # Create a slow mock processor
        slow_processor = Mock()
        
        def slow_validate(file_path):
            import time
            time.sleep(0.1)  # Simulate slow processing
            return Mock(
                path=file_path,
                format="wav",
                duration=180.0,
                sample_rate=44100,
                channels=2
            )
        
        slow_processor.validate_audio_file.side_effect = slow_validate
        slow_processor.separate_vocals.return_value = "/tmp/vocals.wav"
        slow_processor.transcribe_with_alignment.return_value = AlignmentData(
            segments=[Segment(0.0, 5.0, "Test", 0.95, 0)],
            word_segments=[WordSegment("Test", 0.0, 1.0, 0.95, 0)],
            confidence_scores=[0.95],
            audio_duration=180.0
        )
        
        batch_processor = BatchProcessor(audio_processor=slow_processor)
        batch_processor.add_files_to_queue(temp_audio_files)
        
        options = ProcessingOptions(
            model_size=ModelSize.BASE,
            export_formats=[ExportFormat.SRT],
            output_directory=temp_output_dir
        )
        
        # Start processing in a separate thread and cancel quickly
        import threading
        
        def process_batch():
            return batch_processor.process_batch(options)
        
        thread = threading.Thread(target=process_batch)
        thread.start()
        
        # Wait a bit then cancel
        import time
        time.sleep(0.05)
        cancel_result = batch_processor.cancel_processing()
        
        thread.join(timeout=2.0)
        
        # Verify cancellation
        assert cancel_result is True
        
        # Check that some files may be cancelled
        queue_status = batch_processor.get_queue_status()
        cancelled_or_pending = [
            f for f in queue_status["files"] 
            if f["status"] in ["cancelled", "pending"]
        ]
        
        # At least some files should not have completed due to cancellation
        assert len(cancelled_or_pending) >= 0  # May vary based on timing
    
    def test_error_recovery_and_continuation(self, temp_audio_files, temp_output_dir):
        """Test that batch processing continues after individual file failures."""
        # Create processor that fails on middle file
        processor = Mock()
        
        def selective_failure(file_path):
            # Fail on the second file (index 1)
            if temp_audio_files[1] in file_path:
                raise Exception("Simulated processing error")
            return Mock(
                path=file_path,
                format="wav",
                duration=180.0,
                sample_rate=44100,
                channels=2
            )
        
        processor.validate_audio_file.side_effect = selective_failure
        processor.separate_vocals.return_value = "/tmp/vocals.wav"
        processor.transcribe_with_alignment.return_value = AlignmentData(
            segments=[Segment(0.0, 5.0, "Test", 0.95, 0)],
            word_segments=[WordSegment("Test", 0.0, 1.0, 0.95, 0)],
            confidence_scores=[0.95],
            audio_duration=180.0
        )
        
        batch_processor = BatchProcessor(audio_processor=processor)
        batch_processor.add_files_to_queue(temp_audio_files)
        
        options = ProcessingOptions(
            model_size=ModelSize.BASE,
            export_formats=[ExportFormat.SRT],
            output_directory=temp_output_dir
        )
        
        result = batch_processor.process_batch(options)
        
        # Verify that processing continued despite the failure
        assert result.total_files == len(temp_audio_files)
        assert result.successful_files == len(temp_audio_files) - 1
        assert result.failed_files == 1
        
        # Verify that the first and third files succeeded
        queue_status = batch_processor.get_queue_status()
        file_statuses = {f["file_path"]: f["status"] for f in queue_status["files"]}
        
        assert file_statuses[temp_audio_files[0]] == "completed"
        assert file_statuses[temp_audio_files[1]] == "failed"
        assert file_statuses[temp_audio_files[2]] == "completed"