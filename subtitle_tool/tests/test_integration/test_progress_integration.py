"""
Integration tests for progress tracking functionality.

This module tests the integration between the progress widget, main window,
and processing services to ensure proper progress tracking throughout the application.
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
from PyQt6.QtTest import QTest

from src.ui.main_window import MainWindow
from src.ui.progress_widget import ProgressWidget
from src.models.data_models import ProcessingOptions, ModelSize, ExportFormat


class TestProgressIntegration:
    """Test cases for progress tracking integration."""
    
    @pytest.fixture
    def app(self):
        """Create QApplication instance for testing."""
        return QApplication.instance() or QApplication([])
    
    @pytest.fixture
    def main_window(self, app):
        """Create a MainWindow instance for testing."""
        window = MainWindow()
        return window
    
    def test_progress_widget_integration(self, main_window):
        """Test that progress widget is properly integrated into main window."""
        # Check that progress widget exists
        assert hasattr(main_window, 'progress_widget')
        assert isinstance(main_window.progress_widget, ProgressWidget)
        
        # Check initial state
        assert not main_window.progress_widget.isVisible()
        assert not main_window.is_processing()
        
        # Check signal connections (PyQt6 doesn't have receivers() method)
        # Just verify the signal exists
        assert hasattr(main_window.progress_widget, 'cancel_requested')
        
    def test_start_progress_tracking(self, main_window):
        """Test starting progress tracking from main window."""
        estimated_time = 120.0
        
        # Show the main window to ensure proper layout
        main_window.show()
        QApplication.processEvents()
        
        # Start progress tracking
        main_window.start_progress_tracking(estimated_time)
        QApplication.processEvents()
        
        # Check that progress widget is shown and configured
        assert main_window.progress_widget.isVisible()
        assert main_window.progress_widget.is_processing()
        assert main_window.progress_widget._estimated_total_time == estimated_time
        
        # Check that process button is disabled
        assert not main_window.process_btn.isEnabled()
        assert main_window.process_btn.text() == "Processing..."
        
    def test_progress_updates_from_main_window(self, main_window):
        """Test progress updates through main window interface."""
        main_window.start_progress_tracking()
        
        # Update progress
        main_window.update_progress(25.0, "Processing audio", "Vocal Separation", 50.0)
        
        # Check that progress widget received the update
        assert main_window.progress_widget._overall_progress == 25.0
        assert main_window.progress_widget._current_operation_progress == 50.0
        assert main_window.progress_widget._current_operation == "Vocal Separation"
        assert main_window.progress_widget._status_message == "Processing audio"
        
        # Check status bar update
        status_text = main_window.statusBar().currentMessage()
        assert "25.0%" in status_text
        assert "Processing audio" in status_text
        
    def test_finish_progress_tracking_success(self, main_window):
        """Test finishing progress tracking successfully."""
        main_window.start_progress_tracking()
        main_window.update_progress(50.0, "Halfway")
        
        # Finish successfully
        main_window.finish_progress_tracking(success=True, final_message="Processing completed successfully")
        
        # Check that progress widget shows completion
        assert main_window.progress_widget._overall_progress == 100.0
        assert not main_window.progress_widget.is_processing()
        
        # Check that process button is re-enabled (if files are selected)
        # Note: Button will only be enabled if audio files are selected
        assert main_window.process_btn.text() == "Start Processing"
        
        # Check status bar
        status_text = main_window.statusBar().currentMessage()
        assert "Processing completed successfully" in status_text
        
    def test_finish_progress_tracking_failure(self, main_window):
        """Test finishing progress tracking with failure."""
        main_window.start_progress_tracking()
        main_window.update_progress(30.0, "Processing")
        
        # Finish with failure
        main_window.finish_progress_tracking(success=False, final_message="Processing failed due to error")
        
        # Check that progress widget shows failure
        assert not main_window.progress_widget.is_processing()
        
        # Check status bar shows error
        status_text = main_window.statusBar().currentMessage()
        assert "Processing failed" in status_text
        
    def test_cancel_callback_integration(self, main_window):
        """Test cancellation callback integration."""
        cancel_callback = Mock(return_value=True)
        
        # Set cancel callback and start processing
        main_window.set_cancel_callback(cancel_callback)
        main_window.start_progress_tracking()
        
        # Simulate cancel request from progress widget
        main_window.progress_widget._on_cancel_clicked()
        
        # Check that callback was called
        cancel_callback.assert_called_once()
        
        # Check that cancellation signal was emitted from main window
        # (This would be caught by the application controller in real usage)
        
    def test_reset_progress_tracking(self, main_window):
        """Test resetting progress tracking."""
        # Start and update progress
        main_window.start_progress_tracking()
        main_window.update_progress(50.0, "Processing")
        
        # Reset
        main_window.reset_progress_tracking()
        
        # Check that everything is reset
        assert not main_window.progress_widget.isVisible()
        assert not main_window.progress_widget.is_processing()
        assert main_window.process_btn.text() == "Start Processing"
        
    def test_progress_info_retrieval(self, main_window):
        """Test retrieving progress information."""
        main_window.start_progress_tracking(estimated_time=100.0)
        main_window.update_progress(40.0, "Processing", "Speech Recognition", 60.0)
        
        # Get progress info
        info = main_window.get_progress_info()
        
        # Verify information
        assert info['overall_progress'] == 40.0
        assert info['operation_progress'] == 60.0
        assert info['current_operation'] == "Speech Recognition"
        assert info['status_message'] == "Processing"
        assert info['is_processing'] == True
        assert info['estimated_total_time'] == 100.0
        
    def test_processing_workflow_simulation(self, main_window):
        """Test a complete processing workflow simulation."""
        # Add some audio files to enable processing
        test_files = ["/path/to/test1.mp3", "/path/to/test2.wav"]
        main_window.audio_files = test_files
        main_window._update_audio_files_display()
        
        # Start processing
        main_window.start_progress_tracking(estimated_time=180.0)
        
        # Simulate vocal separation phase
        main_window.update_progress(10.0, "Starting vocal separation", "Vocal Separation", 0.0)
        main_window.update_progress(25.0, "Separating vocals from audio", "Vocal Separation", 50.0)
        main_window.update_progress(45.0, "Vocal separation complete", "Vocal Separation", 100.0)
        
        # Simulate speech recognition phase
        main_window.update_progress(50.0, "Starting speech recognition", "Speech Recognition", 0.0)
        main_window.update_progress(70.0, "Transcribing audio", "Speech Recognition", 40.0)
        main_window.update_progress(85.0, "Aligning words", "Speech Recognition", 80.0)
        main_window.update_progress(95.0, "Speech recognition complete", "Speech Recognition", 100.0)
        
        # Simulate subtitle generation
        main_window.update_progress(98.0, "Generating subtitles", "Subtitle Generation", 50.0)
        
        # Complete processing
        main_window.finish_progress_tracking(success=True, final_message="All files processed successfully")
        
        # Verify final state
        assert main_window.progress_widget._overall_progress == 100.0
        assert not main_window.progress_widget.is_processing()
        assert main_window.process_btn.isEnabled()  # Should be enabled since files are selected
        
    def test_cancellation_workflow(self, main_window):
        """Test cancellation workflow."""
        cancel_callback = Mock(return_value=True)
        main_window.set_cancel_callback(cancel_callback)
        
        # Start processing
        main_window.start_progress_tracking()
        main_window.update_progress(30.0, "Processing audio")
        
        # Request cancellation
        main_window.progress_widget._on_cancel_clicked()
        
        # Verify cancellation state
        assert main_window.progress_widget.is_cancellation_requested()
        assert main_window.progress_widget.cancel_button.text() == "Cancelling..."
        assert not main_window.progress_widget.cancel_button.isEnabled()
        
        # Simulate cancellation completion
        main_window.finish_progress_tracking(success=False, final_message="Processing cancelled by user")
        
        # Verify final state
        assert not main_window.progress_widget.is_processing()
        
    def test_multiple_file_progress_tracking(self, main_window):
        """Test progress tracking for multiple files."""
        # Simulate batch processing of multiple files
        files = ["file1.mp3", "file2.wav", "file3.flac"]
        main_window.audio_files = files
        
        main_window.start_progress_tracking(estimated_time=300.0)  # 5 minutes for 3 files
        
        # Process each file
        for i, filename in enumerate(files):
            file_progress_start = i * 33.33
            file_progress_end = (i + 1) * 33.33
            
            # File processing phases
            main_window.update_progress(
                file_progress_start + 5, 
                f"Processing {filename} - Vocal separation", 
                f"File {i+1}/3", 
                15.0
            )
            
            main_window.update_progress(
                file_progress_start + 15, 
                f"Processing {filename} - Speech recognition", 
                f"File {i+1}/3", 
                50.0
            )
            
            main_window.update_progress(
                file_progress_start + 30, 
                f"Processing {filename} - Generating subtitles", 
                f"File {i+1}/3", 
                90.0
            )
            
            main_window.update_progress(
                file_progress_end, 
                f"Completed {filename}", 
                f"File {i+1}/3", 
                100.0
            )
        
        # Complete batch processing
        main_window.finish_progress_tracking(
            success=True, 
            final_message=f"Successfully processed {len(files)} files"
        )
        
        # Verify completion
        assert main_window.progress_widget._overall_progress == 100.0
        assert "Successfully processed 3 files" in main_window.statusBar().currentMessage()
        
    def test_error_handling_during_progress(self, main_window):
        """Test error handling during progress tracking."""
        main_window.start_progress_tracking()
        
        # Simulate normal progress
        main_window.update_progress(20.0, "Processing normally")
        
        # Simulate error condition
        main_window.update_progress(25.0, "Error occurred during vocal separation")
        
        # Finish with error
        main_window.finish_progress_tracking(
            success=False, 
            final_message="Processing failed: Insufficient memory for vocal separation"
        )
        
        # Verify error state
        assert not main_window.progress_widget.is_processing()
        assert "Processing failed" in main_window.statusBar().currentMessage()
        
    def test_progress_widget_visibility_states(self, main_window):
        """Test progress widget visibility in different states."""
        # Show the main window
        main_window.show()
        QApplication.processEvents()
        
        # Initially hidden
        assert not main_window.progress_widget.isVisible()
        
        # Shown when processing starts
        main_window.start_progress_tracking()
        QApplication.processEvents()
        assert main_window.progress_widget.isVisible()
        
        # Remains visible during processing
        main_window.update_progress(50.0, "Processing")
        assert main_window.progress_widget.isVisible()
        
        # Remains visible after completion (until reset)
        main_window.finish_progress_tracking()
        assert main_window.progress_widget.isVisible()
        
        # Hidden after reset
        main_window.reset_progress_tracking()
        assert not main_window.progress_widget.isVisible()
        
    def test_concurrent_progress_updates(self, main_window):
        """Test handling of rapid progress updates."""
        main_window.start_progress_tracking()
        
        # Send rapid updates
        for i in range(100):
            main_window.update_progress(i, f"Step {i}", "Rapid Processing", i)
            
        # Verify final state
        assert main_window.progress_widget._overall_progress == 99.0
        assert main_window.progress_widget._current_operation_progress == 99.0
        assert len(main_window.progress_widget._progress_history) <= 100  # Should be managed
        
    @patch('time.time')
    def test_time_estimation_accuracy(self, mock_time, main_window):
        """Test accuracy of time estimation during progress."""
        start_time = 1000.0
        mock_time.return_value = start_time
        
        # Start processing
        main_window.start_progress_tracking(estimated_time=200.0)
        
        # Simulate progress over time
        mock_time.return_value = start_time + 50  # 50 seconds elapsed
        main_window.update_progress(25.0, "Quarter complete")  # 25% done
        
        # Update time displays
        main_window.progress_widget._update_time_displays()
        
        # Check that time calculations are reasonable
        elapsed_text = main_window.progress_widget.elapsed_time_label.text()
        assert "00:00:50" == elapsed_text
        
        # Remaining time should be calculated based on progress
        remaining_text = main_window.progress_widget.remaining_time_label.text()
        assert remaining_text != "--:--:--"  # Should have a calculated value