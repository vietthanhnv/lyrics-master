#!/usr/bin/env python3
"""
Example demonstrating the main window functionality.

This example shows how to:
1. Create and display the main window
2. Handle file selection events
3. Connect to processing signals
"""

import sys
import tempfile
from pathlib import Path
from PyQt6.QtWidgets import QApplication

# Add src directory to Python path
src_dir = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_dir))

from ui.main_window import MainWindow
from models.data_models import ProcessingOptions


def create_sample_files():
    """Create sample audio and lyric files for demonstration."""
    temp_dir = Path(tempfile.mkdtemp())
    
    # Create sample audio files
    audio_files = []
    for i, ext in enumerate(['.mp3', '.wav', '.flac'], 1):
        audio_file = temp_dir / f"sample_song_{i}{ext}"
        audio_file.write_text(f"# Sample audio file {i}")
        audio_files.append(str(audio_file))
    
    # Create sample lyric file
    lyric_file = temp_dir / "sample_lyrics.txt"
    lyric_file.write_text("""
Verse 1:
This is a sample song
With some sample lyrics
For demonstration purposes

Chorus:
La la la la la
Testing the application
La la la la la
""")
    
    return audio_files, str(lyric_file), temp_dir


def on_files_selected(files):
    """Handle audio files selection."""
    print(f"Audio files selected: {len(files)} files")
    for i, file_path in enumerate(files, 1):
        print(f"  {i}. {Path(file_path).name}")


def on_lyric_file_selected(file_path):
    """Handle lyric file selection."""
    print(f"Lyric file selected: {Path(file_path).name}")


def on_processing_requested(files, options):
    """Handle processing request."""
    print(f"\nProcessing requested for {len(files)} files:")
    print(f"Model size: {options.model_size}")
    print(f"Export formats: {options.export_formats}")
    print(f"Word-level SRT: {options.word_level_srt}")
    print(f"Output directory: {options.output_directory}")
    
    # In a real application, this would start the actual processing
    print("Processing would start here...")


def main():
    """Main example function."""
    app = QApplication(sys.argv)
    app.setApplicationName("Main Window Example")
    
    # Create sample files
    print("Creating sample files...")
    audio_files, lyric_file, temp_dir = create_sample_files()
    print(f"Sample files created in: {temp_dir}")
    
    # Create main window
    window = MainWindow()
    
    # Connect signals to handlers
    window.files_selected.connect(on_files_selected)
    window.lyric_file_selected.connect(on_lyric_file_selected)
    window.processing_requested.connect(on_processing_requested)
    
    # Programmatically add sample files to demonstrate functionality
    print("\nAdding sample files to the window...")
    window._add_audio_files(audio_files)
    
    window.lyric_file = lyric_file
    window._update_lyric_file_display()
    window.lyric_file_selected.emit(lyric_file)
    
    # Show window
    window.show()
    
    print("\nMain window is now displayed!")
    print("You can:")
    print("- See the pre-loaded sample files")
    print("- Try drag-and-drop with other audio files")
    print("- Use the file selection buttons")
    print("- Click 'Start Processing' to see the processing signal")
    print("\nClose the window to exit.")
    
    # Start event loop
    try:
        sys.exit(app.exec())
    finally:
        # Clean up sample files
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)
        print(f"\nCleaned up sample files from: {temp_dir}")


if __name__ == "__main__":
    main()