"""
Tests for translation service implementation.
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
import requests

from src.services.translation_service import (
    TranslationServiceImpl, RateLimiter, RateLimitConfig, TranslationResult
)
from src.models.data_models import (
    TranslationService, AlignmentData, Segment, WordSegment
)


class TestRateLimiter:
    """Test rate limiting functionality."""
    
    def test_rate_limiter_initialization(self):
        """Test rate limiter initialization."""
        config = RateLimitConfig(
            requests_per_minute=10,
            requests_per_hour=100,
            requests_per_day=1000
        )
        limiter = RateLimiter(config)
        
        assert limiter.config == config
        assert limiter.requests_minute == []
        assert limiter.requests_hour == []
        assert limiter.requests_day == []
    
    def test_can_make_request_within_limits(self):
        """Test that requests are allowed within limits."""
        config = RateLimitConfig(
            requests_per_minute=5,
            requests_per_hour=50,
            requests_per_day=500
        )
        limiter = RateLimiter(config)
        
        # Should allow requests within limits
        for _ in range(4):
            assert limiter.can_make_request()
            limiter.record_request()
        
        # Should still allow one more
        assert limiter.can_make_request()
    
    def test_rate_limit_exceeded(self):
        """Test that requests are blocked when limits exceeded."""
        config = RateLimitConfig(
            requests_per_minute=2,
            requests_per_hour=10,
            requests_per_day=100
        )
        limiter = RateLimiter(config)
        
        # Make requests up to limit
        limiter.record_request()
        limiter.record_request()
        
        # Should be blocked now
        assert not limiter.can_make_request()
    
    def test_time_until_next_request(self):
        """Test calculation of wait time."""
        config = RateLimitConfig(
            requests_per_minute=1,
            requests_per_hour=10,
            requests_per_day=100
        )
        limiter = RateLimiter(config)
        
        # No requests made yet
        assert limiter.time_until_next_request() == 0.0
        
        # Make a request
        limiter.record_request()
        
        # Should need to wait
        wait_time = limiter.time_until_next_request()
        assert wait_time > 0
        assert wait_time <= 60


class TestTranslationService:
    """Test translation service implementation."""
    
    @pytest.fixture
    def translation_service(self):
        """Create translation service instance."""
        return TranslationServiceImpl()
    
    @pytest.fixture
    def sample_alignment_data(self):
        """Create sample alignment data for testing."""
        segments = [
            Segment(
                start_time=0.0,
                end_time=2.0,
                text="Hello world",
                confidence=0.95,
                segment_id=0
            ),
            Segment(
                start_time=2.0,
                end_time=4.0,
                text="How are you?",
                confidence=0.90,
                segment_id=1
            )
        ]
        
        word_segments = [
            WordSegment("Hello", 0.0, 0.5, 0.95, 0),
            WordSegment("world", 0.5, 2.0, 0.95, 0),
            WordSegment("How", 2.0, 2.3, 0.90, 1),
            WordSegment("are", 2.3, 2.6, 0.90, 1),
            WordSegment("you?", 2.6, 4.0, 0.90, 1)
        ]
        
        return AlignmentData(
            segments=segments,
            word_segments=word_segments,
            confidence_scores=[0.95, 0.90],
            audio_duration=4.0,
            source_file="test.wav"
        )
    
    def test_initialization(self, translation_service):
        """Test service initialization."""
        assert translation_service.api_keys == {}
        assert len(translation_service.rate_limiters) == 2
        assert TranslationService.DEEPL in translation_service.rate_limiters
        assert TranslationService.GOOGLE in translation_service.rate_limiters
    
    def test_set_api_key_valid(self, translation_service):
        """Test setting valid API key."""
        api_key = "test-api-key-123"
        translation_service.set_api_key(TranslationService.DEEPL, api_key)
        
        assert translation_service.api_keys[TranslationService.DEEPL] == api_key
    
    def test_set_api_key_empty(self, translation_service):
        """Test setting empty API key raises error."""
        with pytest.raises(ValueError, match="API key cannot be empty"):
            translation_service.set_api_key(TranslationService.DEEPL, "")
        
        with pytest.raises(ValueError, match="API key cannot be empty"):
            translation_service.set_api_key(TranslationService.DEEPL, "   ")
    
    def test_is_service_available_no_key(self, translation_service):
        """Test service availability without API key."""
        assert not translation_service.is_service_available(TranslationService.DEEPL)
        assert not translation_service.is_service_available(TranslationService.GOOGLE)
    
    @patch('src.services.translation_service.requests.post')
    def test_is_service_available_deepl_success(self, mock_post, translation_service):
        """Test DeepL service availability check success."""
        # Setup
        translation_service.set_api_key(TranslationService.DEEPL, "test-key")
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        # Test
        assert translation_service.is_service_available(TranslationService.DEEPL)
        
        # Verify request
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert "api-free.deepl.com" in args[0]
        assert "DeepL-Auth-Key test-key" in kwargs['headers']['Authorization']
    
    @patch('src.services.translation_service.requests.post')
    def test_is_service_available_google_success(self, mock_post, translation_service):
        """Test Google service availability check success."""
        # Setup
        translation_service.set_api_key(TranslationService.GOOGLE, "test-key")
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        # Test
        assert translation_service.is_service_available(TranslationService.GOOGLE)
        
        # Verify request
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert "translation.googleapis.com" in args[0]
        assert kwargs['params']['key'] == "test-key"
    
    @patch('src.services.translation_service.requests.post')
    def test_translate_text_deepl_success(self, mock_post, translation_service):
        """Test successful DeepL translation."""
        # Setup
        translation_service.set_api_key(TranslationService.DEEPL, "test-key")
        
        # Mock availability check
        mock_response_availability = Mock()
        mock_response_availability.status_code = 200
        
        # Mock translation response
        mock_response_translation = Mock()
        mock_response_translation.status_code = 200
        mock_response_translation.json.return_value = {
            "translations": [{"text": "Hola mundo"}]
        }
        
        mock_post.side_effect = [mock_response_availability, mock_response_translation]
        
        # Test
        result = translation_service.translate_text("Hello world", "spanish", TranslationService.DEEPL)
        
        assert result == "Hola mundo"
        assert mock_post.call_count == 2
    
    @patch('src.services.translation_service.requests.post')
    def test_translate_text_google_success(self, mock_post, translation_service):
        """Test successful Google translation."""
        # Setup
        translation_service.set_api_key(TranslationService.GOOGLE, "test-key")
        
        # Mock availability check
        mock_response_availability = Mock()
        mock_response_availability.status_code = 200
        
        # Mock translation response
        mock_response_translation = Mock()
        mock_response_translation.status_code = 200
        mock_response_translation.json.return_value = {
            "data": {"translations": [{"translatedText": "Hola mundo"}]}
        }
        
        mock_post.side_effect = [mock_response_availability, mock_response_translation]
        
        # Test
        result = translation_service.translate_text("Hello world", "spanish", TranslationService.GOOGLE)
        
        assert result == "Hola mundo"
        assert mock_post.call_count == 2
    
    def test_translate_text_empty_input(self, translation_service):
        """Test translation with empty input."""
        result = translation_service.translate_text("", "spanish", TranslationService.DEEPL)
        assert result == ""
        
        result = translation_service.translate_text("   ", "spanish", TranslationService.DEEPL)
        assert result == "   "
    
    def test_translate_text_service_unavailable(self, translation_service):
        """Test translation when service is unavailable."""
        with pytest.raises(ValueError, match="not available"):
            translation_service.translate_text("Hello", "spanish", TranslationService.DEEPL)
    
    @patch('src.services.translation_service.requests.post')
    def test_translate_text_api_error(self, mock_post, translation_service):
        """Test translation API error handling."""
        # Setup
        translation_service.set_api_key(TranslationService.DEEPL, "test-key")
        
        # Mock availability check success
        mock_response_availability = Mock()
        mock_response_availability.status_code = 200
        
        # Mock translation error
        mock_response_translation = Mock()
        mock_response_translation.status_code = 400
        mock_response_translation.text = "Bad Request"
        
        mock_post.side_effect = [mock_response_availability, mock_response_translation]
        
        # Test
        with pytest.raises(Exception):
            translation_service.translate_text("Hello", "spanish", TranslationService.DEEPL)
    
    @patch('src.services.translation_service.requests.post')
    def test_rate_limiting(self, mock_post, translation_service):
        """Test rate limiting functionality."""
        # Setup service with very low rate limit
        translation_service.rate_limiters[TranslationService.DEEPL] = RateLimiter(
            RateLimitConfig(requests_per_minute=1, requests_per_hour=10, requests_per_day=100)
        )
        translation_service.set_api_key(TranslationService.DEEPL, "test-key")
        
        # Mock responses
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"translations": [{"text": "Translated"}]}
        mock_post.return_value = mock_response
        
        # First request should succeed
        result1 = translation_service.translate_text("Hello", "spanish", TranslationService.DEEPL)
        assert result1 == "Translated"
        
        # Second request should be delayed due to rate limiting
        start_time = time.time()
        with patch('time.sleep') as mock_sleep:
            translation_service.translate_text("World", "spanish", TranslationService.DEEPL)
            mock_sleep.assert_called_once()
    
    @patch('src.services.translation_service.requests.post')
    def test_generate_bilingual_subtitles_success(self, mock_post, translation_service, sample_alignment_data):
        """Test successful bilingual subtitle generation."""
        # Setup
        translation_service.set_api_key(TranslationService.DEEPL, "test-key")
        
        # Mock availability check
        mock_response_availability = Mock()
        mock_response_availability.status_code = 200
        
        # Mock translation responses
        mock_response_1 = Mock()
        mock_response_1.status_code = 200
        mock_response_1.json.return_value = {"translations": [{"text": "Hola mundo"}]}
        
        mock_response_2 = Mock()
        mock_response_2.status_code = 200
        mock_response_2.json.return_value = {"translations": [{"text": "¿Cómo estás?"}]}
        
        mock_post.side_effect = [
            mock_response_availability,
            mock_response_1,
            mock_response_2
        ]
        
        # Test
        result = translation_service.generate_bilingual_subtitles(
            sample_alignment_data, "spanish", TranslationService.DEEPL
        )
        
        # Verify bilingual text
        assert "Hello world\nHola mundo" in result.segments[0].text
        assert "How are you?\n¿Cómo estás?" in result.segments[1].text
        
        # Verify other data is preserved
        assert len(result.segments) == 2
        assert len(result.word_segments) == 5
        assert result.audio_duration == 4.0
    
    def test_generate_bilingual_subtitles_service_unavailable(self, translation_service, sample_alignment_data):
        """Test bilingual subtitle generation when service unavailable."""
        result = translation_service.generate_bilingual_subtitles(
            sample_alignment_data, "spanish", TranslationService.DEEPL
        )
        
        # Should return original data unchanged
        assert result == sample_alignment_data
    
    @patch('src.services.translation_service.requests.post')
    def test_generate_bilingual_subtitles_partial_failure(self, mock_post, translation_service, sample_alignment_data):
        """Test bilingual subtitle generation with partial translation failures."""
        # Setup
        translation_service.set_api_key(TranslationService.DEEPL, "test-key")
        
        # Mock availability check
        mock_response_availability = Mock()
        mock_response_availability.status_code = 200
        
        # Mock first translation success, second failure
        mock_response_1 = Mock()
        mock_response_1.status_code = 200
        mock_response_1.json.return_value = {"translations": [{"text": "Hola mundo"}]}
        
        mock_response_2 = Mock()
        mock_response_2.status_code = 400
        mock_response_2.text = "Error"
        
        mock_post.side_effect = [
            mock_response_availability,
            mock_response_1,
            mock_response_2
        ]
        
        # Test
        result = translation_service.generate_bilingual_subtitles(
            sample_alignment_data, "spanish", TranslationService.DEEPL
        )
        
        # First segment should be translated, second should be original
        assert "Hello world\nHola mundo" in result.segments[0].text
        assert result.segments[1].text == "How are you?"  # Original text preserved
    
    def test_get_supported_languages(self, translation_service):
        """Test getting supported languages."""
        deepl_languages = translation_service.get_supported_languages(TranslationService.DEEPL)
        google_languages = translation_service.get_supported_languages(TranslationService.GOOGLE)
        
        assert "english" in deepl_languages
        assert "spanish" in deepl_languages
        assert "french" in deepl_languages
        
        assert "english" in google_languages
        assert "spanish" in google_languages
        assert "french" in google_languages
    
    def test_clear_api_key(self, translation_service):
        """Test clearing API key."""
        # Set key first
        translation_service.set_api_key(TranslationService.DEEPL, "test-key")
        assert TranslationService.DEEPL in translation_service.api_keys
        
        # Clear key
        translation_service.clear_api_key(TranslationService.DEEPL)
        assert TranslationService.DEEPL not in translation_service.api_keys
    
    def test_unsupported_language(self, translation_service):
        """Test handling of unsupported languages."""
        translation_service.set_api_key(TranslationService.DEEPL, "test-key")
        
        with patch.object(translation_service, '_test_service_connection', return_value=True):
            with pytest.raises(ValueError, match="Unsupported target language"):
                translation_service.translate_text("Hello", "klingon", TranslationService.DEEPL)


class TestTranslationResult:
    """Test TranslationResult data class."""
    
    def test_translation_result_creation(self):
        """Test creating translation result."""
        result = TranslationResult(
            success=True,
            translated_text="Hola",
            original_text="Hello",
            service_used=TranslationService.DEEPL
        )
        
        assert result.success
        assert result.translated_text == "Hola"
        assert result.original_text == "Hello"
        assert result.service_used == TranslationService.DEEPL
        assert result.error_message is None
        assert result.confidence == 1.0
    
    def test_translation_result_with_error(self):
        """Test creating translation result with error."""
        result = TranslationResult(
            success=False,
            translated_text="",
            original_text="Hello",
            service_used=TranslationService.GOOGLE,
            error_message="API Error",
            confidence=0.0
        )
        
        assert not result.success
        assert result.error_message == "API Error"
        assert result.confidence == 0.0