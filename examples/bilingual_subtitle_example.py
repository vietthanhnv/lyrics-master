"""
Example script demonstrating bilingual subtitle generation functionality.

This script shows how to use the bilingual subtitle service to generate
subtitles in multiple languages and formats with fallback handling.
"""

import os
import tempfile
from pathlib import Path

from src.services.bilingual_subtitle_service import BilingualSubtitleService
from src.services.translation_service import TranslationServiceImpl
from src.services.subtitle_generator import SubtitleGenerator
from src.models.data_models import (
    AlignmentData, Segment, WordSegment, ExportFormat, TranslationService
)


def create_sample_alignment_data():
    """Create sample alignment data for demonstration."""
    segments = [
        Segment(
            start_time=0.0,
            end_time=3.5,
            text="Welcome to our artificial intelligence tutorial",
            confidence=0.95,
            segment_id=1
        ),
        Segment(
            start_time=3.5,
            end_time=7.0,
            text="Today we will learn about machine learning algorithms",
            confidence=0.88,
            segment_id=2
        ),
        Segment(
            start_time=7.0,
            end_time=10.5,
            text="Neural networks are the foundation of deep learning",
            confidence=0.92,
            segment_id=3
        ),
        Segment(
            start_time=10.5,
            end_time=13.0,
            text="Thank you for watching this educational content",
            confidence=0.90,
            segment_id=4
        )
    ]
    
    word_segments = [
        # Segment 1 words
        WordSegment(word="Welcome", start_time=0.0, end_time=0.6, confidence=0.95, segment_id=1),
        WordSegment(word="to", start_time=0.6, end_time=0.8, confidence=0.94, segment_id=1),
        WordSegment(word="our", start_time=0.8, end_time=1.0, confidence=0.96, segment_id=1),
        WordSegment(word="artificial", start_time=1.0, end_time=1.8, confidence=0.93, segment_id=1),
        WordSegment(word="intelligence", start_time=1.8, end_time=2.6, confidence=0.95, segment_id=1),
        WordSegment(word="tutorial", start_time=2.6, end_time=3.5, confidence=0.97, segment_id=1),
        
        # Segment 2 words
        WordSegment(word="Today", start_time=3.5, end_time=3.9, confidence=0.89, segment_id=2),
        WordSegment(word="we", start_time=3.9, end_time=4.1, confidence=0.87, segment_id=2),
        WordSegment(word="will", start_time=4.1, end_time=4.4, confidence=0.88, segment_id=2),
        WordSegment(word="learn", start_time=4.4, end_time=4.8, confidence=0.86, segment_id=2),
        WordSegment(word="about", start_time=4.8, end_time=5.1, confidence=0.90, segment_id=2),
        WordSegment(word="machine", start_time=5.1, end_time=5.6, confidence=0.85, segment_id=2),
        WordSegment(word="learning", start_time=5.6, end_time=6.2, confidence=0.88, segment_id=2),
        WordSegment(word="algorithms", start_time=6.2, end_time=7.0, confidence=0.84, segment_id=2),
        
        # Segment 3 words
        WordSegment(word="Neural", start_time=7.0, end_time=7.4, confidence=0.93, segment_id=3),
        WordSegment(word="networks", start_time=7.4, end_time=8.0, confidence=0.91, segment_id=3),
        WordSegment(word="are", start_time=8.0, end_time=8.2, confidence=0.92, segment_id=3),
        WordSegment(word="the", start_time=8.2, end_time=8.4, confidence=0.94, segment_id=3),
        WordSegment(word="foundation", start_time=8.4, end_time=9.2, confidence=0.90, segment_id=3),
        WordSegment(word="of", start_time=9.2, end_time=9.4, confidence=0.95, segment_id=3),
        WordSegment(word="deep", start_time=9.4, end_time=9.8, confidence=0.89, segment_id=3),
        WordSegment(word="learning", start_time=9.8, end_time=10.5, confidence=0.93, segment_id=3),
        
        # Segment 4 words
        WordSegment(word="Thank", start_time=10.5, end_time=10.8, confidence=0.91, segment_id=4),
        WordSegment(word="you", start_time=10.8, end_time=11.0, confidence=0.92, segment_id=4),
        WordSegment(word="for", start_time=11.0, end_time=11.2, confidence=0.90, segment_id=4),
        WordSegment(word="watching", start_time=11.2, end_time=11.8, confidence=0.94, segment_id=4),
        WordSegment(word="this", start_time=11.8, end_time=12.1, confidence=0.88, segment_id=4),
        WordSegment(word="educational", start_time=12.1, end_time=12.7, confidence=0.86, segment_id=4),
        WordSegment(word="content", start_time=12.7, end_time=13.0, confidence=0.92, segment_id=4)
    ]
    
    return AlignmentData(
        segments=segments,
        word_segments=word_segments,
        confidence_scores=[0.95, 0.88, 0.92, 0.90],
        audio_duration=13.0,
        source_file="ai_tutorial.wav"
    )


