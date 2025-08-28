"""
Integration tests for bilingual subtitle functionality.

This module contains end-to-end integration tests for the complete bilingual
subtitle generation workflow, including translation and export functionality.
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch

from src.services.bilingual_subtitle_service import BilingualSubtitleService
from src.services.translation_service import TranslationServiceImpl
from src.services.subtitle_generator import SubtitleGenerator
from src.models.data_models import (
    AlignmentData, Segment, WordSegment, ExportFormat, TranslationService
)


class TestBilingualIntegration:
    """Integration tests for bilingual subtitle functionality."""
    
    @pytest.fixture
    def sample_alignment_data(self):
        """Create comprehensive sample alignment data for testing."""
        segments = [
            Segment(
                start_time=0.0,
                end_time=3.0,
                text="Hello everyone, welcome to our show",
                confidence=0.95,
                segment_id=1
            ),
            Segment(
                start_time=3.0,
                end_time=6.0,
                text="Today we will discuss artificial intelligence",
                confidence=0.88,
                segment_id=2
            ),
            Segment(
                start_time=6.0,
                end_time=9.0,
                text="Thank you for watching and goodbye",
                confidence=0.92,
                segment_id=3
            )
        ]
        
        word_segments = [
            # Segment 1 words
            WordSegment(word="Hello", start_time=0.0, end_time=0.5, confidence=0.95, segment_id=1),
            WordSegment(word="everyone,", start_time=0.5, end_time=1.2, confidence=0.94, segment_id=1),
            WordSegment(word="welcome", start_time=1.2, end_time=1.8, confidence=0.96, segment_id=1),
            WordSegment(word="to", start_time=1.8, end_time=2.0, confidence=0.93, segment_id=1),
            WordSegment(word="our", start_time=2.0, end_time=2.3, confidence=0.95, segment_id=1),
            WordSegment(word="show", start_time=2.3, end_time=3.0, confidence=0.97, segment_id=1),
            
            # Segment 2 words
            WordSegment(word="Today", start_time=3.0, end_time=3.4, confidence=0.89, segment_id=2),
            WordSegment(word="we", start_time=3.4, end_time=3.6, confidence=0.87, segment_id=2),
            WordSegment(word="will", start_time=3.6, end_time=3.9, confidence=0.88, segment_id=2),
            WordSegment(word="discuss", start_time=3.9, end_time=4.5, confidence=0.86, segment_id=2),
            WordSegment(word="artificial", start_time=4.5, end_time=5.2, confidence=0.90, segment_id=2),
            WordSegment(word="intelligence", start_time=5.2, end_time=6.0, confidence=0.85, segment_id=2),
            
            # Segment 3 words
            WordSegment(word="Thank", start_time=6.0, end_time=6.3, confidence=0.93, segment_id=3),
            WordSegment(word="you", start_time=6.3, end_time=6.6, confidence=0.91, segment_id=3),
            WordSegment(word="for", start_time=6.6, end_time=6.8, confidence=0.92, segment_id=3),
            WordSegment(word="watching", start_time=6.8, end_time=7.5, confidence=0.94, segment_id=3),
            WordSegment(word="and", start_time=7.5, end_time=7.7, confidence=0.90, segment_id=3),
            WordSegment(word="goodbye", start_time=7.7, end_time=9.0, confidence=0.95, segment_id=3)
        ]
        
        return AlignmentData(
            segments=segments,
            word_segments=word_segments,
            confidence_scores=[0.95, 0.88, 0.92],
            audio_duration=9.0,
            source_file="test_presentation.wav"
        )
    
    @pytest.fixture
    def temp_directory(self):
        """Create temporary directory for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir
    
    @pytest.fixture
    def mock_translation_responses(self):
        """Mock translation responses for different services."""
        return {
            "spanish": {
                "Hello everyone, welcome to our show": "Hola a todos, bienvenidos a nuestro programa",
                "Today we will discuss artificial intelligence": "Hoy discutiremos la inteligencia artificial",
                "Thank you for watching and goodbye": "Gracias por vernos y adiós"
            },
            "french": {
                "Hello everyone, welcome to our show": "Bonjour tout le monde, bienvenue à notre émission",
                "Today we will discuss artificial intelligence": "Aujourd'hui nous discuterons de l'intelligence artificielle",
                "Thank you for watching and goodbye": "Merci de nous avoir regardés et au revoir"
            }
        }
    
    def test_end_to_end_bilingual_srt_generation(self, sample_alignment_data, temp_directory, mock_translation_responses):
        """Test complete end-to-end bilingual SRT generation."""
        # Create service with real implementations
        translation_service = TranslationServiceImpl()
        subtitle_generator = SubtitleGenerator()
        bilingual_service = BilingualSubtitleService(translation_service, subtitle_generator)
        
        # Mock the translation API calls
        def mock_perform_translation(text, target_language, service):
            from src.services.translation_service import TranslationResult
            if target_language == "spanish" and text in mock_translation_responses["spanish"]:
                return TranslationResult(
                    success=True,
                    translated_text=mock_translation_responses["spanish"][text],
                    original_text=text,
                    service_used=service
                )
            return TranslationResult(
                success=True,
                translated_text=f"[TRANSLATED: {text}]",
                original_text=text,
                service_used=service
            )
        
        with patch.object(translation_service, 'is_service_available', return_value=True):
            with patch.object(translation_service, '_perform_translation', side_effect=mock_perform_translation):
                # Generate bilingual subtitles
                result = bilingual_service.generate_bilingual_subtitles(
                    alignment_data=sample_alignment_data,
                    target_language="spanish",
                    translation_service=TranslationService.DEEPL,
                    export_formats=[ExportFormat.SRT],
                    output_directory=temp_directory,
                    base_filename="test_presentation"
                )
        
        # Verify results
        assert result['success'] is True
        assert result['translation_success'] is True
        assert len(result['generated_files']) == 1
        
        # Verify file was created
        srt_file_path = result['generated_files'][0]['path']
        assert os.path.exists(srt_file_path)
        
        # Verify file content
        with open(srt_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for bilingual content
        assert "Hello everyone, welcome to our show" in content
        assert "Hola a todos, bienvenidos a nuestro programa" in content
        assert "artificial intelligence" in content
        assert "inteligencia artificial" in content
        
        # Check SRT format structure
        assert "1\n00:00:00,000 --> 00:00:03,000" in content
        assert "2\n00:00:03,000 --> 00:00:06,000" in content
        assert "3\n00:00:06,000 --> 00:00:09,000" in content
    
    def test_end_to_end_bilingual_multiple_formats(self, sample_alignment_data, temp_directory, mock_translation_responses):
        """Test complete bilingual generation with multiple export formats."""
        # Create service with real implementations
        translation_service = TranslationServiceImpl()
        subtitle_generator = SubtitleGenerator()
        bilingual_service = BilingualSubtitleService(translation_service, subtitle_generator)
        
        # Mock the translation API calls
        def mock_perform_translation(text, target_language, service):
            from src.services.translation_service import TranslationResult
            if target_language == "french" and text in mock_translation_responses["french"]:
                return TranslationResult(
                    success=True,
                    translated_text=mock_translation_responses["french"][text],
                    original_text=text,
                    service_used=service
                )
            return TranslationResult(
                success=True,
                translated_text=f"[TRANSLATED: {text}]",
                original_text=text,
                service_used=service
            )
        
        with patch.object(translation_service, 'is_service_available', return_value=True):
            with patch.object(translation_service, '_perform_translation', side_effect=mock_perform_translation):
                # Generate bilingual subtitles in multiple formats
                result = bilingual_service.generate_bilingual_subtitles(
                    alignment_data=sample_alignment_data,
                    target_language="french",
                    translation_service=TranslationService.GOOGLE,
                    export_formats=[ExportFormat.SRT, ExportFormat.VTT, ExportFormat.JSON],
                    output_directory=temp_directory,
                    base_filename="test_presentation"
                )
        
        # Verify results
        assert result['success'] is True
        assert len(result['generated_files']) == 3
        
        # Check all formats were generated
        formats = [f['format'] for f in result['generated_files']]
        assert 'srt' in formats
        assert 'vtt' in formats
        assert 'json' in formats
        
        # Verify all files exist and contain bilingual content
        for file_info in result['generated_files']:
            file_path = file_info['path']
            assert os.path.exists(file_path)
            
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check for bilingual content in all formats
            assert "Hello everyone" in content
            assert "Bonjour tout le monde" in content or "bienvenue" in content
    
    def test_bilingual_ass_karaoke_generation(self, sample_alignment_data, temp_directory, mock_translation_responses):
        """Test bilingual ASS karaoke subtitle generation."""
        # Create service with real implementations
        translation_service = TranslationServiceImpl()
        subtitle_generator = SubtitleGenerator()
        bilingual_service = BilingualSubtitleService(translation_service, subtitle_generator)
        
        # Mock the translation API calls
        def mock_perform_translation(text, target_language, service):
            from src.services.translation_service import TranslationResult
            if target_language == "spanish" and text in mock_translation_responses["spanish"]:
                return TranslationResult(
                    success=True,
                    translated_text=mock_translation_responses["spanish"][text],
                    original_text=text,
                    service_used=service
                )
            return TranslationResult(
                success=True,
                translated_text=f"[TRANSLATED: {text}]",
                original_text=text,
                service_used=service
            )
        
        with patch.object(translation_service, 'is_service_available', return_value=True):
            with patch.object(translation_service, '_perform_translation', side_effect=mock_perform_translation):
                # Generate bilingual ASS subtitles
                result = bilingual_service.generate_bilingual_subtitles(
                    alignment_data=sample_alignment_data,
                    target_language="spanish",
                    translation_service=TranslationService.DEEPL,
                    export_formats=[ExportFormat.ASS],
                    output_directory=temp_directory,
                    base_filename="test_presentation",
                    options={
                        'style_options': {
                            'font_size': 18,
                            'font_name': 'Arial'
                        }
                    }
                )
        
        # Verify results
        assert result['success'] is True
        assert len(result['generated_files']) == 1
        
        # Verify ASS file content
        ass_file_path = result['generated_files'][0]['path']
        with open(ass_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check ASS format structure
        assert "[Script Info]" in content
        assert "[V4+ Styles]" in content
        assert "[Events]" in content
        
        # Check for bilingual styles
        assert "Original" in content
        assert "Translation" in content
        
        # Check for dialogue lines
        assert "Dialogue:" in content
    
    def test_bilingual_word_level_generation(self, sample_alignment_data, temp_directory, mock_translation_responses):
        """Test bilingual word-level subtitle generation."""
        # Create service with real implementations
        translation_service = TranslationServiceImpl()
        subtitle_generator = SubtitleGenerator()
        bilingual_service = BilingualSubtitleService(translation_service, subtitle_generator)
        
        # Mock the translation API calls
        def mock_perform_translation(text, target_language, service):
            from src.services.translation_service import TranslationResult
            if target_language == "spanish" and text in mock_translation_responses["spanish"]:
                return TranslationResult(
                    success=True,
                    translated_text=mock_translation_responses["spanish"][text],
                    original_text=text,
                    service_used=service
                )
            return TranslationResult(
                success=True,
                translated_text=f"[TRANSLATED: {text}]",
                original_text=text,
                service_used=service
            )
        
        with patch.object(translation_service, 'is_service_available', return_value=True):
            with patch.object(translation_service, '_perform_translation', side_effect=mock_perform_translation):
                # Generate bilingual word-level subtitles
                result = bilingual_service.generate_bilingual_subtitles(
                    alignment_data=sample_alignment_data,
                    target_language="spanish",
                    translation_service=TranslationService.DEEPL,
                    export_formats=[ExportFormat.SRT, ExportFormat.VTT],
                    output_directory=temp_directory,
                    base_filename="test_presentation",
                    options={
                        'word_level': True,
                        'words_per_subtitle': 2
                    }
                )
        
        # Verify results
        assert result['success'] is True
        assert len(result['generated_files']) == 2
        
        # Check SRT word-level content
        srt_file = next(f for f in result['generated_files'] if f['format'] == 'srt')
        with open(srt_file['path'], 'r', encoding='utf-8') as f:
            srt_content = f.read()
        
        # Should have more subtitle entries due to word grouping
        subtitle_count = srt_content.count('\n\n')
        assert subtitle_count > 3  # More than the original 3 segments
    
    def test_fallback_handling_integration(self, sample_alignment_data, temp_directory):
        """Test fallback handling when translation service fails."""
        # Create service with real implementations
        translation_service = TranslationServiceImpl()
        subtitle_generator = SubtitleGenerator()
        bilingual_service = BilingualSubtitleService(translation_service, subtitle_generator)
        
        # Mock translation service as unavailable
        with patch.object(translation_service, 'is_service_available', return_value=False):
            # Generate subtitles with fallback enabled
            result = bilingual_service.generate_bilingual_subtitles(
                alignment_data=sample_alignment_data,
                target_language="spanish",
                translation_service=TranslationService.DEEPL,
                export_formats=[ExportFormat.SRT],
                output_directory=temp_directory,
                base_filename="test_presentation",
                options={'include_fallback': True}
            )
        
        # Verify fallback behavior
        assert result['success'] is True
        assert result['translation_success'] is False
        assert result['fallback_used'] is True
        assert len(result['generated_files']) == 1
        
        # Verify file contains original text only
        srt_file_path = result['generated_files'][0]['path']
        with open(srt_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        assert "Hello everyone, welcome to our show" in content
        # Should not contain Spanish translations
        assert "Hola" not in content
    
    def test_preview_generation_integration(self, sample_alignment_data, mock_translation_responses):
        """Test preview generation integration."""
        # Create service with real implementations
        translation_service = TranslationServiceImpl()
        subtitle_generator = SubtitleGenerator()
        bilingual_service = BilingualSubtitleService(translation_service, subtitle_generator)
        
        # Mock the translation API calls
        def mock_perform_translation(text, target_language, service):
            from src.services.translation_service import TranslationResult
            if target_language == "spanish" and text in mock_translation_responses["spanish"]:
                return TranslationResult(
                    success=True,
                    translated_text=mock_translation_responses["spanish"][text],
                    original_text=text,
                    service_used=service
                )
            return TranslationResult(
                success=True,
                translated_text=f"[TRANSLATED: {text}]",
                original_text=text,
                service_used=service
            )
        
        with patch.object(translation_service, 'is_service_available', return_value=True):
            with patch.object(translation_service, '_perform_translation', side_effect=mock_perform_translation):
                # Generate preview
                preview_content = bilingual_service.generate_preview(
                    alignment_data=sample_alignment_data,
                    target_language="spanish",
                    translation_service=TranslationService.DEEPL,
                    format_type=ExportFormat.SRT,
                    max_segments=2
                )
        
        # Verify preview content
        assert preview_content is not None
        assert len(preview_content) > 0
        
        # Should contain first 2 segments only
        assert "Hello everyone" in preview_content
        assert "artificial intelligence" in preview_content
        assert "goodbye" not in preview_content  # Third segment should not be included
        
        # Should contain translations
        assert "Hola" in preview_content
        assert "inteligencia artificial" in preview_content
    
    def test_error_handling_integration(self, sample_alignment_data, temp_directory):
        """Test error handling in integration scenarios."""
        # Create service with real implementations
        translation_service = TranslationServiceImpl()
        subtitle_generator = SubtitleGenerator()
        bilingual_service = BilingualSubtitleService(translation_service, subtitle_generator)
        
        # Mock translation service to raise exception
        with patch.object(translation_service, 'is_service_available', return_value=True):
            with patch.object(translation_service, 'generate_bilingual_subtitles', 
                            side_effect=Exception("Translation API error")):
                # Generate subtitles with fallback disabled
                result = bilingual_service.generate_bilingual_subtitles(
                    alignment_data=sample_alignment_data,
                    target_language="spanish",
                    translation_service=TranslationService.DEEPL,
                    export_formats=[ExportFormat.SRT],
                    output_directory=temp_directory,
                    base_filename="test_presentation",
                    options={'include_fallback': False}
                )
        
        # Verify error handling
        assert result['success'] is False
        assert len(result['errors']) > 0
        assert len(result['generated_files']) == 0
        assert "Failed to create bilingual alignment data" in str(result['errors'])
    
    def test_validation_integration(self, sample_alignment_data, temp_directory):
        """Test validation integration with bilingual service."""
        # Create service with real implementations
        bilingual_service = BilingualSubtitleService()
        
        # Test invalid alignment data
        with pytest.raises(ValueError, match="Alignment data cannot be None"):
            bilingual_service.generate_bilingual_subtitles(
                alignment_data=None,
                target_language="spanish",
                translation_service=TranslationService.DEEPL,
                export_formats=[ExportFormat.SRT],
                output_directory=temp_directory,
                base_filename="test"
            )
        
        # Test invalid target language
        with pytest.raises(ValueError, match="Target language must be specified"):
            bilingual_service.generate_bilingual_subtitles(
                alignment_data=sample_alignment_data,
                target_language="",
                translation_service=TranslationService.DEEPL,
                export_formats=[ExportFormat.SRT],
                output_directory=temp_directory,
                base_filename="test"
            )
        
        # Test invalid export formats
        with pytest.raises(ValueError, match="At least one export format must be specified"):
            bilingual_service.generate_bilingual_subtitles(
                alignment_data=sample_alignment_data,
                target_language="spanish",
                translation_service=TranslationService.DEEPL,
                export_formats=[],
                output_directory=temp_directory,
                base_filename="test"
            )


if __name__ == "__main__":
    pytest.main([__file__])