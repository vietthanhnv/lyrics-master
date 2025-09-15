"""
Tests for SRT exporter functionality.

This module contains comprehensive tests for the SRTExporter class,
covering sentence-level, word-level, and grouped word subtitle generation.
"""

import pytest
from src.services.srt_exporter import SRTExporter
from src.models.data_models import AlignmentData, Segment, WordSegment


class TestSRTExporter:
    """Test cases for SRTExporter class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.exporter = SRTExporter()
        
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
            ),
            Segment(
                start_time=5.0,
                end_time=7.8,
                text="And this is the final segment.",
                confidence=0.88,
                segment_id=3
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
            confidence_scores=[0.95, 0.92, 0.88],
            audio_duration=7.8,
            source_file="test_audio.wav"
        )
    
    def test_generate_sentence_level_basic(self):
        """Test basic sentence-level SRT generation."""
        result = self.exporter.generate_sentence_level(self.sample_alignment_data)
        
        # Check that result is not empty
        assert result
        
        # Check that it contains expected number of subtitle blocks
        blocks = result.strip().split('\n\n')
        assert len(blocks) == 3
        
        # Check first block format
        first_block = blocks[0]
        lines = first_block.split('\n')
        assert lines[0] == "1"
        assert lines[1] == "00:00:00,000 --> 00:00:02,500"
        assert lines[2] == "Hello world, this is a test."
    
    def test_generate_sentence_level_timing_format(self):
        """Test that timing format is correct in sentence-level SRT."""
        result = self.exporter.generate_sentence_level(self.sample_alignment_data)
        
        # Check timing formats
        assert "00:00:00,000 --> 00:00:02,500" in result
        assert "00:00:02,500 --> 00:00:05,000" in result
        assert "00:00:05,000 --> 00:00:07,800" in result
    
    def test_generate_word_level_basic(self):
        """Test basic word-level SRT generation."""
        result = self.exporter.generate_word_level(self.sample_alignment_data)
        
        # Check that result is not empty
        assert result
        
        # Check that it contains expected number of subtitle blocks
        blocks = result.strip().split('\n\n')
        assert len(blocks) == 6  # Number of word segments
        
        # Check first block format
        first_block = blocks[0]
        lines = first_block.split('\n')
        assert lines[0] == "1"
        assert lines[1] == "00:00:00,000 --> 00:00:00,500"
        assert lines[2] == "Hello"
    
    def test_generate_grouped_words_basic(self):
        """Test grouped words SRT generation."""
        result = self.exporter.generate_grouped_words(self.sample_alignment_data, words_per_subtitle=2)
        
        # Check that result is not empty
        assert result
        
        # Check that it contains expected number of subtitle blocks
        blocks = result.strip().split('\n\n')
        assert len(blocks) == 3  # 6 words / 2 words per subtitle
        
        # Check first block format
        first_block = blocks[0]
        lines = first_block.split('\n')
        assert lines[0] == "1"
        assert lines[1] == "00:00:00,000 --> 00:00:01,000"
        assert lines[2] == "Hello world"
    
    def test_format_timestamp_basic(self):
        """Test timestamp formatting."""
        # Test various timestamp values
        assert self.exporter._format_timestamp(0.0) == "00:00:00,000"
        assert self.exporter._format_timestamp(1.5) == "00:00:01,500"
        assert self.exporter._format_timestamp(65.123) == "00:01:05,123"
        assert self.exporter._format_timestamp(3661.456) == "01:01:01,456"
    
    def test_format_timestamp_edge_cases(self):
        """Test timestamp formatting edge cases."""
        # Test millisecond rounding
        assert self.exporter._format_timestamp(1.9999) == "00:00:02,000"
        assert self.exporter._format_timestamp(0.001) == "00:00:00,001"
        
        # Test large values
        assert self.exporter._format_timestamp(7323.789) == "02:02:03,789"
    
    def test_escape_text_basic(self):
        """Test basic text escaping."""
        # Test normal text
        assert self.exporter._escape_text("Hello world") == "Hello world"
        
        # Test text with extra whitespace
        assert self.exporter._escape_text("  Hello   world  ") == "Hello world"
        
        # Test empty text
        assert self.exporter._escape_text("") == ""
        assert self.exporter._escape_text("   ") == ""
    
    def test_escape_text_html_entities(self):
        """Test HTML entity escaping."""
        assert self.exporter._escape_text("Tom &amp; Jerry") == "Tom & Jerry"
        assert self.exporter._escape_text("&lt;tag&gt;") == "<tag>"
        assert self.exporter._escape_text("&quot;quoted&quot;") == '"quoted"'
        assert self.exporter._escape_text("&#39;apostrophe&#39;") == "'apostrophe'"
    
    def test_escape_text_long_lines(self):
        """Test long line handling."""
        long_text = "This is a very long line that should be split into multiple lines because it exceeds the maximum line length limit"
        result = self.exporter._escape_text(long_text)
        
        # Should contain newlines for line breaks
        assert '\n' in result
        
        # Each line should be reasonably short
        lines = result.split('\n')
        for line in lines:
            assert len(line) <= 80
    
    def test_escape_text_control_characters(self):
        """Test control character removal."""
        text_with_control = "Hello\x00\x01world\x7F"
        result = self.exporter._escape_text(text_with_control)
        assert result == "Helloworld"
    
    def test_validate_srt_content_valid(self):
        """Test validation of valid SRT content."""
        valid_srt = """1
