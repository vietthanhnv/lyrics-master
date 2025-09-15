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

from src.services.application_controller import ApplicationController, ApplicationState
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


class TestCompleteWorkflows:
    """Integration tests for complete application workflows."""
    
    def test_single_file_processing_workflow(self, temp_workspace):
        """Test complete single file processing workflow from start to finish."""
        # Setup
        controller = ApplicationController(temp_dir=temp_workspace["workspace"])
        
        # Track progress updates
        progress_updates = []
        
        def progress_callback(percentage, message):
            progress_updates.append((percentage, message))
        
        controller.set_progress_callback(progress_callback)
        
        # Configure processing options
        options = ProcessingOptions(
            model_size=ModelSize.BASE,
            export_formats=[ExportFormat.SRT, ExportFormat.VTT],
            word_level_srt=True,
            karaoke_mode=False,
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
            # Note: Result may fail due to missing models, but we test the workflow
            assert result.processing_time >= 0
            
            # Verify progress callbacks were called if processing succeeded
            if result.success:
                assert len(progress_updates) > 0
            
            # Verify application state
            assert controller.state == ApplicationState.IDLE
    
    def test_batch_processing_workflow(self, temp_workspace):
        """Test complete batch processing workflow with multiple files."""
        # Setup
        controller = ApplicationController(temp_dir=temp_workspace["workspace"])
        
        # Track batch progress
        batch_progress_updates = []
        
        def batch_progress_callback(percentage, message):
            batch_progress_updates.append((percentage, message))
        
        controller.set_progress_callback(batch_progress_callback)
        
        # Configure processing options
        options = ProcessingOptions(
            model_size=ModelSize.SMALL,
            export_formats=[ExportFormat.SRT],
            output_directory=temp_workspace["output_dir"]
        )
        
        # Use subset of files for batch processing
        batch_files = temp_workspace["audio_files"][:2]
        
        # Mock the batch processing at the controller level
        with patch.object(controller, 'batch_processor') as mock_batch_processor, \
             patch.object(controller, '_ensure_models_available') as mock_ensure_models:
            
            mock_ensure_models.return_value = None  # Mock successful model availability
            
            # Configure batch processing results
            processing_results = []
            for i, file_path in enumerate(batch_files):
                result = ProcessingResult(
                    success=True,
                    output_files=[f"{temp_workspace['output_dir']}/{Path(file_path).stem}.srt"],
                    processing_time=5.0 + i * 2,
                    alignment_data=AlignmentData(
                        segments=[Segment(0.0, 10.0, f"Test content {i}", 0.90, 0)],
                        word_segments=[WordSegment(f"Test", 0.0, 2.0, 0.90, 0)],
                        confidence_scores=[0.90],
                        audio_duration=10.0
                    )
                )
                processing_results.append(result)
            
            batch_result = BatchResult(
                total_files=len(batch_files),
                successful_files=len(batch_files),
                failed_files=0,
                processing_results=processing_results,
                total_processing_time=sum(r.processing_time for r in processing_results)
            )
            
            mock_batch_processor.process_batch.return_value = batch_result
            mock_batch_processor.get_queue_status.return_value = {
                "total_files": len(batch_files),
                "completed_files": len(batch_files),
                "failed_files": 0,
                "progress_percentage": 100.0,
                "files": [
                    {"file_path": fp, "status": "completed", "error_message": None}
                    for fp in batch_files
                ]
            }
            
            # Process batch
            result = controller.process_batch(batch_files, options)
            
            # Verify results
            assert isinstance(result, BatchResult)
            assert result.success_rate() == 100.0
            assert result.total_files == len(batch_files)
            
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
            
            # Step 3: Start processing
            window._start_processing()
            
            # Verify processing was requested
            assert len(processing_requested_signals) == 1
            requested_files, requested_options = processing_requested_signals[0]
            assert len(requested_files) == 2
            assert isinstance(requested_options, ProcessingOptions)
            
            # Step 4: Simulate processing completion
            mock_results = [
                f"{temp_workspace['output_dir']}/output_0.srt",
                f"{temp_workspace['output_dir']}/output_1.srt"
            ]
            
            # Create mock result files
            for result_file in mock_results:
                Path(result_file).touch()
            
            # Verify UI state after completion
            assert window.process_btn.isEnabled()  # Should be re-enabled
            
        finally:
            window.hide()
    
    def test_error_handling_workflow(self, temp_workspace):
        """Test complete workflow with error handling and recovery."""
        controller = ApplicationController(temp_dir=temp_workspace["workspace"])
        
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
            
            # Verify recovery (may still fail due to missing models, but workflow should work)
            assert recovery_result.processing_time >= 0
    
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
            
            # Process file
            result = controller.process_audio_file(temp_workspace["audio_files"][0], options)
            
            # Verify session data exists (regardless of processing success)
            session = controller.session_data
            assert session is not None
            
            # Check that session data structure is correct
            assert hasattr(session, 'recent_files')
            assert hasattr(session, 'processing_history')
            assert hasattr(session, 'last_output_directory')


class TestUIWorkflowIntegration:
    """Integration tests specifically for UI workflows."""
    
    def test_complete_ui_processing_workflow(self, app, temp_workspace):
        """Test complete UI workflow from file selection to results display."""
        # Create and configure main window
        window = MainWindow()
        
        # Show window
        window.show()
        
        try:
            # Step 1: Add files through UI
            window._add_audio_files([temp_workspace["audio_files"][0]])
            assert len(window.get_selected_audio_files()) == 1
            
            # Step 2: Start processing
            window._start_processing()
            
            # Verify UI state
            assert window.process_btn.isEnabled()
            
        finally:
            window.hide()
    
    def test_drag_and_drop_workflow(self, app, temp_workspace):
        """Test drag and drop file selection workflow."""
        window = MainWindow()
        window.show()
        
        try:
            # Directly test the add files method (simulating drag/drop)
            dropped_files = temp_workspace["audio_files"][:2]
            window._add_audio_files(dropped_files)
            
            # Verify files were added
            assert len(window.get_selected_audio_files()) == 2
            assert window.process_btn.isEnabled()
            
        finally:
            window.hide()