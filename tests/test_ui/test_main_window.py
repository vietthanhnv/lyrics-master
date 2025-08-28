"""
Tests for the main application window.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from PyQt6.QtCore import Qt, QUrl, QMimeData
from PyQt6.QtGui import QDragEnterEvent, QDropEvent
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication

from src.ui.main_window import MainWindow
from src.models.data_models import ProcessingOptions, ModelSize, ExportFormat


@pytest.fixture
def app():
    """Create QApplication instance for testing."""
    return QApplication.instance() or QApplication([])


@pytest.fixture
def main_window(app):
    """Create MainWindow instance for testing."""
    window = MainWindow()
    return window


@pytest.fixture
def temp_audio_files():
    """Create temporary audio files for testing."""
    files = []
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create test audio files
        for ext in ['.mp3', '.wav', '.flac']:
            file_path = os.path.join(temp_dir, f"test{ext}")
            Path(file_path).touch()
            files.append(file_path)
        
        yield files


@pytest.fixture
def temp_lyric_file():
    """Create temporary lyric file for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        file_path = os.path.join(temp_dir, "test.txt")
        Path(file_path).write_text("Test lyrics content")
        yield file_path


class TestMainWindow:
    """Test cases for MainWindow class."""
    
    def test_window_initialization(self, main_window):
        """Test that the main window initializes correctly."""
        assert main_window.windowTitle() == "Lyric-to-Subtitle App"
        assert main_window.minimumSize().width() == 1200
        assert main_window.minimumSize().height() == 800
        assert len(main_window.audio_files) == 0
        assert main_window.lyric_file is None
        assert main_window.options_panel is not None
        
    def test_supported_formats(self, main_window):
        """Test that supported formats are correctly defined."""
        expected_audio = {'.mp3', '.wav', '.flac', '.ogg', '.m4a', '.aac'}
        expected_lyric = {'.txt', '.lrc'}
        
        assert set(main_window.SUPPORTED_AUDIO_FORMATS.keys()) == expected_audio
        assert set(main_window.SUPPORTED_LYRIC_FORMATS.keys()) == expected_lyric
        
    def test_audio_file_validation(self, main_window, temp_audio_files):
        """Test audio file format validation."""
        # Test valid files
        for file_path in temp_audio_files:
            assert main_window._is_valid_audio_file(file_path)
            
        # Test invalid file
        with tempfile.NamedTemporaryFile(suffix='.txt') as temp_file:
            assert not main_window._is_valid_audio_file(temp_file.name)
            
        # Test non-existent file
        assert not main_window._is_valid_audio_file("/non/existent/file.mp3")
        
    def test_lyric_file_validation(self, main_window, temp_lyric_file):
        """Test lyric file format validation."""
        # Test valid file
        assert main_window._is_valid_lyric_file(temp_lyric_file)
        
        # Test invalid file
        with tempfile.NamedTemporaryFile(suffix='.mp3') as temp_file:
            assert not main_window._is_valid_lyric_file(temp_file.name)
            
    def test_add_audio_files(self, main_window, temp_audio_files):
        """Test adding audio files to the selection."""
        # Initially no files
        assert len(main_window.audio_files) == 0
        assert not main_window.clear_audio_btn.isEnabled()
        assert not main_window.process_btn.isEnabled()
        
        # Add valid files
        main_window._add_audio_files(temp_audio_files)
        
        assert len(main_window.audio_files) == len(temp_audio_files)
        assert main_window.clear_audio_btn.isEnabled()
        assert main_window.process_btn.isEnabled()
        assert main_window.audio_files_list.count() == len(temp_audio_files)
        
    def test_clear_audio_files(self, main_window, temp_audio_files):
        """Test clearing audio files."""
        # Add files first
        main_window._add_audio_files(temp_audio_files)
        assert len(main_window.audio_files) > 0
        
        # Clear files
        main_window._clear_audio_files()
        
        assert len(main_window.audio_files) == 0
        assert not main_window.clear_audio_btn.isEnabled()
        assert not main_window.process_btn.isEnabled()
        assert main_window.audio_files_list.count() == 0
        
    def test_lyric_file_selection(self, main_window, temp_lyric_file):
        """Test lyric file selection and clearing."""
        # Initially no lyric file
        assert main_window.lyric_file is None
        assert not main_window.clear_lyric_btn.isEnabled()
        
        # Set lyric file
        main_window.lyric_file = temp_lyric_file
        main_window._update_lyric_file_display()
        
        assert main_window.lyric_file == temp_lyric_file
        assert main_window.clear_lyric_btn.isEnabled()
        
        # Clear lyric file
        main_window._clear_lyric_file()
        
        assert main_window.lyric_file is None
        assert not main_window.clear_lyric_btn.isEnabled()
        
    def test_drag_enter_event_valid_audio(self, main_window, temp_audio_files):
        """Test drag enter event with valid audio files."""
        # Create mock drag event with audio files
        mime_data = QMimeData()
        urls = [QUrl.fromLocalFile(file_path) for file_path in temp_audio_files]
        mime_data.setUrls(urls)
        
        event = Mock()
        event.mimeData.return_value = mime_data
        
        main_window.dragEnterEvent(event)
        
        event.acceptProposedAction.assert_called_once()
        
    def test_drag_enter_event_invalid_files(self, main_window):
        """Test drag enter event with invalid files."""
        # Create mock drag event with non-audio files
        mime_data = QMimeData()
        with tempfile.NamedTemporaryFile(suffix='.txt') as temp_file:
            urls = [QUrl.fromLocalFile(temp_file.name)]
            mime_data.setUrls(urls)
            
            event = Mock()
            event.mimeData.return_value = mime_data
            
            main_window.dragEnterEvent(event)
            
            event.ignore.assert_called_once()
            
    def test_drop_event_audio_files(self, main_window, temp_audio_files):
        """Test drop event with audio files."""
        # Create mock drop event
        mime_data = QMimeData()
        urls = [QUrl.fromLocalFile(file_path) for file_path in temp_audio_files]
        mime_data.setUrls(urls)
        
        event = Mock()
        event.mimeData.return_value = mime_data
        
        main_window.dropEvent(event)
        
        assert len(main_window.audio_files) == len(temp_audio_files)
        event.acceptProposedAction.assert_called_once()
        
    def test_get_selected_files(self, main_window, temp_audio_files, temp_lyric_file):
        """Test getting selected files."""
        # Add files
        main_window._add_audio_files(temp_audio_files)
        main_window.lyric_file = temp_lyric_file
        
        # Test getters
        audio_files = main_window.get_selected_audio_files()
        lyric_file = main_window.get_selected_lyric_file()
        
        assert audio_files == temp_audio_files
        assert lyric_file == temp_lyric_file
        
        # Ensure returned list is a copy
        audio_files.clear()
        assert len(main_window.audio_files) == len(temp_audio_files)
        
    def test_processing_enabled_control(self, main_window, temp_audio_files):
        """Test processing button enable/disable control."""
        # Initially disabled (no files)
        assert not main_window.process_btn.isEnabled()
        
        # Still disabled even when explicitly enabled (no files)
        main_window.set_processing_enabled(True)
        assert not main_window.process_btn.isEnabled()
        
        # Add files and enable
        main_window._add_audio_files(temp_audio_files)
        main_window.set_processing_enabled(True)
        assert main_window.process_btn.isEnabled()
        
        # Disable processing
        main_window.set_processing_enabled(False)
        assert not main_window.process_btn.isEnabled()
        
    def test_status_update(self, main_window):
        """Test status bar updates."""
        test_message = "Test status message"
        main_window.update_status(test_message)
        
        assert main_window.statusBar().currentMessage() == test_message
        
    @patch('src.ui.main_window.QMessageBox.warning')
    def test_invalid_files_warning(self, mock_warning, main_window):
        """Test warning dialog for invalid files."""
        # Create mix of valid and invalid files
        with tempfile.TemporaryDirectory() as temp_dir:
            valid_file = os.path.join(temp_dir, "valid.mp3")
            invalid_file = os.path.join(temp_dir, "invalid.txt")
            
            Path(valid_file).touch()
            Path(invalid_file).touch()
            
            main_window._add_audio_files([valid_file, invalid_file])
            
            # Should show warning for invalid file
            mock_warning.assert_called_once()
            
            # Should still add valid file
            assert len(main_window.audio_files) == 1
            assert valid_file in main_window.audio_files
            
    def test_signals_emitted(self, main_window, temp_audio_files, temp_lyric_file):
        """Test that appropriate signals are emitted."""
        # Mock signal connections
        files_selected_mock = Mock()
        lyric_selected_mock = Mock()
        processing_requested_mock = Mock()
        
        main_window.files_selected.connect(files_selected_mock)
        main_window.lyric_file_selected.connect(lyric_selected_mock)
        main_window.processing_requested.connect(processing_requested_mock)
        
        # Add audio files - should emit files_selected
        main_window._add_audio_files(temp_audio_files)
        files_selected_mock.assert_called_once_with(main_window.audio_files)
        
        # Select lyric file - should emit lyric_file_selected
        main_window.lyric_file = temp_lyric_file
        main_window.lyric_file_selected.emit(temp_lyric_file)
        lyric_selected_mock.assert_called_once_with(temp_lyric_file)
        
        # Start processing - should emit processing_requested
        main_window._start_processing()
        processing_requested_mock.assert_called_once()
        
    def test_options_panel_integration(self, main_window):
        """Test that options panel is properly integrated."""
        # Options panel should be present
        assert main_window.options_panel is not None
        
        # Should be able to get and set options
        options = main_window.get_processing_options()
        assert isinstance(options, ProcessingOptions)
        
        # Test setting custom options
        custom_options = ProcessingOptions(
            model_size=ModelSize.LARGE,
            export_formats=[ExportFormat.ASS],
            karaoke_mode=True,
            output_directory="/test/output"
        )
        
        main_window.set_processing_options(custom_options)
        retrieved_options = main_window.get_processing_options()
        
        assert retrieved_options.model_size == ModelSize.LARGE
        assert ExportFormat.ASS in retrieved_options.export_formats
        assert retrieved_options.karaoke_mode is True
        assert retrieved_options.output_directory == "/test/output"
        
    @patch('src.ui.main_window.QMessageBox.warning')
    def test_processing_validation(self, mock_warning, main_window, temp_audio_files):
        """Test that processing validates options before starting."""
        # Add audio files
        main_window._add_audio_files(temp_audio_files)
        
        # Set invalid options (empty output directory)
        main_window.options_panel.output_dir_edit.setText("")
        
        # Try to start processing
        main_window._start_processing()
        
        # Should show validation error
        mock_warning.assert_called_once()
        
    def test_options_changed_status_update(self, main_window):
        """Test that status bar updates when options change."""
        # Set invalid options
        main_window.options_panel.output_dir_edit.setText("")
        main_window.options_panel.translation_check.setChecked(True)
        
        # Trigger options change
        main_window._on_options_changed(main_window.get_processing_options())
        
        # Status should indicate configuration issues
        status = main_window.statusBar().currentMessage()
        assert "configuration issues" in status.lower() or "error" in status.lower()