"""
Speech recognition service using OpenAI Whisper for transcription and alignment.

This module provides the SpeechRecognizer class that integrates Whisper functionality
to transcribe audio and generate word-level timestamps.
"""

import os
import tempfile
import logging
from typing import Optional, Callable, List, Dict, Any
import time

from ..models.data_models import ModelSize, AlignmentData, Segment, WordSegment
from ..services.interfaces import ProcessingError


logger = logging.getLogger(__name__)


class TranscriptionResult:
    """Result of speech recognition and alignment operation."""
    
    def __init__(self, success: bool, alignment_data: Optional[AlignmentData] = None,
                 error_message: Optional[str] = None, processing_time: float = 0.0):
        self.success = success
        self.alignment_data = alignment_data
        self.error_message = error_message
        self.processing_time = processing_time


class SpeechRecognizer:
    """
    Handles speech recognition and word-level alignment using OpenAI Whisper.
    
    This class provides functionality to transcribe audio files and generate
    word-level timestamps using OpenAI's Whisper model.
    """
    
    def __init__(self, device: str = "auto"):
        """
        Initialize the SpeechRecognizer.
        
        Args:
            device: Device to use for inference ("cpu", "cuda", or "auto")
        """
        self.device = self._determine_device(device)
        self.progress_callback: Optional[Callable[[float, str], None]] = None
        self._whisper_model = None
    
    def _determine_device(self, device: str) -> str:
        """Determine the appropriate device for inference."""
        if device == "auto":
            try:
                import torch
                return "cuda" if torch.cuda.is_available() else "cpu"
            except ImportError:
                return "cpu"
        return device
    
    def _get_whisper_model_name(self, model_size: ModelSize) -> str:
        """Get Whisper model name based on size."""
        model_map = {
            ModelSize.TINY: "tiny",
            ModelSize.BASE: "base",
            ModelSize.SMALL: "small", 
            ModelSize.MEDIUM: "medium",
            ModelSize.LARGE: "large"
        }
        return model_map.get(model_size, "base")
    
    def _convert_whisper_result_to_alignment_data(self, result: Dict[str, Any], audio_path: str) -> AlignmentData:
        """Convert Whisper result to AlignmentData format."""
        segments = []
        word_segments = []
        confidence_scores = []
        
        # Get audio duration from result or estimate
        audio_duration = 0.0
        if 'segments' in result and result['segments']:
            audio_duration = max(seg.get('end', 0) for seg in result['segments'])
        
        # Process segments
        for i, segment in enumerate(result.get('segments', [])):
            # Create segment
            seg = Segment(
                start_time=segment.get('start', 0.0),
                end_time=segment.get('end', 0.0),
                text=segment.get('text', '').strip(),
                confidence=segment.get('avg_logprob', 0.0),
                segment_id=i
            )
            segments.append(seg)
            confidence_scores.append(seg.confidence)
            
            # Process words in segment
            for word_info in segment.get('words', []):
                word_seg = WordSegment(
                    word=word_info.get('word', '').strip(),
                    start_time=word_info.get('start', seg.start_time),
                    end_time=word_info.get('end', seg.end_time),
                    confidence=word_info.get('probability', seg.confidence),
                    segment_id=i
                )
                word_segments.append(word_seg)
        
        # If no segments found, create a mock segment
        if not segments:
            segments.append(Segment(
                start_time=0.0,
                end_time=audio_duration or 10.0,
                text="No speech detected",
                confidence=0.0,
                segment_id=0
            ))
            confidence_scores.append(0.0)
        
        return AlignmentData(
            segments=segments,
            word_segments=word_segments,
            confidence_scores=confidence_scores,
            audio_duration=audio_duration or segments[-1].end_time if segments else 0.0,
            source_file=audio_path
        )
    
    def _update_progress(self, percentage: float, message: str):
        """Update progress if callback is set."""
        if self.progress_callback:
            self.progress_callback(percentage, message)
    
    def set_progress_callback(self, callback: Callable[[float, str], None]) -> None:
        """Set callback function for progress updates."""
        self.progress_callback = callback
        self._whisper_model = None
        self._align_model = None
        self._align_metadata = None
        
        # Confidence thresholds for flagging uncertain segments
        self.low_confidence_threshold = 0.6
        self.word_confidence_threshold = 0.5
    
    def set_progress_callback(self, callback: Callable[[float, str], None]) -> None:
        """
        Set callback function for progress updates.
        
        Args:
            callback: Function that receives (progress_percentage, status_message)
        """
        self.progress_callback = callback
    
    def set_confidence_thresholds(self, segment_threshold: float = 0.6, 
                                 word_threshold: float = 0.5) -> None:
        """
        Set confidence thresholds for flagging uncertain segments.
        
        Args:
            segment_threshold: Minimum confidence for segments (0.0-1.0)
            word_threshold: Minimum confidence for words (0.0-1.0)
        """
        self.low_confidence_threshold = max(0.0, min(1.0, segment_threshold))
        self.word_confidence_threshold = max(0.0, min(1.0, word_threshold))
    
    def transcribe_with_alignment(self, audio_path: str, model_size: ModelSize = ModelSize.BASE,
                                language: Optional[str] = None) -> TranscriptionResult:
        """
        Transcribe audio file and generate word-level alignment using OpenAI Whisper.
        
        Args:
            audio_path: Path to the audio file to transcribe
            model_size: Whisper model size to use
            language: Language code for transcription (auto-detect if None)
            
        Returns:
            TranscriptionResult containing alignment data or error info
        """
        start_time = time.time()
        
        try:
            # Validate input file
            if not os.path.exists(audio_path):
                raise ProcessingError(f"Input audio file not found: {audio_path}")
            
            self._update_progress(0.0, "Initializing speech recognition...")
            
            # Import whisper
            try:
                import whisper
            except ImportError:
                raise ProcessingError("OpenAI Whisper is not installed. Please install it with: pip install openai-whisper")
            
            # Load Whisper model
            self._update_progress(10.0, f"Loading {model_size.value} Whisper model...")
            if self._whisper_model is None:
                model_name = self._get_whisper_model_name(model_size)
                self._whisper_model = whisper.load_model(model_name, device=self.device)
            
            # Perform transcription with word timestamps
            self._update_progress(30.0, "Transcribing audio...")
            result = self._whisper_model.transcribe(
                audio_path,
                language=language,
                word_timestamps=True,
                verbose=False
            )
            
            # Convert to AlignmentData format
            self._update_progress(80.0, "Processing alignment results...")
            alignment_data = self._convert_whisper_result_to_alignment_data(result, audio_path)
            
            self._update_progress(100.0, "Speech recognition complete")
            
            processing_time = time.time() - start_time
            logger.info(f"Speech recognition completed in {processing_time:.2f} seconds")
            
            return TranscriptionResult(
                success=True,
                alignment_data=alignment_data,
                processing_time=processing_time
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            error_msg = f"Speech recognition failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            
            return TranscriptionResult(
                success=False,
                error_message=error_msg,
                processing_time=processing_time
            )
            
            return TranscriptionResult(
                success=False,
                error_message=error_msg,
                processing_time=processing_time
            )
    
    def _determine_device(self, device: str) -> str:
        """
        Determine the best device to use for inference.
        
        Args:
            device: Requested device ("cpu", "cuda", or "auto")
            
        Returns:
            Device string to use
        """
        if device == "auto":
            try:
                import torch
                if torch.cuda.is_available():
                    return "cuda"
                else:
                    return "cpu"
            except ImportError:
                return "cpu"
        return device
    
    def _check_whisperx_availability(self) -> None:
        """
        Check if WhisperX is available for import.
        
        Raises:
            ProcessingError: If WhisperX is not installed
        """
        try:
            import whisperx
        except ImportError:
            raise ProcessingError(
                "WhisperX is not installed. Please install it with: pip install whisperx"
            )
    
    def _load_whisper_model(self, model_size: ModelSize):
        """
        Load the Whisper model for transcription.
        
        Args:
            model_size: Size of the model to load
            
        Returns:
            Loaded Whisper model
        """
        try:
            import whisperx
            
            model_name = self._get_whisper_model_name(model_size)
            
            # Load model with specified device and compute type
            model = whisperx.load_model(
                model_name, 
                device=self.device, 
                compute_type=self.compute_type
            )
            
            return model
            
        except Exception as e:
            raise ProcessingError(f"Failed to load Whisper model: {e}")
    
    def _get_whisper_model_name(self, model_size: ModelSize) -> str:
        """
        Get the Whisper model name for the specified size.
        
        Args:
            model_size: The requested model size
            
        Returns:
            String name of the Whisper model
        """
        model_mapping = {
            ModelSize.TINY: "tiny",
            ModelSize.BASE: "base", 
            ModelSize.SMALL: "small",
            ModelSize.MEDIUM: "medium",
            ModelSize.LARGE: "large-v2"
        }
        
        return model_mapping.get(model_size, "base")
    
    def _transcribe_audio(self, model, audio_path: str) -> Dict[str, Any]:
        """
        Transcribe audio using the loaded Whisper model.
        
        Args:
            model: Loaded Whisper model
            audio_path: Path to audio file
            
        Returns:
            Transcription result dictionary
        """
        try:
            import whisperx
            
            # Load audio
            audio = whisperx.load_audio(audio_path)
            
            # Perform transcription
            result = model.transcribe(audio, batch_size=16)
            
            return result
            
        except Exception as e:
            raise ProcessingError(f"Transcription failed: {e}")
    
    def _load_alignment_model(self, language: str):
        """
        Load the alignment model for forced alignment.
        
        Args:
            language: Language code for alignment
            
        Returns:
            Tuple of (align_model, align_metadata)
        """
        try:
            import whisperx
            
            # Load alignment model
            model_a, metadata = whisperx.load_align_model(
                language_code=language, 
                device=self.device
            )
            
            return model_a, metadata
            
        except Exception as e:
            raise ProcessingError(f"Failed to load alignment model: {e}")
    
    def _perform_alignment(self, transcription_result: Dict[str, Any], 
                          align_model, align_metadata, audio_path: str) -> Dict[str, Any]:
        """
        Perform forced alignment on transcription results.
        
        Args:
            transcription_result: Result from transcription
            align_model: Loaded alignment model
            align_metadata: Alignment model metadata
            audio_path: Path to original audio file
            
        Returns:
            Aligned transcription result
        """
        try:
            import whisperx
            
            # Load audio for alignment
            audio = whisperx.load_audio(audio_path)
            
            # Perform alignment
            result = whisperx.align(
                transcription_result["segments"], 
                align_model, 
                align_metadata, 
                audio, 
                self.device, 
                return_char_alignments=False
            )
            
            return result
            
        except Exception as e:
            raise ProcessingError(f"Alignment failed: {e}")
    
    def _convert_to_alignment_data(self, aligned_result: Dict[str, Any], 
                                  source_file: str) -> AlignmentData:
        """
        Convert WhisperX results to AlignmentData format.
        
        Args:
            aligned_result: Result from WhisperX alignment
            source_file: Path to source audio file
            
        Returns:
            AlignmentData object
        """
        segments = []
        word_segments = []
        confidence_scores = []
        
        # Get audio duration (estimate from last segment if available)
        audio_duration = 0.0
        
        for seg_idx, segment in enumerate(aligned_result.get("segments", [])):
            # Create segment
            segment_obj = Segment(
                start_time=segment.get("start", 0.0),
                end_time=segment.get("end", 0.0),
                text=segment.get("text", "").strip(),
                confidence=segment.get("avg_logprob", 0.0),
                segment_id=seg_idx
            )
            segments.append(segment_obj)
            confidence_scores.append(segment_obj.confidence)
            
            # Update audio duration
            audio_duration = max(audio_duration, segment_obj.end_time)
            
            # Create word segments
            for word_data in segment.get("words", []):
                word_segment = WordSegment(
                    word=word_data.get("word", "").strip(),
                    start_time=word_data.get("start", segment_obj.start_time),
                    end_time=word_data.get("end", segment_obj.end_time),
                    confidence=word_data.get("score", segment_obj.confidence),
                    segment_id=seg_idx
                )
                word_segments.append(word_segment)
        
        return AlignmentData(
            segments=segments,
            word_segments=word_segments,
            confidence_scores=confidence_scores,
            audio_duration=audio_duration,
            source_file=source_file
        )
    
    def _flag_uncertain_segments(self, alignment_data: AlignmentData) -> None:
        """
        Flag segments and words with low confidence scores.
        
        Args:
            alignment_data: AlignmentData to analyze and flag
        """
        # Flag low-confidence segments
        for segment in alignment_data.segments:
            if segment.confidence < self.low_confidence_threshold:
                logger.warning(
                    f"Low confidence segment ({segment.confidence:.2f}): "
                    f"'{segment.text}' at {segment.start_time:.2f}s"
                )
        
        # Flag low-confidence words
        low_confidence_words = [
            word for word in alignment_data.word_segments 
            if word.confidence < self.word_confidence_threshold
        ]
        
        if low_confidence_words:
            logger.info(f"Found {len(low_confidence_words)} low-confidence words")
            for word in low_confidence_words[:5]:  # Log first 5 as examples
                logger.warning(
                    f"Low confidence word ({word.confidence:.2f}): "
                    f"'{word.word}' at {word.start_time:.2f}s"
                )
    
    def _update_progress(self, percentage: float, message: str) -> None:
        """
        Update progress if callback is set.
        
        Args:
            percentage: Progress percentage (0-100)
            message: Status message
        """
        if self.progress_callback:
            self.progress_callback(percentage, message)
    
    def get_supported_languages(self) -> List[str]:
        """
        Get list of languages supported by WhisperX alignment.
        
        Returns:
            List of supported language codes
        """
        # Common languages supported by WhisperX alignment
        return [
            "en", "es", "fr", "de", "it", "ja", "zh", "nl", "uk", "pt",
            "ar", "cs", "ru", "pl", "hu", "fi", "fa", "el", "tr", "da",
            "he", "vi", "ko", "ur", "te", "hi", "ca", "ml", "no", "nn"
        ]
    
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
        # Actual times will vary based on hardware and audio complexity
        time_multipliers = {
            ModelSize.TINY: 0.05,   # ~3 seconds for 1 minute of audio
            ModelSize.BASE: 0.1,    # ~6 seconds for 1 minute of audio  
            ModelSize.SMALL: 0.15,  # ~9 seconds for 1 minute of audio
            ModelSize.MEDIUM: 0.25, # ~15 seconds for 1 minute of audio
            ModelSize.LARGE: 0.4    # ~24 seconds for 1 minute of audio
        }
        
        multiplier = time_multipliers.get(model_size, 0.1)
        
        # Add extra time for alignment (roughly 50% more)
        return audio_duration * multiplier * 1.5
    
    def cleanup_models(self) -> None:
        """
        Clean up loaded models to free memory.
        """
        self._whisper_model = None
        self._align_model = None
        self._align_metadata = None
        
        # Force garbage collection if available
        try:
            import gc
            gc.collect()
        except ImportError:
            pass
        
        # Clear CUDA cache if using GPU
        if self.device == "cuda":
            try:
                import torch
                torch.cuda.empty_cache()
            except ImportError:
                pass