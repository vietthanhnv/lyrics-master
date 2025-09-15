"""
Configuration management for the lyric-to-subtitle application.

This module handles application settings, model paths, and user preferences.
"""

import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional
import yaml
from dataclasses import dataclass, asdict


@dataclass
class AppConfig:
    """Application configuration settings."""
    
    # First-run setup
    first_run_completed: bool = False
    setup_version: str = "1.0.0"
    
    # Model settings
    default_model_size: str = "base"
    models_directory: str = ""
    
    # Processing settings
    default_export_formats: list = None
    default_output_directory: str = ""
    enable_word_level_srt: bool = True
    enable_karaoke_mode: bool = False
    
    # Translation settings
    translation_enabled: bool = False
    default_translation_service: str = "deepl"
    deepl_api_key: str = ""
    google_translate_api_key: str = ""
    
    # UI settings
    window_width: int = 800
    window_height: int = 600
    theme: str = "default"
    
    # Performance settings
    max_concurrent_downloads: int = 2
    temp_directory: str = ""
    cleanup_temp_files: bool = True
    
    def __post_init__(self):
        if self.default_export_formats is None:
            self.default_export_formats = ["srt"]
        
        if not self.models_directory:
            self.models_directory = str(get_default_models_directory())
        
        if not self.default_output_directory:
            self.default_output_directory = str(Path.home() / "Documents" / "Subtitles")
        
        if not self.temp_directory:
            self.temp_directory = str(get_default_temp_directory())


def get_app_data_directory() -> Path:
    """Get the application data directory based on the operating system."""
    if os.name == 'nt':  # Windows
        app_data = os.getenv('APPDATA', str(Path.home() / 'AppData' / 'Roaming'))
        return Path(app_data) / 'LyricToSubtitleApp'
    elif os.name == 'posix':  # macOS and Linux
        if sys.platform == 'darwin':  # macOS
            return Path.home() / 'Library' / 'Application Support' / 'LyricToSubtitleApp'
        else:  # Linux
            xdg_config = os.getenv('XDG_CONFIG_HOME', str(Path.home() / '.config'))
            return Path(xdg_config) / 'lyric-to-subtitle-app'
    else:
        # Fallback for other systems
        return Path.home() / '.lyric-to-subtitle-app'


def get_default_models_directory() -> Path:
    """Get the default directory for storing AI models."""
    return get_app_data_directory() / 'models'


def get_default_temp_directory() -> Path:
    """Get the default temporary directory."""
    return get_app_data_directory() / 'temp'


def get_config_file_path() -> Path:
    """Get the path to the configuration file."""
    return get_app_data_directory() / 'config.yaml'


class ConfigManager:
    """Manages application configuration loading and saving."""
    
    def __init__(self):
        self.config_path = get_config_file_path()
        self._config: Optional[AppConfig] = None
    
    def load_config(self) -> AppConfig:
        """Load configuration from file or create default if not exists."""
        if self._config is not None:
            return self._config
        
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config_data = yaml.safe_load(f)
                    self._config = AppConfig(**config_data)
            except Exception as e:
                print(f"Error loading config: {e}. Using default configuration.")
                self._config = AppConfig()
        else:
            self._config = AppConfig()
            self.save_config()
        
        return self._config
    
    def save_config(self) -> bool:
        """Save current configuration to file."""
        if self._config is None:
            return False
        
        try:
            # Ensure config directory exists
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.config_path, 'w', encoding='utf-8') as f:
                yaml.dump(asdict(self._config), f, default_flow_style=False)
            return True
        except Exception as e:
            print(f"Error saving config: {e}")
            return False
    
    def get_config(self) -> AppConfig:
        """Get current configuration."""
        if self._config is None:
            return self.load_config()
        return self._config
    
    def update_config(self, **kwargs) -> bool:
        """Update configuration with new values."""
        if self._config is None:
            self.load_config()
        
        for key, value in kwargs.items():
            if hasattr(self._config, key):
                setattr(self._config, key, value)
        
        return self.save_config()
    
    def reset_to_defaults(self) -> bool:
        """Reset configuration to default values."""
        self._config = AppConfig()
        return self.save_config()
    
    def is_first_run(self) -> bool:
        """Check if this is the first run of the application."""
        config = self.get_config()
        return not config.first_run_completed
    
    def needs_setup(self) -> bool:
        """Check if the application needs setup (first run or missing critical components)."""
        if self.is_first_run():
            return True
        
        # Check if critical directories exist
        config = self.get_config()
        models_dir = Path(config.models_directory)
        if not models_dir.exists():
            return True
        
        return False
    
    def mark_setup_completed(self, version: str = "1.0.0") -> bool:
        """Mark the first-run setup as completed."""
        return self.update_config(
            first_run_completed=True,
            setup_version=version
        )


# Global config manager instance
config_manager = ConfigManager()