"""
Tests for ASS subtitle format exporter.

This module contains comprehensive tests for the ASSExporter class,
covering karaoke subtitle generation, styling options, and format validation.
"""

import pytest
from src.services.ass_exporter import ASSExporter, ASSStyle
from src.models.data_models import AlignmentData, Segment, WordSegment


class TestASSExporter:
    """Test cases for ASSExporter class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.exporter = ASSExporter()
        
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
            WordSegment(word="This", start_time=2.5, end_time=2.8, confidence=0.94, segment_id=2),
            WordSegment(word="is", start_time=2.8, end_time=3.0, confidence=0.92, segment_id=2),
            WordSegment(word="the", start_time=3.0, end_time=3.2, confidence=0.90, segment_id=2),
            WordSegment(word="second", start_time=3.2, end_time=3.7, confidence=0.93, segment_id=2),
            WordSegment(word="segment", start_time=3.7, end_time=5.0, confidence=0.91, segment_id=2),
        ]
        
        self.sample_alignment_data = AlignmentData(
            segments=self.sample_segments,
            word_segments=self.sample_word_segments,
            confidence_scores=[0.95, 0.92],
            audio_duration=5.0,
            source_file="test_audio.wav"
        )
    
    def test_generate_karaoke_subtitles_basic(self):
        """Test basic karaoke subtitle generation."""
        result = self.exporter.generate_karaoke_subtitles(self.sample_alignment_data)
        
        # Check that result is not empty
        assert result
        
        # Check for required ASS sections
        assert "[Script Info]" in result
        assert "[V4+ Styles]" in result
        assert "[Events]" in result
        
        # Check for karaoke timing tags
        assert "\\k" in result
        
        # Check that words are included
        assert "Hello" in result
        assert "world" in result
        assert "test" in result
    
    def test_generate_karaoke_subtitles_with_custom_style(self):
        """Test karaoke subtitle generation with custom styling."""
        style_options = {
            "font_name": "Times New Roman",
            "font_size": 24,
            "bold": False,
            "primary_color": "#FF0000",  # Red
            "karaoke_fill_color": "#00FF00",  # Green
            "alignment": 8  # Top center
        }
        
        result = self.exporter.generate_karaoke_subtitles(self.sample_alignment_data, style_options)
        
        # Check that custom font is used
        assert "Times New Roman" in result
        assert "24" in result
        
        # Check that colors are converted properly (RGB to BGR)
        assert "&H000000FF" in result  # Red converted to BGR
        assert "&H0000FF00" in result  # Green converted to BGR
        
        # Check alignment
        assert ",8," in result  # Alignment value in style line
    
    def test_generate_sentence_level_karaoke(self):
        """Test sentence-level karaoke generation."""
        result = self.exporter.generate_sentence_level_karaoke(self.sample_alignment_data)
        
        # Check that result is not empty
        assert result
        
        # Check for required ASS sections
        assert "[Script Info]" in result
        assert "[V4+ Styles]" in result
        assert "[Events]" in result
        
        # Check for fade effects instead of karaoke timing
        assert "\\fad" in result
        
        # Check that full sentences are included
        assert "Hello world, this is a test." in result
        assert "This is the second segment." in result
    
    def test_generate_karaoke_subtitles_empty_data(self):
        """Test karaoke generation with empty alignment data."""
        empty_data = AlignmentData(
            segments=[],
            word_segments=[],
            confidence_scores=[],
            audio_duration=0.0
        )
        
        with pytest.raises(ValueError, match="must contain at least one word segment"):
            self.exporter.generate_karaoke_subtitles(empty_data)
    
    def test_generate_sentence_level_karaoke_empty_data(self):
        """Test sentence-level generation with empty alignment data."""
        empty_data = AlignmentData(
            segments=[],
            word_segments=[],
            confidence_scores=[],
            audio_duration=0.0
        )
        
        with pytest.raises(ValueError, match="must contain at least one segment"):
            self.exporter.generate_sentence_level_karaoke(empty_data)
    
    def test_format_color_conversion(self):
        """Test color format conversion."""
        # Test hex color conversion
        assert self.exporter._format_color("#FF0000") == "&H000000FF"  # Red
        assert self.exporter._format_color("#00FF00") == "&H0000FF00"  # Green
        assert self.exporter._format_color("#0000FF") == "&H00FF0000"  # Blue
        
        # Test short hex format
        assert self.exporter._format_color("#F00") == "&H000000FF"  # Red
        
        # Test ASS format passthrough
        assert self.exporter._format_color("&H00FFFFFF") == "&H00FFFFFF"
        
        # Test invalid format fallback
        assert self.exporter._format_color("invalid") == "&H00FFFFFF"
    
    def test_format_ass_timestamp(self):
        """Test ASS timestamp formatting."""
        # Test basic formatting
        assert self.exporter._format_ass_timestamp(0.0) == "0:00:00.00"
        assert self.exporter._format_ass_timestamp(1.5) == "0:00:01.50"
        assert self.exporter._format_ass_timestamp(65.25) == "0:01:05.25"
        assert self.exporter._format_ass_timestamp(3661.75) == "1:01:01.75"
        
        # Test precision handling
        assert self.exporter._format_ass_timestamp(1.234) == "0:00:01.23"
        assert self.exporter._format_ass_timestamp(1.236) == "0:00:01.24"
    
    def test_escape_ass_text(self):
        """Test ASS text escaping."""
        # Test basic escaping
        assert self.exporter._escape_ass_text("Hello world") == "Hello world"
        
        # Test ASS-specific character escaping
        assert self.exporter._escape_ass_text("Hello {world}") == "Hello \\{world\\}"
        assert self.exporter._escape_ass_text("Hello\\world") == "Hello\\\\world"
        
        # Test line break handling
        assert self.exporter._escape_ass_text("Hello\nworld") == "Hello\\Nworld"
        assert self.exporter._escape_ass_text("Hello\r\nworld") == "Hello\\Nworld"
        
        # Test whitespace normalization
        assert self.exporter._escape_ass_text("Hello   world") == "Hello world"
        assert self.exporter._escape_ass_text("  Hello world  ") == "Hello world"
        
        # Test empty input
        assert self.exporter._escape_ass_text("") == ""
        assert self.exporter._escape_ass_text(None) == ""
    
    def test_create_style_from_options(self):
        """Test style creation from options dictionary."""
        options = {
            "font_name": "Helvetica",
            "font_size": 18,
            "bold": False,
            "italic": True,
            "primary_color": "#FFFFFF",
            "alignment": 5,
            "margin_left": 20,
            "outline_width": 1.5,
            "transition_duration": 0.2
        }
        
        style = self.exporter._create_style_from_options(options)
        
        assert style.font_name == "Helvetica"
        assert style.font_size == 18
        assert style.bold is False
        assert style.italic is True
        assert style.primary_color == "&H00FFFFFF"
        assert style.alignment == 5
        assert style.margin_left == 20
        assert style.outline_width == 1.5
        assert style.transition_duration == 0.2
    
    def test_create_style_from_none_options(self):
        """Test style creation with None options."""
        style = self.exporter._create_style_from_options(None)
        
        # Should return default style
        assert style.font_name == "Arial"
        assert style.font_size == 20
        assert style.bold is True
    
    def test_group_words_by_segments(self):
        """Test grouping words by segments."""
        grouped = self.exporter._group_words_by_segments(self.sample_alignment_data)
        
        # Should have two groups (segment 1 and 2)
        assert len(grouped) == 2
        assert 1 in grouped
        assert 2 in grouped
        
        # Check segment 1 words
        segment1, words1 = grouped[1]
        assert segment1.segment_id == 1
        assert len(words1) == 6  # Hello, world, this, is, a, test
        assert words1[0].word == "Hello"
        assert words1[-1].word == "test"
        
        # Check segment 2 words
        segment2, words2 = grouped[2]
        assert segment2.segment_id == 2
        assert len(words2) == 5  # This, is, the, second, segment
        assert words2[0].word == "This"
        assert words2[-1].word == "segment"
    
    def test_generate_karaoke_text(self):
        """Test karaoke text generation with timing."""
        words = self.sample_word_segments[:3]  # First 3 words
        segment_start = 0.0
        style = ASSStyle()
        
        result = self.exporter._generate_karaoke_text(words, segment_start, style)
        
        # Check that karaoke timing tags are present
        assert "\\k" in result
        
        # Check that words are included
        assert "Hello" in result
        assert "world" in result
        assert "this" in result
        
        # Check that spaces are preserved between words
        assert " " in result
    
    def test_validate_ass_content_valid(self):
        """Test validation of valid ASS content."""
        valid_content = self.exporter.generate_karaoke_subtitles(self.sample_alignment_data)
        errors = self.exporter.validate_ass_content(valid_content)
        
        assert len(errors) == 0
    
    def test_validate_ass_content_empty(self):
        """Test validation of empty ASS content."""
        errors = self.exporter.validate_ass_content("")
        
        assert len(errors) > 0
        assert any("empty" in error.lower() for error in errors)
    
    def test_validate_ass_content_missing_sections(self):
        """Test validation of ASS content with missing sections."""
        incomplete_content = "[Script Info]\nTitle: Test"
        errors = self.exporter.validate_ass_content(incomplete_content)
        
        assert len(errors) > 0
        assert any("[V4+ Styles]" in error for error in errors)
        assert any("[Events]" in error for error in errors)
    
    def test_validate_ass_content_no_styles(self):
        """Test validation of ASS content with no style definitions."""
        content_no_styles = """[Script Info]
