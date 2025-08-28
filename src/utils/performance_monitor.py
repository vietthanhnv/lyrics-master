"""
Performance monitoring utilities for the lyric-to-subtitle application.

This module provides tools for monitoring performance, memory usage, and
resource consumption during audio processing operations.
"""

import time
import psutil
import threading
import logging
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from contextlib import contextmanager
import json
import os


logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """Container for performance metrics."""
    
    operation_name: str
    start_time: float
    end_time: Optional[float] = None
    duration: Optional[float] = None
    
    # Memory metrics (in MB)
    start_memory: float = 0.0
    end_memory: float = 0.0
    peak_memory: float = 0.0
    memory_delta: float = 0.0
    
    # CPU metrics
    start_cpu_percent: float = 0.0
    avg_cpu_percent: float = 0.0
    
    # Custom metrics
    custom_metrics: Dict[str, Any] = field(default_factory=dict)
    
    # Status
    success: bool = True
    error_message: Optional[str] = None
    
    def finalize(self) -> None:
        """Finalize metrics calculation."""
        if self.end_time is not None:
            self.duration = self.end_time - self.start_time
            self.memory_delta = self.end_memory - self.start_memory
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            'operation_name': self.operation_name,
            'duration': self.duration,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'memory_delta': self.memory_delta,
            'peak_memory': self.peak_memory,
            'avg_cpu_percent': self.avg_cpu_percent,
            'success': self.success,
            'error_message': self.error_message,
            'custom_metrics': self.custom_metrics
        }


