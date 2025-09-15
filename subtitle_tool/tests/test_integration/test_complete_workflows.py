"""
Integration tests for complete workflows.

This module tests end-to-end workflows including single file processing,
batch processing, and UI integration with real audio files.
"""

import pytest
import os
import tempfile
import shutil
import threading
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer

from src.services.application_controller import ApplicationController, ApplicationState
from src.services.audio_processor import AudioProcessor
from src.services.batch_processor import BatchProcessor
from src.ui.main_window import MainWindow
from src.models.data_models import (
    ProcessingOptions, ModelSize, ExportFormat, AlignmentData,
    Segment, WordSegment, ProcessingResult, BatchResult, AudioFile
)


@pytest.fixture
def app():
    """Create QApplication instance for testing."""
    return QApplication.instance() or QApplication([])


@pytest.fixture
def temp_workspace():
    """Create temporary workspace with test files."""
    workspace = tempfile.mkdtemp()
    
    # Create test audio file (using the actual hello.mp3 if available)
    test_audio_path = Path("data/hello.mp3")
    if test_audio_path.exists():
        # Copy the real test file
        shutil.copy(test_audio_path, Path(workspace) / "hello.mp3")
    else:
        # Create a dummy audio file
        with open(Path(workspace) / "hello.mp3", "wb") as f:
            f.write(b"fake mp3 data for testing")
    
    # Create additional test files
    for i in range(3):
        with open(Path(workspace) / f"test_audio_{i}.wav", "wb") as f:
            f.write(b"fake wav data for testing")
    
    # Create test lyric file
    with open(Path(workspace) / "test_lyrics.txt", "w") as f:
        f.write("Hello world\nThis is a test\nOf the lyric system")
    
    # Create output directory
    output_dir = Path(workspace) / "output"
    output_dir.mkdir()
    
    yield {
        "workspace": workspace,
        "audio_files": [
            str(Path(workspace) / "hello.mp3"),
            str(Path(workspace) / "test_audio_0.wav"),
            str(Path(workspace) / "test_audio_1.wav"),
            str(Path(workspace) / "test_audio_2.wav")
        ],
        "lyric_file": str(Path(workspace) / "test_lyrics.txt"),
        "output_dir": str(output_dir)
    }
    
    # Cleanup
    shutil.rmtree(workspace, ignore_errors=True)


@pytest.fixture
def mock_ai_components():
    """Create mock AI components for testing."""
    # Mock audio separator
    audio_separator = Mock()
    audio_separator.separate.return_value = ["/tmp/vocals.wav", "/tmp/instrumental.wav"]
    
    # Mock whisper
    whisper_model = Mock()
    whisper_result = Mock()
    whisper_result.segments = [
        Mock(start=0.0, end=5.0, text="Hello world"),
        Mock(start=5.0, end=10.0, text="This is a test")
    ]
    whisper_result.word_segments = [
        Mock(word="Hello", start=0.0, end=1.0),
        Mock(word="world", start=1.0, end=2.0),
        Mock(word="This", start=5.0, end=6.0),
        Mock(word="is", start=6.0, end=6.5),
        Mock(word="a", start=6.5, end=7.0),
        Mock(word="test", start=7.0, end=8.0)
    ]
    whisper_model.transcribe.return_value = whisper_result
    
    return {
        "audio_separator": audio_separator,
        "whisper_model": whisper_model
    }


