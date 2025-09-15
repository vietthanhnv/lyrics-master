"""
Integration tests for batch processing reporting functionality.

This module tests the complete batch processing workflow with enhanced reporting,
including summary generation, error categorization, and report export.
"""

import pytest
import os
import tempfile
import json
from unittest.mock import Mock, patch

from src.services.batch_processor import BatchProcessor
from src.models.data_models import (
    ProcessingOptions, ProcessingResult, ModelSize, ExportFormat,
    AlignmentData, Segment, WordSegment
)


class TestBatchReportingIntegration:
    """Integration tests for batch processing reporting."""
    
    @pytest.fixture
    def mock_audio_processor(self):
        """Create a mock audio processor for integration tests."""
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
        """Create a BatchProcessor instance for integration tests."""
        return BatchProcessor(audio_processor=mock_audio_processor)
    
    @pytest.fixture
    def temp_audio_files(self):
        """Create temporary audio files for testing."""
        files = []
        for i in range(3):
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
                f.write(b"fake audio data for integration test")
                files.append(f.name)
        
        yield files
        
        # Cleanup
        for file_path in files:
            try:
                os.unlink(file_path)
            except FileNotFoundError:
                pass
    
    def test_complete_batch_reporting_workflow(self, batch_processor, temp_audio_files):
        """Test complete batch processing workflow with reporting."""
        # Add files to queue
        batch_processor.add_files_to_queue(temp_audio_files)
        
        # Set up processing options
        options = ProcessingOptions(
            model_size=ModelSize.BASE,
            export_formats=[ExportFormat.SRT, ExportFormat.VTT],
            output_directory="/tmp"
        )
        
        # Mock mixed success/failure results
        def mock_process_side_effect(file_path, options):
            if file_path == temp_audio_files[0]:  # First file fails with validation error
                return ProcessingResult(
                    success=False,
                    output_files=[],
                    processing_time=0.3,
                    error_message="Unsupported audio format detected"
                )
            elif file_path == temp_audio_files[1]:  # Second file fails with processing error
                return ProcessingResult(
                    success=False,
                    output_files=[],
                    processing_time=1.2,
                    error_message="Model transcription failed"
                )
            else:  # Third file succeeds
                return ProcessingResult(
                    success=True,
                    output_files=["/tmp/output.srt", "/tmp/output.vtt"],
                    processing_time=3.5,
                    alignment_data=AlignmentData(
                        segments=[Segment(0.0, 5.0, "Success", 0.95, 0)],
                        word_segments=[WordSegment("Success", 0.0, 1.0, 0.95, 0)],
                        confidence_scores=[0.95],
                        audio_duration=180.0
                    )
                )
        
        # Process batch with mocked results
        with patch.object(batch_processor, '_process_single_file', side_effect=mock_process_side_effect):
            result = batch_processor.process_batch(options)
        
        # Verify batch result structure
        assert result.total_files == 3
        assert result.successful_files == 1
        assert result.failed_files == 2
        assert result.cancelled_files == 0
        
        # Verify enhanced reporting data
        assert len(result.file_reports) == 3
        assert result.summary_stats is not None
        
        # Verify summary statistics
        stats = result.summary_stats
        assert stats.total_files == 3
        assert stats.successful_files == 1
        assert stats.failed_files == 2
        assert abs(stats.success_rate - 33.33) < 0.1  # Approximately 33.33%
        assert stats.total_output_files == 2  # Only successful file has outputs
        assert stats.validation_errors == 1  # First file
        assert stats.processing_errors == 1  # Second file
        assert stats.export_errors == 0
        assert stats.system_errors == 0
        
        # Verify individual file reports
        file_reports = result.file_reports
        
        # First file - validation error
        assert file_reports[0].success is False
        assert file_reports[0].error_category == "validation"
        assert "unsupported" in file_reports[0].error_message.lower()
        
        # Second file - processing error
        assert file_reports[1].success is False
        assert file_reports[1].error_category == "processing"
        assert "transcription" in file_reports[1].error_message.lower()
        
        # Third file - success
        assert file_reports[2].success is True
        assert file_reports[2].error_category is None
        assert len(file_reports[2].output_files) == 2
    
    def test_batch_report_export_integration(self, batch_processor, temp_audio_files):
        """Test exporting batch reports in different formats."""
        # Add files and process
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
                processing_time=2.0,
                alignment_data=AlignmentData(
                    segments=[Segment(0.0, 5.0, "Test", 0.95, 0)],
                    word_segments=[WordSegment("Test", 0.0, 1.0, 0.95, 0)],
                    confidence_scores=[0.95],
                    audio_duration=180.0
                )
            )
            
            result = batch_processor.process_batch(options)
        
        # Test report export
        with tempfile.TemporaryDirectory() as temp_dir:
            # Export both text and JSON reports
            exported_files = batch_processor.export_batch_report(
                result, temp_dir, formats=['txt', 'json']
            )
            
            assert len(exported_files) == 2
            
            # Verify text report
            txt_file = next(f for f in exported_files if f.endswith('.txt'))
            assert os.path.exists(txt_file)
            
            with open(txt_file, 'r', encoding='utf-8') as f:
                txt_content = f.read()
                assert "BATCH PROCESSING SUMMARY REPORT" in txt_content
                assert "Total Files Processed: 3" in txt_content
                assert "Successful: 3" in txt_content
                assert "Success Rate: 100.0%" in txt_content
            
            # Verify JSON report
            json_file = next(f for f in exported_files if f.endswith('.json'))
            assert os.path.exists(json_file)
            
            with open(json_file, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
                
                assert "timestamp" in json_data
                assert "summary_stats" in json_data
                assert "file_reports" in json_data
                
                summary = json_data["summary_stats"]
                assert summary["total_files"] == 3
                assert summary["successful_files"] == 3
                assert summary["success_rate"] == 100.0
                
                reports = json_data["file_reports"]
                assert len(reports) == 3
                for report in reports:
                    assert report["success"] is True
                    assert len(report["output_files"]) == 1
    
    def test_batch_summary_generation(self, batch_processor, temp_audio_files):
        """Test batch summary generation functionality."""
        batch_processor.add_files_to_queue(temp_audio_files)
        
        options = ProcessingOptions(
            model_size=ModelSize.BASE,
            export_formats=[ExportFormat.SRT],
            output_directory="/tmp"
        )
        
        # Mock processing with one failure
        def mock_process_side_effect(file_path, options):
            if file_path == temp_audio_files[0]:
                return ProcessingResult(
                    success=False,
                    output_files=[],
                    processing_time=0.5,
                    error_message="Export permission denied"
                )
            else:
                return ProcessingResult(
                    success=True,
                    output_files=["/tmp/output.srt"],
                    processing_time=2.0
                )
        
        with patch.object(batch_processor, '_process_single_file', side_effect=mock_process_side_effect):
            result = batch_processor.process_batch(options)
        
        # Test get_batch_summary method
        summary = batch_processor.get_batch_summary(result)
        
        # Verify summary structure
        assert "overview" in summary
        assert "timing" in summary
        assert "output" in summary
        assert "errors" in summary
        assert "files" in summary
        
        # Verify overview data
        overview = summary["overview"]
        assert overview["total_files"] == 3
        assert overview["successful_files"] == 2
        assert overview["failed_files"] == 1
        assert abs(overview["success_rate"] - 66.67) < 0.1
        
        # Verify error breakdown
        errors = summary["errors"]
        assert errors["export_errors"] == 1  # "permission" keyword
        assert errors["validation_errors"] == 0
        assert errors["processing_errors"] == 0
        assert errors["system_errors"] == 0
        
        # Verify file details
        files = summary["files"]
        assert len(files) == 3
        
        failed_file = next(f for f in files if not f["success"])
        assert failed_file["error"] == "Export permission denied"
        assert failed_file["output_count"] == 0
        
        successful_files = [f for f in files if f["success"]]
        assert len(successful_files) == 2
        for file_info in successful_files:
            assert file_info["output_count"] == 1
            assert file_info["error"] is None
    
    def test_completion_notification_integration(self, batch_processor, temp_audio_files):
        """Test batch completion notification integration."""
        batch_processor.add_files_to_queue(temp_audio_files)
        
        # Capture notifications
        notifications = []
        def progress_callback(percentage, message):
            notifications.append((percentage, message))
        
        batch_processor.set_progress_callback(progress_callback)
        
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
                processing_time=1.5
            )
            
            batch_processor.process_batch(options)
        
        # Verify completion notification was sent
        completion_notifications = [n for n in notifications if n[0] == 100.0]
        assert len(completion_notifications) > 0
        
        # Verify notification message content
        final_notification = completion_notifications[-1]
        message = final_notification[1]
        assert "completed successfully" in message.lower()
        assert "3 files processed" in message
        # Note: timing information may not be included for very short processing times