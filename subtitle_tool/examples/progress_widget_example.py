"""
Example demonstrating the ProgressWidget functionality.

This example shows how to use the ProgressWidget for tracking progress
of long-running operations with real-time updates, cancellation support,
and time estimation.
"""

import sys
import time
import random
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QHBoxLayout
from PyQt6.QtCore import QTimer, QThread, pyqtSignal

# Add src to path for imports
sys.path.insert(0, 'src')

from ui.progress_widget import ProgressWidget


class MockProcessingThread(QThread):
    """Mock processing thread that simulates long-running operations."""
    
    progress_updated = pyqtSignal(float, str, str, float)  # overall, message, operation, operation_progress
    processing_finished = pyqtSignal(bool, str)  # success, message
    
    def __init__(self):
        super().__init__()
        self.should_cancel = False
        
    def run(self):
        """Simulate a multi-phase processing operation."""
        try:
            # Phase 1: Vocal Separation (0-40%)
            self._simulate_phase(
                "Vocal Separation",
                start_progress=0.0,
                end_progress=40.0,
                duration=8.0,  # 8 seconds
                steps=[
                    "Loading audio file...",
                    "Initializing Demucs model...",
                    "Analyzing audio structure...",
                    "Separating vocal tracks...",
                    "Optimizing vocal isolation...",
                    "Saving separated vocals..."
                ]
            )
            
            if self.should_cancel:
                return
                
            # Phase 2: Speech Recognition (40-80%)
            self._simulate_phase(
                "Speech Recognition",
                start_progress=40.0,
                end_progress=80.0,
                duration=10.0,  # 10 seconds
                steps=[
                    "Loading WhisperX model...",
                    "Preprocessing audio...",
                    "Running speech recognition...",
                    "Performing forced alignment...",
                    "Calculating word timestamps...",
                    "Validating transcription quality..."
                ]
            )
            
            if self.should_cancel:
                return
                
            # Phase 3: Subtitle Generation (80-100%)
            self._simulate_phase(
                "Subtitle Generation",
                start_progress=80.0,
                end_progress=100.0,
                duration=4.0,  # 4 seconds
                steps=[
                    "Formatting subtitle data...",
                    "Generating SRT files...",
                    "Creating karaoke ASS files...",
                    "Exporting VTT format...",
                    "Saving JSON alignment data..."
                ]
            )
            
            if self.should_cancel:
                self.processing_finished.emit(False, "Processing cancelled by user")
            else:
                self.processing_finished.emit(True, "All subtitle formats generated successfully!")
                
        except Exception as e:
            self.processing_finished.emit(False, f"Processing failed: {str(e)}")
    
    def _simulate_phase(self, operation_name, start_progress, end_progress, duration, steps):
        """Simulate a processing phase with multiple steps."""
        progress_range = end_progress - start_progress
        step_duration = duration / len(steps)
        
        for i, step_message in enumerate(steps):
            if self.should_cancel:
                return
                
            # Calculate progress within this phase
            step_progress = (i / len(steps)) * 100.0
            overall_progress = start_progress + (i / len(steps)) * progress_range
            
            # Emit progress update
            self.progress_updated.emit(
                overall_progress,
                step_message,
                operation_name,
                step_progress
            )
            
            # Simulate processing time with some randomness
            sleep_time = step_duration * (0.8 + random.random() * 0.4)  # ±20% variation
            time.sleep(sleep_time)
        
        # Complete the phase
        self.progress_updated.emit(
            end_progress,
            f"{operation_name} completed",
            operation_name,
            100.0
        )
    
    def cancel_processing(self):
        """Request cancellation of processing."""
        self.should_cancel = True
        return True


class ProgressExampleWindow(QMainWindow):
    """Main window demonstrating progress widget functionality."""
    
    def __init__(self):
        super().__init__()
        self.processing_thread = None
        self.setup_ui()
        
    def setup_ui(self):
        """Set up the user interface."""
        self.setWindowTitle("Progress Widget Example")
        self.setGeometry(100, 100, 800, 600)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Control buttons
        button_layout = QHBoxLayout()
        
        self.start_button = QPushButton("Start Processing")
        self.start_button.clicked.connect(self.start_processing)
        button_layout.addWidget(self.start_button)
        
        self.reset_button = QPushButton("Reset")
        self.reset_button.clicked.connect(self.reset_progress)
        button_layout.addWidget(self.reset_button)
        
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        # Progress widget
        self.progress_widget = ProgressWidget()
        self.progress_widget.cancel_requested.connect(self.cancel_processing)
        layout.addWidget(self.progress_widget)
        
        # Set up cancel callback
        self.progress_widget.set_cancel_callback(self.handle_cancel_request)
        
    def start_processing(self):
        """Start the mock processing operation."""
        if self.processing_thread and self.processing_thread.isRunning():
            return
            
        # Disable start button
        self.start_button.setEnabled(False)
        
        # Start progress tracking with estimated time (22 seconds total)
        self.progress_widget.start_processing(estimated_total_time=22.0)
        
        # Create and start processing thread
        self.processing_thread = MockProcessingThread()
        self.processing_thread.progress_updated.connect(self.update_progress)
        self.processing_thread.processing_finished.connect(self.finish_processing)
        self.processing_thread.start()
        
    def update_progress(self, overall_progress, message, operation, operation_progress):
        """Update progress display."""
        self.progress_widget.update_progress(
            overall_progress, message, operation, operation_progress
        )
        
    def finish_processing(self, success, message):
        """Handle processing completion."""
        self.progress_widget.finish_processing(success, message)
        self.start_button.setEnabled(True)
        
        # Clean up thread
        if self.processing_thread:
            self.processing_thread.wait()
            self.processing_thread = None
            
    def cancel_processing(self):
        """Handle cancellation request."""
        if self.processing_thread and self.processing_thread.isRunning():
            self.processing_thread.cancel_processing()
            
    def handle_cancel_request(self):
        """Handle cancel callback from progress widget."""
        if self.processing_thread and self.processing_thread.isRunning():
            self.processing_thread.cancel_processing()
            return True
        return False
        
    def reset_progress(self):
        """Reset the progress widget."""
        # Cancel any running processing
        if self.processing_thread and self.processing_thread.isRunning():
            self.processing_thread.cancel_processing()
            self.processing_thread.wait()
            
        # Reset progress widget
        self.progress_widget.reset()
        self.start_button.setEnabled(True)


def main():
    """Run the progress widget example."""
    app = QApplication(sys.argv)
    
    # Create and show the example window
    window = ProgressExampleWindow()
    window.show()
    
    # Add some example text to help users
    print("Progress Widget Example")
    print("======================")
    print("Click 'Start Processing' to begin a simulated processing operation.")
    print("The progress widget will show:")
    print("- Overall progress and current operation progress")
    print("- Real-time status messages")
    print("- Elapsed time and estimated remaining time")
    print("- Processing speed calculations")
    print("- Detailed progress log (click 'Show Details')")
    print("- Cancellation support (click 'Cancel Processing')")
    print("")
    print("Try cancelling mid-process to see cancellation handling.")
    print("Use 'Reset' to return to the initial state.")
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()