00:00:00,000 --> 00:00:02,500
Hello world

2
00:00:02,500 --> 00:00:05,000
This is a test"""
        
        errors = self.exporter.validate_srt_content(valid_srt)
        assert len(errors) == 0
    
    def test_validate_srt_content_invalid_format(self):
        """Test validation of invalid SRT content."""
        # Missing timing line
        invalid_srt = """1
Hello world

2
00:00:02,500 --> 00:00:05,000
This is a test"""
        
        errors = self.exporter.validate_srt_content(invalid_srt)
        assert len(errors) > 0
        assert any("Insufficient lines" in error for error in errors)
    
    def test_validate_srt_content_invalid_timing(self):
        """Test validation of invalid timing format."""
        invalid_srt = """1
00:00:00 -> 00:00:02,500
Hello world"""
        
        errors = self.exporter.validate_srt_content(invalid_srt)
        assert len(errors) > 0
        assert any("Invalid timing format" in error for error in errors)
    
    def test_validate_srt_content_empty(self):
        """Test validation of empty SRT content."""
        errors = self.exporter.validate_srt_content("")
        assert len(errors) > 0
        assert any("empty" in error.lower() for error in errors)
    
    def test_validate_timestamp_valid(self):
        """Test timestamp validation with valid formats."""
        assert self.exporter._validate_timestamp("00:00:00,000")
        assert self.exporter._validate_timestamp("01:23:45,678")
        assert self.exporter._validate_timestamp("99:59:59,999")
    
    def test_validate_timestamp_invalid(self):
        """Test timestamp validation with invalid formats."""
        assert not self.exporter._validate_timestamp("0:0:0,0")
        assert not self.exporter._validate_timestamp("00:00:00.000")
        assert not self.exporter._validate_timestamp("00:00:00,0000")
        assert not self.exporter._validate_timestamp("invalid")
    
    def test_generate_sentence_level_empty_data(self):
        """Test sentence-level generation with empty data."""
        empty_data = AlignmentData(
            segments=[],
            word_segments=[],
            confidence_scores=[],
            audio_duration=0.0
        )
        
        with pytest.raises(ValueError, match="must contain at least one segment"):
            self.exporter.generate_sentence_level(empty_data)
    
    def test_generate_word_level_empty_data(self):
        """Test word-level generation with empty data."""
        empty_data = AlignmentData(
            segments=[],
            word_segments=[],
            confidence_scores=[],
            audio_duration=0.0
        )
        
        with pytest.raises(ValueError, match="must contain at least one word segment"):
            self.exporter.generate_word_level(empty_data)
    
    def test_generate_grouped_words_invalid_params(self):
        """Test grouped words generation with invalid parameters."""
        with pytest.raises(ValueError, match="words_per_subtitle must be at least 1"):
            self.exporter.generate_grouped_words(self.sample_alignment_data, words_per_subtitle=0)
    
    def test_generate_sentence_level_special_characters(self):
        """Test sentence-level generation with special characters."""
        special_segments = [
            Segment(
                start_time=0.0,
                end_time=2.0,
                text="Special chars: àáâãäåæçèéêë",
                confidence=0.95,
                segment_id=1
            ),
            Segment(
                start_time=2.0,
                end_time=4.0,
                text="Symbols: !@#$%^&*()_+-=[]{}|;':\",./<>?",
                confidence=0.90,
                segment_id=2
            )
        ]
        
        special_data = AlignmentData(
            segments=special_segments,
            word_segments=[],
            confidence_scores=[0.95, 0.90],
            audio_duration=4.0
        )
        
        result = self.exporter.generate_sentence_level(special_data)
        
        # Should not raise exceptions and should contain the special characters
        assert "àáâãäåæçèéêë" in result
        assert "!@#$%^&*()_+-=[]{}|;':\",./<>?" in result
    
    def test_integration_full_workflow(self):
        """Test complete workflow from alignment data to validated SRT."""
        # Generate sentence-level SRT
        srt_content = self.exporter.generate_sentence_level(self.sample_alignment_data)
        
        # Validate the generated content
        errors = self.exporter.validate_srt_content(srt_content)
        assert len(errors) == 0, f"Generated SRT has validation errors: {errors}"
        
        # Check that content has expected structure
        blocks = srt_content.strip().split('\n\n')
        assert len(blocks) == len(self.sample_segments)
        
        # Verify each block has correct format
        for i, block in enumerate(blocks):
            lines = block.split('\n')
            assert len(lines) >= 3
            assert lines[0] == str(i + 1)
            assert ' --> ' in lines[1]
            assert lines[2].strip()  # Non-empty text