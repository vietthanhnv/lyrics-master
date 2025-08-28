"""
Integration tests for VTT and JSON export functionality.
"""

import json
import tempfile
import os
import pytest
from pathlib import Path

from src.services.subtitle_generator import SubtitleGenerator
from src.models.data_models import AlignmentData, Segment, WordSegment, ExportFormat


class TestVTTJSONIntegration:
    """Integration tests for VTT and JSON export through SubtitleGenerator."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.generator = SubtitleGenerator()
        
        # Create comprehensive test data
        self.test_segments = [
            Segment(
                start_time=0.0,
                end_time=3.2,
                text="Welcome to the integration test",
                confidence=0.95,
                segment_id=1
            ),
            Segment(
                start_time=3.2,
                end_time=6.8,
                text="This tests VTT and JSON export",
                confidence=0.88,
                segment_id=2
            ),
            Segment(
                start_time=6.8,
                end_time=10.5,
                text="With comprehensive validation",
                confidence=0.92,
                segment_id=3
            )
        ]
        
        self.test_word_segments = [
            WordSegment(word="Welcome", start_time=0.0, end_time=0.6, confidence=0.95, segment_id=1),
            WordSegment(word="to", start_time=0.6, end_time=0.8, confidence=0.93, segment_id=1),
            WordSegment(word="the", start_time=0.8, end_time=1.0, confidence=0.91, segment_id=1),
            WordSegment(word="integration", start_time=1.0, end_time=1.8, confidence=0.94, segment_id=1),
            WordSegment(word="test", start_time=1.8, end_time=2.2, confidence=0.96, segment_id=1),
            WordSegment(word="This", start_time=3.2, end_time=3.5, confidence=0.90, segment_id=2),
            WordSegment(word="tests", start_time=3.5, end_time=3.9, confidence=0.88, segment_id=2),
            WordSegment(word="VTT", start_time=3.9, end_time=4.2, confidence=0.85, segment_id=2),
            WordSegment(word="and", start_time=4.2, end_time=4.4, confidence=0.87, segment_id=2),
            WordSegment(word="JSON", start_time=4.4, end_time=4.8, confidence=0.89, segment_id=2),
            WordSegment(word="export", start_time=4.8, end_time=5.3, confidence=0.91, segment_id=2),
        ]
        
        self.test_alignment_data = AlignmentData(
            segments=self.test_segments,
            word_segments=self.test_word_segments,
            confidence_scores=[0.95, 0.88, 0.92],
            audio_duration=10.5,
            source_file="integration_test.wav"
        )
    
    def test_vtt_generation_through_generator(self):
        """Test VTT generation through SubtitleGenerator."""
        result = self.generator.generate_vtt(self.test_alignment_data)
        
        # Verify VTT format
        assert result.startswith("WEBVTT")
        assert "00:00:00.000 --> 00:00:03.200" in result
        assert "Welcome to the integration test" in result
        assert "00:00:03.200 --> 00:00:06.800" in result
        assert "This tests VTT and JSON export" in result
    
    def test_json_generation_through_generator(self):
        """Test JSON generation through SubtitleGenerator."""
        result = self.generator.export_json_alignment(self.test_alignment_data)
        
        # Parse and verify JSON structure
        data = json.loads(result)
        
        assert "metadata" in data
        assert "segments" in data
        assert "word_segments" in data
        assert "audio" in data
        assert "statistics" in data
        
        # Verify content
        assert len(data["segments"]) == 3
        assert len(data["word_segments"]) == 11
        assert data["audio"]["duration"] == 10.5
        assert data["audio"]["source_file"] == "integration_test.wav"
    
    def test_supported_formats_includes_new_formats(self):
        """Test that supported formats include VTT and JSON."""
        supported_formats = self.generator.get_supported_formats()
        
        assert ExportFormat.VTT in supported_formats
        assert ExportFormat.JSON in supported_formats
        assert ExportFormat.SRT in supported_formats
        assert ExportFormat.ASS in supported_formats
    
    def test_file_generation_and_saving_vtt(self):
        """Test complete VTT file generation and saving."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = os.path.join(temp_dir, "test_output.vtt")
            
            # Generate VTT content
            content = self.generator.generate_vtt(self.test_alignment_data)
            
            # Save file
            success = self.generator.save_subtitle_file(content, output_path, ExportFormat.VTT)
            assert success
            
            # Verify file exists and has correct content
            assert os.path.exists(output_path)
            
            with open(output_path, 'r', encoding='utf-8') as f:
                file_content = f.read()
            
            assert file_content.startswith("WEBVTT")
            assert "Welcome to the integration test" in file_content
    
    def test_file_generation_and_saving_json(self):
        """Test complete JSON file generation and saving."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = os.path.join(temp_dir, "test_output.json")
            
            # Generate JSON content
            content = self.generator.export_json_alignment(self.test_alignment_data)
            
            # Save file
            success = self.generator.save_subtitle_file(content, output_path, ExportFormat.JSON)
            assert success
            
            # Verify file exists and has correct content
            assert os.path.exists(output_path)
            
            with open(output_path, 'r', encoding='utf-8') as f:
                file_content = f.read()
            
            # Parse to verify valid JSON
            data = json.loads(file_content)
            assert "segments" in data
            assert "word_segments" in data