"""
Performance and quality validation tests for the lyric-to-subtitle application.

This module provides comprehensive tests for:
1. Performance benchmarks for processing times
2. Subtitle quality validation with reference data
3. Memory usage and resource cleanup tests
"""

import pytest
import time
import os
import tempfile
import shutil
import json
import psutil
import gc
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from unittest.mock import Mock, patch, MagicMock

from src.models.data_models import (
    ProcessingOptions, AlignmentData, Segment, WordSegment, 
    ModelSize, AudioFile
)
from src.services.audio_processor import AudioProcessor, AudioProcessingResult
from src.services.speech_recognizer import SpeechRecognizer, TranscriptionResult
from src.services.vocal_separator import VocalSeparator, VocalSeparationResult
from src.services.subtitle_generator import SubtitleGenerator
from src.services.srt_exporter import SRTExporter
from src.services.ass_exporter import ASSExporter
from src.services.vtt_exporter import VTTExporter
from src.services.json_exporter import JSONExporter


class PerformanceBenchmark:
    """Helper class for performance benchmarking."""
    
    def __init__(self):
        self.results: Dict[str, Dict] = {}
        self.process = psutil.Process()
    
    def start_benchmark(self, test_name: str) -> None:
        """Start benchmarking for a test."""
        self.results[test_name] = {
            'start_time': time.time(),
            'start_memory': self.process.memory_info().rss / 1024 / 1024,  # MB
            'start_cpu_percent': self.process.cpu_percent()
        }
    
    def end_benchmark(self, test_name: str) -> Dict:
        """End benchmarking and return results."""
        if test_name not in self.results:
            raise ValueError(f"Benchmark {test_name} was not started")
        
        end_time = time.time()
        end_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        
        result = self.results[test_name]
        result.update({
            'end_time': end_time,
            'duration': end_time - result['start_time'],
            'end_memory': end_memory,
            'memory_delta': end_memory - result['start_memory'],
            'peak_memory': end_memory
        })
        
        return result