class TestCompleteWorkflows:
    """Integration tests for complete application workflows."""
    
    def test_single_file_processing_workflow(self, temp_workspace, mock_ai_components):
        """Test complete single file processing workflow from start to finish."""
        # Setup
        controller = ApplicationController(temp_dir=temp_workspace["workspace"])
        
        # Track progress updates
        progress_updates = []
        status_updates = []
        
        def progress_callback(percentage, message):
            progress_updates.append((percentage, message))
        
        def status_callback(status):
            status_updates.append(status)
        
        controller.set_progress_callback(progress_callback)
        controller.set_status_callback(status_callback)
        
        # Configure processing options
        options = ProcessingOptions(
            model_size=ModelSize.BASE,
            export_formats=[ExportFormat.SRT, ExportFormat.VTT, ExportFormat.ASS],
            word_level_srt=True,
            karaoke_mode=True,
            output_directory=temp_workspace["output_dir"]
        )
        
        # Mock the AI processing pipeline
        with patch('src.services.audio_processor.AudioProcessor') as mock_processor_class:
            mock_processor = Mock()
            mock_processor_class.return_value = mock_processor
            
            # Configure mock processor
            mock_processor.validate_audio_file.return_value = AudioFile(
                path=temp_workspace["audio_files"][0],
                format="mp3",
                duration=10.0,
                sample_rate=44100,
                channels=2,
                file_size=1024
            )
            
            mock_processor.separate_vocals.return_value = "/tmp/vocals.wav"
            
            mock_processor.transcribe_with_alignment.return_value = AlignmentData(
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
                audio_duration=10.0
            )
            
            # Process single file
            result = controller.process_audio_file(temp_workspace["audio_files"][0], options)
            
            # Verify results
            assert isinstance(result, ProcessingResult)
            assert result.success is True
            assert len(result.output_files) == 3  # SRT, VTT, ASS
            assert result.alignment_data is not None
            assert result.processing_time > 0
            
            # Verify progress callbacks were called
            assert len(progress_updates) > 0
            assert progress_updates[-1][0] == 100.0  # Final progress should be 100%
            
            # Verify status updates
            assert len(status_updates) > 0
            assert ApplicationState.PROCESSING_SINGLE in [s.state for s in status_updates]
            
            # Verify session data was updated
            assert len(controller.session_data.processing_history) == 1
            assert temp_workspace["audio_files"][0] in controller.session_data.recent_files
            
            # Verify application state returned to idle
            assert controller.state == ApplicationState.IDLE
    
    def test_batch_processing_workflow(self, temp_workspace, mock_ai_components):
        """Test complete batch processing workflow with multiple files."""
        # Setup
        controller = ApplicationController(temp_dir=temp_workspace["workspace"])
        
        # Track batch progress
        batch_progress_updates = []
        file_progress_updates = []
        
        def batch_progress_callback(percentage, message):
            batch_progress_updates.append((percentage, message))
        
        def file_progress_callback(file_path, percentage, operation):
            file_progress_updates.append((file_path, percentage, operation))
        
        controller.set_progress_callback(batch_progress_callback)
        controller.set_file_progress_callback(file_progress_callback)
        
        # Configure processing options
        options = ProcessingOptions(
            model_size=ModelSize.SMALL,
            export_formats=[ExportFormat.SRT, ExportFormat.JSON],
            output_directory=temp_workspace["output_dir"]
        )
        
        # Mock the batch processing pipeline
        with patch('src.services.batch_processor.BatchProcessor') as mock_batch_class:
            mock_batch_processor = Mock()
            mock_batch_class.return_value = mock_batch_processor
            
            # Configure successful batch result
            mock_batch_result = BatchResult(
                total_files=len(temp_workspace["audio_files"]),
                successful_files=len(temp_workspace["audio_files"]),
                failed_files=0,
                processing_results=[
                    ProcessingResult(
                        success=True,
                        output_files=[f"output_{i}.srt", f"output_{i}.json"],
                        processing_time=5.0 + i,
                        alignment_data=AlignmentData(
                            segments=[Segment(0.0, 5.0, f"Test {i}", 0.95, 0)],
                            word_segments=[WordSegment(f"Test", 0.0, 1.0, 0.95, 0)],
                            confidence_scores=[0.95],
                            audio_duration=5.0
                        )
                    )
                    for i in range(len(temp_workspace["audio_files"]))
                ],
                total_processing_time=20.0
            )
            
            mock_batch_processor.process_batch.return_value = mock_batch_result
            mock_batch_processor.get_queue_status.return_value = {
                "total_files": len(temp_workspace["audio_files"]),
                "completed_files": len(temp_workspace["audio_files"]),
                "failed_files": 0,
                "progress_percentage": 100.0
            }
            
            # Process batch
            result = controller.process_batch(temp_workspace["audio_files"], options)
            
            # Verify results
            assert isinstance(result, BatchResult)
            assert result.success_rate() == 100.0
            assert result.total_files == len(temp_workspace["audio_files"])
            assert result.successful_files == len(temp_workspace["audio_files"])
            assert result.failed_files == 0
            
            # Verify all files have results
            assert len(result.processing_results) == len(temp_workspace["audio_files"])
            for processing_result in result.processing_results:
                assert processing_result.success is True
                assert len(processing_result.output_files) == 2  # SRT and JSON
            
            # Verify batch processor was called correctly
            mock_batch_processor.add_files_to_queue.assert_called_once_with(temp_workspace["audio_files"])
            mock_batch_processor.process_batch.assert_called_once_with(options)
            
            # Verify application state
            assert controller.state == ApplicationState.IDLE
    
    def test_ui_workflow_integration(self, app, temp_workspace):
        """Test complete UI workflow with file selection and processing."""
        # Create main window
        window = MainWindow()
        
        # Track UI signals
        files_selected_signals = []
        processing_requested_signals = []
        
        def on_files_selected(files):
            files_selected_signals.append(files)
        
        def on_processing_requested(files, options):
            processing_requested_signals.append((files, options))
        
        window.files_selected.connect(on_files_selected)
        window.processing_requested.connect(on_processing_requested)
        
        # Show window
        window.show()
        
        try:
            # Step 1: Add audio files
            window._add_audio_files(temp_workspace["audio_files"][:2])  # Add first 2 files
            
            # Verify files were added
            assert len(window.get_selected_audio_files()) == 2
            assert window.process_btn.isEnabled()
            assert len(files_selected_signals) == 1
            
            # Step 2: Add lyric file (optional)
            window.lyric_file = temp_workspace["lyric_file"]
            window._update_lyric_file_display()
            assert window.get_selected_lyric_file() == temp_workspace["lyric_file"]
            
            # Step 3: Configure processing options through UI
            # This would normally be done through the options panel
            # For testing, we'll simulate the configuration
            
            # Step 4: Start processing
            window._start_processing()
            
            # Verify processing was requested
            assert len(processing_requested_signals) == 1
            requested_files, requested_options = processing_requested_signals[0]
            assert len(requested_files) == 2
            assert isinstance(requested_options, ProcessingOptions)
            
            # Step 5: Simulate processing completion
            # In a real scenario, this would be handled by the application controller
            mock_results = [
                f"{temp_workspace['output_dir']}/output_0.srt",
                f"{temp_workspace['output_dir']}/output_1.srt"
            ]
            
            # Create mock result files
            for result_file in mock_results:
                Path(result_file).touch()
            
            # Simulate processing completion signal
            window._on_processing_complete(mock_results, None)
            
            # Verify UI state after completion
            assert window.process_btn.isEnabled()  # Should be re-enabled
            
        finally:
            window.hide()
    
    def test_error_handling_workflow(self, temp_workspace):
        """Test complete workflow with error handling and recovery."""
        controller = ApplicationController(temp_dir=temp_workspace["workspace"])
        
        # Track error handling
        error_callbacks = []
        
        def error_callback(error_context):
            error_callbacks.append(error_context)
        
        controller.set_error_callback(error_callback)
        
        # Configure options with invalid output directory
        options = ProcessingOptions(
            model_size=ModelSize.BASE,
            export_formats=[ExportFormat.SRT],
            output_directory="/invalid/directory/path"
        )
        
        # Attempt processing with invalid options
        result = controller.process_audio_file(temp_workspace["audio_files"][0], options)
        
        # Verify error handling
        assert result.success is False
        assert result.error_message is not None
        assert len(error_callbacks) > 0
        
        # Verify application state
        assert controller.state == ApplicationState.IDLE  # Should return to idle after error
        
        # Test recovery - fix the options and try again
        options.output_directory = temp_workspace["output_dir"]
        
        with patch('src.services.audio_processor.AudioProcessor') as mock_processor_class:
            mock_processor = Mock()
            mock_processor_class.return_value = mock_processor
            
            # Configure successful processing
            mock_processor.validate_audio_file.return_value = AudioFile(
                path=temp_workspace["audio_files"][0],
                format="mp3",
                duration=10.0,
                sample_rate=44100,
                channels=2,
                file_size=1024
            )
            
            mock_processor.separate_vocals.return_value = "/tmp/vocals.wav"
            mock_processor.transcribe_with_alignment.return_value = AlignmentData(
                segments=[Segment(0.0, 5.0, "Recovery test", 0.95, 0)],
                word_segments=[WordSegment("Recovery", 0.0, 2.0, 0.95, 0)],
                confidence_scores=[0.95],
                audio_duration=5.0
            )
            
            # Retry processing
            recovery_result = controller.process_audio_file(temp_workspace["audio_files"][0], options)
            
            # Verify recovery
            assert recovery_result.success is True
            assert recovery_result.error_message is None
    
    def test_cancellation_workflow(self, temp_workspace):
        """Test workflow cancellation during processing."""
        controller = ApplicationController(temp_dir=temp_workspace["workspace"])
        
        # Configure options
        options = ProcessingOptions(
            model_size=ModelSize.BASE,
            export_formats=[ExportFormat.SRT],
            output_directory=temp_workspace["output_dir"]
        )
        
        # Mock slow processing
        with patch('src.services.audio_processor.AudioProcessor') as mock_processor_class:
            mock_processor = Mock()
            mock_processor_class.return_value = mock_processor
            
            # Configure slow validation
            def slow_validate(file_path):
                time.sleep(0.2)  # Simulate slow processing
                return AudioFile(
                    path=file_path,
                    format="mp3",
                    duration=10.0,
                    sample_rate=44100,
                    channels=2,
                    file_size=1024
                )
            
            mock_processor.validate_audio_file.side_effect = slow_validate
            
            # Start processing in a separate thread
            def process_file():
                return controller.process_audio_file(temp_workspace["audio_files"][0], options)
            
            thread = threading.Thread(target=process_file)
            thread.start()
            
            # Wait a bit then cancel
            time.sleep(0.1)
            cancel_result = controller.cancel_processing()
            
            # Wait for thread to complete
            thread.join(timeout=2.0)
            
            # Verify cancellation
            assert cancel_result is True
            assert controller.state == ApplicationState.IDLE
    
    def test_session_data_persistence(self, temp_workspace):
        """Test that session data is properly maintained across operations."""
        controller = ApplicationController(temp_dir=temp_workspace["workspace"])
        
        # Configure options
        options = ProcessingOptions(
            model_size=ModelSize.MEDIUM,
            export_formats=[ExportFormat.SRT, ExportFormat.VTT],
            output_directory=temp_workspace["output_dir"]
        )
        
        # Mock successful processing
        with patch('src.services.audio_processor.AudioProcessor') as mock_processor_class:
            mock_processor = Mock()
            mock_processor_class.return_value = mock_processor
            
            mock_processor.validate_audio_file.return_value = AudioFile(
                path=temp_workspace["audio_files"][0],
                format="mp3",
                duration=10.0,
                sample_rate=44100,
                channels=2,
                file_size=1024
            )
            
            mock_processor.separate_vocals.return_value = "/tmp/vocals.wav"
            mock_processor.transcribe_with_alignment.return_value = AlignmentData(
                segments=[Segment(0.0, 5.0, "Session test", 0.95, 0)],
                word_segments=[WordSegment("Session", 0.0, 2.0, 0.95, 0)],
                confidence_scores=[0.95],
                audio_duration=5.0
            )
            
            # Process multiple files
            for i, audio_file in enumerate(temp_workspace["audio_files"][:2]):
                result = controller.process_audio_file(audio_file, options)
                assert result.success is True
            
            # Verify session data
            session = controller.session_data
            
            # Check recent files
            assert len(session.recent_files) == 2
            for audio_file in temp_workspace["audio_files"][:2]:
                assert audio_file in session.recent_files
            
            # Check processing history
            assert len(session.processing_history) == 2
            for record in session.processing_history:
                assert record["success"] is True
                assert record["model_size"] == ModelSize.MEDIUM.value
                assert len(record["export_formats"]) == 2
            
            # Check last processing options
            assert session.last_processing_options is not None
            assert session.last_processing_options.model_size == ModelSize.MEDIUM
            
            # Check directories
            assert session.last_output_directory == temp_workspace["output_dir"]


