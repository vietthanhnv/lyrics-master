"""
Tests for VTT exporter functionality.
"""

import pytest
from src.services.vtt_exporter import VTTExporter
from src.models.data_models import AlignmentData, Segment, WordSegment


class TestVTTExporter:
    """Test cases for VTT exporter."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.exporter = VTTExporter()
        
        # Create test segments
        self.test_segments = [
            Segment(
                start_time=0.0,
                end_time=2.5,
                text="Hello world",
                confidence=0.95,
                segment_id=1
            ),
            Segment(
                start_time=2.5,
                end_time=5.0,
                text="This is a test",
                confidence=0.88,
                segment_id=2
            ),
            Segment(
                start_time=5.0,
                end_time=7.2,
                text="VTT subtitle format",
                confidence=0.92,
                segment_id=3
            )
        ]
        
        # Create test word segments
        self.test_word_segments = [
            WordSegment(word="Hello", start_time=0.0, end_time=0.5, confidence=0.95, segment_id=1),
            WordSegment(word="world", start_time=0.5, end_time=1.0, confidence=0.93, segment_id=1),
            WordSegment(word="This", start_time=2.5, end_time=2.8, confidence=0.90, segment_id=2),
            WordSegment(word="is", start_time=2.8, end_time=3.0, confidence=0.88, segment_id=2),
            WordSegment(word="a", start_time=3.0, end_time=3.1, confidence=0.85, segment_id=2),
            WordSegment(word="test", start_time=3.1, end_time=3.5, confidence=0.92, segment_id=2),
        ]
        
        # Create test alignment data
        self.test_alignment_data = AlignmentData(
            segments=self.test_segments,
            word_segments=self.test_word_segments,
            confidence_scores=[0.95, 0.88, 0.92],
            audio_duration=7.2,
            source_file="test_audio.wav"
        )
    
    def test_generate_sentence_level_basic(self):
        """Test basic sentence-level VTT generation."""
        result = self.exporter.generate_sentence_level(self.test_alignment_data)
        
        # Check VTT header
        assert result.startswith("WEBVTT")
        
        # Check timing format
        assert "00:00:00.000 --> 00:00:02.500" in result
        assert "00:00:02.500 --> 00:00:05.000" in result
        assert "00:00:05.000 --> 00:00:07.200" in result
        
        # Check text content
        assert "Hello world" in result
        assert "This is a test" in result
        assert "VTT subtitle format" in result
    
    def test_generate_word_level_basic(self):
        """Test basic word-level VTT generation."""
        result = self.exporter.generate_word_level(self.test_alignment_data)
        
        # Check VTT header
        assert result.startswith("WEBVTT")
        
        # Check word timing
        assert "00:00:00.000 --> 00:00:00.500" in result
        assert "00:00:00.500 --> 00:00:01.000" in result
        
        # Check word content
        assert "Hello" in result
        assert "world" in result
        assert "This" in result
    
    def test_generate_grouped_words(self):
        """Test grouped words VTT generation."""
        result = self.exporter.generate_grouped_words(self.test_alignment_data, words_per_subtitle=2)
        
        # Check VTT header
        assert result.startswith("WEBVTT")
        
        # Check grouped timing (first group: Hello world)
        assert "00:00:00.000 --> 00:00:01.000" in result
        
        # Check grouped text
        assert "Hello world" in result
        assert "This is" in result
    
    def test_generate_with_cues(self):
        """Test VTT generation with cue identifiers."""
        result = self.exporter.generate_with_cues(self.test_alignment_data)
        
        # Check VTT header
        assert result.startswith("WEBVTT")
        
        # Check cue identifiers
        assert "cue-1" in result
        assert "cue-2" in result
        assert "cue-3" in result
    
    def test_generate_with_speaker_labels(self):
        """Test VTT generation with speaker labels."""
        result = self.exporter.generate_with_cues(self.test_alignment_data, include_speaker_labels=True)
        
        # Check VTT header
        assert result.startswith("WEBVTT")
        
        # Check speaker labels
        assert "<v Speaker>Hello world" in result
        assert "<v Speaker>This is a test" in result
    
    def test_add_styling_cues(self):
        """Test VTT generation with CSS styling cues."""
        result = self.exporter.add_styling_cues(self.test_alignment_data)
        
        # Check VTT header
        assert result.startswith("WEBVTT")
        
        # Check styling based on confidence levels
        # High confidence (>= 0.8) should have high-confidence class
        assert "<c.high-confidence>" in result
        assert "</c>" in result
    
    def test_format_timestamp(self):
        """Test timestamp formatting."""
        # Test various timestamp values
        assert self.exporter._format_timestamp(0.0) == "00:00:00.000"
        assert self.exporter._format_timestamp(1.5) == "00:00:01.500"
        assert self.exporter._format_timestamp(65.123) == "00:01:05.123"
        assert self.exporter._format_timestamp(3661.456) == "01:01:01.456"
    
    def test_escape_text(self):
        """Test text escaping for VTT format."""
        # Test basic text
        assert self.exporter._escape_text("Hello world") == "Hello world"
        
        # Test HTML entities
        assert self.exporter._escape_text("&amp; &lt; &gt;") == "& &lt; &gt;"
        
        # Test angle brackets (should be escaped)
        assert self.exporter._escape_text("Hello <test> world") == "Hello &lt;test&gt; world"
        
        # Test multiple whitespace
        assert self.exporter._escape_text("Hello    world") == "Hello world"
        
        # Test newlines
        assert self.exporter._escape_text("Hello\nworld") == "Hello\nworld"
    
    def test_validate_vtt_content_valid(self):
        """Test validation of valid VTT content."""
        valid_vtt = """WEBVTT