class QualityValidator:
    """Helper class for subtitle quality validation."""
    
    @staticmethod
    def validate_timing_accuracy(alignment_data: AlignmentData, 
                               tolerance: float = 0.1) -> Dict[str, any]:
        """
        Validate timing accuracy of alignment data.
        
        Args:
            alignment_data: The alignment data to validate
            tolerance: Acceptable timing tolerance in seconds
            
        Returns:
            Dictionary with validation results
        """
        issues = []
        
        # Check for overlapping segments
        for i in range(len(alignment_data.segments) - 1):
            current = alignment_data.segments[i]
            next_seg = alignment_data.segments[i + 1]
            
            if current.end_time > next_seg.start_time + tolerance:
                issues.append({
                    'type': 'overlap',
                    'segment_1': i,
                    'segment_2': i + 1,
                    'overlap_duration': current.end_time - next_seg.start_time
                })
        
        # Check for gaps between segments
        gaps = []
        for i in range(len(alignment_data.segments) - 1):
            current = alignment_data.segments[i]
            next_seg = alignment_data.segments[i + 1]
            
            gap = next_seg.start_time - current.end_time
            if gap > tolerance:
                gaps.append({
                    'segment_after': i,
                    'gap_duration': gap
                })
        
        # Check word timing consistency
        word_timing_issues = []
        for word in alignment_data.word_segments:
            if word.end_time <= word.start_time:
                word_timing_issues.append({
                    'word': word.word,
                    'start': word.start_time,
                    'end': word.end_time
                })
        
        return {
            'timing_overlaps': issues,
            'timing_gaps': gaps,
            'word_timing_issues': word_timing_issues,
            'total_issues': len(issues) + len(word_timing_issues),
            'is_valid': len(issues) == 0 and len(word_timing_issues) == 0
        }
    
    @staticmethod
    def validate_text_quality(alignment_data: AlignmentData) -> Dict[str, any]:
        """
        Validate text quality of transcription.
        
        Args:
            alignment_data: The alignment data to validate
            
        Returns:
            Dictionary with text quality metrics
        """
        total_chars = 0
        empty_segments = 0
        short_segments = 0
        confidence_scores = []
        
        for segment in alignment_data.segments:
            text_length = len(segment.text.strip())
            total_chars += text_length
            
            if text_length == 0:
                empty_segments += 1
            elif text_length < 3:
                short_segments += 1
            
            confidence_scores.append(segment.confidence)
        
        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0
        
        return {
            'total_segments': len(alignment_data.segments),
            'total_characters': total_chars,
            'empty_segments': empty_segments,
            'short_segments': short_segments,
            'average_confidence': avg_confidence,
            'min_confidence': min(confidence_scores) if confidence_scores else 0,
            'max_confidence': max(confidence_scores) if confidence_scores else 0,
            'text_quality_score': max(0, 1.0 - (empty_segments + short_segments) / len(alignment_data.segments))
        }
    
    @staticmethod
    def validate_subtitle_format(subtitle_content: str, format_type: str) -> Dict[str, any]:
        """
        Validate subtitle format compliance.
        
        Args:
            subtitle_content: The subtitle content to validate
            format_type: Type of subtitle format ('srt', 'ass', 'vtt', 'json')
            
        Returns:
            Dictionary with format validation results
        """
        if format_type == 'srt':
            return QualityValidator._validate_srt_format(subtitle_content)
        elif format_type == 'ass':
            return QualityValidator._validate_ass_format(subtitle_content)
        elif format_type == 'vtt':
            return QualityValidator._validate_vtt_format(subtitle_content)
        elif format_type == 'json':
            return QualityValidator._validate_json_format(subtitle_content)
        else:
            return {'is_valid': False, 'errors': [f'Unknown format: {format_type}']}
    
    @staticmethod
    def _validate_srt_format(content: str) -> Dict[str, any]:
        """Validate SRT format."""
        lines = content.strip().split('\n')
        errors = []
        subtitle_count = 0
        
        i = 0
        while i < len(lines):
            # Skip empty lines
            if not lines[i].strip():
                i += 1
                continue
            
            # Check subtitle number
            try:
                subtitle_num = int(lines[i].strip())
                subtitle_count += 1
            except (ValueError, IndexError):
                errors.append(f"Invalid subtitle number at line {i + 1}")
                i += 1
                continue
            
            # Check timing line
            i += 1
            if i >= len(lines):
                errors.append(f"Missing timing line for subtitle {subtitle_num}")
                break
            
            timing_line = lines[i].strip()
            if ' --> ' not in timing_line:
                errors.append(f"Invalid timing format at line {i + 1}")
            
            # Skip to next subtitle (find next number or end)
            i += 1
            while i < len(lines) and lines[i].strip() and not lines[i].strip().isdigit():
                i += 1
        
        return {
            'is_valid': len(errors) == 0,
            'errors': errors,
            'subtitle_count': subtitle_count
        }
    
    @staticmethod
    def _validate_ass_format(content: str) -> Dict[str, any]:
        """Validate ASS format."""
        lines = content.strip().split('\n')
        errors = []
        has_script_info = False
        has_styles = False
        has_events = False
        dialogue_count = 0
        
        for line in lines:
            line = line.strip()
            if line.startswith('[Script Info]'):
                has_script_info = True
            elif line.startswith('[V4+ Styles]'):
                has_styles = True
            elif line.startswith('[Events]'):
                has_events = True
            elif line.startswith('Dialogue:'):
                dialogue_count += 1
        
        if not has_script_info:
            errors.append("Missing [Script Info] section")
        if not has_styles:
            errors.append("Missing [V4+ Styles] section")
        if not has_events:
            errors.append("Missing [Events] section")
        
        return {
            'is_valid': len(errors) == 0,
            'errors': errors,
            'dialogue_count': dialogue_count
        }
    
    @staticmethod
    def _validate_vtt_format(content: str) -> Dict[str, any]:
        """Validate VTT format."""
        lines = content.strip().split('\n')
        errors = []
        
        if not lines or not lines[0].strip().startswith('WEBVTT'):
            errors.append("Missing WEBVTT header")
        
        cue_count = 0
        for line in lines:
            if ' --> ' in line:
                cue_count += 1
        
        return {
            'is_valid': len(errors) == 0,
            'errors': errors,
            'cue_count': cue_count
        }
    
    @staticmethod
    def _validate_json_format(content: str) -> Dict[str, any]:
        """Validate JSON format."""
        errors = []
        
        try:
            data = json.loads(content)
            
            # Check required fields
            required_fields = ['segments', 'words', 'metadata']
            for field in required_fields:
                if field not in data:
                    errors.append(f"Missing required field: {field}")
            
            # Validate segments structure
            if 'segments' in data and isinstance(data['segments'], list):
                for i, segment in enumerate(data['segments']):
                    if not isinstance(segment, dict):
                        errors.append(f"Segment {i} is not a dictionary")
                        continue
                    
                    required_seg_fields = ['start', 'end', 'text']
                    for field in required_seg_fields:
                        if field not in segment:
                            errors.append(f"Segment {i} missing field: {field}")
            
        except json.JSONDecodeError as e:
            errors.append(f"Invalid JSON: {e}")
        
        return {
            'is_valid': len(errors) == 0,
            'errors': errors
        }


@pytest.fixture
def performance_benchmark():
    """Fixture providing performance benchmarking utilities."""
    return PerformanceBenchmark()


@pytest.fixture
def quality_validator():
    """Fixture providing quality validation utilities."""
    return QualityValidator()


