"""
First-run setup wizard for initial application configuration and model downloads.

This module provides a guided setup experience for new users, including:
- System requirements checking
- Model download and initialization
- Configuration setup
- User guidance
"""

import os
import sys
import platform
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging

from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QPixmap, QFont, QIcon
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QTextEdit, QCheckBox, QGroupBox, QScrollArea,
    QWidget, QFrame, QSpacerItem, QSizePolicy, QMessageBox,
    QComboBox, QLineEdit, QFileDialog
)

from ..models.data_models import ModelSize
from ..services.interfaces import ModelType
from ..services.model_manager import ModelManager
from ..services.model_downloader import ModelDownloader, DownloadProgress
from ..utils.config import config_manager, AppConfig


logger = logging.getLogger(__name__)


class ModelDownloadWorker(QThread):
    """Worker thread for downloading models in the background."""
    
    progress_updated = pyqtSignal(str, float, str)  # model_key, percentage, status
    download_completed = pyqtSignal(str, bool, str)  # model_key, success, message
    all_downloads_completed = pyqtSignal(bool)  # success
    
    def __init__(self, models_to_download: List[Tuple[ModelType, ModelSize]]):
        super().__init__()
        self.models_to_download = models_to_download
        self.downloader = ModelDownloader()
        self.should_stop = False
        
    def run(self):
        """Download all required models."""
        try:
            total_success = True
            
            for model_type, model_size in self.models_to_download:
                if self.should_stop:
                    break
                
                model_key = f"{model_type.value}_{model_size.value}"
                
                # Set up progress callback
                def progress_callback(progress: DownloadProgress):
                    if not self.should_stop:
                        status = f"Downloading {model_type.value} ({model_size.value})"
                        if progress.speed_mbps > 0:
                            status += f" - {progress.speed_mbps:.1f} MB/s"
                        if progress.eta_seconds:
                            eta_min = int(progress.eta_seconds / 60)
                            eta_sec = int(progress.eta_seconds % 60)
                            status += f" - ETA: {eta_min:02d}:{eta_sec:02d}"
                        
                        self.progress_updated.emit(model_key, progress.percentage, status)
                
                self.downloader.set_progress_callback(progress_callback)
                
                # Download the model
                self.progress_updated.emit(model_key, 0.0, f"Starting download of {model_type.value} ({model_size.value})")
                result = self.downloader.download_model(model_type, model_size)
                
                if result.success:
                    self.download_completed.emit(model_key, True, "Download completed successfully")
                    self.progress_updated.emit(model_key, 100.0, "Download completed")
                else:
                    self.download_completed.emit(model_key, False, result.error_message or "Download failed")
                    total_success = False
                    
                    # Don't continue if a critical model fails
                    if model_type == ModelType.DEMUCS or model_size == ModelSize.BASE:
                        break
            
            self.all_downloads_completed.emit(total_success and not self.should_stop)
            
        except Exception as e:
            logger.error(f"Error in model download worker: {e}")
            self.all_downloads_completed.emit(False)
    
    def stop(self):
        """Stop the download process."""
        self.should_stop = True
        self.downloader.cancel_download()


