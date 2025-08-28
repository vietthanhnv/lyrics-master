"""
Tests for the first-run setup wizard.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtTest import QTest

from src.ui.first_run_wizard import FirstRunWizard, SystemRequirementsChecker, ModelDownloadWorker
from src.models.data_models import ModelSize
from src.services.interfaces import ModelType


@pytest.fixture
def app():
    """Create QApplication for testing."""
    return QApplication.instance() or QApplication([])


@pytest.fixture
def temp_config_dir():
    """Create temporary directory for configuration."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


class TestSystemRequirementsChecker:
    """Test system requirements checking functionality."""
    
    def test_check_python_version(self):
        """Test Python version checking."""
        passed, message = SystemRequirementsChecker.check_python_version()
        assert isinstance(passed, bool)
        assert isinstance(message, str)
        assert "Python" in message
    
    def test_check_disk_space(self, temp_config_dir):
        """Test disk space checking."""
        with patch('src.utils.config.config_manager.get_config') as mock_config:
            mock_config.return_value.models_directory = temp_config_dir
            
            passed, message = SystemRequirementsChecker.check_disk_space()
            assert isinstance(passed, bool)
            assert isinstance(message, str)
            assert "GB" in message
    
    def test_check_memory(self):
        """Test memory checking."""
        passed, message = SystemRequirementsChecker.check_memory()
        assert isinstance(passed, bool)
        assert isinstance(message, str)
    
    def test_check_ffmpeg(self):
        """Test FFmpeg availability checking."""
        passed, message = SystemRequirementsChecker.check_ffmpeg()
        assert isinstance(passed, bool)
        assert isinstance(message, str)
        assert "FFmpeg" in message or "ffmpeg" in message.lower()
    
    def test_check_gpu_support(self):
        """Test GPU support checking."""
        passed, message = SystemRequirementsChecker.check_gpu_support()
        assert isinstance(passed, bool)
        assert isinstance(message, str)
    
    def test_check_all_requirements(self):
        """Test checking all requirements."""
        requirements = SystemRequirementsChecker.check_all_requirements()
        
        assert isinstance(requirements, dict)
        expected_keys = ["Python Version", "Disk Space", "Memory", "FFmpeg", "GPU Support"]
        
        for key in expected_keys:
            assert key in requirements
            passed, message = requirements[key]
            assert isinstance(passed, bool)
            assert isinstance(message, str)


class TestModelDownloadWorker:
    """Test model download worker functionality."""
    
    def test_worker_initialization(self):
        """Test worker initialization."""
        models = [(ModelType.DEMUCS, ModelSize.BASE)]
        worker = ModelDownloadWorker(models)
        
        assert worker.models_to_download == models
        assert hasattr(worker, 'downloader')
        assert worker.should_stop is False
    
    def test_worker_stop(self):
        """Test worker stop functionality."""
        models = [(ModelType.DEMUCS, ModelSize.BASE)]
        worker = ModelDownloadWorker(models)
        
        worker.stop()
        assert worker.should_stop is True


