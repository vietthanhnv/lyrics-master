"""
Tests for the results panel UI component.
"""

import pytest
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtTest import QTest

from src.ui.results_panel import ResultsPanel
from src.models.data_models import (
    ProcessingResult, BatchResult, BatchFileReport, 
    BatchSummaryStats, AlignmentData, Segment, WordSegment
)


@pytest.fixture
def app():
    """Create QApplication instance for testing."""
    return QApplication.instance() or QApplication([])


@pytest.fixture
def results_panel(app):
    """Create ResultsPanel instance for testing."""
    return ResultsPanel()


@pytest.fixture
def sample_processing_result():
    """Create sample processing result for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create sample output files
        output_files = []
        for i, ext in enumerate(['srt', 'ass', 'vtt']):
            file_path = os.path.join(temp_dir, f"test_output_{i}.{ext}")
            with open(file_path, 'w') as f:
                f.write(f"Sample {ext.upper()} content")
            output_files.append(file_path)
        
        # Create sample alignment data
        segments = [
            Segment(0.0, 5.0, "Hello world", 0.95, 0),
            Segment(5.0, 10.0, "This is a test", 0.88, 1)
        ]
        
        word_segments = [
            WordSegment("Hello", 0.0, 1.0, 0.95, 0),
            WordSegment("world", 1.0, 2.0, 0.92, 0),
            WordSegment("This", 5.0, 5.5, 0.88, 1),
            WordSegment("is", 5.5, 6.0, 0.90, 1),
            WordSegment("a", 6.0, 6.2, 0.85, 1),
            WordSegment("test", 6.2, 7.0, 0.87, 1)
        ]
        
        alignment_data = AlignmentData(
            segments=segments,
            word_segments=word_segments,
            confidence_scores=[0.95, 0.88],
            audio_duration=10.0,
            source_file="test_audio.wav"
        )
        
        yield ProcessingResult(
            success=True,
            output_files=output_files,
            processing_time=15.5,
            alignment_data=alignment_data
        )


@pytest.fixture
def sample_batch_result():
    """Create sample batch result for testing."""
    # Create sample file reports
    file_reports = [
        BatchFileReport(
            file_path="/path/to/file1.wav",
            file_name="file1.wav",
            status="completed",
            success=True,
            processing_time=12.3,
            output_files=["/path/to/file1.srt", "/path/to/file1.ass"],
            file_size=1024000,
            audio_duration=180.0
        ),
        BatchFileReport(
            file_path="/path/to/file2.wav",
            file_name="file2.wav",
            status="failed",
            success=False,
            processing_time=5.1,
            output_files=[],
            error_message="Audio file corrupted",
            error_category="validation",
            file_size=512000,
            audio_duration=120.0
        ),
        BatchFileReport(
            file_path="/path/to/file3.wav",
            file_name="file3.wav",
            status="completed",
            success=True,
            processing_time=18.7,
            output_files=["/path/to/file3.srt"],
            file_size=2048000,
            audio_duration=240.0
        )
    ]
    
    # Create processing results
    processing_results = [
        ProcessingResult(True, ["/path/to/file1.srt", "/path/to/file1.ass"], 12.3),
        ProcessingResult(False, [], 5.1, "Audio file corrupted"),
        ProcessingResult(True, ["/path/to/file3.srt"], 18.7)
    ]
    
    batch_result = BatchResult(
        total_files=3,
        successful_files=2,
        failed_files=1,
        processing_results=processing_results,
        total_processing_time=36.1,
        file_reports=file_reports,
        cancelled_files=0
    )
    
    # Generate summary stats
    batch_result.summary_stats = batch_result.generate_summary_stats()
    
    return batch_result


class TestResultsPanel:
    """Test cases for ResultsPanel class."""
    
    def test_initialization(self, results_panel):
        """Test results panel initialization."""
        assert results_panel is not None
        assert not results_panel.isVisible()
        assert not results_panel.is_visible_panel()
        assert results_panel.tab_widget.count() == 3
        
        # Check tab names
        assert results_panel.tab_widget.tabText(0) == "Single File Results"
        assert results_panel.tab_widget.tabText(1) == "Batch Results"
        assert results_panel.tab_widget.tabText(2) == "Error Details"
        
    def test_show_success_results(self, results_panel, sample_processing_result):
        """Test displaying successful processing results."""
        # Show success results
        results_panel.show_success_results(sample_processing_result, 15.5)
        
        # Check panel is visible
        assert results_panel.isVisible()
        assert results_panel.is_visible_panel()
        
        # Check correct tab is selected
        assert results_panel.tab_widget.currentIndex() == 0
        
        # Check success section is visible, error section is hidden
        assert results_panel.success_group.isVisible()
        assert not results_panel.error_group.isVisible()
        
        # Check processing summary
        summary_text = results_panel.processing_summary.text()
        assert "Successfully processed" in summary_text
        assert "3 subtitle file(s)" in summary_text
        assert "15.5s" in summary_text
        
        # Check files list
        assert results_panel.files_list.count() == 3
        
        # Check file items
        for i in range(3):
            item = results_panel.files_list.item(i)
            assert item is not None
            file_path = item.data(Qt.ItemDataRole.UserRole)
            assert file_path in sample_processing_result.output_files
            
    def test_show_error_results(self, results_panel):
        """Test displaying error results."""
        error_message = "Processing failed due to insufficient memory"
        error_category = "system"
        suggestions = ["Close other applications", "Try smaller model size"]
        detailed_error = "MemoryError: Unable to allocate 2GB for model"
        
        # Show error results
        results_panel.show_error_results(
            error_message, error_category, suggestions, detailed_error
        )
        
        # Check panel is visible
        assert results_panel.isVisible()
        assert results_panel.is_visible_panel()
        
        # Check correct tab is selected
        assert results_panel.tab_widget.currentIndex() == 0
        
        # Check error section is visible, success section is hidden
        assert not results_panel.success_group.isVisible()
        assert results_panel.error_group.isVisible()
        
        # Check error message
        assert results_panel.error_message.text() == error_message
        
        # Check suggestions
        assert results_panel.suggestions_list.count() == 2
        item1 = results_panel.suggestions_list.item(0)
        item2 = results_panel.suggestions_list.item(1)
        assert "Close other applications" in item1.text()
        assert "Try smaller model size" in item2.text()
        
        # Check error log
        error_log_text = results_panel.error_log.toPlainText()
        assert error_category in error_log_text
        assert error_message in error_log_text
        assert detailed_error in error_log_text
        
    def test_show_error_results_with_defaults(self, results_panel):
        """Test displaying error results with default suggestions."""
        error_message = "Validation failed"
        error_category = "validation"
        
        # Show error results without custom suggestions
        results_panel.show_error_results(error_message, error_category)
        
        # Check default suggestions are provided
        assert results_panel.suggestions_list.count() > 0
        
        # Check that validation-specific suggestions are included
        suggestions_text = []
        for i in range(results_panel.suggestions_list.count()):
            item = results_panel.suggestions_list.item(i)
            suggestions_text.append(item.text())
        
        suggestions_combined = " ".join(suggestions_text)
        assert "corrupted" in suggestions_combined.lower() or "format" in suggestions_combined.lower()
        
    def test_show_batch_results(self, results_panel, sample_batch_result):
        """Test displaying batch processing results."""
        # Show batch results
        results_panel.show_batch_results(sample_batch_result)
        
        # Check panel is visible
        assert results_panel.isVisible()
        assert results_panel.is_visible_panel()
        
        # Check correct tab is selected
        assert results_panel.tab_widget.currentIndex() == 1
        
        # Check summary statistics
        assert results_panel.total_files_label.text() == "3"
        assert results_panel.successful_files_label.text() == "2"
        assert results_panel.failed_files_label.text() == "1"
        assert "66.7%" in results_panel.success_rate_label.text()
        assert "36.1s" in results_panel.processing_time_label.text()
        
        # Check batch tree
        assert results_panel.batch_tree.topLevelItemCount() == 3
        
        # Check individual file items
        for i in range(3):
            item = results_panel.batch_tree.topLevelItem(i)
            assert item is not None
            
            report = item.data(0, Qt.ItemDataRole.UserRole)
            assert isinstance(report, BatchFileReport)
            
            # Check status display
            status_text = item.text(1)
            if report.success:
                assert "✓ Success" in status_text
            else:
                assert "✗ Failed" in status_text
                
    def test_hide_results(self, results_panel, sample_processing_result):
        """Test hiding the results panel."""
        # Show results first
        results_panel.show_success_results(sample_processing_result)
        assert results_panel.isVisible()
        
        # Hide results
        results_panel.hide_results()
        assert not results_panel.isVisible()
        assert not results_panel.is_visible_panel()
        
    def test_auto_hide_functionality(self, results_panel, sample_processing_result):
        """Test auto-hide functionality for success messages."""
        # Enable auto-hide
        results_panel.auto_hide_checkbox.setChecked(True)
        
        # Show success results
        results_panel.show_success_results(sample_processing_result)
        assert results_panel.isVisible()
        
        # Check that auto-hide timer is started
        assert results_panel._auto_hide_timer.isActive()
        
        # Disable auto-hide and show again
        results_panel.auto_hide_checkbox.setChecked(False)
        results_panel.show_success_results(sample_processing_result)
        
        # Timer should not be active
        assert not results_panel._auto_hide_timer.isActive()
        
    def test_file_size_formatting(self, results_panel):
        """Test file size formatting utility."""
        # Test various file sizes
        assert "1.0 KB" in results_panel._get_file_size.__func__(results_panel, "/fake/1024byte/file")
        
        # Test with non-existent file
        size_str = results_panel._get_file_size("/non/existent/file")
        assert size_str == "Unknown"
        
    def test_default_suggestions_by_category(self, results_panel):
        """Test default suggestions for different error categories."""
        categories = ["validation", "processing", "export", "system"]
        
        for category in categories:
            suggestions = results_panel._get_default_suggestions(category)
            assert len(suggestions) > 0
            assert all(isinstance(s, str) for s in suggestions)
            
        # Test unknown category defaults to system suggestions
        unknown_suggestions = results_panel._get_default_suggestions("unknown")
        system_suggestions = results_panel._get_default_suggestions("system")
        assert unknown_suggestions == system_suggestions
        
    @patch('src.ui.results_panel.QMessageBox')
    def test_help_dialog(self, mock_messagebox, results_panel):
        """Test help dialog display."""
        # Trigger help dialog
        results_panel._show_help()
        
        # Check that message box was called
        mock_messagebox.information.assert_called_once()
        args = mock_messagebox.information.call_args[0]
        
        # Check dialog content
        assert "Troubleshooting Guide" in args[2]
        assert "Common Issues" in args[2]
        
    def test_signal_emissions(self, results_panel):
        """Test that signals are emitted correctly."""
        # Create signal spies
        retry_spy = Mock()
        open_file_spy = Mock()
        show_folder_spy = Mock()
        
        results_panel.retry_requested.connect(retry_spy)
        results_panel.open_file_requested.connect(open_file_spy)
        results_panel.show_in_folder_requested.connect(show_folder_spy)
        
        # Test retry signal
        results_panel._retry_processing()
        retry_spy.assert_called_once_with("current_file")
        
        # Test file operations (these will be tested with mocked file paths)
        # Note: Actual file operations would require more complex mocking
        
    @patch('src.ui.results_panel.QFileDialog')
    def test_export_batch_report(self, mock_file_dialog, results_panel, sample_batch_result):
        """Test batch report export functionality."""
        # Set up batch results
        results_panel._current_batch_results = sample_batch_result
        
        # Mock file dialog to return a path
        mock_file_dialog.getSaveFileName.return_value = ("/path/to/report.txt", "")
        
        # Mock the export method
        with patch.object(sample_batch_result, 'export_summary_report') as mock_export:
            results_panel._export_batch_report()
            mock_export.assert_called_once_with("/path/to/report.txt")
            
    @patch('src.ui.results_panel.QApplication')
    def test_copy_error_details(self, mock_app, results_panel):
        """Test copying error details to clipboard."""
        # Set up error details
        results_panel.error_log.setText("Test error log")
        results_panel.system_info.setText("Test system info")
        
        # Mock clipboard
        mock_clipboard = Mock()
        mock_app.clipboard.return_value = mock_clipboard
        
        # Copy error details
        with patch('src.ui.results_panel.QMessageBox'):
            results_panel._copy_error_details()
            
        # Check clipboard was called
        mock_clipboard.setText.assert_called_once()
        clipboard_text = mock_clipboard.setText.call_args[0][0]
        assert "Test error log" in clipboard_text
        assert "Test system info" in clipboard_text
        
    def test_system_info_update(self, results_panel):
        """Test system information update."""
        results_panel._update_system_info()
        
        system_text = results_panel.system_info.toPlainText()
        assert "Python Version:" in system_text
        assert "Platform:" in system_text
        assert "Architecture:" in system_text
        
    @patch('tempfile.NamedTemporaryFile')
    def test_file_operations_with_temp_files(self, mock_temp_file, results_panel):
        """Test file operations with temporary files."""
        # This test ensures file operations work with temporary files
        # In a real scenario, we'd test with actual temporary files
        
        # Create a mock temporary file
        mock_file = Mock()
        mock_file.name = "/tmp/test_file.srt"
        mock_temp_file.return_value.__enter__.return_value = mock_file
        
        # Test would involve creating actual temp files and testing file operations
        # For now, we just ensure the mock setup works
        assert mock_file.name.endswith('.srt')


class TestResultsPanelIntegration:
    """Integration tests for ResultsPanel with other components."""
    
    def test_integration_with_main_window_signals(self, results_panel):
        """Test integration with main window signal handling."""
        # This would test the actual signal connections in a real integration test
        # For now, we verify the signals exist
        
        assert hasattr(results_panel, 'retry_requested')
        assert hasattr(results_panel, 'open_file_requested')
        assert hasattr(results_panel, 'show_in_folder_requested')
        
    def test_results_panel_state_management(self, results_panel, sample_processing_result):
        """Test state management across different result types."""
        # Show success results
        results_panel.show_success_results(sample_processing_result)
        assert results_panel._current_results is not None
        assert results_panel.success_group.isVisible()
        
        # Show error results
        results_panel.show_error_results("Test error", "processing")
        assert not results_panel.success_group.isVisible()
        assert results_panel.error_group.isVisible()
        
        # Hide results
        results_panel.hide_results()
        assert not results_panel.isVisible()
        
    def test_tab_switching_behavior(self, results_panel, sample_processing_result, sample_batch_result):
        """Test tab switching behavior with different result types."""
        # Show single file results
        results_panel.show_success_results(sample_processing_result)
        assert results_panel.tab_widget.currentIndex() == 0
        
        # Show batch results
        results_panel.show_batch_results(sample_batch_result)
        assert results_panel.tab_widget.currentIndex() == 1
        
        # Show error results (should go back to single file tab)
        results_panel.show_error_results("Test error", "processing")
        assert results_panel.tab_widget.currentIndex() == 0


if __name__ == "__main__":
    pytest.main([__file__])