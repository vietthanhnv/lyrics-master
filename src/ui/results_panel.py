"""
Results display and error handling UI for the lyric-to-subtitle application.

This module provides comprehensive results display with success notifications,
error handling with user-friendly messages and recovery suggestions.
"""

import os
import webbrowser
from pathlib import Path
from typing import List, Optional, Dict, Any, Callable
from datetime import datetime

from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QGroupBox, QTextEdit, QScrollArea,
    QListWidget, QListWidgetItem, QFrame, QSizePolicy,
    QMessageBox, QFileDialog, QTabWidget, QTreeWidget,
    QTreeWidgetItem, QProgressBar, QSplitter
)
from PyQt6.QtGui import QFont, QPixmap, QIcon, QColor, QPalette

from ..models.data_models import ProcessingResult, BatchResult, BatchFileReport


class ResultsPanel(QWidget):
    """
    Comprehensive results display and error handling panel.
    
    Features:
    - Success notifications with file location information
    - Error display with user-friendly messages and recovery suggestions
    - Generated subtitle files display with preview and actions
    - Batch processing results summary
    - Export and sharing options
    """
    
    # Signals
    retry_requested = pyqtSignal(str)  # Emitted when user requests retry for a file
    open_file_requested = pyqtSignal(str)  # Emitted when user wants to open a file
    show_in_folder_requested = pyqtSignal(str)  # Emitted when user wants to show file in folder
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # State
        self._current_results: Optional[ProcessingResult] = None
        self._current_batch_results: Optional[BatchResult] = None
        self._is_visible = False
        
        # Auto-hide timer for success messages
        self._auto_hide_timer = QTimer()
        self._auto_hide_timer.timeout.connect(self._auto_hide_success)
        self._auto_hide_timer.setSingleShot(True)
        
        self._setup_ui()
        
    def _setup_ui(self):
        """Initialize the user interface components."""
        self.setMinimumHeight(400)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)
        
        # Create tabbed interface for different result types
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)
        
        # Single file results tab
        self._create_single_results_tab()
        
        # Batch results tab
        self._create_batch_results_tab()
        
        # Error details tab
        self._create_error_details_tab()
        
        # Control buttons
        self._create_control_buttons(main_layout)
        
        # Initially hide the panel
        self.setVisible(False)
        
    def _create_single_results_tab(self):
        """Create the single file results display tab."""
        single_tab = QWidget()
        layout = QVBoxLayout(single_tab)
        
        # Success notification section
        self.success_group = QGroupBox("✓ Processing Completed Successfully!")
        self.success_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 14px;
                color: #4CAF50;
                border: 2px solid #4CAF50;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        success_layout = QVBoxLayout(self.success_group)
        
        # Processing summary
        self.processing_summary = QLabel()
        self.processing_summary.setWordWrap(True)
        self.processing_summary.setStyleSheet("color: #2E7D32; font-size: 12px;")
        success_layout.addWidget(self.processing_summary)
        
        # Generated files list
        files_label = QLabel("Generated Files:")
        files_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        success_layout.addWidget(files_label)
        
        self.files_list = QListWidget()
        self.files_list.setMaximumHeight(150)
        self.files_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #cccccc;
                border-radius: 4px;
                background-color: #f9f9f9;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #eeeeee;
            }
            QListWidget::item:hover {
                background-color: #e3f2fd;
            }
        """)
        success_layout.addWidget(self.files_list)
        
        # File actions
        file_actions = QHBoxLayout()
        
        self.open_folder_btn = QPushButton("📁 Open Output Folder")
        self.open_folder_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                padding: 8px 16px;
                border-radius: 4px;
                border: none;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        self.open_folder_btn.clicked.connect(self._open_output_folder)
        file_actions.addWidget(self.open_folder_btn)
        
        self.preview_btn = QPushButton("👁 Preview Files")
        self.preview_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 8px 16px;
                border-radius: 4px;
                border: none;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #388E3C;
            }
        """)
        self.preview_btn.clicked.connect(self._preview_files)
        file_actions.addWidget(self.preview_btn)
        
        file_actions.addStretch()
        success_layout.addLayout(file_actions)
        
        layout.addWidget(self.success_group)
        
        # Error notification section
        self.error_group = QGroupBox("⚠ Processing Failed")
        self.error_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 14px;
                color: #f44336;
                border: 2px solid #f44336;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        error_layout = QVBoxLayout(self.error_group)
        
        # Error message
        self.error_message = QLabel()
        self.error_message.setWordWrap(True)
        self.error_message.setStyleSheet("color: #C62828; font-size: 12px;")
        error_layout.addWidget(self.error_message)
        
        # Recovery suggestions
        suggestions_label = QLabel("Suggested Solutions:")
        suggestions_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        error_layout.addWidget(suggestions_label)
        
        self.suggestions_list = QListWidget()
        self.suggestions_list.setMaximumHeight(120)
        self.suggestions_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #ffcdd2;
                border-radius: 4px;
                background-color: #ffebee;
            }
            QListWidget::item {
                padding: 6px;
                border-bottom: 1px solid #ffcdd2;
            }
        """)
        error_layout.addWidget(self.suggestions_list)
        
        # Error actions
        error_actions = QHBoxLayout()
        
        self.retry_btn = QPushButton("🔄 Retry Processing")
        self.retry_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                padding: 8px 16px;
                border-radius: 4px;
                border: none;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
        """)
        self.retry_btn.clicked.connect(self._retry_processing)
        error_actions.addWidget(self.retry_btn)
        
        self.help_btn = QPushButton("❓ Get Help")
        self.help_btn.setStyleSheet("""
            QPushButton {
                background-color: #9C27B0;
                color: white;
                padding: 8px 16px;
                border-radius: 4px;
                border: none;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #7B1FA2;
            }
        """)
        self.help_btn.clicked.connect(self._show_help)
        error_actions.addWidget(self.help_btn)
        
        error_actions.addStretch()
        error_layout.addLayout(error_actions)
        
        layout.addWidget(self.error_group)
        
        layout.addStretch()
        
        self.tab_widget.addTab(single_tab, "Single File Results")
        
    def _create_batch_results_tab(self):
        """Create the batch processing results display tab."""
        batch_tab = QWidget()
        layout = QVBoxLayout(batch_tab)
        
        # Batch summary section
        summary_group = QGroupBox("Batch Processing Summary")
        summary_layout = QGridLayout(summary_group)
        
        # Statistics labels
        self.total_files_label = QLabel("0")
        self.successful_files_label = QLabel("0")
        self.failed_files_label = QLabel("0")
        self.success_rate_label = QLabel("0%")
        self.processing_time_label = QLabel("0s")
        
        # Style for statistics
        stat_style = "font-weight: bold; font-size: 14px;"
        self.total_files_label.setStyleSheet(stat_style)
        self.successful_files_label.setStyleSheet(stat_style + "color: #4CAF50;")
        self.failed_files_label.setStyleSheet(stat_style + "color: #f44336;")
        self.success_rate_label.setStyleSheet(stat_style)
        self.processing_time_label.setStyleSheet(stat_style)
        
        # Add to grid
        summary_layout.addWidget(QLabel("Total Files:"), 0, 0)
        summary_layout.addWidget(self.total_files_label, 0, 1)
        summary_layout.addWidget(QLabel("Successful:"), 0, 2)
        summary_layout.addWidget(self.successful_files_label, 0, 3)
        
        summary_layout.addWidget(QLabel("Failed:"), 1, 0)
        summary_layout.addWidget(self.failed_files_label, 1, 1)
        summary_layout.addWidget(QLabel("Success Rate:"), 1, 2)
        summary_layout.addWidget(self.success_rate_label, 1, 3)
        
        summary_layout.addWidget(QLabel("Total Time:"), 2, 0)
        summary_layout.addWidget(self.processing_time_label, 2, 1)
        
        layout.addWidget(summary_group)
        
        # File results tree
        results_group = QGroupBox("Individual File Results")
        results_layout = QVBoxLayout(results_group)
        
        self.batch_tree = QTreeWidget()
        self.batch_tree.setHeaderLabels(["File", "Status", "Time", "Output Files"])
        self.batch_tree.setAlternatingRowColors(True)
        self.batch_tree.setRootIsDecorated(False)
        results_layout.addWidget(self.batch_tree)
        
        # Batch actions
        batch_actions = QHBoxLayout()
        
        self.export_report_btn = QPushButton("📊 Export Report")
        self.export_report_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                padding: 8px 16px;
                border-radius: 4px;
                border: none;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        self.export_report_btn.clicked.connect(self._export_batch_report)
        batch_actions.addWidget(self.export_report_btn)
        
        self.retry_failed_btn = QPushButton("🔄 Retry Failed Files")
        self.retry_failed_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                padding: 8px 16px;
                border-radius: 4px;
                border: none;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
        """)
        self.retry_failed_btn.clicked.connect(self._retry_failed_files)
        batch_actions.addWidget(self.retry_failed_btn)
        
        batch_actions.addStretch()
        results_layout.addLayout(batch_actions)
        
        layout.addWidget(results_group)
        
        self.tab_widget.addTab(batch_tab, "Batch Results")
        
    def _create_error_details_tab(self):
        """Create the detailed error information tab."""
        error_tab = QWidget()
        layout = QVBoxLayout(error_tab)
        
        # Error details section
        details_group = QGroupBox("Error Details")
        details_layout = QVBoxLayout(details_group)
        
        # Error log
        self.error_log = QTextEdit()
        self.error_log.setReadOnly(True)
        self.error_log.setMaximumHeight(200)
        self.error_log.setStyleSheet("""
            QTextEdit {
                background-color: #ffebee;
                border: 1px solid #ffcdd2;
                border-radius: 4px;
                font-family: monospace;
                font-size: 10px;
            }
        """)
        details_layout.addWidget(self.error_log)
        
        # System information
        system_group = QGroupBox("System Information")
        system_layout = QVBoxLayout(system_group)
        
        self.system_info = QTextEdit()
        self.system_info.setReadOnly(True)
        self.system_info.setMaximumHeight(150)
        self.system_info.setStyleSheet("""
            QTextEdit {
                background-color: #f5f5f5;
                border: 1px solid #cccccc;
                border-radius: 4px;
                font-family: monospace;
                font-size: 10px;
            }
        """)
        system_layout.addWidget(self.system_info)
        
        layout.addWidget(details_group)
        layout.addWidget(system_group)
        
        # Diagnostic actions
        diag_actions = QHBoxLayout()
        
        self.copy_error_btn = QPushButton("📋 Copy Error Details")
        self.copy_error_btn.setStyleSheet("""
            QPushButton {
                background-color: #607D8B;
                color: white;
                padding: 8px 16px;
                border-radius: 4px;
                border: none;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #455A64;
            }
        """)
        self.copy_error_btn.clicked.connect(self._copy_error_details)
        diag_actions.addWidget(self.copy_error_btn)
        
        self.save_log_btn = QPushButton("💾 Save Error Log")
        self.save_log_btn.setStyleSheet("""
            QPushButton {
                background-color: #795548;
                color: white;
                padding: 8px 16px;
                border-radius: 4px;
                border: none;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #5D4037;
            }
        """)
        self.save_log_btn.clicked.connect(self._save_error_log)
        diag_actions.addWidget(self.save_log_btn)
        
        diag_actions.addStretch()
        layout.addLayout(diag_actions)
        
        self.tab_widget.addTab(error_tab, "Error Details")
        
    def _create_control_buttons(self, parent_layout):
        """Create the main control buttons."""
        control_layout = QHBoxLayout()
        
        # Close/Hide button
        self.close_btn = QPushButton("✕ Close Results")
        self.close_btn.setStyleSheet("""
            QPushButton {
                background-color: #757575;
                color: white;
                padding: 8px 16px;
                border-radius: 4px;
                border: none;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #616161;
            }
        """)
        self.close_btn.clicked.connect(self.hide_results)
        control_layout.addWidget(self.close_btn)
        
        control_layout.addStretch()
        
        # Auto-hide checkbox for success messages
        from PyQt6.QtWidgets import QCheckBox
        self.auto_hide_checkbox = QCheckBox("Auto-hide success messages (5s)")
        self.auto_hide_checkbox.setChecked(True)
        control_layout.addWidget(self.auto_hide_checkbox)
        
        parent_layout.addLayout(control_layout)
        
    def show_success_results(self, result: ProcessingResult, processing_time: float = 0.0):
        """
        Display successful processing results.
        
        Args:
            result: The processing result to display
            processing_time: Time taken for processing in seconds
        """
        self._current_results = result
        
        # Show success section, hide error section
        self.success_group.setVisible(True)
        self.error_group.setVisible(False)
        
        # Update processing summary
        file_count = len(result.output_files)
        time_str = f"{processing_time:.1f}s" if processing_time > 0 else "N/A"
        
        summary_text = (
            f"Successfully processed audio file and generated {file_count} subtitle file(s) "
            f"in {time_str}. Files are ready for use with video editing software or media players."
        )
        self.processing_summary.setText(summary_text)
        
        # Update files list
        self.files_list.clear()
        for file_path in result.output_files:
            item = QListWidgetItem()
            
            # Create rich text for file item
            file_name = os.path.basename(file_path)
            file_size = self._get_file_size(file_path)
            file_format = Path(file_path).suffix.upper().lstrip('.')
            
            item.setText(f"{file_name}")
            item.setToolTip(f"Path: {file_path}\nSize: {file_size}\nFormat: {file_format}")
            
            # Add context menu for file actions
            item.setData(Qt.ItemDataRole.UserRole, file_path)
            
            self.files_list.addItem(item)
        
        # Connect file list double-click to open file
        self.files_list.itemDoubleClicked.connect(self._on_file_double_clicked)
        
        # Show the panel and switch to single results tab
        self.setVisible(True)
        self.tab_widget.setCurrentIndex(0)
        self._is_visible = True
        
        # Auto-hide after 5 seconds if enabled
        if self.auto_hide_checkbox.isChecked():
            self._auto_hide_timer.start(5000)
        
    def show_error_results(self, error_message: str, error_category: str = "processing", 
                          suggestions: Optional[List[str]] = None, 
                          detailed_error: Optional[str] = None):
        """
        Display error results with recovery suggestions.
        
        Args:
            error_message: User-friendly error message
            error_category: Category of error (validation, processing, export, system)
            suggestions: List of recovery suggestions
            detailed_error: Detailed technical error information
        """
        # Show error section, hide success section
        self.success_group.setVisible(False)
        self.error_group.setVisible(True)
        
        # Update error message
        self.error_message.setText(error_message)
        
        # Update suggestions
        self.suggestions_list.clear()
        if suggestions:
            for suggestion in suggestions:
                item = QListWidgetItem(f"• {suggestion}")
                self.suggestions_list.addItem(item)
        else:
            # Provide default suggestions based on error category
            default_suggestions = self._get_default_suggestions(error_category)
            for suggestion in default_suggestions:
                item = QListWidgetItem(f"• {suggestion}")
                self.suggestions_list.addItem(item)
        
        # Update error details tab
        if detailed_error:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            error_log_text = f"[{timestamp}] Error Category: {error_category}\n"
            error_log_text += f"[{timestamp}] Error Message: {error_message}\n"
            error_log_text += f"[{timestamp}] Detailed Error:\n{detailed_error}\n"
            self.error_log.setText(error_log_text)
        
        # Update system information
        self._update_system_info()
        
        # Show the panel and switch to single results tab
        self.setVisible(True)
        self.tab_widget.setCurrentIndex(0)
        self._is_visible = True
        
    def show_batch_results(self, batch_result: BatchResult):
        """
        Display batch processing results.
        
        Args:
            batch_result: The batch processing result to display
        """
        self._current_batch_results = batch_result
        
        # Update summary statistics
        self.total_files_label.setText(str(batch_result.total_files))
        self.successful_files_label.setText(str(batch_result.successful_files))
        self.failed_files_label.setText(str(batch_result.failed_files))
        self.success_rate_label.setText(f"{batch_result.success_rate():.1f}%")
        self.processing_time_label.setText(f"{batch_result.total_processing_time:.1f}s")
        
        # Update batch tree
        self.batch_tree.clear()
        
        for i, report in enumerate(batch_result.file_reports):
            item = QTreeWidgetItem()
            
            # File name
            item.setText(0, report.file_name)
            
            # Status with icon
            if report.success:
                item.setText(1, "✓ Success")
                item.setForeground(1, QColor("#4CAF50"))
            else:
                item.setText(1, "✗ Failed")
                item.setForeground(1, QColor("#f44336"))
            
            # Processing time
            item.setText(2, f"{report.processing_time:.1f}s")
            
            # Output files count
            item.setText(3, str(len(report.output_files)))
            
            # Store full report data
            item.setData(0, Qt.ItemDataRole.UserRole, report)
            
            self.batch_tree.addTopLevelItem(item)
        
        # Resize columns to content
        for i in range(4):
            self.batch_tree.resizeColumnToContents(i)
        
        # Show the panel and switch to batch results tab
        self.setVisible(True)
        self.tab_widget.setCurrentIndex(1)
        self._is_visible = True
        
    def hide_results(self):
        """Hide the results panel."""
        self.setVisible(False)
        self._is_visible = False
        self._auto_hide_timer.stop()
        
    def is_visible_panel(self) -> bool:
        """Check if the results panel is currently visible."""
        return self._is_visible
        
    def _get_default_suggestions(self, error_category: str) -> List[str]:
        """Get default recovery suggestions based on error category."""
        suggestions = {
            "validation": [
                "Check that the audio file is not corrupted",
                "Ensure the file format is supported (.mp3, .wav, .flac, .ogg)",
                "Verify the file is not empty or too short",
                "Try converting the file to a different format"
            ],
            "processing": [
                "Check available disk space for temporary files",
                "Ensure sufficient RAM is available (4GB+ recommended)",
                "Try using a smaller model size (tiny or base)",
                "Close other applications to free up system resources"
            ],
            "export": [
                "Check write permissions for the output directory",
                "Ensure sufficient disk space for output files",
                "Try selecting a different output directory",
                "Close any applications that might be using the output files"
            ],
            "system": [
                "Restart the application and try again",
                "Check system requirements and available resources",
                "Update your graphics drivers if using GPU acceleration",
                "Contact support if the problem persists"
            ]
        }
        
        return suggestions.get(error_category, suggestions["system"])
        
    def _get_file_size(self, file_path: str) -> str:
        """Get human-readable file size."""
        try:
            size = os.path.getsize(file_path)
            for unit in ['B', 'KB', 'MB', 'GB']:
                if size < 1024.0:
                    return f"{size:.1f} {unit}"
                size /= 1024.0
            return f"{size:.1f} TB"
        except OSError:
            return "Unknown"
            
    def _update_system_info(self):
        """Update system information display."""
        import platform
        import sys
        
        info_text = f"Python Version: {sys.version}\n"
        info_text += f"Platform: {platform.platform()}\n"
        info_text += f"Architecture: {platform.architecture()[0]}\n"
        info_text += f"Processor: {platform.processor()}\n"
        
        try:
            import psutil
            memory = psutil.virtual_memory()
            info_text += f"Total RAM: {memory.total / (1024**3):.1f} GB\n"
            info_text += f"Available RAM: {memory.available / (1024**3):.1f} GB\n"
            info_text += f"CPU Count: {psutil.cpu_count()}\n"
        except ImportError:
            info_text += "psutil not available for detailed system info\n"
        
        self.system_info.setText(info_text)
        
    # Event handlers
    def _on_file_double_clicked(self, item: QListWidgetItem):
        """Handle double-click on file item."""
        file_path = item.data(Qt.ItemDataRole.UserRole)
        if file_path:
            self.open_file_requested.emit(file_path)
            
    def _open_output_folder(self):
        """Open the output folder in file explorer."""
        if self._current_results and self._current_results.output_files:
            folder_path = os.path.dirname(self._current_results.output_files[0])
            self.show_in_folder_requested.emit(folder_path)
            
    def _preview_files(self):
        """Preview generated subtitle files."""
        if self._current_results and self._current_results.output_files:
            # Open first file for preview
            self.open_file_requested.emit(self._current_results.output_files[0])
            
    def _retry_processing(self):
        """Request retry of failed processing."""
        if self._current_results:
            # Emit retry signal - parent will handle the actual retry
            self.retry_requested.emit("current_file")
            
    def _show_help(self):
        """Show help information."""
        help_text = """
        <h3>Troubleshooting Guide</h3>
        
        <h4>Common Issues and Solutions:</h4>
        
        <b>Audio File Issues:</b>
        <ul>
        <li>Ensure file is not corrupted or protected</li>
        <li>Try converting to WAV format</li>
        <li>Check file is not empty or too short (&lt;5 seconds)</li>
        </ul>
        
        <b>Processing Issues:</b>
        <ul>
        <li>Close other applications to free memory</li>
        <li>Try smaller model size (tiny/base)</li>
        <li>Ensure 4GB+ RAM available</li>
        </ul>
        
        <b>Output Issues:</b>
        <ul>
        <li>Check output folder permissions</li>
        <li>Ensure sufficient disk space</li>
        <li>Try different output location</li>
        </ul>
        
        <p>For more help, check the documentation or contact support.</p>
        """
        
        QMessageBox.information(self, "Help - Troubleshooting", help_text)
        
    def _export_batch_report(self):
        """Export batch processing report."""
        if not self._current_batch_results:
            return
            
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Batch Report",
            f"batch_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            "Text Files (*.txt);;JSON Files (*.json);;All Files (*)"
        )
        
        if file_path:
            try:
                if file_path.endswith('.json'):
                    self._current_batch_results.export_json_report(file_path)
                else:
                    self._current_batch_results.export_summary_report(file_path)
                
                QMessageBox.information(
                    self, 
                    "Export Successful", 
                    f"Batch report exported to:\n{file_path}"
                )
            except Exception as e:
                QMessageBox.warning(
                    self,
                    "Export Failed",
                    f"Failed to export batch report:\n{str(e)}"
                )
                
    def _retry_failed_files(self):
        """Request retry of failed files in batch."""
        if self._current_batch_results:
            failed_files = [
                report.file_path for report in self._current_batch_results.file_reports
                if not report.success
            ]
            
            if failed_files:
                # Emit retry signal for failed files
                for file_path in failed_files:
                    self.retry_requested.emit(file_path)
            else:
                QMessageBox.information(
                    self,
                    "No Failed Files",
                    "There are no failed files to retry."
                )
                
    def _copy_error_details(self):
        """Copy error details to clipboard."""
        from PyQt6.QtWidgets import QApplication
        
        error_text = self.error_log.toPlainText()
        system_text = self.system_info.toPlainText()
        
        full_text = "=== ERROR DETAILS ===\n"
        full_text += error_text + "\n\n"
        full_text += "=== SYSTEM INFORMATION ===\n"
        full_text += system_text
        
        clipboard = QApplication.clipboard()
        clipboard.setText(full_text)
        
        # Show temporary notification
        QMessageBox.information(
            self,
            "Copied",
            "Error details copied to clipboard."
        )
        
    def _save_error_log(self):
        """Save error log to file."""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Error Log",
            f"error_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            "Text Files (*.txt);;All Files (*)"
        )
        
        if file_path:
            try:
                error_text = self.error_log.toPlainText()
                system_text = self.system_info.toPlainText()
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write("=== ERROR LOG ===\n")
                    f.write(error_text + "\n\n")
                    f.write("=== SYSTEM INFORMATION ===\n")
                    f.write(system_text)
                
                QMessageBox.information(
                    self,
                    "Log Saved",
                    f"Error log saved to:\n{file_path}"
                )
            except Exception as e:
                QMessageBox.warning(
                    self,
                    "Save Failed",
                    f"Failed to save error log:\n{str(e)}"
                )
                
    def _auto_hide_success(self):
        """Auto-hide success message after timer expires."""
        if self.success_group.isVisible():
            self.hide_results()