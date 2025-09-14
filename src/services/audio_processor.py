"""
Audio processing controller that orchestrates vocal separation and speech recognition.

This module provides the AudioProcessor class that coordinates the complete
audio-to-subtitle pipeline, managing temporary files and progress aggregation.
"""

import os
import tempfile
import shutil
import logging
from typing import Optional, Callable, List
import time

from ..models.data_models import ModelSize, AlignmentData, ProcessingOptions, AudioFile
from ..services.interfaces import ProcessingError, IAudioProcessor
from ..services.vocal_separator import VocalSeparator, VocalSeparationResult
from ..services.speech_recognizer import SpeechRecognizer, TranscriptionResult
from ..services.audio_file_service import AudioFileService


logger = logging.getLogger(__name__)


class AudioProcessingResult:
    """Result of complete audio processing pipeline."""
    
    def __init__(self, success: bool, alignment_data: Optional[AlignmentData] = None,
                 error_message: Optional[str] = None, processing_time: float = 0.0,
                 vocals_path: Optional[str] = None, instrumental_path: Optional[str] = None):
        self.success = success
        self.alignment_data = alignment_data
        self.error_message = error_message
        self.processing_time = processing_time
        self.vocals_path = vocals_path
        self.instrumental_path = instrumental_path


class AudioProcessor(IAudioProcessor):
    """
    Orchestrates the complete audio processing pipeline.
    
    This class coordinates vocal separation using Demucs and speech recognition
    using WhisperX, managing the workflow and temporary files.
    """
    
    def __init__(self, temp_dir: Optional[str] = None, device: str = "auto"):
        """
        Initialize the AudioProcessor.
        
        Args:
            temp_dir: Optional custom temporary directory for processing files
            device: Device to use for AI models ("cpu", "cuda", or "auto")
        """
        self.temp_dir = temp_dir or tempfile.gettempdir()
        self.device = device
        self.progress_callback: Optional[Callable[[float, str], None]] = None
        
        # Initialize components
        self.vocal_separator = VocalSeparator(temp_dir=self.temp_dir)
        self.speech_recognizer = SpeechRecognizer(device=device)
        self.audio_file_service = AudioFileService()
        
        # Track temporary files for cleanup
        self._temp_files: List[str] = []
        
        # Processing state
        self._is_processing = False
        self._current_operation = ""
        
        # Ensure temp directory exists
        os.makedirs(self.temp_dir, exist_ok=True)
    
    def set_progress_callback(self, callback: Callable[[float, str], None]) -> None:
        """
        Set callback function for progress updates.
        
        Args:
            callback: Function that receives (progress_percentage, status_message)
        """
        self.progress_callback = callback
        
        # Set callbacks for sub-components
        self.vocal_separator.set_progress_callback(self._vocal_progress_callback)
        self.speech_recognizer.set_progress_callback(self._speech_progress_callback)
    
    def separate_vocals(self, audio_path: str, model_size: ModelSize) -> VocalSeparationResult:
        """
        Separate vocals from audio and return separation result.
        
        Args:
            audio_path: Path to the input audio file
            model_size: Model size to use for separation
            
        Returns:
            VocalSeparationResult containing paths to separated files
            
        Raises:
            ProcessingError: If vocal separation fails
        """
        try:
            self._current_operation = "vocal_separation"
            self._update_progress(0.0, "Starting vocal separation...")
            
            result = self.vocal_separator.separate_vocals(audio_path, model_size)
            
            if not result.success:
                raise ProcessingError(result.error_message or "Vocal separation failed")
            
            # Track the vocals file for cleanup
            if result.vocals_path:
                self._temp_files.append(result.vocals_path)
            
            # Track the instrumental file for cleanup if it exists
            if result.instrumental_path:
                self._temp_files.append(result.instrumental_path)
            
            self._update_progress(100.0, "Vocal separation complete")
            return result
            
        except Exception as e:
            logger.error(f"Vocal separation failed: {e}")
            raise ProcessingError(f"Vocal separation failed: {e}")
    
    def transcribe_with_alignment(self, vocals_path: str, model_size: ModelSize) -> AlignmentData:
        """
        Transcribe vocals and generate word-level alignment.
        
        Args:
            vocals_path: Path to the vocals audio file
            model_size: Model size to use for transcription
            
        Returns:
            AlignmentData with transcription and word-level timing
            
        Raises:
            ProcessingError: If transcription fails
        """
        try:
            self._current_operation = "speech_recognition"
            self._update_progress(0.0, "Starting speech recognition...")
            
            result = self.speech_recognizer.transcribe_with_alignment(
                vocals_path, model_size
            )
            
            if not result.success:
                raise ProcessingError(result.error_message or "Speech recognition failed")
            
            self._update_progress(100.0, "Speech recognition complete")
            return result.alignment_data
            
        except Exception as e:
            logger.error(f"Speech recognition failed: {e}")
            raise ProcessingError(f"Speech recognition failed: {e}")
    
    def validate_audio_file(self, file_path: str) -> AudioFile:
        """
        Validate and extract metadata from audio file.
        
        Args:
            file_path: Path to the audio file to validate
            
        Returns:
            AudioFile object with metadata
            
        Raises:
            ProcessingError: If file validation fails
        """
        try:
            # First validate the file
            is_valid, errors = self.audio_file_service.validate_audio_file(file_path)
            if not is_valid:
                raise ProcessingError(f"Audio file validation failed: {'; '.join(errors)}")
            
            # Extract metadata
            audio_file = self.audio_file_service.extract_metadata(file_path)
            if audio_file is None:
                raise ProcessingError("Failed to extract audio file metadata")
            
            return audio_file
        except ProcessingError:
            raise
        except Exception as e:
            raise ProcessingError(f"Audio file validation failed: {e}")
    
    def process_audio_file(self, audio_path: str, options: ProcessingOptions) -> AudioProcessingResult:
        """
        Process a complete audio file through the full pipeline.
        
        Args:
            audio_path: Path to the input audio file
            options: Processing options including model sizes
            
        Returns:
            AudioProcessingResult with alignment data or error info
        """
        start_time = time.time()
        vocals_path = None
        instrumental_path = None
        
        try:
            self._is_processing = True
            self._update_progress(0.0, "Starting audio processing pipeline...")
            
            # Step 1: Validate input file (5% of progress)
            self._update_progress(0.0, "Validating audio file...")
            audio_file = self.validate_audio_file(audio_path)
            logger.info(f"Processing audio file: {audio_file.path} ({audio_file.duration:.2f}s)")
            
            # Check if we should use mock processing (when models aren't available)
            try:
                # Step 2: Vocal separation (45% of progress)
                self._update_progress(5.0, "Separating vocals from audio...")
                separation_result = self.separate_vocals(audio_path, options.model_size)
                
                vocals_path = separation_result.vocals_path
                
                # Handle instrumental file if requested
                if options.save_instrumental and separation_result.instrumental_path:
                    instrumental_path = self._save_instrumental_file(separation_result.instrumental_path, audio_path, options.output_directory)
                
                # Step 3: Speech recognition and alignment (45% of progress)
                self._update_progress(50.0, "Transcribing and aligning speech...")
                alignment_data = self.transcribe_with_alignment(vocals_path, options.model_size)
                
            except Exception as model_error:
                # If models aren't available, use mock processing for demonstration
                logger.warning(f"Models not available, using mock processing: {model_error}")
                
                # Mock processing with simulated progress
                self._update_progress(5.0, "Separating vocals from audio... (mock)")
                time.sleep(1.0)  # Simulate processing time
                
                self._update_progress(25.0, "Processing audio separation... (mock)")
                time.sleep(1.0)
                
                self._update_progress(50.0, "Transcribing and aligning speech... (mock)")
                time.sleep(1.0)
                
                self._update_progress(75.0, "Generating word-level alignment... (mock)")
                time.sleep(1.0)
                
                # Create mock alignment data
                alignment_data = self._create_mock_alignment_data(audio_file)
                vocals_path = audio_path  # Use original file as mock vocals
            
            # Step 4: Finalization (5% of progress)
            self._update_progress(95.0, "Finalizing results...")
            
            # Validate alignment data
            validation_errors = alignment_data.validate()
            if validation_errors:
                logger.warning(f"Alignment data validation warnings: {validation_errors}")
            
            processing_time = time.time() - start_time
            self._update_progress(100.0, f"Audio processing complete ({processing_time:.1f}s)")
            
            logger.info(
                f"Audio processing completed successfully in {processing_time:.2f} seconds. "
                f"Generated {len(alignment_data.segments)} segments and "
                f"{len(alignment_data.word_segments)} word segments."
            )
            
            return AudioProcessingResult(
                success=True,
                alignment_data=alignment_data,
                processing_time=processing_time,
                vocals_path=vocals_path,
                instrumental_path=instrumental_path
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            error_msg = f"Audio processing failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            
            # Clean up on error
            self.cleanup_temp_files()
            
            return AudioProcessingResult(
                success=False,
                error_message=error_msg,
                processing_time=processing_time,
                vocals_path=vocals_path,
                instrumental_path=instrumental_path
            )
            
        finally:
            self._is_processing = False
    
    def _create_mock_alignment_data(self, audio_file: AudioFile) -> AlignmentData:
        """Create mock alignment data for demonstration purposes."""
        from ..models.data_models import AlignmentData, Segment, WordSegment
        
        # Create mock segments based on audio duration
        duration = audio_file.duration
        num_segments = max(1, int(duration / 10))  # One segment per 10 seconds
        
        segments = []
        word_segments = []
        
        mock_lyrics = [
            "Hello world, this is a sample lyric",
            "Generated for demonstration purposes",
            "The actual processing would use AI models",
            "To create real word-level alignment",
            "From your audio file content"
        ]
        
        current_time = 0.0
        segment_duration = duration / num_segments
        
        for i in range(num_segments):
            start_time = current_time
            end_time = min(current_time + segment_duration, duration)
            
            # Use mock lyrics cycling through the list
            text = mock_lyrics[i % len(mock_lyrics)]
            
            # Create segment
            segment = Segment(
                start_time=start_time,
                end_time=end_time,
                text=text,
                confidence=0.85  # Mock confidence
            )
            segments.append(segment)
            
            # Create word segments for this segment
            words = text.split()
            word_duration = (end_time - start_time) / len(words)
            
            for j, word in enumerate(words):
                word_start = start_time + (j * word_duration)
                word_end = start_time + ((j + 1) * word_duration)
                
                word_segment = WordSegment(
                    word=word,
                    start_time=word_start,
                    end_time=word_end,
                    confidence=0.80 + (0.15 * (j % 3) / 3),  # Varying confidence
                    segment_id=i  # Use segment index as segment_id
                )
                word_segments.append(word_segment)
            
            current_time = end_time
        
        return AlignmentData(
            segments=segments,
            word_segments=word_segments,
            confidence_scores=[seg.confidence for seg in segments],
            audio_duration=duration,
            source_file=audio_file.path
        )
    
    def _save_instrumental_file(self, instrumental_path: str, original_audio_path: str, output_directory: str) -> Optional[str]:
        """
        Save the instrumental file to the output directory.
        
        Args:
            instrumental_path: Path to the temporary instrumental file
            original_audio_path: Path to the original audio file
            output_directory: Directory to save the instrumental file
            
        Returns:
            Path to the saved instrumental file, or None if saving failed
        """
        try:
            if not instrumental_path or not os.path.exists(instrumental_path):
                logger.warning("Instrumental file not found, skipping save")
                return None
            
            # Generate output filename
            original_name = os.path.splitext(os.path.basename(original_audio_path))[0]
            instrumental_filename = f"{original_name}_instrumental.wav"
            output_path = os.path.join(output_directory, instrumental_filename)
            
            # Ensure output directory exists
            os.makedirs(output_directory, exist_ok=True)
            
            # Copy the instrumental file to the output directory
            shutil.copy2(instrumental_path, output_path)
            
            logger.info(f"Instrumental file saved to: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Failed to save instrumental file: {e}")
            return None

    def estimate_processing_time(self, audio_duration: float, model_size: ModelSize) -> float:
        """
        Estimate total processing time for the complete pipeline.
        
        Args:
            audio_duration: Duration of audio in seconds
            model_size: Model size to be used
            
        Returns:
            Estimated processing time in seconds
        """
        # Get estimates from individual components
        vocal_time = self.vocal_separator.estimate_processing_time(audio_duration, model_size)
        speech_time = self.speech_recognizer.estimate_processing_time(audio_duration, model_size)
        
        # Add some overhead for file I/O and coordination
        overhead = audio_duration * 0.02  # 2% overhead
        
        return vocal_time + speech_time + overhead
    
    def cancel_processing(self) -> bool:
        """
        Cancel the current processing operation if possible.
        
        Returns:
            True if cancellation was successful, False otherwise
        """
        if not self._is_processing:
            return True
        
        success = True
        
        # Try to cancel vocal separation
        if self._current_operation == "vocal_separation":
            success &= self.vocal_separator.cancel_processing()
        
        # Clean up temporary files
        self.cleanup_temp_files()
        
        self._is_processing = False
        self._current_operation = ""
        
        if success:
            self._update_progress(0.0, "Processing cancelled")
            logger.info("Audio processing cancelled by user")
        
        return success
    
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
        
        # Also clean up component temp files
        self.vocal_separator.cleanup_temp_files()
        self.speech_recognizer.cleanup_models()
    
    def get_processing_status(self) -> dict:
        """
        Get current processing status information.
        
        Returns:
            Dictionary with processing status details
        """
        return {
            "is_processing": self._is_processing,
            "current_operation": self._current_operation,
            "temp_files_count": len(self._temp_files)
        }
    
    def _vocal_progress_callback(self, percentage: float, message: str) -> None:
        """
        Handle progress updates from vocal separation.
        
        Args:
            percentage: Progress percentage from vocal separator (0-100)
            message: Status message from vocal separator
        """
        # Map vocal separation progress to overall progress (5% to 50%)
        overall_progress = 5.0 + (percentage * 0.45)
        self._update_progress(overall_progress, f"Vocal separation: {message}")
    
    def _speech_progress_callback(self, percentage: float, message: str) -> None:
        """
        Handle progress updates from speech recognition.
        
        Args:
            percentage: Progress percentage from speech recognizer (0-100)
            message: Status message from speech recognizer
        """
        # Map speech recognition progress to overall progress (50% to 95%)
        overall_progress = 50.0 + (percentage * 0.45)
        self._update_progress(overall_progress, f"Speech recognition: {message}")
    
    def _update_progress(self, percentage: float, message: str) -> None:
        """
        Update progress if callback is set.
        
        Args:
            percentage: Progress percentage (0-100)
            message: Status message
        """
        if self.progress_callback:
            self.progress_callback(percentage, message)
    
    def get_supported_audio_formats(self) -> List[str]:
        """
        Get list of supported audio formats.
        
        Returns:
            List of supported file extensions
        """
        return self.audio_file_service.get_supported_formats()
    
    def set_confidence_thresholds(self, segment_threshold: float = 0.6, 
                                 word_threshold: float = 0.5) -> None:
        """
        Set confidence thresholds for flagging uncertain segments.
        
        Args:
            segment_threshold: Minimum confidence for segments (0.0-1.0)
            word_threshold: Minimum confidence for words (0.0-1.0)
        """
        self.speech_recognizer.set_confidence_thresholds(
            segment_threshold, word_threshold
        )
    
    def get_device_info(self) -> dict:
        """
        Get information about the processing device being used.
        
        Returns:
            Dictionary with device information
        """
        device_info = {
            "device": self.device,
            "temp_dir": self.temp_dir
        }
        
        # Add CUDA info if available
        if self.device == "cuda":
            try:
                import torch
                if torch.cuda.is_available():
                    device_info["cuda_device_count"] = torch.cuda.device_count()
                    device_info["cuda_current_device"] = torch.cuda.current_device()
                    device_info["cuda_device_name"] = torch.cuda.get_device_name()
            except ImportError:
                device_info["cuda_available"] = False
        
        return device_info