def mock_translation_service():
    """Create a mock translation service for demonstration."""
    class MockTranslationService(TranslationServiceImpl):
        def __init__(self):
            super().__init__()
            # Mock translations for demonstration
            self.mock_translations = {
                "spanish": {
                    "Welcome to our artificial intelligence tutorial": "Bienvenidos a nuestro tutorial de inteligencia artificial",
                    "Today we will learn about machine learning algorithms": "Hoy aprenderemos sobre algoritmos de aprendizaje automático",
                    "Neural networks are the foundation of deep learning": "Las redes neuronales son la base del aprendizaje profundo",
                    "Thank you for watching this educational content": "Gracias por ver este contenido educativo"
                },
                "french": {
                    "Welcome to our artificial intelligence tutorial": "Bienvenue à notre tutoriel d'intelligence artificielle",
                    "Today we will learn about machine learning algorithms": "Aujourd'hui nous apprendrons les algorithmes d'apprentissage automatique",
                    "Neural networks are the foundation of deep learning": "Les réseaux de neurones sont la base de l'apprentissage profond",
                    "Thank you for watching this educational content": "Merci d'avoir regardé ce contenu éducatif"
                }
            }
        
        def is_service_available(self, service: TranslationService) -> bool:
            """Mock service availability - always return True for demo."""
            return True
        
        def translate_text(self, text: str, target_language: str, service: TranslationService) -> str:
            """Mock translation method."""
            if target_language in self.mock_translations and text in self.mock_translations[target_language]:
                return self.mock_translations[target_language][text]
            return f"[MOCK TRANSLATION TO {target_language.upper()}]: {text}"
        
        def _perform_translation(self, text: str, target_language: str, service: TranslationService):
            """Mock internal translation method."""
            from src.services.translation_service import TranslationResult
            translated_text = self.translate_text(text, target_language, service)
            return TranslationResult(
                success=True,
                translated_text=translated_text,
                original_text=text,
                service_used=service
            )
    
    return MockTranslationService()


