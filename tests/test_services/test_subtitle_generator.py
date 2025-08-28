"""
Tests for subtitle generator service.

This module contains comprehensive tests for the SubtitleGenerator class,
covering SRT generation, file operations, and integration functionality.
"""

import pytest
import tempfile
import os
from pathlib import Path

from src.services.subtitle_generator import SubtitleGenerator
from src.models.data_models import AlignmentData, Segment, WordSegment, ExportFormat, SubtitleFile


class TestSubtitleGenerator:
    """Test cases for SubtitleGenerator class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.generator = SubtitleGenerator()
        
        # Create sample alignment data
        self.sample_segments = [
            Segment(
                start_time=0.0,
                end_time=2.5,
                text="Hello world, this is a test.",
                confidence=0.95,
                segment_id=1
            ),
            Segment(
                start_time=2.5,
                end_time=5.0,
                text="This is the second segment.",
                confidence=0.92,
                segment_id=2
            )
        ]
        
        self.sample_word_segments = [
            WordSegment(word="Hello", start_time=0.0, end_time=0.5, confidence=0.95, segment_id=1),
            WordSegment(word="world", start_time=0.5, end_time=1.0, confidence=0.93, segment_id=1),
            WordSegment(word="this", start_time=1.2, end_time=1.5, confidence=0.91, segment_id=1),
            WordSegment(word="is", start_time=1.5, end_time=1.7, confidence=0.94, segment_id=1),
            WordSegment(word="a", start_time=1.7, end_time=1.8, confidence=0.89, segment_id=1),
            WordSegment(word="test", start_time=1.8, end_time=2.5, confidence=0.96, segment_id=1),
        ]
        
        self.sample_alignment_data = AlignmentData(
            segments=self.sample_segments,
            word_segments=self.sample_word_segments,
            confidence_scores=[0.95, 0.92],
            audio_duration=5.0,
            source_file="test_audio.wav"
        )
    
    def test_generate_srt_sentence_level(self):
        """Test sentence-level SRT generation."""
        result = self.generator.generate_srt(self.sample_alignment_data, word_level=False)
        
        # Check that result is not empty
        assert result
        
        # Check that it contains expected content
        assert "Hello world, this is a test." in result
        assert "This is the second segment." in result
        
        # Check timing format
        assert "00:00:00,000 --> 00:00:02,500" in result
        assert "00:00:02,500 --> 00:00:05,000" in result
    
    def test_generate_srt_word_level(self):
        """Test word-level SRT generation."""
        result = self.generator.generate_srt(self.sample_alignment_data, word_level=True)
        
        # Check that result is not empty
        assert result
        
        # Check that it contains individual words
        assert "Hello" in result
        assert "world" in result
        assert "test" in result
        
        # Should have more subtitle blocks than sentence-level
        word_blocks = result.strip().split('\n\n')
        sentence_result = self.generator.generate_srt(self.sample_alignment_data, word_level=False)
        sentence_blocks = sentence_result.strip().split('\n\n')
        assert len(word_blocks) > len(sentence_blocks)
    
    def test_generate_srt_grouped_words(self):
        """Test grouped words SRT generation."""
        result = self.generator.generate_srt_grouped_words(self.sample_alignment_data, words_per_subtitle=2)
        
        # Check that result is not empty
        assert result
        
        # Check that words are grouped
        blocks = result.strip().split('\n\n')
        
        # Should have 3 blocks (6 words / 2 words per subtitle)
        assert len(blocks) == 3
        
        # Check first block contains two words
        first_block = blocks[0]
        lines = first_block.split('\n')
        assert "Hello world" in lines[2]
    
    def test_generate_ass_karaoke_basic(self):
        """Test basic ASS karaoke generation."""
        result = self.generator.generate_ass_karaoke(self.sample_alignment_data)
        
        # Check that result is not empty
        assert result
        
        # Check for ASS format structure
        assert "[Script Info]" in result
        assert "[V4+ Styles]" in result
        assert "[Events]" in result
        
        # Check for karaoke timing tags
        assert "\\k" in result
    
    def test_generate_vtt_implemented(self):
        """Test that VTT generation works correctly."""
        result = self.generator.generate_vtt(self.sample_alignment_data)
        
        # Check VTT format
        assert result.startswith("WEBVTT")
        assert "00:00:00.000 --> 00:00:02.500" in result
        assert "Hello world" in result
    
    def test_export_json_alignment_implemented(self):
        """Test that JSON export works correctly."""
        result = self.generator.export_json_alignment(self.sample_alignment_data)
        
        # Parse and verify JSON structure
        import json
        data = json.loads(result)
        assert "metadata" in data
        assert "segments" in data
        assert "word_segments" in data
    
    def test_save_subtitle_file_success(self):
        """Test successful subtitle file saving."""
        content = self.generator.generate_srt(self.sample_alignment_data)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, "test_subtitles.srt")
            
            result = self.generator.save_subtitle_file(content, file_path, ExportFormat.SRT)
            
            # Check that file was saved successfully
            assert result is True
            assert os.path.exists(file_path)
            
            # Check file content
            with open(file_path, 'r', encoding='utf-8') as f:
                saved_content = f.read()
            assert saved_content == content
    
    def test_save_subtitle_file_creates_directory(self):
        """Test that save_subtitle_file creates necessary directories."""
        content = self.generator.generate_srt(self.sample_alignment_data)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            nested_path = os.path.join(temp_dir, "nested", "dir", "test_subtitles.srt")
            
            result = self.generator.save_subtitle_file(content, nested_path, ExportFormat.SRT)
            
            # Check that file was saved successfully
            assert result is True
            assert os.path.exists(nested_path)
    
    def test_save_subtitle_file_empty_content(self):
        """Test saving empty content raises ValueError."""
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, "test_subtitles.srt")
            
            with pytest.raises(ValueError, match="Content cannot be empty"):
                self.generator.save_subtitle_file("", file_path, ExportFormat.SRT)
            
            with pytest.raises(ValueError, match="Content cannot be empty"):
                self.generator.save_subtitle_file("   ", file_path, ExportFormat.SRT)
    
    def test_save_subtitle_file_empty_path(self):
        """Test saving with empty path raises ValueError."""
        content = self.generator.generate_srt(self.sample_alignment_data)
        
        with pytest.raises(ValueError, match="File path cannot be empty"):
            self.generator.save_subtitle_file(content, "", ExportFormat.SRT)
    
    def test_save_subtitle_file_invalid_srt_content(self):
        """Test saving invalid SRT content raises ValueError."""
        invalid_content = "This is not valid SRT content"
        
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, "test_subtitles.srt")
            
            with pytest.raises(ValueError, match="Invalid SRT content"):
                self.generator.save_subtitle_file(invalid_content, file_path, ExportFormat.SRT)
    
    def test_save_subtitle_file_invalid_ass_content(self):
        """Test saving invalid ASS content raises ValueError."""
        invalid_content = "This is not valid ASS content"
        
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, "test_subtitles.ass")
            
            with pytest.raises(ValueError, match="Invalid ASS content"):
                self.generator.save_subtitle_file(invalid_content, file_path, ExportFormat.ASS)
    
    def test_generate_subtitle_file_srt_sentence(self):
        """Test complete subtitle file generation for SRT sentence-level."""
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, "test_subtitles.srt")
            
            subtitle_file = self.generator.generate_subtitle_file(
                self.sample_alignment_data,
                file_path,
                ExportFormat.SRT,
                word_level=False
            )
            
            # Check SubtitleFile object
            assert isinstance(subtitle_file, SubtitleFile)
            assert subtitle_file.path == file_path
            assert subtitle_file.format == ExportFormat.SRT
            assert subtitle_file.duration == 5.0
            assert subtitle_file.word_count > 0
            
            # Check file was created
            assert os.path.exists(file_path)
    
    def test_generate_subtitle_file_srt_word_level(self):
        """Test complete subtitle file generation for SRT word-level."""
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, "test_subtitles.srt")
            
            subtitle_file = self.generator.generate_subtitle_file(
                self.sample_alignment_data,
                file_path,
                ExportFormat.SRT,
                word_level=True
            )
            
            # Check SubtitleFile object
            assert isinstance(subtitle_file, SubtitleFile)
            assert subtitle_file.format == ExportFormat.SRT
            assert subtitle_file.word_count > 0
            
            # Word-level should have more content
            sentence_file = self.generator.generate_subtitle_file(
                self.sample_alignment_data,
                os.path.join(temp_dir, "sentence.srt"),
                ExportFormat.SRT,
                word_level=False
            )
            
            # Word-level content should be longer
            assert len(subtitle_file.content) > len(sentence_file.content)
    
    def test_generate_subtitle_file_srt_grouped_words(self):
        """Test complete subtitle file generation for SRT grouped words."""
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, "test_subtitles.srt")
            
            subtitle_file = self.generator.generate_subtitle_file(
                self.sample_alignment_data,
                file_path,
                ExportFormat.SRT,
                words_per_subtitle=2
            )
            
            # Check SubtitleFile object
            assert isinstance(subtitle_file, SubtitleFile)
            assert subtitle_file.format == ExportFormat.SRT
            assert subtitle_file.word_count > 0
            
            # Check that content has grouped words
            assert "Hello world" in subtitle_file.content
    
    def test_generate_subtitle_file_ass_format(self):
        """Test subtitle file generation for ASS format."""
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, "test_subtitles.ass")
            
            subtitle_file = self.generator.generate_subtitle_file(
                self.sample_alignment_data,
                file_path,
                ExportFormat.ASS
            )
            
            # Check SubtitleFile object
            assert isinstance(subtitle_file, SubtitleFile)
            assert subtitle_file.path == file_path
            assert subtitle_file.format == ExportFormat.ASS
            assert subtitle_file.duration == 5.0
            assert subtitle_file.word_count > 0
            
            # Check file was created
            assert os.path.exists(file_path)
            
            # Check ASS content structure
            assert "[Script Info]" in subtitle_file.content
            assert "[V4+ Styles]" in subtitle_file.content
            assert "[Events]" in subtitle_file.content
    
    def test_count_words_in_srt_content(self):
        """Test word counting in SRT content."""
        content = self.generator.generate_srt(self.sample_alignment_data, word_level=False)
        word_count = self.generator._count_words_in_content(content, ExportFormat.SRT)
        
        # Should count words from both segments
        # "Hello world, this is a test." = 6 words
        # "This is the second segment." = 5 words
        # Total = 11 words
        assert word_count == 11
    
    def test_get_supported_formats(self):
        """Test getting supported formats."""
        formats = self.generator.get_supported_formats()
        
        assert isinstance(formats, list)
        assert ExportFormat.SRT in formats
        assert ExportFormat.ASS in formats
        # All formats should be supported
        assert ExportFormat.VTT in formats
        assert ExportFormat.JSON in formats
        assert len(formats) == 4
    
    def test_validate_alignment_data_valid(self):
        """Test validation of valid alignment data."""
        errors = self.generator.validate_alignment_data(self.sample_alignment_data)
        assert len(errors) == 0
    
    def test_validate_alignment_data_none(self):
        """Test validation of None alignment data."""
        errors = self.generator.validate_alignment_data(None)
        assert len(errors) > 0
        assert any("None" in error for error in errors)
    
    def test_validate_alignment_data_invalid(self):
        """Test validation of invalid alignment data."""
        invalid_data = AlignmentData(
            segments=[],  # Empty segments
            word_segments=[],
            confidence_scores=[],
            audio_duration=-1.0  # Invalid duration
        )
        
        errors = self.generator.validate_alignment_data(invalid_data)
        assert len(errors) > 0
    
    def test_integration_full_workflow(self):
        """Test complete workflow from alignment data to saved file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Test sentence-level SRT
            sentence_path = os.path.join(temp_dir, "sentence.srt")
            sentence_file = self.generator.generate_subtitle_file(
                self.sample_alignment_data,
                sentence_path,
                ExportFormat.SRT,
                word_level=False
            )
            
            # Test word-level SRT
            word_path = os.path.join(temp_dir, "word.srt")
            word_file = self.generator.generate_subtitle_file(
                self.sample_alignment_data,
                word_path,
                ExportFormat.SRT,
                word_level=True
            )
            
            # Test grouped words SRT
            grouped_path = os.path.join(temp_dir, "grouped.srt")
            grouped_file = self.generator.generate_subtitle_file(
                self.sample_alignment_data,
                grouped_path,
                ExportFormat.SRT,
                words_per_subtitle=3
            )
            
            # Test ASS karaoke format
            ass_path = os.path.join(temp_dir, "karaoke.ass")
            ass_file = self.generator.generate_subtitle_file(
                self.sample_alignment_data,
                ass_path,
                ExportFormat.ASS
            )
            
            # Verify all files were created
            assert os.path.exists(sentence_path)
            assert os.path.exists(word_path)
            assert os.path.exists(grouped_path)
            assert os.path.exists(ass_path)
            
            # Verify file contents are different
            assert sentence_file.content != word_file.content
            assert word_file.content != grouped_file.content
            assert ass_file.content != sentence_file.content
            
            # Verify all have valid word counts
            assert sentence_file.word_count > 0
            assert word_file.word_count > 0
            assert grouped_file.word_count > 0
            assert ass_file.word_count > 0
            
            # Word-level and grouped should have same word count
            assert word_file.word_count == grouped_file.word_count