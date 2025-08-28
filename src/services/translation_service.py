"""
Translation service implementation for multilingual subtitle generation.

This module provides translation capabilities using DeepL and Google Translate APIs,
with rate limiting, error handling, and API key management.
"""

import time
import logging
import requests
from typing import Dict, Optional, List
from dataclasses import dataclass
from threading import Lock

from .interfaces import ITranslationService
from ..models.data_models import AlignmentData, Segment, WordSegment, TranslationService as TranslationServiceEnum


@dataclass
class TranslationResult:
    """Result of a translation operation."""
    success: bool
    translated_text: str
    original_text: str
    service_used: TranslationServiceEnum
    error_message: Optional[str] = None
    confidence: float = 1.0


@dataclass
class RateLimitConfig:
    """Rate limiting configuration for translation services."""
    requests_per_minute: int
    requests_per_hour: int
    requests_per_day: int


class RateLimiter:
    """Rate limiter for API requests."""
    
    def __init__(self, config: RateLimitConfig):
        self.config = config
        self.requests_minute: List[float] = []
        self.requests_hour: List[float] = []
        self.requests_day: List[float] = []
        self.lock = Lock()
    
    def can_make_request(self) -> bool:
        """Check if a request can be made within rate limits."""
        with self.lock:
            current_time = time.time()
            
            # Clean old requests
            self._clean_old_requests(current_time)
            
            # Check limits
            if len(self.requests_minute) >= self.config.requests_per_minute:
                return False
            if len(self.requests_hour) >= self.config.requests_per_hour:
                return False
            if len(self.requests_day) >= self.config.requests_per_day:
                return False
            
            return True
    
    def record_request(self) -> None:
        """Record a new request."""
        with self.lock:
            current_time = time.time()
            self.requests_minute.append(current_time)
            self.requests_hour.append(current_time)
            self.requests_day.append(current_time)
    
    def _clean_old_requests(self, current_time: float) -> None:
        """Remove old requests from tracking lists."""
        minute_ago = current_time - 60
        hour_ago = current_time - 3600
        day_ago = current_time - 86400
        
        self.requests_minute = [t for t in self.requests_minute if t > minute_ago]
        self.requests_hour = [t for t in self.requests_hour if t > hour_ago]
        self.requests_day = [t for t in self.requests_day if t > day_ago]
    
    def time_until_next_request(self) -> float:
        """Get time in seconds until next request can be made."""
        with self.lock:
            current_time = time.time()
            self._clean_old_requests(current_time)
            
            if len(self.requests_minute) >= self.config.requests_per_minute:
                oldest_minute = min(self.requests_minute)
                return max(0, 60 - (current_time - oldest_minute))
            
            return 0.0


