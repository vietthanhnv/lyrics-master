"""
Integration tests for results display and error handling functionality.
"""

import pytest
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtTest import QTest

from src.ui.main_window import MainWindow
from src.ui.results_panel import ResultsPanel
from src.models.data_models import (
    ProcessingResult, BatchResult, BatchFileReport,
    AlignmentData, Segment, WordSegment, ProcessingOptions
)


@pytest.fixture
def app():
    """Create QApplication instance for testing."""
    return QApplication.instance() or QApplication([])


@pytest.fixture
def main_window(app):
    """Create MainWindow instance for testing."""
    return MainWindow()


@pytest.fixture
def sample_audio_files():
    """Create sample audio files for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        audio_files = []
        for i in range(3):
            file_path = os.path.join(temp_dir, f"test_audio_{i}.wav")
            # Create empty file
            with open(file_path, 'wb') as f:
                f.write(b'\x00' * 1024)  # Write some dummy data
            audio_files.append(file_path)
        yield audio_files


@pytest.fixture
def sample_successful_result():
    """Create sample successful processing result."""
    with tempfile.TemporaryDirectory() as temp_dir:
        output_files = []
        for ext in ['srt', 'ass', 'vtt']:
            file_path = os.path.join(temp_dir, f"output.{ext}")
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(f"Sample {ext.upper()} content\nLine 2\nLine 3")
            output_files.append(file_path)
        
        # Create alignment data
        segments = [
            Segment(0.0, 3.0, "Hello world", 0.95, 0),
            Segment(3.0, 6.0, "This is a test", 0.88, 1)
        ]
        
        word_segments = [
            WordSegment("Hello", 0.0, 1.0, 0.95, 0),
            WordSegment("world", 1.0, 2.0, 0.92, 0),
            WordSegment("This", 3.0, 3.5, 0.88, 1),
            WordSegment("is", 3.5, 4.0, 0.90, 1),
            WordSegment("a", 4.0, 4.2, 0.85, 1),
            WordSegment("test", 4.2, 5.0, 0.87, 1)
        ]
        
        alignment_data = AlignmentData(
            segments=segments,
            word_segments=word_segments,
            confidence_scores=[0.95, 0.88],
            audio_duration=6.0,
            source_file="test_audio.wav"
        )
        
        yield ProcessingResult(
            success=True,
            output_files=output_files,
            processing_time=12.5,
            alignment_data=alignment_data
        )


@pytest.fixture
def sample_failed_result():
    """Create sample failed processing result."""
    return ProcessingResult(
        success=False,
        output_files=[],
        processing_time=2.1,
        error_message="Audio file format not supported"
    )


@pytest.fixture
def sample_batch_result_mixed():
    """Create sample batch result with mixed success/failure."""
    file_reports = [
        BatchFileReport(
            file_path="/path/to/success1.wav",
            file_name="success1.wav",
            status="completed",
            success=True,
            processing_time=15.2,
            output_files=["/path/to/success1.srt", "/path/to/success1.ass"],
            file_size=2048000,
            audio_duration=180.0
        ),
        BatchFileReport(
            file_path="/path/to/failed1.wav",
            file_name="failed1.wav",
            status="failed",
            success=False,
            processing_time=3.1,
            output_files=[],
            error_message="Insufficient memory",
            error_category="system",
            file_size=4096000,
            audio_duration=300.0
        ),
        BatchFileReport(
            file_path="/path/to/success2.wav",
            file_name="success2.wav",
            status="completed",
            success=True,
            processing_time=22.8,
            output_files=["/path/to/success2.srt"],
            file_size=1536000,
            audio_duration=120.0
        ),
        BatchFileReport(
            file_path="/path/to/failed2.wav",
            file_name="failed2.wav",
            status="failed",
            success=False,
            processing_time=1.5,
            output_files=[],
            error_message="File corrupted",
            error_category="validation",
            file_size=512000,
            audio_duration=60.0
        )
    ]
    
    processing_results = [
        ProcessingResult(True, ["/path/to/success1.srt", "/path/to/success1.ass"], 15.2),
        ProcessingResult(False, [], 3.1, "Insufficient memory"),
        ProcessingResult(True, ["/path/to/success2.srt"], 22.8),
        ProcessingResult(False, [], 1.5, "File corrupted")
    ]
    
    batch_result = BatchResult(
        total_files=4,
        successful_files=2,
        failed_files=2,
        processing_results=processing_results,
        total_processing_time=42.6,
        file_reports=file_reports,
        cancelled_files=0
    )
    
    batch_result.summary_stats = batch_result.generate_summary_stats()
    return batch_result


class TestResultsIntegration:
    """Integration tests for results display functionality."""
    
    def test_main_window_results_integration(self, main_window, sample_successful_result):
        """Test integration between main window and results panel."""
        # Initially results should be hidden
        assert not main_window.is_results_visible()
        assert not main_window.results_panel.isVisible()
        
        # Show successful results
        main_window.show_processing_success(sample_successful_result, 12.5)
        
        # Results should now be visible
        assert main_window.is_results_visible()
        assert main_window.results_panel.isVisible()
        
        # Check that success section is shown
        assert main_window.results_panel.success_group.isVisible()
        assert not main_window.results_panel.error_group.isVisible()
        
        # Hide results
        main_window.hide_results()
        assert not main_window.is_results_visible()
        
    def test_error_display_integration(self, main_window):
        """Test error display integration."""
        error_message = "Processing failed due to corrupted audio file"
        error_category = "validation"
        suggestions = [
            "Try converting the file to WAV format",
            "Check if the file plays in a media player",
            "Use a different audio file"
        ]
        detailed_error = "AudioDecodeError: Invalid header in WAV file"
        
        # Show error results
        main_window.show_processing_error(
            error_message, error_category, suggestions, detailed_error
        )
        
        # Check error is displayed
        assert main_window.is_results_visible()
        assert not main_window.results_panel.success_group.isVisible()
        assert main_window.results_panel.error_group.isVisible()
        
        # Check error content
        assert main_window.results_panel.error_message.text() == error_message
        assert main_window.results_panel.suggestions_list.count() == 3
        
        # Check error log contains detailed error
        error_log = main_window.results_panel.error_log.toPlainText()
        assert detailed_error in error_log
        assert error_category in error_log
        
    def test_batch_results_integration(self, main_window, sample_batch_result_mixed):
        """Test batch results display integration."""
        # Show batch results
        main_window.show_batch_results(sample_batch_result_mixed)
        
        # Check results are visible and on correct tab
        assert main_window.is_results_visible()
        assert main_window.results_panel.tab_widget.currentIndex() == 1
        
        # Check summary statistics
        assert main_window.results_panel.total_files_label.text() == "4"
        assert main_window.results_panel.successful_files_label.text() == "2"
        assert main_window.results_panel.failed_files_label.text() == "2"
        assert "50.0%" in main_window.results_panel.success_rate_label.text()
        
        # Check individual file results
        assert main_window.results_panel.batch_tree.topLevelItemCount() == 4
        
        # Check success and failure items
        success_count = 0
        failure_count = 0
        
        for i in range(4):
            item = main_window.results_panel.batch_tree.topLevelItem(i)
            status_text = item.text(1)
            if "✓ Success" in status_text:
                success_count += 1
            elif "✗ Failed" in status_text:
                failure_count += 1
                
        assert success_count == 2
        assert failure_count == 2
        
    def test_file_operations_integration(self, main_window, sample_successful_result):
        """Test file operations integration."""
        # Show successful results
        main_window.show_processing_success(sample_successful_result)
        
        # Test signal connections exist
        assert main_window.results_panel.retry_requested.receivers() > 0
        assert main_window.results_panel.open_file_requested.receivers() > 0
        assert main_window.results_panel.show_in_folder_requested.receivers() > 0
        
        # Test retry signal emission
        retry_spy = Mock()
        main_window.results_panel.retry_requested.connect(retry_spy)
        
        # Trigger retry
        main_window.results_panel._retry_processing()
        retry_spy.assert_called_once_with("current_file")
        
    @patch('subprocess.run')
    @patch('os.startfile')
    @patch('platform.system')
    def test_file_opening_cross_platform(self, mock_platform, mock_startfile, mock_subprocess, main_window):
        """Test cross-platform file opening functionality."""
        test_file = "/path/to/test.srt"
        
        # Test Windows
        mock_platform.return_value = "Windows"
        main_window._on_open_file_requested(test_file)
        mock_startfile.assert_called_once_with(test_file)
        
        # Reset mocks
        mock_startfile.reset_mock()
        mock_subprocess.reset_mock()
        
        # Test macOS
        mock_platform.return_value = "Darwin"
        main_window._on_open_file_requested(test_file)
        mock_subprocess.run.assert_called_once_with(["open", test_file])
        
        # Reset mocks
        mock_subprocess.reset_mock()
        
        # Test Linux
        mock_platform.return_value = "Linux"
        main_window._on_open_file_requested(test_file)
        mock_subprocess.run.assert_called_once_with(["xdg-open", test_file])
        
    @patch('subprocess.run')
    @patch('platform.system')
    def test_folder_opening_cross_platform(self, mock_platform, mock_subprocess, main_window):
        """Test cross-platform folder opening functionality."""
        test_folder = "/path/to/folder"
        
        # Test Windows
        mock_platform.return_value = "Windows"
        main_window._on_show_in_folder_requested(test_folder)
        mock_subprocess.run.assert_called_with(["explorer", test_folder])
        
        # Reset mock
        mock_subprocess.reset_mock()
        
        # Test macOS
        mock_platform.return_value = "Darwin"
        main_window._on_show_in_folder_requested(test_folder)
        mock_subprocess.run.assert_called_with(["open", test_folder])
        
        # Reset mock
        mock_subprocess.reset_mock()
        
        # Test Linux
        mock_platform.return_value = "Linux"
        main_window._on_show_in_folder_requested(test_folder)
        mock_subprocess.run.assert_called_with(["xdg-open", test_folder])
        
    def test_auto_hide_timer_integration(self, main_window, sample_successful_result):
        """Test auto-hide timer integration."""
        # Enable auto-hide
        main_window.results_panel.auto_hide_checkbox.setChecked(True)
        
        # Show success results
        main_window.show_processing_success(sample_successful_result)
        
        # Check timer is active
        assert main_window.results_panel._auto_hide_timer.isActive()
        
        # Manually trigger timer (simulate timeout)
        main_window.results_panel._auto_hide_success()
        
        # Results should be hidden
        assert not main_window.is_results_visible()
        
    def test_results_state_transitions(self, main_window, sample_successful_result, sample_batch_result_mixed):
        """Test state transitions between different result types."""
        # Start with no results
        assert not main_window.is_results_visible()
        
        # Show success results
        main_window.show_processing_success(sample_successful_result)
        assert main_window.is_results_visible()
        assert main_window.results_panel.tab_widget.currentIndex() == 0
        assert main_window.results_panel.success_group.isVisible()
        
        # Show error results (should switch to error display)
        main_window.show_processing_error("Test error", "processing")
        assert main_window.is_results_visible()
        assert main_window.results_panel.tab_widget.currentIndex() == 0
        assert main_window.results_panel.error_group.isVisible()
        assert not main_window.results_panel.success_group.isVisible()
        
        # Show batch results (should switch to batch tab)
        main_window.show_batch_results(sample_batch_result_mixed)
        assert main_window.is_results_visible()
        assert main_window.results_panel.tab_widget.currentIndex() == 1
        
        # Hide results
        main_window.hide_results()
        assert not main_window.is_results_visible()
        
    def test_error_recovery_suggestions_by_category(self, main_window):
        """Test error recovery suggestions for different categories."""
        categories = ["validation", "processing", "export", "system"]
        
        for category in categories:
            main_window.show_processing_error(f"Test {category} error", category)
            
            # Check that suggestions are provided
            assert main_window.results_panel.suggestions_list.count() > 0
            
            # Check that suggestions are category-appropriate
            suggestions_text = []
            for i in range(main_window.results_panel.suggestions_list.count()):
                item = main_window.results_panel.suggestions_list.item(i)
                suggestions_text.append(item.text().lower())
            
            combined_text = " ".join(suggestions_text)
            
            if category == "validation":
                assert any(word in combined_text for word in ["format", "corrupted", "convert"])
            elif category == "processing":
                assert any(word in combined_text for word in ["memory", "ram", "model", "resources"])
            elif category == "export":
                assert any(word in combined_text for word in ["permission", "disk", "directory"])
            elif category == "system":
                assert any(word in combined_text for word in ["restart", "system", "requirements"])
                
    @patch('src.ui.results_panel.QFileDialog')
    def test_batch_report_export_integration(self, mock_file_dialog, main_window, sample_batch_result_mixed):
        """Test batch report export integration."""
        # Show batch results
        main_window.show_batch_results(sample_batch_result_mixed)
        
        # Mock file dialog
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as temp_file:
            temp_path = temp_file.name
            
        mock_file_dialog.getSaveFileName.return_value = (temp_path, "")
        
        try:
            # Trigger export
            main_window.results_panel._export_batch_report()
            
            # Check file was created and contains expected content
            assert os.path.exists(temp_path)
            
            with open(temp_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            assert "BATCH PROCESSING SUMMARY REPORT" in content
            assert "Total Files Processed: 4" in content
            assert "Successful: 2" in content
            assert "Failed: 2" in content
            
        finally:
            # Clean up
            if os.path.exists(temp_path):
                os.unlink(temp_path)
                
    def test_results_panel_memory_management(self, main_window, sample_successful_result):
        """Test memory management and cleanup in results panel."""
        # Show and hide results multiple times
        for i in range(5):
            main_window.show_processing_success(sample_successful_result)
            assert main_window.is_results_visible()
            
            main_window.hide_results()
            assert not main_window.is_results_visible()
            
        # Check that panel still works correctly
        main_window.show_processing_success(sample_successful_result)
        assert main_window.is_results_visible()
        assert main_window.results_panel.files_list.count() == len(sample_successful_result.output_files)
        
    def test_concurrent_result_updates(self, main_window, sample_successful_result):
        """Test handling of concurrent result updates."""
        # Rapidly show different results
        main_window.show_processing_success(sample_successful_result)
        main_window.show_processing_error("Error 1", "validation")
        main_window.show_processing_error("Error 2", "processing")
        main_window.show_processing_success(sample_successful_result)
        
        # Final state should be success
        assert main_window.is_results_visible()
        assert main_window.results_panel.success_group.isVisible()
        assert not main_window.results_panel.error_group.isVisible()


class TestResultsErrorHandling:
    """Test error handling in results display."""
    
    def test_invalid_file_paths_handling(self, main_window):
        """Test handling of invalid file paths in results."""
        # Create result with non-existent files
        invalid_result = ProcessingResult(
            success=True,
            output_files=["/non/existent/file1.srt", "/non/existent/file2.ass"],
            processing_time=10.0
        )
        
        # Should not crash when displaying
        main_window.show_processing_success(invalid_result)
        assert main_window.is_results_visible()
        
        # File list should still show the files (even if they don't exist)
        assert main_window.results_panel.files_list.count() == 2
        
    def test_empty_results_handling(self, main_window):
        """Test handling of empty results."""
        # Create empty result
        empty_result = ProcessingResult(
            success=True,
            output_files=[],
            processing_time=0.0
        )
        
        # Should handle gracefully
        main_window.show_processing_success(empty_result)
        assert main_window.is_results_visible()
        assert main_window.results_panel.files_list.count() == 0
        
    def test_malformed_batch_results_handling(self, main_window):
        """Test handling of malformed batch results."""
        # Create batch result with missing data
        malformed_batch = BatchResult(
            total_files=1,
            successful_files=0,
            failed_files=1,
            processing_results=[],
            total_processing_time=0.0,
            file_reports=[]
        )
        
        # Should handle gracefully
        main_window.show_batch_results(malformed_batch)
        assert main_window.is_results_visible()
        assert main_window.results_panel.batch_tree.topLevelItemCount() == 0
        
    @patch('src.ui.results_panel.os.path.getsize')
    def test_file_size_error_handling(self, mock_getsize, main_window, sample_successful_result):
        """Test file size calculation error handling."""
        # Mock file size to raise an error
        mock_getsize.side_effect = OSError("Permission denied")
        
        # Should handle gracefully
        main_window.show_processing_success(sample_successful_result)
        assert main_window.is_results_visible()
        
        # File items should still be created
        assert main_window.results_panel.files_list.count() == len(sample_successful_result.output_files)


if __name__ == "__main__":
    pytest.main([__file__])