00:00:00.000 --> 00:00:02.500
Hello world

00:00:02.500 --> 00:00:05.000
This is a test"""
        
        errors = self.exporter.validate_vtt_content(valid_vtt)
        assert len(errors) == 0
    
    def test_validate_vtt_content_missing_header(self):
        """Test validation of VTT content missing header."""
        invalid_vtt = """00:00:00.000 --> 00:00:02.500
Hello world"""
        
        errors = self.exporter.validate_vtt_content(invalid_vtt)
        assert len(errors) > 0
        assert "must start with 'WEBVTT'" in errors[0]
    
    def test_validate_vtt_content_invalid_timing(self):
        """Test validation of VTT content with invalid timing."""
        invalid_vtt = """WEBVTT

invalid_time --> 00:00:02.500
Hello world"""
        
        errors = self.exporter.validate_vtt_content(invalid_vtt)
        assert len(errors) > 0
        assert "Invalid start timestamp" in str(errors)
    
    def test_validate_vtt_content_empty(self):
        """Test validation of empty VTT content."""
        errors = self.exporter.validate_vtt_content("")
        assert len(errors) > 0
        assert "VTT content is empty" in errors[0]
    
    def test_validate_timestamp_valid(self):
        """Test timestamp validation with valid formats."""
        assert self.exporter._validate_timestamp("00:00:00.000") == True
        assert self.exporter._validate_timestamp("01:23:45.678") == True
        assert self.exporter._validate_timestamp("23:59.999") == True  # Short format
    
    def test_validate_timestamp_invalid(self):
        """Test timestamp validation with invalid formats."""
        assert self.exporter._validate_timestamp("invalid") == False
        assert self.exporter._validate_timestamp("00:00:00,000") == False  # Wrong separator
        assert self.exporter._validate_timestamp("25:00:00.000") == False  # Invalid hour
    
    def test_empty_alignment_data(self):
        """Test handling of empty alignment data."""
        empty_data = AlignmentData(
            segments=[],
            word_segments=[],
            confidence_scores=[],
            audio_duration=0.0
        )
        
        with pytest.raises(ValueError, match="must contain at least one segment"):
            self.exporter.generate_sentence_level(empty_data)
        
        with pytest.raises(ValueError, match="must contain at least one word segment"):
            self.exporter.generate_word_level(empty_data)
    
    def test_none_alignment_data(self):
        """Test handling of None alignment data."""
        with pytest.raises(ValueError, match="must contain at least one segment"):
            self.exporter.generate_sentence_level(None)
        
        with pytest.raises(ValueError, match="must contain at least one word segment"):
            self.exporter.generate_word_level(None)
    
    def test_grouped_words_invalid_parameter(self):
        """Test grouped words with invalid parameters."""
        with pytest.raises(ValueError, match="words_per_subtitle must be at least 1"):
            self.exporter.generate_grouped_words(self.test_alignment_data, words_per_subtitle=0)
        
        with pytest.raises(ValueError, match="words_per_subtitle must be at least 1"):
            self.exporter.generate_grouped_words(self.test_alignment_data, words_per_subtitle=-1)
    
    def test_long_text_line_breaking(self):
        """Test automatic line breaking for long text."""
        long_segment = Segment(
            start_time=0.0,
            end_time=5.0,
            text="This is a very long line of text that should be automatically broken into multiple lines to ensure readability and proper formatting in the VTT subtitle file",
            confidence=0.9,
            segment_id=1
        )
        
        long_alignment_data = AlignmentData(
            segments=[long_segment],
            word_segments=[],
            confidence_scores=[0.9],
            audio_duration=5.0
        )
        
        result = self.exporter.generate_sentence_level(long_alignment_data)
        
        # Check that long text is present and properly formatted
        assert "This is a very long line" in result
        # The text should be broken into multiple lines
        lines = result.split('\n')
        text_lines = [line for line in lines if line and not line.startswith('WEBVTT') and '-->' not in line and not line.startswith('cue-')]
        
        # Should have multiple text lines due to line breaking
        assert len([line for line in text_lines if line.strip()]) >= 1
    
    def test_special_characters_handling(self):
        """Test handling of special characters in text."""
        special_segment = Segment(
            start_time=0.0,
            end_time=2.0,
            text="Special chars: àáâãäåæçèéêë & <tag> \"quotes\" 'apostrophe'",
            confidence=0.9,
            segment_id=1
        )
        
        special_alignment_data = AlignmentData(
            segments=[special_segment],
            word_segments=[],
            confidence_scores=[0.9],
            audio_duration=2.0
        )
        
        result = self.exporter.generate_sentence_level(special_alignment_data)
        
        # Check that special characters are preserved (except escaped ones)
        assert "àáâãäåæçèéêë" in result
        assert "&lt;tag&gt;" in result  # Should be escaped
        assert "\"quotes\"" in result
        assert "'apostrophe'" in result
    
    def test_confidence_based_styling(self):
        """Test styling based on confidence levels."""
        # Create segments with different confidence levels
        segments_varied_confidence = [
            Segment(start_time=0.0, end_time=1.0, text="High confidence", confidence=0.9, segment_id=1),
            Segment(start_time=1.0, end_time=2.0, text="Medium confidence", confidence=0.6, segment_id=2),
            Segment(start_time=2.0, end_time=3.0, text="Low confidence", confidence=0.3, segment_id=3),
        ]
        
        varied_alignment_data = AlignmentData(
            segments=segments_varied_confidence,
            word_segments=[],
            confidence_scores=[0.9, 0.6, 0.3],
            audio_duration=3.0
        )
        
        result = self.exporter.add_styling_cues(varied_alignment_data)
        
        # Check that different confidence levels get different CSS classes
        assert "high-confidence" in result
        assert "medium-confidence" in result
        assert "low-confidence" in result
    
    def test_custom_style_classes(self):
        """Test custom style classes for confidence levels."""
        custom_styles = {
            'high': 'excellent',
            'medium': 'good',
            'low': 'poor'
        }
        
        result = self.exporter.add_styling_cues(self.test_alignment_data, style_classes=custom_styles)
        
        # Check that custom style classes are used
        assert "excellent" in result
        # Should not contain default classes
        assert "high-confidence" not in result