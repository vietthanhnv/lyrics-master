#!/usr/bin/env python3
"""
Debug script to test imports in the same context as the main application.
"""

import sys
import os
from pathlib import Path

# Add src directory to Python path (same as main app)
src_dir = Path(__file__).parent / "src"
sys.path.insert(0, str(src_dir))

print("=== Debug Import Test ===")
print(f"Python path: {sys.path[:3]}...")
print(f"Current working directory: {os.getcwd()}")

def test_direct_import():
    """Test direct import of audio-separator."""
    print("\n1. Testing direct import...")
    try:
        from audio_separator.separator import Separator
        print("✓ Direct import successful")
        return True
    except Exception as e:
        print(f"✗ Direct import failed: {e}")
        return False

def test_from_vocal_separator():
    """Test import from within VocalSeparator class."""
    print("\n2. Testing import from VocalSeparator context...")
    try:
        from src.services.vocal_separator import VocalSeparator
        separator = VocalSeparator()
        print("✓ VocalSeparator created successfully")
        
        # Now test the actual method that's failing
        from src.models.data_models import ModelSize
        result = separator.separate_vocals("dummy_path.mp3", ModelSize.BASE)
        print(f"✓ separate_vocals method called (expected to fail with file not found)")
        return True
    except Exception as e:
        print(f"✗ VocalSeparator test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_import_in_try_catch():
    """Test the exact import pattern used in the vocal separator."""
    print("\n3. Testing exact import pattern from vocal_separator.py...")
    try:
        try:
            from audio_separator.separator import Separator
            print("✓ Import in try-catch successful")
            return True
        except ImportError as e:
            print(f"✗ Import in try-catch failed: {e}")
            return False
    except Exception as e:
        print(f"✗ Outer exception: {e}")
        return False

def main():
    """Run all debug tests."""
    tests = [
        test_direct_import,
        test_from_vocal_separator,
        test_import_in_try_catch
    ]
    
    results = []
    for test in tests:
        try:
            results.append(test())
        except Exception as e:
            print(f"Test failed with exception: {e}")
            results.append(False)
    
    print(f"\n=== Results ===")
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)