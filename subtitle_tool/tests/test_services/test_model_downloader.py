"""
Tests for the ModelDownloader service.
"""

import pytest
import tempfile
import shutil
import asyncio
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
import aiohttp

from src.services.model_downloader import ModelDownloader, DownloadProgress, DownloadResult
from src.services.interfaces import ModelType
from src.models.data_models import ModelSize


class TestModelDownloader:
    """Test cases for ModelDownloader class."""
    
    @pytest.fixture
    def temp_models_dir(self):
        """Create a temporary directory for models."""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def model_downloader(self, temp_models_dir):
        """Create ModelDownloader instance with temporary directory."""
        with patch('src.services.model_downloader.config_manager') as mock_config:
            mock_config.get_config.return_value.models_directory = str(temp_models_dir)
            downloader = ModelDownloader()
            return downloader
    
    def test_init_creates_models_directory(self, model_downloader, temp_models_dir):
        """Test that ModelDownloader creates models directory on initialization."""
        assert temp_models_dir.exists()
        assert model_downloader.models_dir == temp_models_dir
    
    def test_set_progress_callback(self, model_downloader):
        """Test setting progress callback."""
        callback = Mock()
        model_downloader.set_progress_callback(callback)
        
        assert model_downloader._progress_callback == callback
    
    def test_get_download_url_valid_model(self, model_downloader):
        """Test getting download URL for valid model."""
        url = model_downloader._get_download_url(ModelType.WHISPERX, ModelSize.BASE)
        
        assert url is not None
        assert url.startswith("https://")
    
    def test_get_download_url_invalid_model(self, model_downloader):
        """Test getting download URL for invalid model returns None."""
        # Mock an invalid model by temporarily modifying the URLs dict
        original_urls = model_downloader._model_urls
        model_downloader._model_urls = {}
        
        url = model_downloader._get_download_url(ModelType.WHISPERX, ModelSize.BASE)
        
        assert url is None
        
        # Restore original URLs
        model_downloader._model_urls = original_urls
    
    def test_get_output_path_whisperx(self, model_downloader, temp_models_dir):
        """Test getting output path for WhisperX model."""
        path = model_downloader._get_output_path(ModelType.WHISPERX, ModelSize.BASE)
        
        expected_path = temp_models_dir / "whisperx" / "base.pt"
        assert path == expected_path
    
    def test_get_output_path_demucs(self, model_downloader, temp_models_dir):
        """Test getting output path for Demucs model."""
        path = model_downloader._get_output_path(ModelType.DEMUCS, ModelSize.BASE)
        
        expected_path = temp_models_dir / "demucs" / "htdemucs.th"
        assert path == expected_path
    
    def test_check_disk_space_sufficient(self, model_downloader):
        """Test disk space check with sufficient space."""
        # Test with a small requirement (1 KB)
        result = model_downloader.check_disk_space(1024)
        
        # Should return True for reasonable space requirements
        assert result is True
    
    def test_cancel_download_all(self, model_downloader):
        """Test cancelling all downloads."""
        result = model_downloader.cancel_download()
        
        # Should return False when no downloads are active
        assert result is False
    
    def test_cancel_specific_download(self, model_downloader):
        """Test cancelling specific download."""
        result = model_downloader.cancel_download(ModelType.WHISPERX, ModelSize.BASE)
        
        # Should return False when no download is active
        assert result is False
    
    def test_get_active_downloads_empty(self, model_downloader):
        """Test getting active downloads when none are running."""
        active = model_downloader.get_active_downloads()
        
        assert active == []
    
    def test_is_download_active_false(self, model_downloader):
        """Test checking if download is active when it's not."""
        result = model_downloader.is_download_active(ModelType.WHISPERX, ModelSize.BASE)
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_download_model_async_no_url(self, model_downloader):
        """Test async download with no URL available."""
        # Mock empty URLs
        model_downloader._model_urls = {}
        
        result = await model_downloader.download_model_async(ModelType.WHISPERX, ModelSize.BASE)
        
        assert result.success is False
        assert "No download URL available" in result.error_message
    
    @pytest.mark.asyncio
    async def test_check_disk_space_async_success(self, model_downloader):
        """Test async disk space checking."""
        # Mock a successful HEAD request
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = AsyncMock()
            mock_response = AsyncMock()
            mock_response.headers = {'content-length': '1000'}
            
            mock_session.head.return_value.__aenter__.return_value = mock_response
            mock_session_class.return_value.__aenter__.return_value = mock_session
            
            # Mock check_disk_space to return True
            model_downloader.check_disk_space = Mock(return_value=True)
            
            result = await model_downloader._check_disk_space_async("http://example.com/file", Path("/tmp/test"))
            
            assert result is True
    
    @pytest.mark.asyncio
    async def test_download_model_async_insufficient_disk_space(self, model_downloader):
        """Test async download with insufficient disk space."""
        # Mock disk space check to return False
        model_downloader._check_disk_space_async = AsyncMock(return_value=False)
        
        result = await model_downloader.download_model_async(ModelType.WHISPERX, ModelSize.BASE)
        
        assert result.success is False
        assert "Insufficient disk space" in result.error_message
    
    def test_download_file_network_error_sync(self, model_downloader, temp_models_dir):
        """Test download with network error using sync wrapper."""
        # Test the sync wrapper with a mock that returns a failure result
        async def mock_download_async(model_type, model_size):
            return DownloadResult(success=False, error_message="Network error")
        
        model_downloader.download_model_async = mock_download_async
        
        result = model_downloader.download_model(ModelType.WHISPERX, ModelSize.BASE)
        
        assert result.success is False
        assert "Network error" in result.error_message
    
    def test_download_model_sync_wrapper(self, model_downloader):
        """Test synchronous download wrapper."""
        # Mock the async method to return a successful result
        async def mock_download_async(model_type, model_size):
            return DownloadResult(success=True, file_path="/mock/path")
        
        model_downloader.download_model_async = mock_download_async
        
        result = model_downloader.download_model(ModelType.WHISPERX, ModelSize.BASE)
        
        assert result.success is True