Title: Test

[V4+ Styles]
Format: Name, Fontname, Fontsize

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"""
        
        errors = self.exporter.validate_ass_content(content_no_styles)
        
        assert len(errors) > 0
        assert any("style definitions" in error.lower() for error in errors)
    
    def test_validate_ass_content_no_dialogue(self):
        """Test validation of ASS content with no dialogue lines."""
        content_no_dialogue = """[Script Info]
Title: Test

[V4+ Styles]
Format: Name, Fontname, Fontsize
Style: Default,Arial,20

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"""
        
        errors = self.exporter.validate_ass_content(content_no_dialogue)
        
        assert len(errors) > 0
        assert any("dialogue lines" in error.lower() for error in errors)
    
    def test_get_default_style_options(self):
        """Test getting default style options."""
        options = self.exporter.get_default_style_options()
        
        assert isinstance(options, dict)
        assert "font_name" in options
        assert "font_size" in options
        assert "primary_color" in options
        assert "karaoke_fill_color" in options
        
        # Check default values
        assert options["font_name"] == "Arial"
        assert options["font_size"] == 20
        assert options["bold"] is True
    
    def test_ass_style_dataclass(self):
        """Test ASSStyle dataclass functionality."""
        # Test default values
        style = ASSStyle()
        assert style.font_name == "Arial"
        assert style.font_size == 20
        assert style.bold is True
        assert style.primary_color == "&H00FFFFFF"
        
        # Test custom values
        custom_style = ASSStyle(
            font_name="Helvetica",
            font_size=24,
            bold=False,
            primary_color="&H000000FF"
        )
        assert custom_style.font_name == "Helvetica"
        assert custom_style.font_size == 24
        assert custom_style.bold is False
        assert custom_style.primary_color == "&H000000FF"
    
    def test_integration_karaoke_timing_accuracy(self):
        """Test that karaoke timing is accurate for word highlighting."""
        # Create precise word segments
        precise_words = [
            WordSegment(word="One", start_time=0.0, end_time=1.0, confidence=0.95, segment_id=1),
            WordSegment(word="Two", start_time=1.0, end_time=2.0, confidence=0.95, segment_id=1),
            WordSegment(word="Three", start_time=2.0, end_time=3.0, confidence=0.95, segment_id=1),
        ]
        
        precise_segments = [
            Segment(start_time=0.0, end_time=3.0, text="One Two Three", confidence=0.95, segment_id=1)
        ]
        
        precise_data = AlignmentData(
            segments=precise_segments,
            word_segments=precise_words,
            confidence_scores=[0.95],
            audio_duration=3.0
        )
        
        result = self.exporter.generate_karaoke_subtitles(precise_data)
        
        # Check that timing tags reflect the 1-second duration for each word
        # Each word should have \k100 (100 centiseconds = 1 second)
        assert "\\k100" in result
        
        # Check that all words are present
        assert "One" in result
        assert "Two" in result
        assert "Three" in result
    
    def test_integration_multiple_segments_karaoke(self):
        """Test karaoke generation with multiple segments."""
        result = self.exporter.generate_karaoke_subtitles(self.sample_alignment_data)
        
        # Should have dialogue lines for both segments
        dialogue_lines = [line for line in result.split('\n') if line.startswith('Dialogue:')]
        assert len(dialogue_lines) == 2
        
        # Check timing for both segments (ASS format uses different separator)
        assert "0:00:00.00" in result
        assert "0:00:02.50" in result
        assert "0:00:05.00" in result
    
    def test_edge_case_very_short_words(self):
        """Test handling of very short word durations."""
        short_words = [
            WordSegment(word="I", start_time=0.0, end_time=0.05, confidence=0.95, segment_id=1),  # 50ms
            WordSegment(word="am", start_time=0.05, end_time=0.08, confidence=0.95, segment_id=1),  # 30ms
        ]
        
        short_segments = [
            Segment(start_time=0.0, end_time=0.08, text="I am", confidence=0.95, segment_id=1)
        ]
        
        short_data = AlignmentData(
            segments=short_segments,
            word_segments=short_words,
            confidence_scores=[0.95],
            audio_duration=0.08
        )
        
        result = self.exporter.generate_karaoke_subtitles(short_data)
        
        # Should handle very short durations gracefully
        assert result
        assert "\\k" in result
        assert "I" in result
        assert "am" in result