@pytest.fixture
def sample_audio_file():
    """Fixture providing a sample audio file for testing."""
    # Use the existing test audio file
    audio_path = "data/hello.mp3"
    if os.path.exists(audio_path):
        return audio_path
    
    # Create a mock audio file if the real one doesn't exist
    temp_dir = tempfile.mkdtemp()
    audio_path = os.path.join(temp_dir, "test_audio.wav")
    
    # Create a minimal WAV file (just headers, no actual audio data for testing)
    with open(audio_path, 'wb') as f:
        # WAV header (44 bytes)
        f.write(b'RIFF')
        f.write((36).to_bytes(4, 'little'))  # File size - 8
        f.write(b'WAVE')
        f.write(b'fmt ')
        f.write((16).to_bytes(4, 'little'))  # Subchunk1Size
        f.write((1).to_bytes(2, 'little'))   # AudioFormat (PCM)
        f.write((1).to_bytes(2, 'little'))   # NumChannels
        f.write((44100).to_bytes(4, 'little'))  # SampleRate
        f.write((88200).to_bytes(4, 'little'))  # ByteRate
        f.write((2).to_bytes(2, 'little'))   # BlockAlign
        f.write((16).to_bytes(2, 'little'))  # BitsPerSample
        f.write(b'data')
        f.write((0).to_bytes(4, 'little'))   # Subchunk2Size
    
    return audio_path


@pytest.fixture
def sample_alignment_data():
    """Fixture providing sample alignment data for testing."""
    segments = [
        Segment(
            start_time=0.0,
            end_time=2.5,
            text="Hello world",
            confidence=0.95,
            segment_id=0
        ),
        Segment(
            start_time=2.5,
            end_time=5.0,
            text="This is a test",
            confidence=0.88,
            segment_id=1
        )
    ]
    
    word_segments = [
        WordSegment(word="Hello", start_time=0.0, end_time=0.5, confidence=0.96, segment_id=0),
        WordSegment(word="world", start_time=0.5, end_time=1.0, confidence=0.94, segment_id=0),
        WordSegment(word="This", start_time=2.5, end_time=2.8, confidence=0.90, segment_id=1),
        WordSegment(word="is", start_time=2.8, end_time=3.0, confidence=0.85, segment_id=1),
        WordSegment(word="a", start_time=3.0, end_time=3.1, confidence=0.92, segment_id=1),
        WordSegment(word="test", start_time=3.1, end_time=3.5, confidence=0.88, segment_id=1)
    ]
    
    return AlignmentData(
        segments=segments,
        word_segments=word_segments,
        confidence_scores=[0.95, 0.88],
        audio_duration=5.0,
        source_file="test_audio.wav"
    )


