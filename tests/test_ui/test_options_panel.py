"""
Tests for the OptionsPanel UI component.
"""

import pytest
from unittest.mock import Mock, patch
from pathlib import Path

from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import Qt
from PyQt6.QtTest import QTest

from src.ui.options_panel import OptionsPanel
from src.models.data_models import (
    ProcessingOptions, ModelSize, ExportFormat, TranslationService
)


@pytest.fixture
def app():
    """Create QApplication instance for testing."""
    return QApplication.instance() or QApplication([])


@pytest.fixture
def options_panel(app):
    """Create OptionsPanel instance for testing."""
    panel = OptionsPanel()
    return panel


class TestOptionsPanel:
    """Test cases for OptionsPanel functionality."""
    
    def test_initialization(self, options_panel):
        """Test that options panel initializes correctly."""
        assert options_panel is not None
        assert options_panel.tab_widget is not None
        assert options_panel.tab_widget.count() == 4  # 4 tabs
        
        # Check tab names
        tab_names = [
            options_panel.tab_widget.tabText(i) 
            for i in range(options_panel.tab_widget.count())
        ]
        expected_tabs = ["Model & Processing", "Export Formats", "Translation", "Output & Batch"]
        assert tab_names == expected_tabs
        
    def test_default_options(self, options_panel):
        """Test that default options are set correctly."""
        options = options_panel.get_current_options()
        
        assert options.model_size == ModelSize.BASE
        assert ExportFormat.SRT in options.export_formats
        assert options.word_level_srt is True
        assert options.karaoke_mode is False
        assert options.translation_enabled is False
        assert options.target_language is None
        assert options.translation_service is None
        
    def test_model_size_selection(self, options_panel):
        """Test model size selection functionality."""
        # Test changing model size
        options_panel.model_size_combo.setCurrentIndex(2)  # Should be SMALL
        options = options_panel.get_current_options()
        assert options.model_size == ModelSize.SMALL
        
    def test_export_format_selection(self, options_panel):
        """Test export format selection functionality."""
        # Initially only SRT should be selected
        options = options_panel.get_current_options()
        assert options.export_formats == [ExportFormat.SRT]
        
        # Select additional formats
        options_panel.format_checks[ExportFormat.ASS].setChecked(True)
        options_panel.format_checks[ExportFormat.VTT].setChecked(True)
        
        options = options_panel.get_current_options()
        assert ExportFormat.SRT in options.export_formats
        assert ExportFormat.ASS in options.export_formats
        assert ExportFormat.VTT in options.export_formats
        
    def test_karaoke_mode_toggle(self, options_panel):
        """Test karaoke mode toggle functionality."""
        # Initially disabled
        assert not options_panel.karaoke_check.isChecked()
        
        # Enable karaoke mode
        options_panel.karaoke_check.setChecked(True)
        options = options_panel.get_current_options()
        assert options.karaoke_mode is True
        
    def test_translation_settings(self, options_panel):
        """Test translation settings functionality."""
        # Initially disabled
        assert not options_panel.translation_check.isChecked()
        assert not options_panel.translation_service_combo.isEnabled()
        assert not options_panel.target_language_combo.isEnabled()
        
        # Enable translation
        options_panel.translation_check.setChecked(True)
        
        # Controls should now be enabled
        assert options_panel.translation_service_combo.isEnabled()
        assert options_panel.target_language_combo.isEnabled()
        
        # Set translation options
        options_panel.translation_service_combo.setCurrentIndex(0)  # DeepL
        options_panel.target_language_combo.setCurrentIndex(1)  # Spanish
        
        options = options_panel.get_current_options()
        assert options.translation_enabled is True
        assert options.translation_service == TranslationService.DEEPL
        assert options.target_language == "es"  # Spanish code
        
    def test_output_directory_setting(self, options_panel):
        """Test output directory setting functionality."""
        test_dir = "/test/output/directory"
        options_panel.output_dir_edit.setText(test_dir)
        
        options = options_panel.get_current_options()
        assert options.output_directory == test_dir
        
    @patch('PyQt6.QtWidgets.QFileDialog.getExistingDirectory')
    def test_browse_output_directory(self, mock_dialog, options_panel):
        """Test browse output directory functionality."""
        test_dir = "/selected/directory"
        mock_dialog.return_value = test_dir
        
        # Simulate clicking browse button
        options_panel._browse_output_directory()
        
        assert options_panel.output_dir_edit.text() == test_dir
        mock_dialog.assert_called_once()
        
    def test_options_validation(self, options_panel):
        """Test options validation functionality."""
        # Valid options should pass validation
        assert options_panel.is_valid()
        
        # Invalid options should fail validation
        options_panel.output_dir_edit.setText("")  # Empty output directory
        options_panel.translation_check.setChecked(True)  # Enable translation without language
        
        assert not options_panel.is_valid()
        errors = options_panel.validate_current_options()
        assert len(errors) > 0
        
    def test_reset_to_defaults(self, options_panel):
        """Test reset to defaults functionality."""
        # Change some settings
        options_panel.model_size_combo.setCurrentIndex(3)  # MEDIUM
        options_panel.karaoke_check.setChecked(True)
        options_panel.translation_check.setChecked(True)
        
        # Reset to defaults (simulate clicking Yes in dialog)
        with patch('PyQt6.QtWidgets.QMessageBox.question') as mock_question:
            mock_question.return_value = QMessageBox.StandardButton.Yes
            options_panel._reset_to_defaults()
        
        # Check that settings are back to defaults
        options = options_panel.get_current_options()
        assert options.model_size == ModelSize.BASE
        assert not options.karaoke_mode
        assert not options.translation_enabled
        
    def test_set_options(self, options_panel):
        """Test setting options programmatically."""
        # Create custom options
        custom_options = ProcessingOptions(
            model_size=ModelSize.LARGE,
            export_formats=[ExportFormat.ASS, ExportFormat.VTT],
            word_level_srt=False,
            karaoke_mode=True,
            translation_enabled=True,
            target_language="fr",
            translation_service=TranslationService.GOOGLE,
            output_directory="/custom/output"
        )
        
        # Set options
        options_panel.set_options(custom_options)
        
        # Verify UI reflects the options
        assert options_panel.model_size_combo.currentData() == ModelSize.LARGE
        assert options_panel.format_checks[ExportFormat.ASS].isChecked()
        assert options_panel.format_checks[ExportFormat.VTT].isChecked()
        assert not options_panel.format_checks[ExportFormat.SRT].isChecked()
        assert not options_panel.word_level_check.isChecked()
        assert options_panel.karaoke_check.isChecked()
        assert options_panel.translation_check.isChecked()
        assert options_panel.target_language_combo.currentData() == "fr"
        assert options_panel.translation_service_combo.currentData() == TranslationService.GOOGLE
        assert options_panel.output_dir_edit.text() == "/custom/output"
        
    def test_options_changed_signal(self, options_panel):
        """Test that options_changed signal is emitted correctly."""
        signal_received = Mock()
        options_panel.options_changed.connect(signal_received)
        
        # Manually trigger options change (simulates user interaction)
        options_panel._on_options_changed()
        
        # Signal should have been emitted
        signal_received.assert_called()
        
        # Get the emitted options
        emitted_options = signal_received.call_args[0][0]
        assert isinstance(emitted_options, ProcessingOptions)
        
    def test_file_naming_options(self, options_panel):
        """Test file naming options functionality."""
        # Test that the naming combo box has the expected options
        naming_options = [options_panel.naming_combo.itemText(i) 
                         for i in range(options_panel.naming_combo.count())]
        expected_options = ["Original name + format", "Original name + timestamp", "Custom prefix"]
        assert naming_options == expected_options
        
        # Test that prefix controls exist
        assert hasattr(options_panel, 'prefix_label')
        assert hasattr(options_panel, 'prefix_edit')
        
        # Test changing naming style
        options_panel.naming_combo.setCurrentText("Custom prefix")
        assert options_panel.naming_combo.currentText() == "Custom prefix"
        
    def test_confidence_threshold_setting(self, options_panel):
        """Test confidence threshold setting."""
        # Set confidence threshold
        options_panel.confidence_spin.setValue(0.75)
        
        # Note: This would be part of extended ProcessingOptions in a real implementation
        # For now, just verify the UI control works
        assert options_panel.confidence_spin.value() == 0.75
        
    def test_advanced_options(self, options_panel):
        """Test advanced processing options."""
        # Test denoising option
        options_panel.denoise_check.setChecked(True)
        assert options_panel.denoise_check.isChecked()
        
        # Test vocal enhancement option
        options_panel.enhance_vocals_check.setChecked(True)
        assert options_panel.enhance_vocals_check.isChecked()
        
    def test_batch_processing_options(self, options_panel):
        """Test batch processing configuration options."""
        # Test parallel processing
        options_panel.parallel_check.setChecked(True)
        assert options_panel.parallel_check.isChecked()
        
        # Test max concurrent files
        options_panel.max_concurrent_spin.setValue(4)
        assert options_panel.max_concurrent_spin.value() == 4
        
        # Test continue on error
        options_panel.continue_on_error_check.setChecked(False)
        assert not options_panel.continue_on_error_check.isChecked()
        
        # Test batch report generation
        options_panel.batch_report_check.setChecked(False)
        assert not options_panel.batch_report_check.isChecked()
        
    def test_performance_settings(self, options_panel):
        """Test performance configuration options."""
        # Test memory usage setting
        options_panel.memory_combo.setCurrentText("Aggressive")
        assert options_panel.memory_combo.currentText() == "Aggressive"
        
        # Test cleanup temp files
        options_panel.cleanup_temp_check.setChecked(False)
        assert not options_panel.cleanup_temp_check.isChecked()


