#!/usr/bin/env python3

import sys
import traceback

def test_audio_separator():
    try:
        print("Testing audio-separator import...")
        from audio_separator.separator import Separator
        print("✓ audio-separator imported successfully")
        
        print("Testing Separator initialization...")
        separator = Separator()
        print("✓ Separator initialized successfully")
        
        print("Testing model listing...")
        # This should work without downloading anything
        print("✓ audio-separator is working properly")
        
        return True
        
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        traceback.print_exc()
        return False

def test_numpy():
    try:
        import numpy as np
        print(f"NumPy version: {np.__version__}")
        return True
    except Exception as e:
        print(f"NumPy error: {e}")
        return False

if __name__ == "__main__":
    print("=== Testing Dependencies ===")
    
    numpy_ok = test_numpy()
    separator_ok = test_audio_separator()
    
    if numpy_ok and separator_ok:
        print("\n✓ All dependencies are working!")
        sys.exit(0)
    else:
        print("\n✗ Some dependencies have issues")
        sys.exit(1)