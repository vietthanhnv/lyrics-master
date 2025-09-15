"""
Main application window with file selection and drag-and-drop support.
"""

import os
from pathlib import Path
from typing import List, Optional, Callable, Dict, Any

from PyQt6.QtCore import Qt, pyqtSignal, QMimeData
from PyQt6.QtGui import QAction, QDragEnterEvent, QDropEvent
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QPushButton, QFileDialog, QGroupBox,
    QListWidget, QListWidgetItem, QMessageBox, QMenuBar,
    QSplitter, QScrollArea
)

from ..models.data_models import ProcessingOptions, ProcessingResult, BatchResult
from .options_panel import OptionsPanel
from .progress_widget import ProgressWidget
from .results_panel import ResultsPanel


class MainWindow(QMainWindow):
    """
    Main application window providing file selection and drag-and-drop functionality.
    
    Supports:
    - Audio file selection via dialog or drag-and-drop
    - Optional lyric file selection
    - File validation and display
    - Integration with processing pipeline
    """
    
    # Signals
    files_selected = pyqtSignal(list)  # Emitted when audio files are selected
    lyric_file_selected = pyqtSignal(str)  # Emitted when lyric file is selected
    processing_requested = pyqtSignal(list, object)  # files, ProcessingOptions
    cancel_processing_requested = pyqtSignal()  # Emitted when user requests cancellation
    
    # Supported audio formats
    SUPPORTED_AUDIO_FORMATS = {
        '.mp3': 'MP3 Audio',
        '.wav': 'WAV Audio', 
        '.flac': 'FLAC Audio',
        '.ogg': 'OGG Audio',
        '.m4a': 'M4A Audio',
        '.aac': 'AAC Audio'
    }
    
    # Supported lyric formats
    SUPPORTED_LYRIC_FORMATS = {
        '.txt': 'Text File',
        '.lrc': 'LRC Lyric File'
    }
    
    def __init__(self):
        super().__init__()
        self.audio_files: List[str] = []
        self.lyric_file: Optional[str] = None
        
        self._setup_ui()
        self._setup_drag_drop()
        self._connect_signals()
        
    def _setup_ui(self):
        """Initialize the user interface components."""
        self.setWindowTitle("Lyric-to-Subtitle App")
        self.setMinimumSize(1200, 800)
        self.resize(1400, 900)
        
        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Create menu bar
        self._create_menu_bar()
        
        # Create horizontal splitter for main content
        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)
        
        # Left panel - File selection and processing
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        # File selection section
        file_group = QGroupBox("File Selection")
        file_layout = QVBoxLayout(file_group)
        
        # Audio files section
        audio_section = QWidget()
        audio_layout = QVBoxLayout(audio_section)
        
        audio_label = QLabel("Audio Files:")
        audio_label.setStyleSheet("font-weight: bold; font-size: 12px;")
        audio_layout.addWidget(audio_label)
        
        # Audio file buttons
        audio_buttons = QHBoxLayout()
        self.select_audio_btn = QPushButton("Select Audio Files")
        self.select_audio_btn.setToolTip("Select one or more audio files (.mp3, .wav, .flac, .ogg)")
        self.clear_audio_btn = QPushButton("Clear")
        self.clear_audio_btn.setEnabled(False)
        
        audio_buttons.addWidget(self.select_audio_btn)
        audio_buttons.addWidget(self.clear_audio_btn)
        audio_buttons.addStretch()
        audio_layout.addLayout(audio_buttons)
        
        # Audio files list
        self.audio_files_list = QListWidget()
        self.audio_files_list.setMaximumHeight(150)
        self.audio_files_list.setToolTip("Selected audio files will appear here")
        audio_layout.addWidget(self.audio_files_list)
        
        file_layout.addWidget(audio_section)
        
        # Lyric file section (optional)
        lyric_section = QWidget()
        lyric_layout = QVBoxLayout(lyric_section)
        
        lyric_label = QLabel("Lyric File (Optional):")
        lyric_label.setStyleSheet("font-weight: bold; font-size: 12px;")
        lyric_layout.addWidget(lyric_label)
        
        # Lyric file buttons
        lyric_buttons = QHBoxLayout()
        self.select_lyric_btn = QPushButton("Select Lyric File")
        self.select_lyric_btn.setToolTip("Select a lyric file (.txt, .lrc) for reference")
        self.clear_lyric_btn = QPushButton("Clear")
        self.clear_lyric_btn.setEnabled(False)
        
        lyric_buttons.addWidget(self.select_lyric_btn)
        lyric_buttons.addWidget(self.clear_lyric_btn)
        lyric_buttons.addStretch()
        lyric_layout.addLayout(lyric_buttons)
        
        # Lyric file display
        self.lyric_file_label = QLabel("No lyric file selected")
        self.lyric_file_label.setStyleSheet("color: gray; font-style: italic;")
        lyric_layout.addWidget(self.lyric_file_label)
        
        file_layout.addWidget(lyric_section)
        
        left_layout.addWidget(file_group)
        
        # Drag and drop instructions
        instructions = QLabel(
            "💡 Tip: You can also drag and drop audio files directly onto this window!"
        )
        instructions.setStyleSheet(
            "background-color: #e8f4fd; border: 1px solid #bee5eb; "
            "border-radius: 4px; padding: 8px; color: #0c5460;"
        )
        instructions.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_layout.addWidget(instructions)
        
        # Processing section
        processing_group = QGroupBox("Processing")
        processing_layout = QVBoxLayout(processing_group)
        
        self.process_btn = QPushButton("Start Processing")
        self.process_btn.setEnabled(False)
        self.process_btn.setStyleSheet(
            "QPushButton { background-color: #007bff; color: white; "
            "font-weight: bold; padding: 12px; border-radius: 4px; font-size: 14px; }"
            "QPushButton:hover { background-color: #0056b3; }"
            "QPushButton:disabled { background-color: #6c757d; }"
        )
        processing_layout.addWidget(self.process_btn)
        
        left_layout.addWidget(processing_group)
        
        # Progress tracking section
        self.progress_widget = ProgressWidget()
        self.progress_widget.setVisible(False)  # Initially hidden
        left_layout.addWidget(self.progress_widget)
        
        # Results display section
        self.results_panel = ResultsPanel()
        self.results_panel.setVisible(False)  # Initially hidden
        left_layout.addWidget(self.results_panel)
        
        left_layout.addStretch()
        
        # Add left panel to splitter
        splitter.addWidget(left_panel)
        
        # Right panel - Options configuration
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        # Options panel title
        options_title = QLabel("Processing Options")
        options_title.setStyleSheet("font-weight: bold; font-size: 14px; padding: 5px;")
        right_layout.addWidget(options_title)
        
        # Create options panel
        self.options_panel = OptionsPanel()
        
        # Put options panel in scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidget(self.options_panel)
        scroll_area.setWidgetResizable(True)
        scroll_area.setMinimumWidth(450)
        right_layout.addWidget(scroll_area)
        
        # Add right panel to splitter
        splitter.addWidget(right_panel)
        
        # Set splitter proportions (60% left, 40% right)
        splitter.setSizes([600, 400])
        
        # Status bar
        self.statusBar().showMessage("Ready - Select audio files to begin")
        
    def _create_menu_bar(self):
        """Create the application menu bar."""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("File")
        
        # Open audio files action
        open_audio_action = QAction("Open Audio Files...", self)
        open_audio_action.setShortcut("Ctrl+O")
        open_audio_action.triggered.connect(self._select_audio_files)
        file_menu.addAction(open_audio_action)
        
        # Open lyric file action
        open_lyric_action = QAction("Open Lyric File...", self)
        open_lyric_action.setShortcut("Ctrl+L")
        open_lyric_action.triggered.connect(self._select_lyric_file)
        file_menu.addAction(open_lyric_action)
        
        file_menu.addSeparator()
        
        # Exit action
        exit_action = QAction("Exit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Help menu
        help_menu = menubar.addMenu("Help")
        
        about_action = QAction("About", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)
        
    def _setup_drag_drop(self):
        """Enable drag and drop functionality for audio files."""
        self.setAcceptDrops(True)
        
    def _connect_signals(self):
        """Connect UI signals to their handlers."""
        self.select_audio_btn.clicked.connect(self._select_audio_files)
        self.clear_audio_btn.clicked.connect(self._clear_audio_files)
        self.select_lyric_btn.clicked.connect(self._select_lyric_file)
        self.clear_lyric_btn.clicked.connect(self._clear_lyric_file)
        self.process_btn.clicked.connect(self._start_processing)
        
        # Connect options panel signals
        self.options_panel.options_changed.connect(self._on_options_changed)
        
        # Connect progress widget signals
        self.progress_widget.cancel_requested.connect(self._on_cancel_requested)
        
        # Connect results panel signals
        self.results_panel.retry_requested.connect(self._on_retry_requested)
        self.results_panel.open_file_requested.connect(self._on_open_file_requested)
        self.results_panel.show_in_folder_requested.connect(self._on_show_in_folder_requested)
        
    def _select_audio_files(self):
        """Open file dialog to select audio files."""
        # Create filter string for supported formats
        audio_filters = []
        for ext, desc in self.SUPPORTED_AUDIO_FORMATS.items():
            audio_filters.append(f"{desc} (*{ext})")
        
        all_audio = "Audio Files (" + " ".join(f"*{ext}" for ext in self.SUPPORTED_AUDIO_FORMATS.keys()) + ")"
        filter_string = f"{all_audio};;{';; '.join(audio_filters)};;All Files (*)"
        
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Audio Files",
            "",
            filter_string
        )
        
        if files:
            self._add_audio_files(files)
            
    def _add_audio_files(self, file_paths: List[str]):
        """Add audio files to the selection, validating formats."""
        valid_files = []
        invalid_files = []
        
        for file_path in file_paths:
            if self._is_valid_audio_file(file_path):
                if file_path not in self.audio_files:
                    valid_files.append(file_path)
            else:
                invalid_files.append(file_path)
        
        # Add valid files
        self.audio_files.extend(valid_files)
        self._update_audio_files_display()
        
        # Show warning for invalid files
        if invalid_files:
            invalid_names = [os.path.basename(f) for f in invalid_files]
            QMessageBox.warning(
                self,
                "Invalid Files",
                f"The following files are not supported audio formats:\n\n"
                f"{chr(10).join(invalid_names)}\n\n"
                f"Supported formats: {', '.join(self.SUPPORTED_AUDIO_FORMATS.keys())}"
            )
        
        # Emit signal if we have valid files
        if valid_files:
            self.files_selected.emit(self.audio_files)
            self.statusBar().showMessage(f"Selected {len(self.audio_files)} audio file(s)")
            
    def _clear_audio_files(self):
        """Clear all selected audio files."""
        self.audio_files.clear()
        self._update_audio_files_display()
        self.statusBar().showMessage("Audio files cleared")
        
    def _update_audio_files_display(self):
        """Update the audio files list widget."""
        self.audio_files_list.clear()
        
        for file_path in self.audio_files:
            item = QListWidgetItem(os.path.basename(file_path))
            item.setToolTip(file_path)
            self.audio_files_list.addItem(item)
        
        # Update button states
        has_files = len(self.audio_files) > 0
        self.clear_audio_btn.setEnabled(has_files)
        self.process_btn.setEnabled(has_files)
        
    def _select_lyric_file(self):
        """Open file dialog to select a lyric file."""
        lyric_filters = []
        for ext, desc in self.SUPPORTED_LYRIC_FORMATS.items():
            lyric_filters.append(f"{desc} (*{ext})")
        
        all_lyrics = "Lyric Files (" + " ".join(f"*{ext}" for ext in self.SUPPORTED_LYRIC_FORMATS.keys()) + ")"
        filter_string = f"{all_lyrics};;{';; '.join(lyric_filters)};;All Files (*)"
        
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Lyric File",
            "",
            filter_string
        )
        
        if file_path and self._is_valid_lyric_file(file_path):
            self.lyric_file = file_path
            self._update_lyric_file_display()
            self.lyric_file_selected.emit(file_path)
            
    def _clear_lyric_file(self):
        """Clear the selected lyric file."""
        self.lyric_file = None
        self._update_lyric_file_display()
        
    def _update_lyric_file_display(self):
        """Update the lyric file display."""
        if self.lyric_file:
            filename = os.path.basename(self.lyric_file)
            self.lyric_file_label.setText(f"Selected: {filename}")
            self.lyric_file_label.setStyleSheet("color: black; font-style: normal;")
            self.lyric_file_label.setToolTip(self.lyric_file)
            self.clear_lyric_btn.setEnabled(True)
        else:
            self.lyric_file_label.setText("No lyric file selected")
            self.lyric_file_label.setStyleSheet("color: gray; font-style: italic;")
            self.lyric_file_label.setToolTip("")
            self.clear_lyric_btn.setEnabled(False)
            
    def _start_processing(self):
        """Start the processing workflow with selected files."""
        if not self.audio_files:
            QMessageBox.warning(self, "No Files", "Please select audio files first.")
            return
        
        # Get options from options panel
        options = self.options_panel.get_current_options()
        
        # Validate options
        validation_errors = options.validate()
        if validation_errors:
            error_text = "\n".join(f"• {error}" for error in validation_errors)
            QMessageBox.warning(
                self,
                "Invalid Configuration",
                f"Please fix the following configuration issues:\n\n{error_text}"
            )
            return
        
        self.processing_requested.emit(self.audio_files, options)
        
    def _on_options_changed(self, options: ProcessingOptions):
        """Handle changes to processing options."""
        # Update status bar with validation info
        validation_errors = options.validate()
        if validation_errors:
            self.statusBar().showMessage(f"Configuration issues: {len(validation_errors)} error(s)")
        elif self.audio_files:
            self.statusBar().showMessage(f"Ready to process {len(self.audio_files)} file(s)")
        else:
            self.statusBar().showMessage("Ready - Select audio files to begin")
        
    def _is_valid_audio_file(self, file_path: str) -> bool:
        """Check if the file is a supported audio format."""
        if not os.path.isfile(file_path):
            return False
            
        ext = Path(file_path).suffix.lower()
        return ext in self.SUPPORTED_AUDIO_FORMATS
        
    def _is_valid_lyric_file(self, file_path: str) -> bool:
        """Check if the file is a supported lyric format."""
        if not os.path.isfile(file_path):
            return False
            
        ext = Path(file_path).suffix.lower()
        return ext in self.SUPPORTED_LYRIC_FORMATS
        
    def _show_about(self):
        """Show the about dialog."""
        QMessageBox.about(
            self,
            "About Lyric-to-Subtitle App",
            "Lyric-to-Subtitle App v1.0.0\n\n"
            "Automatically generates word-level synchronized subtitles from music files.\n\n"
            "Uses AI-powered vocal separation and speech recognition to create "
            "high-quality subtitles for karaoke videos, lyric videos, and accessibility."
        )
        
    # Drag and Drop Event Handlers
    def dragEnterEvent(self, event: QDragEnterEvent):
        """Handle drag enter events for file drops."""
        if event.mimeData().hasUrls():
            # Check if any of the dragged files are audio files
            urls = event.mimeData().urls()
            has_audio = any(
                self._is_valid_audio_file(url.toLocalFile()) 
                for url in urls if url.isLocalFile()
            )
            
            if has_audio:
                event.acceptProposedAction()
            else:
                event.ignore()
        else:
            event.ignore()
            
    def dropEvent(self, event: QDropEvent):
        """Handle file drop events."""
        if event.mimeData().hasUrls():
            file_paths = []
            for url in event.mimeData().urls():
                if url.isLocalFile():
                    file_paths.append(url.toLocalFile())
            
            if file_paths:
                self._add_audio_files(file_paths)
                event.acceptProposedAction()
            else:
                event.ignore()
        else:
            event.ignore()
            
    # Public interface methods
    def get_selected_audio_files(self) -> List[str]:
        """Get the list of selected audio files."""
        return self.audio_files.copy()
        
    def get_selected_lyric_file(self) -> Optional[str]:
        """Get the selected lyric file path."""
        return self.lyric_file
        
    def set_processing_enabled(self, enabled: bool):
        """Enable or disable the processing button."""
        self.process_btn.setEnabled(enabled and len(self.audio_files) > 0)
        
    def update_status(self, message: str):
        """Update the status bar message."""
        self.statusBar().showMessage(message)
        
    def get_processing_options(self) -> ProcessingOptions:
        """Get the current processing options from the options panel."""
        return self.options_panel.get_current_options()
        
    def set_processing_options(self, options: ProcessingOptions):
        """Set the processing options in the options panel."""
        self.options_panel.set_options(options)
    
    def start_progress_tracking(self, estimated_time: Optional[float] = None):
        """
        Start progress tracking for processing operations.
        
        Args:
            estimated_time: Optional estimated total processing time in seconds
        """
        self.progress_widget.setVisible(True)
        self.progress_widget.start_processing(estimated_time)
        self.process_btn.setEnabled(False)
        self.process_btn.setText("Processing...")
        
    def update_progress(self, overall_percentage: float, message: str, 
                       operation: Optional[str] = None, 
                       operation_percentage: Optional[float] = None):
        """
        Update progress information.
        
        Args:
            overall_percentage: Overall progress percentage (0-100)
            message: Status message describing current activity
            operation: Optional name of current operation
            operation_percentage: Optional progress of current operation (0-100)
        """
        self.progress_widget.update_progress(
            overall_percentage, message, operation, operation_percentage
        )
        
        # Update status bar with current progress
        self.statusBar().showMessage(f"{overall_percentage:.1f}% - {message}")
        
    def finish_progress_tracking(self, success: bool = True, 
                               final_message: str = "Processing completed"):
        """
        Finish progress tracking.
        
        Args:
            success: Whether processing completed successfully
            final_message: Final status message to display
        """
        self.progress_widget.finish_processing(success, final_message)
        self.process_btn.setEnabled(len(self.audio_files) > 0)
        self.process_btn.setText("Start Processing")
        
        # Update status bar
        if success:
            self.statusBar().showMessage(final_message)
        else:
            self.statusBar().showMessage(f"Processing failed: {final_message}")
            
    def reset_progress_tracking(self):
        """Reset progress tracking to initial state."""
        self.progress_widget.reset()
        self.progress_widget.setVisible(False)
        self.process_btn.setEnabled(len(self.audio_files) > 0)
        self.process_btn.setText("Start Processing")
        
    def set_cancel_callback(self, callback: Callable[[], bool]):
        """
        Set the callback function for handling cancellation requests.
        
        Args:
            callback: Function that returns True if cancellation was successful
        """
        self.progress_widget.set_cancel_callback(callback)
        
    def is_processing(self) -> bool:
        """Check if processing is currently active."""
        return self.progress_widget.is_processing()
        
    def get_progress_info(self) -> Dict[str, Any]:
        """Get current progress information."""
        return self.progress_widget.get_progress_info()
        
    def _on_cancel_requested(self):
        """Handle cancellation request from progress widget."""
        self.cancel_processing_requested.emit()
        
    def _on_retry_requested(self, file_path: str):
        """Handle retry request from results panel."""
        # For now, just restart processing with the same files
        # In a full implementation, this would be handled by the application controller
        if file_path == "current_file" and self.audio_files:
            self._start_processing()
        
    def _on_open_file_requested(self, file_path: str):
        """Handle request to open a file."""
        import subprocess
        import platform
        
        try:
            if platform.system() == "Windows":
                os.startfile(file_path)
            elif platform.system() == "Darwin":  # macOS
                subprocess.run(["open", file_path])
            else:  # Linux
                subprocess.run(["xdg-open", file_path])
        except Exception as e:
            QMessageBox.warning(
                self,
                "Cannot Open File",
                f"Failed to open file:\n{file_path}\n\nError: {str(e)}"
            )
            
    def _on_show_in_folder_requested(self, folder_path: str):
        """Handle request to show folder in file explorer."""
        import subprocess
        import platform
        
        try:
            if platform.system() == "Windows":
                subprocess.run(["explorer", folder_path])
            elif platform.system() == "Darwin":  # macOS
                subprocess.run(["open", folder_path])
            else:  # Linux
                subprocess.run(["xdg-open", folder_path])
        except Exception as e:
            QMessageBox.warning(
                self,
                "Cannot Open Folder",
                f"Failed to open folder:\n{folder_path}\n\nError: {str(e)}"
            )
    
    # Public methods for showing results
    def show_processing_success(self, result: ProcessingResult, processing_time: float = 0.0):
        """
        Show successful processing results.
        
        Args:
            result: The processing result to display
            processing_time: Time taken for processing in seconds
        """
        self.results_panel.show_success_results(result, processing_time)
        
    def show_processing_error(self, error_message: str, error_category: str = "processing",
                            suggestions: Optional[List[str]] = None,
                            detailed_error: Optional[str] = None):
        """
        Show processing error with recovery suggestions.
        
        Args:
            error_message: User-friendly error message
            error_category: Category of error (validation, processing, export, system)
            suggestions: List of recovery suggestions
            detailed_error: Detailed technical error information
        """
        self.results_panel.show_error_results(error_message, error_category, suggestions, detailed_error)
        
    def show_batch_results(self, batch_result: BatchResult):
        """
        Show batch processing results.
        
        Args:
            batch_result: The batch processing result to display
        """
        self.results_panel.show_batch_results(batch_result)
        
    def hide_results(self):
        """Hide the results panel."""
        self.results_panel.hide_results()
        
    def is_results_visible(self) -> bool:
        """Check if results panel is currently visible."""
        return self.results_panel.is_visible_panel()