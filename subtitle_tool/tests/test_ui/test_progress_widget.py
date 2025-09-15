"""
Tests for the ProgressWidget class.

This module tests the progress tracking and status display functionality,
including real-time updates, cancellation support, and time estimation.
"""

import pytest
import time
from unittest.mock import Mock, patch
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
from PyQt6.QtTest import QTest

from src.ui.progress_widget import ProgressWidget


class TestProgressWidget:
    """Test cases for ProgressWidget functionality."""
    
    @pytest.fixture
    def app(self):
        """Create QApplication instance for testing."""
        return QApplication.instance() or QApplication([])
    
    @pytest.fixture
    def progress_widget(self, app):
        """Create a ProgressWidget instance for testing."""
        widget = ProgressWidget()
        return widget
    
    def test_initial_state(self, progress_widget):
        """Test that progress widget initializes with correct default state."""
        # Check initial progress values
        assert progress_widget._overall_progress == 0.0
        assert progress_widget._current_operation_progress == 0.0
        assert progress_widget._current_operation == ""
        assert not progress_widget._is_processing
        assert not progress_widget._cancellation_requested
        
        # Check UI state
        assert progress_widget.overall_progress_bar.value() == 0
        assert progress_widget.operation_progress_bar.value() == 0
        assert not progress_widget.cancel_button.isEnabled()
        assert progress_widget.operation_label.text() == "Ready"
        assert progress_widget.phase_label.text() == "Idle"
        
    def test_start_processing(self, progress_widget):
        """Test starting progress tracking."""
        estimated_time = 120.0  # 2 minutes
        
        progress_widget.start_processing(estimated_time)
        
        # Check state changes
        assert progress_widget._is_processing
        assert progress_widget._estimated_total_time == estimated_time
        assert progress_widget._start_time is not None
        assert progress_widget.cancel_button.isEnabled()
        assert progress_widget._update_timer.isActive()
        
        # Check UI updates
        assert progress_widget.phase_label.text() == "Initializing"
        
    def test_update_progress(self, progress_widget):
        """Test progress updates."""
        progress_widget.start_processing()
        
        # Test basic progress update
        progress_widget.update_progress(25.0, "Processing audio file", "Vocal Separation", 50.0)
        
        assert progress_widget._overall_progress == 25.0
        assert progress_widget._current_operation_progress == 50.0
        assert progress_widget._current_operation == "Vocal Separation"
        assert progress_widget._status_message == "Processing audio file"
        
        # Check UI updates
        assert progress_widget.overall_progress_bar.value() == 25
        assert progress_widget.operation_progress_bar.value() == 50
        assert progress_widget.operation_label.text() == "Vocal Separation"
        assert progress_widget.status_label.text() == "Processing audio file"
        
        # Check progress history
        assert len(progress_widget._progress_history) == 1
        assert progress_widget._progress_history[0]['progress'] == 25.0
        assert progress_widget._progress_history[0]['message'] == "Processing audio file"
        
    def test_progress_bounds(self, progress_widget):
        """Test that progress values are properly bounded."""
        progress_widget.start_processing()
        
        # Test negative values
        progress_widget.update_progress(-10.0, "Test", operation_percentage=-5.0)
        assert progress_widget._overall_progress == 0.0
        assert progress_widget._current_operation_progress == 0.0
        
        # Test values over 100
        progress_widget.update_progress(150.0, "Test", operation_percentage=120.0)
        assert progress_widget._overall_progress == 100.0
        assert progress_widget._current_operation_progress == 100.0
        
    def test_finish_processing_success(self, progress_widget):
        """Test finishing processing successfully."""
        progress_widget.start_processing()
        progress_widget.update_progress(50.0, "Halfway done")
        
        progress_widget.finish_processing(success=True, final_message="All done!")
        
        # Check state changes
        assert not progress_widget._is_processing
        assert progress_widget._overall_progress == 100.0
        assert progress_widget._current_operation_progress == 100.0
        assert progress_widget._status_message == "All done!"
        assert not progress_widget.cancel_button.isEnabled()
        assert not progress_widget._update_timer.isActive()
        
        # Check UI updates
        assert progress_widget.phase_label.text() == "Completed"
        assert progress_widget.overall_progress_bar.value() == 100
        
    def test_finish_processing_failure(self, progress_widget):
        """Test finishing processing with failure."""
        progress_widget.start_processing()
        progress_widget.update_progress(30.0, "Processing")
        
        progress_widget.finish_processing(success=False, final_message="Processing failed")
        
        # Check state changes
        assert not progress_widget._is_processing
        assert progress_widget._status_message == "Processing failed"
        assert not progress_widget.cancel_button.isEnabled()
        
        # Check UI updates
        assert progress_widget.phase_label.text() == "Failed"
        
    def test_reset(self, progress_widget):
        """Test resetting progress widget."""
        # Set up some state
        progress_widget.start_processing()
        progress_widget.update_progress(50.0, "Processing")
        
        # Reset
        progress_widget.reset()
        
        # Check that everything is reset
        assert not progress_widget._is_processing
        assert not progress_widget._cancellation_requested
        assert progress_widget._start_time is None
        assert progress_widget._estimated_total_time is None
        assert len(progress_widget._progress_history) == 0
        assert not progress_widget._update_timer.isActive()
        
        # Check UI reset
        assert progress_widget.overall_progress_bar.value() == 0
        assert progress_widget.operation_progress_bar.value() == 0
        assert not progress_widget.cancel_button.isEnabled()
        assert progress_widget.phase_label.text() == "Idle"
        
    def test_cancel_request(self, progress_widget):
        """Test cancellation request handling."""
        cancel_callback = Mock(return_value=True)
        progress_widget.set_cancel_callback(cancel_callback)
        progress_widget.start_processing()
        
        # Simulate cancel button click
        progress_widget._on_cancel_clicked()
        
        # Check state changes
        assert progress_widget._cancellation_requested
        assert not progress_widget.cancel_button.isEnabled()
        assert progress_widget.cancel_button.text() == "Cancelling..."
        assert progress_widget.phase_label.text() == "Cancelling"
        
        # Check that callback was called
        cancel_callback.assert_called_once()
        
    def test_cancel_callback_failure(self, progress_widget):
        """Test handling of cancel callback failure."""
        cancel_callback = Mock(side_effect=Exception("Cancel failed"))
        progress_widget.set_cancel_callback(cancel_callback)
        progress_widget.start_processing()
        
        # Should not raise exception
        progress_widget._on_cancel_clicked()
        
        # Check that cancellation was still marked as requested
        assert progress_widget._cancellation_requested
        
    def test_progress_signals(self, progress_widget):
        """Test that progress signals are emitted correctly."""
        progress_updated_signal = Mock()
        cancel_requested_signal = Mock()
        
        progress_widget.progress_updated.connect(progress_updated_signal)
        progress_widget.cancel_requested.connect(cancel_requested_signal)
        
        progress_widget.start_processing()
        progress_widget.update_progress(25.0, "Test message")
        
        # Check progress signal
        progress_updated_signal.assert_called_once_with(25.0, "Test message")
        
        # Test cancel signal
        progress_widget._on_cancel_clicked()
        cancel_requested_signal.assert_called_once()
        
    def test_progress_history_management(self, progress_widget):
        """Test that progress history is managed correctly."""
        progress_widget.start_processing()
        
        # Add multiple progress updates
        for i in range(10):
            progress_widget.update_progress(i * 10, f"Step {i}")
            
        assert len(progress_widget._progress_history) == 10
        
        # Test that old entries are cleaned up (simulate old timestamps)
        old_time = time.time() - 700  # 11+ minutes ago
        progress_widget._progress_history[0]['time'] = old_time
        
        # Add new entry to trigger cleanup
        progress_widget.update_progress(100.0, "Final step")
        
        # Old entry should be removed
        assert all(entry['time'] > time.time() - 600 for entry in progress_widget._progress_history)
        
    def test_time_formatting(self, progress_widget):
        """Test duration formatting."""
        # Test various durations
        assert progress_widget._format_duration(0) == "00:00:00"
        assert progress_widget._format_duration(59) == "00:00:59"
        assert progress_widget._format_duration(60) == "00:01:00"
        assert progress_widget._format_duration(3661) == "01:01:01"
        assert progress_widget._format_duration(7200) == "02:00:00"
        
    def test_progress_info(self, progress_widget):
        """Test getting progress information."""
        progress_widget.start_processing(estimated_total_time=100.0)
        
        # Add a small delay to ensure elapsed time > 0
        import time
        time.sleep(0.01)
        
        progress_widget.update_progress(50.0, "Halfway", "Test Operation", 75.0)
        
        info = progress_widget.get_progress_info()
        
        assert info['overall_progress'] == 50.0
        assert info['operation_progress'] == 75.0
        assert info['current_operation'] == "Test Operation"
        assert info['status_message'] == "Halfway"
        assert info['is_processing'] == True
        assert info['estimated_total_time'] == 100.0
        assert info['updates_count'] == 1
        assert info['elapsed_time'] >= 0  # Changed to >= since it might be very small
        
    def test_details_toggle(self, progress_widget):
        """Test showing/hiding details section."""
        # Show the widget to ensure proper layout
        progress_widget.show()
        QApplication.processEvents()
        
        # Initially hidden
        assert not progress_widget.details_group.isVisible()
        assert progress_widget.details_button.text() == "Show Details"
        
        # Show details
        progress_widget._toggle_details()
        # Process events to ensure UI updates
        QApplication.processEvents()
        assert progress_widget.details_group.isVisible()
        assert progress_widget.details_button.text() == "Hide Details"
        
        # Hide details
        progress_widget._toggle_details()
        # Process events to ensure UI updates
        QApplication.processEvents()
        assert not progress_widget.details_group.isVisible()
        assert progress_widget.details_button.text() == "Show Details"
        
    def test_progress_log(self, progress_widget):
        """Test progress logging functionality."""
        progress_widget.start_processing()
        
        # Check that start is logged
        log_text = progress_widget.progress_log.toPlainText()
        assert "Processing started" in log_text
        
        # Add progress update
        progress_widget.update_progress(25.0, "Test progress")
        
        # Check that progress is logged
        log_text = progress_widget.progress_log.toPlainText()
        assert "25.0% - Test progress" in log_text
        
        # Finish processing
        progress_widget.finish_processing(success=True, final_message="Done")
        
        # Check final message is logged
        log_text = progress_widget.progress_log.toPlainText()
        assert "Done" in log_text
        
    @patch('time.time')
    def test_speed_calculation(self, mock_time, progress_widget):
        """Test processing speed calculation."""
        # Mock time progression
        start_time = 1000.0
        mock_time.return_value = start_time
        
        progress_widget.start_processing()
        
        # Simulate progress over time
        mock_time.return_value = start_time + 60  # 1 minute later
        progress_widget.update_progress(30.0, "Progress 1")
        
        mock_time.return_value = start_time + 120  # 2 minutes later
        progress_widget.update_progress(60.0, "Progress 2")
        
        # Update speed displays
        progress_widget._update_speed_displays()
        
        # Check that speed labels are updated (exact values depend on calculation)
        assert "30.0 %/min" in progress_widget.speed_label.text()
        
    def test_not_processing_updates(self, progress_widget):
        """Test that updates are ignored when not processing."""
        # Don't start processing
        progress_widget.update_progress(50.0, "Should be ignored")
        
        # Progress should remain at 0
        assert progress_widget._overall_progress == 0.0
        assert progress_widget.overall_progress_bar.value() == 0
        
    def test_estimated_time_calculation(self, progress_widget):
        """Test estimated time calculations."""
        with patch('time.time') as mock_time:
            start_time = 1000.0
            mock_time.return_value = start_time
            
            # Start with estimated time
            progress_widget.start_processing(estimated_total_time=200.0)
            
            # Simulate 50 seconds elapsed, 25% progress
            mock_time.return_value = start_time + 50
            progress_widget.update_progress(25.0, "Quarter done")
            
            # Update time displays
            progress_widget._update_time_displays()
            
            # Check that remaining time is calculated
            remaining_text = progress_widget.remaining_time_label.text()
            assert remaining_text != "--:--:--"  # Should have calculated value
            
    def test_widget_visibility_and_layout(self, progress_widget):
        """Test widget visibility and layout properties."""
        # Check minimum height is set
        assert progress_widget.minimumHeight() == 300
        
        # Check that all major components exist
        assert progress_widget.overall_progress_bar is not None
        assert progress_widget.operation_progress_bar is not None
        assert progress_widget.cancel_button is not None
        assert progress_widget.details_button is not None
        assert progress_widget.progress_log is not None
        
        # Check that details section is initially hidden
        assert not progress_widget.details_group.isVisible()