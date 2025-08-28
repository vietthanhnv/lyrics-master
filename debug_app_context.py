#!/usr/bin/env python3
"""
Debug script to test imports in the exact same context as the running application.
"""

import sys
import os
from pathlib import Path

# Add src directory to Python path (same as main app)
src_dir = Path(__file__).parent / "src"
sys.path.insert(0, str(src_dir))

def test_with_pyqt():
    """Test imports after initializing PyQt6."""
    print("=== Testing with PyQt6 Context ===")
    
    try:
        # Initialize PyQt6 (same as main app)
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtCore import Qt
        
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )
        
        app = QApplication([])
        app.setApplicationName("Debug Test")
        print("✓ PyQt6 initialized")
        
        # Now test the imports
        print("\n1. Testing audio-separator import after PyQt6 init...")
        try:
            from audio_separator.separator import Separator
            print("✓ audio-separator import successful")
        except Exception as e:
            print(f"✗ audio-separator import failed: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        # Test creating the services
        print("\n2. Testing service creation...")
        try:
            from src.services.application_controller import ApplicationController
            controller = ApplicationController()
            print("✓ ApplicationController created")
        except Exception as e:
            print(f"✗ ApplicationController creation failed: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        # Test the actual processing call
        print("\n3. Testing processing with real file...")
        try:
            from src.models.data_models import ProcessingOptions, ModelSize, ExportFormat
            
            # Check if test file exists
            test_file = "data/hello.mp3"
            if not os.path.exists(test_file):
                print(f"Test file {test_file} not found, skipping processing test")
                return True
            
            options = ProcessingOptions(
                model_size=ModelSize.BASE,
                export_formats=[ExportFormat.SRT],
                output_directory="temp_output"
            )
            
            # Create output directory
            os.makedirs("temp_output", exist_ok=True)
            
            print(f"Processing {test_file}...")
            result = controller.process_audio_file(test_file, options)
            
            if result.success:
                print("✓ Processing completed successfully!")
                print(f"Output files: {result.output_files}")
            else:
                print(f"✗ Processing failed: {result.error_message}")
                return False
                
        except Exception as e:
            print(f"✗ Processing test failed: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        return True
        
    except Exception as e:
        print(f"✗ PyQt6 test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run the debug test."""
    success = test_with_pyqt()
    
    if success:
        print("\n✓ All tests passed! The issue might be elsewhere.")
    else:
        print("\n✗ Found the issue in PyQt6 context.")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)