class TranslationService(ITranslationService):
    """Implementation of translation service with DeepL and Google Translate support."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.api_keys: Dict[TranslationServiceEnum, str] = {}
        self.rate_limiters: Dict[TranslationServiceEnum, RateLimiter] = {
            TranslationServiceEnum.DEEPL: RateLimiter(RateLimitConfig(
                requests_per_minute=20,
                requests_per_hour=500,
                requests_per_day=10000
            )),
            TranslationServiceEnum.GOOGLE: RateLimiter(RateLimitConfig(
                requests_per_minute=60,
                requests_per_hour=1000,
                requests_per_day=50000
            ))
        }
        
        # Service endpoints
        self.endpoints = {
            TranslationServiceEnum.DEEPL: "https://api-free.deepl.com/v2/translate",
            TranslationServiceEnum.GOOGLE: "https://translation.googleapis.com/language/translate/v2"
        }
        
        # Supported language codes mapping
        self.language_codes = {
            TranslationServiceEnum.DEEPL: {
                "english": "EN",
                "spanish": "ES",
                "french": "FR",
                "german": "DE",
                "italian": "IT",
                "portuguese": "PT",
                "russian": "RU",
                "japanese": "JA",
                "chinese": "ZH",
                "korean": "KO"
            },
            TranslationServiceEnum.GOOGLE: {
                "english": "en",
                "spanish": "es",
                "french": "fr",
                "german": "de",
                "italian": "it",
                "portuguese": "pt",
                "russian": "ru",
                "japanese": "ja",
                "chinese": "zh",
                "korean": "ko"
            }
        }
    
    def set_api_key(self, service: TranslationServiceEnum, api_key: str) -> None:
        """Set API key for translation service."""
        if not api_key or not api_key.strip():
            raise ValueError(f"API key cannot be empty for {service.value}")
        
        self.api_keys[service] = api_key.strip()
        self.logger.info(f"API key set for {service.value}")
    
    def is_service_available(self, service: TranslationServiceEnum) -> bool:
        """Check if translation service is available."""
        if service not in self.api_keys:
            self.logger.warning(f"No API key configured for {service.value}")
            return False
        
        try:
            # Test with a simple request
            test_result = self._test_service_connection(service)
            return test_result
        except Exception as e:
            self.logger.error(f"Service availability check failed for {service.value}: {e}")
            return False
    
    def translate_text(self, text: str, target_language: str, service: TranslationServiceEnum) -> str:
        """Translate text to target language."""
        if not text or not text.strip():
            return text
        
        if not self.is_service_available(service):
            raise ValueError(f"Translation service {service.value} is not available")
        
        # Check rate limits
        rate_limiter = self.rate_limiters[service]
        if not rate_limiter.can_make_request():
            wait_time = rate_limiter.time_until_next_request()
            if wait_time > 0:
                self.logger.warning(f"Rate limit reached for {service.value}, waiting {wait_time:.1f}s")
                time.sleep(wait_time)
        
        try:
            result = self._perform_translation(text, target_language, service)
            rate_limiter.record_request()
            
            if result.success:
                return result.translated_text
            else:
                # Check if it's an unsupported language error
                if "Unsupported target language" in (result.error_message or ""):
                    raise ValueError(result.error_message)
                else:
                    raise Exception(result.error_message or "Translation failed")
                
        except ValueError:
            # Re-raise ValueError for unsupported languages
            raise
        except Exception as e:
            self.logger.error(f"Translation failed with {service.value}: {e}")
            raise
    
    def generate_bilingual_subtitles(self, alignment_data: AlignmentData, target_language: str, service: TranslationServiceEnum) -> AlignmentData:
        """Generate bilingual subtitle data."""
        if not self.is_service_available(service):
            self.logger.warning(f"Translation service {service.value} not available, returning original data")
            return alignment_data
        
        try:
            # Translate segments
            translated_segments = []
            for segment in alignment_data.segments:
                try:
                    # Use internal translation method to avoid service availability re-check
                    result = self._perform_translation(segment.text, target_language, service)
                    if result.success:
                        # Create bilingual text (original + translation)
                        bilingual_text = f"{segment.text}\n{result.translated_text}"
                        
                        translated_segment = Segment(
                            start_time=segment.start_time,
                            end_time=segment.end_time,
                            text=bilingual_text,
                            confidence=segment.confidence,
                            segment_id=segment.segment_id
                        )
                        translated_segments.append(translated_segment)
                    else:
                        # Keep original segment if translation fails
                        translated_segments.append(segment)
                    
                except Exception as e:
                    self.logger.warning(f"Failed to translate segment {segment.segment_id}: {e}")
                    # Keep original segment if translation fails
                    translated_segments.append(segment)
            
            # Create new alignment data with translated segments
            bilingual_data = AlignmentData(
                segments=translated_segments,
                word_segments=alignment_data.word_segments,  # Keep original word segments
                confidence_scores=alignment_data.confidence_scores,
                audio_duration=alignment_data.audio_duration,
                source_file=alignment_data.source_file
            )
            
            return bilingual_data
            
        except Exception as e:
            self.logger.error(f"Bilingual subtitle generation failed: {e}")
            # Return original data if translation fails completely
            return alignment_data
    
    def _test_service_connection(self, service: TranslationServiceEnum) -> bool:
        """Test connection to translation service."""
        try:
            if service == TranslationServiceEnum.DEEPL:
                return self._test_deepl_connection()
            elif service == TranslationServiceEnum.GOOGLE:
                return self._test_google_connection()
            else:
                return False
        except Exception:
            return False
    
    def _test_deepl_connection(self) -> bool:
        """Test DeepL API connection."""
        headers = {
            "Authorization": f"DeepL-Auth-Key {self.api_keys[TranslationServiceEnum.DEEPL]}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        data = {
            "text": "Hello",
            "target_lang": "ES"
        }
        
        response = requests.post(
            self.endpoints[TranslationServiceEnum.DEEPL],
            headers=headers,
            data=data,
            timeout=10
        )
        
        return response.status_code == 200
    
    def _test_google_connection(self) -> bool:
        """Test Google Translate API connection."""
        params = {
            "key": self.api_keys[TranslationServiceEnum.GOOGLE],
            "q": "Hello",
            "target": "es",
            "format": "text"
        }
        
        response = requests.post(
            self.endpoints[TranslationServiceEnum.GOOGLE],
            params=params,
            timeout=10
        )
        
        return response.status_code == 200
    
    def _perform_translation(self, text: str, target_language: str, service: TranslationServiceEnum) -> TranslationResult:
        """Perform actual translation request."""
        try:
            if service == TranslationServiceEnum.DEEPL:
                return self._translate_with_deepl(text, target_language)
            elif service == TranslationServiceEnum.GOOGLE:
                return self._translate_with_google(text, target_language)
            else:
                return TranslationResult(
                    success=False,
                    translated_text="",
                    original_text=text,
                    service_used=service,
                    error_message=f"Unsupported service: {service.value}"
                )
        except Exception as e:
            return TranslationResult(
                success=False,
                translated_text="",
                original_text=text,
                service_used=service,
                error_message=str(e)
            )
    
    def _translate_with_deepl(self, text: str, target_language: str) -> TranslationResult:
        """Translate text using DeepL API."""
        # Map language name to DeepL code
        lang_code = self._get_language_code(target_language, TranslationServiceEnum.DEEPL)
        if not lang_code:
            return TranslationResult(
                success=False,
                translated_text="",
                original_text=text,
                service_used=TranslationServiceEnum.DEEPL,
                error_message=f"Unsupported target language for DeepL: {target_language}"
            )
        
        headers = {
            "Authorization": f"DeepL-Auth-Key {self.api_keys[TranslationServiceEnum.DEEPL]}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        data = {
            "text": text,
            "target_lang": lang_code
        }
        
        response = requests.post(
            self.endpoints[TranslationServiceEnum.DEEPL],
            headers=headers,
            data=data,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            translated_text = result["translations"][0]["text"]
            
            return TranslationResult(
                success=True,
                translated_text=translated_text,
                original_text=text,
                service_used=TranslationServiceEnum.DEEPL
            )
        else:
            error_msg = f"DeepL API error: {response.status_code} - {response.text}"
            return TranslationResult(
                success=False,
                translated_text="",
                original_text=text,
                service_used=TranslationServiceEnum.DEEPL,
                error_message=error_msg
            )
    
    def _translate_with_google(self, text: str, target_language: str) -> TranslationResult:
        """Translate text using Google Translate API."""
        # Map language name to Google code
        lang_code = self._get_language_code(target_language, TranslationServiceEnum.GOOGLE)
        if not lang_code:
            return TranslationResult(
                success=False,
                translated_text="",
                original_text=text,
                service_used=TranslationServiceEnum.GOOGLE,
                error_message=f"Unsupported target language for Google Translate: {target_language}"
            )
        
        params = {
            "key": self.api_keys[TranslationServiceEnum.GOOG],
            "q": text,
            "target": lang_code,
            "format": "text"
        }
        
        response = requests.post(
            self.endpoints[TranslationServiceEnum.GOOGLE],
            params=params,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            translated_text = result["data"]["translations"][0]["translatedText"]
            
            return TranslationResult(
                success=True,
                translated_text=translated_text,
                original_text=text,
                service_used=TranslationServiceEnum.GOOGLE
            )
        else:
            error_msg = f"Google Translate API error: {response.status_code} - {response.text}"
            return TranslationResult(
                success=False,
                translated_text="",
                original_text=text,
                service_used=TranslationServiceEnum.GOOGLE,
                error_message=error_msg
            )
    
    def _get_language_code(self, language_name: str, service: TranslationServiceEnum) -> Optional[str]:
        """Get language code for service from language name."""
        language_name = language_name.lower().strip()
        return self.language_codes[service].get(language_name)
    
    def get_supported_languages(self, service: TranslationServiceEnum) -> List[str]:
        """Get list of supported languages for a service."""
        return list(self.language_codes[service].keys())
    
    def clear_api_key(self, service: TranslationServiceEnum) -> None:
        """Clear API key for a service."""
        if service in self.api_keys:
            del self.api_keys[service]
            self.logger.info(f"API key cleared for {service.value}")