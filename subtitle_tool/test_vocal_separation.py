#!/usr/bin/env python3
"""
Test script to debug vocal separation output files.
"""

import sys
import os
from pathlib import Path

# Add src directory to Python path
src_dir = Path(__file__).parent / "src"
sys.path.insert(0, str(src_dir))

def test_vocal_separation():
    """Test vocal separation with the hello.mp3 file."""
    print("=== Testing Vocal Separation ===")
    
    try:
        from src.services.vocal_separator import VocalSeparator
        from src.models.data_models import ModelSize
        
        # Create output directory in workspace
        output_dir = "test_output"
        os.makedirs(output_dir, exist_ok=True)
        
        # Create separator with local output directory
        separator = VocalSeparator(temp_dir=output_dir)
        
        # Test file
        test_file = "data/hello.mp3"
        if not os.path.exists(test_file):
            print(f"Test file {test_file} not found")
            return False
        
        print(f"Processing {test_file}...")
        result = separator.separate_vocals(test_file, ModelSize.BASE)
        
        if result.success:
            print(f"✓ Vocal separation successful!")
            print(f"Vocals path: {result.vocals_path}")
            
            # List all files in output directory
            print(f"\nFiles in output directory:")
            for root, dirs, files in os.walk(output_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    print(f"  {file_path}")
            
            return True
        else:
            print(f"✗ Vocal separation failed: {result.error_message}")
            return False
            
    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run the test."""
    success = test_vocal_separation()
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)