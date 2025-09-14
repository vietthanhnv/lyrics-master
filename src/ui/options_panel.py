"""
Processing configuration and options panel for the lyric-to-subtitle application.

This module provides a comprehensive options panel that allows users to configure
all processing settings including model selection, export formats, translation
settings, and output options.
"""

import os
from pathlib import Path
from typing import List, Optional, Dict, Any

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QGroupBox, QLabel, QComboBox, QCheckBox, QPushButton,
    QLineEdit, QFileDialog, QSpinBox, QDoubleSpinBox,
    QTabWidget, QScrollArea, QFrame, QSizePolicy,
    QMessageBox, QToolTip, QApplication
)
from PyQt6.QtGui import QFont, QPalette

from ..models.data_models import (
    ProcessingOptions, ModelSize, ExportFormat, 
    TranslationService
)


class OptionsPanel(QWidget):
    """
    Comprehensive options panel for processing configuration.
    
    Provides configuration for:
    - Model selection and processing options
    - Export format choices and settings
    - Translation settings and language selection
    - Output directory and batch processing options
    """
    
    # Signals
    options_changed = pyqtSignal(object)  # Emitted when options are modified
    
    # Language codes for translation
    SUPPORTED_LANGUAGES = {
        "English": "en",
        "Spanish": "es", 
        "French": "fr",
        "German": "de",
        "Italian": "it",
        "Portuguese": "pt",
        "Russian": "ru",
        "Japanese": "ja",
        "Korean": "ko",
        "Chinese (Simplified)": "zh-cn",
        "Chinese (Traditional)": "zh-tw",
        "Arabic": "ar",
        "Hindi": "hi",
        "Dutch": "nl",
        "Swedish": "sv",
        "Norwegian": "no",
        "Danish": "da",
        "Finnish": "fi",
        "Polish": "pl",
        "Czech": "cs",
        "Hungarian": "hu",
        "Turkish": "tr",
        "Greek": "el",
        "Hebrew": "he",
        "Thai": "th",
        "Vietnamese": "vi",
        "Indonesian": "id",
        "Malay": "ms"
    }
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_options = ProcessingOptions()
        self._setup_ui()
        self._connect_signals()
        self._load_default_options()
        
    def _setup_ui(self):
        """Initialize the user interface components."""
        self.setMinimumWidth(400)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # Create tabbed interface for better organization
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)
        
        # Create tabs
        self._create_model_tab()
        self._create_export_tab()
        # self._create_translation_tab()  # Hidden for now - to be developed later
        self._create_output_tab()
        
        # Action buttons
        self._create_action_buttons(main_layout)
        
    def _create_model_tab(self):
        """Create the model and processing options tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(15)
        
        # Model Selection Group
        model_group = QGroupBox("Model Configuration")
        model_layout = QGridLayout(model_group)
        
        # Model size selection
        model_layout.addWidget(QLabel("Model Size:"), 0, 0)
        self.model_size_combo = QComboBox()
        for size in ModelSize:
            display_name = size.value.title()
            self.model_size_combo.addItem(display_name, size)
        self.model_size_combo.setToolTip(
            "Select model size. Larger models are more accurate but slower.\n"
            "Tiny: Fastest, least accurate\n"
            "Base: Good balance of speed and accuracy\n"
            "Small: Better accuracy, moderate speed\n"
            "Medium: High accuracy, slower\n"
            "Large: Best accuracy, slowest"
        )
        model_layout.addWidget(self.model_size_combo, 0, 1)
        
        # Processing quality settings
        model_layout.addWidget(QLabel("Processing Quality:"), 1, 0)
        self.quality_combo = QComboBox()
        self.quality_combo.addItems(["Fast", "Balanced", "High Quality"])
        self.quality_combo.setCurrentText("Balanced")
        self.quality_combo.setToolTip(
            "Processing quality vs speed trade-off:\n"
            "Fast: Quick processing, lower quality\n"
            "Balanced: Good balance of speed and quality\n"
            "High Quality: Best quality, slower processing"
        )
        model_layout.addWidget(self.quality_combo, 1, 1)
        
        layout.addWidget(model_group)
        
        # Advanced Processing Options
        advanced_group = QGroupBox("Advanced Options")
        advanced_layout = QGridLayout(advanced_group)
        
        # Confidence threshold
        advanced_layout.addWidget(QLabel("Confidence Threshold:"), 0, 0)
        self.confidence_spin = QDoubleSpinBox()
        self.confidence_spin.setRange(0.0, 1.0)
        self.confidence_spin.setSingleStep(0.1)
        self.confidence_spin.setValue(0.5)
        self.confidence_spin.setDecimals(2)
        self.confidence_spin.setToolTip(
            "Minimum confidence score for word alignment (0.0-1.0).\n"
            "Higher values filter out uncertain words but may reduce output."
        )
        advanced_layout.addWidget(self.confidence_spin, 0, 1)
        
        # Enable denoising
        self.denoise_check = QCheckBox("Enable Audio Denoising")
        self.denoise_check.setToolTip(
            "Apply noise reduction to improve speech recognition accuracy.\n"
            "May help with low-quality audio but increases processing time."
        )
        advanced_layout.addWidget(self.denoise_check, 1, 0, 1, 2)
        
        # Enable vocal enhancement
        self.enhance_vocals_check = QCheckBox("Enhance Vocal Separation")
        self.enhance_vocals_check.setToolTip(
            "Use advanced vocal separation techniques for better isolation.\n"
            "Recommended for complex music with multiple instruments."
        )
        advanced_layout.addWidget(self.enhance_vocals_check, 2, 0, 1, 2)
        
        # Save instrumental track
        self.save_instrumental_check = QCheckBox("Save Instrumental Track")
        self.save_instrumental_check.setToolTip(
            "Save the instrumental (music-only) track after vocal separation.\n"
            "This creates an additional output file with vocals removed."
        )
        advanced_layout.addWidget(self.save_instrumental_check, 3, 0, 1, 2)
        
        layout.addWidget(advanced_group)
        layout.addStretch()
        
        self.tab_widget.addTab(tab, "Model & Processing")
        
    def _create_export_tab(self):
        """Create the export formats and options tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(15)
        
        # Export Formats Group
        formats_group = QGroupBox("Export Formats")
        formats_layout = QVBoxLayout(formats_group)
        
        # Format checkboxes
        self.format_checks = {}
        for fmt in ExportFormat:
            checkbox = QCheckBox(f"{fmt.value.upper()} Format")
            checkbox.setToolTip(self._get_format_tooltip(fmt))
            self.format_checks[fmt] = checkbox
            formats_layout.addWidget(checkbox)
        
        # Set SRT as default
        self.format_checks[ExportFormat.SRT].setChecked(True)
        
        layout.addWidget(formats_group)
        
        # SRT Options Group
        srt_group = QGroupBox("SRT Options")
        srt_layout = QGridLayout(srt_group)
        
        # Word-level SRT
        self.word_level_check = QCheckBox("Generate Word-Level SRT")
        self.word_level_check.setChecked(True)
        self.word_level_check.setToolTip(
            "Create SRT files with individual word timing.\n"
            "Useful for karaoke-style applications."
        )
        srt_layout.addWidget(self.word_level_check, 0, 0, 1, 2)
        
        # Maximum line length
        srt_layout.addWidget(QLabel("Max Line Length:"), 1, 0)
        self.max_line_spin = QSpinBox()
        self.max_line_spin.setRange(20, 100)
        self.max_line_spin.setValue(42)
        self.max_line_spin.setToolTip("Maximum characters per subtitle line")
        srt_layout.addWidget(self.max_line_spin, 1, 1)
        
        # Maximum lines per subtitle
        srt_layout.addWidget(QLabel("Max Lines per Subtitle:"), 2, 0)
        self.max_lines_spin = QSpinBox()
        self.max_lines_spin.setRange(1, 4)
        self.max_lines_spin.setValue(2)
        self.max_lines_spin.setToolTip("Maximum number of lines per subtitle")
        srt_layout.addWidget(self.max_lines_spin, 2, 1)
        
        layout.addWidget(srt_group)
        
        # Karaoke Options Group
        karaoke_group = QGroupBox("Karaoke Options")
        karaoke_layout = QGridLayout(karaoke_group)
        
        # Enable karaoke mode
        self.karaoke_check = QCheckBox("Enable Karaoke Mode")
        self.karaoke_check.setToolTip(
            "Generate ASS files with karaoke-style word highlighting effects.\n"
            "Creates smooth word-by-word highlighting animations."
        )
        karaoke_layout.addWidget(self.karaoke_check, 0, 0, 1, 2)
        
        # Karaoke style options
        karaoke_layout.addWidget(QLabel("Highlight Color:"), 1, 0)
        self.highlight_color_combo = QComboBox()
        self.highlight_color_combo.addItems([
            "Yellow", "Red", "Blue", "Green", "Orange", "Purple", "Pink"
        ])
        self.highlight_color_combo.setToolTip("Color for word highlighting")
        karaoke_layout.addWidget(self.highlight_color_combo, 1, 1)
        
        karaoke_layout.addWidget(QLabel("Animation Speed:"), 2, 0)
        self.animation_speed_combo = QComboBox()
        self.animation_speed_combo.addItems(["Slow", "Normal", "Fast"])
        self.animation_speed_combo.setCurrentText("Normal")
        self.animation_speed_combo.setToolTip("Speed of karaoke highlighting animation")
        karaoke_layout.addWidget(self.animation_speed_combo, 2, 1)
        
        layout.addWidget(karaoke_group)
        layout.addStretch()
        
        self.tab_widget.addTab(tab, "Export Formats")
        
    def _create_translation_tab(self):
        """Create the translation settings tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(15)
        
        # Translation Enable Group
        enable_group = QGroupBox("Translation Settings")
        enable_layout = QGridLayout(enable_group)
        
        # Enable translation
        self.translation_check = QCheckBox("Enable Translation")
        self.translation_check.setToolTip(
            "Generate bilingual subtitles with translations.\n"
            "Requires internet connection and API keys."
        )
        enable_layout.addWidget(self.translation_check, 0, 0, 1, 2)
        
        # Translation service
        enable_layout.addWidget(QLabel("Translation Service:"), 1, 0)
        self.translation_service_combo = QComboBox()
        for service in TranslationService:
            self.translation_service_combo.addItem(service.value.title(), service)
        self.translation_service_combo.setToolTip(
            "Choose translation service:\n"
            "DeepL: Higher quality, limited free usage\n"
            "Google: Good quality, more generous free tier"
        )
        enable_layout.addWidget(self.translation_service_combo, 1, 1)
        
        # Target language
        enable_layout.addWidget(QLabel("Target Language:"), 2, 0)
        self.target_language_combo = QComboBox()
        for lang_name, lang_code in self.SUPPORTED_LANGUAGES.items():
            self.target_language_combo.addItem(lang_name, lang_code)
        self.target_language_combo.setToolTip("Select target language for translation")
        enable_layout.addWidget(self.target_language_combo, 2, 1)
        
        layout.addWidget(enable_group)
        
        # API Configuration Group
        api_group = QGroupBox("API Configuration")
        api_layout = QGridLayout(api_group)
        
        # DeepL API Key
        api_layout.addWidget(QLabel("DeepL API Key:"), 0, 0)
        self.deepl_key_edit = QLineEdit()
        self.deepl_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.deepl_key_edit.setPlaceholderText("Enter DeepL API key (optional)")
        self.deepl_key_edit.setToolTip(
            "DeepL API key for translation service.\n"
            "Get your free API key at https://www.deepl.com/pro-api"
        )
        api_layout.addWidget(self.deepl_key_edit, 0, 1)
        
        # Google API Key
        api_layout.addWidget(QLabel("Google API Key:"), 1, 0)
        self.google_key_edit = QLineEdit()
        self.google_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.google_key_edit.setPlaceholderText("Enter Google Translate API key (optional)")
        self.google_key_edit.setToolTip(
            "Google Translate API key for translation service.\n"
            "Get your API key from Google Cloud Console"
        )
        api_layout.addWidget(self.google_key_edit, 1, 1)
        
        # Test connection button
        self.test_connection_btn = QPushButton("Test Connection")
        self.test_connection_btn.setToolTip("Test translation service connection")
        api_layout.addWidget(self.test_connection_btn, 2, 0, 1, 2)
        
        layout.addWidget(api_group)
        
        # Bilingual Options Group
        bilingual_group = QGroupBox("Bilingual Subtitle Options")
        bilingual_layout = QGridLayout(bilingual_group)
        
        # Layout style
        bilingual_layout.addWidget(QLabel("Layout Style:"), 0, 0)
        self.bilingual_layout_combo = QComboBox()
        self.bilingual_layout_combo.addItems([
            "Original on top", "Translation on top", "Side by side"
        ])
        self.bilingual_layout_combo.setToolTip("How to arrange original and translated text")
        bilingual_layout.addWidget(self.bilingual_layout_combo, 0, 1)
        
        # Separator
        bilingual_layout.addWidget(QLabel("Text Separator:"), 1, 0)
        self.separator_edit = QLineEdit()
        self.separator_edit.setText(" | ")
        self.separator_edit.setToolTip("Text separator between original and translation")
        bilingual_layout.addWidget(self.separator_edit, 1, 1)
        
        layout.addWidget(bilingual_group)
        layout.addStretch()
        
        self.tab_widget.addTab(tab, "Translation")
        
    def _create_output_tab(self):
        """Create the output and batch processing options tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(15)
        
        # Output Directory Group
        output_group = QGroupBox("Output Settings")
        output_layout = QGridLayout(output_group)
        
        # Output directory
        output_layout.addWidget(QLabel("Output Directory:"), 0, 0)
        self.output_dir_edit = QLineEdit()
        self.output_dir_edit.setText(str(Path.cwd()))
        self.output_dir_edit.setToolTip("Directory where subtitle files will be saved")
        output_layout.addWidget(self.output_dir_edit, 0, 1)
        
        self.browse_output_btn = QPushButton("Browse...")
        self.browse_output_btn.setToolTip("Select output directory")
        output_layout.addWidget(self.browse_output_btn, 0, 2)
        
        # File naming options
        output_layout.addWidget(QLabel("File Naming:"), 1, 0)
        self.naming_combo = QComboBox()
        self.naming_combo.addItems([
            "Original name + format", "Original name + timestamp", "Custom prefix"
        ])
        self.naming_combo.setToolTip("How to name output files")
        output_layout.addWidget(self.naming_combo, 1, 1, 1, 2)
        
        # Custom prefix (shown when "Custom prefix" is selected)
        self.prefix_label = QLabel("Custom Prefix:")
        self.prefix_edit = QLineEdit()
        self.prefix_edit.setPlaceholderText("Enter custom prefix")
        self.prefix_edit.setToolTip("Custom prefix for output files")
        output_layout.addWidget(self.prefix_label, 2, 0)
        output_layout.addWidget(self.prefix_edit, 2, 1, 1, 2)
        
        # Initially hide custom prefix controls
        self.prefix_label.hide()
        self.prefix_edit.hide()
        
        layout.addWidget(output_group)
        
        # Batch Processing Group
        batch_group = QGroupBox("Batch Processing")
        batch_layout = QGridLayout(batch_group)
        
        # Parallel processing
        batch_layout.addWidget(QLabel("Parallel Processing:"), 0, 0)
        self.parallel_check = QCheckBox("Enable parallel processing")
        self.parallel_check.setToolTip(
            "Process multiple files simultaneously.\n"
            "Faster but uses more system resources."
        )
        batch_layout.addWidget(self.parallel_check, 0, 1)
        
        # Max concurrent files
        batch_layout.addWidget(QLabel("Max Concurrent Files:"), 1, 0)
        self.max_concurrent_spin = QSpinBox()
        self.max_concurrent_spin.setRange(1, 8)
        self.max_concurrent_spin.setValue(2)
        self.max_concurrent_spin.setToolTip("Maximum number of files to process simultaneously")
        batch_layout.addWidget(self.max_concurrent_spin, 1, 1)
        
        # Continue on error
        self.continue_on_error_check = QCheckBox("Continue processing on errors")
        self.continue_on_error_check.setChecked(True)
        self.continue_on_error_check.setToolTip(
            "Continue processing remaining files if one fails.\n"
            "Recommended for batch processing."
        )
        batch_layout.addWidget(self.continue_on_error_check, 2, 0, 1, 2)
        
        # Generate batch report
        self.batch_report_check = QCheckBox("Generate batch processing report")
        self.batch_report_check.setChecked(True)
        self.batch_report_check.setToolTip("Create a detailed report of batch processing results")
        batch_layout.addWidget(self.batch_report_check, 3, 0, 1, 2)
        
        layout.addWidget(batch_group)
        
        # Performance Group
        performance_group = QGroupBox("Performance Settings")
        performance_layout = QGridLayout(performance_group)
        
        # Memory usage
        performance_layout.addWidget(QLabel("Memory Usage:"), 0, 0)
        self.memory_combo = QComboBox()
        self.memory_combo.addItems(["Conservative", "Balanced", "Aggressive"])
        self.memory_combo.setCurrentText("Balanced")
        self.memory_combo.setToolTip(
            "Memory usage strategy:\n"
            "Conservative: Lower memory usage, slower\n"
            "Balanced: Good balance of speed and memory\n"
            "Aggressive: Higher memory usage, faster"
        )
        performance_layout.addWidget(self.memory_combo, 0, 1)
        
        # Temporary files cleanup
        self.cleanup_temp_check = QCheckBox("Clean up temporary files")
        self.cleanup_temp_check.setChecked(True)
        self.cleanup_temp_check.setToolTip("Automatically delete temporary files after processing")
        performance_layout.addWidget(self.cleanup_temp_check, 1, 0, 1, 2)
        
        layout.addWidget(performance_group)
        layout.addStretch()
        
        self.tab_widget.addTab(tab, "Output & Batch")
        
    def _create_action_buttons(self, parent_layout):
        """Create action buttons for the options panel."""
        buttons_layout = QHBoxLayout()
        
        # Reset to defaults
        self.reset_btn = QPushButton("Reset to Defaults")
        self.reset_btn.setToolTip("Reset all options to default values")
        buttons_layout.addWidget(self.reset_btn)
        
        # Save preset (hidden for now)
        self.save_preset_btn = QPushButton("Save Preset...")
        self.save_preset_btn.setToolTip("Save current settings as a preset")
        self.save_preset_btn.hide()  # Hide the button
        buttons_layout.addWidget(self.save_preset_btn)
        
        # Load preset (hidden for now)
        self.load_preset_btn = QPushButton("Load Preset...")
        self.load_preset_btn.setToolTip("Load a saved preset")
        self.load_preset_btn.hide()  # Hide the button
        buttons_layout.addWidget(self.load_preset_btn)
        
        buttons_layout.addStretch()
        
        # Validate options
        self.validate_btn = QPushButton("Validate Settings")
        self.validate_btn.setToolTip("Check if current settings are valid")
        buttons_layout.addWidget(self.validate_btn)
        
        parent_layout.addLayout(buttons_layout)
        
    def _connect_signals(self):
        """Connect UI signals to their handlers."""
        # Model tab signals
        self.model_size_combo.currentIndexChanged.connect(self._on_options_changed)
        self.quality_combo.currentTextChanged.connect(self._on_options_changed)
        self.confidence_spin.valueChanged.connect(self._on_options_changed)
        self.denoise_check.toggled.connect(self._on_options_changed)
        self.enhance_vocals_check.toggled.connect(self._on_options_changed)
        self.save_instrumental_check.toggled.connect(self._on_options_changed)
        
        # Export tab signals
        for checkbox in self.format_checks.values():
            checkbox.toggled.connect(self._on_options_changed)
        self.word_level_check.toggled.connect(self._on_options_changed)
        self.max_line_spin.valueChanged.connect(self._on_options_changed)
        self.max_lines_spin.valueChanged.connect(self._on_options_changed)
        self.karaoke_check.toggled.connect(self._on_options_changed)
        self.highlight_color_combo.currentTextChanged.connect(self._on_options_changed)
        self.animation_speed_combo.currentTextChanged.connect(self._on_options_changed)
        
        # Translation tab signals (commented out - tab is hidden)
        # self.translation_check.toggled.connect(self._on_translation_toggled)
        # self.translation_service_combo.currentIndexChanged.connect(self._on_options_changed)
        # self.target_language_combo.currentIndexChanged.connect(self._on_options_changed)
        # self.deepl_key_edit.textChanged.connect(self._on_options_changed)
        # self.google_key_edit.textChanged.connect(self._on_options_changed)
        # self.test_connection_btn.clicked.connect(self._test_translation_connection)
        # self.bilingual_layout_combo.currentTextChanged.connect(self._on_options_changed)
        # self.separator_edit.textChanged.connect(self._on_options_changed)
        
        # Output tab signals
        self.output_dir_edit.textChanged.connect(self._on_options_changed)
        self.browse_output_btn.clicked.connect(self._browse_output_directory)
        self.naming_combo.currentTextChanged.connect(self._on_naming_changed)
        self.prefix_edit.textChanged.connect(self._on_options_changed)
        self.parallel_check.toggled.connect(self._on_options_changed)
        self.max_concurrent_spin.valueChanged.connect(self._on_options_changed)
        self.continue_on_error_check.toggled.connect(self._on_options_changed)
        self.batch_report_check.toggled.connect(self._on_options_changed)
        self.memory_combo.currentTextChanged.connect(self._on_options_changed)
        self.cleanup_temp_check.toggled.connect(self._on_options_changed)
        
        # Action button signals
        self.reset_btn.clicked.connect(self._reset_to_defaults)
        self.save_preset_btn.clicked.connect(self._save_preset)
        self.load_preset_btn.clicked.connect(self._load_preset)
        self.validate_btn.clicked.connect(self._validate_settings)
        
    def _load_default_options(self):
        """Load default processing options into the UI."""
        # Set default output directory if not set
        if not self._current_options.output_directory:
            self._current_options.output_directory = str(Path.cwd())
        self._update_ui_from_options(self._current_options)
        
    def _on_options_changed(self):
        """Handle changes to any option."""
        try:
            self._current_options = self._get_options_from_ui()
            self.options_changed.emit(self._current_options)
        except Exception:
            # Ignore errors during UI updates (e.g., during initialization)
            pass
        
    def _on_translation_toggled(self, enabled: bool):
        """Handle translation checkbox toggle."""
        # Enable/disable translation-related controls
        self.translation_service_combo.setEnabled(enabled)
        self.target_language_combo.setEnabled(enabled)
        self.deepl_key_edit.setEnabled(enabled)
        self.google_key_edit.setEnabled(enabled)
        self.test_connection_btn.setEnabled(enabled)
        self.bilingual_layout_combo.setEnabled(enabled)
        self.separator_edit.setEnabled(enabled)
        
        self._on_options_changed()
        
    def _on_naming_changed(self, naming_style: str):
        """Handle file naming style change."""
        show_prefix = naming_style == "Custom prefix"
        self.prefix_label.setVisible(show_prefix)
        self.prefix_edit.setVisible(show_prefix)
        self._on_options_changed()
        
    def _browse_output_directory(self):
        """Open directory browser for output directory selection."""
        current_dir = self.output_dir_edit.text() or str(Path.cwd())
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Output Directory",
            current_dir
        )
        
        if directory:
            self.output_dir_edit.setText(directory)
            
    def _test_translation_connection(self):
        """Test connection to the selected translation service."""
        # This would normally test the actual API connection
        # For now, just show a placeholder message
        service = self.translation_service_combo.currentData()
        if service == TranslationService.DEEPL:
            api_key = self.deepl_key_edit.text()
            service_name = "DeepL"
        else:
            api_key = self.google_key_edit.text()
            service_name = "Google Translate"
        
        if not api_key:
            QMessageBox.warning(
                self,
                "Missing API Key",
                f"Please enter your {service_name} API key first."
            )
            return
        
        # Placeholder for actual connection test
        QMessageBox.information(
            self,
            "Connection Test",
            f"Connection test for {service_name} would be performed here.\n"
            f"In a real implementation, this would validate the API key."
        )
        
    def _reset_to_defaults(self):
        """Reset all options to default values."""
        reply = QMessageBox.question(
            self,
            "Reset to Defaults",
            "Are you sure you want to reset all settings to default values?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self._current_options = ProcessingOptions()
            self._update_ui_from_options(self._current_options)
            self._on_options_changed()
            
    def _save_preset(self):
        """Save current settings as a preset."""
        # Placeholder for preset saving functionality
        QMessageBox.information(
            self,
            "Save Preset",
            "Preset saving functionality would be implemented here.\n"
            "This would allow users to save and load custom configurations."
        )
        
    def _load_preset(self):
        """Load a saved preset."""
        # Placeholder for preset loading functionality
        QMessageBox.information(
            self,
            "Load Preset",
            "Preset loading functionality would be implemented here.\n"
            "This would allow users to load previously saved configurations."
        )
        
    def _validate_settings(self):
        """Validate current settings and show results."""
        options = self._get_options_from_ui()
        errors = options.validate()
        
        if not errors:
            QMessageBox.information(
                self,
                "Validation Successful",
                "All settings are valid and ready for processing."
            )
        else:
            error_text = "\n".join(f"• {error}" for error in errors)
            QMessageBox.warning(
                self,
                "Validation Errors",
                f"The following issues were found:\n\n{error_text}"
            )
            
    def _get_options_from_ui(self) -> ProcessingOptions:
        """Extract ProcessingOptions from current UI state."""
        # Get selected export formats
        export_formats = []
        for fmt, checkbox in self.format_checks.items():
            if checkbox.isChecked():
                export_formats.append(fmt)
        
        # Get translation settings (disabled for now)
        translation_enabled = False  # Translation is disabled
        target_language = None
        translation_service = None
        
        # Translation controls are hidden, so we set defaults
        # if translation_enabled:
        #     target_language = self.target_language_combo.currentData()
        #     translation_service = self.translation_service_combo.currentData()
        
        return ProcessingOptions(
            model_size=self.model_size_combo.currentData(),
            export_formats=export_formats,
            word_level_srt=self.word_level_check.isChecked(),
            karaoke_mode=self.karaoke_check.isChecked(),
            translation_enabled=translation_enabled,
            target_language=target_language,
            translation_service=translation_service,
            output_directory=self.output_dir_edit.text(),
            save_instrumental=self.save_instrumental_check.isChecked()
        )
        
    def _update_ui_from_options(self, options: ProcessingOptions):
        """Update UI controls to match the given ProcessingOptions."""
        # Model settings
        model_index = self.model_size_combo.findData(options.model_size)
        if model_index >= 0:
            self.model_size_combo.setCurrentIndex(model_index)
        
        # Export formats
        for fmt, checkbox in self.format_checks.items():
            checkbox.setChecked(fmt in options.export_formats)
        
        # SRT options
        self.word_level_check.setChecked(options.word_level_srt)
        
        # Karaoke options
        self.karaoke_check.setChecked(options.karaoke_mode)
        
        # Translation settings (commented out - controls are hidden)
        # self.translation_check.setChecked(options.translation_enabled)
        # self._on_translation_toggled(options.translation_enabled)
        # 
        # if options.translation_service:
        #     service_index = self.translation_service_combo.findData(options.translation_service)
        #     if service_index >= 0:
        #         self.translation_service_combo.setCurrentIndex(service_index)
        # 
        # if options.target_language:
        #     lang_index = self.target_language_combo.findData(options.target_language)
        #     if lang_index >= 0:
        #         self.target_language_combo.setCurrentIndex(lang_index)
        
        # Output directory
        self.output_dir_edit.setText(options.output_directory)
        
        # Instrumental output option
        self.save_instrumental_check.setChecked(options.save_instrumental)
        
    def _get_model_size_tooltip(self, size: ModelSize) -> str:
        """Get tooltip text for model size."""
        tooltips = {
            ModelSize.TINY: "Fastest processing, lowest accuracy (~39 MB)",
            ModelSize.BASE: "Good balance of speed and accuracy (~74 MB)",
            ModelSize.SMALL: "Better accuracy, moderate speed (~244 MB)",
            ModelSize.MEDIUM: "High accuracy, slower processing (~769 MB)",
            ModelSize.LARGE: "Best accuracy, slowest processing (~1550 MB)"
        }
        return tooltips.get(size, "")
        
    def _get_format_tooltip(self, fmt: ExportFormat) -> str:
        """Get tooltip text for export format."""
        tooltips = {
            ExportFormat.SRT: "SubRip format - widely supported by video players and editors",
            ExportFormat.ASS: "Advanced SubStation Alpha - supports styling and karaoke effects",
            ExportFormat.VTT: "WebVTT format - optimized for web browsers and HTML5 video",
            ExportFormat.JSON: "JSON format - detailed alignment data for developers"
        }
        return tooltips.get(fmt, "")
        
    # Public interface methods
    def get_current_options(self) -> ProcessingOptions:
        """Get the current processing options."""
        return self._get_options_from_ui()
        
    def set_options(self, options: ProcessingOptions):
        """Set the processing options and update UI."""
        self._current_options = options
        self._update_ui_from_options(options)
        
    def validate_current_options(self) -> List[str]:
        """Validate current options and return list of errors."""
        options = self._get_options_from_ui()
        return options.validate()
        
    def is_valid(self) -> bool:
        """Check if current options are valid."""
        return len(self.validate_current_options()) == 0