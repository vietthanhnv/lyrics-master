"""
Integration tests for SRT subtitle generation.

This module contains integration tests that verify SRT subtitle generation
works correctly with the complete audio processing pipeline.
"""

import pytest
import tempfile
import os
from unittest.mock import Mock, patch

from src.services.subtitle_generator import SubtitleGenerator
from src.services.srt_exporter import SRTExporter
from src.models.data_models import (
    AlignmentData, Segment, WordSegment, ExportFormat,
    ProcessingOptions, ModelSize
)


class TestSRTIntegration:
    """Integration tests for SRT subtitle generation."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.subtitle_generator = SubtitleGenerator()
        self.srt_exporter = SRTExporter()
        
        # Create realistic alignment data that might come from WhisperX
        self.realistic_alignment_data = AlignmentData(
            segments=[
                Segment(
                    start_time=0.12,
                    end_time=3.45,
                    text="Welcome to the lyric subtitle generator application.",
                    confidence=0.94,
                    segment_id=1
                ),
                Segment(
                    start_time=3.67,
                    end_time=7.23,
                    text="This tool converts audio files into synchronized subtitles.",
                    confidence=0.91,
                    segment_id=2
                ),
                Segment(
                    start_time=7.45,
                    end_time=11.89,
                    text="Perfect for creating karaoke videos and accessibility content.",
                    confidence=0.88,
                    segment_id=3
                )
            ],
            word_segments=[
                # First segment words
                WordSegment(word="Welcome", start_time=0.12, end_time=0.58, confidence=0.96, segment_id=1),
                WordSegment(word="to", start_time=0.58, end_time=0.72, confidence=0.94, segment_id=1),
                WordSegment(word="the", start_time=0.72, end_time=0.89, confidence=0.93, segment_id=1),
                WordSegment(word="lyric", start_time=0.89, end_time=1.34, confidence=0.95, segment_id=1),
                WordSegment(word="subtitle", start_time=1.34, end_time=1.89, confidence=0.92, segment_id=1),
                WordSegment(word="generator", start_time=1.89, end_time=2.67, confidence=0.94, segment_id=1),
                WordSegment(word="application", start_time=2.67, end_time=3.45, confidence=0.91, segment_id=1),
                
                # Second segment words
                WordSegment(word="This", start_time=3.67, end_time=3.89, confidence=0.93, segment_id=2),
                WordSegment(word="tool", start_time=3.89, end_time=4.23, confidence=0.95, segment_id=2),
                WordSegment(word="converts", start_time=4.23, end_time=4.89, confidence=0.89, segment_id=2),
                WordSegment(word="audio", start_time=4.89, end_time=5.34, confidence=0.92, segment_id=2),
                WordSegment(word="files", start_time=5.34, end_time=5.78, confidence=0.94, segment_id=2),
                WordSegment(word="into", start_time=5.78, end_time=6.12, confidence=0.96, segment_id=2),
                WordSegment(word="synchronized", start_time=6.12, end_time=6.89, confidence=0.87, segment_id=2),
                WordSegment(word="subtitles", start_time=6.89, end_time=7.23, confidence=0.90, segment_id=2),
                
                # Third segment words
                WordSegment(word="Perfect", start_time=7.45, end_time=7.89, confidence=0.91, segment_id=3),
                WordSegment(word="for", start_time=7.89, end_time=8.12, confidence=0.94, segment_id=3),
                WordSegment(word="creating", start_time=8.12, end_time=8.67, confidence=0.88, segment_id=3),
                WordSegment(word="karaoke", start_time=8.67, end_time=9.34, confidence=0.85, segment_id=3),
                WordSegment(word="videos", start_time=9.34, end_time=9.78, confidence=0.92, segment_id=3),
                WordSegment(word="and", start_time=9.78, end_time=9.95, confidence=0.96, segment_id=3),
                WordSegment(word="accessibility", start_time=9.95, end_time=10.89, confidence=0.83, segment_id=3),
                WordSegment(word="content", start_time=10.89, end_time=11.89, confidence=0.89, segment_id=3),
            ],
            confidence_scores=[0.94, 0.91, 0.88],
            audio_duration=11.89,
            source_file="sample_audio.wav"
        )
    
    def test_sentence_level_srt_generation(self):
        """Test sentence-level SRT generation with realistic data."""
        srt_content = self.subtitle_generator.generate_srt(
            self.realistic_alignment_data, 
            word_level=False
        )
        
        # Validate the generated SRT
        validation_errors = self.srt_exporter.validate_srt_content(srt_content)
        assert len(validation_errors) == 0, f"SRT validation failed: {validation_errors}"
        
        # Check content structure
        blocks = srt_content.strip().split('\n\n')
        assert len(blocks) == 3  # Three segments
        
        # Check timing precision
        assert "00:00:00,120 --> 00:00:03,450" in srt_content
        assert "00:00:03,670 --> 00:00:07,230" in srt_content
        assert "00:00:07,450 --> 00:00:11,890" in srt_content
        
        # Check text content
        assert "Welcome to the lyric subtitle generator application." in srt_content
        assert "This tool converts audio files into synchronized subtitles." in srt_content
        assert "Perfect for creating karaoke videos and accessibility content." in srt_content
    
    def test_word_level_srt_generation(self):
        """Test word-level SRT generation with realistic data."""
        srt_content = self.subtitle_generator.generate_srt(
            self.realistic_alignment_data, 
            word_level=True
        )
        
        # Validate the generated SRT
        validation_errors = self.srt_exporter.validate_srt_content(srt_content)
        assert len(validation_errors) == 0, f"SRT validation failed: {validation_errors}"
        
        # Check content structure
        blocks = srt_content.strip().split('\n\n')
        assert len(blocks) == len(self.realistic_alignment_data.word_segments)
        
        # Check individual word timing
        assert "00:00:00,120 --> 00:00:00,580" in srt_content  # Welcome
        assert "00:00:00,890 --> 00:00:01,340" in srt_content  # lyric
        assert "00:00:06,120 --> 00:00:06,890" in srt_content  # synchronized
        
        # Check individual words are present
        assert "\nWelcome\n" in srt_content
        assert "\nlyric\n" in srt_content
        assert "\nsynchronized\n" in srt_content
    
    def test_grouped_words_srt_generation(self):
        """Test grouped words SRT generation with realistic data."""
        srt_content = self.subtitle_generator.generate_srt_grouped_words(
            self.realistic_alignment_data, 
            words_per_subtitle=4
        )
        
        # Validate the generated SRT
        validation_errors = self.srt_exporter.validate_srt_content(srt_content)
        assert len(validation_errors) == 0, f"SRT validation failed: {validation_errors}"
        
        # Check content structure
        blocks = srt_content.strip().split('\n\n')
        expected_blocks = len(self.realistic_alignment_data.word_segments) // 4
        if len(self.realistic_alignment_data.word_segments) % 4 != 0:
            expected_blocks += 1
        assert len(blocks) == expected_blocks
        
        # Check grouped content (words are grouped sequentially)
        assert "Welcome to the lyric" in srt_content
        assert "tool converts audio files" in srt_content
    
    def test_complete_file_generation_workflow(self):
        """Test complete workflow from alignment data to saved SRT files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Generate sentence-level SRT file
            sentence_path = os.path.join(temp_dir, "sentence_subtitles.srt")
            sentence_file = self.subtitle_generator.generate_subtitle_file(
                self.realistic_alignment_data,
                sentence_path,
                ExportFormat.SRT,
                word_level=False
            )
            
            # Generate word-level SRT file
            word_path = os.path.join(temp_dir, "word_subtitles.srt")
            word_file = self.subtitle_generator.generate_subtitle_file(
                self.realistic_alignment_data,
                word_path,
                ExportFormat.SRT,
                word_level=True
            )
            
            # Generate grouped words SRT file
            grouped_path = os.path.join(temp_dir, "grouped_subtitles.srt")
            grouped_file = self.subtitle_generator.generate_subtitle_file(
                self.realistic_alignment_data,
                grouped_path,
                ExportFormat.SRT,
                words_per_subtitle=3
            )
            
            # Verify all files exist
            assert os.path.exists(sentence_path)
            assert os.path.exists(word_path)
            assert os.path.exists(grouped_path)
            
            # Verify file metadata
            assert sentence_file.format == ExportFormat.SRT
            assert word_file.format == ExportFormat.SRT
            assert grouped_file.format == ExportFormat.SRT
            
            assert sentence_file.duration == 11.89
            assert word_file.duration == 11.89
            assert grouped_file.duration == 11.89
            
            # Verify word counts are reasonable
            assert sentence_file.word_count > 0
            assert word_file.word_count > 0
            assert grouped_file.word_count > 0
            
            # Word-level and grouped should have same word count
            assert word_file.word_count == grouped_file.word_count
            
            # Verify file contents are valid SRT
            for file_path in [sentence_path, word_path, grouped_path]:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                validation_errors = self.srt_exporter.validate_srt_content(content)
                assert len(validation_errors) == 0, f"File {file_path} has invalid SRT: {validation_errors}"
    
    def test_processing_options_integration(self):
        """Test integration with ProcessingOptions for SRT generation."""
        # Create processing options that would be used in real workflow
        options = ProcessingOptions(
            model_size=ModelSize.BASE,
            export_formats=[ExportFormat.SRT],
            word_level_srt=True,
            karaoke_mode=False,
            translation_enabled=False,
            output_directory="/tmp/subtitles"
        )
        
        # Verify options are valid
        validation_errors = options.validate()
        assert len(validation_errors) == 0
        
        # Generate SRT based on options
        if options.word_level_srt:
            srt_content = self.subtitle_generator.generate_srt(
                self.realistic_alignment_data, 
                word_level=True
            )
        else:
            srt_content = self.subtitle_generator.generate_srt(
                self.realistic_alignment_data, 
                word_level=False
            )
        
        # Verify content is valid
        validation_errors = self.srt_exporter.validate_srt_content(srt_content)
        assert len(validation_errors) == 0
    
    def test_edge_case_very_short_segments(self):
        """Test SRT generation with very short timing segments."""
        short_alignment_data = AlignmentData(
            segments=[
                Segment(
                    start_time=0.001,
                    end_time=0.123,
                    text="Hi",
                    confidence=0.95,
                    segment_id=1
                )
            ],
            word_segments=[
                WordSegment(word="Hi", start_time=0.001, end_time=0.123, confidence=0.95, segment_id=1)
            ],
            confidence_scores=[0.95],
            audio_duration=0.123,
            source_file="short_audio.wav"
        )
        
        # Test sentence-level
        sentence_srt = self.subtitle_generator.generate_srt(short_alignment_data, word_level=False)
        validation_errors = self.srt_exporter.validate_srt_content(sentence_srt)
        assert len(validation_errors) == 0
        
        # Check timing format for very short durations
        assert "00:00:00,001 --> 00:00:00,123" in sentence_srt
        
        # Test word-level
        word_srt = self.subtitle_generator.generate_srt(short_alignment_data, word_level=True)
        validation_errors = self.srt_exporter.validate_srt_content(word_srt)
        assert len(validation_errors) == 0
    
    def test_edge_case_long_segments(self):
        """Test SRT generation with very long timing segments."""
        long_alignment_data = AlignmentData(
            segments=[
                Segment(
                    start_time=3600.0,  # 1 hour
                    end_time=7323.456,  # 2+ hours
                    text="This is a very long segment that occurs much later in a long audio file.",
                    confidence=0.85,
                    segment_id=1
                )
            ],
            word_segments=[
                WordSegment(word="This", start_time=3600.0, end_time=3600.5, confidence=0.85, segment_id=1),
                WordSegment(word="is", start_time=3600.5, end_time=3600.8, confidence=0.87, segment_id=1),
                WordSegment(word="long", start_time=7320.0, end_time=7323.456, confidence=0.83, segment_id=1),
            ],
            confidence_scores=[0.85],
            audio_duration=7323.456,
            source_file="long_audio.wav"
        )
        
        # Test sentence-level
        sentence_srt = self.subtitle_generator.generate_srt(long_alignment_data, word_level=False)
        validation_errors = self.srt_exporter.validate_srt_content(sentence_srt)
        assert len(validation_errors) == 0
        
        # Check timing format for long durations
        assert "01:00:00,000 --> 02:02:03,456" in sentence_srt
        
        # Test word-level
        word_srt = self.subtitle_generator.generate_srt(long_alignment_data, word_level=True)
        validation_errors = self.srt_exporter.validate_srt_content(word_srt)
        assert len(validation_errors) == 0
    
    def test_special_characters_handling(self):
        """Test SRT generation with special characters and unicode."""
        special_alignment_data = AlignmentData(
            segments=[
                Segment(
                    start_time=0.0,
                    end_time=3.0,
                    text="Café & résumé with émojis 🎵🎤",
                    confidence=0.90,
                    segment_id=1
                ),
                Segment(
                    start_time=3.0,
                    end_time=6.0,
                    text="Quotes \"test\" and 'apostrophes' & symbols!",
                    confidence=0.88,
                    segment_id=2
                )
            ],
            word_segments=[
                WordSegment(word="Café", start_time=0.0, end_time=0.5, confidence=0.90, segment_id=1),
                WordSegment(word="&", start_time=0.5, end_time=0.7, confidence=0.85, segment_id=1),
                WordSegment(word="résumé", start_time=0.7, end_time=1.2, confidence=0.88, segment_id=1),
            ],
            confidence_scores=[0.90, 0.88],
            audio_duration=6.0,
            source_file="special_chars_audio.wav"
        )
        
        # Test sentence-level
        sentence_srt = self.subtitle_generator.generate_srt(special_alignment_data, word_level=False)
        validation_errors = self.srt_exporter.validate_srt_content(sentence_srt)
        assert len(validation_errors) == 0
        
        # Check that special characters are preserved
        assert "Café & résumé with émojis 🎵🎤" in sentence_srt
        assert "Quotes \"test\" and 'apostrophes' & symbols!" in sentence_srt
        
        # Test word-level
        word_srt = self.subtitle_generator.generate_srt(special_alignment_data, word_level=True)
        validation_errors = self.srt_exporter.validate_srt_content(word_srt)
        assert len(validation_errors) == 0