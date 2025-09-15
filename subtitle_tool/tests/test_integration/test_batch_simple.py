"""
Simple integration test for batch processing functionality.
"""

import pytest
import tempfile
import os
from unittest.mock import Mock

from src.services.batch_processor import BatchProcessor
from src.models.data_models import (
    ProcessingOptions, ModelSize, ExportFormat, AlignmentData,
    Segment, WordSegment
)


def test_batch_processor_integration():
    """Test basic batch processor integration."""
    # Create mock audio processor
    mock_processor = Mock()
    mock_processor.validate_audio_file.return_value = Mock(
        path="/test/audio.wav",
        format="wav",
        duration=180.0,
        sample_rate=44100,
        channels=2
    )
    mock_processor.separate_vocals.return_value = "/tmp/vocals.wav"
    mock_processor.transcribe_with_alignment.return_value = AlignmentData(
        segments=[Segment(0.0, 5.0, "Test text", 0.95, 0)],
        word_segments=[WordSegment("Test", 0.0, 1.0, 0.95, 0)],
        confidence_scores=[0.95],
        audio_duration=180.0
    )
    
    # Create batch processor
    batch_processor = BatchProcessor(audio_processor=mock_processor)
    
    # Create temporary files
    temp_files = []
    for i in range(2):
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
            f.write(b"fake audio data")
            temp_files.append(f.name)
    
    try:
        # Add files to queue
        batch_processor.add_files_to_queue(temp_files)
        
        # Process batch
        options = ProcessingOptions(
            model_size=ModelSize.BASE,
            export_formats=[ExportFormat.SRT],
            output_directory="/tmp"
        )
        
        result = batch_processor.process_batch(options)
        
        # Verify results
        assert result.total_files == 2
        assert result.successful_files == 2
        assert result.failed_files == 0
        assert result.success_rate() == 100.0
        
    finally:
        # Cleanup
        for file_path in temp_files:
            try:
                os.unlink(file_path)
            except FileNotFoundError:
                pass