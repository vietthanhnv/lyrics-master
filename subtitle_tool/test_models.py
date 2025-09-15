#!/usr/bin/env python3
"""
Test script to verify that the AI models are working correctly.
"""

import sys
import os
from pathlib import Path

# Add src directory to Python path
src_dir = Path(__file__).parent / "src"
sys.path.insert(0, str(src_dir))

def test_audio_separator():
    """Test audio-separator functionality."""
    print("Testing audio-separator...")
    try:
        from audio_separator.separator import Separator
        print("✓ audio-separator import successful")
        
        # Create separator instance
        separator = Separator(output_dir="temp_test")
        print("✓ Separator instance created")
        
        return True
    except Exception as e:
        print(f"✗ audio-separator test failed: {e}")
        return False

def test_whisper():
    """Test OpenAI Whisper functionality."""
    print("\nTesting OpenAI Whisper...")
    try:
        import whisper
        print("✓ whisper import successful")
        
        # List available models
        models = whisper.available_models()
        print(f"✓ Available models: {models}")
        
        return True
    except Exception as e:
        print(f"✗ whisper test failed: {e}")
        return False

def test_vocal_separator():
    """Test our VocalSeparator class."""
    print("\nTesting VocalSeparator class...")
    try:
        from src.services.vocal_separator import VocalSeparator
        from src.models.data_models import ModelSize
        
        separator = VocalSeparator()
        print("✓ VocalSeparator instance created")
        
        # Test model mapping
        model = separator._get_audio_separator_model(ModelSize.BASE)
        print(f"✓ Model mapping works: {model}")
        
        return True
    except Exception as e:
        print(f"✗ VocalSeparator test failed: {e}")
        return False

def test_speech_recognizer():
    """Test our SpeechRecognizer class."""
    print("\nTesting SpeechRecognizer class...")
    try:
        from src.services.speech_recognizer import SpeechRecognizer
        from src.models.data_models import ModelSize
        
        recognizer = SpeechRecognizer()
        print("✓ SpeechRecognizer instance created")
        
        # Test model mapping
        model = recognizer._get_whisper_model_name(ModelSize.BASE)
        print(f"✓ Model mapping works: {model}")
        
        return True
    except Exception as e:
        print(f"✗ SpeechRecognizer test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("=== AI Models Test Suite ===\n")
    
    tests = [
        test_audio_separator,
        test_whisper,
        test_vocal_separator,
        test_speech_recognizer
    ]
    
    results = []
    for test in tests:
        results.append(test())
    
    print(f"\n=== Test Results ===")
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("✓ All tests passed! Models are ready to use.")
    else:
        print("✗ Some tests failed. Check the output above for details.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)