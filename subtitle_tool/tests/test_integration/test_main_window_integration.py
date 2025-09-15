"""
Integration tests for the main window functionality.
"""

import tempfile
from pathlib import Path

import pytest
from PyQt6.QtWidgets import QApplication

from src.ui.main_window import MainWindow


@pytest.fixture
def app():
    """Create QApplication instance for testing."""
    return QApplication.instance() or QApplication([])


class TestMainWindowIntegration:
    """Integration tests for MainWindow."""
    
    def test_main_window_can_be_created_and_shown(self, app):
        """Test that the main window can be created and shown without errors."""
        window = MainWindow()
        
        # Verify window is created properly
        assert window is not None
        assert window.windowTitle() == "Lyric-to-Subtitle App"
        
        # Show window (this would display it in a real application)
        window.show()
        assert window.isVisible()
        
        # Hide window to clean up
        window.hide()
        
    def test_complete_file_selection_workflow(self, app):
        """Test the complete file selection workflow."""
        window = MainWindow()
        
        # Create temporary test files
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create audio files
            audio_files = []
            for ext in ['.mp3', '.wav']:
                file_path = Path(temp_dir) / f"test{ext}"
                file_path.touch()
                audio_files.append(str(file_path))
            
            # Create lyric file
            lyric_file = Path(temp_dir) / "lyrics.txt"
            lyric_file.write_text("Test lyrics content")
            
            # Test adding audio files
            window._add_audio_files(audio_files)
            assert len(window.get_selected_audio_files()) == 2
            assert window.process_btn.isEnabled()
            
            # Test adding lyric file
            window.lyric_file = str(lyric_file)
            window._update_lyric_file_display()
            assert window.get_selected_lyric_file() == str(lyric_file)
            
            # Test clearing files
            window._clear_audio_files()
            assert len(window.get_selected_audio_files()) == 0
            assert not window.process_btn.isEnabled()
            
            window._clear_lyric_file()
            assert window.get_selected_lyric_file() is None
            
    def test_signal_connections_work(self, app):
        """Test that signal connections work properly."""
        window = MainWindow()
        
        # Track signal emissions
        files_selected_count = 0
        lyric_selected_count = 0
        processing_requested_count = 0
        
        def on_files_selected(files):
            nonlocal files_selected_count
            files_selected_count += 1
            
        def on_lyric_selected(file_path):
            nonlocal lyric_selected_count
            lyric_selected_count += 1
            
        def on_processing_requested(files, options):
            nonlocal processing_requested_count
            processing_requested_count += 1
        
        # Connect signals
        window.files_selected.connect(on_files_selected)
        window.lyric_file_selected.connect(on_lyric_selected)
        window.processing_requested.connect(on_processing_requested)
        
        # Create test files and trigger signals
        with tempfile.TemporaryDirectory() as temp_dir:
            audio_file = Path(temp_dir) / "test.mp3"
            audio_file.touch()
            
            lyric_file = Path(temp_dir) / "lyrics.txt"
            lyric_file.write_text("Test lyrics")
            
            # Add audio file - should trigger files_selected
            window._add_audio_files([str(audio_file)])
            assert files_selected_count == 1
            
            # Emit lyric file selected signal
            window.lyric_file_selected.emit(str(lyric_file))
            assert lyric_selected_count == 1
            
            # Start processing - should trigger processing_requested
            window._start_processing()
            assert processing_requested_count == 1