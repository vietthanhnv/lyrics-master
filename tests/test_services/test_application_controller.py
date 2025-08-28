"""
Tests for the ApplicationController class.
"""

import pytest
import os
import tempfile
import time
from unittest.mock import Mock, patch, MagicMock

from src.services.application_controller import ApplicationController, ApplicationState, SessionData
from src.models.data_models import (
    ProcessingOptions, ProcessingResult, BatchResult, ProcessingStatus,
    ModelSize, ExportFormat, AlignmentData, Segment, WordSegment
)
from src.services.interfaces import ProcessingError, ValidationError


class TestApplicationController:
    """Test cases for ApplicationController."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir
    
    @pytest.fixture
    def sample_options(self, temp_dir):
        """Create sample processing options."""
        return ProcessingOptions(
            model_size=ModelSize.TINY,
            export_formats=[ExportFormat.SRT],
            output_directory=temp_dir
        )
    
    @pytest.fixture
    def sample_alignment_data(self):
        """Create sample alignment data."""
        segments = [
            Segment(0.0, 2.0, "Hello world", 0.9, 0),
            Segment(2.0, 4.0, "This is a test", 0.8, 1)
        ]
        word_segments = [
            WordSegment("Hello", 0.0, 0.5, 0.9, 0),
            WordSegment("world", 0.5, 1.0, 0.8, 0),
            WordSegment("This", 2.0, 2.3, 0.9, 1),
            WordSegment("is", 2.3, 2.5, 0.7, 1),
            WordSegment("a", 2.5, 2.6, 0.8, 1),
            WordSegment("test", 2.6, 3.0, 0.9, 1)
        ]
        return AlignmentData(
            segments=segments,
            word_segments=word_segments,
            confidence_scores=[0.9, 0.8],
            audio_duration=4.0
        )
    
    @pytest.fixture
    def mock_services(self):
        """Create mocked services for testing."""
        with patch('src.services.application_controller.ModelManager') as mock_model_manager, \
             patch('src.services.application_controller.AudioProcessor') as mock_audio_processor, \
             patch('src.services.application_controller.BatchProcessor') as mock_batch_processor, \
             patch('src.services.application_controller.SubtitleGenerator') as mock_subtitle_generator, \
             patch('src.services.application_controller.TranslationService') as mock_translation_service:
            
            yield {
                'model_manager': mock_model_manager.return_value,
                'audio_processor': mock_audio_processor.return_value,
                'batch_processor': mock_batch_processor.return_value,
                'subtitle_generator': mock_subtitle_generator.return_value,
                'translation_service': mock_translation_service.return_value
            }
    
    def test_initialization(self, mock_services):
        """Test ApplicationController initialization."""
        controller = ApplicationController()
        
        assert controller.state == ApplicationState.IDLE
        assert isinstance(controller.session_data, SessionData)
        assert controller.current_files == []
        assert controller.current_options is None
        assert controller.progress_callback is None
    
    def test_initialization_with_custom_params(self, temp_dir, mock_services):
        """Test ApplicationController initialization with custom parameters."""
        controller = ApplicationController(temp_dir=temp_dir, device="cpu")
        
        assert controller.temp_dir == temp_dir
        assert controller.device == "cpu"
        assert controller.state == ApplicationState.IDLE
    
    def test_set_progress_callback(self, mock_services):
        """Test setting progress callback."""
        controller = ApplicationController()
        callback = Mock()
        
        controller.set_progress_callback(callback)
        assert controller.progress_callback == callback
    
    def test_get_processing_status_idle(self, mock_services):
        """Test getting processing status when idle."""
        controller = ApplicationController()
        
        status = controller.get_processing_status()
        
        assert isinstance(status, ProcessingStatus)
        assert not status.is_active
        assert status.current_file is None
        assert status.progress_percentage == 0.0
        assert status.current_operation == ""
    
    def test_get_processing_status_active(self, mock_services, temp_dir):
        """Test getting processing status when processing."""
        controller = ApplicationController()
        
        # Simulate active processing
        controller.state = ApplicationState.PROCESSING_SINGLE
        controller.current_files = [os.path.join(temp_dir, "test.mp3")]
        controller.current_progress = 50.0
        controller.current_operation = "Processing audio"
        controller.processing_start_time = time.time() - 10  # 10 seconds ago
        
        status = controller.get_processing_status()
        
        assert status.is_active
        assert status.current_file == controller.current_files[0]
        assert status.progress_percentage == 50.0
        assert status.current_operation == "Processing audio"
        assert status.estimated_time_remaining is not None
    
    def test_cancel_processing_when_idle(self, mock_services):
        """Test cancelling processing when idle."""
        controller = ApplicationController()
        
        result = controller.cancel_processing()
        assert result is True
        assert controller.state == ApplicationState.IDLE
    
    def test_cancel_processing_when_active(self, mock_services):
        """Test cancelling processing when active."""
        controller = ApplicationController()
        controller.state = ApplicationState.PROCESSING_SINGLE
        
        # Mock successful cancellation
        mock_services['audio_processor'].cancel_processing.return_value = True
        
        result = controller.cancel_processing()
        
        assert result is True
        assert controller.state == ApplicationState.IDLE
        mock_services['audio_processor'].cancel_processing.assert_called_once()
    
    def test_validate_processing_inputs_valid(self, mock_services, temp_dir, sample_options):
        """Test input validation with valid inputs."""
        controller = ApplicationController()
        
        # Create a test file
        test_file = os.path.join(temp_dir, "test.mp3")
        with open(test_file, 'w') as f:
            f.write("test")
        
        # Should not raise any exception
        controller._validate_processing_inputs([test_file], sample_options)
    
    def test_validate_processing_inputs_missing_file(self, mock_services, sample_options):
        """Test input validation with missing file."""
        controller = ApplicationController()
        
        with pytest.raises(ValidationError, match="File not found"):
            controller._validate_processing_inputs(["/nonexistent/file.mp3"], sample_options)
    
    def test_validate_processing_inputs_no_files(self, mock_services, sample_options):
        """Test input validation with no files."""
        controller = ApplicationController()
        
        with pytest.raises(ValidationError, match="No files provided"):
            controller._validate_processing_inputs([], sample_options)
    
    def test_validate_processing_inputs_invalid_options(self, mock_services, temp_dir):
        """Test input validation with invalid options."""
        controller = ApplicationController()
        
        # Create a test file
        test_file = os.path.join(temp_dir, "test.mp3")
        with open(test_file, 'w') as f:
            f.write("test")
        
        # Create invalid options (missing output directory)
        invalid_options = ProcessingOptions(
            model_size=ModelSize.TINY,
            export_formats=[ExportFormat.SRT],
            output_directory=""  # Invalid
        )
        
        with pytest.raises(ValidationError, match="Invalid processing options"):
            controller._validate_processing_inputs([test_file], invalid_options)
    
    def test_session_data_methods(self, mock_services):
        """Test session data management methods."""
        controller = ApplicationController()
        
        # Test recent files
        controller.session_data.add_recent_file("/path/to/file1.mp3")
        controller.session_data.add_recent_file("/path/to/file2.mp3")
        
        recent_files = controller.get_recent_files()
        assert len(recent_files) == 2
        assert recent_files[0] == "/path/to/file2.mp3"  # Most recent first
        
        # Test processing history
        history = controller.get_processing_history()
        assert isinstance(history, list)
        
        # Test last processing options
        assert controller.get_last_processing_options() is None
    
    def test_set_last_directories(self, mock_services):
        """Test setting last used directories."""
        controller = ApplicationController()
        
        controller.set_last_directories(input_dir="/input", output_dir="/output")
        
        assert controller.session_data.last_input_directory == "/input"
        assert controller.session_data.last_output_directory == "/output"
    
    def test_get_supported_audio_formats(self, mock_services):
        """Test getting supported audio formats."""
        controller = ApplicationController()
        
        # Mock the audio processor method
        mock_services['audio_processor'].get_supported_audio_formats.return_value = ['.mp3', '.wav']
        
        formats = controller.get_supported_audio_formats()
        
        assert formats == ['.mp3', '.wav']
        mock_services['audio_processor'].get_supported_audio_formats.assert_called_once()
    
    def test_get_available_models(self, mock_services):
        """Test getting available models."""
        from src.services.interfaces import ModelType
        
        controller = ApplicationController()
        
        # Mock the model manager method
        mock_services['model_manager'].list_available_models.return_value = {
            ModelType.DEMUCS: [ModelSize.TINY, ModelSize.BASE],
            ModelType.WHISPERX: [ModelSize.TINY, ModelSize.BASE]
        }
        
        models = controller.get_available_models()
        
        expected = {
            'demucs': ['tiny', 'base'],
            'whisperx': ['tiny', 'base']
        }
        assert models == expected
    
    def test_get_device_info(self, mock_services):
        """Test getting device information."""
        controller = ApplicationController()
        
        # Mock the audio processor method
        mock_services['audio_processor'].get_device_info.return_value = {
            'device': 'cpu',
            'temp_dir': '/tmp'
        }
        mock_services['audio_processor'].get_supported_audio_formats.return_value = ['.mp3']
        
        device_info = controller.get_device_info()
        
        assert 'device' in device_info
        assert 'application_state' in device_info
        assert 'models_available' in device_info
        assert 'supported_formats' in device_info
        assert device_info['application_state'] == 'idle'
    
    def test_progress_update_callback(self, mock_services):
        """Test progress update callback functionality."""
        controller = ApplicationController()
        callback = Mock()
        controller.set_progress_callback(callback)
        
        # Test progress update
        controller._update_progress(50.0, "Test message")
        
        callback.assert_called_once_with(50.0, "Test message")
        assert controller.current_progress == 50.0
        assert controller.current_operation == "Test message"
    
    def test_cleanup_processing_context(self, mock_services):
        """Test cleanup of processing context."""
        controller = ApplicationController()
        
        # Set up some processing context
        controller.current_files = ["/test/file.mp3"]
        controller.current_options = Mock()
        controller.current_result = Mock()
        controller.processing_start_time = time.time()
        controller.current_progress = 50.0
        controller.current_operation = "Processing"
        
        # Clean up
        controller._cleanup_processing_context()
        
        # Verify cleanup
        assert controller.current_files == []
        assert controller.current_options is None
        assert controller.current_result is None
        assert controller.processing_start_time is None
        assert controller.current_progress == 0.0
        assert controller.current_operation == ""
        
        # Verify audio processor cleanup was called
        mock_services['audio_processor'].cleanup_temp_files.assert_called_once()


class TestSessionData:
    """Test cases for SessionData class."""
    
    def test_add_recent_file(self):
        """Test adding files to recent files list."""
        session = SessionData()
        
        session.add_recent_file("/path/to/file1.mp3")
        session.add_recent_file("/path/to/file2.mp3")
        
        assert len(session.recent_files) == 2
        assert session.recent_files[0] == "/path/to/file2.mp3"  # Most recent first
        assert session.recent_files[1] == "/path/to/file1.mp3"
    
    def test_add_recent_file_duplicate(self):
        """Test adding duplicate file to recent files."""
        session = SessionData()
        
        session.add_recent_file("/path/to/file1.mp3")
        session.add_recent_file("/path/to/file2.mp3")
        session.add_recent_file("/path/to/file1.mp3")  # Duplicate
        
        assert len(session.recent_files) == 2
        assert session.recent_files[0] == "/path/to/file1.mp3"  # Moved to front
        assert session.recent_files[1] == "/path/to/file2.mp3"
    
    def test_add_recent_file_max_limit(self):
        """Test recent files list respects maximum limit."""
        session = SessionData()
        
        # Add more than max_recent files
        for i in range(15):
            session.add_recent_file(f"/path/to/file{i}.mp3")
        
        assert len(session.recent_files) == 10  # Default max_recent
        assert session.recent_files[0] == "/path/to/file14.mp3"  # Most recent
    
    def test_add_processing_record(self):
        """Test adding processing record to history."""
        session = SessionData()
        
        options = ProcessingOptions(
            model_size=ModelSize.TINY,
            export_formats=[ExportFormat.SRT],
            output_directory="/output"
        )
        
        result = ProcessingResult(
            success=True,
            output_files=["/output/test.srt"],
            processing_time=10.5
        )
        
        session.add_processing_record(["/input/test.mp3"], options, result, 10.5)
        
        assert len(session.processing_history) == 1
        record = session.processing_history[0]
        
        assert record['files'] == ["/input/test.mp3"]
        assert record['success'] is True
        assert record['processing_time'] == 10.5
        assert record['output_files'] == ["/output/test.srt"]
        assert record['model_size'] == 'tiny'
        assert record['export_formats'] == ['srt']
        assert 'timestamp' in record
    
    def test_processing_history_limit(self):
        """Test processing history respects maximum limit."""
        session = SessionData()
        
        options = ProcessingOptions(
            model_size=ModelSize.TINY,
            export_formats=[ExportFormat.SRT],
            output_directory="/output"
        )
        
        result = ProcessingResult(
            success=True,
            output_files=[],
            processing_time=1.0
        )
        
        # Add more than 50 records
        for i in range(55):
            session.add_processing_record([f"/input/test{i}.mp3"], options, result, 1.0)
        
        assert len(session.processing_history) == 50  # Maximum limit