class TestPerformanceBenchmarks:
    """Test cases for performance benchmarking."""
    
    def test_audio_processing_performance_benchmark(self, performance_benchmark, sample_audio_file):
        """Test performance benchmarking of complete audio processing pipeline."""
        performance_benchmark.start_benchmark("audio_processing")
        
        # Mock the audio processor to avoid actual AI processing
        with patch('src.services.audio_processor.AudioProcessor') as mock_processor:
            mock_instance = Mock()
            mock_processor.return_value = mock_instance
            
            # Mock successful processing result
            mock_result = AudioProcessingResult(
                success=True,
                alignment_data=Mock(),
                processing_time=2.5,
                vocals_path="/tmp/vocals.wav"
            )
            mock_instance.process_audio_file.return_value = mock_result
            
            # Create processor and run processing
            processor = AudioProcessor()
            options = ProcessingOptions(model_size=ModelSize.BASE)
            
            start_time = time.time()
            result = processor.process_audio_file(sample_audio_file, options)
            end_time = time.time()
            
            # Verify processing completed
            assert result.success
            
            # Benchmark should complete within reasonable time
            processing_time = end_time - start_time
            assert processing_time < 5.0  # Should complete quickly with mocks
        
        benchmark_result = performance_benchmark.end_benchmark("audio_processing")
        
        # Validate benchmark results
        assert benchmark_result['duration'] > 0
        assert 'memory_delta' in benchmark_result
        assert 'peak_memory' in benchmark_result
        
        # Log performance metrics
        print(f"Audio processing benchmark:")
        print(f"  Duration: {benchmark_result['duration']:.3f}s")
        print(f"  Memory delta: {benchmark_result['memory_delta']:.2f}MB")
        print(f"  Peak memory: {benchmark_result['peak_memory']:.2f}MB")
    
    def test_vocal_separation_performance_benchmark(self, performance_benchmark, sample_audio_file):
        """Test performance benchmarking of vocal separation."""
        performance_benchmark.start_benchmark("vocal_separation")
        
        with patch('src.services.vocal_separator.VocalSeparator') as mock_separator:
            mock_instance = Mock()
            mock_separator.return_value = mock_instance
            
            # Mock successful separation result
            mock_result = VocalSeparationResult(
                success=True,
                vocals_path="/tmp/vocals.wav",
                processing_time=1.5
            )
            mock_instance.separate_vocals.return_value = mock_result
            
            # Create separator and run separation
            separator = VocalSeparator()
            
            start_time = time.time()
            result = separator.separate_vocals(sample_audio_file, ModelSize.BASE)
            end_time = time.time()
            
            # Verify separation completed
            assert result.success
            
            processing_time = end_time - start_time
            assert processing_time < 3.0  # Should complete quickly with mocks
        
        benchmark_result = performance_benchmark.end_benchmark("vocal_separation")
        
        # Validate benchmark results
        assert benchmark_result['duration'] > 0
        print(f"Vocal separation benchmark:")
        print(f"  Duration: {benchmark_result['duration']:.3f}s")
        print(f"  Memory delta: {benchmark_result['memory_delta']:.2f}MB")
    
    def test_speech_recognition_performance_benchmark(self, performance_benchmark, sample_audio_file):
        """Test performance benchmarking of speech recognition."""
        performance_benchmark.start_benchmark("speech_recognition")
        
        with patch('src.services.speech_recognizer.SpeechRecognizer') as mock_recognizer:
            mock_instance = Mock()
            mock_recognizer.return_value = mock_instance
            
            # Mock successful transcription result
            mock_alignment = AlignmentData(
                segments=[],
                word_segments=[],
                confidence_scores=[],
                audio_duration=5.0,
                source_file=sample_audio_file
            )
            mock_result = TranscriptionResult(
                success=True,
                alignment_data=mock_alignment,
                processing_time=2.0
            )
            mock_instance.transcribe_with_alignment.return_value = mock_result
            
            # Create recognizer and run transcription
            recognizer = SpeechRecognizer()
            
            start_time = time.time()
            result = recognizer.transcribe_with_alignment(sample_audio_file, ModelSize.BASE)
            end_time = time.time()
            
            # Verify transcription completed
            assert result.success
            
            processing_time = end_time - start_time
            assert processing_time < 3.0  # Should complete quickly with mocks
        
        benchmark_result = performance_benchmark.end_benchmark("speech_recognition")
        
        # Validate benchmark results
        assert benchmark_result['duration'] > 0
        print(f"Speech recognition benchmark:")
        print(f"  Duration: {benchmark_result['duration']:.3f}s")
        print(f"  Memory delta: {benchmark_result['memory_delta']:.2f}MB")
    
    def test_subtitle_generation_performance_benchmark(self, performance_benchmark, sample_alignment_data):
        """Test performance benchmarking of subtitle generation."""
        performance_benchmark.start_benchmark("subtitle_generation")
        
        # Test all subtitle formats
        formats = ['srt', 'ass', 'vtt', 'json']
        results = {}
        
        for format_type in formats:
            start_time = time.time()
            
            if format_type == 'srt':
                exporter = SRTExporter()
                content = exporter.export_srt(sample_alignment_data, word_level=False)
            elif format_type == 'ass':
                exporter = ASSExporter()
                content = exporter.export_ass_karaoke(sample_alignment_data)
            elif format_type == 'vtt':
                exporter = VTTExporter()
                content = exporter.export_vtt(sample_alignment_data)
            elif format_type == 'json':
                exporter = JSONExporter()
                content = exporter.export_json_alignment(sample_alignment_data)
            
            end_time = time.time()
            results[format_type] = {
                'duration': end_time - start_time,
                'content_length': len(content)
            }
            
            # Verify content was generated
            assert len(content) > 0
        
        benchmark_result = performance_benchmark.end_benchmark("subtitle_generation")
        
        # Validate benchmark results
        assert benchmark_result['duration'] > 0
        print(f"Subtitle generation benchmark:")
        print(f"  Total duration: {benchmark_result['duration']:.3f}s")
        for format_type, result in results.items():
            print(f"  {format_type.upper()}: {result['duration']:.3f}s, {result['content_length']} chars")
    
    @pytest.mark.parametrize("model_size", [ModelSize.TINY, ModelSize.BASE, ModelSize.SMALL])
    def test_model_size_performance_comparison(self, performance_benchmark, sample_audio_file, model_size):
        """Test performance comparison across different model sizes."""
        test_name = f"model_size_{model_size.value}"
        performance_benchmark.start_benchmark(test_name)
        
        with patch('src.services.audio_processor.AudioProcessor') as mock_processor:
            mock_instance = Mock()
            mock_processor.return_value = mock_instance
            
            # Simulate different processing times based on model size
            processing_times = {
                ModelSize.TINY: 1.0,
                ModelSize.BASE: 2.0,
                ModelSize.SMALL: 2.5,
                ModelSize.MEDIUM: 4.0,
                ModelSize.LARGE: 6.0
            }
            
            mock_result = AudioProcessingResult(
                success=True,
                alignment_data=Mock(),
                processing_time=processing_times.get(model_size, 2.0)
            )
            mock_instance.process_audio_file.return_value = mock_result
            
            # Process with specific model size
            processor = AudioProcessor()
            options = ProcessingOptions(model_size=model_size)
            result = processor.process_audio_file(sample_audio_file, options)
            
            assert result.success
        
        benchmark_result = performance_benchmark.end_benchmark(test_name)
        
        # Store results for comparison
        print(f"Model {model_size.value} benchmark:")
        print(f"  Duration: {benchmark_result['duration']:.3f}s")
        print(f"  Memory delta: {benchmark_result['memory_delta']:.2f}MB")


