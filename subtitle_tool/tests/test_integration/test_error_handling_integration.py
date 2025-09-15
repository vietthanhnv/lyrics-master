"""
Integration tests for error handling and recovery mechanisms.

This module tests the integration between the ErrorHandler and ApplicationController
to ensure proper error handling, retry logic, and user-guided recovery.
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock

from src.services.application_controller import ApplicationController
from src.services.error_handler import ErrorHandler, ErrorCategory, ErrorSeverity
from src.services.interfaces import ProcessingError, ValidationError, ModelError
from src.models.data_models import ProcessingOptions, ModelSize, ExportFormat


class TestErrorHandlingIntegration:
    """Integration tests for error handling in ApplicationController."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.controller = ApplicationController(temp_dir="/tmp/test", device="cpu")
    
    def test_error_handler_initialization(self):
        """Test that ErrorHandler is properly initialized in ApplicationController."""
        assert hasattr(self.controller, 'error_handler')
        assert isinstance(self.controller.error_handler, ErrorHandler)
        assert self.controller.error_handler.max_retries == 3
        assert self.controller.error_handler.retry_interval == 5.0
    
    def test_service_initialization_error_handling(self):
        """Test error handling during service initialization."""
        # Mock a service initialization failure
        with patch('src.services.application_controller.ModelManager') as mock_model_manager:
            mock_model_manager.side_effect = Exception("Model manager initialization failed")
            
            with pytest.raises(ProcessingError) as exc_info:
                ApplicationController(temp_dir="/tmp/test", device="cpu")
            
            # Check that the error message is user-friendly
            assert "Failed to initialize application services" in str(exc_info.value)
    
    @patch('src.services.application_controller.AudioProcessor')
    @patch('src.services.application_controller.ModelManager')
    def test_single_file_processing_error_handling(self, mock_model_manager, mock_audio_processor):
        """Test error handling in single file processing."""
        # Set up mocks
        mock_model_manager.return_value = Mock()
        mock_audio_processor.return_value = Mock()
        
        # Mock validation to pass
        with patch.object(self.controller, '_validate_processing_inputs'):
            with patch.object(self.controller, '_ensure_models_available'):
                # Mock audio processor to fail
                mock_audio_processor.return_value.process_audio_file.side_effect = ProcessingError("Audio processing failed")
                
                options = ProcessingOptions(
                    model_size=ModelSize.BASE,
                    export_formats=[ExportFormat.SRT],
                    output_directory="/tmp/test"
                )
                
                result = self.controller.process_audio_file("test.mp3", options)
                
                # Check that error was handled properly
                assert result.success is False
                assert "processing failed" in result.error_message.lower()
                
                # Check that error was recorded in error handler
                assert len(self.controller.error_handler.error_history) > 0
                error_record = self.controller.error_handler.error_history[0]
                assert error_record.category == ErrorCategory.PROCESSING
    
    @patch('src.services.application_controller.BatchProcessor')
    @patch('src.services.application_controller.ModelManager')
    def test_batch_processing_error_handling(self, mock_model_manager, mock_batch_processor):
        """Test error handling in batch processing."""
        # Set up mocks
        mock_model_manager.return_value = Mock()
        mock_batch_processor.return_value = Mock()
        
        # Mock validation to pass
        with patch.object(self.controller, '_validate_processing_inputs'):
            with patch.object(self.controller, '_ensure_models_available'):
                # Mock batch processor to fail
                mock_batch_processor.return_value.process_batch.side_effect = ProcessingError("Batch processing failed")
                
                options = ProcessingOptions(
                    model_size=ModelSize.BASE,
                    export_formats=[ExportFormat.SRT],
                    output_directory="/tmp/test"
                )
                
                result = self.controller.process_batch(["test1.mp3", "test2.mp3"], options)
                
                # Check that error was handled properly
                assert result.successful_files == 0
                assert result.failed_files == 2
                
                # Check that error was recorded in error handler
                assert len(self.controller.error_handler.error_history) > 0
    
    def test_validation_error_handling(self):
        """Test handling of validation errors."""
        options = ProcessingOptions(
            model_size=ModelSize.BASE,
            export_formats=[ExportFormat.SRT],
            output_directory="/nonexistent/directory"
        )
        
        # This should trigger a validation error
        result = self.controller.process_audio_file("nonexistent.mp3", options)
        
        assert result.success is False
        assert "file" in result.error_message.lower() or "directory" in result.error_message.lower()
    
    def test_error_statistics_collection(self):
        """Test error statistics collection."""
        # Initially no errors
        stats = self.controller.get_error_statistics()
        assert stats["total_errors"] == 0
        
        # Trigger some errors
        options = ProcessingOptions(
            model_size=ModelSize.BASE,
            export_formats=[ExportFormat.SRT],
            output_directory="/tmp/test"
        )
        
        # File not found error
        self.controller.process_audio_file("nonexistent.mp3", options)
        
        # Check statistics
        stats = self.controller.get_error_statistics()
        assert stats["total_errors"] > 0
        assert "validation" in stats["category_breakdown"]
    
    def test_recovery_suggestions(self):
        """Test recovery suggestions for different error types."""
        # Test file not found error
        error = FileNotFoundError("test.mp3")
        suggestions = self.controller.get_recovery_suggestions(error)
        
        assert len(suggestions) > 0
        assert any("file" in suggestion.lower() for suggestion in suggestions)
        assert any("exists" in suggestion.lower() for suggestion in suggestions)
        
        # Test memory error
        error = MemoryError("Out of memory")
        suggestions = self.controller.get_recovery_suggestions(error)
        
        assert len(suggestions) > 0
        assert any("memory" in suggestion.lower() for suggestion in suggestions)
        assert any("smaller" in suggestion.lower() for suggestion in suggestions)
    
    def test_critical_error_handling(self):
        """Test handling of critical errors."""
        critical_error = Exception("Critical system failure")
        
        # Mock categorization to return critical severity
        with patch.object(self.controller.error_handler, '_categorize_error', 
                         return_value=(ErrorCategory.SYSTEM, ErrorSeverity.CRITICAL)):
            
            error_info = self.controller.handle_critical_error(critical_error, "test_operation")
            
            assert "user_message" in error_info
            assert "recovery_suggestions" in error_info
            assert "diagnostics" in error_info
            assert "should_restart" in error_info
            assert error_info["should_restart"] is True
    
    def test_retry_last_operation(self):
        """Test retry functionality for last operation."""
        # Set up a failed operation context
        self.controller.current_files = ["test.mp3"]
        self.controller.current_options = ProcessingOptions(
            model_size=ModelSize.BASE,
            export_formats=[ExportFormat.SRT],
            output_directory="/tmp/test"
        )
        
        # Add an error to history
        self.controller.error_handler.handle_processing_error(
            ProcessingError("Test error"), "test_operation"
        )
        
        # Mock the process_audio_file to succeed on retry
        with patch.object(self.controller, 'process_audio_file') as mock_process:
            from src.models.data_models import ProcessingResult
            mock_process.return_value = ProcessingResult(
                success=True,
                output_files=["test.srt"],
                processing_time=1.0
            )
            
            result = self.controller.retry_last_operation()
            
            assert result is not None
            assert result.success is True
            mock_process.assert_called_once()
    
    def test_retry_last_operation_no_context(self):
        """Test retry when no operation context is available."""
        # Clear any existing context
        self.controller.current_files = []
        self.controller.current_options = None
        
        result = self.controller.retry_last_operation()
        assert result is None
    
    def test_clear_error_history(self):
        """Test clearing error history."""
        # Add some errors
        self.controller.error_handler.handle_processing_error(
            ProcessingError("Test error"), "test_operation"
        )
        
        assert len(self.controller.error_handler.error_history) > 0
        
        # Clear history
        self.controller.clear_error_history()
        
        assert len(self.controller.error_handler.error_history) == 0
    
    @patch('src.services.application_controller.AudioProcessor')
    def test_automatic_retry_integration(self, mock_audio_processor):
        """Test automatic retry integration in ApplicationController."""
        # Set up mock to fail first time, succeed second time
        call_count = 0
        def mock_process_audio(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ConnectionError("Network timeout")  # Retryable error
            else:
                from src.models.data_models import ProcessingResult, AlignmentData
                return ProcessingResult(
                    success=True,
                    output_files=["test.srt"],
                    processing_time=1.0,
                    alignment_data=AlignmentData(
                        segments=[],
                        word_segments=[],
                        confidence_scores=[],
                        audio_duration=10.0
                    )
                )
        
        # Mock the internal processing method
        with patch.object(self.controller, '_process_audio_file_internal', side_effect=mock_process_audio):
            with patch.object(self.controller, '_validate_processing_inputs'):
                with patch.object(self.controller, '_ensure_models_available'):
                    with patch.object(self.controller, '_generate_subtitle_files', return_value=["test.srt"]):
                        
                        options = ProcessingOptions(
                            model_size=ModelSize.BASE,
                            export_formats=[ExportFormat.SRT],
                            output_directory="/tmp/test"
                        )
                        
                        result = self.controller.process_audio_file("test.mp3", options)
                        
                        # Should succeed after retry
                        assert result.success is True
                        assert call_count == 2  # Called twice due to retry
    
    def test_system_diagnostics_collection(self):
        """Test system diagnostics collection for error reporting."""
        diagnostics = self.controller._collect_system_diagnostics()
        
        # Check that basic system info is collected
        expected_keys = ["platform", "python_version", "device", "temp_dir"]
        for key in expected_keys:
            assert key in diagnostics
        
        # Check that memory/CPU info is collected (if psutil is available)
        if "memory_usage" in diagnostics:
            assert isinstance(diagnostics["memory_usage"], (int, float))
            assert 0 <= diagnostics["memory_usage"] <= 100
    
    def test_error_context_integration(self):
        """Test that error context is properly created and used."""
        # Trigger an error and check that context is properly set
        options = ProcessingOptions(
            model_size=ModelSize.BASE,
            export_formats=[ExportFormat.SRT],
            output_directory="/tmp/test"
        )
        
        result = self.controller.process_audio_file("nonexistent.mp3", options)
        
        # Check that error was recorded with proper context
        assert len(self.controller.error_handler.error_history) > 0
        error_record = self.controller.error_handler.error_history[0]
        
        assert error_record.context.operation == "single_file_processing"
        assert error_record.context.file_path == "nonexistent.mp3"
        assert error_record.context.model_type == "base"
    
    def test_concurrent_error_handling(self):
        """Test error handling under concurrent access."""
        import threading
        import time
        
        errors = []
        results = []
        
        def process_file(file_name):
            try:
                options = ProcessingOptions(
                    model_size=ModelSize.BASE,
                    export_formats=[ExportFormat.SRT],
                    output_directory="/tmp/test"
                )
                result = self.controller.process_audio_file(f"nonexistent_{file_name}.mp3", options)
                results.append(result)
            except Exception as e:
                errors.append(e)
        
        # Create multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=process_file, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Check that no exceptions occurred during concurrent processing
        assert len(errors) == 0
        assert len(results) == 5
        
        # All results should be failures due to file not found
        for result in results:
            assert result.success is False
        
        # Check that all errors were recorded
        assert len(self.controller.error_handler.error_history) == 5