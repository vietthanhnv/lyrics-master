#!/usr/bin/env python3
"""
Example demonstrating the results panel and error handling UI functionality.

This example shows how to use the ResultsPanel to display:
- Successful processing results with file listings
- Error messages with recovery suggestions
- Batch processing results with statistics
- Different error categories and their handling

Run this script to see an interactive demonstration of the results display system.
"""

import sys
import os
import tempfile
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QPushButton, QLabel, QGroupBox
from PyQt6.QtCore import Qt

from ui.results_panel import ResultsPanel
from models.data_models import (
    ProcessingResult, BatchResult, BatchFileReport, BatchSummaryStats,
    AlignmentData, Segment, WordSegment
)


class ResultsPanelDemo(QMainWindow):
    """Demo application for the results panel."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Results Panel Demo - Lyric-to-Subtitle App")
        self.setGeometry(100, 100, 1200, 800)
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Title
        title = QLabel("Results Panel and Error Handling Demo")
        title.setStyleSheet("font-size: 18px; font-weight: bold; margin: 10px;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Control buttons
        self._create_control_buttons(layout)
        
        # Results panel
        self.results_panel = ResultsPanel()
        layout.addWidget(self.results_panel)
        
        # Connect signals
        self.results_panel.retry_requested.connect(self._on_retry_requested)
        self.results_panel.open_file_requested.connect(self._on_open_file_requested)
        self.results_panel.show_in_folder_requested.connect(self._on_show_in_folder_requested)
        
        # Create sample data
        self._create_sample_data()
        
    def _create_control_buttons(self, layout):
        """Create control buttons for demo."""
        controls_group = QGroupBox("Demo Controls")
        controls_layout = QVBoxLayout(controls_group)
        
        # Success results buttons
        success_row = QHBoxLayout()
        
        self.show_success_btn = QPushButton("Show Success Results")
        self.show_success_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 10px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        self.show_success_btn.clicked.connect(self._show_success_results)
        success_row.addWidget(self.show_success_btn)
        
        self.show_batch_btn = QPushButton("Show Batch Results")
        self.show_batch_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                padding: 10px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        self.show_batch_btn.clicked.connect(self._show_batch_results)
        success_row.addWidget(self.show_batch_btn)
        
        controls_layout.addLayout(success_row)
        
        # Error buttons
        error_row1 = QHBoxLayout()
        
        self.show_validation_error_btn = QPushButton("Validation Error")
        self.show_validation_error_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF5722;
                color: white;
                padding: 10px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #E64A19;
            }
        """)
        self.show_validation_error_btn.clicked.connect(self._show_validation_error)
        error_row1.addWidget(self.show_validation_error_btn)
        
        self.show_processing_error_btn = QPushButton("Processing Error")
        self.show_processing_error_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                padding: 10px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
        """)
        self.show_processing_error_btn.clicked.connect(self._show_processing_error)
        error_row1.addWidget(self.show_processing_error_btn)
        
        controls_layout.addLayout(error_row1)
        
        error_row2 = QHBoxLayout()
        
        self.show_export_error_btn = QPushButton("Export Error")
        self.show_export_error_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                padding: 10px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
        """)
        self.show_export_error_btn.clicked.connect(self._show_export_error)
        error_row2.addWidget(self.show_export_error_btn)
        
        self.show_system_error_btn = QPushButton("System Error")
        self.show_system_error_btn.setStyleSheet("""
            QPushButton {
                background-color: #9C27B0;
                color: white;
                padding: 10px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #7B1FA2;
            }
        """)
        self.show_system_error_btn.clicked.connect(self._show_system_error)
        error_row2.addWidget(self.show_system_error_btn)
        
        controls_layout.addLayout(error_row2)
        
        # Utility buttons
        util_row = QHBoxLayout()
        
        self.hide_results_btn = QPushButton("Hide Results")
        self.hide_results_btn.setStyleSheet("""
            QPushButton {
                background-color: #757575;
                color: white;
                padding: 10px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #616161;
            }
        """)
        self.hide_results_btn.clicked.connect(self._hide_results)
        util_row.addWidget(self.hide_results_btn)
        
        controls_layout.addLayout(util_row)
        
        layout.addWidget(controls_group)
        
    def _create_sample_data(self):
        """Create sample data for demonstration."""
        # Create temporary files for demonstration
        self.temp_dir = tempfile.mkdtemp()
        
        # Create sample output files
        self.sample_output_files = []
        formats = [
            ('srt', 'SubRip Subtitle'),
            ('ass', 'Advanced SubStation Alpha'),
            ('vtt', 'WebVTT Subtitle'),
            ('json', 'JSON Alignment Data')
        ]
        
        for ext, desc in formats:
            file_path = os.path.join(self.temp_dir, f"sample_output.{ext}")
            with open(file_path, 'w', encoding='utf-8') as f:
                if ext == 'srt':
                    f.write("1\n00:00:00,000 --> 00:00:03,000\nHello world\n\n")
                    f.write("2\n00:00:03,000 --> 00:00:06,000\nThis is a test\n\n")
                elif ext == 'ass':
                    f.write("[Script Info]\nTitle: Sample Karaoke\n\n")
                    f.write("[V4+ Styles]\nFormat: Name, Fontname, Fontsize\n")
                    f.write("Style: Default,Arial,20\n\n")
                    f.write("[Events]\nFormat: Layer, Start, End, Style, Text\n")
                    f.write("Dialogue: 0,0:00:00.00,0:00:03.00,Default,Hello world\n")
                elif ext == 'vtt':
                    f.write("WEBVTT\n\n00:00.000 --> 00:03.000\nHello world\n\n")
                    f.write("00:03.000 --> 00:06.000\nThis is a test\n\n")
                elif ext == 'json':
                    f.write('{"segments": [{"start": 0.0, "end": 3.0, "text": "Hello world"}]}')
            
            self.sample_output_files.append(file_path)
        
        # Create sample alignment data
        segments = [
            Segment(0.0, 3.0, "Hello world", 0.95, 0),
            Segment(3.0, 6.0, "This is a test", 0.88, 1),
            Segment(6.0, 10.0, "Sample subtitle content", 0.92, 2)
        ]
        
        word_segments = [
            WordSegment("Hello", 0.0, 1.0, 0.95, 0),
            WordSegment("world", 1.0, 2.0, 0.92, 0),
            WordSegment("This", 3.0, 3.5, 0.88, 1),
            WordSegment("is", 3.5, 4.0, 0.90, 1),
            WordSegment("a", 4.0, 4.2, 0.85, 1),
            WordSegment("test", 4.2, 5.0, 0.87, 1),
            WordSegment("Sample", 6.0, 6.8, 0.92, 2),
            WordSegment("subtitle", 6.8, 7.8, 0.89, 2),
            WordSegment("content", 7.8, 9.0, 0.94, 2)
        ]
        
        self.sample_alignment_data = AlignmentData(
            segments=segments,
            word_segments=word_segments,
            confidence_scores=[0.95, 0.88, 0.92],
            audio_duration=10.0,
            source_file="sample_audio.wav"
        )
        
        # Create sample batch result
        self.sample_batch_result = self._create_sample_batch_result()
        
    def _create_sample_batch_result(self):
        """Create sample batch processing result."""
        file_reports = [
            BatchFileReport(
                file_path="/demo/audio/song1.wav",
                file_name="song1.wav",
                status="completed",
                success=True,
                processing_time=18.5,
                output_files=["/demo/output/song1.srt", "/demo/output/song1.ass"],
                file_size=3145728,  # 3MB
                audio_duration=210.0  # 3.5 minutes
            ),
            BatchFileReport(
                file_path="/demo/audio/song2.wav",
                file_name="song2.wav",
                status="completed",
                success=True,
                processing_time=22.1,
                output_files=["/demo/output/song2.srt", "/demo/output/song2.vtt"],
                file_size=4194304,  # 4MB
                audio_duration=280.0  # 4.67 minutes
            ),
            BatchFileReport(
                file_path="/demo/audio/song3.wav",
                file_name="song3.wav",
                status="failed",
                success=False,
                processing_time=3.2,
                output_files=[],
                error_message="Insufficient memory for processing",
                error_category="system",
                file_size=8388608,  # 8MB
                audio_duration=420.0  # 7 minutes
            ),
            BatchFileReport(
                file_path="/demo/audio/song4.wav",
                file_name="song4.wav",
                status="completed",
                success=True,
                processing_time=15.8,
                output_files=["/demo/output/song4.srt"],
                file_size=2097152,  # 2MB
                audio_duration=165.0  # 2.75 minutes
            ),
            BatchFileReport(
                file_path="/demo/audio/song5.wav",
                file_name="song5.wav",
                status="failed",
                success=False,
                processing_time=1.1,
                output_files=[],
                error_message="Unsupported audio format",
                error_category="validation",
                file_size=1048576,  # 1MB
                audio_duration=90.0  # 1.5 minutes
            )
        ]
        
        processing_results = [
            ProcessingResult(True, ["/demo/output/song1.srt", "/demo/output/song1.ass"], 18.5),
            ProcessingResult(True, ["/demo/output/song2.srt", "/demo/output/song2.vtt"], 22.1),
            ProcessingResult(False, [], 3.2, "Insufficient memory for processing"),
            ProcessingResult(True, ["/demo/output/song4.srt"], 15.8),
            ProcessingResult(False, [], 1.1, "Unsupported audio format")
        ]
        
        batch_result = BatchResult(
            total_files=5,
            successful_files=3,
            failed_files=2,
            processing_results=processing_results,
            total_processing_time=60.7,
            file_reports=file_reports,
            cancelled_files=0
        )
        
        batch_result.summary_stats = batch_result.generate_summary_stats()
        return batch_result
        
    def _show_success_results(self):
        """Show successful processing results."""
        result = ProcessingResult(
            success=True,
            output_files=self.sample_output_files,
            processing_time=18.5,
            alignment_data=self.sample_alignment_data
        )
        
        self.results_panel.show_success_results(result, 18.5)
        print("✓ Showing successful processing results")
        
    def _show_batch_results(self):
        """Show batch processing results."""
        self.results_panel.show_batch_results(self.sample_batch_result)
        print("📊 Showing batch processing results")
        
    def _show_validation_error(self):
        """Show validation error example."""
        error_message = "The selected audio file format is not supported or the file is corrupted."
        suggestions = [
            "Check that the file is a valid audio file (.mp3, .wav, .flac, .ogg)",
            "Try playing the file in a media player to verify it's not corrupted",
            "Convert the file to WAV format using audio conversion software",
            "Ensure the file is not protected by DRM or other restrictions"
        ]
        detailed_error = """
AudioValidationError: Invalid audio file format
File: /path/to/problematic_audio.xyz
Expected formats: ['.mp3', '.wav', '.flac', '.ogg', '.m4a']
Detected format: '.xyz' (unsupported)
File size: 0 bytes (possibly empty or corrupted)
        """.strip()
        
        self.results_panel.show_error_results(
            error_message, "validation", suggestions, detailed_error
        )
        print("⚠ Showing validation error example")
        
    def _show_processing_error(self):
        """Show processing error example."""
        error_message = "Processing failed due to insufficient system resources. The audio file is too large for the available memory."
        suggestions = [
            "Close other applications to free up system memory",
            "Try using a smaller model size (tiny or base instead of large)",
            "Split the audio file into smaller segments",
            "Ensure at least 4GB of RAM is available for processing",
            "Check available disk space for temporary files"
        ]
        detailed_error = """
ProcessingError: Out of memory during vocal separation
Model: demucs-large
Audio duration: 45 minutes
Required memory: ~8GB
Available memory: 2.1GB
Temporary files: /tmp/audio_processing/
Disk space available: 15GB
        """.strip()
        
        self.results_panel.show_error_results(
            error_message, "processing", suggestions, detailed_error
        )
        print("🔧 Showing processing error example")
        
    def _show_export_error(self):
        """Show export error example."""
        error_message = "Failed to save subtitle files to the selected output directory. Check file permissions and available disk space."
        suggestions = [
            "Check that you have write permissions for the output directory",
            "Ensure sufficient disk space is available (at least 100MB free)",
            "Try selecting a different output directory",
            "Close any applications that might be using the output files",
            "Run the application as administrator if necessary"
        ]
        detailed_error = """
ExportError: Permission denied when writing subtitle files
Output directory: /restricted/folder/
Required permissions: write, create
Current permissions: read-only
Available space: 50MB
Files to create: ['output.srt', 'output.ass', 'output.vtt']
        """.strip()
        
        self.results_panel.show_error_results(
            error_message, "export", suggestions, detailed_error
        )
        print("💾 Showing export error example")
        
    def _show_system_error(self):
        """Show system error example."""
        error_message = "A critical system error occurred during processing. The application encountered an unexpected condition."
        suggestions = [
            "Restart the application and try again",
            "Check that your system meets the minimum requirements",
            "Update your graphics drivers if using GPU acceleration",
            "Verify that all required dependencies are installed",
            "Contact technical support if the problem persists"
        ]
        detailed_error = """
SystemError: CUDA out of memory
GPU: NVIDIA GeForce RTX 3060
CUDA Version: 11.8
Available VRAM: 12GB
Required VRAM: 16GB
Fallback to CPU: Failed (insufficient RAM)
Stack trace:
  File "vocal_separator.py", line 145, in separate_vocals
    model.load_state_dict(checkpoint)
  RuntimeError: CUDA out of memory
        """.strip()
        
        self.results_panel.show_error_results(
            error_message, "system", suggestions, detailed_error
        )
        print("🖥 Showing system error example")
        
    def _hide_results(self):
        """Hide the results panel."""
        self.results_panel.hide_results()
        print("👁 Results panel hidden")
        
    def _on_retry_requested(self, file_path):
        """Handle retry request."""
        print(f"🔄 Retry requested for: {file_path}")
        
    def _on_open_file_requested(self, file_path):
        """Handle file open request."""
        print(f"📂 Open file requested: {file_path}")
        
        # In a real application, this would open the file with the default application
        if os.path.exists(file_path):
            print(f"   File exists and would be opened")
        else:
            print(f"   File does not exist (this is expected for demo files)")
            
    def _on_show_in_folder_requested(self, folder_path):
        """Handle show in folder request."""
        print(f"📁 Show in folder requested: {folder_path}")
        
        # In a real application, this would open the folder in the file explorer
        if os.path.exists(folder_path):
            print(f"   Folder exists and would be opened")
        else:
            print(f"   Folder does not exist (this is expected for demo folders)")
            
    def closeEvent(self, event):
        """Clean up temporary files on close."""
        import shutil
        if hasattr(self, 'temp_dir') and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
        event.accept()


def main():
    """Run the results panel demo."""
    app = QApplication(sys.argv)
    
    # Set application properties
    app.setApplicationName("Results Panel Demo")
    app.setApplicationVersion("1.0.0")
    
    # Create and show demo window
    demo = ResultsPanelDemo()
    demo.show()
    
    print("Results Panel Demo Started")
    print("=" * 50)
    print("Use the buttons to demonstrate different result types:")
    print("• Success Results - Shows successful processing with file listings")
    print("• Batch Results - Shows batch processing statistics and individual file results")
    print("• Error Examples - Shows different error categories with recovery suggestions")
    print("• Each error type demonstrates category-specific suggestions")
    print("=" * 50)
    
    # Run the application
    sys.exit(app.exec())


if __name__ == "__main__":
    main()