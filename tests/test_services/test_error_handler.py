"""
Tests for the ErrorHandler class.

This module tests the error handling and recovery mechanisms including
categorized error processing, automatic retry logic, and user-guided recovery.
"""

import pytest
import time
import threading
from unittest.mock import Mock, patch, MagicMock

from src.services.error_handler import (
    ErrorHandler, ErrorCategory, ErrorSeverity, ErrorContext, ErrorRecord
)
from src.services.interfaces import ProcessingError, ModelError, ValidationError


class TestErrorHandler:
    """Test cases for ErrorHandler class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.error_handler = ErrorHandler(max_retries=3, retry_interval=0.1)  # Fast retry for tests
    
    def test_initialization(self):
        """Test ErrorHandler initialization."""
        assert self.error_handler.max_retries == 3
        assert self.error_handler.retry_interval == 0.1
        assert len(self.error_handler.error_history) == 0
        assert len(self.error_handler.error_patterns) == 0
    
    def test_error_categorization_validation_errors(self):
        """Test categorization of validation errors."""
        # Test ValidationError exception type
        error = ValidationError("File not found")
        category, severity = self.error_handler._categorize_error(error)
        assert category == ErrorCategory.VALIDATION
        assert severity == ErrorSeverity.MEDIUM
        
        # Test FileNotFoundError
        error = FileNotFoundError("test.mp3")
        category, severity = self.error_handler._categorize_error(error)
        assert category == ErrorCategory.VALIDATION
        assert severity == ErrorSeverity.MEDIUM
        
        # Test PermissionError
        error = PermissionError("Access denied")
        category, severity = self.error_handler._categorize_error(error)
        assert category == ErrorCategory.VALIDATION
        assert severity == ErrorSeverity.HIGH
    
    def test_error_categorization_processing_errors(self):
        """Test categorization of processing errors."""
        # Test ProcessingError exception type
        error = ProcessingError("Audio processing failed")
        category, severity = self.error_handler._categorize_error(error)
        assert category == ErrorCategory.PROCESSING
        assert severity == ErrorSeverity.HIGH
        
        # Test pattern matching
        error = Exception("vocal separation failed")
        category, severity = self.error_handler._categorize_error(error)
        assert category == ErrorCategory.PROCESSING
        assert severity == ErrorSeverity.HIGH
    
    def test_error_categorization_model_errors(self):
        """Test categorization of model errors."""
        # Test ModelError exception type
        error = ModelError("Model loading failed")
        category, severity = self.error_handler._categorize_error(error)
        assert category == ErrorCategory.MODEL
        assert severity == ErrorSeverity.HIGH
        
        # Test CUDA memory error
        error = Exception("cuda out of memory")
        category, severity = self.error_handler._categorize_error(error)
        assert category == ErrorCategory.MODEL
        assert severity == ErrorSeverity.HIGH
    
    def test_error_categorization_network_errors(self):
        """Test categorization of network errors."""
        # Test ConnectionError
        error = ConnectionError("Network unreachable")
        category, severity = self.error_handler._categorize_error(error)
        assert category == ErrorCategory.NETWORK
        assert severity == ErrorSeverity.MEDIUM
        
        # Test TimeoutError
        error = TimeoutError("Connection timeout")
        category, severity = self.error_handler._categorize_error(error)
        assert category == ErrorCategory.NETWORK
        assert severity == ErrorSeverity.MEDIUM
    
    def test_error_categorization_system_errors(self):
        """Test categorization of system errors."""
        # Test MemoryError
        error = MemoryError("Out of memory")
        category, severity = self.error_handler._categorize_error(error)
        assert category == ErrorCategory.SYSTEM
        assert severity == ErrorSeverity.HIGH
        
        # Test OSError
        error = OSError("Disk full")
        category, severity = self.error_handler._categorize_error(error)
        assert category == ErrorCategory.SYSTEM
        assert severity == ErrorSeverity.HIGH
    
    def test_handle_processing_error(self):
        """Test handling of processing errors."""
        error = ProcessingError("Test processing error")
        context = "test_operation"
        
        user_message = self.error_handler.handle_processing_error(error, context)
        
        # Check that error was recorded
        assert len(self.error_handler.error_history) == 1
        error_record = self.error_handler.error_history[0]
        
        assert error_record.error == error
        assert error_record.category == ErrorCategory.PROCESSING
        assert error_record.severity == ErrorSeverity.HIGH
        assert error_record.context.operation == context
        assert isinstance(user_message, str)
        assert len(user_message) > 0
    
    def test_user_message_generation(self):
        """Test generation of user-friendly error messages."""
        # Test validation error
        error = FileNotFoundError("test.mp3")
        message = self.error_handler._generate_user_message(
            error, ErrorCategory.VALIDATION, ErrorSeverity.MEDIUM
        )
        assert "input file" in message.lower()
        assert "could not be found" in message.lower()
        
        # Test critical error
        error = Exception("Critical system failure")
        message = self.error_handler._generate_user_message(
            error, ErrorCategory.SYSTEM, ErrorSeverity.CRITICAL
        )
        assert "critical error" in message.lower()
    
    def test_recovery_suggestions(self):
        """Test generation of recovery suggestions."""
        # Test validation error suggestions
        error = FileNotFoundError("test.mp3")
        suggestions = self.error_handler.get_recovery_suggestions(error)
        
        assert len(suggestions) > 0
        assert any("file exists" in suggestion.lower() for suggestion in suggestions)
        assert any("accessible" in suggestion.lower() for suggestion in suggestions)
        
        # Test memory error suggestions
        error = MemoryError("Out of memory")
        suggestions = self.error_handler.get_recovery_suggestions(error)
        
        assert len(suggestions) > 0
        assert any("memory" in suggestion.lower() for suggestion in suggestions)
        assert any("smaller model" in suggestion.lower() for suggestion in suggestions)
    
    def test_should_retry_logic(self):
        """Test retry decision logic."""
        # Validation errors should not be retried
        error = ValidationError("Invalid file")
        assert not self.error_handler.should_retry(error)
        
        # Critical errors should not be retried
        error = Exception("Critical system failure")
        # Mock categorization to return critical severity
        with patch.object(self.error_handler, '_categorize_error', 
                         return_value=(ErrorCategory.SYSTEM, ErrorSeverity.CRITICAL)):
            assert not self.error_handler.should_retry(error)
        
        # Network errors should be retried
        error = ConnectionError("Network timeout")
        assert self.error_handler.should_retry(error)
        
        # Transient system errors should be retried
        error = Exception("temporary file locked")
        assert self.error_handler.should_retry(error)
    
    def test_retry_operation(self):
        """Test retry operation functionality."""
        # Create a mock operation that fails twice then succeeds
        call_count = 0
        def mock_operation():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Network timeout")
            return "success"
        
        # Create error record
        error_record = ErrorRecord(
            error=ConnectionError("Network timeout"),
            category=ErrorCategory.NETWORK,
            severity=ErrorSeverity.MEDIUM,
            context=ErrorContext(operation="test"),
            user_message="Network error",
            recovery_suggestions=["Check connection"],
            max_retries=3
        )
        
        # Test multiple retry attempts until success
        success = False
        result = None
        error = None
        
        # First retry attempt (should fail)
        success, result, error = self.error_handler.retry_operation(
            mock_operation, error_record
        )
        assert success is False
        assert error_record.retry_count == 1
        
        # Second retry attempt (should fail)
        success, result, error = self.error_handler.retry_operation(
            mock_operation, error_record
        )
        assert success is False
        assert error_record.retry_count == 2
        
        # Third retry attempt (should succeed)
        success, result, error = self.error_handler.retry_operation(
            mock_operation, error_record
        )
        assert success is True
        assert result == "success"
        assert error is None
        assert error_record.resolved is True
        assert error_record.retry_count == 3
    
    def test_retry_operation_max_retries_exceeded(self):
        """Test retry operation when max retries are exceeded."""
        def failing_operation():
            raise ConnectionError("Network timeout")
        
        # Create error record with max retries already reached
        error_record = ErrorRecord(
            error=ConnectionError("Network timeout"),
            category=ErrorCategory.NETWORK,
            severity=ErrorSeverity.MEDIUM,
            context=ErrorContext(operation="test"),
            user_message="Network error",
            recovery_suggestions=["Check connection"],
            retry_count=3,
            max_retries=3
        )
        
        # Test that retry is not attempted
        success, result, error = self.error_handler.retry_operation(
            failing_operation, error_record
        )
        
        assert success is False
        assert result is None
        assert error == error_record.error
    
    def test_error_statistics(self):
        """Test error statistics collection."""
        # Initially no errors
        stats = self.error_handler.get_error_statistics()
        assert stats["total_errors"] == 0
        
        # Add some errors
        self.error_handler.handle_processing_error(
            ValidationError("File not found"), "test1"
        )
        self.error_handler.handle_processing_error(
            ProcessingError("Processing failed"), "test2"
        )
        self.error_handler.handle_processing_error(
            ConnectionError("Network error"), "test3"
        )
        
        stats = self.error_handler.get_error_statistics()
        
        assert stats["total_errors"] == 3
        assert stats["resolved_errors"] == 0
        assert stats["resolution_rate"] == 0.0
        assert "validation" in stats["category_breakdown"]
        assert "processing" in stats["category_breakdown"]
        assert "network" in stats["category_breakdown"]
    
    def test_error_pattern_tracking(self):
        """Test error pattern tracking."""
        # Add multiple similar errors
        for i in range(3):
            self.error_handler.handle_processing_error(
                FileNotFoundError(f"file{i}.mp3"), "test"
            )
        
        stats = self.error_handler.get_error_statistics()
        
        # Check that patterns are tracked
        assert len(stats["common_patterns"]) > 0
        assert any("FileNotFoundError" in pattern for pattern in stats["common_patterns"])
    
    def test_clear_error_history(self):
        """Test clearing error history."""
        # Add some errors
        self.error_handler.handle_processing_error(
            ValidationError("Test error"), "test"
        )
        
        assert len(self.error_handler.error_history) == 1
        assert len(self.error_handler.error_patterns) > 0
        
        # Clear history
        self.error_handler.clear_error_history()
        
        assert len(self.error_handler.error_history) == 0
        assert len(self.error_handler.error_patterns) == 0
    
    def test_recovery_callback_registration(self):
        """Test recovery callback registration."""
        callback_called = False
        
        def test_callback():
            nonlocal callback_called
            callback_called = True
        
        # Register callback
        self.error_handler.register_recovery_callback(
            ErrorCategory.VALIDATION, test_callback
        )
        
        # Check callback was registered
        assert len(self.error_handler.recovery_callbacks[ErrorCategory.VALIDATION]) == 1
        assert test_callback in self.error_handler.recovery_callbacks[ErrorCategory.VALIDATION]
    
    @patch('psutil.virtual_memory')
    @patch('psutil.disk_usage')
    @patch('psutil.cpu_percent')
    @patch('psutil.Process')
    def test_error_context_system_info(self, mock_process, mock_cpu, mock_disk, mock_memory):
        """Test error context system information collection."""
        # Mock system info
        mock_memory.return_value.percent = 75.0
        mock_memory.return_value.available = 8 * 1024**3  # 8GB
        mock_disk.return_value.percent = 50.0
        mock_cpu.return_value = 25.0
        mock_process.return_value.memory_info.return_value.rss = 512 * 1024**2  # 512MB
        
        context = ErrorContext(operation="test_operation")
        
        assert context.system_info["memory_usage"] == 75.0
        assert context.system_info["disk_usage"] == 50.0
        assert context.system_info["cpu_usage"] == 25.0
        assert context.system_info["available_memory_gb"] == 8.0
        assert context.system_info["process_memory_mb"] == 512.0
    
    def test_thread_safety(self):
        """Test thread safety of error handler."""
        errors = []
        
        def add_errors():
            for i in range(10):
                try:
                    self.error_handler.handle_processing_error(
                        Exception(f"Error {i}"), f"thread_{threading.current_thread().ident}"
                    )
                except Exception as e:
                    errors.append(e)
        
        # Create multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=add_errors)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Check that no errors occurred during concurrent access
        assert len(errors) == 0
        
        # Check that all errors were recorded
        assert len(self.error_handler.error_history) == 50  # 5 threads * 10 errors each


class TestErrorRecord:
    """Test cases for ErrorRecord class."""
    
    def test_can_retry(self):
        """Test retry capability checking."""
        record = ErrorRecord(
            error=Exception("Test"),
            category=ErrorCategory.NETWORK,
            severity=ErrorSeverity.MEDIUM,
            context=ErrorContext(operation="test"),
            user_message="Test error",
            recovery_suggestions=[],
            retry_count=0,
            max_retries=3
        )
        
        # Should be able to retry initially
        assert record.can_retry() is True
        
        # Should not be able to retry after max retries
        record.retry_count = 3
        assert record.can_retry() is False
        
        # Should not be able to retry if resolved
        record.retry_count = 0
        record.resolved = True
        assert record.can_retry() is False
    
    def test_should_retry_now(self):
        """Test retry timing logic."""
        record = ErrorRecord(
            error=Exception("Test"),
            category=ErrorCategory.NETWORK,
            severity=ErrorSeverity.MEDIUM,
            context=ErrorContext(operation="test"),
            user_message="Test error",
            recovery_suggestions=[],
            retry_count=0,
            max_retries=3
        )
        
        # Should retry immediately if no previous retry
        assert record.should_retry_now(min_retry_interval=1.0) is True
        
        # Should not retry immediately after a recent retry
        record.last_retry_time = time.time()
        assert record.should_retry_now(min_retry_interval=1.0) is False
        
        # Should retry after enough time has passed
        record.last_retry_time = time.time() - 2.0
        assert record.should_retry_now(min_retry_interval=1.0) is True


class TestErrorContext:
    """Test cases for ErrorContext class."""
    
    def test_initialization(self):
        """Test ErrorContext initialization."""
        context = ErrorContext(
            operation="test_operation",
            file_path="/path/to/file.mp3",
            model_type="whisperx",
            model_size="base"
        )
        
        assert context.operation == "test_operation"
        assert context.file_path == "/path/to/file.mp3"
        assert context.model_type == "whisperx"
        assert context.model_size == "base"
        assert isinstance(context.timestamp, float)
        assert isinstance(context.thread_id, str)
        assert isinstance(context.system_info, dict)
    
    @patch('psutil.virtual_memory')
    def test_system_info_collection_failure(self, mock_memory):
        """Test system info collection when psutil fails."""
        # Mock psutil to raise an exception
        mock_memory.side_effect = Exception("psutil error")
        
        context = ErrorContext(operation="test")
        
        # Should handle the exception gracefully
        assert context.system_info == {}