class SystemRequirementsChecker:
    """Checks system requirements for the application."""
    
    @staticmethod
    def check_python_version() -> Tuple[bool, str]:
        """Check if Python version is compatible."""
        version = sys.version_info
        if version.major >= 3 and version.minor >= 9:
            return True, f"Python {version.major}.{version.minor}.{version.micro}"
        else:
            return False, f"Python {version.major}.{version.minor}.{version.micro} (requires 3.9+)"
    
    @staticmethod
    def check_disk_space() -> Tuple[bool, str]:
        """Check available disk space for models."""
        try:
            models_dir = config_manager.get_config().models_directory
            Path(models_dir).mkdir(parents=True, exist_ok=True)
            
            free_space = shutil.disk_usage(models_dir).free
            required_space = 2 * 1024 * 1024 * 1024  # 2GB minimum
            
            free_gb = free_space / (1024 * 1024 * 1024)
            required_gb = required_space / (1024 * 1024 * 1024)
            
            if free_space >= required_space:
                return True, f"{free_gb:.1f} GB available"
            else:
                return False, f"{free_gb:.1f} GB available (requires {required_gb:.1f} GB)"
        except Exception as e:
            return False, f"Could not check disk space: {e}"
    
    @staticmethod
    def check_memory() -> Tuple[bool, str]:
        """Check available system memory."""
        try:
            import psutil
            memory = psutil.virtual_memory()
            total_gb = memory.total / (1024 * 1024 * 1024)
            available_gb = memory.available / (1024 * 1024 * 1024)
            
            if total_gb >= 4.0:  # 4GB minimum recommended
                return True, f"{total_gb:.1f} GB total, {available_gb:.1f} GB available"
            else:
                return False, f"{total_gb:.1f} GB total (4GB+ recommended)"
        except ImportError:
            return True, "Memory check unavailable (psutil not installed)"
        except Exception as e:
            return False, f"Could not check memory: {e}"
    
    @staticmethod
    def check_ffmpeg() -> Tuple[bool, str]:
        """Check if FFmpeg is available."""
        try:
            import subprocess
            result = subprocess.run(['ffmpeg', '-version'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                # Extract version from output
                lines = result.stdout.split('\n')
                version_line = next((line for line in lines if 'ffmpeg version' in line), '')
                if version_line:
                    version = version_line.split()[2] if len(version_line.split()) > 2 else 'unknown'
                    return True, f"FFmpeg {version}"
                return True, "FFmpeg available"
            else:
                return False, "FFmpeg not found in PATH"
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
            return False, "FFmpeg not responding"
        except FileNotFoundError:
            return False, "FFmpeg not installed"
        except Exception as e:
            return False, f"FFmpeg check failed: {e}"
    
    @staticmethod
    def check_gpu_support() -> Tuple[bool, str]:
        """Check for GPU support (CUDA/Metal)."""
        try:
            import torch
            
            if torch.cuda.is_available():
                gpu_name = torch.cuda.get_device_name(0)
                return True, f"CUDA GPU: {gpu_name}"
            elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
                return True, "Apple Metal Performance Shaders (MPS)"
            else:
                return False, "No GPU acceleration available (CPU only)"
        except ImportError:
            return False, "PyTorch not available"
        except Exception as e:
            return False, f"GPU check failed: {e}"
    
    @classmethod
    def check_all_requirements(cls) -> Dict[str, Tuple[bool, str]]:
        """Check all system requirements."""
        return {
            "Python Version": cls.check_python_version(),
            "Disk Space": cls.check_disk_space(),
            "Memory": cls.check_memory(),
            "FFmpeg": cls.check_ffmpeg(),
            "GPU Support": cls.check_gpu_support()
        }


class FirstRunWizard(QDialog):
    """
    First-run setup wizard for the application.
    
    Guides users through:
    1. Welcome and system requirements check
    2. Model selection and download
    3. Configuration setup
    4. Completion and next steps
    """
    
    setup_completed = pyqtSignal(bool)  # success
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.model_manager = ModelManager()
        self.download_worker: Optional[ModelDownloadWorker] = None
        self.required_models: Dict[str, Tuple[ModelType, ModelSize]] = {}
        
        self._setup_ui()
        self._check_system_requirements()
        
    def _setup_ui(self):
        """Initialize the wizard UI."""
        self.setWindowTitle("Lyric-to-Subtitle App - First Run Setup")
        self.setModal(True)
        self.setFixedSize(800, 600)
        
        # Main layout
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        
        # Header
        header = self._create_header()
        layout.addWidget(header)
        
        # Content area with scroll
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameStyle(QFrame.Shape.NoFrame)
        
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        scroll_area.setWidget(self.content_widget)
        
        layout.addWidget(scroll_area)
        
        # Navigation buttons
        nav_layout = QHBoxLayout()
        nav_layout.addStretch()
        
        self.back_btn = QPushButton("Back")
        self.back_btn.setEnabled(False)
        self.next_btn = QPushButton("Next")
        self.cancel_btn = QPushButton("Cancel")
        
        nav_layout.addWidget(self.back_btn)
        nav_layout.addWidget(self.next_btn)
        nav_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(nav_layout)
        
        # Connect navigation
        self.back_btn.clicked.connect(self._go_back)
        self.next_btn.clicked.connect(self._go_next)
        self.cancel_btn.clicked.connect(self.reject)
        
        # Start with welcome page
        self.current_page = 0
        self._show_welcome_page()
    
    def _create_header(self) -> QWidget:
        """Create the wizard header."""
        header = QWidget()
        header.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #4a90e2, stop:1 #357abd);
                border-radius: 8px;
            }
            QLabel {
                color: white;
                background: transparent;
            }
        """)
        header.setFixedHeight(80)
        
        layout = QHBoxLayout(header)
        layout.setContentsMargins(20, 10, 20, 10)
        
        # Title
        title = QLabel("Welcome to Lyric-to-Subtitle App")
        title.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        layout.addWidget(title)
        
        layout.addStretch()
        
        # Step indicator
        self.step_label = QLabel("Step 1 of 4")
        self.step_label.setFont(QFont("Arial", 12))
        layout.addWidget(self.step_label)
        
        return header
    
    def _clear_content(self):
        """Clear the current content."""
        while self.content_layout.count():
            child = self.content_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
    
    def _show_welcome_page(self):
        """Show the welcome page with system requirements."""
        self._clear_content()
        self.step_label.setText("Step 1 of 4: System Check")
        self.next_btn.setText("Next")
        
        # Welcome message
        welcome = QLabel("""
        <h2>Welcome to Lyric-to-Subtitle App!</h2>
        <p>This wizard will help you set up the application for first use.</p>
        <p>We'll check your system requirements and download the necessary AI models.</p>
        """)
        welcome.setWordWrap(True)
        self.content_layout.addWidget(welcome)
        
        # System requirements section
        req_group = QGroupBox("System Requirements Check")
        req_layout = QVBoxLayout(req_group)
        
        self.requirements_labels = {}
        requirements = SystemRequirementsChecker.check_all_requirements()
        
        for req_name, (passed, details) in requirements.items():
            req_widget = QWidget()
            req_widget_layout = QHBoxLayout(req_widget)
            req_widget_layout.setContentsMargins(0, 5, 0, 5)
            
            # Status icon
            status_label = QLabel("✅" if passed else "❌")
            status_label.setFixedWidth(30)
            req_widget_layout.addWidget(status_label)
            
            # Requirement name
            name_label = QLabel(req_name)
            name_label.setFixedWidth(120)
            req_widget_layout.addWidget(name_label)
            
            # Details
            details_label = QLabel(details)
            details_label.setStyleSheet("color: green;" if passed else "color: red;")
            req_widget_layout.addWidget(details_label)
            
            req_widget_layout.addStretch()
            req_layout.addWidget(req_widget)
            
            self.requirements_labels[req_name] = (status_label, details_label, passed)
        
        self.content_layout.addWidget(req_group)
        
        # Check if we can proceed
        all_critical_passed = all(
            passed for req_name, (_, _, passed) in self.requirements_labels.items()
            if req_name in ["Python Version", "Disk Space"]
        )
        
        if not all_critical_passed:
            warning = QLabel("""
            <p style="color: red;"><b>⚠️ Critical requirements not met!</b></p>
            <p>Please resolve the issues above before continuing.</p>
            """)
            warning.setWordWrap(True)
            self.content_layout.addWidget(warning)
            self.next_btn.setEnabled(False)
        else:
            self.next_btn.setEnabled(True)
        
        self.content_layout.addStretch()
    
    def _show_model_selection_page(self):
        """Show the model selection page."""
        self._clear_content()
        self.step_label.setText("Step 2 of 4: Model Selection")
        
        # Model selection explanation
        explanation = QLabel("""
        <h3>AI Model Selection</h3>
        <p>The application uses AI models for vocal separation and speech recognition.</p>
        <p>Choose the model size based on your needs:</p>
        <ul>
        <li><b>Base:</b> Good balance of speed and accuracy (recommended)</li>
        <li><b>Small:</b> Faster processing, lower accuracy</li>
        <li><b>Large:</b> Slower processing, higher accuracy</li>
        </ul>
        """)
        explanation.setWordWrap(True)
        self.content_layout.addWidget(explanation)
        
        # Model selection
        model_group = QGroupBox("Select Models to Download")
        model_layout = QVBoxLayout(model_group)
        
        # WhisperX model selection
        whisper_widget = QWidget()
        whisper_layout = QHBoxLayout(whisper_widget)
        whisper_layout.addWidget(QLabel("WhisperX Model Size:"))
        
        self.whisper_combo = QComboBox()
        self.whisper_combo.addItems(["base", "small", "large"])
        self.whisper_combo.setCurrentText("base")
        whisper_layout.addWidget(self.whisper_combo)
        whisper_layout.addStretch()
        
        model_layout.addWidget(whisper_widget)
        
        # Demucs model (fixed to base)
        demucs_widget = QWidget()
        demucs_layout = QHBoxLayout(demucs_widget)
        demucs_layout.addWidget(QLabel("Demucs Model:"))
        demucs_layout.addWidget(QLabel("Base (htdemucs)"))
        demucs_layout.addStretch()
        
        model_layout.addWidget(demucs_widget)
        
        # Storage requirements
        storage_info = QLabel("""
        <p><b>Storage Requirements:</b></p>
        <ul>
        <li>Demucs (Base): ~320 MB</li>
        <li>WhisperX (Base): ~74 MB</li>
        <li>WhisperX (Small): ~244 MB</li>
        <li>WhisperX (Large): ~1.5 GB</li>
        </ul>
        """)
        storage_info.setWordWrap(True)
        model_layout.addWidget(storage_info)
        
        self.content_layout.addWidget(model_group)
        
        # Configuration options
        config_group = QGroupBox("Configuration")
        config_layout = QVBoxLayout(config_group)
        
        # Output directory selection
        output_widget = QWidget()
        output_layout = QHBoxLayout(output_widget)
        output_layout.addWidget(QLabel("Default Output Directory:"))
        
        self.output_dir_edit = QLineEdit()
        self.output_dir_edit.setText(config_manager.get_config().default_output_directory)
        output_layout.addWidget(self.output_dir_edit)
        
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse_output_directory)
        output_layout.addWidget(browse_btn)
        
        config_layout.addWidget(output_widget)
        
        self.content_layout.addWidget(config_group)
        self.content_layout.addStretch()
    
    def _show_download_page(self):
        """Show the model download page."""
        self._clear_content()
        self.step_label.setText("Step 3 of 4: Downloading Models")
        self.next_btn.setText("Skip Downloads")
        self.next_btn.setEnabled(False)  # Disable until downloads complete
        
        # Download explanation
        explanation = QLabel("""
        <h3>Downloading AI Models</h3>
        <p>Please wait while we download the required AI models. This may take several minutes depending on your internet connection.</p>
        """)
        explanation.setWordWrap(True)
        self.content_layout.addWidget(explanation)
        
        # Progress section
        progress_group = QGroupBox("Download Progress")
        progress_layout = QVBoxLayout(progress_group)
        
        # Overall progress
        self.overall_progress = QProgressBar()
        self.overall_progress.setTextVisible(True)
        self.overall_progress.setFormat("Overall Progress: %p%")
        progress_layout.addWidget(self.overall_progress)
        
        # Individual model progress
        self.model_progress_widgets = {}
        
        # Prepare models to download
        whisper_size = ModelSize(self.whisper_combo.currentText())
        self.required_models = {
            "demucs_base": (ModelType.DEMUCS, ModelSize.BASE),
            f"whisperx_{whisper_size.value}": (ModelType.WHISPERX, whisper_size)
        }
        
        for model_key, (model_type, model_size) in self.required_models.items():
            model_widget = QWidget()
            model_layout = QVBoxLayout(model_widget)
            
            # Model name
            model_name = QLabel(f"{model_type.value} ({model_size.value})")
            model_name.setFont(QFont("Arial", 10, QFont.Weight.Bold))
            model_layout.addWidget(model_name)
            
            # Progress bar
            progress_bar = QProgressBar()
            progress_bar.setTextVisible(True)
            progress_bar.setFormat("Waiting...")
            model_layout.addWidget(progress_bar)
            
            # Status label
            status_label = QLabel("Preparing download...")
            status_label.setStyleSheet("color: gray;")
            model_layout.addWidget(status_label)
            
            progress_layout.addWidget(model_widget)
            
            self.model_progress_widgets[model_key] = {
                'progress_bar': progress_bar,
                'status_label': status_label
            }
        
        self.content_layout.addWidget(progress_group)
        
        # Download log
        log_group = QGroupBox("Download Log")
        log_layout = QVBoxLayout(log_group)
        
        self.download_log = QTextEdit()
        self.download_log.setMaximumHeight(150)
        self.download_log.setReadOnly(True)
        log_layout.addWidget(self.download_log)
        
        self.content_layout.addWidget(log_group)
        
        # Start downloads
        QTimer.singleShot(500, self._start_downloads)
    
    def _show_completion_page(self):
        """Show the setup completion page."""
        self._clear_content()
        self.step_label.setText("Step 4 of 4: Setup Complete")
        self.next_btn.setText("Finish")
        self.back_btn.setEnabled(False)
        
        # Success message
        success = QLabel("""
        <h2>🎉 Setup Complete!</h2>
        <p>The Lyric-to-Subtitle App has been successfully configured.</p>
        """)
        success.setWordWrap(True)
        self.content_layout.addWidget(success)
        
        # Summary
        summary_group = QGroupBox("Setup Summary")
        summary_layout = QVBoxLayout(summary_group)
        
        # Check what was actually downloaded
        available_models = self.model_manager.list_available_models()
        
        summary_text = "<ul>"
        for model_type, sizes in available_models.items():
            for size in sizes:
                summary_text += f"<li>✅ {model_type.value} ({size.value}) - Ready</li>"
        summary_text += "</ul>"
        
        if not available_models:
            summary_text = "<p style='color: orange;'>⚠️ No models were downloaded. You can download them later from the settings.</p>"
        
        summary_label = QLabel(summary_text)
        summary_label.setWordWrap(True)
        summary_layout.addWidget(summary_label)
        
        self.content_layout.addWidget(summary_group)
        
        # Next steps
        next_steps = QLabel("""
        <h3>Next Steps:</h3>
        <ol>
        <li>Select audio files to process</li>
        <li>Choose your preferred export formats</li>
        <li>Start generating subtitles!</li>
        </ol>
        <p><b>Tip:</b> You can access settings and download additional models from the main application menu.</p>
        """)
        next_steps.setWordWrap(True)
        self.content_layout.addWidget(next_steps)
        
        self.content_layout.addStretch()
    
    def _start_downloads(self):
        """Start downloading the selected models."""
        models_to_download = list(self.required_models.values())
        
        # Check which models are already available
        models_needed = []
        for model_type, model_size in models_to_download:
            if not self.model_manager.check_model_availability(model_type, model_size):
                models_needed.append((model_type, model_size))
        
        if not models_needed:
            self._log_download("All required models are already available!")
            self.overall_progress.setValue(100)
            self.next_btn.setEnabled(True)
            self.next_btn.setText("Next")
            return
        
        # Start download worker
        self.download_worker = ModelDownloadWorker(models_needed)
        self.download_worker.progress_updated.connect(self._on_download_progress)
        self.download_worker.download_completed.connect(self._on_download_completed)
        self.download_worker.all_downloads_completed.connect(self._on_all_downloads_completed)
        self.download_worker.start()
        
        self._log_download(f"Starting download of {len(models_needed)} models...")
    
    def _on_download_progress(self, model_key: str, percentage: float, status: str):
        """Handle download progress updates."""
        if model_key in self.model_progress_widgets:
            widgets = self.model_progress_widgets[model_key]
            widgets['progress_bar'].setValue(int(percentage))
            widgets['progress_bar'].setFormat(f"{percentage:.1f}%")
            widgets['status_label'].setText(status)
            widgets['status_label'].setStyleSheet("color: blue;")
        
        # Update overall progress
        total_progress = sum(
            widgets['progress_bar'].value() 
            for widgets in self.model_progress_widgets.values()
        ) / len(self.model_progress_widgets)
        
        self.overall_progress.setValue(int(total_progress))
    
    def _on_download_completed(self, model_key: str, success: bool, message: str):
        """Handle individual download completion."""
        if model_key in self.model_progress_widgets:
            widgets = self.model_progress_widgets[model_key]
            if success:
                widgets['status_label'].setText("✅ Download completed")
                widgets['status_label'].setStyleSheet("color: green;")
                widgets['progress_bar'].setValue(100)
            else:
                widgets['status_label'].setText(f"❌ {message}")
                widgets['status_label'].setStyleSheet("color: red;")
        
        self._log_download(f"{model_key}: {message}")
    
    def _on_all_downloads_completed(self, success: bool):
        """Handle completion of all downloads."""
        if success:
            self._log_download("✅ All downloads completed successfully!")
            self.overall_progress.setValue(100)
        else:
            self._log_download("⚠️ Some downloads failed. You can retry later from settings.")
        
        self.next_btn.setEnabled(True)
        self.next_btn.setText("Next")
        
        # Update model manager cache
        self.model_manager.invalidate_availability_cache()
    
    def _log_download(self, message: str):
        """Add a message to the download log."""
        self.download_log.append(f"[{QTimer().remainingTime()}] {message}")
        self.download_log.verticalScrollBar().setValue(
            self.download_log.verticalScrollBar().maximum()
        )
    
    def _browse_output_directory(self):
        """Browse for output directory."""
        directory = QFileDialog.getExistingDirectory(
            self, "Select Default Output Directory",
            self.output_dir_edit.text()
        )
        if directory:
            self.output_dir_edit.setText(directory)
    
    def _check_system_requirements(self):
        """Check system requirements and update UI."""
        # This is called during initialization
        pass
    
    def _go_back(self):
        """Go to the previous page."""
        if self.current_page > 0:
            self.current_page -= 1
            self._show_current_page()
    
    def _go_next(self):
        """Go to the next page."""
        if self.current_page < 3:
            # Save configuration before proceeding
            if self.current_page == 1:  # Model selection page
                self._save_configuration()
            
            self.current_page += 1
            self._show_current_page()
        else:
            # Finish setup
            self._finish_setup()
    
    def _show_current_page(self):
        """Show the current page based on page number."""
        self.back_btn.setEnabled(self.current_page > 0)
        
        if self.current_page == 0:
            self._show_welcome_page()
        elif self.current_page == 1:
            self._show_model_selection_page()
        elif self.current_page == 2:
            self._show_download_page()
        elif self.current_page == 3:
            self._show_completion_page()
    
    def _save_configuration(self):
        """Save the user's configuration choices."""
        config = config_manager.get_config()
        
        # Update configuration
        config.default_model_size = self.whisper_combo.currentText()
        config.default_output_directory = self.output_dir_edit.text()
        
        # Save configuration
        config_manager.save_config()
    
    def _finish_setup(self):
        """Finish the setup process."""
        # Mark first run as completed
        config = config_manager.get_config()
        config_manager.update_config(first_run_completed=True)
        
        self.setup_completed.emit(True)
        self.accept()
    
    def closeEvent(self, event):
        """Handle dialog close event."""
        if self.download_worker and self.download_worker.isRunning():
            reply = QMessageBox.question(
                self, "Cancel Setup",
                "Downloads are in progress. Are you sure you want to cancel setup?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.download_worker.stop()
                self.download_worker.wait(3000)  # Wait up to 3 seconds
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()