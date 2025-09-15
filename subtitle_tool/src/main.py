"""
Main entry point for the Lyric-to-Subtitle App.

This module initializes the application and starts the PyQt6 event loop.
"""

import sys

sys.path.append(".")

import os
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

# Add src directory to Python path for imports
src_dir = Path(__file__).parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))


def setup_application() -> QApplication:
    """Set up and configure the PyQt6 application."""
    # Enable high DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    
    app = QApplication(sys.argv)
    app.setApplicationName("Lyric-to-Subtitle App")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("Lyric-to-Subtitle App Team")
    
    return app


def create_connected_main_window():
    """Create main window and connect it to the application controller."""
    from src.ui.main_window import MainWindow
    from src.services.application_controller import ApplicationController
    from PyQt6.QtCore import QThread, QObject, pyqtSignal
    
    # Create the main window
    main_window = MainWindow()
    
    # Create the application controller
    app_controller = ApplicationController()
    
    # Connect UI signals to controller methods
    def on_processing_requested(files, options):
        """Handle processing request from UI."""
        try:
            # Update UI to show processing started
            main_window.start_progress_tracking()
            
            # Process files (this should be done in a separate thread for real apps)
            if len(files) == 1:
                result = app_controller.process_audio_file(files[0], options)
            else:
                result = app_controller.process_batch(files, options)
            
            # Update UI with results
            if hasattr(result, 'success'):  # Single file result
                if result.success:
                    main_window.show_processing_success(result)
                    main_window.finish_progress_tracking(True, "Processing completed successfully!")
                else:
                    main_window.show_processing_error(result.error_message or "Processing failed")
                    main_window.finish_progress_tracking(False, result.error_message or "Processing failed")
            else:  # Batch result
                if result.successful_files > 0:
                    main_window.show_batch_results(result)
                    main_window.finish_progress_tracking(True, f"Batch completed: {result.successful_files}/{result.total_files} successful")
                else:
                    main_window.show_processing_error("All files failed to process")
                    main_window.finish_progress_tracking(False, "Batch processing failed")
                    
        except Exception as e:
            main_window.show_processing_error(f"Processing error: {str(e)}")
            main_window.finish_progress_tracking(False, f"Error: {str(e)}")
    
    def on_cancel_requested():
        """Handle cancellation request from UI."""
        success = app_controller.cancel_processing()
        if success:
            main_window.reset_progress_tracking()
            main_window.update_status("Processing cancelled")
        else:
            main_window.update_status("Failed to cancel processing")
    
    # Set up progress callback
    def on_progress_update(percentage, message):
        """Handle progress updates from controller."""
        main_window.update_progress(percentage, message)
    
    app_controller.set_progress_callback(on_progress_update)
    
    # Connect signals
    main_window.processing_requested.connect(on_processing_requested)
    main_window.cancel_processing_requested.connect(on_cancel_requested)
    
    return main_window, app_controller


def main():
    """Main application entry point."""
    try:
        app = setup_application()
        
        # Import here to avoid circular imports and ensure Qt is initialized
        from src.ui.first_run_wizard import FirstRunWizard
        from src.utils.config import config_manager
        
        # Check if first-run setup is needed
        if config_manager.needs_setup():
            # Show first-run wizard
            wizard = FirstRunWizard()
            
            def on_setup_completed(success):
                if success:
                    # Create and show main window after successful setup
                    main_window, app_controller = create_connected_main_window()
                    main_window.show()
                else:
                    # Exit if setup was cancelled or failed
                    app.quit()
            
            wizard.setup_completed.connect(on_setup_completed)
            wizard.show()
        else:
            # Normal startup - show main window directly
            main_window, app_controller = create_connected_main_window()
            main_window.show()
        
        # Start event loop
        sys.exit(app.exec())
        
    except ImportError as e:
        print(f"Failed to import required modules: {e}")
        print("Please ensure all dependencies are installed.")
        sys.exit(1)
    except Exception as e:
        print(f"Application failed to start: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()