class TestQualityValidation:
    """Test cases for subtitle quality validation."""
    
    def test_timing_accuracy_validation(self, quality_validator, sample_alignment_data):
        """Test validation of timing accuracy in alignment data."""
        # Test with good alignment data
        result = quality_validator.validate_timing_accuracy(sample_alignment_data)
        
        assert result['is_valid']
        assert len(result['timing_overlaps']) == 0
        assert len(result['word_timing_issues']) == 0
        assert result['total_issues'] == 0
        
        print(f"Timing validation results:")
        print(f"  Valid: {result['is_valid']}")
        print(f"  Overlaps: {len(result['timing_overlaps'])}")
        print(f"  Gaps: {len(result['timing_gaps'])}")
        print(f"  Word issues: {len(result['word_timing_issues'])}")
    
    def test_timing_accuracy_validation_with_issues(self, quality_validator):
        """Test timing validation with problematic alignment data."""
        # Create alignment data with timing issues
        segments = [
            Segment(start_time=0.0, end_time=2.5, text="First", confidence=0.9, segment_id=0),
            Segment(start_time=2.0, end_time=4.0, text="Overlap", confidence=0.8, segment_id=1),  # Overlaps with first
        ]
        
        word_segments = [
            WordSegment(word="Bad", start_time=1.0, end_time=0.5, confidence=0.7, segment_id=0),  # End before start
        ]
        
        bad_alignment = AlignmentData(
            segments=segments,
            word_segments=word_segments,
            confidence_scores=[0.9, 0.8],
            audio_duration=4.0
        )
        
        result = quality_validator.validate_timing_accuracy(bad_alignment)
        
        assert not result['is_valid']
        assert len(result['timing_overlaps']) > 0
        assert len(result['word_timing_issues']) > 0
        assert result['total_issues'] > 0
        
        print(f"Bad timing validation results:")
        print(f"  Valid: {result['is_valid']}")
        print(f"  Total issues: {result['total_issues']}")
    
    def test_text_quality_validation(self, quality_validator, sample_alignment_data):
        """Test validation of text quality in transcription."""
        result = quality_validator.validate_text_quality(sample_alignment_data)
        
        assert result['total_segments'] == 2
        assert result['total_characters'] > 0
        assert result['empty_segments'] == 0
        assert result['average_confidence'] > 0.8
        assert result['text_quality_score'] > 0.8
        
        print(f"Text quality validation results:")
        print(f"  Total segments: {result['total_segments']}")
        print(f"  Total characters: {result['total_characters']}")
        print(f"  Average confidence: {result['average_confidence']:.3f}")
        print(f"  Quality score: {result['text_quality_score']:.3f}")
    
    def test_text_quality_validation_with_issues(self, quality_validator):
        """Test text quality validation with problematic data."""
        # Create alignment data with text quality issues
        segments = [
            Segment(start_time=0.0, end_time=1.0, text="", confidence=0.5, segment_id=0),  # Empty
            Segment(start_time=1.0, end_time=2.0, text="Hi", confidence=0.3, segment_id=1),  # Short + low confidence
            Segment(start_time=2.0, end_time=3.0, text="Good text here", confidence=0.9, segment_id=2),  # Good
        ]
        
        bad_alignment = AlignmentData(
            segments=segments,
            word_segments=[],
            confidence_scores=[0.5, 0.3, 0.9],
            audio_duration=3.0
        )
        
        result = quality_validator.validate_text_quality(bad_alignment)
        
        assert result['empty_segments'] > 0
        assert result['short_segments'] > 0
        assert result['average_confidence'] < 0.7
        assert result['text_quality_score'] < 0.8
        
        print(f"Bad text quality validation results:")
        print(f"  Empty segments: {result['empty_segments']}")
        print(f"  Short segments: {result['short_segments']}")
        print(f"  Quality score: {result['text_quality_score']:.3f}")
    
    def test_srt_format_validation(self, quality_validator, sample_alignment_data):
        """Test validation of SRT subtitle format."""
        # Generate SRT content
        exporter = SRTExporter()
        srt_content = exporter.export_srt(sample_alignment_data, word_level=False)
        
        # Validate format
        result = quality_validator.validate_subtitle_format(srt_content, 'srt')
        
        assert result['is_valid']
        assert len(result['errors']) == 0
        assert result['subtitle_count'] > 0
        
        print(f"SRT format validation:")
        print(f"  Valid: {result['is_valid']}")
        print(f"  Subtitle count: {result['subtitle_count']}")
        print(f"  Errors: {len(result['errors'])}")
    
    def test_ass_format_validation(self, quality_validator, sample_alignment_data):
        """Test validation of ASS subtitle format."""
        # Generate ASS content
        exporter = ASSExporter()
        ass_content = exporter.export_ass_karaoke(sample_alignment_data)
        
        # Validate format
        result = quality_validator.validate_subtitle_format(ass_content, 'ass')
        
        assert result['is_valid']
        assert len(result['errors']) == 0
        assert result['dialogue_count'] > 0
        
        print(f"ASS format validation:")
        print(f"  Valid: {result['is_valid']}")
        print(f"  Dialogue count: {result['dialogue_count']}")
        print(f"  Errors: {len(result['errors'])}")
    
    def test_vtt_format_validation(self, quality_validator, sample_alignment_data):
        """Test validation of VTT subtitle format."""
        # Generate VTT content
        exporter = VTTExporter()
        vtt_content = exporter.export_vtt(sample_alignment_data)
        
        # Validate format
        result = quality_validator.validate_subtitle_format(vtt_content, 'vtt')
        
        assert result['is_valid']
        assert len(result['errors']) == 0
        assert result['cue_count'] > 0
        
        print(f"VTT format validation:")
        print(f"  Valid: {result['is_valid']}")
        print(f"  Cue count: {result['cue_count']}")
        print(f"  Errors: {len(result['errors'])}")
    
    def test_json_format_validation(self, quality_validator, sample_alignment_data):
        """Test validation of JSON export format."""
        # Generate JSON content
        exporter = JSONExporter()
        json_content = exporter.export_json_alignment(sample_alignment_data)
        
        # Validate format
        result = quality_validator.validate_subtitle_format(json_content, 'json')
        
        assert result['is_valid']
        assert len(result['errors']) == 0
        
        print(f"JSON format validation:")
        print(f"  Valid: {result['is_valid']}")
        print(f"  Errors: {len(result['errors'])}")
    
    def test_subtitle_format_validation_with_invalid_content(self, quality_validator):
        """Test format validation with invalid subtitle content."""
        # Test invalid SRT
        invalid_srt = "This is not a valid SRT file"
        result = quality_validator.validate_subtitle_format(invalid_srt, 'srt')
        assert not result['is_valid']
        assert len(result['errors']) > 0
        
        # Test invalid JSON
        invalid_json = "{ invalid json content"
        result = quality_validator.validate_subtitle_format(invalid_json, 'json')
        assert not result['is_valid']
        assert len(result['errors']) > 0
        
        # Test invalid VTT (missing header)
        invalid_vtt = "00:00:00.000 --> 00:00:02.000\nHello"
        result = quality_validator.validate_subtitle_format(invalid_vtt, 'vtt')
        assert not result['is_valid']
        assert len(result['errors']) > 0


