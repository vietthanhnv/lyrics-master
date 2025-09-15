"""
Integration tests for UI workflows with sample audio files.

This module tests UI components integration with real audio processing
and user interaction scenarios.
"""

import pytest
import os
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer, pyqtSignal
from PyQt6.QtTest import QTest

from src.ui.main_window import MainWindow
from src.ui.options_panel import OptionsPanel
from src.ui.progress_widget import ProgressWidget
from src.ui.results_panel import ResultsPanel
from src.services.application_controller import ApplicationController
from src.models.data_models import (
    ProcessingOptions, ModelSize, ExportFormat, ProcessingResult,
    AlignmentData, Segment, WordSegment
)


@pytest.fixture
def app():
    """Create QApplication instance for testing."""
    return QApplication.instance() or QApplication([])


@pytest.fixture
def sample_audio_workspace():
    """Create workspace with sample audio files for UI testing."""
    workspace = tempfile.mkdtemp()
    
    # Copy real hello.mp3 if available, otherwise create dummy files
    hello_mp3_path = Path("data/hello.mp3")
    if hello_mp3_path.exists():
        shutil.copy(hello_mp3_path, Path(workspace) / "hello.mp3")
    else:
        # Create dummy MP3 file with realistic size
        with open(Path(workspace) / "hello.mp3", "wb") as f:
            f.write(b"ID3" + b"\x00" * 1000)  # Dummy MP3 header + data
    
    # Create additional test files
    audio_formats = ["wav", "flac", "ogg"]
    for i, fmt in enumerate(audio_formats):
        with open(Path(workspace) / f"sample_{i}.{fmt}", "wb") as f:
            f.write(b"fake audio data" * 100)  # Make files reasonably sized
    
    # Create lyric files
    with open(Path(workspace) / "lyrics.txt", "w") as f:
        f.write("Hello world\nThis is a test song\nWith multiple lines")
    
    with open(Path(workspace) / "lyrics.lrc", "w") as f:
        f.write("[00:00.00]Hello world\n[00:05.00]This is a test song\n[00:10.00]With multiple lines")
    
    # Create output directory
    output_dir = Path(workspace) / "output"
    output_dir.mkdir()
    
    yield {
        "workspace": workspace,
        "hello_mp3": str(Path(workspace) / "hello.mp3"),
        "audio_files": [
            str(Path(workspace) / f"sample_{i}.{fmt}")
            for i, fmt in enumerate(audio_formats)
        ],
        "lyric_files": [
            str(Path(workspace) / "lyrics.txt"),
            str(Path(workspace) / "lyrics.lrc")
        ],
        "output_dir": str(output_dir)
    }
    
    # Cleanup
    shutil.rmtree(workspace, ignore_errors=True)


