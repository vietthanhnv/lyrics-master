"""
Tests for the ModelManager service.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch

from src.services.model_manager import ModelManager
from src.services.interfaces import ModelType
from src.models.data_models import ModelSize


class TestModelManager:
    """Test cases for ModelManager class."""
    
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
    
    def test_init_creates_models_directory(self, model_manager, temp_models_dir):
        """Test that ModelManager creates models directory on initialization."""
        assert temp_models_dir.exists()
        assert model_manager.models_dir == temp_models_dir
    
    def test_check_model_availability_missing_model(self, model_manager):
        """Test checking availability of non-existent model."""
        result = model_manager.check_model_availability(ModelType.WHISPERX, ModelSize.BASE)
        assert result is False
    
    def test_check_model_availability_existing_model(self, model_manager, temp_models_dir):
        """Test checking availability of existing model."""
        # Create a mock model file
        whisperx_dir = temp_models_dir / "whisperx"
        whisperx_dir.mkdir(parents=True, exist_ok=True)
        model_file = whisperx_dir / "base.pt"
        model_file.write_text("mock model content")
        
        result = model_manager.check_model_availability(ModelType.WHISPERX, ModelSize.BASE)
        assert result is True
    
    def test_get_model_path_existing_model(self, model_manager, temp_models_dir):
        """Test getting path for existing model."""
        # Create a mock model file
        whisperx_dir = temp_models_dir / "whisperx"
        whisperx_dir.mkdir(parents=True, exist_ok=True)
        model_file = whisperx_dir / "base.pt"
        model_file.write_text("mock model content")
        
        path = model_manager.get_model_path(ModelType.WHISPERX, ModelSize.BASE)
        assert path == str(model_file)
    
    def test_get_model_path_missing_model(self, model_manager):
        """Test getting path for non-existent model raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            model_manager.get_model_path(ModelType.WHISPERX, ModelSize.BASE)    
    
    def test_list_available_models_empty(self, model_manager):
        """Test listing available models when none exist."""
        available = model_manager.list_available_models()
        assert available == {}
    
    def test_list_available_models_with_models(self, model_manager, temp_models_dir):
        """Test listing available models when some exist."""
        # Create mock model files
        whisperx_dir = temp_models_dir / "whisperx"
        whisperx_dir.mkdir(parents=True, exist_ok=True)
        (whisperx_dir / "base.pt").write_text("mock base model")
        (whisperx_dir / "small.pt").write_text("mock small model")
        
        demucs_dir = temp_models_dir / "demucs"
        demucs_dir.mkdir(parents=True, exist_ok=True)
        (demucs_dir / "htdemucs.th").write_text("mock demucs model")
        
        available = model_manager.list_available_models()
        
        assert ModelType.WHISPERX in available
        assert ModelSize.BASE in available[ModelType.WHISPERX]
        assert ModelSize.SMALL in available[ModelType.WHISPERX]
        assert ModelType.DEMUCS in available
    
    def test_get_model_metadata(self, model_manager):
        """Test getting model metadata."""
        metadata = model_manager.get_model_metadata(ModelType.WHISPERX, ModelSize.BASE)
        
        assert "filename" in metadata
        assert "checksum" in metadata
        assert "url" in metadata
        assert metadata["filename"] == "base.pt"
    
    def test_get_models_directory(self, model_manager, temp_models_dir):
        """Test getting models directory path."""
        directory = model_manager.get_models_directory()
        assert directory == str(temp_models_dir)
    
    def test_calculate_file_checksum(self, model_manager, temp_models_dir):
        """Test calculating file checksum."""
        test_file = temp_models_dir / "test.txt"
        test_content = "test content for checksum"
        test_file.write_text(test_content)
        
        checksum = model_manager._calculate_file_checksum(test_file)
        
        # Verify it's a valid SHA256 hash (64 hex characters)
        assert len(checksum) == 64
        assert all(c in "0123456789abcdef" for c in checksum)
    
    def test_verify_model_integrity_no_checksum(self, model_manager, temp_models_dir):
        """Test model integrity verification when no checksum is available."""
        # Create a mock model file
        whisperx_dir = temp_models_dir / "whisperx"
        whisperx_dir.mkdir(parents=True, exist_ok=True)
        model_file = whisperx_dir / "base.pt"
        model_file.write_text("mock model content")
        
        # Should return True when no checksum is available (development mode)
        result = model_manager._verify_model_integrity(ModelType.WHISPERX, ModelSize.BASE, model_file)
        assert result is True
    
    def test_clear_model_cache(self, model_manager, temp_models_dir):
        """Test clearing model cache."""
        # Create some mock model files
        whisperx_dir = temp_models_dir / "whisperx"
        whisperx_dir.mkdir(parents=True, exist_ok=True)
        (whisperx_dir / "base.pt").write_text("mock model")
        
        # Verify files exist
        assert (whisperx_dir / "base.pt").exists()
        
        # Clear cache
        result = model_manager.clear_model_cache()
        
        assert result is True
        assert temp_models_dir.exists()  # Directory should still exist
        assert not (whisperx_dir / "base.pt").exists()  # Files should be gone
    
    def test_set_download_progress_callback(self, model_manager):
        """Test setting download progress callback."""
        callback = Mock()
        model_manager.set_download_progress_callback(callback)
        
        assert model_manager._download_progress_callback == callback    

    def test_download_model_integration(self, model_manager):
        """Test download_model method integration with ModelDownloader."""
        with patch('src.services.model_downloader.ModelDownloader') as mock_downloader_class:
            mock_downloader = Mock()
            mock_downloader_class.return_value = mock_downloader
            
            # Mock successful download
            from src.services.model_downloader import DownloadResult
            mock_downloader.download_model.return_value = DownloadResult(success=True)
            
            result = model_manager.download_model(ModelType.WHISPERX, ModelSize.BASE)
            
            assert result is True
            mock_downloader_class.assert_called_once()
            mock_downloader.download_model.assert_called_once_with(ModelType.WHISPERX, ModelSize.BASE)
    
    def test_download_model_with_progress_callback(self, model_manager):
        """Test download_model with progress callback."""
        callback = Mock()
        model_manager.set_download_progress_callback(callback)
        
        with patch('src.services.model_downloader.ModelDownloader') as mock_downloader_class:
            mock_downloader = Mock()
            mock_downloader_class.return_value = mock_downloader
            
            # Mock successful download
            from src.services.model_downloader import DownloadResult
            mock_downloader.download_model.return_value = DownloadResult(success=True)
            
            result = model_manager.download_model(ModelType.WHISPERX, ModelSize.BASE)
            
            assert result is True
            mock_downloader.set_progress_callback.assert_called_once()
    
    def test_download_model_failure(self, model_manager):
        """Test download_model when download fails."""
        with patch('src.services.model_downloader.ModelDownloader') as mock_downloader_class:
            mock_downloader = Mock()
            mock_downloader_class.return_value = mock_downloader
            
            # Mock failed download
            from src.services.model_downloader import DownloadResult
            mock_downloader.download_model.return_value = DownloadResult(success=False, error_message="Network error")
            
            result = model_manager.download_model(ModelType.WHISPERX, ModelSize.BASE)
            
            assert result is False
    
    def test_check_required_models(self, model_manager, temp_models_dir):
        """Test checking required models for application startup."""
        # Create some mock model files
        whisperx_dir = temp_models_dir / "whisperx"
        whisperx_dir.mkdir(parents=True, exist_ok=True)
        (whisperx_dir / "base.pt").write_text("mock base model")
        
        required_models = {
            ModelType.WHISPERX: ModelSize.BASE,
            ModelType.DEMUCS: ModelSize.BASE
        }
        
        results = model_manager.check_required_models(required_models)
        
        assert "whisperx_base" in results
        assert "demucs_base" in results
        assert results["whisperx_base"] is True
        assert results["demucs_base"] is False
    
    def test_get_missing_models(self, model_manager, temp_models_dir):
        """Test getting list of missing required models."""
        # Create one model but not the other
        whisperx_dir = temp_models_dir / "whisperx"
        whisperx_dir.mkdir(parents=True, exist_ok=True)
        (whisperx_dir / "base.pt").write_text("mock base model")
        
        required_models = {
            ModelType.WHISPERX: ModelSize.BASE,
            ModelType.DEMUCS: ModelSize.BASE
        }
        
        missing = model_manager.get_missing_models(required_models)
        
        assert len(missing) == 1
        assert (ModelType.DEMUCS, ModelSize.BASE) in missing
    
    def test_is_offline_ready(self, model_manager, temp_models_dir):
        """Test checking if system is ready for offline operation."""
        required_models = {
            ModelType.WHISPERX: ModelSize.BASE,
            ModelType.DEMUCS: ModelSize.BASE
        }
        
        # Initially no models available
        assert model_manager.is_offline_ready(required_models) is False
        
        # Add all required models
        whisperx_dir = temp_models_dir / "whisperx"
        whisperx_dir.mkdir(parents=True, exist_ok=True)
        (whisperx_dir / "base.pt").write_text("mock base model")
        
        demucs_dir = temp_models_dir / "demucs"
        demucs_dir.mkdir(parents=True, exist_ok=True)
        (demucs_dir / "htdemucs.th").write_text("mock demucs model")
        
        # Clear cache to force fresh check
        model_manager.invalidate_availability_cache()
        
        assert model_manager.is_offline_ready(required_models) is True
    
    def test_invalidate_availability_cache(self, model_manager):
        """Test invalidating the availability cache."""
        # Populate cache
        model_manager.check_model_availability(ModelType.WHISPERX, ModelSize.BASE)
        assert len(model_manager._availability_cache) > 0
        
        # Invalidate cache
        model_manager.invalidate_availability_cache()
        assert len(model_manager._availability_cache) == 0
    
    def test_get_model_info(self, model_manager, temp_models_dir):
        """Test getting comprehensive model information."""
        # Create a mock model file
        whisperx_dir = temp_models_dir / "whisperx"
        whisperx_dir.mkdir(parents=True, exist_ok=True)
        model_file = whisperx_dir / "base.pt"
        model_file.write_text("mock model content")
        
        info = model_manager.get_model_info(ModelType.WHISPERX, ModelSize.BASE)
        
        assert info["type"] == "whisperx"
        assert info["size"] == "base"
        assert info["available"] is True
        assert "path" in info
        assert "metadata" in info
        assert "file_size_bytes" in info
        assert "file_size_mb" in info
    
    def test_get_all_models_info(self, model_manager):
        """Test getting information about all models."""
        all_info = model_manager.get_all_models_info()
        
        # Should include all models defined in metadata
        assert "whisperx_tiny" in all_info
        assert "whisperx_base" in all_info
        assert "demucs_base" in all_info
        
        # Each model should have required fields
        for model_key, info in all_info.items():
            assert "type" in info
            assert "size" in info
            assert "available" in info
            assert "path" in info
            assert "metadata" in info