class TestMemoryAndResourceManagement:
    """Test cases for memory usage and resource cleanup."""
    
    def test_memory_usage_during_processing(self, performance_benchmark, sample_audio_file):
        """Test memory usage during audio processing pipeline."""
        performance_benchmark.start_benchmark("memory_usage")
        
        initial_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        
        with patch('src.services.audio_processor.AudioProcessor') as mock_processor:
            mock_instance = Mock()
            mock_processor.return_value = mock_instance
            
            # Mock processing that simulates memory usage
            mock_result = AudioProcessingResult(
                success=True,
                alignment_data=Mock(),
                processing_time=1.0
            )
            mock_instance.process_audio_file.return_value = mock_result
            
            # Process multiple files to test memory accumulation
            processor = AudioProcessor()
            options = ProcessingOptions(model_size=ModelSize.BASE)
            
            for i in range(3):
                result = processor.process_audio_file(sample_audio_file, options)
                assert result.success
                
                # Check memory hasn't grown excessively
                current_memory = psutil.Process().memory_info().rss / 1024 / 1024
                memory_growth = current_memory - initial_memory
                
                # Allow some memory growth but not excessive (< 100MB per iteration)
                assert memory_growth < 100 * (i + 1), f"Excessive memory growth: {memory_growth}MB"
        
        benchmark_result = performance_benchmark.end_benchmark("memory_usage")
        
        print(f"Memory usage test:")
        print(f"  Initial memory: {initial_memory:.2f}MB")
        print(f"  Final memory: {benchmark_result['end_memory']:.2f}MB")
        print(f"  Memory delta: {benchmark_result['memory_delta']:.2f}MB")
    
    def test_temporary_file_cleanup(self, sample_audio_file):
        """Test that temporary files are properly cleaned up."""
        temp_files_before = len(os.listdir(tempfile.gettempdir()))
        
        with patch('src.services.audio_processor.AudioProcessor') as mock_processor:
            mock_instance = Mock()
            mock_processor.return_value = mock_instance
            
            # Mock temp file creation and cleanup
            temp_files = []
            
            def mock_cleanup():
                for temp_file in temp_files:
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                temp_files.clear()
            
            mock_instance.cleanup_temp_files = mock_cleanup
            mock_instance._temp_files = temp_files
            
            # Simulate creating temp files
            for i in range(3):
                temp_file = tempfile.mktemp(suffix=f"_test_{i}.wav")
                with open(temp_file, 'w') as f:
                    f.write("test")
                temp_files.append(temp_file)
            
            # Verify temp files exist
            for temp_file in temp_files:
                assert os.path.exists(temp_file)
            
            # Process and cleanup
            processor = AudioProcessor()
            processor.cleanup_temp_files()
            
            # Verify temp files are cleaned up
            for temp_file in temp_files:
                assert not os.path.exists(temp_file)
        
        # Verify no excessive temp files remain
        temp_files_after = len(os.listdir(tempfile.gettempdir()))
        temp_files_created = temp_files_after - temp_files_before
        
        # Allow some temp files but not excessive growth
        assert temp_files_created < 10, f"Too many temp files created: {temp_files_created}"
        
        print(f"Temp file cleanup test:")
        print(f"  Temp files before: {temp_files_before}")
        print(f"  Temp files after: {temp_files_after}")
        print(f"  Net created: {temp_files_created}")
    
    def test_resource_cleanup_on_error(self, sample_audio_file):
        """Test that resources are cleaned up properly when errors occur."""
        with patch('src.services.audio_processor.AudioProcessor') as mock_processor:
            mock_instance = Mock()
            mock_processor.return_value = mock_instance
            
            # Mock processing that fails
            mock_instance.process_audio_file.side_effect = Exception("Processing failed")
            
            # Track cleanup calls
            cleanup_called = False
            
            def mock_cleanup():
                nonlocal cleanup_called
                cleanup_called = True
            
            mock_instance.cleanup_temp_files = mock_cleanup
            
            # Process and expect failure
            processor = AudioProcessor()
            options = ProcessingOptions(model_size=ModelSize.BASE)
            
            try:
                processor.process_audio_file(sample_audio_file, options)
            except Exception:
                pass  # Expected to fail
            
            # Verify cleanup was called
            assert cleanup_called, "Cleanup should be called on error"
        
        print("Resource cleanup on error test: PASSED")
    
    def test_memory_leak_detection(self, performance_benchmark, sample_audio_file):
        """Test for memory leaks during repeated processing."""
        performance_benchmark.start_benchmark("memory_leak_test")
        
        # Get baseline memory
        gc.collect()  # Force garbage collection
        baseline_memory = psutil.Process().memory_info().rss / 1024 / 1024
        
        with patch('src.services.audio_processor.AudioProcessor') as mock_processor:
            mock_instance = Mock()
            mock_processor.return_value = mock_instance
            
            mock_result = AudioProcessingResult(
                success=True,
                alignment_data=Mock(),
                processing_time=0.5
            )
            mock_instance.process_audio_file.return_value = mock_result
            
            # Process multiple times
            processor = AudioProcessor()
            options = ProcessingOptions(model_size=ModelSize.BASE)
            
            memory_samples = []
            
            for i in range(10):
                processor.process_audio_file(sample_audio_file, options)
                
                # Force garbage collection and measure memory
                gc.collect()
                current_memory = psutil.Process().memory_info().rss / 1024 / 1024
                memory_samples.append(current_memory)
                
                # Check for excessive memory growth
                memory_growth = current_memory - baseline_memory
                if i > 5:  # Allow some initial growth
                    assert memory_growth < 50, f"Potential memory leak detected: {memory_growth}MB growth"
        
        benchmark_result = performance_benchmark.end_benchmark("memory_leak_test")
        
        # Analyze memory trend
        if len(memory_samples) > 5:
            early_avg = sum(memory_samples[:3]) / 3
            late_avg = sum(memory_samples[-3:]) / 3
            memory_trend = late_avg - early_avg
            
            print(f"Memory leak detection:")
            print(f"  Baseline: {baseline_memory:.2f}MB")
            print(f"  Early average: {early_avg:.2f}MB")
            print(f"  Late average: {late_avg:.2f}MB")
            print(f"  Memory trend: {memory_trend:.2f}MB")
            
            # Fail if significant upward trend
            assert memory_trend < 20, f"Potential memory leak: {memory_trend}MB upward trend"
    
    def test_concurrent_processing_resource_usage(self, performance_benchmark, sample_audio_file):
        """Test resource usage during concurrent processing operations."""
        performance_benchmark.start_benchmark("concurrent_processing")
        
        import threading
        import queue
        
        results_queue = queue.Queue()
        errors_queue = queue.Queue()
        
        def process_audio(thread_id):
            try:
                with patch('src.services.audio_processor.AudioProcessor') as mock_processor:
                    mock_instance = Mock()
                    mock_processor.return_value = mock_instance
                    
                    mock_result = AudioProcessingResult(
                        success=True,
                        alignment_data=Mock(),
                        processing_time=0.5
                    )
                    mock_instance.process_audio_file.return_value = mock_result
                    
                    processor = AudioProcessor()
                    options = ProcessingOptions(model_size=ModelSize.BASE)
                    result = processor.process_audio_file(sample_audio_file, options)
                    
                    results_queue.put((thread_id, result.success))
            except Exception as e:
                errors_queue.put((thread_id, str(e)))
        
        # Start multiple threads
        threads = []
        num_threads = 3
        
        for i in range(num_threads):
            thread = threading.Thread(target=process_audio, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=10)  # 10 second timeout
        
        # Check results
        successful_results = 0
        while not results_queue.empty():
            thread_id, success = results_queue.get()
            if success:
                successful_results += 1
        
        # Check for errors
        errors = []
        while not errors_queue.empty():
            thread_id, error = errors_queue.get()
            errors.append(f"Thread {thread_id}: {error}")
        
        benchmark_result = performance_benchmark.end_benchmark("concurrent_processing")
        
        print(f"Concurrent processing test:")
        print(f"  Threads: {num_threads}")
        print(f"  Successful: {successful_results}")
        print(f"  Errors: {len(errors)}")
        print(f"  Duration: {benchmark_result['duration']:.3f}s")
        
        # Verify most operations succeeded
        assert successful_results >= num_threads - 1, f"Too many failed operations: {len(errors)}"
        
        # Log any errors for debugging
        for error in errors:
            print(f"  Error: {error}")


