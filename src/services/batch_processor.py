"""
Batch processing controller for handling multiple audio files.

This module provides the BatchProcessor class that manages queues of audio files,
tracks progress across multiple files, and handles error recovery for failed files.
"""

import os
import logging
import time
from typing import List, Dict, Optional, Callable, Any
from dataclasses import dataclass, field
from enum import Enum
from concurrent.futures import ThreadPoolExecutor, Future
import threading

from ..models.data_models import (
    ProcessingOptions, ProcessingResult, BatchResult, ProcessingStatus,
    AudioFile, AlignmentData, BatchFileReport, BatchSummaryStats
)
from ..services.interfaces import ProcessingError, IAudioProcessor
from ..services.audio_processor import AudioProcessor


logger = logging.getLogger(__name__)


class BatchFileStatus(Enum):
    """Status of individual files in batch processing."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class BatchFileItem:
    """Represents a file in the batch processing queue."""
    file_path: str
    status: BatchFileStatus = BatchFileStatus.PENDING
    result: Optional[ProcessingResult] = None
    error_message: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    
    @property
    def processing_time(self) -> float:
        """Calculate processing time for this file."""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return 0.0


@dataclass
class BatchProcessingState:
    """Current state of batch processing operation."""
    total_files: int = 0
    completed_files: int = 0
    failed_files: int = 0
    current_file_index: int = 0
    current_file_path: Optional[str] = None
    is_active: bool = False
    is_cancelled: bool = False
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    files: List[BatchFileItem] = field(default_factory=list)
    
    @property
    def progress_percentage(self) -> float:
        """Calculate overall progress percentage."""
        if self.total_files == 0:
            return 0.0
        return (self.completed_files + self.failed_files) / self.total_files * 100
    
    @property
    def estimated_time_remaining(self) -> Optional[float]:
        """Estimate remaining processing time based on completed files."""
        if not self.start_time or self.completed_files == 0:
            return None
        
        elapsed_time = time.time() - self.start_time
        avg_time_per_file = elapsed_time / (self.completed_files + self.failed_files)
        remaining_files = self.total_files - self.completed_files - self.failed_files
        
        return avg_time_per_file * remaining_files


class BatchProcessor:
    """
    Manages batch processing of multiple audio files.
    
    This class provides queue management, progress tracking, error handling,
    and continuation for failed files during batch processing operations.
    """
    
    def __init__(self, audio_processor: Optional[IAudioProcessor] = None,
                 max_concurrent_files: int = 1):
        """
        Initialize the BatchProcessor.
        
        Args:
            audio_processor: Audio processor instance for file processing
            max_concurrent_files: Maximum number of files to process concurrently
        """
        self.audio_processor = audio_processor or AudioProcessor()
        self.max_concurrent_files = max_concurrent_files
        self.state = BatchProcessingState()
        self.progress_callback: Optional[Callable[[float, str], None]] = None
        self.file_progress_callback: Optional[Callable[[str, float, str], None]] = None
        self._lock = threading.Lock()
        self._executor: Optional[ThreadPoolExecutor] = None
        self._futures: List[Future] = []
        
        logger.info(f"BatchProcessor initialized with max_concurrent_files={max_concurrent_files}")
    
    def set_progress_callback(self, callback: Callable[[float, str], None]) -> None:
        """
        Set callback for overall batch progress updates.
        
        Args:
            callback: Function to call with (progress_percentage, status_message)
        """
        self.progress_callback = callback
    
    def set_file_progress_callback(self, callback: Callable[[str, float, str], None]) -> None:
        """
        Set callback for individual file progress updates.
        
        Args:
            callback: Function to call with (file_path, progress_percentage, operation)
        """
        self.file_progress_callback = callback
    
    def add_files_to_queue(self, file_paths: List[str]) -> None:
        """
        Add files to the processing queue.
        
        Args:
            file_paths: List of audio file paths to add to queue
            
        Raises:
            ValueError: If files are already being processed
        """
        with self._lock:
            if self.state.is_active:
                raise ValueError("Cannot add files while batch processing is active")
            
            # Validate files exist and are supported
            valid_files = []
            for file_path in file_paths:
                if not os.path.exists(file_path):
                    logger.warning(f"File not found, skipping: {file_path}")
                    continue
                
                try:
                    # Basic validation - let audio processor handle detailed validation
                    if not any(file_path.lower().endswith(ext) for ext in ['.mp3', '.wav', '.flac', '.ogg']):
                        logger.warning(f"Unsupported file format, skipping: {file_path}")
                        continue
                    
                    valid_files.append(file_path)
                except Exception as e:
                    logger.warning(f"Error validating file {file_path}: {e}")
                    continue
            
            # Add valid files to queue
            for file_path in valid_files:
                batch_item = BatchFileItem(file_path=file_path)
                self.state.files.append(batch_item)
            
            self.state.total_files = len(self.state.files)
            logger.info(f"Added {len(valid_files)} files to batch queue (total: {self.state.total_files})")
    
    def clear_queue(self) -> None:
        """Clear the processing queue."""
        with self._lock:
            if self.state.is_active:
                raise ValueError("Cannot clear queue while batch processing is active")
            
            self.state = BatchProcessingState()
            logger.info("Batch processing queue cleared")
    
    def process_batch(self, options: ProcessingOptions) -> BatchResult:
        """
        Process all files in the queue.
        
        Args:
            options: Processing options to apply to all files
            
        Returns:
            BatchResult with processing summary
            
        Raises:
            ValueError: If no files in queue or processing already active
        """
        with self._lock:
            if self.state.is_active:
                raise ValueError("Batch processing is already active")
            
            if self.state.total_files == 0:
                raise ValueError("No files in processing queue")
            
            self.state.is_active = True
            self.state.is_cancelled = False
            self.state.start_time = time.time()
            self.state.completed_files = 0
            self.state.failed_files = 0
            self.state.current_file_index = 0
        
        logger.info(f"Starting batch processing of {self.state.total_files} files")
        
        try:
            # Process files sequentially for now (can be made concurrent later)
            self._process_files_sequentially(options)
            
        except Exception as e:
            logger.error(f"Batch processing failed: {e}")
            self._update_progress("Batch processing failed")
        finally:
            with self._lock:
                self.state.is_active = False
                self.state.end_time = time.time()
        
        result = self._create_batch_result()
        
        # Send completion notification
        self._send_completion_notification(result)
        
        return result
    
    def _process_files_sequentially(self, options: ProcessingOptions) -> None:
        """Process files one by one in sequence."""
        for i, file_item in enumerate(self.state.files):
            if self.state.is_cancelled:
                file_item.status = BatchFileStatus.CANCELLED
                continue
            
            with self._lock:
                self.state.current_file_index = i
                self.state.current_file_path = file_item.file_path
                file_item.status = BatchFileStatus.PROCESSING
                file_item.start_time = time.time()
            
            self._update_progress(f"Processing file {i + 1}/{self.state.total_files}: {os.path.basename(file_item.file_path)}")
            
            try:
                # Set up file-specific progress callback
                def file_progress(progress: float, operation: str):
                    if self.file_progress_callback:
                        self.file_progress_callback(file_item.file_path, progress, operation)
                
                self.audio_processor.set_progress_callback(file_progress)
                
                # Process the file
                result = self._process_single_file(file_item.file_path, options)
                
                with self._lock:
                    file_item.result = result
                    file_item.end_time = time.time()
                    
                    if result.success:
                        file_item.status = BatchFileStatus.COMPLETED
                        self.state.completed_files += 1
                        logger.info(f"Successfully processed: {file_item.file_path}")
                    else:
                        file_item.status = BatchFileStatus.FAILED
                        file_item.error_message = result.error_message
                        self.state.failed_files += 1
                        logger.error(f"Failed to process {file_item.file_path}: {result.error_message}")
                
            except Exception as e:
                with self._lock:
                    file_item.status = BatchFileStatus.FAILED
                    file_item.error_message = str(e)
                    file_item.end_time = time.time()
                    self.state.failed_files += 1
                
                logger.error(f"Exception processing {file_item.file_path}: {e}")
            
            # Update overall progress
            self._update_progress(f"Completed {self.state.completed_files + self.state.failed_files}/{self.state.total_files} files")
    
    def _send_completion_notification(self, result: BatchResult) -> None:
        """Send batch completion notification."""
        if not result.summary_stats:
            result.summary_stats = result.generate_summary_stats()
        
        stats = result.summary_stats
        
        # Create notification message
        if stats.successful_files == stats.total_files:
            message = f"✓ Batch processing completed successfully! All {stats.total_files} files processed."
        elif stats.failed_files == 0:
            message = f"✓ Batch processing completed! {stats.successful_files} files processed, {stats.cancelled_files} cancelled."
        else:
            message = f"⚠ Batch processing completed with {stats.failed_files} failures. {stats.successful_files}/{stats.total_files} files successful."
        
        # Add timing information
        if stats.total_processing_time > 0:
            message += f" Total time: {stats.total_processing_time:.1f}s"
        
        logger.info(f"Batch completion: {message}")
        
        # Call progress callback with completion message
        if self.progress_callback:
            self.progress_callback(100.0, message)
    
    def export_batch_report(self, result: BatchResult, output_dir: str, 
                          formats: List[str] = None) -> List[str]:
        """
        Export batch processing report in specified formats.
        
        Args:
            result: BatchResult to export
            output_dir: Directory to save reports
            formats: List of formats ('txt', 'json'). Defaults to ['txt']
            
        Returns:
            List of exported file paths
        """
        import os
        from datetime import datetime
        
        if formats is None:
            formats = ['txt']
        
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate timestamp for unique filenames
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        exported_files = []
        
        try:
            # Export text report
            if 'txt' in formats:
                txt_path = os.path.join(output_dir, f"batch_report_{timestamp}.txt")
                result.export_summary_report(txt_path)
                exported_files.append(txt_path)
                logger.info(f"Exported text report: {txt_path}")
            
            # Export JSON report
            if 'json' in formats:
                json_path = os.path.join(output_dir, f"batch_report_{timestamp}.json")
                result.export_json_report(json_path)
                exported_files.append(json_path)
                logger.info(f"Exported JSON report: {json_path}")
            
        except Exception as e:
            logger.error(f"Error exporting batch report: {e}")
            raise
        
        return exported_files
    
    def get_batch_summary(self, result: BatchResult = None) -> Dict[str, Any]:
        """
        Get a summary of batch processing results.
        
        Args:
            result: BatchResult to summarize. If None, uses current state.
            
        Returns:
            Dictionary with batch summary information
        """
        if result is None:
            result = self._create_batch_result()
        
        if not result.summary_stats:
            result.summary_stats = result.generate_summary_stats()
        
        stats = result.summary_stats
        
        return {
            "overview": {
                "total_files": stats.total_files,
                "successful_files": stats.successful_files,
                "failed_files": stats.failed_files,
                "cancelled_files": stats.cancelled_files,
                "success_rate": stats.success_rate,
                "failure_rate": stats.failure_rate
            },
            "timing": {
                "total_processing_time": stats.total_processing_time,
                "average_processing_time": stats.average_processing_time,
                "start_time": result.start_time,
                "end_time": result.end_time
            },
            "output": {
                "total_output_files": stats.total_output_files,
                "total_audio_duration": stats.total_audio_duration
            },
            "errors": {
                "validation_errors": stats.validation_errors,
                "processing_errors": stats.processing_errors,
                "export_errors": stats.export_errors,
                "system_errors": stats.system_errors
            },
            "files": [
                {
                    "name": report.file_name,
                    "status": report.status,
                    "success": report.success,
                    "processing_time": report.processing_time,
                    "output_count": len(report.output_files),
                    "error": report.error_message if not report.success else None
                }
                for report in result.file_reports
            ]
        }
    
    def _process_files_sequentially(self, options: ProcessingOptions) -> None:
        """Process files one by one in sequence."""
        for i, file_item in enumerate(self.state.files):
            if self.state.is_cancelled:
                file_item.status = BatchFileStatus.CANCELLED
                continue
            
            with self._lock:
                self.state.current_file_index = i
                self.state.current_file_path = file_item.file_path
                file_item.status = BatchFileStatus.PROCESSING
                file_item.start_time = time.time()
            
            self._update_progress(f"Processing file {i + 1}/{self.state.total_files}: {os.path.basename(file_item.file_path)}")
            
            try:
                # Set up file-specific progress callback
                def file_progress(progress: float, operation: str):
                    if self.file_progress_callback:
                        self.file_progress_callback(file_item.file_path, progress, operation)
                
                self.audio_processor.set_progress_callback(file_progress)
                
                # Process the file
                result = self._process_single_file(file_item.file_path, options)
                
                with self._lock:
                    file_item.result = result
                    file_item.end_time = time.time()
                    
                    if result.success:
                        file_item.status = BatchFileStatus.COMPLETED
                        self.state.completed_files += 1
                        logger.info(f"Successfully processed: {file_item.file_path}")
                    else:
                        file_item.status = BatchFileStatus.FAILED
                        file_item.error_message = result.error_message
                        self.state.failed_files += 1
                        logger.error(f"Failed to process {file_item.file_path}: {result.error_message}")
                
            except Exception as e:
                with self._lock:
                    file_item.status = BatchFileStatus.FAILED
                    file_item.error_message = str(e)
                    file_item.end_time = time.time()
                    self.state.failed_files += 1
                
                logger.error(f"Exception processing {file_item.file_path}: {e}")
            
            # Update overall progress
            self._update_progress(f"Completed {self.state.completed_files + self.state.failed_files}/{self.state.total_files} files")
    
    def _process_single_file(self, file_path: str, options: ProcessingOptions) -> ProcessingResult:
        """
        Process a single audio file.
        
        Args:
            file_path: Path to audio file
            options: Processing options
            
        Returns:
            ProcessingResult for the file
        """
        start_time = time.time()
        
        try:
            # Validate audio file
            audio_file = self.audio_processor.validate_audio_file(file_path)
            
            # Separate vocals
            vocals_path = self.audio_processor.separate_vocals(file_path, options.model_size)
            
            # Transcribe and align
            alignment_data = self.audio_processor.transcribe_with_alignment(vocals_path, options.model_size)
            
            # Generate output files (this would typically be done by subtitle generator)
            output_files = self._generate_output_files(file_path, alignment_data, options)
            
            processing_time = max(time.time() - start_time, 0.001)  # Ensure minimum time for testing
            
            return ProcessingResult(
                success=True,
                output_files=output_files,
                processing_time=processing_time,
                alignment_data=alignment_data
            )
            
        except Exception as e:
            processing_time = max(time.time() - start_time, 0.001)  # Ensure minimum time for testing
            return ProcessingResult(
                success=False,
                output_files=[],
                processing_time=processing_time,
                error_message=str(e)
            )
    
    def _generate_output_files(self, input_path: str, alignment_data: AlignmentData, 
                             options: ProcessingOptions) -> List[str]:
        """
        Generate output subtitle files.
        
        This is a placeholder - in the full implementation, this would use
        the SubtitleGenerator service.
        """
        output_files = []
        base_name = os.path.splitext(os.path.basename(input_path))[0]
        
        for format_type in options.export_formats:
            output_file = os.path.join(options.output_directory, f"{base_name}.{format_type.value}")
            # Normalize path separators for cross-platform compatibility
            output_file = output_file.replace('\\', '/')
            output_files.append(output_file)
        
        return output_files
    
    def cancel_processing(self) -> bool:
        """
        Cancel the current batch processing operation.
        
        Returns:
            True if cancellation was successful
        """
        with self._lock:
            if not self.state.is_active:
                return False
            
            self.state.is_cancelled = True
            logger.info("Batch processing cancellation requested")
        
        # Cancel any running futures
        for future in self._futures:
            future.cancel()
        
        return True
    
    def get_processing_status(self) -> ProcessingStatus:
        """
        Get current processing status.
        
        Returns:
            ProcessingStatus with current state information
        """
        with self._lock:
            return ProcessingStatus(
                is_active=self.state.is_active,
                current_file=self.state.current_file_path,
                progress_percentage=self.state.progress_percentage,
                current_operation=f"Processing file {self.state.current_file_index + 1}/{self.state.total_files}" if self.state.is_active else "Idle",
                estimated_time_remaining=self.state.estimated_time_remaining
            )
    
    def get_queue_status(self) -> Dict[str, Any]:
        """
        Get detailed status of all files in the queue.
        
        Returns:
            Dictionary with queue status information
        """
        with self._lock:
            return {
                "total_files": self.state.total_files,
                "completed_files": self.state.completed_files,
                "failed_files": self.state.failed_files,
                "pending_files": self.state.total_files - self.state.completed_files - self.state.failed_files,
                "is_active": self.state.is_active,
                "is_cancelled": self.state.is_cancelled,
                "progress_percentage": self.state.progress_percentage,
                "estimated_time_remaining": self.state.estimated_time_remaining,
                "files": [
                    {
                        "file_path": item.file_path,
                        "status": item.status.value,
                        "processing_time": item.processing_time,
                        "error_message": item.error_message
                    }
                    for item in self.state.files
                ]
            }
    
    def _create_batch_result(self) -> BatchResult:
        """Create BatchResult from current state with enhanced reporting."""
        from ..models.data_models import BatchFileReport
        import os
        
        processing_results = []
        file_reports = []
        cancelled_count = 0
        
        for file_item in self.state.files:
            if file_item.result:
                processing_results.append(file_item.result)
            else:
                # Create a failed result for files that didn't complete
                processing_results.append(ProcessingResult(
                    success=False,
                    output_files=[],
                    processing_time=file_item.processing_time,
                    error_message=file_item.error_message or "Processing was cancelled or failed"
                ))
            
            # Create detailed file report
            file_report = self._create_file_report(file_item)
            file_reports.append(file_report)
            
            if file_item.status == BatchFileStatus.CANCELLED:
                cancelled_count += 1
        
        total_time = 0.0
        if self.state.start_time and self.state.end_time:
            total_time = self.state.end_time - self.state.start_time
        
        batch_result = BatchResult(
            total_files=self.state.total_files,
            successful_files=self.state.completed_files,
            failed_files=self.state.failed_files,
            processing_results=processing_results,
            total_processing_time=total_time,
            file_reports=file_reports,
            start_time=self.state.start_time,
            end_time=self.state.end_time,
            cancelled_files=cancelled_count
        )
        
        # Generate summary statistics
        batch_result.summary_stats = batch_result.generate_summary_stats()
        
        return batch_result
    
    def _create_file_report(self, file_item: BatchFileItem) -> 'BatchFileReport':
        """Create a detailed report for a single file."""
        from ..models.data_models import BatchFileReport
        import os
        
        # Determine status string
        status_map = {
            BatchFileStatus.COMPLETED: "completed",
            BatchFileStatus.FAILED: "failed",
            BatchFileStatus.CANCELLED: "cancelled",
            BatchFileStatus.PENDING: "pending",
            BatchFileStatus.PROCESSING: "processing"
        }
        
        # Get file information
        file_size = None
        audio_duration = None
        try:
            if os.path.exists(file_item.file_path):
                file_size = os.path.getsize(file_item.file_path)
            
            # Try to get audio duration from result
            if file_item.result and file_item.result.alignment_data:
                audio_duration = file_item.result.alignment_data.audio_duration
        except Exception:
            pass  # Ignore errors getting file info
        
        # Categorize error if present
        error_category = None
        if file_item.error_message:
            error_category = self._categorize_error(file_item.error_message)
        
        # Use processing time from result if available, otherwise from file item
        processing_time = file_item.processing_time
        if file_item.result and file_item.result.processing_time > 0:
            processing_time = file_item.result.processing_time
        
        return BatchFileReport(
            file_path=file_item.file_path,
            file_name=os.path.basename(file_item.file_path),
            status=status_map.get(file_item.status, "unknown"),
            success=file_item.status == BatchFileStatus.COMPLETED,
            processing_time=processing_time,
            output_files=file_item.result.output_files if file_item.result else [],
            error_message=file_item.error_message,
            error_category=error_category,
            file_size=file_size,
            audio_duration=audio_duration
        )
    
    def _categorize_error(self, error_message: str) -> str:
        """Categorize error based on error message content."""
        error_lower = error_message.lower()
        
        # Validation errors
        if any(keyword in error_lower for keyword in [
            'unsupported', 'invalid', 'format', 'corrupt', 'not found', 'validation'
        ]):
            return "validation"
        
        # Processing errors (AI model related)
        elif any(keyword in error_lower for keyword in [
            'model', 'transcription', 'alignment', 'separation', 'whisper', 'demucs'
        ]):
            return "processing"
        
        # Export errors
        elif any(keyword in error_lower for keyword in [
            'export', 'write', 'save', 'output', 'permission', 'disk'
        ]):
            return "export"
        
        # System errors
        elif any(keyword in error_lower for keyword in [
            'memory', 'timeout', 'system', 'resource', 'network'
        ]):
            return "system"
        
        # Default to processing if unclear
        return "processing"
    
    def _update_progress(self, message: str) -> None:
        """Update progress and notify callback."""
        if self.progress_callback:
            self.progress_callback(self.state.progress_percentage, message)
        
        logger.debug(f"Batch progress: {self.state.progress_percentage:.1f}% - {message}")