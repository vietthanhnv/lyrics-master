"""
Vocal separation service using audio-separator for isolating vocals from mixed audio.

This module provides the VocalSeparator class that wraps audio-separator functionality
to extract vocals from audio files, with progress tracking and error handling.
"""

import os
import tempfile
import shutil
import time
from pathlib import Path
from typing import Optional, Callable, Dict, Any
import logging

from ..models.data_models import ModelSize
from ..services.interfaces import ProcessingError


logger = logging.getLogger(__name__)


class VocalSeparationResult:
    """Result of vocal separation operation."""
    
    def __init__(self, success: bool, vocals_path: Optional[str] = None, 
                 instrumental_path: Optional[str] = None,
                 error_message: Optional[str] = None, processing_time: float = 0.0):
        self.success = success
        self.vocals_path = vocals_path
        self.instrumental_path = instrumental_path
        self.error_message = error_message
        self.processing_time = processing_time


class VocalSeparator:
    """
    Handles vocal separation using audio-separator models.
    
    This class provides functionality to separate vocals from mixed audio tracks
    using various AI models including MDX-Net, VR Arch, Demucs, and MDXC.
    """
    
    def __init__(self, temp_dir: Optional[str] = None):
        """
        Initialize the VocalSeparator.
        
        Args:
            temp_dir: Optional custom temporary directory for processing files
        """
        self.temp_dir = temp_dir or tempfile.gettempdir()
        self.progress_callback: Optional[Callable[[float, str], None]] = None
        self._current_process = None
        self._temp_files = []  # Track temporary files for cleanup
        self.logger = logging.getLogger(__name__)
        
        # Ensure temp directory exists
        os.makedirs(self.temp_dir, exist_ok=True)
    
    def _get_audio_separator_model(self, model_size: ModelSize) -> str:
        """Get appropriate audio-separator model based on size."""
        # Map model sizes to actual audio-separator models
        # Using simpler models that work better with short audio files
        model_map = {
            ModelSize.TINY: "UVR_MDXNET_KARA_2.onnx",
            ModelSize.BASE: "UVR_MDXNET_KARA_2.onnx",  # Use a more compatible model
            ModelSize.SMALL: "UVR-MDX-NET-Inst_HQ_3.onnx",
            ModelSize.MEDIUM: "htdemucs.yaml",
            ModelSize.LARGE: "htdemucs_ft.yaml"
        }
        return model_map.get(model_size, model_map[ModelSize.BASE])
    
    def _create_temp_output_dir(self) -> str:
        """Create a temporary output directory for separation results."""
        output_dir = os.path.join(self.temp_dir, f"vocal_separation_{int(time.time())}")
        os.makedirs(output_dir, exist_ok=True)
        return output_dir
    
    def _update_progress(self, percentage: float, message: str):
        """Update progress if callback is set."""
        if self.progress_callback:
            self.progress_callback(percentage, message)
        self.logger = logging.getLogger(__name__)
    
    def set_progress_callback(self, callback: Callable[[float, str], None]) -> None:
        """
        Set callback function for progress updates.
        
        Args:
            callback: Function that receives (progress_percentage, status_message)
        """
        self.progress_callback = callback
    
    def separate_vocals(self, audio_path: str, model_size: ModelSize = ModelSize.BASE) -> VocalSeparationResult:
        """
        Separate vocals from the input audio file using audio-separator.
        
        Args:
            audio_path: Path to the input audio file
            model_size: Model size to use for separation
            
        Returns:
            VocalSeparationResult containing the path to separated vocals or error info
        """
        start_time = time.time()
        
        try:
            # Validate input file
            if not os.path.exists(audio_path):
                raise ProcessingError(f"Input audio file not found: {audio_path}")
            
            # Check file size and format
            file_size = os.path.getsize(audio_path)
            if file_size == 0:
                raise ProcessingError("Input audio file is empty")
            
            # Update progress
            self._update_progress(0.0, "Initializing vocal separation...")
            
            # Import audio-separator
            try:
                from audio_separator.separator import Separator
                self.logger.info("audio-separator imported successfully")
            except ImportError as e:
                self.logger.error(f"audio-separator not available: {e}")
                raise ProcessingError(f"Required package 'audio-separator' is not installed. Please install it with: pip install audio-separator")
            
            # Create temporary output directory
            output_dir = self._create_temp_output_dir()
            
            # Update progress
            self._update_progress(10.0, "Loading separation model...")
            
            # Initialize separator with appropriate model
            separator = Separator(
                output_dir=output_dir,
                output_format='wav',
                normalization_threshold=0.9,
                amplification_threshold=0.0,
                mdx_params={
                    "hop_length": 1024,
                    "segment_size": 256,
                    "overlap": 0.25,
                    "batch_size": 1,
                    "enable_denoise": False
                }
            )
            
            # Select model based on size
            model_filename = self._get_audio_separator_model(model_size)
            
            # Update progress
            self._update_progress(20.0, f"Loading model: {model_filename}")
            
            # Load the model
            separator.load_model(model_filename=model_filename)
            
            # Update progress
            self._update_progress(40.0, "Starting vocal separation...")
            
            try:
                # Perform separation
                output_files = separator.separate(audio_path)
                logger.info(f"Separator returned output files: {output_files}")
                
                # Update progress
                self._update_progress(90.0, "Finalizing vocal extraction...")
                
                # Find the vocals and instrumental files
                vocals_path = None
                instrumental_path = None
                logger.info(f"Looking for vocals and instrumental files in output files: {output_files}")
                
                for file_path in output_files:
                    filename = os.path.basename(file_path).lower()
                    logger.info(f"Checking file: {filename}")
                    if 'vocals' in filename:
                        vocals_path = file_path
                        logger.info(f"Found vocals file: {vocals_path}")
                    elif 'instrumental' in filename or 'accomp' in filename or 'music' in filename:
                        instrumental_path = file_path
                        logger.info(f"Found instrumental file: {instrumental_path}")
                
                if not vocals_path:
                    # If no vocals file found, use the first output file
                    vocals_path = output_files[0] if output_files else None
                    logger.info(f"No vocals file found, using first output: {vocals_path}")
                
                if not vocals_path or not os.path.exists(vocals_path):
                    # Try to find files in the output directory manually
                    logger.info(f"Searching for files in output directory: {output_dir}")
                    for root, dirs, files in os.walk(output_dir):
                        for file in files:
                            filename_lower = file.lower()
                            if 'vocals' in filename_lower:
                                vocals_path = os.path.join(root, file)
                                logger.info(f"Found vocals file manually: {vocals_path}")
                            elif 'instrumental' in filename_lower or 'accomp' in filename_lower or 'music' in filename_lower:
                                instrumental_path = os.path.join(root, file)
                                logger.info(f"Found instrumental file manually: {instrumental_path}")
                
                if not vocals_path or not os.path.exists(vocals_path):
                    raise ProcessingError("Vocal separation completed but vocals file not found")
                    
            except Exception as sep_error:
                logger.error(f"Error during separation: {sep_error}")
                raise ProcessingError(f"Vocal separation failed: {str(sep_error)}")
            
            output_size = os.path.getsize(vocals_path)
            if output_size == 0:
                raise ProcessingError("Vocal separation produced empty output file")
            
            # Update progress
            self._update_progress(100.0, "Vocal separation complete")
            
            processing_time = time.time() - start_time
            logger.info(f"Vocal separation completed in {processing_time:.2f} seconds")
            logger.info(f"Input file: {file_size} bytes, Output file: {output_size} bytes")
            
            return VocalSeparationResult(
                success=True,
                vocals_path=vocals_path,
                instrumental_path=instrumental_path,
                processing_time=processing_time
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            error_msg = f"Vocal separation failed: {str(e)}"
            logger.error(error_msg)
            
            return VocalSeparationResult(
                success=False,
                error_message=error_msg,
                processing_time=processing_time
            )
            
            # Clean up on error
            self.cleanup_temp_files()
            
            return VocalSeparationResult(
                success=False,
                error_message=error_msg,
                processing_time=processing_time
            )
        except Exception as e:
            processing_time = time.time() - start_time
            error_msg = f"Unexpected error during vocal separation: {str(e)}"
            logger.error(error_msg, exc_info=True)
            
            # Clean up on error
            self.cleanup_temp_files()
            
            return VocalSeparationResult(
                success=False,
                error_message=error_msg,
                processing_time=processing_time
            )
    
    def _check_demucs_availability(self) -> None:
        """
        Check if Demucs is available for import.
        
        Raises:
            ProcessingError: If Demucs is not installed
        """
        try:
            import demucs.api
            import torch
            import torchaudio
        except ImportError as e:
            missing_package = str(e).split("'")[1] if "'" in str(e) else "unknown package"
            raise ProcessingError(
                f"Required package '{missing_package}' is not installed. "
                f"Please install it with: pip install demucs torch torchaudio"
            )
    
    def _check_system_resources(self, audio_path: str, model_size: ModelSize) -> None:
        """
        Check if system has sufficient resources for processing.
        
        Args:
            audio_path: Path to the audio file to process
            model_size: Model size that will be used
            
        Raises:
            ProcessingError: If insufficient resources are detected
        """
        import psutil
        
        try:
            # Check available memory
            memory = psutil.virtual_memory()
            available_gb = memory.available / (1024**3)
            
            # Estimate memory requirements based on model size
            memory_requirements = {
                ModelSize.TINY: 2.0,    # 2GB
                ModelSize.BASE: 4.0,    # 4GB
                ModelSize.SMALL: 4.0,   # 4GB
                ModelSize.MEDIUM: 6.0,  # 6GB
                ModelSize.LARGE: 8.0    # 8GB
            }
            
            required_gb = memory_requirements.get(model_size, 4.0)
            
            if available_gb < required_gb:
                raise ProcessingError(
                    f"Insufficient memory: {available_gb:.1f}GB available, "
                    f"{required_gb:.1f}GB required for {model_size.value} model. "
                    f"Try using a smaller model or close other applications."
                )
            
            # Check available disk space in temp directory
            disk_usage = psutil.disk_usage(self.temp_dir)
            available_disk_gb = disk_usage.free / (1024**3)
            
            # Estimate disk space needed (roughly 3x the input file size)
            file_size_gb = os.path.getsize(audio_path) / (1024**3)
            required_disk_gb = max(file_size_gb * 3, 1.0)  # At least 1GB
            
            if available_disk_gb < required_disk_gb:
                raise ProcessingError(
                    f"Insufficient disk space: {available_disk_gb:.1f}GB available, "
                    f"{required_disk_gb:.1f}GB required for processing. "
                    f"Please free up disk space."
                )
                
            logger.info(f"Resource check passed: {available_gb:.1f}GB RAM, {available_disk_gb:.1f}GB disk available")
            
        except ImportError:
            # psutil not available, skip resource checking
            logger.warning("psutil not available, skipping resource checks")
        except Exception as e:
            # Don't fail processing due to resource check errors
            logger.warning(f"Resource check failed: {e}")
    
    def _get_demucs_model_name(self, model_size: ModelSize) -> str:
        """
        Get the appropriate Demucs model name based on size.
        
        Args:
            model_size: The requested model size
            
        Returns:
            String name of the Demucs model to use
        """
        # Map our model sizes to Demucs model names
        model_mapping = {
            ModelSize.TINY: "mdx_extra_q",  # Fastest, lower quality
            ModelSize.BASE: "htdemucs",     # Default balanced model
            ModelSize.SMALL: "htdemucs",    # Same as base for Demucs
            ModelSize.MEDIUM: "htdemucs_ft", # Fine-tuned version
            ModelSize.LARGE: "mdx_extra"    # Highest quality, slowest
        }
        
        return model_mapping.get(model_size, "htdemucs")
    
    def _create_temp_output_dir(self) -> str:
        """
        Create a temporary directory for output files.
        
        Returns:
            Path to the created temporary directory
        """
        temp_output = tempfile.mkdtemp(prefix="demucs_", dir=self.temp_dir)
        self._temp_files.append(temp_output)
        return temp_output
    
    def _run_demucs_separation(self, audio_path: str, output_dir: str, model_name: str) -> str:
        """
        Run the actual Demucs separation process.
        
        Args:
            audio_path: Path to input audio file
            output_dir: Directory for output files
            model_name: Name of Demucs model to use
            
        Returns:
            Path to the separated vocals file
        """
        try:
            import demucs.api
            import torch
            import torchaudio
            
            # Update progress
            self._update_progress(30.0, "Loading audio file...")
            
            # Check available device (GPU vs CPU)
            device = "cuda" if torch.cuda.is_available() else "cpu"
            logger.info(f"Using device: {device} for Demucs processing")
            
            # Load the separator with device specification
            separator = demucs.api.Separator(model=model_name, device=device)
            
            # Update progress
            self._update_progress(40.0, f"Processing audio with {model_name} model...")
            
            # Perform separation with progress tracking
            # The Demucs API handles the actual separation
            origin, separated = separator.separate_audio_file(audio_path)
            
            # Update progress
            self._update_progress(70.0, "Extracting vocals...")
            
            # Validate separation results
            if not isinstance(separated, (list, tuple)) or len(separated) == 0:
                raise ProcessingError("Demucs separation returned no stems")
            
            # Save vocals to output directory
            vocals_filename = f"vocals_{Path(audio_path).stem}.wav"
            vocals_path = os.path.join(output_dir, vocals_filename)
            
            # Extract vocals - handle different model outputs
            vocals_tensor = None
            if len(separated) == 4:
                # Standard 4-stem separation: drums, bass, other, vocals
                vocals_tensor = separated[3]  # vocals stem
                logger.info("Using 4-stem separation, extracting vocals from index 3")
            elif len(separated) == 2:
                # 2-stem separation: accompaniment, vocals
                vocals_tensor = separated[1]  # vocals stem
                logger.info("Using 2-stem separation, extracting vocals from index 1")
            else:
                # Try to find vocals in available stems
                logger.warning(f"Unexpected number of stems ({len(separated)}), using last stem as vocals")
                vocals_tensor = separated[-1]
            
            if vocals_tensor is None:
                raise ProcessingError("Could not extract vocals from separation results")
            
            # Ensure tensor is on CPU for saving
            vocals_tensor = vocals_tensor.cpu()
            
            # Validate tensor shape and content
            if vocals_tensor.numel() == 0:
                raise ProcessingError("Extracted vocals tensor is empty")
            
            # Save vocals as WAV file
            torchaudio.save(vocals_path, vocals_tensor, separator.samplerate)
            
            # Verify the output file was created and has content
            if not os.path.exists(vocals_path):
                raise ProcessingError("Failed to save vocals file")
            
            file_size = os.path.getsize(vocals_path)
            if file_size == 0:
                raise ProcessingError("Saved vocals file is empty")
            
            self._update_progress(80.0, "Vocals file saved successfully")
            logger.info(f"Vocals extracted and saved to: {vocals_path} ({file_size} bytes)")
            
            return vocals_path
            
        except ImportError as e:
            raise ProcessingError(f"Required dependencies not available: {e}")
        except torch.cuda.OutOfMemoryError:
            raise ProcessingError("Insufficient GPU memory for processing. Try using a smaller model or ensure sufficient system resources.")
        except RuntimeError as e:
            if "out of memory" in str(e).lower():
                raise ProcessingError("Insufficient memory for processing. Try using a smaller model or close other applications.")
            else:
                raise ProcessingError(f"Runtime error during separation: {e}")
        except Exception as e:
            raise ProcessingError(f"Demucs separation failed: {e}")
    
    def _update_progress(self, percentage: float, message: str) -> None:
        """
        Update progress if callback is set.
        
        Args:
            percentage: Progress percentage (0-100)
            message: Status message
        """
        if self.progress_callback:
            self.progress_callback(percentage, message)
    
    def cleanup_temp_files(self) -> None:
        """
        Clean up temporary files created during processing.
        """
        for temp_path in self._temp_files:
            try:
                if os.path.isfile(temp_path):
                    os.remove(temp_path)
                elif os.path.isdir(temp_path):
                    shutil.rmtree(temp_path)
                logger.debug(f"Cleaned up temporary file/directory: {temp_path}")
            except Exception as e:
                logger.warning(f"Failed to clean up {temp_path}: {e}")
        
        self._temp_files.clear()
    
    def cancel_processing(self) -> bool:
        """
        Cancel the current processing operation if possible.
        
        Returns:
            True if cancellation was successful, False otherwise
        """
        # In a real implementation, this would terminate the Demucs process
        # For now, we'll just mark it as cancelled
        if self._current_process:
            try:
                # Terminate the process if it exists
                self._current_process.terminate()
                return True
            except Exception as e:
                logger.error(f"Failed to cancel processing: {e}")
                return False
        return True
    
    def get_supported_formats(self) -> list[str]:
        """
        Get list of audio formats supported by Demucs.
        
        Returns:
            List of supported file extensions
        """
        return ['.mp3', '.wav', '.flac', '.ogg', '.m4a', '.mp4']
    
    def estimate_processing_time(self, audio_duration: float, model_size: ModelSize) -> float:
        """
        Estimate processing time based on audio duration and model size.
        
        Args:
            audio_duration: Duration of audio in seconds
            model_size: Model size being used
            
        Returns:
            Estimated processing time in seconds
        """
        # These are rough estimates based on typical performance
        # Actual times will vary based on hardware
        time_multipliers = {
            ModelSize.TINY: 0.1,    # ~6 seconds for 1 minute of audio
            ModelSize.BASE: 0.2,    # ~12 seconds for 1 minute of audio
            ModelSize.SMALL: 0.2,   # Same as base
            ModelSize.MEDIUM: 0.3,  # ~18 seconds for 1 minute of audio
            ModelSize.LARGE: 0.5    # ~30 seconds for 1 minute of audio
        }
        
        multiplier = time_multipliers.get(model_size, 0.2)
        return audio_duration * multiplier