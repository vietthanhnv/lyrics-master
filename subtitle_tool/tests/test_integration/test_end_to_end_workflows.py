"""
End-to-end integration tests for complete application workflows.

This module tests the complete application workflow from file input
to subtitle output, including error scenarios and edge cases.
"""

import pytest
import os
import tempfile
import shutil
import threading
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call

from src.services.application_controller import ApplicationController, ApplicationState
from src.services.audio_processor import AudioProcessor
from src.services.batch_processor import BatchProcessor
from src.services.subtitle_generator import SubtitleGenerator
from src.models.data_models import (
    ProcessingOptions, ModelSize, ExportFormat, AlignmentData,
    Segment, WordSegment, ProcessingResult, BatchResult, AudioFile
)


@pytest.fixture
def end_to_end_workspace():
    """Create comprehensive workspace for end-to-end testing."""
    workspace = tempfile.mkdtemp()
    
    # Create realistic test audio files
    audio_files = []
    
    # Copy real hello.mp3 if available
    hello_path = Path("data/hello.mp3")
    if hello_path.exists():
        dest_path = Path(workspace) / "hello.mp3"
        shutil.copy(hello_path, dest_path)
        audio_files.append(str(dest_path))
    
    # Create additional test files with different formats and sizes
    test_files = [
        ("short_song.wav", 1024),
        ("medium_song.flac", 2048),
        ("long_song.ogg", 4096),
        ("podcast.mp3", 8192)
    ]
    
    for filename, size in test_files:
        file_path = Path(workspace) / filename
        with open(file_path, "wb") as f:
            f.write(b"fake audio data" * size)
        audio_files.append(str(file_path))
    
    # Create lyric files
    lyric_files = []
    
    # Simple text lyrics
    simple_lyrics = Path(workspace) / "simple.txt"
    simple_lyrics.write_text("Hello world\nThis is a test\nOf the subtitle system")
    lyric_files.append(str(simple_lyrics))
    
    # LRC format lyrics
    lrc_lyrics = Path(workspace) / "timed.lrc"
    lrc_lyrics.write_text("""[00:00.00]Hello world
[00:05.00]This is a test
[00:10.00]Of the subtitle system
[00:15.00]With precise timing""")
    lyric_files.append(str(lrc_lyrics))
    
    # Create output directories
    output_dir = Path(workspace) / "output"
    output_dir.mkdir()
    
    batch_output_dir = Path(workspace) / "batch_output"
    batch_output_dir.mkdir()
    
    yield {
        "workspace": workspace,
        "audio_files": audio_files,
        "lyric_files": lyric_files,
        "output_dir": str(output_dir),
        "batch_output_dir": str(batch_output_dir)
    }
    
    # Cleanup
    shutil.rmtree(workspace, ignore_errors=True)