class TestDownloadProgress:
    """Test cases for DownloadProgress dataclass."""
    
    def test_download_progress_creation(self):
        """Test creating DownloadProgress instance."""
        progress = DownloadProgress(
            bytes_downloaded=500,
            total_bytes=1000,
            percentage=50.0,
            speed_mbps=1.5
        )
        
        assert progress.bytes_downloaded == 500
        assert progress.total_bytes == 1000
        assert progress.percentage == 50.0
        assert progress.speed_mbps == 1.5
    
    def test_is_complete_true(self):
        """Test is_complete property when download is complete."""
        progress = DownloadProgress(
            bytes_downloaded=1000,
            total_bytes=1000,
            percentage=100.0,
            speed_mbps=1.5
        )
        
        assert progress.is_complete is True
    
    def test_is_complete_false(self):
        """Test is_complete property when download is not complete."""
        progress = DownloadProgress(
            bytes_downloaded=500,
            total_bytes=1000,
            percentage=50.0,
            speed_mbps=1.5
        )
        
        assert progress.is_complete is False


class TestDownloadResult:
    """Test cases for DownloadResult dataclass."""
    
    def test_download_result_success(self):
        """Test creating successful DownloadResult."""
        result = DownloadResult(
            success=True,
            file_path="/path/to/model.pt",
            bytes_downloaded=1000,
            total_bytes=1000
        )
        
        assert result.success is True
        assert result.file_path == "/path/to/model.pt"
        assert result.error_message is None
    
    def test_download_result_failure(self):
        """Test creating failed DownloadResult."""
        result = DownloadResult(
            success=False,
            error_message="Network timeout"
        )
        
        assert result.success is False
        assert result.error_message == "Network timeout"
        assert result.file_path is None