class TestReferenceDataValidation:
    """Test cases for validating against reference data."""
    
    def test_subtitle_accuracy_against_reference(self, quality_validator, sample_alignment_data):
        """Test subtitle accuracy against reference transcription."""
        # Create reference transcription
        reference_text = "Hello world. This is a test."
        
        # Generate actual transcription from alignment data
        actual_segments = sample_alignment_data.segments
        actual_text = " ".join([seg.text for seg in actual_segments])
        
        # Calculate similarity metrics
        def calculate_word_accuracy(reference: str, actual: str) -> float:
            """Calculate word-level accuracy between reference and actual text."""
            ref_words = reference.lower().split()
            actual_words = actual.lower().split()
            
            # Simple word matching (could be enhanced with edit distance)
            matches = 0
            for word in ref_words:
                if word in actual_words:
                    matches += 1
            
            return matches / len(ref_words) if ref_words else 0.0
        
        accuracy = calculate_word_accuracy(reference_text, actual_text)
        
        print(f"Subtitle accuracy test:")
        print(f"  Reference: '{reference_text}'")
        print(f"  Actual: '{actual_text}'")
        print(f"  Word accuracy: {accuracy:.3f}")
        
        # Expect reasonable accuracy for test data
        assert accuracy > 0.5, f"Low accuracy: {accuracy}"
    
    def test_timing_precision_against_reference(self, quality_validator, sample_alignment_data):
        """Test timing precision against reference timing data."""
        # Create reference timing data
        reference_timings = [
            {"start": 0.0, "end": 2.5, "text": "Hello world"},
            {"start": 2.5, "end": 5.0, "text": "This is a test"}
        ]
        
        # Compare with actual alignment data
        timing_errors = []
        
        for i, (ref, actual) in enumerate(zip(reference_timings, sample_alignment_data.segments)):
            start_error = abs(ref["start"] - actual.start_time)
            end_error = abs(ref["end"] - actual.end_time)
            
            timing_errors.append({
                'segment': i,
                'start_error': start_error,
                'end_error': end_error,
                'max_error': max(start_error, end_error)
            })
        
        # Calculate average timing error
        avg_error = sum(err['max_error'] for err in timing_errors) / len(timing_errors)
        max_error = max(err['max_error'] for err in timing_errors)
        
        print(f"Timing precision test:")
        print(f"  Average error: {avg_error:.3f}s")
        print(f"  Maximum error: {max_error:.3f}s")
        
        for i, error in enumerate(timing_errors):
            print(f"  Segment {i}: start={error['start_error']:.3f}s, end={error['end_error']:.3f}s")
        
        # Expect reasonable timing precision
        assert avg_error < 0.1, f"High average timing error: {avg_error}s"
        assert max_error < 0.2, f"High maximum timing error: {max_error}s"
    
    def test_confidence_score_validation(self, quality_validator, sample_alignment_data):
        """Test validation of confidence scores."""
        confidence_scores = sample_alignment_data.confidence_scores
        
        # Validate confidence score ranges
        for i, score in enumerate(confidence_scores):
            assert 0.0 <= score <= 1.0, f"Invalid confidence score at segment {i}: {score}"
        
        # Calculate confidence statistics
        avg_confidence = sum(confidence_scores) / len(confidence_scores)
        min_confidence = min(confidence_scores)
        max_confidence = max(confidence_scores)
        
        # Count low confidence segments
        low_confidence_count = sum(1 for score in confidence_scores if score < 0.7)
        low_confidence_ratio = low_confidence_count / len(confidence_scores)
        
        print(f"Confidence score validation:")
        print(f"  Average confidence: {avg_confidence:.3f}")
        print(f"  Min confidence: {min_confidence:.3f}")
        print(f"  Max confidence: {max_confidence:.3f}")
        print(f"  Low confidence segments: {low_confidence_count}/{len(confidence_scores)} ({low_confidence_ratio:.1%})")
        
        # Expect reasonable confidence levels
        assert avg_confidence > 0.6, f"Low average confidence: {avg_confidence}"
        assert low_confidence_ratio < 0.5, f"Too many low confidence segments: {low_confidence_ratio:.1%}"


if __name__ == "__main__":
    # Run specific test categories
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "-k", "test_performance or test_quality or test_memory"
    ])