"""
Integration tests for ASS subtitle generation.

This module contains integration tests that verify the complete ASS subtitle
generation workflow from alignment data to final ASS files.
"""

import pytest
import tempfile
import os
from pathlib import Path

from src.services.subtitle_generator import SubtitleGenerator
from src.services.ass_exporter import ASSExporter, ASSStyle
from src.models.data_models import AlignmentData, Segment, WordSegment, ExportFormat


class TestASSIntegration:
    """Integration test cases for ASS subtitle generation."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.generator = SubtitleGenerator()
        self.ass_exporter = ASSExporter()
        
        # Create comprehensive test data
        self.test_segments = [
            Segment(
                start_time=0.0,
                end_time=3.5,
                text="Welcome to the karaoke test.",
                confidence=0.95,
                segment_id=1
            ),
            Segment(
                start_time=3.5,
                end_time=7.0,
                text="This demonstrates word-level highlighting.",
                confidence=0.92,
                segment_id=2
            ),
            Segment(
                start_time=7.0,
                end_time=10.0,
                text="Perfect for karaoke videos!",
                confidence=0.94,
                segment_id=3
            )
        ]
        
        self.test_word_segments = [
            # Segment 1 words
            WordSegment(word="Welcome", start_time=0.0, end_time=0.6, confidence=0.95, segment_id=1),
            WordSegment(word="to", start_time=0.6, end_time=0.8, confidence=0.93, segment_id=1),
            WordSegment(word="the", start_time=0.8, end_time=1.0, confidence=0.91, segment_id=1),
            WordSegment(word="karaoke", start_time=1.0, end_time=1.8, confidence=0.96, segment_id=1),
            WordSegment(word="test", start_time=1.8, end_time=3.5, confidence=0.94, segment_id=1),
            
            # Segment 2 words
            WordSegment(word="This", start_time=3.5, end_time=3.8, confidence=0.92, segment_id=2),
            WordSegment(word="demonstrates", start_time=3.8, end_time=4.8, confidence=0.90, segment_id=2),
            WordSegment(word="word-level", start_time=4.8, end_time=5.5, confidence=0.89, segment_id=2),
            WordSegment(word="highlighting", start_time=5.5, end_time=7.0, confidence=0.93, segment_id=2),
            
            # Segment 3 words
            WordSegment(word="Perfect", start_time=7.0, end_time=7.5, confidence=0.94, segment_id=3),
            WordSegment(word="for", start_time=7.5, end_time=7.7, confidence=0.92, segment_id=3),
            WordSegment(word="karaoke", start_time=7.7, end_time=8.5, confidence=0.95, segment_id=3),
            WordSegment(word="videos", start_time=8.5, end_time=10.0, confidence=0.93, segment_id=3),
        ]
        
        self.test_alignment_data = AlignmentData(
            segments=self.test_segments,
            word_segments=self.test_word_segments,
            confidence_scores=[0.95, 0.92, 0.94],
            audio_duration=10.0,
            source_file="karaoke_test.wav"
        )
    
    def test_complete_ass_karaoke_workflow(self):
        """Test complete ASS karaoke generation workflow."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = os.path.join(temp_dir, "karaoke_test.ass")
            
            # Generate ASS subtitle file
            subtitle_file = self.generator.generate_subtitle_file(
                self.test_alignment_data,
                output_path,
                ExportFormat.ASS
            )
            
            # Verify file was created
            assert os.path.exists(output_path)
            assert subtitle_file.path == output_path
            assert subtitle_file.format == ExportFormat.ASS
            
            # Read and verify file content
            with open(output_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Verify ASS structure
            assert "[Script Info]" in content
            assert "[V4+ Styles]" in content
            assert "[Events]" in content
            
            # Verify karaoke timing tags
            assert "\\k" in content
            
            # Verify all words are present
            for word_segment in self.test_word_segments:
                assert word_segment.word in content
            
            # Verify timing accuracy
            assert "0:00:00.00" in content  # Start time
            assert "0:00:10.00" in content  # End time
    
    def test_ass_karaoke_with_custom_styling(self):
        """Test ASS karaoke generation with custom styling options."""
        custom_style = {
            "font_name": "Comic Sans MS",
            "font_size": 28,
            "bold": False,
            "italic": True,
            "primary_color": "#FFFFFF",
            "karaoke_fill_color": "#FFD700",  # Gold
            "karaoke_border_color": "#FF4500",  # Orange Red
            "alignment": 8,  # Top center
            "margin_vertical": 50,
            "outline_width": 3.0,
            "transition_duration": 0.2
        }
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = os.path.join(temp_dir, "custom_karaoke.ass")
            
            # Generate ASS content with custom styling
            content = self.generator.generate_ass_karaoke(
                self.test_alignment_data,
                custom_style
            )
            
            # Save to file
            self.generator.save_subtitle_file(content, output_path, ExportFormat.ASS)
            
            # Verify custom styling is applied
            assert "Comic Sans MS" in content
            assert "28" in content  # Font size
            assert "&H00FFFFFF" in content  # White (RGB to BGR)
            assert "&H0000D7FF" in content  # Gold (RGB to BGR)
            assert "&H000045FF" in content  # Orange Red (RGB to BGR)
            assert ",8," in content  # Top center alignment
            assert "3.0" in content  # Outline width
    
    def test_ass_sentence_level_generation(self):
        """Test ASS sentence-level subtitle generation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = os.path.join(temp_dir, "sentence_karaoke.ass")
            
            # Generate sentence-level ASS content
            content = self.ass_exporter.generate_sentence_level_karaoke(self.test_alignment_data)
            
            # Save to file
            self.generator.save_subtitle_file(content, output_path, ExportFormat.ASS)
            
            # Verify file was created
            assert os.path.exists(output_path)
            
            # Verify content structure
            assert "[Script Info]" in content
            assert "[V4+ Styles]" in content
            assert "[Events]" in content
            
            # Verify fade effects instead of karaoke timing
            assert "\\fad" in content
            
            # Verify full sentences are present
            for segment in self.test_segments:
                assert segment.text in content
    
    def test_ass_validation_integration(self):
        """Test ASS content validation in integration context."""
        # Generate valid ASS content
        valid_content = self.generator.generate_ass_karaoke(self.test_alignment_data)
        
        # Validate the generated content
        validation_errors = self.ass_exporter.validate_ass_content(valid_content)
        assert len(validation_errors) == 0, f"Validation errors: {validation_errors}"
        
        # Test with invalid content
        invalid_content = "This is not valid ASS content"
        validation_errors = self.ass_exporter.validate_ass_content(invalid_content)
        assert len(validation_errors) > 0
    
    def test_ass_timing_precision(self):
        """Test timing precision in ASS karaoke generation."""
        # Create precise timing test data
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
        
        # Generate ASS content
        content = self.generator.generate_ass_karaoke(precise_data)
        
        # Verify timing precision
        # Each word should have \k100 (100 centiseconds = 1 second)
        assert "\\k100" in content
        
        # Verify timestamp formatting
        assert "0:00:00.00" in content
        assert "0:00:03.00" in content
    
    def test_ass_special_characters_handling(self):
        """Test handling of special characters in ASS format."""
        # Create test data with special characters
        special_segments = [
            Segment(
                start_time=0.0,
                end_time=2.0,
                text="Hello {world} & \"friends\"!",
                confidence=0.95,
                segment_id=1
            )
        ]
        
        special_words = [
            WordSegment(word="Hello", start_time=0.0, end_time=0.5, confidence=0.95, segment_id=1),
            WordSegment(word="{world}", start_time=0.5, end_time=1.0, confidence=0.95, segment_id=1),
            WordSegment(word="&", start_time=1.0, end_time=1.2, confidence=0.95, segment_id=1),
            WordSegment(word="\"friends\"!", start_time=1.2, end_time=2.0, confidence=0.95, segment_id=1),
        ]
        
        special_data = AlignmentData(
            segments=special_segments,
            word_segments=special_words,
            confidence_scores=[0.95],
            audio_duration=2.0
        )
        
        # Generate ASS content
        content = self.generator.generate_ass_karaoke(special_data)
        
        # Verify special characters are properly escaped
        assert "\\{world\\}" in content
        assert "&" in content  # Should be preserved
        assert "\"friends\"!" in content  # Should be preserved
        
        # Verify content is still valid
        validation_errors = self.ass_exporter.validate_ass_content(content)
        assert len(validation_errors) == 0
    
    def test_ass_multiline_text_handling(self):
        """Test handling of multiline text in ASS format."""
        # Create test data with line breaks
        multiline_segments = [
            Segment(
                start_time=0.0,
                end_time=3.0,
                text="First line\nSecond line",
                confidence=0.95,
                segment_id=1
            )
        ]
        
        multiline_words = [
            WordSegment(word="First", start_time=0.0, end_time=0.5, confidence=0.95, segment_id=1),
            WordSegment(word="line", start_time=0.5, end_time=1.0, confidence=0.95, segment_id=1),
            WordSegment(word="Second", start_time=1.5, end_time=2.0, confidence=0.95, segment_id=1),
            WordSegment(word="line", start_time=2.0, end_time=3.0, confidence=0.95, segment_id=1),
        ]
        
        multiline_data = AlignmentData(
            segments=multiline_segments,
            word_segments=multiline_words,
            confidence_scores=[0.95],
            audio_duration=3.0
        )
        
        # Generate ASS content (karaoke mode uses word-level timing)
        content = self.generator.generate_ass_karaoke(multiline_data)
        
        # For karaoke mode, words are processed individually, so line breaks
        # in the original segment text don't appear in the karaoke output
        # This is correct behavior - karaoke focuses on word timing
        assert "First" in content
        assert "line" in content
        assert "Second" in content
        
        # Test sentence-level mode which should preserve line breaks
        sentence_content = self.ass_exporter.generate_sentence_level_karaoke(multiline_data)
        assert "\\N" in sentence_content  # Line breaks should be converted in sentence mode
        
        # Verify content is still valid
        validation_errors = self.ass_exporter.validate_ass_content(content)
        assert len(validation_errors) == 0
    
    def test_ass_performance_with_large_dataset(self):
        """Test ASS generation performance with larger datasets."""
        # Create a larger dataset (simulate a full song)
        large_segments = []
        large_words = []
        
        for i in range(20):  # 20 segments
            start_time = i * 5.0
            end_time = (i + 1) * 5.0
            
            segment = Segment(
                start_time=start_time,
                end_time=end_time,
                text=f"This is segment number {i + 1} with some test text.",
                confidence=0.90 + (i % 10) * 0.01,
                segment_id=i + 1
            )
            large_segments.append(segment)
            
            # Add 8 words per segment
            words_per_segment = ["This", "is", "segment", "number", str(i + 1), "with", "test", "text"]
            for j, word in enumerate(words_per_segment):
                word_start = start_time + j * 0.6
                word_end = word_start + 0.5
                
                word_segment = WordSegment(
                    word=word,
                    start_time=word_start,
                    end_time=word_end,
                    confidence=0.90 + (j % 10) * 0.01,
                    segment_id=i + 1
                )
                large_words.append(word_segment)
        
        large_data = AlignmentData(
            segments=large_segments,
            word_segments=large_words,
            confidence_scores=[0.95] * 20,
            audio_duration=100.0
        )
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = os.path.join(temp_dir, "large_karaoke.ass")
            
            # Generate ASS file (should complete without errors)
            subtitle_file = self.generator.generate_subtitle_file(
                large_data,
                output_path,
                ExportFormat.ASS
            )
            
            # Verify file was created and has reasonable size
            assert os.path.exists(output_path)
            file_size = os.path.getsize(output_path)
            assert file_size > 1000  # Should be substantial content
            
            # Verify content structure is maintained
            with open(output_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            assert "[Script Info]" in content
            assert "[V4+ Styles]" in content
            assert "[Events]" in content
            
            # Should have 20 dialogue lines
            dialogue_lines = [line for line in content.split('\n') if line.startswith('Dialogue:')]
            assert len(dialogue_lines) == 20
    
    def test_ass_export_format_compatibility(self):
        """Test ASS export format compatibility with standard players."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = os.path.join(temp_dir, "compatibility_test.ass")
            
            # Generate ASS file
            subtitle_file = self.generator.generate_subtitle_file(
                self.test_alignment_data,
                output_path,
                ExportFormat.ASS
            )
            
            # Read the generated file
            with open(output_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Verify compatibility requirements
            
            # 1. Proper script info section
            assert "ScriptType: v4.00+" in content
            assert "PlayResX:" in content
            assert "PlayResY:" in content
            
            # 2. Proper style format
            assert "Format: Name, Fontname, Fontsize" in content
            assert "Style: Default," in content or "Style: Karaoke," in content
            
            # 3. Proper events format
            assert "Format: Layer, Start, End, Style, Name" in content
            assert "Dialogue:" in content
            
            # 4. Proper timestamp format (H:MM:SS.cc)
            import re
            timestamp_pattern = r'\d:\d{2}:\d{2}\.\d{2}'
            timestamps = re.findall(timestamp_pattern, content)
            assert len(timestamps) >= 6  # At least start and end for each segment
            
            # 5. Karaoke effects are properly formatted
            karaoke_pattern = r'\\k\d+'
            karaoke_tags = re.findall(karaoke_pattern, content)
            assert len(karaoke_tags) > 0  # Should have karaoke timing tags