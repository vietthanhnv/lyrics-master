#!/usr/bin/env python3
"""
Example demonstrating the OptionsPanel functionality.

This example shows how to use the OptionsPanel to configure processing options
for the lyric-to-subtitle application.
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QTextEdit
from PyQt6.QtCore import Qt

from ui.options_panel import OptionsPanel
from models.data_models import ProcessingOptions, ModelSize, ExportFormat, TranslationService


class OptionsExampleWindow(QMainWindow):
    """Example window demonstrating OptionsPanel usage."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Options Panel Example")
        self.setGeometry(100, 100, 1200, 800)
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Create options panel
        self.options_panel = OptionsPanel()
        layout.addWidget(self.options_panel)
        
        # Create buttons for testing
        button_layout = QVBoxLayout()
        
        self.get_options_btn = QPushButton("Get Current Options")
        self.get_options_btn.clicked.connect(self.show_current_options)
        button_layout.addWidget(self.get_options_btn)
        
        self.set_custom_btn = QPushButton("Set Custom Options")
        self.set_custom_btn.clicked.connect(self.set_custom_options)
        button_layout.addWidget(self.set_custom_btn)
        
        self.validate_btn = QPushButton("Validate Options")
        self.validate_btn.clicked.connect(self.validate_options)
        button_layout.addWidget(self.validate_btn)
        
        layout.addLayout(button_layout)
        
        # Create text area for output
        self.output_text = QTextEdit()
        self.output_text.setMaximumHeight(200)
        layout.addWidget(self.output_text)
        
        # Connect options changed signal
        self.options_panel.options_changed.connect(self.on_options_changed)
        
        self.log("Options Panel Example initialized")
        self.log("Try changing settings in the options panel above")
        
    def log(self, message: str):
        """Add a message to the output text area."""
        self.output_text.append(f"• {message}")
        
    def show_current_options(self):
        """Display current options in the output area."""
        options = self.options_panel.get_current_options()
        
        self.log("=== Current Options ===")
        self.log(f"Model Size: {options.model_size.value}")
        self.log(f"Export Formats: {[fmt.value for fmt in options.export_formats]}")
        self.log(f"Word-level SRT: {options.word_level_srt}")
        self.log(f"Karaoke Mode: {options.karaoke_mode}")
        self.log(f"Translation Enabled: {options.translation_enabled}")
        
        if options.translation_enabled:
            self.log(f"Target Language: {options.target_language}")
            self.log(f"Translation Service: {options.translation_service.value if options.translation_service else 'None'}")
        
        self.log(f"Output Directory: {options.output_directory}")
        self.log("")
        
    def set_custom_options(self):
        """Set custom options to demonstrate programmatic configuration."""
        custom_options = ProcessingOptions(
            model_size=ModelSize.LARGE,
            export_formats=[ExportFormat.ASS, ExportFormat.VTT, ExportFormat.JSON],
            word_level_srt=False,
            karaoke_mode=True,
            translation_enabled=True,
            target_language="es",  # Spanish
            translation_service=TranslationService.DEEPL,
            output_directory=str(Path.home() / "subtitle_output")
        )
        
        self.options_panel.set_options(custom_options)
        self.log("Set custom options:")
        self.log("- Model: Large")
        self.log("- Formats: ASS, VTT, JSON")
        self.log("- Karaoke mode enabled")
        self.log("- Translation to Spanish via DeepL")
        self.log("")
        
    def validate_options(self):
        """Validate current options and show results."""
        errors = self.options_panel.validate_current_options()
        
        if not errors:
            self.log("✓ All options are valid!")
        else:
            self.log("✗ Validation errors found:")
            for error in errors:
                self.log(f"  - {error}")
        self.log("")
        
    def on_options_changed(self, options: ProcessingOptions):
        """Handle options changed signal."""
        self.log(f"Options changed - Model: {options.model_size.value}, "
                f"Formats: {len(options.export_formats)}, "
                f"Translation: {options.translation_enabled}")


def main():
    """Run the options panel example."""
    app = QApplication(sys.argv)
    
    # Set application properties
    app.setApplicationName("Options Panel Example")
    app.setApplicationVersion("1.0.0")
    
    # Create and show window
    window = OptionsExampleWindow()
    window.show()
    
    # Run application
    sys.exit(app.exec())


if __name__ == "__main__":
    main()