class TestFirstRunWizard:
    """Test first-run wizard functionality."""
    
    def test_wizard_initialization(self, app):
        """Test wizard initialization."""
        with patch('src.ui.first_run_wizard.ModelManager'):
            wizard = FirstRunWizard()
            
            assert wizard.windowTitle() == "Lyric-to-Subtitle App - First Run Setup"
            assert wizard.isModal()
            assert wizard.current_page == 0
            assert hasattr(wizard, 'model_manager')
            assert hasattr(wizard, 'required_models')
    
    def test_wizard_navigation(self, app):
        """Test wizard page navigation."""
        with patch('src.ui.first_run_wizard.ModelManager'), \
             patch('src.ui.first_run_wizard.SystemRequirementsChecker.check_all_requirements') as mock_check:
            
            # Mock successful requirements check
            mock_check.return_value = {
                "Python Version": (True, "Python 3.9.0"),
                "Disk Space": (True, "10.0 GB available"),
                "Memory": (True, "8.0 GB total"),
                "FFmpeg": (True, "FFmpeg available"),
                "GPU Support": (False, "No GPU acceleration")
            }
            
            wizard = FirstRunWizard()
            
            # Test initial state
            assert wizard.current_page == 0
            assert wizard.back_btn.isEnabled() is False
            assert wizard.next_btn.isEnabled() is True
            
            # Test navigation to next page
            wizard._go_next()
            assert wizard.current_page == 1
            assert wizard.back_btn.isEnabled() is True
    
    def test_wizard_system_requirements_fail(self, app):
        """Test wizard behavior when system requirements fail."""
        with patch('src.ui.first_run_wizard.ModelManager'), \
             patch('src.ui.first_run_wizard.SystemRequirementsChecker.check_all_requirements') as mock_check:
            
            # Mock failed requirements check
            mock_check.return_value = {
                "Python Version": (False, "Python 2.7.0 (requires 3.9+)"),
                "Disk Space": (False, "0.5 GB available (requires 2.0 GB)"),
                "Memory": (True, "8.0 GB total"),
                "FFmpeg": (False, "FFmpeg not found"),
                "GPU Support": (False, "No GPU acceleration")
            }
            
            wizard = FirstRunWizard()
            
            # Should disable next button due to failed critical requirements
            assert wizard.next_btn.isEnabled() is False
    
    def test_wizard_model_selection(self, app):
        """Test model selection page."""
        with patch('src.ui.first_run_wizard.ModelManager'), \
             patch('src.ui.first_run_wizard.SystemRequirementsChecker.check_all_requirements') as mock_check:
            
            mock_check.return_value = {
                "Python Version": (True, "Python 3.9.0"),
                "Disk Space": (True, "10.0 GB available"),
                "Memory": (True, "8.0 GB total"),
                "FFmpeg": (True, "FFmpeg available"),
                "GPU Support": (False, "No GPU acceleration")
            }
            
            wizard = FirstRunWizard()
            wizard.current_page = 1
            wizard._show_model_selection_page()
            
            # Check that model selection widgets exist
            assert hasattr(wizard, 'whisper_combo')
            assert hasattr(wizard, 'output_dir_edit')
            
            # Check default selections
            assert wizard.whisper_combo.currentText() == "base"
    
    def test_configuration_saving(self, app, temp_config_dir):
        """Test configuration saving."""
        with patch('src.ui.first_run_wizard.ModelManager'), \
             patch('src.utils.config.config_manager') as mock_config_manager:
            
            mock_config = Mock()
            mock_config.default_model_size = "base"
            mock_config.default_output_directory = "/test/output"
            mock_config_manager.get_config.return_value = mock_config
            
            wizard = FirstRunWizard()
            wizard.current_page = 1
            wizard._show_model_selection_page()
            
            # Change selections
            wizard.whisper_combo.setCurrentText("small")
            wizard.output_dir_edit.setText("/new/output")
            
            # Save configuration
            wizard._save_configuration()
            
            # Verify configuration was updated
            assert mock_config.default_model_size == "small"
            assert mock_config.default_output_directory == "/new/output"
            mock_config_manager.save_config.assert_called_once()
    
    @patch('src.ui.first_run_wizard.ModelDownloadWorker')
    def test_download_initiation(self, mock_worker_class, app):
        """Test model download initiation."""
        with patch('src.ui.first_run_wizard.ModelManager') as mock_manager_class:
            
            # Mock model manager
            mock_manager = Mock()
            mock_manager.check_model_availability.return_value = False
            mock_manager_class.return_value = mock_manager
            
            # Mock worker
            mock_worker = Mock()
            mock_worker_class.return_value = mock_worker
            
            wizard = FirstRunWizard()
            wizard.current_page = 2
            wizard.required_models = {
                "demucs_base": (ModelType.DEMUCS, ModelSize.BASE)
            }
            wizard._show_download_page()
            
            # Verify worker was created and started
            mock_worker_class.assert_called_once()
            mock_worker.start.assert_called_once()
    
    def test_wizard_completion(self, app):
        """Test wizard completion."""
        with patch('src.ui.first_run_wizard.ModelManager'), \
             patch('src.utils.config.config_manager') as mock_config_manager:
            
            wizard = FirstRunWizard()
            
            # Mock setup completion signal
            setup_completed_signal = Mock()
            wizard.setup_completed.connect(setup_completed_signal)
            
            # Complete setup
            wizard._finish_setup()
            
            # Verify configuration was updated
            mock_config_manager.update_config.assert_called_with(first_run_completed=True)
    
    def test_wizard_cancellation_during_download(self, app):
        """Test wizard cancellation during downloads."""
        with patch('src.ui.first_run_wizard.ModelManager'):
            
            wizard = FirstRunWizard()
            
            # Mock active download worker
            mock_worker = Mock()
            mock_worker.isRunning.return_value = True
            wizard.download_worker = mock_worker
            
            # Mock message box to simulate user choosing to cancel
            with patch('PyQt6.QtWidgets.QMessageBox.question') as mock_question:
                from PyQt6.QtWidgets import QMessageBox
                mock_question.return_value = QMessageBox.StandardButton.Yes
                
                # Create close event
                from PyQt6.QtGui import QCloseEvent
                close_event = QCloseEvent()
                
                wizard.closeEvent(close_event)
                
                # Verify worker was stopped
                mock_worker.stop.assert_called_once()
                mock_worker.wait.assert_called_once_with(3000)
                assert close_event.isAccepted()


if __name__ == "__main__":
    pytest.main([__file__])