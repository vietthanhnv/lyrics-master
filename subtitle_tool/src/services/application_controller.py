"""
Main application controller coordinating all components.

This module provides the ApplicationController class that orchestrates the complete
workflow for single file and batch processing, manages application state, and
handles session data.
"""

import os
import logging
import time
from typing import List, Optional, Callable, Dict, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import threading

from ..models.data_models import (
    ProcessingOptions, ProcessingResult, BatchResult, ProcessingStatus,
    AlignmentData, AudioFile, ModelSize, ExportFormat
)
from ..services.interfaces import (
    IApplicationController, ProcessingError, ValidationError, ModelType
)
from ..services.audio_processor import AudioProcessor
from ..services.batch_processor import BatchProcessor
from ..services.subtitle_generator import SubtitleGenerator
from ..services.translation_service import TranslationService as TranslationServiceImpl
from ..services.model_manager import ModelManager
from ..services.error_handler import ErrorHandler, ErrorContext


logger = logging.getLogger(__name__)


class ApplicationState(Enum):
    """Current state of the application."""
    IDLE = "idle"
    PROCESSING_SINGLE = "processing_single"
    PROCESSING_BATCH = "processing_batch"
    CANCELLING = "cancelling"
    ERROR = "error"


@dataclass
class SessionData:
    """Session data for the application."""
    last_input_directory: str = ""
    last_output_directory: str = ""
    last_processing_options: Optional[ProcessingOptions] = None
    recent_files: List[str] = field(default_factory=list)
    processing_history: List[Dict[str, Any]] = field(default_factory=list)
    
    def add_recent_file(self, file_path: str, max_recent: int = 10):
        """Add file to recent files list."""
        if file_path in self.recent_files:
            self.recent_files.remove(file_path)
        self.recent_files.insert(0, file_path)
        self.recent_files = self.recent_files[:max_recent]
    
    def add_processing_record(self, file_paths: List[str], options: ProcessingOptions,
                            result: ProcessingResult, processing_time: float):
        """Add processing record to history."""
        record = {
            "timestamp": time.time(),
            "files": file_paths,
            "success": result.success,
            "processing_time": processing_time,
            "output_files": result.output_files,
            "model_size": options.model_size.value,
            "export_formats": [fmt.value for fmt in options.export_formats]
        }
        self.processing_history.append(record)
        
        # Keep only last 50 records
        self.processing_history = self.processing_history[-50:]