class PerformanceMonitor:
    """
    Monitor performance metrics during application operations.
    
    This class provides functionality to track timing, memory usage,
    CPU utilization, and custom metrics during processing operations.
    """
    
    def __init__(self, enable_detailed_monitoring: bool = True):
        """
        Initialize the performance monitor.
        
        Args:
            enable_detailed_monitoring: Whether to enable detailed CPU/memory monitoring
        """
        self.enable_detailed_monitoring = enable_detailed_monitoring
        self.metrics_history: List[PerformanceMetrics] = []
        self.active_metrics: Dict[str, PerformanceMetrics] = {}
        self._monitoring_thread: Optional[threading.Thread] = None
        self._stop_monitoring = threading.Event()
        self._lock = threading.Lock()
        
        # Get process handle
        try:
            self.process = psutil.Process()
        except Exception as e:
            logger.warning(f"Failed to get process handle: {e}")
            self.process = None
    
    def start_operation(self, operation_name: str) -> str:
        """
        Start monitoring an operation.
        
        Args:
            operation_name: Name of the operation to monitor
            
        Returns:
            Operation ID for tracking
        """
        operation_id = f"{operation_name}_{int(time.time() * 1000)}"
        
        metrics = PerformanceMetrics(
            operation_name=operation_name,
            start_time=time.time()
        )
        
        if self.process and self.enable_detailed_monitoring:
            try:
                memory_info = self.process.memory_info()
                metrics.start_memory = memory_info.rss / 1024 / 1024  # MB
                metrics.peak_memory = metrics.start_memory
                metrics.start_cpu_percent = self.process.cpu_percent()
            except Exception as e:
                logger.warning(f"Failed to get initial system metrics: {e}")
        
        with self._lock:
            self.active_metrics[operation_id] = metrics
        
        # Start detailed monitoring if enabled
        if self.enable_detailed_monitoring and not self._monitoring_thread:
            self._start_monitoring_thread()
        
        logger.debug(f"Started monitoring operation: {operation_name} (ID: {operation_id})")
        return operation_id
    
    def end_operation(self, operation_id: str, success: bool = True, 
                     error_message: Optional[str] = None) -> PerformanceMetrics:
        """
        End monitoring an operation.
        
        Args:
            operation_id: ID of the operation to end
            success: Whether the operation was successful
            error_message: Error message if operation failed
            
        Returns:
            Final performance metrics
        """
        with self._lock:
            if operation_id not in self.active_metrics:
                raise ValueError(f"Operation {operation_id} not found in active metrics")
            
            metrics = self.active_metrics[operation_id]
            metrics.end_time = time.time()
            metrics.success = success
            metrics.error_message = error_message
            
            if self.process and self.enable_detailed_monitoring:
                try:
                    memory_info = self.process.memory_info()
                    metrics.end_memory = memory_info.rss / 1024 / 1024  # MB
                    metrics.peak_memory = max(metrics.peak_memory, metrics.end_memory)
                except Exception as e:
                    logger.warning(f"Failed to get final system metrics: {e}")
            
            metrics.finalize()
            
            # Move to history
            self.metrics_history.append(metrics)
            del self.active_metrics[operation_id]
        
        # Stop monitoring thread if no active operations
        if not self.active_metrics and self._monitoring_thread:
            self._stop_monitoring_thread()
        
        logger.debug(f"Ended monitoring operation: {metrics.operation_name} "
                    f"(Duration: {metrics.duration:.3f}s, Success: {success})")
        
        return metrics
    
    def add_custom_metric(self, operation_id: str, metric_name: str, value: Any) -> None:
        """
        Add a custom metric to an active operation.
        
        Args:
            operation_id: ID of the operation
            metric_name: Name of the custom metric
            value: Value of the metric
        """
        with self._lock:
            if operation_id in self.active_metrics:
                self.active_metrics[operation_id].custom_metrics[metric_name] = value
    
    @contextmanager
    def monitor_operation(self, operation_name: str):
        """
        Context manager for monitoring an operation.
        
        Args:
            operation_name: Name of the operation to monitor
            
        Yields:
            Operation ID for adding custom metrics
        """
        operation_id = self.start_operation(operation_name)
        try:
            yield operation_id
            self.end_operation(operation_id, success=True)
        except Exception as e:
            self.end_operation(operation_id, success=False, error_message=str(e))
            raise
    
    def get_operation_metrics(self, operation_name: Optional[str] = None) -> List[PerformanceMetrics]:
        """
        Get metrics for operations.
        
        Args:
            operation_name: Filter by operation name (optional)
            
        Returns:
            List of performance metrics
        """
        if operation_name is None:
            return self.metrics_history.copy()
        
        return [m for m in self.metrics_history if m.operation_name == operation_name]
    
    def get_performance_summary(self, operation_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get performance summary statistics.
        
        Args:
            operation_name: Filter by operation name (optional)
            
        Returns:
            Dictionary with summary statistics
        """
        metrics = self.get_operation_metrics(operation_name)
        
        if not metrics:
            return {'total_operations': 0}
        
        successful_metrics = [m for m in metrics if m.success]
        failed_metrics = [m for m in metrics if not m.success]
        
        durations = [m.duration for m in successful_metrics if m.duration is not None]
        memory_deltas = [m.memory_delta for m in successful_metrics]
        
        summary = {
            'total_operations': len(metrics),
            'successful_operations': len(successful_metrics),
            'failed_operations': len(failed_metrics),
            'success_rate': len(successful_metrics) / len(metrics) if metrics else 0,
        }
        
        if durations:
            summary.update({
                'avg_duration': sum(durations) / len(durations),
                'min_duration': min(durations),
                'max_duration': max(durations),
                'total_duration': sum(durations)
            })
        
        if memory_deltas:
            summary.update({
                'avg_memory_delta': sum(memory_deltas) / len(memory_deltas),
                'max_memory_delta': max(memory_deltas),
                'min_memory_delta': min(memory_deltas)
            })
        
        return summary
    
    def export_metrics(self, file_path: str, operation_name: Optional[str] = None) -> None:
        """
        Export metrics to a JSON file.
        
        Args:
            file_path: Path to export file
            operation_name: Filter by operation name (optional)
        """
        metrics = self.get_operation_metrics(operation_name)
        summary = self.get_performance_summary(operation_name)
        
        export_data = {
            'summary': summary,
            'metrics': [m.to_dict() for m in metrics],
            'export_time': time.time()
        }
        
        with open(file_path, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        logger.info(f"Exported {len(metrics)} metrics to {file_path}")
    
    def clear_history(self) -> None:
        """Clear metrics history."""
        with self._lock:
            self.metrics_history.clear()
        logger.debug("Cleared performance metrics history")
    
    def _start_monitoring_thread(self) -> None:
        """Start the background monitoring thread."""
        if self._monitoring_thread and self._monitoring_thread.is_alive():
            return
        
        self._stop_monitoring.clear()
        self._monitoring_thread = threading.Thread(
            target=self._monitoring_loop,
            daemon=True
        )
        self._monitoring_thread.start()
        logger.debug("Started performance monitoring thread")
    
    def _stop_monitoring_thread(self) -> None:
        """Stop the background monitoring thread."""
        if self._monitoring_thread and self._monitoring_thread.is_alive():
            self._stop_monitoring.set()
            self._monitoring_thread.join(timeout=1.0)
            logger.debug("Stopped performance monitoring thread")
    
    def _monitoring_loop(self) -> None:
        """Background monitoring loop."""
        cpu_samples = []
        
        while not self._stop_monitoring.wait(0.5):  # Sample every 0.5 seconds
            if not self.active_metrics or not self.process:
                continue
            
            try:
                # Get current system metrics
                memory_info = self.process.memory_info()
                current_memory = memory_info.rss / 1024 / 1024  # MB
                cpu_percent = self.process.cpu_percent()
                
                cpu_samples.append(cpu_percent)
                
                # Update active metrics
                with self._lock:
                    for metrics in self.active_metrics.values():
                        metrics.peak_memory = max(metrics.peak_memory, current_memory)
                        
                        # Update average CPU (simple moving average)
                        if cpu_samples:
                            metrics.avg_cpu_percent = sum(cpu_samples) / len(cpu_samples)
                
                # Keep only recent CPU samples (last 10 samples)
                if len(cpu_samples) > 10:
                    cpu_samples = cpu_samples[-10:]
                    
            except Exception as e:
                logger.warning(f"Error in monitoring loop: {e}")
    
    def __del__(self):
        """Cleanup when monitor is destroyed."""
        if self._monitoring_thread and self._monitoring_thread.is_alive():
            self._stop_monitoring_thread()


class ResourceValidator:
    """
    Validate system resources and performance requirements.
    
    This class provides functionality to check if the system has
    sufficient resources for processing operations.
    """
    
    @staticmethod
    def check_memory_requirements(required_mb: float, operation_name: str = "operation") -> bool:
        """
        Check if sufficient memory is available.
        
        Args:
            required_mb: Required memory in MB
            operation_name: Name of the operation for logging
            
        Returns:
            True if sufficient memory is available
        """
        try:
            memory = psutil.virtual_memory()
            available_mb = memory.available / 1024 / 1024
            
            if available_mb < required_mb:
                logger.warning(
                    f"Insufficient memory for {operation_name}: "
                    f"{available_mb:.1f}MB available, {required_mb:.1f}MB required"
                )
                return False
            
            logger.debug(
                f"Memory check passed for {operation_name}: "
                f"{available_mb:.1f}MB available, {required_mb:.1f}MB required"
            )
            return True
            
        except Exception as e:
            logger.warning(f"Failed to check memory requirements: {e}")
            return True  # Assume OK if we can't check
    
    @staticmethod
    def check_disk_space(required_mb: float, path: str = None, 
                        operation_name: str = "operation") -> bool:
        """
        Check if sufficient disk space is available.
        
        Args:
            required_mb: Required disk space in MB
            path: Path to check (uses temp directory if None)
            operation_name: Name of the operation for logging
            
        Returns:
            True if sufficient disk space is available
        """
        try:
            import tempfile
            check_path = path or tempfile.gettempdir()
            
            disk_usage = psutil.disk_usage(check_path)
            available_mb = disk_usage.free / 1024 / 1024
            
            if available_mb < required_mb:
                logger.warning(
                    f"Insufficient disk space for {operation_name}: "
                    f"{available_mb:.1f}MB available, {required_mb:.1f}MB required at {check_path}"
                )
                return False
            
            logger.debug(
                f"Disk space check passed for {operation_name}: "
                f"{available_mb:.1f}MB available, {required_mb:.1f}MB required"
            )
            return True
            
        except Exception as e:
            logger.warning(f"Failed to check disk space requirements: {e}")
            return True  # Assume OK if we can't check
    
    @staticmethod
    def get_system_info() -> Dict[str, Any]:
        """
        Get comprehensive system information.
        
        Returns:
            Dictionary with system information
        """
        info = {}
        
        try:
            # CPU information
            info['cpu_count'] = psutil.cpu_count()
            info['cpu_count_logical'] = psutil.cpu_count(logical=True)
            info['cpu_percent'] = psutil.cpu_percent(interval=1)
            
            # Memory information
            memory = psutil.virtual_memory()
            info['memory_total_gb'] = memory.total / 1024 / 1024 / 1024
            info['memory_available_gb'] = memory.available / 1024 / 1024 / 1024
            info['memory_percent'] = memory.percent
            
            # Disk information
            import tempfile
            disk_usage = psutil.disk_usage(tempfile.gettempdir())
            info['disk_total_gb'] = disk_usage.total / 1024 / 1024 / 1024
            info['disk_free_gb'] = disk_usage.free / 1024 / 1024 / 1024
            info['disk_percent'] = (disk_usage.used / disk_usage.total) * 100
            
            # GPU information (if available)
            try:
                import torch
                if torch.cuda.is_available():
                    info['gpu_available'] = True
                    info['gpu_count'] = torch.cuda.device_count()
                    info['gpu_name'] = torch.cuda.get_device_name(0)
                    info['gpu_memory_gb'] = torch.cuda.get_device_properties(0).total_memory / 1024 / 1024 / 1024
                else:
                    info['gpu_available'] = False
            except ImportError:
                info['gpu_available'] = False
            
        except Exception as e:
            logger.warning(f"Failed to get complete system info: {e}")
        
        return info
    
    @staticmethod
    def validate_processing_requirements(audio_duration: float, model_size: str) -> Dict[str, bool]:
        """
        Validate system requirements for audio processing.
        
        Args:
            audio_duration: Duration of audio in seconds
            model_size: Size of the model to be used
            
        Returns:
            Dictionary with validation results
        """
        results = {}
        
        # Estimate memory requirements based on model size and audio duration
        memory_requirements = {
            'tiny': 2.0,    # 2GB base + audio factor
            'base': 4.0,    # 4GB base + audio factor
            'small': 4.0,   # 4GB base + audio factor
            'medium': 6.0,  # 6GB base + audio factor
            'large': 8.0    # 8GB base + audio factor
        }
        
        base_memory = memory_requirements.get(model_size.lower(), 4.0)
        audio_factor = min(audio_duration / 60.0, 5.0)  # Cap at 5x for very long audio
        required_memory = base_memory + (audio_factor * 0.5)  # 0.5GB per minute
        
        results['memory_ok'] = ResourceValidator.check_memory_requirements(
            required_memory * 1024, f"audio processing ({model_size})"
        )
        
        # Estimate disk space requirements (roughly 3x audio file size)
        estimated_audio_size = audio_duration * 0.5  # Rough estimate: 0.5MB per second
        required_disk = estimated_audio_size * 3
        
        results['disk_ok'] = ResourceValidator.check_disk_space(
            required_disk, operation_name="audio processing"
        )
        
        # Check CPU requirements (basic check)
        cpu_count = psutil.cpu_count()
        results['cpu_ok'] = cpu_count >= 2  # Minimum 2 cores recommended
        
        results['overall_ok'] = all(results.values())
        
        return results


# Global performance monitor instance
_global_monitor: Optional[PerformanceMonitor] = None


def get_performance_monitor() -> PerformanceMonitor:
    """Get the global performance monitor instance."""
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = PerformanceMonitor()
    return _global_monitor


def monitor_performance(operation_name: str):
    """
    Decorator for monitoring function performance.
    
    Args:
        operation_name: Name of the operation to monitor
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            monitor = get_performance_monitor()
            with monitor.monitor_operation(operation_name) as operation_id:
                result = func(*args, **kwargs)
                # Add result info as custom metric if available
                if hasattr(result, 'success'):
                    monitor.add_custom_metric(operation_id, 'operation_success', result.success)
                return result
        return wrapper
    return decorator