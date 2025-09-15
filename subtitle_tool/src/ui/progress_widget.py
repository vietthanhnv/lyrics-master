"""
Progress tracking and status display widget for the lyric-to-subtitle application.

This module provides a comprehensive progress widget that displays real-time progress
indicators, estimated completion times, current operation status, and cancellation support.
"""

import time
from typing import Optional, Callable, Dict, Any
from datetime import datetime, timedelta

from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread, pyqtSlot
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QProgressBar, QGroupBox,
    QTextEdit, QScrollArea, QFrame, QSizePolicy
)
from PyQt6.QtGui import QFont, QPalette, QColor


class ProgressWidget(QWidget):
    """
    Comprehensive progress tracking widget with real-time indicators.
    
    Features:
    - Real-time progress bars for overall and current operation
    - Estimated completion time calculation and display
    - Current operation status with detailed messages
    - Processing speed and throughput metrics
    - Cancellation support with confirmation
    - Progress history and logging
    """
    
    # Signals
    cancel_requested = pyqtSignal()  # Emitted when user requests cancellation
    progress_updated = pyqtSignal(float, str)  # Emitted when progress changes
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Progress tracking state
        self._overall_progress = 0.0
        self._current_operation_progress = 0.0
        self._current_operation = ""
        self._status_message = ""
        self._is_processing = False
        self._start_time: Optional[float] = None
        self._last_update_time: Optional[float] = None
        self._progress_history: list = []
        self._estimated_total_time: Optional[float] = None
        
        # Cancellation support
        self._cancel_callback: Optional[Callable[[], bool]] = None
        self._cancellation_requested = False
        
        # UI update timer
        self._update_timer = QTimer()
        self._update_timer.timeout.connect(self._update_time_displays)
        self._update_timer.setInterval(1000)  # Update every second
        
        self._setup_ui()
        self._reset_progress()
        
    def _setup_ui(self):
        """Initialize the user interface components."""
        self.setMinimumHeight(300)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)
        
        # Progress section
        self._create_progress_section(main_layout)
        
        # Status section
        self._create_status_section(main_layout)
        
        # Control section
        self._create_control_section(main_layout)
        
        # Details section (collapsible)
        self._create_details_section(main_layout)
        
    def _create_progress_section(self, parent_layout):
        """Create the progress bars and time display section."""
        progress_group = QGroupBox("Processing Progress")
        progress_layout = QGridLayout(progress_group)
        progress_layout.setSpacing(10)
        
        # Overall progress
        progress_layout.addWidget(QLabel("Overall Progress:"), 0, 0)
        self.overall_progress_bar = QProgressBar()
        self.overall_progress_bar.setMinimum(0)
        self.overall_progress_bar.setMaximum(100)
        self.overall_progress_bar.setValue(0)
        self.overall_progress_bar.setTextVisible(True)
        self.overall_progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #cccccc;
                border-radius: 5px;
                text-align: center;
                font-weight: bold;
                height: 25px;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 3px;
            }
        """)
        progress_layout.addWidget(self.overall_progress_bar, 0, 1, 1, 2)
        
        # Current operation progress
        progress_layout.addWidget(QLabel("Current Operation:"), 1, 0)
        self.operation_progress_bar = QProgressBar()
        self.operation_progress_bar.setMinimum(0)
        self.operation_progress_bar.setMaximum(100)
        self.operation_progress_bar.setValue(0)
        self.operation_progress_bar.setTextVisible(True)
        self.operation_progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #cccccc;
                border-radius: 5px;
                text-align: center;
                font-weight: bold;
                height: 20px;
            }
            QProgressBar::chunk {
                background-color: #2196F3;
                border-radius: 3px;
            }
        """)
        progress_layout.addWidget(self.operation_progress_bar, 1, 1, 1, 2)
        
        # Time information
        progress_layout.addWidget(QLabel("Elapsed Time:"), 2, 0)
        self.elapsed_time_label = QLabel("00:00:00")
        self.elapsed_time_label.setStyleSheet("font-family: monospace; font-weight: bold;")
        progress_layout.addWidget(self.elapsed_time_label, 2, 1)
        
        progress_layout.addWidget(QLabel("Estimated Remaining:"), 2, 2)
        self.remaining_time_label = QLabel("--:--:--")
        self.remaining_time_label.setStyleSheet("font-family: monospace; font-weight: bold;")
        progress_layout.addWidget(self.remaining_time_label, 2, 3)
        
        # Processing speed
        progress_layout.addWidget(QLabel("Processing Speed:"), 3, 0)
        self.speed_label = QLabel("-- %/min")
        self.speed_label.setStyleSheet("font-family: monospace;")
        progress_layout.addWidget(self.speed_label, 3, 1)
        
        progress_layout.addWidget(QLabel("ETA:"), 3, 2)
        self.eta_label = QLabel("--:--:--")
        self.eta_label.setStyleSheet("font-family: monospace; font-weight: bold;")
        progress_layout.addWidget(self.eta_label, 3, 3)
        
        parent_layout.addWidget(progress_group)
        
    def _create_status_section(self, parent_layout):
        """Create the current status and operation display section."""
        status_group = QGroupBox("Current Status")
        status_layout = QVBoxLayout(status_group)
        
        # Current operation
        operation_layout = QHBoxLayout()
        operation_layout.addWidget(QLabel("Operation:"))
        self.operation_label = QLabel("Ready")
        self.operation_label.setStyleSheet("font-weight: bold; color: #2196F3;")
        operation_layout.addWidget(self.operation_label)
        operation_layout.addStretch()
        status_layout.addLayout(operation_layout)
        
        # Status message
        message_layout = QHBoxLayout()
        message_layout.addWidget(QLabel("Status:"))
        self.status_label = QLabel("Waiting for processing to begin...")
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet("color: #666666;")
        message_layout.addWidget(self.status_label)
        message_layout.addStretch()
        status_layout.addLayout(message_layout)
        
        # Processing phase indicator
        phase_layout = QHBoxLayout()
        phase_layout.addWidget(QLabel("Phase:"))
        self.phase_label = QLabel("Idle")
        self.phase_label.setStyleSheet("font-weight: bold;")
        phase_layout.addWidget(self.phase_label)
        phase_layout.addStretch()
        status_layout.addLayout(phase_layout)
        
        parent_layout.addWidget(status_group)
        
    def _create_control_section(self, parent_layout):
        """Create the control buttons section."""
        control_layout = QHBoxLayout()
        
        # Cancel button
        self.cancel_button = QPushButton("Cancel Processing")
        self.cancel_button.setEnabled(False)
        self.cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
                border-radius: 4px;
                border: none;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        self.cancel_button.clicked.connect(self._on_cancel_clicked)
        control_layout.addWidget(self.cancel_button)
        
        control_layout.addStretch()
        
        # Show/hide details button
        self.details_button = QPushButton("Show Details")
        self.details_button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                padding: 8px 16px;
                border-radius: 4px;
                border: none;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        self.details_button.clicked.connect(self._toggle_details)
        control_layout.addWidget(self.details_button)
        
        parent_layout.addLayout(control_layout)
        
    def _create_details_section(self, parent_layout):
        """Create the collapsible details section."""
        self.details_group = QGroupBox("Processing Details")
        self.details_group.setVisible(False)
        details_layout = QVBoxLayout(self.details_group)
        
        # Progress log
        log_label = QLabel("Progress Log:")
        log_label.setStyleSheet("font-weight: bold;")
        details_layout.addWidget(log_label)
        
        self.progress_log = QTextEdit()
        self.progress_log.setMaximumHeight(150)
        self.progress_log.setReadOnly(True)
        self.progress_log.setStyleSheet("""
            QTextEdit {
                background-color: #f5f5f5;
                border: 1px solid #cccccc;
                border-radius: 4px;
                font-family: monospace;
                font-size: 10px;
            }
        """)
        details_layout.addWidget(self.progress_log)
        
        # Statistics
        stats_layout = QGridLayout()
        
        stats_layout.addWidget(QLabel("Updates Received:"), 0, 0)
        self.updates_count_label = QLabel("0")
        stats_layout.addWidget(self.updates_count_label, 0, 1)
        
        stats_layout.addWidget(QLabel("Average Speed:"), 0, 2)
        self.avg_speed_label = QLabel("-- %/min")
        stats_layout.addWidget(self.avg_speed_label, 0, 3)
        
        stats_layout.addWidget(QLabel("Peak Speed:"), 1, 0)
        self.peak_speed_label = QLabel("-- %/min")
        stats_layout.addWidget(self.peak_speed_label, 1, 1)
        
        stats_layout.addWidget(QLabel("Stall Count:"), 1, 2)
        self.stall_count_label = QLabel("0")
        stats_layout.addWidget(self.stall_count_label, 1, 3)
        
        details_layout.addLayout(stats_layout)
        
        parent_layout.addWidget(self.details_group)
        
    def set_cancel_callback(self, callback: Callable[[], bool]) -> None:
        """
        Set the callback function to call when cancellation is requested.
        
        Args:
            callback: Function that returns True if cancellation was successful
        """
        self._cancel_callback = callback
        
    def start_processing(self, estimated_total_time: Optional[float] = None) -> None:
        """
        Start progress tracking for a new processing operation.
        
        Args:
            estimated_total_time: Optional estimated total processing time in seconds
        """
        self._is_processing = True
        self._start_time = time.time()
        self._last_update_time = self._start_time
        self._estimated_total_time = estimated_total_time
        self._cancellation_requested = False
        self._progress_history.clear()
        
        # Reset progress displays
        self._reset_progress()
        
        # Enable controls
        self.cancel_button.setEnabled(True)
        
        # Start update timer
        self._update_timer.start()
        
        # Log start
        self._log_progress("Processing started")
        
        # Update UI
        self.phase_label.setText("Initializing")
        self.phase_label.setStyleSheet("font-weight: bold; color: #FF9800;")
        
    def update_progress(self, overall_percentage: float, message: str, 
                       operation: Optional[str] = None, 
                       operation_percentage: Optional[float] = None) -> None:
        """
        Update progress information.
        
        Args:
            overall_percentage: Overall progress percentage (0-100)
            message: Status message describing current activity
            operation: Optional name of current operation
            operation_percentage: Optional progress of current operation (0-100)
        """
        if not self._is_processing:
            return
            
        current_time = time.time()
        
        # Update progress values
        self._overall_progress = max(0.0, min(100.0, overall_percentage))
        if operation_percentage is not None:
            self._current_operation_progress = max(0.0, min(100.0, operation_percentage))
        
        if operation:
            self._current_operation = operation
        
        self._status_message = message
        self._last_update_time = current_time
        
        # Add to progress history for speed calculation
        self._progress_history.append({
            'time': current_time,
            'progress': self._overall_progress,
            'message': message,
            'operation': self._current_operation
        })
        
        # Keep only recent history (last 10 minutes)
        cutoff_time = current_time - 600
        self._progress_history = [
            entry for entry in self._progress_history 
            if entry['time'] > cutoff_time
        ]
        
        # Update UI
        self._update_progress_displays()
        self._log_progress(f"{self._overall_progress:.1f}% - {message}")
        
        # Emit signal
        self.progress_updated.emit(overall_percentage, message)
        
    def finish_processing(self, success: bool = True, final_message: str = "Processing completed") -> None:
        """
        Finish progress tracking.
        
        Args:
            success: Whether processing completed successfully
            final_message: Final status message to display
        """
        self._is_processing = False
        
        # Stop update timer
        self._update_timer.stop()
        
        # Update final progress
        if success:
            self._overall_progress = 100.0
            self._current_operation_progress = 100.0
            self.phase_label.setText("Completed")
            self.phase_label.setStyleSheet("font-weight: bold; color: #4CAF50;")
        else:
            self.phase_label.setText("Failed")
            self.phase_label.setStyleSheet("font-weight: bold; color: #f44336;")
        
        self._status_message = final_message
        
        # Disable cancel button
        self.cancel_button.setEnabled(False)
        
        # Update displays one final time
        self._update_progress_displays()
        self._log_progress(final_message)
        
        # Calculate final statistics
        if self._start_time:
            total_time = time.time() - self._start_time
            self._log_progress(f"Total processing time: {self._format_duration(total_time)}")
        
    def reset(self) -> None:
        """Reset the progress widget to initial state."""
        self._is_processing = False
        self._cancellation_requested = False
        self._start_time = None
        self._last_update_time = None
        self._estimated_total_time = None
        self._progress_history.clear()
        
        # Stop timer
        self._update_timer.stop()
        
        # Reset UI
        self._reset_progress()
        self.cancel_button.setEnabled(False)
        self.progress_log.clear()
        
    def is_processing(self) -> bool:
        """Check if processing is currently active."""
        return self._is_processing
        
    def is_cancellation_requested(self) -> bool:
        """Check if cancellation has been requested."""
        return self._cancellation_requested
        
    def get_progress_info(self) -> Dict[str, Any]:
        """
        Get current progress information.
        
        Returns:
            Dictionary with progress details
        """
        elapsed_time = 0.0
        if self._start_time:
            elapsed_time = time.time() - self._start_time
            
        return {
            'overall_progress': self._overall_progress,
            'operation_progress': self._current_operation_progress,
            'current_operation': self._current_operation,
            'status_message': self._status_message,
            'is_processing': self._is_processing,
            'elapsed_time': elapsed_time,
            'estimated_total_time': self._estimated_total_time,
            'updates_count': len(self._progress_history)
        }
        
    @pyqtSlot()
    def _on_cancel_clicked(self):
        """Handle cancel button click."""
        if not self._is_processing or self._cancellation_requested:
            return
            
        # Mark cancellation as requested
        self._cancellation_requested = True
        
        # Update UI
        self.cancel_button.setText("Cancelling...")
        self.cancel_button.setEnabled(False)
        self.phase_label.setText("Cancelling")
        self.phase_label.setStyleSheet("font-weight: bold; color: #FF5722;")
        self._status_message = "Cancellation requested, please wait..."
        self._update_progress_displays()
        self._log_progress("Cancellation requested by user")
        
        # Call cancel callback if set
        if self._cancel_callback:
            try:
                success = self._cancel_callback()
                if success:
                    self._log_progress("Cancellation successful")
                else:
                    self._log_progress("Cancellation failed or not supported")
            except Exception as e:
                self._log_progress(f"Cancellation error: {e}")
        
        # Emit signal
        self.cancel_requested.emit()
        
    @pyqtSlot()
    def _toggle_details(self):
        """Toggle the visibility of the details section."""
        is_visible = self.details_group.isVisible()
        self.details_group.setVisible(not is_visible)
        self.details_button.setText("Hide Details" if not is_visible else "Show Details")
        
    @pyqtSlot()
    def _update_time_displays(self):
        """Update time-related displays (called by timer)."""
        if not self._is_processing or not self._start_time:
            return
            
        current_time = time.time()
        elapsed_time = current_time - self._start_time
        
        # Update elapsed time
        self.elapsed_time_label.setText(self._format_duration(elapsed_time))
        
        # Calculate and update remaining time
        if self._overall_progress > 0:
            if self._estimated_total_time:
                # Use provided estimate
                remaining_time = max(0, self._estimated_total_time - elapsed_time)
            else:
                # Calculate based on current progress
                estimated_total = elapsed_time * (100.0 / self._overall_progress)
                remaining_time = max(0, estimated_total - elapsed_time)
            
            self.remaining_time_label.setText(self._format_duration(remaining_time))
            
            # Calculate ETA
            eta_time = datetime.now() + timedelta(seconds=remaining_time)
            self.eta_label.setText(eta_time.strftime("%H:%M:%S"))
        else:
            self.remaining_time_label.setText("--:--:--")
            self.eta_label.setText("--:--:--")
        
        # Calculate processing speed
        self._update_speed_displays()
        
    def _update_progress_displays(self):
        """Update progress bar displays."""
        # Update progress bars
        self.overall_progress_bar.setValue(int(self._overall_progress))
        self.operation_progress_bar.setValue(int(self._current_operation_progress))
        
        # Update labels
        self.operation_label.setText(self._current_operation or "Processing")
        self.status_label.setText(self._status_message)
        
        # Update statistics
        self.updates_count_label.setText(str(len(self._progress_history)))
        
    def _update_speed_displays(self):
        """Update processing speed displays."""
        if len(self._progress_history) < 2:
            return
            
        # Calculate current speed (progress per minute)
        recent_entries = self._progress_history[-5:]  # Last 5 entries
        if len(recent_entries) >= 2:
            time_diff = recent_entries[-1]['time'] - recent_entries[0]['time']
            progress_diff = recent_entries[-1]['progress'] - recent_entries[0]['progress']
            
            if time_diff > 0:
                speed_per_minute = (progress_diff / time_diff) * 60
                self.speed_label.setText(f"{speed_per_minute:.1f} %/min")
        
        # Calculate average speed
        if len(self._progress_history) >= 2:
            total_time = self._progress_history[-1]['time'] - self._progress_history[0]['time']
            total_progress = self._progress_history[-1]['progress'] - self._progress_history[0]['progress']
            
            if total_time > 0:
                avg_speed = (total_progress / total_time) * 60
                self.avg_speed_label.setText(f"{avg_speed:.1f} %/min")
        
        # Calculate peak speed
        peak_speed = 0.0
        for i in range(1, len(self._progress_history)):
            time_diff = self._progress_history[i]['time'] - self._progress_history[i-1]['time']
            progress_diff = self._progress_history[i]['progress'] - self._progress_history[i-1]['progress']
            
            if time_diff > 0:
                speed = (progress_diff / time_diff) * 60
                peak_speed = max(peak_speed, speed)
        
        self.peak_speed_label.setText(f"{peak_speed:.1f} %/min")
        
        # Count stalls (periods with no progress)
        stall_count = 0
        for i in range(1, len(self._progress_history)):
            if self._progress_history[i]['progress'] == self._progress_history[i-1]['progress']:
                stall_count += 1
        
        self.stall_count_label.setText(str(stall_count))
        
    def _reset_progress(self):
        """Reset progress displays to initial state."""
        self._overall_progress = 0.0
        self._current_operation_progress = 0.0
        self._current_operation = ""
        self._status_message = "Waiting for processing to begin..."
        
        # Reset UI elements
        self.overall_progress_bar.setValue(0)
        self.operation_progress_bar.setValue(0)
        self.operation_label.setText("Ready")
        self.status_label.setText(self._status_message)
        self.phase_label.setText("Idle")
        self.phase_label.setStyleSheet("font-weight: bold; color: #666666;")
        
        # Reset time displays
        self.elapsed_time_label.setText("00:00:00")
        self.remaining_time_label.setText("--:--:--")
        self.eta_label.setText("--:--:--")
        self.speed_label.setText("-- %/min")
        
        # Reset statistics
        self.updates_count_label.setText("0")
        self.avg_speed_label.setText("-- %/min")
        self.peak_speed_label.setText("-- %/min")
        self.stall_count_label.setText("0")
        
        # Reset cancel button
        self.cancel_button.setText("Cancel Processing")
        
    def _log_progress(self, message: str):
        """Add a message to the progress log."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        
        # Add to log widget
        self.progress_log.append(log_entry)
        
        # Auto-scroll to bottom
        scrollbar = self.progress_log.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        
    def _format_duration(self, seconds: float) -> str:
        """
        Format duration in seconds as HH:MM:SS.
        
        Args:
            seconds: Duration in seconds
            
        Returns:
            Formatted duration string
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"