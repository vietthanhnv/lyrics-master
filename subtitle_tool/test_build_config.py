#!/usr/bin/env python3
"""
Test script to verify the build configuration is correct.

This script checks that all necessary files are in place and that
the PyInstaller spec file is valid.
"""

import sys
import os
from pathlib import Path


def test_build_files():
    """Test that all build files are present."""
    print("🔍 Testing build configuration...")
    
    required_files = [
        "lyric_to_subtitle_app.spec",
        "build_scripts/build.py",
        "build_scripts/build_windows.bat",
        "build_scripts/build_macos.sh", 
        "build_scripts/build_linux.sh",
        "build_scripts/create_desktop_file.sh",
        "build_config.yaml",
        "requirements-build.txt",
        "BUILD.md"
    ]
    
    missing_files = []
    for file_path in required_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)
        else:
            print(f"   ✅ {file_path}")
    
    if missing_files:
        print(f"\n❌ Missing files: {missing_files}")
        return False
    
    print("\n✅ All build files are present")
    return True


def test_spec_file():
    """Test that the spec file is valid Python."""
    print("\n🔍 Testing PyInstaller spec file...")
    
    try:
        spec_path = Path("lyric_to_subtitle_app.spec")
        with open(spec_path, 'r') as f:
            spec_content = f.read()
        
        # Basic syntax check
        compile(spec_content, str(spec_path), 'exec')
        print("   ✅ Spec file syntax is valid")
        
        # Check for required variables
        required_vars = ['a', 'pyz', 'exe']
        for var in required_vars:
            if var not in spec_content:
                print(f"   ⚠️  Warning: Variable '{var}' not found in spec file")
            else:
                print(f"   ✅ Found variable '{var}'")
        
        return True
        
    except SyntaxError as e:
        print(f"   ❌ Spec file syntax error: {e}")
        return False
    except Exception as e:
        print(f"   ❌ Error reading spec file: {e}")
        return False


def test_dependencies():
    """Test that build dependencies can be imported."""
    print("\n🔍 Testing build dependencies...")
    
    # Test PyInstaller
    try:
        import PyInstaller
        print(f"   ✅ PyInstaller {PyInstaller.__version__}")
    except ImportError:
        print("   ❌ PyInstaller not installed")
        print("      Install with: pip install pyinstaller")
        return False
    
    # Test main application dependencies
    try:
        import PyQt6
        print(f"   ✅ PyQt6 available")
    except ImportError:
        print("   ⚠️  PyQt6 not installed (needed for application)")
    
    try:
        import torch
        print(f"   ✅ PyTorch {torch.__version__}")
    except ImportError:
        print("   ⚠️  PyTorch not installed (needed for AI models)")
    
    return True


def test_entry_point():
    """Test that the main entry point exists and is valid."""
    print("\n🔍 Testing application entry point...")
    
    main_script = Path("src/main.py")
    if not main_script.exists():
        print(f"   ❌ Main script not found: {main_script}")
        return False
    
    try:
        with open(main_script, 'r') as f:
            content = f.read()
        
        # Check for main function
        if 'def main():' not in content:
            print("   ❌ main() function not found")
            return False
        
        # Check for if __name__ == "__main__"
        if 'if __name__ == "__main__":' not in content:
            print("   ❌ __main__ guard not found")
            return False
        
        print("   ✅ Entry point is valid")
        return True
        
    except Exception as e:
        print(f"   ❌ Error reading main script: {e}")
        return False


def main():
    """Run all build configuration tests."""
    print("🚀 Testing Lyric-to-Subtitle App build configuration\n")
    
    tests = [
        test_build_files,
        test_spec_file,
        test_dependencies,
        test_entry_point,
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"   ❌ Test failed with exception: {e}")
            results.append(False)
    
    print("\n" + "="*50)
    
    if all(results):
        print("✅ All build configuration tests passed!")
        print("\nYou can now build the application:")
        print("  Windows: build_scripts\\build_windows.bat")
        print("  macOS:   ./build_scripts/build_macos.sh")
        print("  Linux:   ./build_scripts/build_linux.sh")
        return 0
    else:
        failed_count = len([r for r in results if not r])
        print(f"❌ {failed_count} test(s) failed!")
        print("\nPlease fix the issues above before building.")
        return 1


if __name__ == "__main__":
    sys.exit(main())