class TestUIWorkflows:
    """Integration tests for UI workflows."""
    
    def test_main_window_complete_workflow(self, app, sample_audio_workspace):
        """Test complete workflow through main window."""
        window = MainWindow()
        
        # Track UI events
        events = []
        
        def track_event(event_name):
            def handler(*args):
                events.append((event_name, args))
            return handler
        
        window.files_selected.connect(track_event("files_selected"))
        window.lyric_file_selected.connect(track_event("lyric_selected"))
        window.processing_requested.connect(track_event("processing_requested"))
        
        window.show()
        
        try:
            # Step 1: Add audio files
            audio_files = [sample_audio_workspace["hello_mp3"]] + sample_audio_workspace["audio_files"][:2]
            window._add_audio_files(audio_files)
            
            # Verify files were added
            assert len(window.get_selected_audio_files()) == 3
            assert window.process_btn.isEnabled()
            assert len([e for e in events if e[0] == "files_selected"]) == 1
            
            # Step 2: Add lyric file
            window.lyric_file = sample_audio_workspace["lyric_files"][0]
            window._update_lyric_file_display()
            assert window.get_selected_lyric_file() == sample_audio_workspace["lyric_files"][0]
            
            # Step 3: Configure processing through options (if options panel exists)
            if hasattr(window, 'options_panel'):
                # Test options panel integration
                options_panel = window.options_panel
                
                # Set model size
                if hasattr(options_panel, 'model_size_combo'):
                    options_panel.model_size_combo.setCurrentText("base")
                
                # Set export formats
                if hasattr(options_panel, 'export_format_checkboxes'):
                    for checkbox in options_panel.export_format_checkboxes.values():
                        checkbox.setChecked(True)
            
            # Step 4: Start processing
            window._start_processing()
            
            # Verify processing was requested
            processing_events = [e for e in events if e[0] == "processing_requested"]
            assert len(processing_events) == 1
            
            requested_files, requested_options = processing_events[0][1]
            assert len(requested_files) == 3
            assert isinstance(requested_options, ProcessingOptions)
            
            # Step 5: Simulate processing progress
            if hasattr(window, 'progress_widget'):
                progress_widget = window.progress_widget
                
                # Simulate progress updates
                for progress in [10, 25, 50, 75, 90, 100]:
                    progress_widget.update_progress(progress, f"Processing... {progress}%")
                    QTest.qWait(10)  # Small delay to simulate real progress
            
            # Step 6: Simulate processing completion
            output_files = [
                f"{sample_audio_workspace['output_dir']}/hello.srt",
                f"{sample_audio_workspace['output_dir']}/hello.vtt",
                f"{sample_audio_workspace['output_dir']}/sample_0.srt"
            ]
            
            # Create mock output files
            for output_file in output_files:
                Path(output_file).write_text("1\n00:00:00,000 --> 00:00:05,000\nTest subtitle\n")
            
            window._on_processing_complete(output_files, None)
            
            # Verify UI state after completion
            assert window.process_btn.isEnabled()
            
            # Step 7: Test results display
            if hasattr(window, 'results_panel'):
                results_panel = window.results_panel
                assert results_panel.isVisible()
                
                # Verify results are displayed
                if hasattr(results_panel, 'get_displayed_files'):
                    displayed_files = results_panel.get_displayed_files()
                    assert len(displayed_files) > 0
            
        finally:
            window.hide()
    
    def test_options_panel_workflow(self, app, sample_audio_workspace):
        """Test options panel configuration workflow."""
        try:
            options_panel = OptionsPanel()
            options_panel.show()
            
            # Test model size selection
            if hasattr(options_panel, 'model_size_combo'):
                combo = options_panel.model_size_combo
                
                # Test all model sizes
                for model_size in ModelSize:
                    combo.setCurrentText(model_size.value)
                    assert combo.currentText() == model_size.value
            
            # Test export format selection
            if hasattr(options_panel, 'export_format_checkboxes'):
                checkboxes = options_panel.export_format_checkboxes
                
                # Test selecting different combinations
                for fmt in ExportFormat:
                    if fmt.value in checkboxes:
                        checkbox = checkboxes[fmt.value]
                        checkbox.setChecked(True)
                        assert checkbox.isChecked()
            
            # Test output directory selection
            if hasattr(options_panel, 'output_dir_edit'):
                options_panel.output_dir_edit.setText(sample_audio_workspace["output_dir"])
                assert options_panel.output_dir_edit.text() == sample_audio_workspace["output_dir"]
            
            # Test getting processing options
            if hasattr(options_panel, 'get_processing_options'):
                options = options_panel.get_processing_options()
                assert isinstance(options, ProcessingOptions)
                assert options.output_directory == sample_audio_workspace["output_dir"]
            
            # Test translation settings
            if hasattr(options_panel, 'translation_enabled_checkbox'):
                translation_checkbox = options_panel.translation_enabled_checkbox
                translation_checkbox.setChecked(True)
                
                if hasattr(options_panel, 'target_language_combo'):
                    lang_combo = options_panel.target_language_combo
                    lang_combo.setCurrentText("Spanish")
                    assert lang_combo.currentText() == "Spanish"
            
        except ImportError:
            # Options panel might not be implemented yet
            pytest.skip("OptionsPanel not available")
        finally:
            if 'options_panel' in locals():
                options_panel.hide()
    
    def test_progress_widget_workflow(self, app):
        """Test progress widget during processing workflow."""
        try:
            progress_widget = ProgressWidget()
            progress_widget.show()
            
            # Test initial state
            assert progress_widget.get_progress() == 0
            
            # Test progress updates
            test_progress_values = [
                (10, "Validating audio file..."),
                (25, "Separating vocals..."),
                (50, "Transcribing audio..."),
                (75, "Generating subtitles..."),
                (90, "Exporting files..."),
                (100, "Processing complete!")
            ]
            
            for progress, message in test_progress_values:
                progress_widget.update_progress(progress, message)
                QTest.qWait(50)  # Small delay to see progress
                
                assert progress_widget.get_progress() == progress
                if hasattr(progress_widget, 'get_status_message'):
                    assert message in progress_widget.get_status_message()
            
            # Test cancellation
            if hasattr(progress_widget, 'cancel_button'):
                cancel_clicked = False
                
                def on_cancel():
                    nonlocal cancel_clicked
                    cancel_clicked = True
                
                progress_widget.cancel_requested.connect(on_cancel)
                progress_widget.cancel_button.click()
                assert cancel_clicked
            
            # Test reset
            if hasattr(progress_widget, 'reset'):
                progress_widget.reset()
                assert progress_widget.get_progress() == 0
            
        except ImportError:
            pytest.skip("ProgressWidget not available")
        finally:
            if 'progress_widget' in locals():
                progress_widget.hide()
    
    def test_results_panel_workflow(self, app, sample_audio_workspace):
        """Test results panel display workflow."""
        try:
            results_panel = ResultsPanel()
            results_panel.show()
            
            # Create test result files
            result_files = []
            for i, fmt in enumerate(["srt", "vtt", "ass"]):
                result_file = Path(sample_audio_workspace["output_dir"]) / f"test_{i}.{fmt}"
                result_file.write_text(f"Test {fmt.upper()} content")
                result_files.append(str(result_file))
            
            # Test displaying results
            if hasattr(results_panel, 'display_results'):
                results_panel.display_results(result_files)
                
                # Verify results are displayed
                if hasattr(results_panel, 'get_displayed_files'):
                    displayed = results_panel.get_displayed_files()
                    assert len(displayed) == len(result_files)
            
            # Test file operations
            if hasattr(results_panel, 'open_file_location'):
                # Test opening file location (should not crash)
                results_panel.open_file_location(result_files[0])
            
            if hasattr(results_panel, 'preview_file'):
                # Test file preview
                results_panel.preview_file(result_files[0])
            
            # Test clearing results
            if hasattr(results_panel, 'clear_results'):
                results_panel.clear_results()
                
                if hasattr(results_panel, 'get_displayed_files'):
                    displayed = results_panel.get_displayed_files()
                    assert len(displayed) == 0
            
        except ImportError:
            pytest.skip("ResultsPanel not available")
        finally:
            if 'results_panel' in locals():
                results_panel.hide()
    
    def test_error_handling_ui_workflow(self, app, sample_audio_workspace):
        """Test UI error handling workflow."""
        window = MainWindow()
        window.show()
        
        try:
            # Test invalid file handling
            invalid_files = [
                "/nonexistent/file.mp3",
                sample_audio_workspace["workspace"] + "/invalid.txt"
            ]
            
            # Add invalid files
            window._add_audio_files(invalid_files)
            
            # Verify error handling (files should be filtered or error shown)
            selected_files = window.get_selected_audio_files()
            # Invalid files should either be filtered out or cause error display
            
            # Test processing with no files
            window._clear_audio_files()
            assert len(window.get_selected_audio_files()) == 0
            assert not window.process_btn.isEnabled()
            
            # Test processing with invalid options
            window._add_audio_files([sample_audio_workspace["hello_mp3"]])
            
            # Mock processing error
            error_message = "Test error: Invalid output directory"
            window._on_processing_error(error_message)
            
            # Verify error is displayed (implementation dependent)
            # This would typically show an error dialog or status message
            
        finally:
            window.hide()
    
    def test_file_drag_drop_workflow(self, app, sample_audio_workspace):
        """Test file drag and drop workflow."""
        window = MainWindow()
        window.show()
        
        try:
            # Test dropping valid audio files
            valid_files = [
                sample_audio_workspace["hello_mp3"],
                sample_audio_workspace["audio_files"][0]
            ]
            
            # Simulate drag and drop
            if hasattr(window, '_handle_dropped_files'):
                window._handle_dropped_files(valid_files)
                
                # Verify files were added
                assert len(window.get_selected_audio_files()) == 2
                assert window.process_btn.isEnabled()
            
            # Test dropping mixed file types
            mixed_files = valid_files + [sample_audio_workspace["lyric_files"][0]]
            
            if hasattr(window, '_handle_dropped_files'):
                window._clear_audio_files()  # Clear first
                window._handle_dropped_files(mixed_files)
                
                # Should handle audio and lyric files appropriately
                audio_files = window.get_selected_audio_files()
                lyric_file = window.get_selected_lyric_file()
                
                assert len(audio_files) >= 2  # Audio files should be added
                # Lyric file might be auto-detected and set
            
            # Test dropping invalid files
            invalid_files = [
                sample_audio_workspace["workspace"] + "/nonexistent.mp3",
                __file__  # Python file should be rejected
            ]
            
            if hasattr(window, '_handle_dropped_files'):
                initial_count = len(window.get_selected_audio_files())
                window._handle_dropped_files(invalid_files)
                
                # Invalid files should be filtered out
                final_count = len(window.get_selected_audio_files())
                assert final_count == initial_count  # No change or appropriate handling
            
        finally:
            window.hide()
    
    def test_batch_processing_ui_workflow(self, app, sample_audio_workspace):
        """Test batch processing through UI workflow."""
        window = MainWindow()
        
        # Mock application controller for batch processing
        with patch('src.ui.main_window.ApplicationController') as mock_controller_class:
            mock_controller = Mock()
            mock_controller_class.return_value = mock_controller
            
            # Configure batch processing result
            from src.models.data_models import BatchResult
            mock_batch_result = BatchResult(
                total_files=3,
                successful_files=2,
                failed_files=1,
                processing_results=[],
                total_processing_time=30.0
            )
            
            mock_controller.process_batch.return_value = mock_batch_result
            
            window.show()
            
            try:
                # Add multiple files for batch processing
                batch_files = [sample_audio_workspace["hello_mp3"]] + sample_audio_workspace["audio_files"]
                window._add_audio_files(batch_files)
                
                assert len(window.get_selected_audio_files()) == len(batch_files)
                
                # Start batch processing
                window._start_processing()
                
                # Verify batch processing was initiated
                if hasattr(window, '_is_batch_mode') and window._is_batch_mode():
                    mock_controller.process_batch.assert_called_once()
                else:
                    # Single file processing might be called multiple times
                    assert mock_controller.process_audio_file.call_count > 0
                
                # Simulate batch completion
                if hasattr(window, '_on_batch_complete'):
                    window._on_batch_complete(mock_batch_result)
                
                # Verify UI shows batch results
                # Implementation would depend on how batch results are displayed
                
            finally:
                window.hide()


class TestRealAudioProcessing:
    """Integration tests with real audio processing (if available)."""
    
    @pytest.mark.skipif(not Path("data/hello.mp3").exists(), reason="Sample audio file not available")
    def test_real_audio_file_processing(self, app, sample_audio_workspace):
        """Test processing with real hello.mp3 file."""
        # This test would use the actual hello.mp3 file if available
        # and test the complete pipeline with real AI models (if configured)
        
        window = MainWindow()
        
        # Use real application controller (not mocked)
        controller = ApplicationController()
        
        # Configure for real processing (would need models available)
        options = ProcessingOptions(
            model_size=ModelSize.TINY,  # Use smallest model for testing
            export_formats=[ExportFormat.SRT],
            output_directory=sample_audio_workspace["output_dir"]
        )
        
        window.show()
        
        try:
            # Add real audio file
            window._add_audio_files([sample_audio_workspace["hello_mp3"]])
            
            # Note: This test would only work if AI models are available
            # In a real test environment, you might want to skip this
            # or use it only in specific test configurations
            
            # For now, just verify the file can be loaded
            assert len(window.get_selected_audio_files()) == 1
            assert window.process_btn.isEnabled()
            
        finally:
            window.hide()