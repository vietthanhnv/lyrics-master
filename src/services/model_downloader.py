"""
Model download service with progress tracking and resumption capabilities.

This module handles downloading AI models from remote sources with progress callbacks,
error handling, and download resumption support.
"""

import asyncio
import aiohttp
import aiofiles
from pathlib import Path
from typing import Callable, Optional, Dict, Any, List
import logging
from dataclasses import dataclass

from .interfaces import ModelType
from ..models.data_models import ModelSize
from ..utils.config import config_manager


@dataclass
class DownloadProgress:
    """Progress information for model downloads."""
    bytes_downloaded: int
    total_bytes: int
    percentage: float
    speed_mbps: float
    eta_seconds: Optional[float] = None
    
    @property
    def is_complete(self) -> bool:
        """Check if download is complete."""
        return self.bytes_downloaded >= self.total_bytes


@dataclass
class DownloadResult:
    """Result of a model download operation."""
    success: bool
    file_path: Optional[str] = None
    error_message: Optional[str] = None
    bytes_downloaded: int = 0
    total_bytes: int = 0


class ModelDownloader:
    """Handles downloading AI models with progress tracking and resumption."""
    
    def __init__(self):
        self.config = config_manager.get_config()
        self.models_dir = Path(self.config.models_directory)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        
        # Progress callback
        self._progress_callback: Optional[Callable[[DownloadProgress], None]] = None
        
        # Download session configuration
        self._session_timeout = aiohttp.ClientTimeout(total=3600)  # 1 hour timeout
        self._chunk_size = 8192  # 8KB chunks
        
        # Model URLs mapping
        self._model_urls = self._get_model_urls()
        
        # Download cancellation support
        self._active_downloads: Dict[str, asyncio.Task] = {}
        self._cancelled_downloads: set = set()
        
        # Logger
        self.logger = logging.getLogger(__name__)
    
    def _get_model_urls(self) -> Dict[str, Dict[str, str]]:
        """Get model download URLs."""
        return {
            ModelType.DEMUCS.value: {
                ModelSize.BASE.value: "https://dl.fbaipublicfiles.com/demucs/hybrid_transformer/htdemucs.th"
            },
            ModelType.WHISPERX.value: {
                ModelSize.TINY.value: "https://openaipublic.azureedge.net/main/whisper/models/65147644a518d12f04e32d6f3b26facc3f8dd46e5390956a9424a650c0ce22794.pt",
                ModelSize.BASE.value: "https://openaipublic.azureedge.net/main/whisper/models/ed3a0b6b1c0edf879ad9b11b1af5a0e6ab5db9205f891f668f8b0e6c6326e34e.pt",
                ModelSize.SMALL.value: "https://openaipublic.azureedge.net/main/whisper/models/9ecf779972d90ba49c06d968637d720dd632c55bbf19a8717b3f3bbc1a1c6b6e.pt",
                ModelSize.MEDIUM.value: "https://openaipublic.azureedge.net/main/whisper/models/345ae4da62f9b3d59415adc60127b97c714f32e89e936602e85993674d08dcb1.pt",
                ModelSize.LARGE.value: "https://openaipublic.azureedge.net/main/whisper/models/e4b87e7e0bf463eb8e6956e646f1e277e901512310def2c24bf0e11bd3c28e9a.pt"
            }
        }    

    def set_progress_callback(self, callback: Callable[[DownloadProgress], None]) -> None:
        """Set callback for download progress updates."""
        self._progress_callback = callback
    
    async def download_model_async(self, model_type: ModelType, model_size: ModelSize) -> DownloadResult:
        """Download a model asynchronously with progress tracking."""
        download_key = f"{model_type.value}_{model_size.value}"
        
        try:
            # Check if download is already cancelled
            if download_key in self._cancelled_downloads:
                self._cancelled_downloads.discard(download_key)
                return DownloadResult(
                    success=False,
                    error_message="Download was cancelled"
                )
            
            # Get download URL
            url = self._get_download_url(model_type, model_size)
            if not url:
                return DownloadResult(
                    success=False,
                    error_message=f"No download URL available for {model_type.value}/{model_size.value}"
                )
            
            # Determine output file path
            output_path = self._get_output_path(model_type, model_size)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Check disk space before starting download
            if not await self._check_disk_space_async(url, output_path):
                return DownloadResult(
                    success=False,
                    error_message="Insufficient disk space for download"
                )
            
            # Check if partial download exists
            resume_from = 0
            if output_path.exists():
                resume_from = output_path.stat().st_size
                self.logger.info(f"Resuming download from {resume_from} bytes")
            
            # Create download task and track it
            download_task = asyncio.create_task(
                self._download_file(url, output_path, resume_from, download_key)
            )
            self._active_downloads[download_key] = download_task
            
            try:
                # Download the model
                result = await download_task
                return result
            finally:
                # Clean up task tracking
                self._active_downloads.pop(download_key, None)
            
        except asyncio.CancelledError:
            self.logger.info(f"Download cancelled for {model_type.value}/{model_size.value}")
            return DownloadResult(
                success=False,
                error_message="Download was cancelled"
            )
        except Exception as e:
            self.logger.error(f"Error downloading model {model_type.value}/{model_size.value}: {e}")
            return DownloadResult(
                success=False,
                error_message=str(e)
            )
    
    def download_model(self, model_type: ModelType, model_size: ModelSize) -> DownloadResult:
        """Download a model synchronously (wrapper for async method)."""
        try:
            # Get or create event loop
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            # Run the async download
            return loop.run_until_complete(self.download_model_async(model_type, model_size))
            
        except Exception as e:
            self.logger.error(f"Error in synchronous download: {e}")
            return DownloadResult(
                success=False,
                error_message=str(e)
            )
    
    async def _download_file(self, url: str, output_path: Path, resume_from: int = 0, download_key: str = "") -> DownloadResult:
        """Download a file with progress tracking and resumption support."""
        headers = {}
        if resume_from > 0:
            headers['Range'] = f'bytes={resume_from}-'
        
        connector = aiohttp.TCPConnector(limit=1, limit_per_host=1)
        async with aiohttp.ClientSession(timeout=self._session_timeout, connector=connector) as session:
            try:
                async with session.get(url, headers=headers) as response:
                    # Check for cancellation
                    if download_key in self._cancelled_downloads:
                        raise asyncio.CancelledError("Download cancelled by user")
                    
                    # Check response status
                    if response.status not in [200, 206]:  # 206 for partial content
                        return DownloadResult(
                            success=False,
                            error_message=f"HTTP {response.status}: {response.reason}"
                        )
                    
                    # Get total file size
                    content_length = response.headers.get('content-length')
                    if content_length:
                        total_size = int(content_length) + resume_from
                    else:
                        total_size = 0
                    
                    # Open file for writing (append mode if resuming)
                    mode = 'ab' if resume_from > 0 else 'wb'
                    
                    async with aiofiles.open(output_path, mode) as f:
                        bytes_downloaded = resume_from
                        start_time = asyncio.get_event_loop().time()
                        last_progress_time = start_time
                        
                        async for chunk in response.content.iter_chunked(self._chunk_size):
                            # Check for cancellation periodically
                            if download_key in self._cancelled_downloads:
                                raise asyncio.CancelledError("Download cancelled by user")
                            
                            await f.write(chunk)
                            bytes_downloaded += len(chunk)
                            
                            # Update progress every 0.5 seconds to avoid too frequent callbacks
                            current_time = asyncio.get_event_loop().time()
                            if current_time - last_progress_time >= 0.5:
                                elapsed_time = current_time - start_time
                                
                                if elapsed_time > 0:
                                    speed_bps = (bytes_downloaded - resume_from) / elapsed_time
                                    speed_mbps = speed_bps / (1024 * 1024)  # Convert to MB/s
                                    
                                    # Calculate ETA
                                    eta_seconds = None
                                    if total_size > 0 and speed_bps > 0:
                                        remaining_bytes = total_size - bytes_downloaded
                                        eta_seconds = remaining_bytes / speed_bps
                                    
                                    # Create progress object
                                    progress = DownloadProgress(
                                        bytes_downloaded=bytes_downloaded,
                                        total_bytes=total_size,
                                        percentage=(bytes_downloaded / total_size * 100) if total_size > 0 else 0,
                                        speed_mbps=speed_mbps,
                                        eta_seconds=eta_seconds
                                    )
                                    
                                    # Call progress callback
                                    if self._progress_callback:
                                        try:
                                            self._progress_callback(progress)
                                        except Exception as e:
                                            self.logger.warning(f"Progress callback error: {e}")
                                    
                                    last_progress_time = current_time
                    
                    # Final progress update
                    if self._progress_callback and total_size > 0:
                        final_progress = DownloadProgress(
                            bytes_downloaded=bytes_downloaded,
                            total_bytes=total_size,
                            percentage=100.0,
                            speed_mbps=0.0,
                            eta_seconds=0.0
                        )
                        try:
                            self._progress_callback(final_progress)
                        except Exception as e:
                            self.logger.warning(f"Final progress callback error: {e}")
                    
                    return DownloadResult(
                        success=True,
                        file_path=str(output_path),
                        bytes_downloaded=bytes_downloaded,
                        total_bytes=total_size
                    )
                    
            except asyncio.CancelledError:
                # Clean up partial file if cancelled early in download
                if output_path.exists() and resume_from == 0:
                    try:
                        output_path.unlink()
                    except Exception as e:
                        self.logger.warning(f"Failed to clean up partial file: {e}")
                raise
            except aiohttp.ClientError as e:
                return DownloadResult(
                    success=False,
                    error_message=f"Network error: {e}"
                )
            except OSError as e:
                return DownloadResult(
                    success=False,
                    error_message=f"File system error: {e}"
                )
    
    def _get_download_url(self, model_type: ModelType, model_size: ModelSize) -> Optional[str]:
        """Get download URL for a specific model."""
        return self._model_urls.get(model_type.value, {}).get(model_size.value)
    
    def _get_output_path(self, model_type: ModelType, model_size: ModelSize) -> Path:
        """Get output file path for a model."""
        model_dir = self.models_dir / model_type.value
        
        # Determine filename based on model type
        if model_type == ModelType.DEMUCS:
            filename = "htdemucs.th"
        else:  # WhisperX
            filename = f"{model_size.value}.pt"
        
        return model_dir / filename
    
    def check_disk_space(self, required_bytes: int) -> bool:
        """Check if there's enough disk space for download."""
        try:
            import shutil
            free_bytes = shutil.disk_usage(self.models_dir).free
            return free_bytes >= required_bytes
        except Exception:
            return True  # Assume space is available if check fails
    
    async def _check_disk_space_async(self, url: str, output_path: Path) -> bool:
        """Asynchronously check if there's enough disk space for download."""
        try:
            # Try to get file size from HEAD request
            connector = aiohttp.TCPConnector(limit=1, limit_per_host=1)
            timeout = aiohttp.ClientTimeout(total=30)  # Short timeout for HEAD request
            
            async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
                try:
                    async with session.head(url) as response:
                        content_length = response.headers.get('content-length')
                        if content_length:
                            required_bytes = int(content_length)
                            
                            # Add 10% buffer for safety
                            required_bytes = int(required_bytes * 1.1)
                            
                            return self.check_disk_space(required_bytes)
                except aiohttp.ClientError:
                    # If HEAD request fails, assume space is available
                    pass
            
            return True  # Assume space is available if we can't determine file size
            
        except Exception as e:
            self.logger.warning(f"Could not check disk space: {e}")
            return True  # Assume space is available if check fails
    
    def cancel_download(self, model_type: ModelType = None, model_size: ModelSize = None) -> bool:
        """Cancel ongoing download(s)."""
        try:
            if model_type and model_size:
                # Cancel specific download
                download_key = f"{model_type.value}_{model_size.value}"
                self._cancelled_downloads.add(download_key)
                
                if download_key in self._active_downloads:
                    task = self._active_downloads[download_key]
                    task.cancel()
                    return True
                return False
            else:
                # Cancel all active downloads
                cancelled_count = 0
                for download_key, task in list(self._active_downloads.items()):
                    self._cancelled_downloads.add(download_key)
                    task.cancel()
                    cancelled_count += 1
                
                return cancelled_count > 0
                
        except Exception as e:
            self.logger.error(f"Error cancelling download: {e}")
            return False
    
    def get_active_downloads(self) -> List[str]:
        """Get list of currently active downloads."""
        return list(self._active_downloads.keys())
    
    def is_download_active(self, model_type: ModelType, model_size: ModelSize) -> bool:
        """Check if a specific download is currently active."""
        download_key = f"{model_type.value}_{model_size.value}"
        return download_key in self._active_downloads