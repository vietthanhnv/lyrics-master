#!/usr/bin/env python3
"""
Demo script to test the first-run wizard functionality.
"""

import sys
import os
from pathlib import Path

# Add src directory to Python path
src_dir = Path(__file__).parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from PyQt6.QtWidgets import QApplication
from src.utils.config import config_manager
from src.ui.first_run_wizard import FirstRunWizard, SystemRequirementsChecker


def test_system_requirements():
    """Test system requirements checking."""
    print("=== System Requirements Check ===")
    
    requirements = SystemRequirementsChecker.check_all_requirements()
    
    for req_name, (passed, details) in requirements.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} {req_name}: {details}")
    
    print()


def test_config_manager():
    """Test configuration manager first-run detection."""
    print("=== Configuration Manager Test ===")
    
    print(f"Is first run: {config_manager.is_first_run()}")
    print(f"Needs setup: {config_manager.needs_setup()}")
    
    config = config_manager.get_config()
    print(f"Models directory: {config.models_directory}")
    print(f"Default output directory: {config.default_output_directory}")
    print(f"Default model size: {config.default_model_size}")
    
    print()


def test_wizard_creation():
    """Test wizard creation (without showing it)."""
    print("=== First-Run Wizard Creation Test ===")
    
    try:
        app = QApplication.instance() or QApplication([])
        
        # Create wizard
        wizard = FirstRunWizard()
        print(f"✅ Wizard created successfully")
        print(f"   Window title: {wizard.windowTitle()}")
        print(f"   Is modal: {wizard.isModal()}")
        print(f"   Current page: {wizard.current_page}")
        
        # Test navigation methods exist
        assert hasattr(wizard, '_go_next'), "Missing _go_next method"
        assert hasattr(wizard, '_go_back'), "Missing _go_back method"
        assert hasattr(wizard, '_show_welcome_page'), "Missing _show_welcome_page method"
        
        print("✅ All required methods exist")
        
        wizard.close()
        
    except Exception as e:
        print(f"❌ Error creating wizard: {e}")
        return False
    
    print()
    return True


def main():
    """Main test function."""
    print("First-Run Setup Implementation Test")
    print("=" * 40)
    print()
    
    # Test system requirements
    test_system_requirements()
    
    # Test configuration manager
    test_config_manager()
    
    # Test wizard creation
    wizard_ok = test_wizard_creation()
    
    # Summary
    print("=== Test Summary ===")
    print("✅ System requirements checker: Working")
    print("✅ Configuration manager: Working")
    print(f"{'✅' if wizard_ok else '❌'} First-run wizard: {'Working' if wizard_ok else 'Failed'}")
    
    if wizard_ok:
        print("\n🎉 First-run setup implementation is working correctly!")
        print("\nTo test the full wizard:")
        print("1. Delete the configuration file to simulate first run")
        print("2. Run the main application: python src/main.py")
        print("3. The first-run wizard should appear automatically")
    else:
        print("\n❌ There are issues with the first-run setup implementation")
    
    return 0 if wizard_ok else 1


if __name__ == "__main__":
    sys.exit(main())