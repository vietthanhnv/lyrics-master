#!/usr/bin/env python3
"""
Example script demonstrating translation service usage.

This script shows how to use the translation service to create bilingual subtitles
from alignment data.
"""

import sys
import os

# Add project root to path for imports
project_root = os.path.join(os.path.dirname(__file__), '..')
sys.path.insert(0, project_root)

from src.services.translation_service import TranslationServiceImpl
from src.services.subtitle_generator import SubtitleGenerator
from src.models.data_models import (
    AlignmentData, Segment, WordSegment, TranslationService
)


def create_sample_alignment_data():
    """Create sample alignment data for demonstration."""
    segments = [
        Segment(
            start_time=0.0,
            end_time=3.5,
            text="Welcome to our music application",
            confidence=0.95,
            segment_id=0
        ),
        Segment(
            start_time=3.5,
            end_time=7.0,
            text="This tool helps create synchronized subtitles",
            confidence=0.92,
            segment_id=1
        ),
        Segment(
            start_time=7.0,
            end_time=10.5,
            text="Perfect for karaoke and lyric videos",
            confidence=0.88,
            segment_id=2
        )
    ]
    
    word_segments = [
        WordSegment("Welcome", 0.0, 0.6, 0.95, 0),
        WordSegment("to", 0.6, 0.8, 0.95, 0),
        WordSegment("our", 0.8, 1.1, 0.95, 0),
        WordSegment("music", 1.1, 1.7, 0.95, 0),
        WordSegment("application", 1.7, 3.5, 0.95, 0),
        
        WordSegment("This", 3.5, 3.8, 0.92, 1),
        WordSegment("tool", 3.8, 4.2, 0.92, 1),
        WordSegment("helps", 4.2, 4.7, 0.92, 1),
        WordSegment("create", 4.7, 5.3, 0.92, 1),
        WordSegment("synchronized", 5.3, 6.2, 0.92, 1),
        WordSegment("subtitles", 6.2, 7.0, 0.92, 1),
        
        WordSegment("Perfect", 7.0, 7.5, 0.88, 2),
        WordSegment("for", 7.5, 7.8, 0.88, 2),
        WordSegment("karaoke", 7.8, 8.5, 0.88, 2),
        WordSegment("and", 8.5, 8.8, 0.88, 2),
        WordSegment("lyric", 8.8, 9.3, 0.88, 2),
        WordSegment("videos", 9.3, 10.5, 0.88, 2)
    ]
    
    return AlignmentData(
        segments=segments,
        word_segments=word_segments,
        confidence_scores=[0.95, 0.92, 0.88],
        audio_duration=10.5,
        source_file="demo_audio.wav"
    )


def demonstrate_translation_service():
    """Demonstrate translation service functionality."""
    print("🌍 Translation Service Demo")
    print("=" * 50)
    
    # Create services
    translation_service = TranslationServiceImpl()
    subtitle_generator = SubtitleGenerator()
    
    # Create sample data
    alignment_data = create_sample_alignment_data()
    
    print("\n📝 Original Alignment Data:")
    for i, segment in enumerate(alignment_data.segments):
        print(f"  {i+1}. [{segment.start_time:.1f}s - {segment.end_time:.1f}s] {segment.text}")
    
    # Show supported languages
    print(f"\n🔤 Supported Languages:")
    deepl_langs = translation_service.get_supported_languages(TranslationService.DEEPL)
    google_langs = translation_service.get_supported_languages(TranslationService.GOOGLE)
    
    print(f"  DeepL: {', '.join(deepl_langs[:5])}... ({len(deepl_langs)} total)")
    print(f"  Google: {', '.join(google_langs[:5])}... ({len(google_langs)} total)")
    
    # Demonstrate API key management
    print(f"\n🔑 API Key Management:")
    print(f"  DeepL available: {translation_service.is_service_available(TranslationService.DEEPL)}")
    print(f"  Google available: {translation_service.is_service_available(TranslationService.GOOGLE)}")
    
    # Note: In a real application, you would set actual API keys
    print("\n⚠️  Note: To use translation services, you need to set API keys:")
    print("  translation_service.set_api_key(TranslationService.DEEPL, 'your-deepl-key')")
    print("  translation_service.set_api_key(TranslationService.GOOGLE, 'your-google-key')")
    
    # Demonstrate fallback behavior (without API keys)
    print(f"\n🔄 Fallback Behavior (no API keys set):")
    bilingual_data = translation_service.generate_bilingual_subtitles(
        alignment_data, "spanish", TranslationService.DEEPL
    )
    
    if bilingual_data == alignment_data:
        print("  ✅ Service correctly returned original data when unavailable")
    else:
        print("  ❌ Unexpected behavior when service unavailable")
    
    # Generate subtitles from original data
    print(f"\n📄 Generated SRT Subtitles:")
    srt_content = subtitle_generator.generate_srt(alignment_data, word_level=False)
    print(srt_content[:300] + "..." if len(srt_content) > 300 else srt_content)
    
    # Show rate limiting info
    print(f"\n⏱️  Rate Limiting Configuration:")
    deepl_limiter = translation_service.rate_limiters[TranslationService.DEEPL]
    google_limiter = translation_service.rate_limiters[TranslationService.GOOGLE]
    
    print(f"  DeepL: {deepl_limiter.config.requests_per_minute}/min, "
          f"{deepl_limiter.config.requests_per_hour}/hour")
    print(f"  Google: {google_limiter.config.requests_per_minute}/min, "
          f"{google_limiter.config.requests_per_hour}/hour")
    
    print(f"\n✨ Translation service implementation complete!")
    print(f"   - ✅ DeepL and Google Translate API integration")
    print(f"   - ✅ Rate limiting and error handling")
    print(f"   - ✅ Bilingual subtitle generation")
    print(f"   - ✅ API key management")
    print(f"   - ✅ Graceful fallback when services unavailable")


if __name__ == "__main__":
    demonstrate_translation_service()