class TestOptionsValidation:
    """Test cases for options validation."""
    
    def test_valid_minimal_options(self, options_panel):
        """Test validation of minimal valid options."""
        # Set minimal valid options
        options_panel.output_dir_edit.setText("/valid/output")
        
        errors = options_panel.validate_current_options()
        assert len(errors) == 0
        
    def test_invalid_empty_output_directory(self, options_panel):
        """Test validation fails for empty output directory."""
        options_panel.output_dir_edit.setText("")
        
        errors = options_panel.validate_current_options()
        assert any("output directory" in error.lower() for error in errors)
        
    def test_invalid_translation_without_language(self, options_panel):
        """Test validation fails for translation without target language."""
        options_panel.translation_check.setChecked(True)
        options_panel.target_language_combo.setCurrentIndex(-1)  # No selection
        
        errors = options_panel.validate_current_options()
        assert any("target language" in error.lower() for error in errors)
        
    def test_invalid_no_export_formats(self, options_panel):
        """Test validation fails when no export formats are selected."""
        # Uncheck all format checkboxes
        for checkbox in options_panel.format_checks.values():
            checkbox.setChecked(False)
        
        errors = options_panel.validate_current_options()
        assert any("export format" in error.lower() for error in errors)


class TestUIInteractions:
    """Test cases for UI interactions and user experience."""
    
    def test_tab_navigation(self, options_panel):
        """Test tab navigation functionality."""
        # Test switching between tabs
        for i in range(options_panel.tab_widget.count()):
            options_panel.tab_widget.setCurrentIndex(i)
            assert options_panel.tab_widget.currentIndex() == i
            
    def test_tooltip_presence(self, options_panel):
        """Test that important controls have tooltips."""
        # Check that key controls have tooltips
        assert options_panel.model_size_combo.toolTip() != ""
        assert options_panel.karaoke_check.toolTip() != ""
        assert options_panel.translation_check.toolTip() != ""
        assert options_panel.output_dir_edit.toolTip() != ""
        
    def test_control_enabling_disabling(self, options_panel):
        """Test that controls are properly enabled/disabled based on context."""
        # Translation controls should be disabled initially
        assert not options_panel.translation_service_combo.isEnabled()
        assert not options_panel.target_language_combo.isEnabled()
        
        # Enable translation
        options_panel.translation_check.setChecked(True)
        
        # Controls should now be enabled
        assert options_panel.translation_service_combo.isEnabled()
        assert options_panel.target_language_combo.isEnabled()
        
        # Disable translation again
        options_panel.translation_check.setChecked(False)
        
        # Controls should be disabled again
        assert not options_panel.translation_service_combo.isEnabled()
        assert not options_panel.target_language_combo.isEnabled()