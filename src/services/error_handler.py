"""
Error handling and recovery mechanisms for the lyric-to-subtitle application.

This module provides comprehensive error handling with categorized error processing,
automatic retry logic for transient failures, and user-guided recovery for critical errors.
"""

import logging
import time
import traceback
from typing import Dict, List, Optional, Callable, Any, Tuple
from enum import Enum
from dataclasses import dataclass, field
import os
import psutil
import threading

from .interfaces import IErrorHandler, ProcessingError, ModelError, ValidationError


logger = logging.getLogger(__name__)


class ErrorCategory(Enum):
    """Categories of errors for better handling and recovery."""
    VALIDATION = "validation"
    PROCESSING = "processing"
    MODEL = "model"
    NETWORK = "network"
    SYSTEM = "system"
    EXPORT = "export"
    UNKNOWN = "unknown"


class ErrorSeverity(Enum):
    """Severity levels for errors."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ErrorContext:
    """Context information for error handling."""
    operation: str
    file_path: Optional[str] = None
    model_type: Optional[str] = None
    model_size: Optional[str] = None
    timestamp: float = field(default_factory=time.time)
    thread_id: str = field(default_factory=lambda: str(threading.current_thread().ident))
    system_info: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.system_info:
            self.system_info = self._collect_system_info()
    
    def _collect_system_info(self) -> Dict[str, Any]:
        """Collect relevant system information for error context."""
        try:
            return {
                "memory_usage": psutil.virtual_memory().percent,
                "disk_usage": psutil.disk_usage('/').percent if os.name != 'nt' else psutil.disk_usage('C:').percent,
                "cpu_usage": psutil.cpu_percent(interval=0.1),
                "available_memory_gb": psutil.virtual_memory().available / (1024**3),
                "process_memory_mb": psutil.Process().memory_info().rss / (1024**2)
            }
        except Exception:
            return {}


@dataclass
class ErrorRecord:
    """Record of an error occurrence."""
    error: Exception
    category: ErrorCategory
    severity: ErrorSeverity
    context: ErrorContext
    user_message: str
    recovery_suggestions: List[str]
    retry_count: int = 0
    max_retries: int = 3
    last_retry_time: Optional[float] = None
    resolved: bool = False
    
    def can_retry(self) -> bool:
        """Check if error can be retried."""
        return self.retry_count < self.max_retries and not self.resolved
    
    def should_retry_now(self, min_retry_interval: float = 5.0) -> bool:
        """Check if enough time has passed for retry."""
        if not self.can_retry():
            return False
        
        if self.last_retry_time is None:
            return True
        
        return time.time() - self.last_retry_time >= min_retry_interval


class ErrorHandler(IErrorHandler):
    """
    Comprehensive error handler with categorized processing and recovery mechanisms.
    
    This class provides:
    - Categorized error processing for different types of failures
    - Automatic retry logic for transient failures
    - User-guided recovery suggestions for critical errors
    - Error logging and tracking
    """
    
    def __init__(self, max_retries: int = 3, retry_interval: float = 5.0):
        """
        Initialize the ErrorHandler.
        
        Args:
            max_retries: Maximum number of automatic retries for transient errors
            retry_interval: Minimum interval between retries in seconds
        """
        self.max_retries = max_retries
        self.retry_interval = retry_interval
        self.error_history: List[ErrorRecord] = []
        self.error_patterns: Dict[str, int] = {}
        self._lock = threading.Lock()
        
        # Error categorization patterns
        self._error_patterns = self._initialize_error_patterns()
        
        # Recovery callbacks
        self.recovery_callbacks: Dict[ErrorCategory, List[Callable]] = {
            category: [] for category in ErrorCategory
        }
        
        logger.info(f"ErrorHandler initialized with max_retries={max_retries}, retry_interval={retry_interval}")
    
    def _initialize_error_patterns(self) -> Dict[str, Tuple[ErrorCategory, ErrorSeverity]]:
        """Initialize error pattern matching for categorization."""
        return {
            # Validation errors
            "file not found": (ErrorCategory.VALIDATION, ErrorSeverity.MEDIUM),
            "invalid file format": (ErrorCategory.VALIDATION, ErrorSeverity.MEDIUM),
            "unsupported format": (ErrorCategory.VALIDATION, ErrorSeverity.MEDIUM),
            "permission denied": (ErrorCategory.VALIDATION, ErrorSeverity.HIGH),
            "directory not writable": (ErrorCategory.VALIDATION, ErrorSeverity.HIGH),
            
            # Processing errors
            "vocal separation failed": (ErrorCategory.PROCESSING, ErrorSeverity.HIGH),
            "transcription failed": (ErrorCategory.PROCESSING, ErrorSeverity.HIGH),
            "alignment failed": (ErrorCategory.PROCESSING, ErrorSeverity.HIGH),
            "audio processing error": (ErrorCategory.PROCESSING, ErrorSeverity.HIGH),
            
            # Model errors
            "model not found": (ErrorCategory.MODEL, ErrorSeverity.HIGH),
            "model download failed": (ErrorCategory.MODEL, ErrorSeverity.HIGH),
            "model loading failed": (ErrorCategory.MODEL, ErrorSeverity.CRITICAL),
            "cuda out of memory": (ErrorCategory.MODEL, ErrorSeverity.HIGH),
            "insufficient memory": (ErrorCategory.MODEL, ErrorSeverity.HIGH),
            
            # Network errors
            "connection timeout": (ErrorCategory.NETWORK, ErrorSeverity.MEDIUM),
            "network unreachable": (ErrorCategory.NETWORK, ErrorSeverity.MEDIUM),
            "download interrupted": (ErrorCategory.NETWORK, ErrorSeverity.MEDIUM),
            "api rate limit": (ErrorCategory.NETWORK, ErrorSeverity.LOW),
            
            # System errors
            "disk full": (ErrorCategory.SYSTEM, ErrorSeverity.CRITICAL),
            "out of memory": (ErrorCategory.SYSTEM, ErrorSeverity.CRITICAL),
            "system overload": (ErrorCategory.SYSTEM, ErrorSeverity.HIGH),
            "temporary directory": (ErrorCategory.SYSTEM, ErrorSeverity.MEDIUM),
            "temporary file": (ErrorCategory.SYSTEM, ErrorSeverity.MEDIUM),
            "file locked": (ErrorCategory.SYSTEM, ErrorSeverity.MEDIUM),
            "locked": (ErrorCategory.SYSTEM, ErrorSeverity.MEDIUM),
            
            # Export errors
            "export failed": (ErrorCategory.EXPORT, ErrorSeverity.MEDIUM),
            "file write error": (ErrorCategory.EXPORT, ErrorSeverity.MEDIUM),
            "subtitle generation": (ErrorCategory.EXPORT, ErrorSeverity.MEDIUM),
        }
    
    def handle_processing_error(self, error: Exception, context: str) -> str:
        """
        Handle processing error and return user-friendly message.
        
        Args:
            error: The exception that occurred
            context: Context description of where the error occurred
            
        Returns:
            User-friendly error message
        """
        error_context = ErrorContext(operation=context)
        category, severity = self._categorize_error(error)
        
        # Create error record
        error_record = ErrorRecord(
            error=error,
            category=category,
            severity=severity,
            context=error_context,
            user_message=self._generate_user_message(error, category, severity),
            recovery_suggestions=self.get_recovery_suggestions(error),
            max_retries=self._get_max_retries_for_category(category)
        )
        
        # Log the error
        self.log_error(error, context)
        
        # Store error record
        with self._lock:
            self.error_history.append(error_record)
            self._update_error_patterns(error)
        
        # Handle automatic retry for transient errors
        if self._should_auto_retry(error_record):
            logger.info(f"Scheduling automatic retry for {category.value} error")
        
        return error_record.user_message
    
    def log_error(self, error: Exception, context: str) -> None:
        """
        Log error with context information.
        
        Args:
            error: The exception to log
            context: Context description
        """
        error_context = ErrorContext(operation=context)
        category, severity = self._categorize_error(error)
        
        # Determine log level based on severity
        log_level = {
            ErrorSeverity.LOW: logging.INFO,
            ErrorSeverity.MEDIUM: logging.WARNING,
            ErrorSeverity.HIGH: logging.ERROR,
            ErrorSeverity.CRITICAL: logging.CRITICAL
        }.get(severity, logging.ERROR)
        
        # Create detailed log message
        log_message = (
            f"[{category.value.upper()}] {context}: {str(error)}\n"
            f"Severity: {severity.value}\n"
            f"Thread: {error_context.thread_id}\n"
            f"System: Memory {error_context.system_info.get('memory_usage', 'N/A')}%, "
            f"CPU {error_context.system_info.get('cpu_usage', 'N/A')}%"
        )
        
        if error_context.file_path:
            log_message += f"\nFile: {error_context.file_path}"
        
        if error_context.model_type:
            log_message += f"\nModel: {error_context.model_type} ({error_context.model_size})"
        
        # Log with appropriate level
        logger.log(log_level, log_message, exc_info=severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL])
        
        # For critical errors, also log stack trace
        if severity == ErrorSeverity.CRITICAL:
            logger.critical(f"Stack trace for critical error:\n{traceback.format_exc()}")
    
    def get_recovery_suggestions(self, error: Exception) -> List[str]:
        """
        Get suggested recovery actions for error.
        
        Args:
            error: The exception to get suggestions for
            
        Returns:
            List of recovery suggestions
        """
        category, severity = self._categorize_error(error)
        error_str = str(error).lower()
        
        suggestions = []
        
        # Category-specific suggestions
        if category == ErrorCategory.VALIDATION:
            suggestions.extend([
                "Check that the input file exists and is accessible",
                "Verify the file format is supported (.mp3, .wav, .flac, .ogg)",
                "Ensure you have read permissions for the input file",
                "Check that the output directory exists and is writable"
            ])
            
            # More specific suggestions for FileNotFoundError
            if isinstance(error, FileNotFoundError):
                suggestions.insert(0, "Verify that the file exists at the specified path")
        
        elif category == ErrorCategory.PROCESSING:
            suggestions.extend([
                "Try using a smaller model size (e.g., 'tiny' or 'base')",
                "Check that the audio file is not corrupted",
                "Ensure sufficient system memory is available",
                "Try processing a shorter audio file first"
            ])
        
        elif category == ErrorCategory.MODEL:
            suggestions.extend([
                "Check your internet connection for model downloads",
                "Ensure sufficient disk space for model files",
                "Try restarting the application to reload models",
                "Clear the model cache and re-download"
            ])
            
            if "cuda" in error_str or "memory" in error_str:
                suggestions.extend([
                    "Switch to CPU processing if GPU memory is insufficient",
                    "Close other applications to free up GPU memory",
                    "Try using a smaller model size"
                ])
        
        elif category == ErrorCategory.NETWORK:
            suggestions.extend([
                "Check your internet connection",
                "Try again in a few minutes",
                "Use a VPN if network restrictions apply",
                "Check firewall settings"
            ])
        
        elif category == ErrorCategory.SYSTEM:
            suggestions.extend([
                "Free up disk space",
                "Close other applications to free memory",
                "Restart the application",
                "Check system resource usage"
            ])
            
            # Specific suggestions for memory errors
            if isinstance(error, MemoryError) or "memory" in error_str:
                suggestions.insert(0, "Try using a smaller model size")
                suggestions.insert(1, "Close other applications to free memory")
        
        elif category == ErrorCategory.EXPORT:
            suggestions.extend([
                "Check output directory permissions",
                "Ensure sufficient disk space",
                "Try a different output location",
                "Close files that might be in use"
            ])
        
        # Severity-specific suggestions
        if severity == ErrorSeverity.CRITICAL:
            suggestions.extend([
                "Restart the application",
                "Check system requirements",
                "Contact support if the problem persists"
            ])
        
        # Pattern-based suggestions
        if "permission" in error_str:
            suggestions.append("Run the application as administrator if necessary")
        
        if "space" in error_str or "disk" in error_str:
            suggestions.append("Free up disk space and try again")
        
        if "timeout" in error_str:
            suggestions.append("Check network connection and try again")
        
        return suggestions[:5]  # Limit to 5 most relevant suggestions
    
    def should_retry(self, error: Exception) -> bool:
        """
        Determine if operation should be retried.
        
        Args:
            error: The exception to evaluate
            
        Returns:
            True if the operation should be retried
        """
        category, severity = self._categorize_error(error)
        error_str = str(error).lower()
        
        # Never retry critical errors or validation errors
        if severity == ErrorSeverity.CRITICAL or category == ErrorCategory.VALIDATION:
            return False
        
        # Retry transient network errors
        if category == ErrorCategory.NETWORK:
            return True
        
        # Retry certain system errors
        if category == ErrorCategory.SYSTEM:
            transient_system_errors = ["temporary", "timeout", "busy", "locked"]
            return any(keyword in error_str for keyword in transient_system_errors)
        
        # Retry certain processing errors
        if category == ErrorCategory.PROCESSING:
            transient_processing_errors = ["timeout", "temporary", "busy"]
            return any(keyword in error_str for keyword in transient_processing_errors)
        
        # Retry model download failures
        if category == ErrorCategory.MODEL and "download" in error_str:
            return True
        
        return False
    
    def retry_operation(self, operation: Callable, error_record: ErrorRecord, 
                       *args, **kwargs) -> Tuple[bool, Any, Optional[Exception]]:
        """
        Retry an operation with exponential backoff.
        
        Args:
            operation: The operation to retry
            error_record: The error record for tracking
            *args, **kwargs: Arguments to pass to the operation
            
        Returns:
            Tuple of (success, result, error)
        """
        if not error_record.can_retry():
            return False, None, error_record.error
        
        # Calculate retry delay with exponential backoff
        delay = self.retry_interval * (2 ** error_record.retry_count)
        delay = min(delay, 60.0)  # Cap at 60 seconds
        
        logger.info(f"Retrying operation after {delay:.1f}s delay (attempt {error_record.retry_count + 1})")
        time.sleep(delay)
        
        try:
            error_record.retry_count += 1
            error_record.last_retry_time = time.time()
            
            result = operation(*args, **kwargs)
            error_record.resolved = True
            
            logger.info(f"Operation succeeded on retry {error_record.retry_count}")
            return True, result, None
            
        except Exception as e:
            logger.warning(f"Retry {error_record.retry_count} failed: {e}")
            error_record.error = e
            return False, None, e
    
    def register_recovery_callback(self, category: ErrorCategory, callback: Callable) -> None:
        """
        Register a callback for error recovery.
        
        Args:
            category: Error category to handle
            callback: Callback function for recovery
        """
        with self._lock:
            self.recovery_callbacks[category].append(callback)
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """
        Get error statistics and patterns.
        
        Returns:
            Dictionary with error statistics
        """
        with self._lock:
            total_errors = len(self.error_history)
            if total_errors == 0:
                return {"total_errors": 0}
            
            # Count by category
            category_counts = {}
            severity_counts = {}
            resolved_count = 0
            
            for record in self.error_history:
                category_counts[record.category.value] = category_counts.get(record.category.value, 0) + 1
                severity_counts[record.severity.value] = severity_counts.get(record.severity.value, 0) + 1
                if record.resolved:
                    resolved_count += 1
            
            return {
                "total_errors": total_errors,
                "resolved_errors": resolved_count,
                "resolution_rate": (resolved_count / total_errors) * 100,
                "category_breakdown": category_counts,
                "severity_breakdown": severity_counts,
                "common_patterns": dict(sorted(self.error_patterns.items(), 
                                             key=lambda x: x[1], reverse=True)[:5])
            }
    
    def clear_error_history(self) -> None:
        """Clear error history and patterns."""
        with self._lock:
            self.error_history.clear()
            self.error_patterns.clear()
        logger.info("Error history cleared")
    
    def _categorize_error(self, error: Exception) -> Tuple[ErrorCategory, ErrorSeverity]:
        """
        Categorize an error based on its type and message.
        
        Args:
            error: The exception to categorize
            
        Returns:
            Tuple of (category, severity)
        """
        error_str = str(error).lower()
        error_type = type(error).__name__.lower()
        
        # Check specific exception types first
        if isinstance(error, ValidationError):
            return ErrorCategory.VALIDATION, ErrorSeverity.MEDIUM
        elif isinstance(error, ModelError):
            return ErrorCategory.MODEL, ErrorSeverity.HIGH
        elif isinstance(error, ProcessingError):
            return ErrorCategory.PROCESSING, ErrorSeverity.HIGH
        elif isinstance(error, (ConnectionError, TimeoutError)):
            return ErrorCategory.NETWORK, ErrorSeverity.MEDIUM
        elif isinstance(error, FileNotFoundError):
            return ErrorCategory.VALIDATION, ErrorSeverity.MEDIUM
        elif isinstance(error, PermissionError):
            return ErrorCategory.VALIDATION, ErrorSeverity.HIGH
        elif isinstance(error, MemoryError):
            return ErrorCategory.SYSTEM, ErrorSeverity.HIGH
        elif isinstance(error, OSError):
            return ErrorCategory.SYSTEM, ErrorSeverity.HIGH
        
        # Check error message patterns
        for pattern, (category, severity) in self._error_patterns.items():
            if pattern in error_str or pattern in error_type:
                return category, severity
        
        # Default categorization
        return ErrorCategory.UNKNOWN, ErrorSeverity.MEDIUM
    
    def _generate_user_message(self, error: Exception, category: ErrorCategory, 
                             severity: ErrorSeverity) -> str:
        """
        Generate a user-friendly error message.
        
        Args:
            error: The exception
            category: Error category
            severity: Error severity
            
        Returns:
            User-friendly error message
        """
        base_messages = {
            ErrorCategory.VALIDATION: "There's an issue with the input file or settings.",
            ErrorCategory.PROCESSING: "An error occurred while processing the audio.",
            ErrorCategory.MODEL: "There's an issue with the AI models.",
            ErrorCategory.NETWORK: "A network error occurred.",
            ErrorCategory.SYSTEM: "A system resource issue occurred.",
            ErrorCategory.EXPORT: "An error occurred while saving the output files.",
            ErrorCategory.UNKNOWN: "An unexpected error occurred."
        }
        
        base_message = base_messages.get(category, "An error occurred.")
        
        # Add severity context
        if severity == ErrorSeverity.CRITICAL:
            base_message = f"Critical error: {base_message}"
        elif severity == ErrorSeverity.HIGH:
            base_message = f"Serious error: {base_message}"
        
        # Add specific error details for certain cases
        error_str = str(error).lower()
        if isinstance(error, FileNotFoundError) or "file not found" in error_str:
            base_message += " The specified file could not be found."
        elif "permission" in error_str:
            base_message += " Permission denied - check file access rights."
        elif "memory" in error_str:
            base_message += " Insufficient memory available."
        elif "disk" in error_str or "space" in error_str:
            base_message += " Insufficient disk space."
        elif "network" in error_str or "connection" in error_str:
            base_message += " Check your internet connection."
        
        return base_message
    
    def _should_auto_retry(self, error_record: ErrorRecord) -> bool:
        """Check if error should be automatically retried."""
        return (error_record.can_retry() and 
                self.should_retry(error_record.error) and
                error_record.severity != ErrorSeverity.CRITICAL)
    
    def _get_max_retries_for_category(self, category: ErrorCategory) -> int:
        """Get maximum retries for error category."""
        retry_limits = {
            ErrorCategory.VALIDATION: 0,  # Don't retry validation errors
            ErrorCategory.PROCESSING: 2,
            ErrorCategory.MODEL: 3,
            ErrorCategory.NETWORK: 5,
            ErrorCategory.SYSTEM: 2,
            ErrorCategory.EXPORT: 2,
            ErrorCategory.UNKNOWN: 1
        }
        return retry_limits.get(category, self.max_retries)
    
    def _update_error_patterns(self, error: Exception) -> None:
        """Update error pattern tracking."""
        error_key = f"{type(error).__name__}: {str(error)[:100]}"
        self.error_patterns[error_key] = self.error_patterns.get(error_key, 0) + 1