def demonstrate_bilingual_subtitle_generation():
    """Demonstrate bilingual subtitle generation with various options."""
    print("🎬 Bilingual Subtitle Generation Demo")
    print("=" * 50)
    
    # Create sample data
    alignment_data = create_sample_alignment_data()
    print(f"📊 Created sample alignment data with {len(alignment_data.segments)} segments")
    print(f"   Audio duration: {alignment_data.audio_duration} seconds")
    print(f"   Word segments: {len(alignment_data.word_segments)} words")
    
    # Create services
    translation_service = mock_translation_service()
    subtitle_generator = SubtitleGenerator()
    bilingual_service = BilingualSubtitleService(translation_service, subtitle_generator)
    
    # Create temporary directory for output
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"\n📁 Output directory: {temp_dir}")
        
        # Example 1: Generate Spanish bilingual subtitles in multiple formats
        print("\n🇪🇸 Example 1: Spanish bilingual subtitles (SRT, VTT, JSON)")
        result1 = bilingual_service.generate_bilingual_subtitles(
            alignment_data=alignment_data,
            target_language="spanish",
            translation_service=TranslationService.DEEPL,
            export_formats=[ExportFormat.SRT, ExportFormat.VTT, ExportFormat.JSON],
            output_directory=temp_dir,
            base_filename="ai_tutorial"
        )
        
        print(f"   ✅ Success: {result1['success']}")
        print(f"   🌐 Translation success: {result1['translation_success']}")
        print(f"   📄 Generated files: {len(result1['generated_files'])}")
        
        for file_info in result1['generated_files']:
            print(f"      - {file_info['format'].upper()}: {Path(file_info['path']).name}")
            print(f"        Words: {file_info['word_count']}, Duration: {file_info['duration']}s")
        
        # Example 2: Generate French bilingual ASS karaoke subtitles
        print("\n🇫🇷 Example 2: French bilingual ASS karaoke subtitles")
        result2 = bilingual_service.generate_bilingual_subtitles(
            alignment_data=alignment_data,
            target_language="french",
            translation_service=TranslationService.GOOGLE,
            export_formats=[ExportFormat.ASS],
            output_directory=temp_dir,
            base_filename="ai_tutorial",
            options={
                'style_options': {
                    'font_size': 20,
                    'font_name': 'Arial',
                    'primary_color': '#FFFFFF',
                    'karaoke_fill_color': '#FFFF00'
                }
            }
        )
        
        print(f"   ✅ Success: {result2['success']}")
        print(f"   📄 Generated files: {len(result2['generated_files'])}")
        
        # Example 3: Generate word-level bilingual subtitles
        print("\n📝 Example 3: Word-level bilingual subtitles (grouped)")
        result3 = bilingual_service.generate_bilingual_subtitles(
            alignment_data=alignment_data,
            target_language="spanish",
            translation_service=TranslationService.DEEPL,
            export_formats=[ExportFormat.SRT, ExportFormat.VTT],
            output_directory=temp_dir,
            base_filename="ai_tutorial_words",
            options={
                'word_level': True,
                'words_per_subtitle': 3
            }
        )
        
        print(f"   ✅ Success: {result3['success']}")
        print(f"   📄 Generated files: {len(result3['generated_files'])}")
        
        # Example 4: Generate preview
        print("\n👀 Example 4: Generate preview (first 2 segments)")
        preview_content = bilingual_service.generate_preview(
            alignment_data=alignment_data,
            target_language="spanish",
            translation_service=TranslationService.DEEPL,
            format_type=ExportFormat.SRT,
            max_segments=2
        )
        
        print("   Preview content:")
        print("   " + "─" * 40)
        for line in preview_content.split('\n')[:10]:  # Show first 10 lines
            print(f"   {line}")
        if len(preview_content.split('\n')) > 10:
            print("   ... (truncated)")
        
        # Example 5: Demonstrate fallback handling
        print("\n🔄 Example 5: Fallback handling (service unavailable)")
        
        # Create a service that simulates unavailable translation
        class UnavailableTranslationService(TranslationServiceImpl):
            def is_service_available(self, service: TranslationService) -> bool:
                return False
        
        unavailable_service = UnavailableTranslationService()
        fallback_bilingual_service = BilingualSubtitleService(unavailable_service, subtitle_generator)
        
        result5 = fallback_bilingual_service.generate_bilingual_subtitles(
            alignment_data=alignment_data,
            target_language="german",
            translation_service=TranslationService.DEEPL,
            export_formats=[ExportFormat.SRT],
            output_directory=temp_dir,
            base_filename="ai_tutorial_fallback",
            options={'include_fallback': True}
        )
        
        print(f"   ✅ Success: {result5['success']}")
        print(f"   🌐 Translation success: {result5['translation_success']}")
        print(f"   🔄 Fallback used: {result5['fallback_used']}")
        
        # Show sample file contents
        print("\n📖 Sample file contents:")
        if result1['generated_files']:
            srt_file = next((f for f in result1['generated_files'] if f['format'] == 'srt'), None)
            if srt_file:
                print(f"\n   📄 {Path(srt_file['path']).name}:")
                print("   " + "─" * 40)
                with open(srt_file['path'], 'r', encoding='utf-8') as f:
                    content = f.read()
                    for line in content.split('\n')[:15]:  # Show first 15 lines
                        print(f"   {line}")
                    if len(content.split('\n')) > 15:
                        print("   ... (truncated)")
        
        print(f"\n🎉 Demo completed! Check the output directory for generated files:")
        print(f"   {temp_dir}")
        
        # List all generated files
        print("\n📋 All generated files:")
        for file_path in Path(temp_dir).glob("*"):
            if file_path.is_file():
                size_kb = file_path.stat().st_size / 1024
                print(f"   📄 {file_path.name} ({size_kb:.1f} KB)")


def demonstrate_validation_and_error_handling():
    """Demonstrate validation and error handling features."""
    print("\n🔍 Validation and Error Handling Demo")
    print("=" * 50)
    
    bilingual_service = BilingualSubtitleService()
    
    # Test validation
    print("\n✅ Testing option validation:")
    
    valid_options = {
        'word_level': True,
        'words_per_subtitle': 3,
        'style_options': {'font_size': 16}
    }
    errors = bilingual_service.validate_bilingual_options(valid_options)
    print(f"   Valid options: {len(errors)} errors")
    
    invalid_options = {
        'word_level': True,
        'words_per_subtitle': -1,  # Invalid
        'style_options': {'font_size': 100}  # Invalid
    }
    errors = bilingual_service.validate_bilingual_options(invalid_options)
    print(f"   Invalid options: {len(errors)} errors")
    for error in errors:
        print(f"      - {error}")
    
    # Test supported languages
    print(f"\n🌍 Supported languages:")
    mock_service = mock_translation_service()
    bilingual_service_with_mock = BilingualSubtitleService(mock_service)
    
    for service in [TranslationService.DEEPL, TranslationService.GOOGLE]:
        languages = bilingual_service_with_mock.get_supported_languages(service)
        print(f"   {service.value}: {', '.join(languages[:5])}{'...' if len(languages) > 5 else ''}")


if __name__ == "__main__":
    try:
        demonstrate_bilingual_subtitle_generation()
        demonstrate_validation_and_error_handling()
        
        print("\n" + "=" * 50)
        print("🎯 Key Features Demonstrated:")
        print("   ✅ Bilingual subtitle generation in multiple formats")
        print("   ✅ Word-level and sentence-level timing")
        print("   ✅ ASS karaoke styling with bilingual support")
        print("   ✅ Fallback handling when translation unavailable")
        print("   ✅ Preview generation for testing")
        print("   ✅ Comprehensive validation and error handling")
        print("   ✅ Support for multiple translation services")
        
    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()