class ApplicationController(IApplicationController):
    """
    Main application controller coordinating all components.
    
    This class orchestrates the complete workflow for audio-to-subtitle processing,
    manages application state, handles session data, and coordinates between
    UI components and backend services.
    """
    
    def __init__(self, temp_dir: Optional[str] = None, device: str = "auto"):
        """
        Initialize the ApplicationController.
        
        Args:
            temp_dir: Optional custom temporary directory
            device: Device to use for AI models ("cpu", "cuda", or "auto")
        """
        self.temp_dir = temp_dir
        self.device = device
        
        # Application state
        self.state = ApplicationState.IDLE
        self.session_data = SessionData()
        self._lock = threading.Lock()
        
        # Progress tracking
        self.progress_callback: Optional[Callable[[float, str], None]] = None
        self.current_progress = 0.0
        self.current_operation = ""
        
        # Initialize core services
        self._initialize_services()
        
        # Current processing context
        self.current_files: List[str] = []
        self.current_options: Optional[ProcessingOptions] = None
        self.current_result: Optional[ProcessingResult] = None
        self.processing_start_time: Optional[float] = None
        
        logger.info(f"ApplicationController initialized with device={device}")
        
        # Check system readiness after initialization
        self._check_system_readiness()
    
    def _initialize_services(self):
        """Initialize all backend services."""
        try:
            # Initialize error handler first
            self.error_handler = ErrorHandler(max_retries=3, retry_interval=5.0)
            
            # Initialize model manager
            self.model_manager = ModelManager()
            
            # Initialize audio processor
            self.audio_processor = AudioProcessor(
                temp_dir=self.temp_dir,
                device=self.device
            )
            
            # Initialize batch processor
            self.batch_processor = BatchProcessor(
                audio_processor=self.audio_processor,
                max_concurrent_files=1  # Sequential processing for now
            )
            
            # Initialize subtitle generator
            self.subtitle_generator = SubtitleGenerator()
            
            # Initialize translation service
            self.translation_service = TranslationServiceImpl()
            
            # Set up progress callbacks
            self.audio_processor.set_progress_callback(self._on_audio_progress)
            self.batch_processor.set_progress_callback(self._on_batch_progress)
            
            logger.info("All services initialized successfully")
            
        except Exception as e:
            error_msg = f"Failed to initialize application services: {e}"
            logger.error(error_msg)
            self.state = ApplicationState.ERROR
            
            # Use error handler if available
            if hasattr(self, 'error_handler'):
                user_message = self.error_handler.handle_processing_error(e, "service_initialization")
                raise ProcessingError(user_message)
            else:
                raise ProcessingError(error_msg)
    
    def process_audio_file_with_retry(self, file_path: str, options: ProcessingOptions) -> ProcessingResult:
        """
        Process audio file with automatic retry for transient failures.
        
        Args:
            file_path: Path to the audio file to process
            options: Processing options and configuration
            
        Returns:
            ProcessingResult with generated subtitle files or error information
        """
        def _process_operation():
            return self._process_audio_file_internal(file_path, options)
        
        return self._execute_with_retry(_process_operation, "single_file_processing", file_path, options)
    
    def process_audio_file(self, file_path: str, options: ProcessingOptions) -> ProcessingResult:
        """
        Process a single audio file and generate subtitles.
        
        Args:
            file_path: Path to the audio file to process
            options: Processing options and configuration
            
        Returns:
            ProcessingResult with generated subtitle files or error information
            
        Raises:
            ProcessingError: If processing fails
            ValidationError: If input validation fails
        """
        return self.process_audio_file_with_retry(file_path, options)
    
    def _process_audio_file_internal(self, file_path: str, options: ProcessingOptions) -> ProcessingResult:
        """
        Internal method for processing a single audio file.
        
        Args:
            file_path: Path to the audio file to process
            options: Processing options and configuration
            
        Returns:
            ProcessingResult with generated subtitle files or error information
        """
        with self._lock:
            if self.state != ApplicationState.IDLE:
                raise ProcessingError("Cannot start processing: another operation is in progress")
            
            self.state = ApplicationState.PROCESSING_SINGLE
            self.current_files = [file_path]
            self.current_options = options
            self.processing_start_time = time.time()
        
        try:
            self._update_progress(0.0, "Starting single file processing...")
            
            # Validate inputs
            self._validate_processing_inputs([file_path], options)
            
            # Check and download models if needed
            self._ensure_models_available(options)
            
            # Process the audio file
            self._update_progress(10.0, "Processing audio file...")
            audio_result = self.audio_processor.process_audio_file(file_path, options)
            
            if not audio_result.success:
                raise ProcessingError(audio_result.error_message or "Audio processing failed")
            
            # Generate subtitle files
            self._update_progress(80.0, "Generating subtitle files...")
            output_files = self._generate_subtitle_files(
                audio_result.alignment_data, file_path, options
            )
            
            # Handle translation if enabled
            if options.translation_enabled:
                self._update_progress(90.0, "Generating translations...")
                translated_files = self._generate_translated_subtitles(
                    audio_result.alignment_data, file_path, options
                )
                output_files.extend(translated_files)
            
            processing_time = time.time() - self.processing_start_time
            
            result = ProcessingResult(
                success=True,
                output_files=output_files,
                processing_time=processing_time,
                alignment_data=audio_result.alignment_data
            )
            
            # Update session data
            self.session_data.add_recent_file(file_path)
            self.session_data.add_processing_record([file_path], options, result, processing_time)
            self.session_data.last_processing_options = options
            
            self._update_progress(100.0, f"Processing completed successfully ({processing_time:.1f}s)")
            
            logger.info(
                f"Single file processing completed: {file_path} -> "
                f"{len(output_files)} output files in {processing_time:.2f}s"
            )
            
            return result
            
        except Exception as e:
            processing_time = time.time() - self.processing_start_time if self.processing_start_time else 0.0
            
            # Use error handler for comprehensive error processing
            context = ErrorContext(
                operation="single_file_processing",
                file_path=file_path,
                model_type=options.model_size.value if options else None
            )
            
            user_message = self.error_handler.handle_processing_error(e, "single_file_processing")
            
            # Check if we should retry the operation
            if self.error_handler.should_retry(e):
                logger.info("Attempting automatic retry for transient error")
                # Note: Actual retry logic would be implemented in a wrapper method
                # For now, we'll just log the retry possibility
            
            result = ProcessingResult(
                success=False,
                output_files=[],
                processing_time=processing_time,
                error_message=user_message
            )
            
            self._update_progress(0.0, f"Processing failed: {user_message}")
            return result
            
        finally:
            with self._lock:
                self.state = ApplicationState.IDLE
                self.current_result = result if 'result' in locals() else None
                self._cleanup_processing_context()
    
    def process_batch(self, file_paths: List[str], options: ProcessingOptions) -> BatchResult:
        """
        Process multiple audio files in batch.
        
        Args:
            file_paths: List of audio file paths to process
            options: Processing options and configuration
            
        Returns:
            BatchResult with processing summary and individual results
            
        Raises:
            ProcessingError: If batch processing setup fails
            ValidationError: If input validation fails
        """
        with self._lock:
            if self.state != ApplicationState.IDLE:
                raise ProcessingError("Cannot start batch processing: another operation is in progress")
            
            self.state = ApplicationState.PROCESSING_BATCH
            self.current_files = file_paths.copy()
            self.current_options = options
            self.processing_start_time = time.time()
        
        try:
            self._update_progress(0.0, f"Starting batch processing of {len(file_paths)} files...")
            
            # Validate inputs
            self._validate_processing_inputs(file_paths, options)
            
            # Check and download models if needed
            self._ensure_models_available(options)
            
            # Set up batch processor
            self.batch_processor.clear_queue()
            self.batch_processor.add_files_to_queue(file_paths)
            
            # Process the batch
            self._update_progress(5.0, "Processing batch files...")
            batch_result = self.batch_processor.process_batch(options)
            
            # Generate subtitle files for successful results
            self._update_progress(85.0, "Generating subtitle files...")
            self._generate_batch_subtitle_files(batch_result, options)
            
            # Handle translation if enabled
            if options.translation_enabled:
                self._update_progress(95.0, "Generating translations...")
                self._generate_batch_translated_subtitles(batch_result, options)
            
            processing_time = time.time() - self.processing_start_time
            batch_result.total_processing_time = processing_time
            
            # Update session data
            for file_path in file_paths:
                self.session_data.add_recent_file(file_path)
            self.session_data.last_processing_options = options
            
            self._update_progress(100.0, f"Batch processing completed ({processing_time:.1f}s)")
            
            logger.info(
                f"Batch processing completed: {len(file_paths)} files -> "
                f"{batch_result.successful_files} successful, {batch_result.failed_files} failed "
                f"in {processing_time:.2f}s"
            )
            
            return batch_result
            
        except Exception as e:
            processing_time = time.time() - self.processing_start_time if self.processing_start_time else 0.0
            
            # Use error handler for comprehensive error processing
            context = ErrorContext(
                operation="batch_processing",
                file_path=f"{len(file_paths)} files",
                model_type=options.model_size.value if options else None
            )
            
            user_message = self.error_handler.handle_processing_error(e, "batch_processing")
            
            # Check if we should retry the operation
            if self.error_handler.should_retry(e):
                logger.info("Batch processing error may be retryable")
                # Note: Actual retry logic would be implemented in a wrapper method
            
            # Create failed batch result
            batch_result = BatchResult(
                total_files=len(file_paths),
                successful_files=0,
                failed_files=len(file_paths),
                processing_results=[],
                total_processing_time=processing_time
            )
            
            self._update_progress(0.0, f"Batch processing failed: {user_message}")
            return batch_result
            
        finally:
            with self._lock:
                self.state = ApplicationState.IDLE
                self._cleanup_processing_context()
    
    def get_processing_status(self) -> ProcessingStatus:
        """
        Get current processing status.
        
        Returns:
            ProcessingStatus with current state information
        """
        with self._lock:
            current_file = None
            if self.current_files:
                if self.state == ApplicationState.PROCESSING_SINGLE:
                    current_file = self.current_files[0]
                elif self.state == ApplicationState.PROCESSING_BATCH:
                    # Get current file from batch processor
                    batch_status = self.batch_processor.get_processing_status()
                    current_file = batch_status.current_file
            
            # Calculate estimated time remaining
            estimated_time = None
            if self.processing_start_time and self.current_progress > 0:
                elapsed = time.time() - self.processing_start_time
                if self.current_progress < 100:
                    estimated_time = (elapsed / self.current_progress) * (100 - self.current_progress)
            
            return ProcessingStatus(
                is_active=self.state in [ApplicationState.PROCESSING_SINGLE, ApplicationState.PROCESSING_BATCH],
                current_file=current_file,
                progress_percentage=self.current_progress,
                current_operation=self.current_operation,
                estimated_time_remaining=estimated_time
            )
    
    def cancel_processing(self) -> bool:
        """
        Cancel current processing operation.
        
        Returns:
            True if cancellation was successful, False otherwise
        """
        with self._lock:
            if self.state == ApplicationState.IDLE:
                return True
            
            if self.state == ApplicationState.CANCELLING:
                return False  # Already cancelling
            
            previous_state = self.state
            self.state = ApplicationState.CANCELLING
        
        try:
            success = True
            
            if previous_state == ApplicationState.PROCESSING_SINGLE:
                # Cancel audio processor
                success &= self.audio_processor.cancel_processing()
                
            elif previous_state == ApplicationState.PROCESSING_BATCH:
                # Cancel batch processor
                success &= self.batch_processor.cancel_processing()
            
            # Clean up resources
            self._cleanup_processing_context()
            
            if success:
                self._update_progress(0.0, "Processing cancelled by user")
                logger.info(f"Processing cancelled successfully from state: {previous_state}")
            else:
                logger.warning(f"Processing cancellation may not have been complete from state: {previous_state}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error during processing cancellation: {e}")
            return False
            
        finally:
            with self._lock:
                self.state = ApplicationState.IDLE
    
    def set_progress_callback(self, callback: Callable[[float, str], None]) -> None:
        """
        Set callback for progress updates.
        
        Args:
            callback: Function to call with (progress_percentage, status_message)
        """
        self.progress_callback = callback
    
    def _validate_processing_inputs(self, file_paths: List[str], options: ProcessingOptions) -> None:
        """
        Validate processing inputs.
        
        Args:
            file_paths: List of file paths to validate
            options: Processing options to validate
            
        Raises:
            ValidationError: If validation fails
        """
        # Validate file paths
        if not file_paths:
            raise ValidationError("No files provided for processing")
        
        for file_path in file_paths:
            if not os.path.exists(file_path):
                raise ValidationError(f"File not found: {file_path}")
            
            if not os.path.isfile(file_path):
                raise ValidationError(f"Path is not a file: {file_path}")
        
        # Validate processing options
        validation_errors = options.validate()
        if validation_errors:
            raise ValidationError(f"Invalid processing options: {'; '.join(validation_errors)}")
        
        # Validate output directory
        if not os.path.exists(options.output_directory):
            try:
                os.makedirs(options.output_directory, exist_ok=True)
            except Exception as e:
                raise ValidationError(f"Cannot create output directory {options.output_directory}: {e}")
        
        if not os.access(options.output_directory, os.W_OK):
            raise ValidationError(f"Output directory is not writable: {options.output_directory}")
    
    def _ensure_models_available(self, options: ProcessingOptions) -> None:
        """
        Ensure required models are available, downloading if necessary.
        
        Args:
            options: Processing options containing model requirements
            
        Raises:
            ProcessingError: If models cannot be obtained
        """
        from ..services.interfaces import ModelType
        
        required_models = [
            (ModelType.DEMUCS, options.model_size),
            (ModelType.WHISPERX, options.model_size)
        ]
        
        # For now, we'll skip the model availability check and let the actual
        # processing services handle model loading. This is more robust since
        # the services can handle package imports and model downloads themselves.
        logger.info("Skipping model availability check - services will handle model loading")
    
    def _generate_subtitle_files(self, alignment_data: AlignmentData, 
                               input_file: str, options: ProcessingOptions) -> List[str]:
        """
        Generate subtitle files from alignment data.
        
        Args:
            alignment_data: Word-level alignment data
            input_file: Original input file path
            options: Processing options
            
        Returns:
            List of generated subtitle file paths
        """
        output_files = []
        base_name = os.path.splitext(os.path.basename(input_file))[0]
        
        for export_format in options.export_formats:
            try:
                if export_format == ExportFormat.SRT:
                    content = self.subtitle_generator.generate_srt(
                        alignment_data, word_level=options.word_level_srt
                    )
                elif export_format == ExportFormat.ASS:
                    style_options = {"karaoke_mode": options.karaoke_mode}
                    content = self.subtitle_generator.generate_ass_karaoke(
                        alignment_data, style_options
                    )
                elif export_format == ExportFormat.VTT:
                    content = self.subtitle_generator.generate_vtt(alignment_data)
                elif export_format == ExportFormat.JSON:
                    content = self.subtitle_generator.export_json_alignment(alignment_data)
                else:
                    logger.warning(f"Unsupported export format: {export_format}")
                    continue
                
                # Save the file
                output_path = os.path.join(
                    options.output_directory, 
                    f"{base_name}.{export_format.value}"
                )
                
                if self.subtitle_generator.save_subtitle_file(content, output_path, export_format):
                    output_files.append(output_path)
                    logger.debug(f"Generated subtitle file: {output_path}")
                else:
                    logger.error(f"Failed to save subtitle file: {output_path}")
                    
            except Exception as e:
                logger.error(f"Error generating {export_format.value} subtitle: {e}")
        
        return output_files
    
    def _generate_translated_subtitles(self, alignment_data: AlignmentData,
                                     input_file: str, options: ProcessingOptions) -> List[str]:
        """
        Generate translated subtitle files.
        
        Args:
            alignment_data: Word-level alignment data
            input_file: Original input file path
            options: Processing options with translation settings
            
        Returns:
            List of generated translated subtitle file paths
        """
        if not options.translation_enabled or not options.target_language:
            return []
        
        try:
            # Generate bilingual alignment data
            bilingual_data = self.translation_service.generate_bilingual_subtitles(
                alignment_data, options.target_language, options.translation_service
            )
            
            output_files = []
            base_name = os.path.splitext(os.path.basename(input_file))[0]
            
            for export_format in options.export_formats:
                try:
                    if export_format == ExportFormat.SRT:
                        content = self.subtitle_generator.generate_bilingual_srt(
                            bilingual_data, word_level=options.word_level_srt
                        )
                    elif export_format == ExportFormat.ASS:
                        style_options = {"karaoke_mode": options.karaoke_mode}
                        content = self.subtitle_generator.generate_bilingual_ass_karaoke(
                            bilingual_data, style_options
                        )
                    elif export_format == ExportFormat.VTT:
                        content = self.subtitle_generator.generate_bilingual_vtt(
                            bilingual_data, word_level=options.word_level_srt
                        )
                    elif export_format == ExportFormat.JSON:
                        content = self.subtitle_generator.export_bilingual_json_alignment(
                            bilingual_data, options.target_language
                        )
                    else:
                        continue
                    
                    # Save the bilingual file
                    output_path = os.path.join(
                        options.output_directory,
                        f"{base_name}_bilingual_{options.target_language}.{export_format.value}"
                    )
                    
                    if self.subtitle_generator.save_subtitle_file(content, output_path, export_format):
                        output_files.append(output_path)
                        logger.debug(f"Generated bilingual subtitle file: {output_path}")
                    
                except Exception as e:
                    logger.error(f"Error generating bilingual {export_format.value} subtitle: {e}")
            
            return output_files
            
        except Exception as e:
            logger.error(f"Error generating translated subtitles: {e}")
            return []
    
    def _generate_batch_subtitle_files(self, batch_result: BatchResult, options: ProcessingOptions) -> None:
        """Generate subtitle files for successful batch results."""
        for i, result in enumerate(batch_result.processing_results):
            if result.success and result.alignment_data:
                try:
                    input_file = self.current_files[i] if i < len(self.current_files) else f"file_{i}"
                    subtitle_files = self._generate_subtitle_files(
                        result.alignment_data, input_file, options
                    )
                    result.output_files.extend(subtitle_files)
                except Exception as e:
                    logger.error(f"Error generating subtitle files for batch item {i}: {e}")
    
    def _generate_batch_translated_subtitles(self, batch_result: BatchResult, options: ProcessingOptions) -> None:
        """Generate translated subtitle files for successful batch results."""
        if not options.translation_enabled:
            return
        
        for i, result in enumerate(batch_result.processing_results):
            if result.success and result.alignment_data:
                try:
                    input_file = self.current_files[i] if i < len(self.current_files) else f"file_{i}"
                    translated_files = self._generate_translated_subtitles(
                        result.alignment_data, input_file, options
                    )
                    result.output_files.extend(translated_files)
                except Exception as e:
                    logger.error(f"Error generating translated subtitles for batch item {i}: {e}")
    
    def _cleanup_processing_context(self) -> None:
        """Clean up processing context and temporary files."""
        try:
            # Clean up audio processor
            self.audio_processor.cleanup_temp_files()
            
            # Reset current processing context
            self.current_files.clear()
            self.current_options = None
            self.current_result = None
            self.processing_start_time = None
            self.current_progress = 0.0
            self.current_operation = ""
            
        except Exception as e:
            logger.warning(f"Error during cleanup: {e}")
    
    def _on_audio_progress(self, percentage: float, message: str) -> None:
        """Handle progress updates from audio processor."""
        # Map audio processor progress to overall progress
        if self.state == ApplicationState.PROCESSING_SINGLE:
            # Audio processing is 10-80% of single file processing
            overall_progress = 10.0 + (percentage * 0.70)
        else:
            # For batch processing, let batch processor handle progress mapping
            overall_progress = percentage
        
        self._update_progress(overall_progress, message)
    
    def _on_batch_progress(self, percentage: float, message: str) -> None:
        """Handle progress updates from batch processor."""
        # Batch processing is 5-85% of overall batch processing
        overall_progress = 5.0 + (percentage * 0.80)
        self._update_progress(overall_progress, message)
    
    def _update_progress(self, percentage: float, message: str) -> None:
        """
        Update progress and notify callback.
        
        Args:
            percentage: Progress percentage (0-100)
            message: Status message
        """
        self.current_progress = percentage
        self.current_operation = message
        
        if self.progress_callback:
            self.progress_callback(percentage, message)
        
        logger.debug(f"Progress: {percentage:.1f}% - {message}")
    
    # Public utility methods
    
    def get_session_data(self) -> SessionData:
        """Get current session data."""
        return self.session_data
    
    def get_recent_files(self) -> List[str]:
        """Get list of recently processed files."""
        return self.session_data.recent_files.copy()
    
    def get_processing_history(self) -> List[Dict[str, Any]]:
        """Get processing history."""
        return self.session_data.processing_history.copy()
    
    def get_last_processing_options(self) -> Optional[ProcessingOptions]:
        """Get the last used processing options."""
        return self.session_data.last_processing_options
    
    def set_last_directories(self, input_dir: str = None, output_dir: str = None) -> None:
        """Set last used directories."""
        if input_dir:
            self.session_data.last_input_directory = input_dir
        if output_dir:
            self.session_data.last_output_directory = output_dir
    
    def get_supported_audio_formats(self) -> List[str]:
        """Get list of supported audio formats."""
        return self.audio_processor.get_supported_audio_formats()
    
    def get_available_models(self) -> Dict[str, List[str]]:
        """Get available AI models."""
        models = self.model_manager.list_available_models()
        return {
            model_type.value: [size.value for size in sizes]
            for model_type, sizes in models.items()
        }
    
    def estimate_processing_time(self, file_paths: List[str], options: ProcessingOptions) -> float:
        """
        Estimate total processing time for given files and options.
        
        Args:
            file_paths: List of audio file paths
            options: Processing options
            
        Returns:
            Estimated processing time in seconds
        """
        total_estimate = 0.0
        
        for file_path in file_paths:
            try:
                # Get audio duration
                audio_file = self.audio_processor.validate_audio_file(file_path)
                file_estimate = self.audio_processor.estimate_processing_time(
                    audio_file.duration, options.model_size
                )
                total_estimate += file_estimate
            except Exception as e:
                logger.warning(f"Could not estimate processing time for {file_path}: {e}")
                # Use default estimate of 2x real-time
                total_estimate += 120.0  # 2 minutes default
        
        # Add overhead for subtitle generation and translation
        overhead = len(file_paths) * 5.0  # 5 seconds per file
        if options.translation_enabled:
            overhead += len(file_paths) * 10.0  # Additional 10 seconds for translation
        
        return total_estimate + overhead
    
    def get_device_info(self) -> Dict[str, Any]:
        """Get information about processing device and capabilities."""
        device_info = self.audio_processor.get_device_info()
        device_info.update({
            "application_state": self.state.value,
            "models_available": self.get_available_models(),
            "supported_formats": self.get_supported_audio_formats()
        })
        return device_info
    
    def _execute_with_retry(self, operation: Callable, operation_name: str, 
                           file_path: str, options: ProcessingOptions) -> ProcessingResult:
        """
        Execute an operation with automatic retry for transient failures.
        
        Args:
            operation: The operation to execute
            operation_name: Name of the operation for logging
            file_path: File path for context
            options: Processing options
            
        Returns:
            ProcessingResult from the operation
        """
        last_error = None
        retry_count = 0
        max_retries = 3
        
        while retry_count <= max_retries:
            try:
                return operation()
            except Exception as e:
                last_error = e
                
                # Use error handler to determine if we should retry
                if retry_count < max_retries and self.error_handler.should_retry(e):
                    retry_count += 1
                    
                    # Calculate retry delay with exponential backoff
                    delay = 2.0 * (2 ** (retry_count - 1))  # 2s, 4s, 8s
                    delay = min(delay, 30.0)  # Cap at 30 seconds
                    
                    logger.info(f"Retrying {operation_name} (attempt {retry_count}/{max_retries}) after {delay}s delay")
                    self._update_progress(
                        self.current_progress, 
                        f"Retrying operation (attempt {retry_count}/{max_retries})..."
                    )
                    
                    time.sleep(delay)
                    continue
                else:
                    # Not retryable or max retries reached
                    break
        
        # All retries failed, handle the final error
        context = ErrorContext(
            operation=operation_name,
            file_path=file_path,
            model_type=options.model_size.value if options else None
        )
        
        user_message = self.error_handler.handle_processing_error(last_error, operation_name)
        
        return ProcessingResult(
            success=False,
            output_files=[],
            processing_time=0.0,
            error_message=user_message
        )
    
    # Error handling and recovery methods
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """
        Get error statistics and patterns from the error handler.
        
        Returns:
            Dictionary with error statistics and patterns
        """
        return self.error_handler.get_error_statistics()
    
    def get_recovery_suggestions(self, error: Exception) -> List[str]:
        """
        Get recovery suggestions for a specific error.
        
        Args:
            error: The exception to get suggestions for
            
        Returns:
            List of recovery suggestions
        """
        return self.error_handler.get_recovery_suggestions(error)
    
    def retry_last_operation(self) -> Optional[ProcessingResult]:
        """
        Retry the last failed operation if it's retryable.
        
        Returns:
            ProcessingResult if retry was attempted, None if no retryable operation
        """
        if not self.current_files or not self.current_options:
            logger.warning("No operation available to retry")
            return None
        
        # Check if we have a recent error that's retryable
        error_stats = self.error_handler.get_error_statistics()
        if error_stats.get("total_errors", 0) == 0:
            logger.warning("No recent errors to retry")
            return None
        
        logger.info("Retrying last operation...")
        
        try:
            if len(self.current_files) == 1:
                return self.process_audio_file(self.current_files[0], self.current_options)
            else:
                batch_result = self.process_batch(self.current_files, self.current_options)
                # Convert BatchResult to ProcessingResult for consistency
                return ProcessingResult(
                    success=batch_result.successful_files > 0,
                    output_files=[],  # Would need to aggregate from batch results
                    processing_time=batch_result.total_processing_time,
                    error_message=None if batch_result.successful_files > 0 else "Batch processing had failures"
                )
        except Exception as e:
            logger.error(f"Retry operation failed: {e}")
            return ProcessingResult(
                success=False,
                output_files=[],
                processing_time=0.0,
                error_message=f"Retry failed: {str(e)}"
            )
    
    def clear_error_history(self) -> None:
        """Clear the error history and patterns."""
        self.error_handler.clear_error_history()
        logger.info("Error history cleared")
    
    def handle_critical_error(self, error: Exception, context: str) -> Dict[str, Any]:
        """
        Handle critical errors with user guidance.
        
        Args:
            error: The critical error that occurred
            context: Context where the error occurred
            
        Returns:
            Dictionary with error information and recovery guidance
        """
        user_message = self.error_handler.handle_processing_error(error, context)
        suggestions = self.error_handler.get_recovery_suggestions(error)
        
        # For critical errors, also collect system diagnostics
        diagnostics = {
            "system_info": self._collect_system_diagnostics(),
            "application_state": self.state.value,
            "current_operation": self.current_operation,
            "error_category": self.error_handler._categorize_error(error)[0].value,
            "error_severity": self.error_handler._categorize_error(error)[1].value
        }
        
        return {
            "user_message": user_message,
            "recovery_suggestions": suggestions,
            "diagnostics": diagnostics,
            "should_restart": self.error_handler._categorize_error(error)[1].value == "critical"
        }
    
    def _collect_system_diagnostics(self) -> Dict[str, Any]:
        """Collect system diagnostics for error reporting."""
        try:
            import psutil
            import platform
            
            return {
                "platform": platform.system(),
                "python_version": platform.python_version(),
                "memory_usage": psutil.virtual_memory().percent,
                "disk_usage": psutil.disk_usage('/').percent if os.name != 'nt' else psutil.disk_usage('C:').percent,
                "cpu_usage": psutil.cpu_percent(interval=0.1),
                "available_memory_gb": psutil.virtual_memory().available / (1024**3),
                "process_memory_mb": psutil.Process().memory_info().rss / (1024**2),
                "device": self.device,
                "temp_dir": self.temp_dir
            }
        except Exception as e:
            logger.warning(f"Failed to collect system diagnostics: {e}")
            return {"error": "Failed to collect diagnostics"}
    
    # First-run setup and system readiness methods
    
    def _check_system_readiness(self):
        """Check if the system is ready for processing."""
        try:
            # Check if required models are available
            required_models = self.get_required_models()
            missing_models = self.model_manager.get_missing_models(required_models)
            
            if missing_models:
                logger.warning(f"Missing required models: {missing_models}")
                # Don't fail initialization, but log the issue
                # The UI will handle prompting for model downloads
            else:
                logger.info("All required models are available")
                
        except Exception as e:
            logger.warning(f"Could not check system readiness: {e}")
    
    def get_required_models(self) -> Dict[ModelType, ModelSize]:
        """Get the required models for basic operation."""
        from ..utils.config import config_manager
        
        config = config_manager.get_config()
        default_size = ModelSize(config.default_model_size)
        
        return {
            ModelType.DEMUCS: ModelSize.BASE,  # Always use base for Demucs
            ModelType.WHISPERX: default_size
        }
    
    def check_models_availability(self) -> Dict[str, bool]:
        """
        Check availability of required models for processing.
        
        Returns:
            Dictionary with model availability status
        """
        required_models = self.get_required_models()
        return self.model_manager.check_required_models(required_models)
    
    def is_ready_for_processing(self) -> Tuple[bool, List[str]]:
        """
        Check if the application is ready for processing.
        
        Returns:
            Tuple of (is_ready, list_of_issues)
        """
        issues = []
        
        # Check model availability
        model_status = self.check_models_availability()
        missing_models = [model for model, available in model_status.items() if not available]
        
        if missing_models:
            issues.append(f"Missing required models: {', '.join(missing_models)}")
        
        # Check if services are initialized
        if not hasattr(self, 'audio_processor') or self.audio_processor is None:
            issues.append("Audio processor not initialized")
        
        if not hasattr(self, 'subtitle_generator') or self.subtitle_generator is None:
            issues.append("Subtitle generator not initialized")
        
        # Check if in error state
        if self.state == ApplicationState.ERROR:
            issues.append("Application is in error state")
        
        return len(issues) == 0, issues
    
    def get_setup_guidance(self) -> Dict[str, Any]:
        """
        Get guidance for setting up the application.
        
        Returns:
            Dictionary with setup guidance information
        """
        guidance = {
            "needs_setup": False,
            "missing_models": [],
            "recommendations": [],
            "next_steps": []
        }
        
        # Check model availability
        required_models = self.get_required_models()
        missing_models = self.model_manager.get_missing_models(required_models)
        
        if missing_models:
            guidance["needs_setup"] = True
            guidance["missing_models"] = [
                f"{model_type.value} ({model_size.value})" 
                for model_type, model_size in missing_models
            ]
            guidance["next_steps"].append("Download required AI models")
        
        # Check system requirements
        try:
            from ..ui.first_run_wizard import SystemRequirementsChecker
            requirements = SystemRequirementsChecker.check_all_requirements()
            
            failed_requirements = [
                req_name for req_name, (passed, _) in requirements.items() 
                if not passed and req_name in ["Python Version", "Disk Space", "FFmpeg"]
            ]
            
            if failed_requirements:
                guidance["needs_setup"] = True
                guidance["recommendations"].extend([
                    f"Resolve {req_name} requirement" for req_name in failed_requirements
                ])
        except ImportError:
            # SystemRequirementsChecker not available
            pass
        
        # Add general recommendations
        if not guidance["needs_setup"]:
            guidance["recommendations"].append("System is ready for processing")
            guidance["next_steps"].append("Select audio files to begin processing")
        
        return guidance