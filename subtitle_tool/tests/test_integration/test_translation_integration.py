"""
Integration tests for translation service with subtitle generation.
"""

import pytest
from unittest.mock import Mock, patch

from src.services.translation_service import TranslationServiceImpl
from src.services.subtitle_generator import SubtitleGenerator
from src.models.data_models import (
    AlignmentData, Segment, WordSegment, TranslationService, ProcessingOptions
)


class TestTranslationIntegration:
    """Test translation service integration with subtitle generation."""
    
    @pytest.fixture
    def translation_service(self):
        """Create translation service instance."""
        return TranslationServiceImpl()
    
    @pytest.fixture
    def subtitle_generator(self):
        """Create subtitle generator instance."""
        return SubtitleGenerator()
    
    @pytest.fixture
    def sample_alignment_data(self):
        """Create sample alignment data for testing."""
        segments = [
            Segment(
                start_time=0.0,
                end_time=3.0,
                text="Hello, how are you today?",
                confidence=0.95,
                segment_id=0
            ),
            Segment(
                start_time=3.0,
                end_time=6.0,
                text="I'm doing great, thank you!",
                confidence=0.90,
                segment_id=1
            )
        ]
        
        word_segments = [
            WordSegment("Hello,", 0.0, 0.5, 0.95, 0),
            WordSegment("how", 0.5, 0.8, 0.95, 0),
            WordSegment("are", 0.8, 1.1, 0.95, 0),
            WordSegment("you", 1.1, 1.4, 0.95, 0),
            WordSegment("today?", 1.4, 3.0, 0.95, 0),
            WordSegment("I'm", 3.0, 3.3, 0.90, 1),
            WordSegment("doing", 3.3, 3.7, 0.90, 1),
            WordSegment("great,", 3.7, 4.2, 0.90, 1),
            WordSegment("thank", 4.2, 4.6, 0.90, 1),
            WordSegment("you!", 4.6, 6.0, 0.90, 1)
        ]
        
        return AlignmentData(
            segments=segments,
            word_segments=word_segments,
            confidence_scores=[0.95, 0.90],
            audio_duration=6.0,
            source_file="test_conversation.wav"
        )
    
    @patch('src.services.translation_service.requests.post')
    def test_bilingual_srt_generation(self, mock_post, translation_service, subtitle_generator, sample_alignment_data):
        """Test generating bilingual SRT subtitles."""
        # Setup translation service
        translation_service.set_api_key(TranslationService.DEEPL, "test-key")
        
        # Mock API responses
        mock_response_availability = Mock()
        mock_response_availability.status_code = 200
        
        mock_response_1 = Mock()
        mock_response_1.status_code = 200
        mock_response_1.json.return_value = {
            "translations": [{"text": "Hola, ¿cómo estás hoy?"}]
        }
        
        mock_response_2 = Mock()
        mock_response_2.status_code = 200
        mock_response_2.json.return_value = {
            "translations": [{"text": "¡Estoy muy bien, gracias!"}]
        }
        
        mock_post.side_effect = [
            mock_response_availability,
            mock_response_1,
            mock_response_2
        ]
        
        # Generate bilingual alignment data
        bilingual_data = translation_service.generate_bilingual_subtitles(
            sample_alignment_data, "spanish", TranslationService.DEEPL
        )
        
        # Generate SRT from bilingual data
        srt_content = subtitle_generator.generate_srt(bilingual_data, word_level=False)
        
        # Verify bilingual content in SRT
        assert "Hello, how are you today?" in srt_content
        assert "Hola, ¿cómo estás hoy?" in srt_content
        assert "I'm doing great, thank you!" in srt_content
        assert "¡Estoy muy bien, gracias!" in srt_content
        
        # Verify SRT format
        assert "00:00:00,000 --> 00:00:03,000" in srt_content
        assert "00:00:03,000 --> 00:00:06,000" in srt_content
    
    @patch('src.services.translation_service.requests.post')
    def test_bilingual_vtt_generation(self, mock_post, translation_service, subtitle_generator, sample_alignment_data):
        """Test generating bilingual VTT subtitles."""
        # Setup translation service
        translation_service.set_api_key(TranslationService.GOOGLE, "test-key")
        
        # Mock API responses
        mock_response_availability = Mock()
        mock_response_availability.status_code = 200
        
        mock_response_1 = Mock()
        mock_response_1.status_code = 200
        mock_response_1.json.return_value = {
            "data": {"translations": [{"translatedText": "Bonjour, comment allez-vous aujourd'hui?"}]}
        }
        
        mock_response_2 = Mock()
        mock_response_2.status_code = 200
        mock_response_2.json.return_value = {
            "data": {"translations": [{"translatedText": "Je vais très bien, merci!"}]}
        }
        
        mock_post.side_effect = [
            mock_response_availability,
            mock_response_1,
            mock_response_2
        ]
        
        # Generate bilingual alignment data
        bilingual_data = translation_service.generate_bilingual_subtitles(
            sample_alignment_data, "french", TranslationService.GOOGLE
        )
        
        # Generate VTT from bilingual data
        vtt_content = subtitle_generator.generate_vtt(bilingual_data)
        
        # Verify bilingual content in VTT
        assert "Hello, how are you today?" in vtt_content
        assert "Bonjour, comment allez-vous aujourd'hui?" in vtt_content
        assert "I'm doing great, thank you!" in vtt_content
        assert "Je vais très bien, merci!" in vtt_content
        
        # Verify VTT format
        assert "WEBVTT" in vtt_content
        assert "00:00:00.000 --> 00:00:03.000" in vtt_content
        assert "00:00:03.000 --> 00:00:06.000" in vtt_content
    
    def test_translation_fallback_behavior(self, translation_service, subtitle_generator, sample_alignment_data):
        """Test fallback behavior when translation service is unavailable."""
        # Don't set API key, so service will be unavailable
        
        # Generate bilingual alignment data (should fallback to original)
        bilingual_data = translation_service.generate_bilingual_subtitles(
            sample_alignment_data, "spanish", TranslationService.DEEPL
        )
        
        # Should return original data unchanged
        assert bilingual_data == sample_alignment_data
        
        # Generate SRT from original data
        srt_content = subtitle_generator.generate_srt(bilingual_data, word_level=False)
        
        # Should contain only original text
        assert "Hello, how are you today?" in srt_content
        assert "I'm doing great, thank you!" in srt_content
        
        # Should not contain any Spanish text
        assert "Hola" not in srt_content
        assert "gracias" not in srt_content
    
    @patch('src.services.translation_service.requests.post')
    def test_processing_options_with_translation(self, mock_post, translation_service, sample_alignment_data):
        """Test processing options with translation enabled."""
        # Create processing options with translation
        options = ProcessingOptions(
            translation_enabled=True,
            target_language="spanish",
            translation_service=TranslationService.DEEPL
        )
        
        # Validate options
        validation_errors = options.validate()
        assert len(validation_errors) == 1  # Only missing output_directory
        
        # Set output directory
        options.output_directory = "/tmp/output"
        validation_errors = options.validate()
        assert len(validation_errors) == 0
        
        # Setup translation service
        translation_service.set_api_key(TranslationService.DEEPL, "test-key")
        
        # Mock API responses
        mock_response_availability = Mock()
        mock_response_availability.status_code = 200
        mock_post.return_value = mock_response_availability
        
        # Verify service is available
        assert translation_service.is_service_available(options.translation_service)
    
    def test_supported_languages_coverage(self, translation_service):
        """Test that both services support common languages."""
        deepl_languages = translation_service.get_supported_languages(TranslationService.DEEPL)
        google_languages = translation_service.get_supported_languages(TranslationService.GOOGLE)
        
        # Common languages that should be supported by both
        common_languages = ["english", "spanish", "french", "german", "italian"]
        
        for lang in common_languages:
            assert lang in deepl_languages, f"{lang} not supported by DeepL"
            assert lang in google_languages, f"{lang} not supported by Google"
    
    @patch('src.services.translation_service.requests.post')
    def test_rate_limiting_integration(self, mock_post, translation_service, sample_alignment_data):
        """Test rate limiting during bilingual subtitle generation."""
        # Setup service with very restrictive rate limits
        from src.services.translation_service import RateLimiter, RateLimitConfig
        
        translation_service.rate_limiters[TranslationService.DEEPL] = RateLimiter(
            RateLimitConfig(requests_per_minute=1, requests_per_hour=5, requests_per_day=10)
        )
        
        translation_service.set_api_key(TranslationService.DEEPL, "test-key")
        
        # Mock responses
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"translations": [{"text": "Translated"}]}
        mock_post.return_value = mock_response
        
        # First translation should work
        result1 = translation_service.translate_text("Hello", "spanish", TranslationService.DEEPL)
        assert result1 == "Translated"
        
        # Second translation should be rate limited
        with patch('time.sleep') as mock_sleep:
            result2 = translation_service.translate_text("World", "spanish", TranslationService.DEEPL)
            assert result2 == "Translated"
            mock_sleep.assert_called_once()  # Should have waited due to rate limit
    
    def test_api_key_management(self, translation_service):
        """Test API key management functionality."""
        # Initially no keys
        assert not translation_service.is_service_available(TranslationService.DEEPL)
        assert not translation_service.is_service_available(TranslationService.GOOGLE)
        
        # Set keys
        translation_service.set_api_key(TranslationService.DEEPL, "deepl-key")
        translation_service.set_api_key(TranslationService.GOOGLE, "google-key")
        
        # Keys should be stored
        assert TranslationService.DEEPL in translation_service.api_keys
        assert TranslationService.GOOGLE in translation_service.api_keys
        
        # Clear one key
        translation_service.clear_api_key(TranslationService.DEEPL)
        assert TranslationService.DEEPL not in translation_service.api_keys
        assert TranslationService.GOOGLE in translation_service.api_keys
        
        # Clear remaining key
        translation_service.clear_api_key(TranslationService.GOOGLE)
        assert TranslationService.GOOGLE not in translation_service.api_keys
        
        # Both services should be unavailable again
        assert not translation_service.is_service_available(TranslationService.DEEPL)
        assert not translation_service.is_service_available(TranslationService.GOOGLE)