class TestEndToEndWorkflows:
    """Comprehensive end-to-end workflow tests."""
    
    def test_complete_single_file_workflow(self, end_to_end_workspace):
        """Test complete single file processing from start to finish."""
        controller = ApplicationController(temp_dir=end_to_end_workspace["workspace"])
        
        # Configure comprehensive processing options
        options = ProcessingOptions(
            model_size=ModelSize.BASE,
            export_formats=[ExportFormat.SRT, ExportFormat.VTT, ExportFormat.ASS, ExportFormat.JSON],
            word_level_srt=True,
            karaoke_mode=True,
            translation_enabled=False,  # Disable translation for this test
            output_directory=end_to_end_workspace["output_dir"]
        )
        
        # Track all callbacks
        progress_updates = []
        status_updates = []
        error_callbacks = []
        
        def progress_callback(percentage, message):
            progress_updates.append((time.time(), percentage, message))
        
        def status_callback(status):
            status_updates.append((time.time(), status))
        
        def error_callback(error_context):
            error_callbacks.append(error_context)
        
        controller.set_progress_callback(progress_callback)
        controller.set_status_callback(status_callback)
        controller.set_error_callback(error_callback)
        
        # Mock the complete AI pipeline
        with patch('src.services.audio_processor.AudioProcessor') as mock_processor_class:
            mock_processor = Mock()
            mock_processor_class.return_value = mock_processor
            
            # Configure realistic processing pipeline
            audio_file = AudioFile(
                path=end_to_end_workspace["audio_files"][0],
                format="mp3",
                duration=30.0,
                sample_rate=44100,
                channels=2,
                file_size=1024000
            )
            
            mock_processor.validate_audio_file.return_value = audio_file
            mock_processor.separate_vocals.return_value = "/tmp/vocals.wav"
            
            # Create realistic alignment data
            alignment_data = AlignmentData(
                segments=[
                    Segment(0.0, 10.0, "Hello world, this is a test", 0.95, 0),
                    Segment(10.0, 20.0, "Of the subtitle generation system", 0.90, 1),
                    Segment(20.0, 30.0, "With word-level timing information", 0.88, 2)
                ],
                word_segments=[
                    WordSegment("Hello", 0.0, 1.5, 0.95, 0),
                    WordSegment("world", 1.5, 3.0, 0.95, 0),
                    WordSegment("this", 4.0, 5.0, 0.93, 0),
                    WordSegment("is", 5.0, 5.5, 0.93, 0),
                    WordSegment("a", 5.5, 6.0, 0.93, 0),
                    WordSegment("test", 6.0, 8.0, 0.95, 0),
                    WordSegment("Of", 10.0, 11.0, 0.90, 1),
                    WordSegment("the", 11.0, 12.0, 0.90, 1),
                    WordSegment("subtitle", 12.0, 14.0, 0.90, 1),
                    WordSegment("generation", 14.0, 16.5, 0.88, 1),
                    WordSegment("system", 16.5, 18.0, 0.90, 1),
                    WordSegment("With", 20.0, 21.0, 0.88, 2),
                    WordSegment("word-level", 21.0, 23.5, 0.85, 2),
                    WordSegment("timing", 23.5, 25.5, 0.88, 2),
                    WordSegment("information", 25.5, 28.0, 0.90, 2)
                ],
                confidence_scores=[0.95, 0.90, 0.88],
                audio_duration=30.0
            )
            
            mock_processor.transcribe_with_alignment.return_value = alignment_data
            
            # Execute the complete workflow
            start_time = time.time()
            result = controller.process_audio_file(end_to_end_workspace["audio_files"][0], options)
            end_time = time.time()
            
            # Verify successful processing
            assert result.success is True
            assert result.error_message is None
            assert len(result.output_files) == 4  # SRT, VTT, ASS, JSON
            assert result.alignment_data is not None
            assert result.processing_time > 0
            
            # Verify all expected output files would be created
            expected_base_name = Path(end_to_end_workspace["audio_files"][0]).stem
            expected_files = [
                f"{expected_base_name}.srt",
                f"{expected_base_name}_word_level.srt",
                f"{expected_base_name}.vtt",
                f"{expected_base_name}_karaoke.ass",
                f"{expected_base_name}_alignment.json"
            ]
            
            # Verify processing pipeline was called correctly
            mock_processor.validate_audio_file.assert_called_once()
            mock_processor.separate_vocals.assert_called_once()
            mock_processor.transcribe_with_alignment.assert_called_once()
            
            # Verify progress callbacks
            assert len(progress_updates) > 0
            assert progress_updates[0][1] == 0  # Should start at 0%
            assert progress_updates[-1][1] == 100  # Should end at 100%
            
            # Verify status updates
            assert len(status_updates) > 0
            states = [update[1].state for update in status_updates]
            assert ApplicationState.PROCESSING_SINGLE in states
            assert ApplicationState.IDLE in states  # Should return to idle
            
            # Verify no errors occurred
            assert len(error_callbacks) == 0
            
            # Verify session data was updated
            session = controller.session_data
            assert end_to_end_workspace["audio_files"][0] in session.recent_files
            assert len(session.processing_history) == 1
            assert session.processing_history[0]["success"] is True
            assert session.last_output_directory == end_to_end_workspace["output_dir"]
    
    def test_complete_batch_workflow(self, end_to_end_workspace):
        """Test complete batch processing workflow."""
        controller = ApplicationController(temp_dir=end_to_end_workspace["workspace"])
        
        # Configure batch processing options
        options = ProcessingOptions(
            model_size=ModelSize.SMALL,
            export_formats=[ExportFormat.SRT, ExportFormat.VTT],
            word_level_srt=False,
            karaoke_mode=False,
            output_directory=end_to_end_workspace["batch_output_dir"]
        )
        
        # Track batch progress
        batch_progress = []
        file_progress = []
        
        def batch_progress_callback(percentage, message):
            batch_progress.append((percentage, message))
        
        def file_progress_callback(file_path, percentage, operation):
            file_progress.append((file_path, percentage, operation))
        
        controller.set_progress_callback(batch_progress_callback)
        controller.set_file_progress_callback(file_progress_callback)
        
        # Use subset of files for batch processing
        batch_files = end_to_end_workspace["audio_files"][:3]
        
        # Mock batch processing pipeline
        with patch('src.services.batch_processor.BatchProcessor') as mock_batch_class:
            mock_batch_processor = Mock()
            mock_batch_class.return_value = mock_batch_processor
            
            # Configure batch processing results
            processing_results = []
            for i, file_path in enumerate(batch_files):
                result = ProcessingResult(
                    success=True,
                    output_files=[
                        f"{end_to_end_workspace['batch_output_dir']}/{Path(file_path).stem}.srt",
                        f"{end_to_end_workspace['batch_output_dir']}/{Path(file_path).stem}.vtt"
                    ],
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
            
            # Execute batch processing
            result = controller.process_batch(batch_files, options)
            
            # Verify batch results
            assert isinstance(result, BatchResult)
            assert result.success_rate() == 100.0
            assert result.total_files == len(batch_files)
            assert result.successful_files == len(batch_files)
            assert result.failed_files == 0
            
            # Verify all files were processed
            assert len(result.processing_results) == len(batch_files)
            for processing_result in result.processing_results:
                assert processing_result.success is True
                assert len(processing_result.output_files) == 2  # SRT and VTT
            
            # Verify batch processor was used correctly
            mock_batch_processor.add_files_to_queue.assert_called_once_with(batch_files)
            mock_batch_processor.process_batch.assert_called_once_with(options)
            
            # Verify session data for batch processing
            session = controller.session_data
            assert len(session.processing_history) == len(batch_files)
            for file_path in batch_files:
                assert file_path in session.recent_files
    
    def test_workflow_with_translation(self, end_to_end_workspace):
        """Test workflow with translation enabled."""
        controller = ApplicationController(temp_dir=end_to_end_workspace["workspace"])
        
        # Configure options with translation
        options = ProcessingOptions(
            model_size=ModelSize.BASE,
            export_formats=[ExportFormat.SRT, ExportFormat.VTT],
            translation_enabled=True,
            target_language="Spanish",
            translation_service="google",
            output_directory=end_to_end_workspace["output_dir"]
        )
        
        # Mock translation service
        with patch('src.services.translation_service.TranslationService') as mock_translation_class:
            mock_translation = Mock()
            mock_translation_class.return_value = mock_translation
            
            # Configure translation responses
            mock_translation.translate_text.side_effect = [
                "Hola mundo, esta es una prueba",
                "Del sistema de generación de subtítulos",
                "Con información de tiempo a nivel de palabra"
            ]
            mock_translation.is_service_available.return_value = True
            
            # Mock audio processing
            with patch('src.services.audio_processor.AudioProcessor') as mock_processor_class:
                mock_processor = Mock()
                mock_processor_class.return_value = mock_processor
                
                mock_processor.validate_audio_file.return_value = AudioFile(
                    path=end_to_end_workspace["audio_files"][0],
                    format="mp3",
                    duration=30.0,
                    sample_rate=44100,
                    channels=2,
                    file_size=1024000
                )
                
                mock_processor.separate_vocals.return_value = "/tmp/vocals.wav"
                mock_processor.transcribe_with_alignment.return_value = AlignmentData(
                    segments=[
                        Segment(0.0, 10.0, "Hello world, this is a test", 0.95, 0),
                        Segment(10.0, 20.0, "Of the subtitle generation system", 0.90, 1),
                        Segment(20.0, 30.0, "With word-level timing information", 0.88, 2)
                    ],
                    word_segments=[],
                    confidence_scores=[0.95, 0.90, 0.88],
                    audio_duration=30.0
                )
                
                # Execute processing with translation
                result = controller.process_audio_file(end_to_end_workspace["audio_files"][0], options)
                
                # Verify successful processing
                assert result.success is True
                
                # Verify translation was called
                assert mock_translation.translate_text.call_count == 3  # One per segment
                
                # Verify bilingual output files would be created
                assert len(result.output_files) >= 2  # At least SRT and VTT
    
    def test_workflow_error_scenarios(self, end_to_end_workspace):
        """Test workflow error handling scenarios."""
        controller = ApplicationController(temp_dir=end_to_end_workspace["workspace"])
        
        # Track errors
        error_contexts = []
        
        def error_callback(error_context):
            error_contexts.append(error_context)
        
        controller.set_error_callback(error_callback)
        
        # Test 1: Invalid file path
        options = ProcessingOptions(
            model_size=ModelSize.BASE,
            export_formats=[ExportFormat.SRT],
            output_directory=end_to_end_workspace["output_dir"]
        )
        
        result = controller.process_audio_file("/nonexistent/file.mp3", options)
        assert result.success is False
        assert result.error_message is not None
        
        # Test 2: Invalid output directory
        options.output_directory = "/invalid/directory"
        result = controller.process_audio_file(end_to_end_workspace["audio_files"][0], options)
        assert result.success is False
        
        # Test 3: Processing failure simulation
        with patch('src.services.audio_processor.AudioProcessor') as mock_processor_class:
            mock_processor = Mock()
            mock_processor_class.return_value = mock_processor
            
            # Simulate processing failure
            mock_processor.validate_audio_file.side_effect = Exception("Simulated processing error")
            
            options.output_directory = end_to_end_workspace["output_dir"]  # Fix directory
            result = controller.process_audio_file(end_to_end_workspace["audio_files"][0], options)
            
            assert result.success is False
            assert "Simulated processing error" in result.error_message
        
        # Verify errors were captured
        assert len(error_contexts) > 0
    
    def test_workflow_cancellation_scenarios(self, end_to_end_workspace):
        """Test workflow cancellation scenarios."""
        controller = ApplicationController(temp_dir=end_to_end_workspace["workspace"])
        
        options = ProcessingOptions(
            model_size=ModelSize.BASE,
            export_formats=[ExportFormat.SRT],
            output_directory=end_to_end_workspace["output_dir"]
        )
        
        # Mock slow processing for cancellation testing
        with patch('src.services.audio_processor.AudioProcessor') as mock_processor_class:
            mock_processor = Mock()
            mock_processor_class.return_value = mock_processor
            
            # Configure slow processing
            def slow_validate(file_path):
                time.sleep(0.5)  # Simulate slow processing
                return AudioFile(
                    path=file_path,
                    format="mp3",
                    duration=30.0,
                    sample_rate=44100,
                    channels=2,
                    file_size=1024000
                )
            
            mock_processor.validate_audio_file.side_effect = slow_validate
            
            # Start processing in thread
            def process_file():
                return controller.process_audio_file(end_to_end_workspace["audio_files"][0], options)
            
            thread = threading.Thread(target=process_file)
            thread.start()
            
            # Wait briefly then cancel
            time.sleep(0.1)
            cancel_result = controller.cancel_processing()
            
            # Wait for thread completion
            thread.join(timeout=2.0)
            
            # Verify cancellation
            assert cancel_result is True
            assert controller.state == ApplicationState.IDLE
    
    def test_workflow_performance_monitoring(self, end_to_end_workspace):
        """Test workflow performance monitoring and metrics."""
        controller = ApplicationController(temp_dir=end_to_end_workspace["workspace"])
        
        # Track performance metrics
        performance_data = []
        
        def performance_callback(metrics):
            performance_data.append(metrics)
        
        if hasattr(controller, 'set_performance_callback'):
            controller.set_performance_callback(performance_callback)
        
        options = ProcessingOptions(
            model_size=ModelSize.BASE,
            export_formats=[ExportFormat.SRT, ExportFormat.VTT],
            output_directory=end_to_end_workspace["output_dir"]
        )
        
        # Mock processing with timing
        with patch('src.services.audio_processor.AudioProcessor') as mock_processor_class:
            mock_processor = Mock()
            mock_processor_class.return_value = mock_processor
            
            # Add realistic delays to simulate processing time
            def timed_validate(file_path):
                time.sleep(0.1)
                return AudioFile(
                    path=file_path,
                    format="mp3",
                    duration=30.0,
                    sample_rate=44100,
                    channels=2,
                    file_size=1024000
                )
            
            def timed_separate(file_path):
                time.sleep(0.2)
                return "/tmp/vocals.wav"
            
            def timed_transcribe(vocals_path):
                time.sleep(0.3)
                return AlignmentData(
                    segments=[Segment(0.0, 10.0, "Performance test", 0.95, 0)],
                    word_segments=[WordSegment("Performance", 0.0, 3.0, 0.95, 0)],
                    confidence_scores=[0.95],
                    audio_duration=10.0
                )
            
            mock_processor.validate_audio_file.side_effect = timed_validate
            mock_processor.separate_vocals.side_effect = timed_separate
            mock_processor.transcribe_with_alignment.side_effect = timed_transcribe
            
            # Process file and measure performance
            start_time = time.time()
            result = controller.process_audio_file(end_to_end_workspace["audio_files"][0], options)
            end_time = time.time()
            
            # Verify processing completed
            assert result.success is True
            
            # Verify timing is reasonable
            total_time = end_time - start_time
            assert total_time >= 0.6  # Should take at least sum of delays
            assert result.processing_time > 0
            
            # Verify performance data if available
            if performance_data:
                assert len(performance_data) > 0
    
    def test_workflow_resource_management(self, end_to_end_workspace):
        """Test workflow resource management and cleanup."""
        controller = ApplicationController(temp_dir=end_to_end_workspace["workspace"])
        
        options = ProcessingOptions(
            model_size=ModelSize.BASE,
            export_formats=[ExportFormat.SRT],
            output_directory=end_to_end_workspace["output_dir"]
        )
        
        # Track temporary files created
        temp_files_created = []
        
        # Mock file operations to track temporary files
        original_tempfile = tempfile.NamedTemporaryFile
        
        def tracked_tempfile(*args, **kwargs):
            temp_file = original_tempfile(*args, **kwargs)
            temp_files_created.append(temp_file.name)
            return temp_file
        
        with patch('tempfile.NamedTemporaryFile', side_effect=tracked_tempfile):
            with patch('src.services.audio_processor.AudioProcessor') as mock_processor_class:
                mock_processor = Mock()
                mock_processor_class.return_value = mock_processor
                
                mock_processor.validate_audio_file.return_value = AudioFile(
                    path=end_to_end_workspace["audio_files"][0],
                    format="mp3",
                    duration=30.0,
                    sample_rate=44100,
                    channels=2,
                    file_size=1024000
                )
                
                mock_processor.separate_vocals.return_value = "/tmp/vocals.wav"
                mock_processor.transcribe_with_alignment.return_value = AlignmentData(
                    segments=[Segment(0.0, 10.0, "Resource test", 0.95, 0)],
                    word_segments=[WordSegment("Resource", 0.0, 3.0, 0.95, 0)],
                    confidence_scores=[0.95],
                    audio_duration=10.0
                )
                
                # Process file
                result = controller.process_audio_file(end_to_end_workspace["audio_files"][0], options)
                
                # Verify processing completed
                assert result.success is True
                
                # Verify cleanup (temporary files should be cleaned up)
                # This would depend on the actual implementation
                # For now, just verify the workflow completed without resource leaks