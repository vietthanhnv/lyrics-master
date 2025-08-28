"""
Integration tests for the AI model management system.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch

from src.services.model_manager import ModelManager
from src.services.model_downloader import ModelDownloader, DownloadResult
from src.services.interfaces import ModelType
from src.models.data_models import ModelSize


class TestModelManagementIntegration:
    """Integration tests for model management components."""
    
    @pytest.fixture
    def temp_models_dir(self):
        """Create a temporary directory for models."""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def model_manager(self, temp_models_dir):
        """Create ModelManager instance with temporary directory."""
        with patch('src.services.model_manager.config_manager') as mock_config:
            mock_config.get_config.return_value.models_directory = str(temp_models_dir)
            manager = ModelManager()
            return manager
    
    def test_complete_model_workflow(self, model_manager, temp_models_dir):
        """Test complete workflow: check availability, download, verify."""
        model_type = ModelType.WHISPERX
        model_size = ModelSize.BASE
        
        # 1. Initially, model should not be available
        assert not model_manager.check_model_availability(model_type, model_size)
        
        # 2. Model should not be in available models list
        available = model_manager.list_available_models()
        assert model_type not in available
        
        # 3. Mock successful download
        with patch('src.services.model_downloader.ModelDownloader.download_model') as mock_download:
            mock_download.return_value = DownloadResult(
                success=True,
                file_path=str(temp_models_dir / "whisperx" / "base.pt")
            )
            
            # Create the actual file to simulate successful download
            whisperx_dir = temp_models_dir / "whisperx"
            whisperx_dir.mkdir(parents=True, exist_ok=True)
            model_file = whisperx_dir / "base.pt"
            model_file.write_text("mock model content")
            
            # Download the model
            result = model_manager.download_model(model_type, model_size)
            assert result is True
        
        # 4. After download, model should be available
        assert model_manager.check_model_availability(model_type, model_size)
        
        # 5. Model should appear in available models list
        available = model_manager.list_available_models()
        assert model_type in available
        assert model_size in available[model_type]
        
        # 6. Should be able to get model path
        model_path = model_manager.get_model_path(model_type, model_size)
        assert model_path == str(model_file)
        assert Path(model_path).exists()
    
    def test_download_with_progress_callback(self, model_manager, temp_models_dir):
        """Test download with progress tracking."""
        progress_updates = []
        
        def progress_callback(percentage, message):
            progress_updates.append((percentage, message))
        
        model_manager.set_download_progress_callback(progress_callback)
        
        # Mock successful download
        with patch('src.services.model_downloader.ModelDownloader') as mock_downloader_class:
            mock_downloader = Mock()
            mock_downloader_class.return_value = mock_downloader
            mock_downloader.download_model.return_value = DownloadResult(success=True)
            
            result = model_manager.download_model(ModelType.WHISPERX, ModelSize.BASE)
            
            assert result is True
            # Verify progress callback was set on downloader
            mock_downloader.set_progress_callback.assert_called_once()
    
    def test_model_metadata_and_paths(self, model_manager):
        """Test model metadata retrieval and path resolution."""
        # Test metadata retrieval
        metadata = model_manager.get_model_metadata(ModelType.WHISPERX, ModelSize.BASE)
        
        assert "filename" in metadata
        assert "checksum" in metadata
        assert "url" in metadata
        assert metadata["filename"] == "base.pt"
        
        # Test models directory
        models_dir = model_manager.get_models_directory()
        assert Path(models_dir).exists()
    
    def test_model_cache_management(self, model_manager, temp_models_dir):
        """Test model cache clearing functionality."""
        # Create some mock model files
        whisperx_dir = temp_models_dir / "whisperx"
        whisperx_dir.mkdir(parents=True, exist_ok=True)
        model_file = whisperx_dir / "base.pt"
        model_file.write_text("mock model content")
        
        # Verify model is available
        assert model_manager.check_model_availability(ModelType.WHISPERX, ModelSize.BASE)
        
        # Clear cache
        result = model_manager.clear_model_cache()
        assert result is True
        
        # Verify model is no longer available
        assert not model_manager.check_model_availability(ModelType.WHISPERX, ModelSize.BASE)
        
        # Verify models directory still exists but is empty
        assert Path(model_manager.get_models_directory()).exists()
        assert not model_file.exists()