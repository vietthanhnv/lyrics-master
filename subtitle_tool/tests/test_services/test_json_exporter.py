"""
Tests for JSON exporter functionality.
"""

import json
import pytest
from datetime import datetime
from src.services.json_exporter import JSONExporter
from src.models.data_models import AlignmentData, Segment, WordSegment


class TestJSONExporter:
    """Test cases for JSON exporter."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.exporter = JSONExporter()
        
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
                text="JSON export format",
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
            WordSegment(word="JSON", start_time=5.0, end_time=5.5, confidence=0.91, segment_id=3),
            WordSegment(word="export", start_time=5.5, end_time=6.0, confidence=0.89, segment_id=3),
            WordSegment(word="format", start_time=6.0, end_time=6.5, confidence=0.93, segment_id=3),
        ]
        
        # Create test alignment data
        self.test_alignment_data = AlignmentData(
            segments=self.test_segments,
            word_segments=self.test_word_segments,
            confidence_scores=[0.95, 0.88, 0.92],
            audio_duration=7.2,
            source_file="test_audio.wav"
        )
    
    def test_export_alignment_data_basic(self):
        """Test basic alignment data export."""
        result = self.exporter.export_alignment_data(self.test_alignment_data)
        
        # Parse JSON to verify structure
        data = json.loads(result)
        
        # Check main structure
        assert "metadata" in data
        assert "segments" in data
        assert "word_segments" in data
        assert "confidence_scores" in data
        assert "audio" in data
        assert "statistics" in data
        
        # Check segments
        assert len(data["segments"]) == 3
        assert data["segments"][0]["text"] == "Hello world"
        assert data["segments"][0]["start_time"] == 0.0
        assert data["segments"][0]["end_time"] == 2.5
        
        # Check word segments
        assert len(data["word_segments"]) == 9
        assert data["word_segments"][0]["word"] == "Hello"
        
        # Check audio info
        assert data["audio"]["duration"] == 7.2
        assert data["audio"]["source_file"] == "test_audio.wav"
    
    def test_export_alignment_data_without_metadata(self):
        """Test alignment data export without metadata."""
        result = self.exporter.export_alignment_data(
            self.test_alignment_data, 
            include_metadata=False
        )
        
        data = json.loads(result)
        assert "metadata" not in data
        assert "segments" in data
        assert "word_segments" in data
    
    def test_export_alignment_data_without_statistics(self):
        """Test alignment data export without statistics."""
        result = self.exporter.export_alignment_data(
            self.test_alignment_data, 
            include_statistics=False
        )
        
        data = json.loads(result)
        assert "statistics" not in data
        assert "segments" in data
        assert "word_segments" in data
    
    def test_export_segments_only(self):
        """Test segments-only export."""
        result = self.exporter.export_segments_only(self.test_alignment_data)
        
        data = json.loads(result)
        
        # Check structure
        assert "segments" in data
        assert "total_segments" in data
        assert "audio_duration" in data
        assert "word_segments" not in data
        
        # Check content
        assert data["total_segments"] == 3
        assert data["audio_duration"] == 7.2
        assert len(data["segments"]) == 3
    
    def test_export_words_only(self):
        """Test words-only export."""
        result = self.exporter.export_words_only(self.test_alignment_data)
        
        data = json.loads(result)
        
        # Check structure
        assert "word_segments" in data
        assert "total_words" in data
        assert "audio_duration" in data
        assert "segments" not in data
        
        # Check content
        assert data["total_words"] == 9
        assert data["audio_duration"] == 7.2
        assert len(data["word_segments"]) == 9
    
    def test_export_subtitle_format_segments(self):
        """Test subtitle format export with segments."""
        result = self.exporter.export_subtitle_format(self.test_alignment_data, "segments")
        
        data = json.loads(result)
        
        # Check structure
        assert data["format"] == "subtitle_json"
        assert data["version"] == "1.0"
        assert "subtitles" in data
        assert "words" not in data
        
        # Check subtitles
        assert len(data["subtitles"]) == 3
        subtitle = data["subtitles"][0]
        assert subtitle["id"] == 1
        assert subtitle["text"] == "Hello world"
        assert subtitle["start"] == 0.0
        assert subtitle["end"] == 2.5
        assert "duration" in subtitle
        assert "confidence" in subtitle
    
    def test_export_subtitle_format_words(self):
        """Test subtitle format export with words."""
        result = self.exporter.export_subtitle_format(self.test_alignment_data, "words")
        
        data = json.loads(result)
        
        # Check structure
        assert "words" in data
        assert "subtitles" not in data
        
        # Check words
        assert len(data["words"]) == 9
        word = data["words"][0]
        assert word["id"] == 1
        assert word["word"] == "Hello"
        assert word["start"] == 0.0
        assert word["end"] == 0.5
        assert "duration" in word
        assert "confidence" in word
        assert "segment_id" in word
    
    def test_export_subtitle_format_both(self):
        """Test subtitle format export with both segments and words."""
        result = self.exporter.export_subtitle_format(self.test_alignment_data, "both")
        
        data = json.loads(result)
        
        # Check structure
        assert "subtitles" in data
        assert "words" in data
        
        # Check content
        assert len(data["subtitles"]) == 3
        assert len(data["words"]) == 9
    
    def test_export_for_editing(self):
        """Test export optimized for editing."""
        result = self.exporter.export_for_editing(self.test_alignment_data)
        
        data = json.loads(result)
        
        # Check structure
        assert "project" in data
        assert "segments" in data
        assert "settings" in data
        
        # Check project info
        project = data["project"]
        assert "name" in project
        assert "created" in project
        assert project["audio_file"] == "test_audio.wav"
        assert project["duration"] == 7.2
        
        # Check segments with words
        segments = data["segments"]
        assert len(segments) == 3
        
        segment = segments[0]
        assert segment["id"] == 1
        assert segment["text"] == "Hello world"
        assert segment["editable"] == True
        assert "words" in segment
        assert len(segment["words"]) == 2  # "Hello" and "world"
        
        # Check word structure
        word = segment["words"][0]
        assert word["word"] == "Hello"
        assert word["editable"] == True
        assert "start_time" in word
        assert "end_time" in word
        assert "confidence" in word
    
    def test_segment_to_dict(self):
        """Test segment to dictionary conversion."""
        segment = self.test_segments[0]
        result = self.exporter._segment_to_dict(segment)
        
        assert result["start_time"] == 0.0
        assert result["end_time"] == 2.5
        assert result["duration"] == 2.5
        assert result["text"] == "Hello world"
        assert result["confidence"] == 0.95
        assert result["segment_id"] == 1
    
    def test_word_segment_to_dict(self):
        """Test word segment to dictionary conversion."""
        word_segment = self.test_word_segments[0]
        result = self.exporter._word_segment_to_dict(word_segment)
        
        assert result["word"] == "Hello"
        assert result["start_time"] == 0.0
        assert result["end_time"] == 0.5
        assert result["duration"] == 0.5
        assert result["confidence"] == 0.95
        assert result["segment_id"] == 1
    
    def test_generate_metadata(self):
        """Test metadata generation."""
        result = self.exporter._generate_metadata(self.test_alignment_data)
        
        assert "export_timestamp" in result
        assert result["format_version"] == "1.0"
        assert result["exporter"] == "lyric-to-subtitle-app"
        assert result["total_segments"] == 3
        assert result["total_words"] == 9
        assert result["audio_duration"] == 7.2
        assert result["source_file"] == "test_audio.wav"
        assert "average_confidence" in result
    
    def test_generate_statistics(self):
        """Test statistics generation."""
        result = self.exporter._generate_statistics(self.test_alignment_data)
        
        # Check structure
        assert "segments" in result
        assert "words" in result
        assert "quality" in result
        
        # Check segment statistics
        seg_stats = result["segments"]
        assert seg_stats["count"] == 3
        assert "average_duration" in seg_stats
        assert "min_duration" in seg_stats
        assert "max_duration" in seg_stats
        assert "average_confidence" in seg_stats
        
        # Check word statistics
        word_stats = result["words"]
        assert word_stats["count"] == 9
        assert "average_duration" in word_stats
        
        # Check quality statistics
        quality = result["quality"]
        assert "high_confidence_segments" in quality
        assert "medium_confidence_segments" in quality
        assert "low_confidence_segments" in quality
    
    def test_group_words_by_segments(self):
        """Test grouping words by segments."""
        result = self.exporter._group_words_by_segments(self.test_alignment_data)
        
        # Check that words are grouped correctly
        assert 1 in result  # segment_id 1
        assert 2 in result  # segment_id 2
        
        segment_1_data = result[1]
        segment, words = segment_1_data
        assert segment.segment_id == 1
        assert len(words) == 2  # "Hello" and "world"
        assert words[0].word == "Hello"
        assert words[1].word == "world"
        
        segment_2_data = result[2]
        segment, words = segment_2_data
        assert segment.segment_id == 2
        assert len(words) == 4  # "This", "is", "a", "test"
        
        segment_3_data = result[3]
        segment, words = segment_3_data
        assert segment.segment_id == 3
        assert len(words) == 3  # "JSON", "export", "format"
    
    def test_validate_json_content_valid(self):
        """Test validation of valid JSON content."""
        valid_json = json.dumps({
            "segments": [
                {
                    "start_time": 0.0,
                    "end_time": 2.5,
                    "text": "Hello world"
                }
            ],
            "word_segments": [
                {
                    "word": "Hello",
                    "start_time": 0.0,
                    "end_time": 0.5
                }
            ]
        })
        
        errors = self.exporter.validate_json_content(valid_json)
        assert len(errors) == 0
    
    def test_validate_json_content_invalid_json(self):
        """Test validation of invalid JSON."""
        invalid_json = "{ invalid json }"
        
        errors = self.exporter.validate_json_content(invalid_json)
        assert len(errors) > 0
        assert "Invalid JSON format" in errors[0]
    
    def test_validate_json_content_empty(self):
        """Test validation of empty JSON content."""
        errors = self.exporter.validate_json_content("")
        assert len(errors) > 0
        assert "JSON content is empty" in errors[0]
    
    def test_validate_json_content_missing_fields(self):
        """Test validation of JSON with missing required fields."""
        invalid_json = json.dumps({
            "segments": [
                {
                    "start_time": 0.0,
                    # missing end_time and text
                }
            ]
        })
        
        errors = self.exporter.validate_json_content(invalid_json)
        assert len(errors) > 0
        assert "missing required field" in str(errors)
    
    def test_parse_json_to_alignment_data(self):
        """Test parsing JSON back to AlignmentData."""
        # First export to JSON
        json_content = self.exporter.export_alignment_data(self.test_alignment_data)
        
        # Then parse back
        result = self.exporter.parse_json_to_alignment_data(json_content)
        
        # Check that data is preserved
        assert len(result.segments) == 3
        assert len(result.word_segments) == 9
        assert result.audio_duration == 7.2
        assert result.source_file == "test_audio.wav"
        
        # Check first segment
        segment = result.segments[0]
        assert segment.start_time == 0.0
        assert segment.end_time == 2.5
        assert segment.text == "Hello world"
        assert segment.confidence == 0.95
        
        # Check first word
        word = result.word_segments[0]
        assert word.word == "Hello"
        assert word.start_time == 0.0
        assert word.end_time == 0.5
        assert word.confidence == 0.95
    
    def test_parse_json_invalid_content(self):
        """Test parsing invalid JSON content."""
        with pytest.raises(ValueError, match="Invalid JSON content"):
            self.exporter.parse_json_to_alignment_data("{ invalid }")
    
    def test_export_subtitle_format_invalid_type(self):
        """Test subtitle format export with invalid type."""
        with pytest.raises(ValueError, match="format_type must be"):
            self.exporter.export_subtitle_format(self.test_alignment_data, "invalid")
    
    def test_empty_alignment_data(self):
        """Test handling of empty alignment data."""
        empty_data = AlignmentData(
            segments=[],
            word_segments=[],
            confidence_scores=[],
            audio_duration=0.0
        )
        
        with pytest.raises(ValueError, match="must contain at least one segment"):
            self.exporter.export_segments_only(empty_data)
        
        with pytest.raises(ValueError, match="must contain at least one word segment"):
            self.exporter.export_words_only(empty_data)
    
    def test_none_alignment_data(self):
        """Test handling of None alignment data."""
        with pytest.raises(ValueError, match="cannot be None"):
            self.exporter.export_alignment_data(None)
        
        with pytest.raises(ValueError, match="cannot be None"):
            self.exporter.export_subtitle_format(None)
        
        with pytest.raises(ValueError, match="cannot be None"):
            self.exporter.export_for_editing(None)
    
    def test_unicode_text_handling(self):
        """Test handling of Unicode text in JSON export."""
        unicode_segment = Segment(
            start_time=0.0,
            end_time=2.0,
            text="Unicode: àáâãäåæçèéêë 中文 العربية русский",
            confidence=0.9,
            segment_id=1
        )
        
        unicode_alignment_data = AlignmentData(
            segments=[unicode_segment],
            word_segments=[],
            confidence_scores=[0.9],
            audio_duration=2.0
        )
        
        result = self.exporter.export_alignment_data(unicode_alignment_data)
        
        # Parse back to verify Unicode is preserved
        data = json.loads(result)
        assert "àáâãäåæçèéêë" in data["segments"][0]["text"]
        assert "中文" in data["segments"][0]["text"]
        assert "العربية" in data["segments"][0]["text"]
        assert "русский" in data["segments"][0]["text"]
    
    def test_precision_rounding(self):
        """Test that floating point values are properly rounded."""
        precise_segment = Segment(
            start_time=1.23456789,
            end_time=2.98765432,
            text="Precision test",
            confidence=0.87654321,
            segment_id=1
        )
        
        precise_alignment_data = AlignmentData(
            segments=[precise_segment],
            word_segments=[],
            confidence_scores=[0.87654321],
            audio_duration=2.98765432
        )
        
        result = self.exporter.export_alignment_data(precise_alignment_data)
        data = json.loads(result)
        
        # Check that values are rounded to 3 decimal places
        segment = data["segments"][0]
        assert segment["start_time"] == 1.235
        assert segment["end_time"] == 2.988
        assert segment["confidence"] == 0.877
    
    def test_empty_statistics_handling(self):
        """Test statistics generation with empty data."""
        empty_data = AlignmentData(
            segments=[],
            word_segments=[],
            confidence_scores=[],
            audio_duration=0.0
        )
        
        result = self.exporter._generate_statistics(empty_data)
        assert result == {}  # Should return empty dict for empty data