class TestUIWorkflowIntegration:
    """Integration tests specifically for UI workflows."""
    
    def test_complete_ui_processing_workflow(self, app, temp_workspace):
        """Test complete UI workflow from file selection to results display."""
        # Create and configure main window
        window = MainWindow()
        
        # Mock the application controller
        with patch('src.ui.main_window.ApplicationController') as mock_controller_class:
            mock_controller = Mock()
            mock_controller_class.return_value = mock_controller
            
            # Configure successful processing
            mock_result = ProcessingResult(
                success=True,
                output_files=[
                    f"{temp_workspace['output_dir']}/test.srt",
                    f"{temp_workspace['output_dir']}/test.vtt"
                ],
                processing_time=10.5,
                alignment_data=AlignmentData(
                    segments=[Segment(0.0, 5.0, "UI test", 0.95, 0)],
                    word_segments=[WordSegment("UI", 0.0, 1.0, 0.95, 0)],
                    confidence_scores=[0.95],
                    audio_duration=5.0
                )
            )
            
            mock_controller.process_audio_file.return_value = mock_result
            
            # Show window
            window.show()
            
            try:
                # Step 1: Add files through UI
                window._add_audio_files([temp_workspace["audio_files"][0]])
                assert len(window.get_selected_audio_files()) == 1
                
                # Step 2: Configure options (simulate user interaction)
                # This would normally be done through options panel
                
                # Step 3: Start processing
                window._start_processing()
                
                # Verify controller was called
                mock_controller.process_audio_file.assert_called_once()
                
                # Step 4: Simulate processing completion
                # Create actual result files for UI display
                for output_file in mock_result.output_files:
                    Path(output_file).parent.mkdir(parents=True, exist_ok=True)
                    Path(output_file).write_text("Test subtitle content")
                
                # Trigger completion callback
                window._on_processing_complete(mock_result.output_files, None)
                
                # Verify UI state
                assert window.process_btn.isEnabled()
                
            finally:
                window.hide()
    
    def test_drag_and_drop_workflow(self, app, temp_workspace):
        """Test drag and drop file selection workflow."""
        window = MainWindow()
        window.show()
        
        try:
            # Simulate drag and drop event
            # Note: This is a simplified test - real drag/drop testing would require
            # more complex Qt event simulation
            
            # Directly call the drag/drop handler method
            dropped_files = temp_workspace["audio_files"][:2]
            window._handle_dropped_files(dropped_files)
            
            # Verify files were added
            assert len(window.get_selected_audio_files()) == 2
            assert window.process_btn.isEnabled()
            
        finally:
            window.hide()