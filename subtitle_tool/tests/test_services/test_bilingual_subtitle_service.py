"""
Tests for bilingual subtitle service.

This module contains comprehensive tests for the bilingual subtitle generation
functionality, including translation integration and fallback handling.
"""

import pytest
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from src.services.bilingual_subtitle_service import BilingualSubtitleService
from src.services.translation_service import TranslationServiceImpl
from src.services.subtitle_generator import SubtitleGenerator
from src.models.data_models import (
    AlignmentData, Segment, WordSegment, ExportFormat, TranslationService, SubtitleFile
)


class TestBilingualSubtitleService:
    """Test cases for BilingualSubtitleService."""
    
    @pytest.fixture
    def sample_alignment_data(self):
        """Create sample alignment data for testing."""
        segments = [
            Segment(
                start_time=0.0,
                end_time=2.0,
                text="Hello world",
                confidence=0.9,
                segment_id=1
            ),
            Segment(
                start_time=2.0,
                end_time=4.0,
                text="How are you",
                confidence=0.8,
                segment_id=2
            )
        ]
        
        word_segments = [
            WordSegment(word="Hello", start_time=0.0, end_time=0.5, confidence=0.9, segment_id=1),
            WordSegment(word="world", start_time=0.5, end_time=1.0, confidence=0.9, segment_id=1),
            WordSegment(word="How", start_time=2.0, end_time=2.3, confidence=0.8, segment_id=2),
            WordSegment(word="are", start_time=2.3, end_time=2.6, confidence=0.8, segment_id=2),
            WordSegment(word="you", start_time=2.6, end_time=3.0, confidence=0.8, segment_id=2)
        ]
        
        return AlignmentData(
            segments=segments,
            word_segments=word_segments,
            confidence_scores=[0.9, 0.8],
            audio_duration=4.0,
            source_file="test_audio.wav"
        )
    
    @pytest.fixture
    def bilingual_alignment_data(self):
        """Create sample bilingual alignment data for testing."""
        segments = [
            Segment(
                start_time=0.0,
                end_time=2.0,
                text="Hello world\nHola mundo",
                confidence=0.9,
                segment_id=1
            ),
            Segment(
                start_time=2.0,
                end_time=4.0,
                text="How are you\nCómo estás",
                confidence=0.8,
                segment_id=2
            )
        ]
        
        word_segments = [
            WordSegment(word="Hello", start_time=0.0, end_time=0.5, confidence=0.9, segment_id=1),
            WordSegment(word="world", start_time=0.5, end_time=1.0, confidence=0.9, segment_id=1),
            WordSegment(word="How", start_time=2.0, end_time=2.3, confidence=0.8, segment_id=2),
            WordSegment(word="are", start_time=2.3, end_time=2.6, confidence=0.8, segment_id=2),
            WordSegment(word="you", start_time=2.6, end_time=3.0, confidence=0.8, segment_id=2)
        ]
        
        return AlignmentData(
            segments=segments,
            word_segments=word_segments,
            confidence_scores=[0.9, 0.8],
            audio_duration=4.0,
            source_file="test_audio.wav"
        )
    
    @pytest.fixture
    def mock_translation_service(self):
        """Create mock translation service."""
        mock_service = Mock(spec=TranslationServiceImpl)
        mock_service.is_service_available.return_value = True
        mock_service.get_supported_languages.return_value = ["spanish", "french", "german"]
        return mock_service
    
    @pytest.fixture
    def mock_subtitle_generator(self):
        """Create mock subtitle generator."""
        mock_generator = Mock(spec=SubtitleGenerator)
        return mock_generator
    
    @pytest.fixture
    def bilingual_service(self, mock_translation_service, mock_subtitle_generator):
        """Create bilingual subtitle service with mocks."""
        return BilingualSubtitleService(mock_translation_service, mock_subtitle_generator)
    
    @pytest.fixture
    def temp_directory(self):
        """Create temporary directory for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir
    
    def test_initialization_default(self):
        """Test service initialization with default dependencies."""
        service = BilingualSubtitleService()
        
        assert service.translation_service is not None
        assert service.subtitle_generator is not None
        assert isinstance(service.translation_service, TranslationServiceImpl)
        assert isinstance(service.subtitle_generator, SubtitleGenerator)
    
    def test_initialization_with_dependencies(self, mock_translation_service, mock_subtitle_generator):
        """Test service initialization with provided dependencies."""
        service = BilingualSubtitleService(mock_translation_service, mock_subtitle_generator)
        
        assert service.translation_service == mock_translation_service
        assert service.subtitle_generator == mock_subtitle_generator
    
    def test_generate_bilingual_subtitles_success(self, bilingual_service, sample_alignment_data, 
                                                bilingual_alignment_data, temp_directory):
        """Test successful bilingual subtitle generation."""
        # Setup mocks
        bilingual_service.translation_service.generate_bilingual_subtitles.return_value = bilingual_alignment_data
        
        mock_subtitle_file = SubtitleFile(
            path=os.path.join(temp_directory, "test_bilingual_spanish.srt"),
            format=ExportFormat.SRT,
            content="Mock SRT content",
            word_count=5,
            duration=4.0
        )
        bilingual_service.subtitle_generator.generate_bilingual_subtitle_file.return_value = mock_subtitle_file
        
        # Test generation
        result = bilingual_service.generate_bilingual_subtitles(
            alignment_data=sample_alignment_data,
            target_language="spanish",
            translation_service=TranslationService.DEEPL,
            export_formats=[ExportFormat.SRT],
            output_directory=temp_directory,
            base_filename="test_audio"
        )
        
        # Verify results
        assert result['success'] is True
        assert result['translation_success'] is True
        assert result['fallback_used'] is False
        assert len(result['generated_files']) == 1
        assert result['generated_files'][0]['format'] == 'srt'
        assert len(result['errors']) == 0
        
        # Verify service calls
        bilingual_service.translation_service.is_service_available.assert_called_once_with(TranslationService.DEEPL)
        bilingual_service.translation_service.generate_bilingual_subtitles.assert_called_once()
        bilingual_service.subtitle_generator.generate_bilingual_subtitle_file.assert_called_once()
    
    def test_generate_bilingual_subtitles_translation_unavailable_with_fallback(
            self, bilingual_service, sample_alignment_data, temp_directory):
        """Test bilingual subtitle generation when translation service is unavailable but fallback is enabled."""
        # Setup mocks - translation service unavailable
        bilingual_service.translation_service.is_service_available.return_value = False
        
        mock_subtitle_file = SubtitleFile(
            path=os.path.join(temp_directory, "test_bilingual_spanish.srt"),
            format=ExportFormat.SRT,
            content="Mock SRT content",
            word_count=5,
            duration=4.0
        )
        bilingual_service.subtitle_generator.generate_bilingual_subtitle_file.return_value = mock_subtitle_file
        
        # Test generation with fallback
        result = bilingual_service.generate_bilingual_subtitles(
            alignment_data=sample_alignment_data,
            target_language="spanish",
            translation_service=TranslationService.DEEPL,
            export_formats=[ExportFormat.SRT],
            output_directory=temp_directory,
            base_filename="test_audio",
            options={'include_fallback': True}
        )
        
        # Verify results
        assert result['success'] is True
        assert result['translation_success'] is False
        assert result['fallback_used'] is True
        assert len(result['generated_files']) == 1
        
        # Verify translation service was not called for generation
        bilingual_service.translation_service.generate_bilingual_subtitles.assert_not_called()
    
    def test_generate_bilingual_subtitles_translation_unavailable_no_fallback(
            self, bilingual_service, sample_alignment_data, temp_directory):
        """Test bilingual subtitle generation when translation service is unavailable and fallback is disabled."""
        # Setup mocks - translation service unavailable
        bilingual_service.translation_service.is_service_available.return_value = False
        
        # Test generation without fallback
        result = bilingual_service.generate_bilingual_subtitles(
            alignment_data=sample_alignment_data,
            target_language="spanish",
            translation_service=TranslationService.DEEPL,
            export_formats=[ExportFormat.SRT],
            output_directory=temp_directory,
            base_filename="test_audio",
            options={'include_fallback': False}
        )
        
        # Verify results
        assert result['success'] is False
        assert result['translation_success'] is False
        assert result['fallback_used'] is False
        assert len(result['generated_files']) == 0
        assert len(result['errors']) > 0
    
    def test_generate_bilingual_subtitles_multiple_formats(self, bilingual_service, sample_alignment_data,
                                                         bilingual_alignment_data, temp_directory):
        """Test bilingual subtitle generation with multiple export formats."""
        # Setup mocks
        bilingual_service.translation_service.generate_bilingual_subtitles.return_value = bilingual_alignment_data
        
        # Mock different subtitle files for different formats
        def mock_generate_file(*args, **kwargs):
            format_type = kwargs.get('format_type')
            return SubtitleFile(
                path=os.path.join(temp_directory, f"test_bilingual_spanish.{format_type.value}"),
                format=format_type,
                content=f"Mock {format_type.value.upper()} content",
                word_count=5,
                duration=4.0
            )
        
        bilingual_service.subtitle_generator.generate_bilingual_subtitle_file.side_effect = mock_generate_file
        
        # Test generation with multiple formats
        result = bilingual_service.generate_bilingual_subtitles(
            alignment_data=sample_alignment_data,
            target_language="spanish",
            translation_service=TranslationService.DEEPL,
            export_formats=[ExportFormat.SRT, ExportFormat.VTT, ExportFormat.JSON],
            output_directory=temp_directory,
            base_filename="test_audio"
        )
        
        # Verify results
        assert result['success'] is True
        assert len(result['generated_files']) == 3
        
        formats = [f['format'] for f in result['generated_files']]
        assert 'srt' in formats
        assert 'vtt' in formats
        assert 'json' in formats
    
    def test_generate_bilingual_subtitles_partial_failure(self, bilingual_service, sample_alignment_data,
                                                        bilingual_alignment_data, temp_directory):
        """Test bilingual subtitle generation with partial format failures."""
        # Setup mocks
        bilingual_service.translation_service.generate_bilingual_subtitles.return_value = bilingual_alignment_data
        
        # Mock success for SRT, failure for VTT
        def mock_generate_file(*args, **kwargs):
            format_type = kwargs.get('format_type')
            if format_type == ExportFormat.SRT:
                return SubtitleFile(
                    path=os.path.join(temp_directory, "test_bilingual_spanish.srt"),
                    format=format_type,
                    content="Mock SRT content",
                    word_count=5,
                    duration=4.0
                )
            else:
                raise Exception("Mock VTT generation failure")
        
        bilingual_service.subtitle_generator.generate_bilingual_subtitle_file.side_effect = mock_generate_file
        
        # Test generation
        result = bilingual_service.generate_bilingual_subtitles(
            alignment_data=sample_alignment_data,
            target_language="spanish",
            translation_service=TranslationService.DEEPL,
            export_formats=[ExportFormat.SRT, ExportFormat.VTT],
            output_directory=temp_directory,
            base_filename="test_audio"
        )
        
        # Verify results
        assert result['success'] is True  # At least one format succeeded
        assert len(result['generated_files']) == 1
        assert result['generated_files'][0]['format'] == 'srt'
        assert len(result['errors']) == 1
        assert 'VTT' in result['errors'][0]
    
    def test_has_translations_with_bilingual_text(self, bilingual_service, bilingual_alignment_data):
        """Test detection of translations in bilingual alignment data."""
        result = bilingual_service._has_translations(bilingual_alignment_data)
        assert result is True
    
    def test_has_translations_without_bilingual_text(self, bilingual_service, sample_alignment_data):
        """Test detection of translations in monolingual alignment data."""
        result = bilingual_service._has_translations(sample_alignment_data)
        assert result is False
    
    def test_build_output_path(self, bilingual_service, temp_directory):
        """Test output path building for bilingual files."""
        result = bilingual_service._build_output_path(
            temp_directory, "test_audio.wav", ExportFormat.SRT, "spanish")
        
        expected_path = os.path.join(temp_directory, "test_audio_bilingual_spanish.srt")
        assert result == expected_path
    
    def test_set_translation_api_key(self, bilingual_service):
        """Test setting translation API key."""
        bilingual_service.set_translation_api_key(TranslationService.DEEPL, "test_key")
        
        bilingual_service.translation_service.set_api_key.assert_called_once_with(
            TranslationService.DEEPL, "test_key")
    
    def test_check_translation_service_availability(self, bilingual_service):
        """Test checking translation service availability."""
        bilingual_service.translation_service.is_service_available.return_value = True
        
        result = bilingual_service.check_translation_service_availability(TranslationService.DEEPL)
        
        assert result is True
        bilingual_service.translation_service.is_service_available.assert_called_once_with(TranslationService.DEEPL)
    
    def test_get_supported_languages(self, bilingual_service):
        """Test getting supported languages."""
        expected_languages = ["spanish", "french", "german"]
        bilingual_service.translation_service.get_supported_languages.return_value = expected_languages
        
        result = bilingual_service.get_supported_languages(TranslationService.DEEPL)
        
        assert result == expected_languages
        bilingual_service.translation_service.get_supported_languages.assert_called_once_with(TranslationService.DEEPL)
    
    def test_validate_bilingual_options_valid(self, bilingual_service):
        """Test validation of valid bilingual options."""
        options = {
            'word_level': True,
            'words_per_subtitle': 3,
            'style_options': {
                'font_size': 16
            }
        }
        
        errors = bilingual_service.validate_bilingual_options(options)
        assert len(errors) == 0
    
    def test_validate_bilingual_options_invalid(self, bilingual_service):
        """Test validation of invalid bilingual options."""
        options = {
            'word_level': True,
            'words_per_subtitle': -1,  # Invalid
            'style_options': {
                'font_size': 100  # Invalid (too large)
            }
        }
        
        errors = bilingual_service.validate_bilingual_options(options)
        assert len(errors) == 2
        assert any("words_per_subtitle" in error for error in errors)
        assert any("font_size" in error for error in errors)
    
    def test_generate_preview(self, bilingual_service, sample_alignment_data, bilingual_alignment_data):
        """Test generating preview of bilingual subtitles."""
        # Setup mocks
        bilingual_service.translation_service.is_service_available.return_value = True
        bilingual_service.translation_service.generate_bilingual_subtitles.return_value = bilingual_alignment_data
        bilingual_service.subtitle_generator.generate_bilingual_srt.return_value = "Mock SRT preview"
        
        # Test preview generation
        result = bilingual_service.generate_preview(
            sample_alignment_data, "spanish", TranslationService.DEEPL, ExportFormat.SRT, max_segments=2)
        
        assert result == "Mock SRT preview"
        bilingual_service.subtitle_generator.generate_bilingual_srt.assert_called_once()
    
    def test_generate_preview_invalid_format(self, bilingual_service, sample_alignment_data):
        """Test preview generation with invalid format."""
        with pytest.raises(ValueError, match="Unsupported preview format"):
            bilingual_service.generate_preview(
                sample_alignment_data, "spanish", TranslationService.DEEPL, "invalid_format")
    
    def test_invalid_parameters(self, bilingual_service, temp_directory):
        """Test bilingual subtitle generation with invalid parameters."""
        # Test with None alignment data
        with pytest.raises(ValueError, match="Alignment data cannot be None"):
            bilingual_service.generate_bilingual_subtitles(
                None, "spanish", TranslationService.DEEPL, [ExportFormat.SRT], temp_directory, "test")
        
        # Test with empty target language
        with pytest.raises(ValueError, match="Target language must be specified"):
            bilingual_service.generate_bilingual_subtitles(
                Mock(), "", TranslationService.DEEPL, [ExportFormat.SRT], temp_directory, "test")
        
        # Test with empty export formats
        with pytest.raises(ValueError, match="At least one export format must be specified"):
            bilingual_service.generate_bilingual_subtitles(
                Mock(), "spanish", TranslationService.DEEPL, [], temp_directory, "test")


if __name__ == "__main__":
    pytest.main([__file__])