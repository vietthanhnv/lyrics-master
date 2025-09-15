"""
Bilingual subtitle generation service.

This module provides a comprehensive service for generating bilingual subtitles
by coordinating translation services with subtitle generation, implementing
fallback handling and error recovery.
"""

import logging
from typing import Dict, Any, Optional, List
from pathlib import Path

from .interfaces import ITranslationService, ISubtitleGenerator
from .translation_service import TranslationServiceImpl
from .subtitle_generator import SubtitleGenerator
from ..models.data_models import (
    AlignmentData, ExportFormat, TranslationService, SubtitleFile, Segment
)


class BilingualSubtitleService:
    """Service for generating bilingual subtitles with translation integration."""
    
    def __init__(self, translation_service: Optional[ITranslationService] = None,
                 subtitle_generator: Optional[ISubtitleGenerator] = None):
        """
        Initialize the bilingual subtitle service.
        
        Args:
            translation_service: Optional translation service instance
            subtitle_generator: Optional subtitle generator instance
        """
        self.logger = logging.getLogger(__name__)
        self.translation_service = translation_service or TranslationServiceImpl()
        self.subtitle_generator = subtitle_generator or SubtitleGenerator()
    
    def generate_bilingual_subtitles(self, alignment_data: AlignmentData, 
                                   target_language: str,
                                   translation_service: TranslationService,
                                   export_formats: List[ExportFormat],
                                   output_directory: str,
                                   base_filename: str,
                                   options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Generate bilingual subtitles in multiple formats.
        
        Args:
            alignment_data: The original alignment data
            target_language: Target language for translation
            translation_service: Translation service to use
            export_formats: List of formats to export
            output_directory: Directory to save subtitle files
            base_filename: Base filename for output files
            options: Optional generation options
            
        Returns:
            Dictionary containing results and generated files
            
        Raises:
            ValueError: If parameters are invalid
        """
        if not alignment_data:
            raise ValueError("Alignment data cannot be None")
        
        if not target_language:
            raise ValueError("Target language must be specified")
        
        if not export_formats:
            raise ValueError("At least one export format must be specified")
        
        # Set default options
        if options is None:
            options = {}
        
        word_level = options.get('word_level', False)
        words_per_subtitle = options.get('words_per_subtitle')
        style_options = options.get('style_options', {})
        include_fallback = options.get('include_fallback', True)
        
        results = {
            'success': False,
            'generated_files': [],
            'errors': [],
            'translation_success': False,
            'fallback_used': False,
            'bilingual_data': None
        }
        
        try:
            # Step 1: Generate bilingual alignment data
            self.logger.info(f"Generating bilingual subtitles for language: {target_language}")
            
            bilingual_data = self._create_bilingual_alignment_data(
                alignment_data, target_language, translation_service, include_fallback)
            
            if bilingual_data:
                results['bilingual_data'] = bilingual_data
                results['translation_success'] = self._has_translations(bilingual_data)
                results['fallback_used'] = not results['translation_success'] and include_fallback
                
                # Step 2: Generate subtitle files in requested formats
                generated_files = []
                
                for format_type in export_formats:
                    try:
                        output_path = self._build_output_path(
                            output_directory, base_filename, format_type, target_language)
                        
                        subtitle_file = self._generate_format_specific_file(
                            bilingual_data, output_path, format_type, target_language,
                            word_level, words_per_subtitle, style_options)
                        
                        generated_files.append({
                            'format': format_type.value,
                            'path': subtitle_file.path,
                            'word_count': subtitle_file.word_count,
                            'duration': subtitle_file.duration
                        })
                        
                        self.logger.info(f"Generated {format_type.value} file: {subtitle_file.path}")
                        
                    except Exception as e:
                        error_msg = f"Failed to generate {format_type.value} file: {str(e)}"
                        self.logger.error(error_msg)
                        results['errors'].append(error_msg)
                
                results['generated_files'] = generated_files
                results['success'] = len(generated_files) > 0
                
            else:
                results['errors'].append("Failed to create bilingual alignment data")
                
        except Exception as e:
            error_msg = f"Bilingual subtitle generation failed: {str(e)}"
            self.logger.error(error_msg)
            results['errors'].append(error_msg)
        
        return results
    
    def _create_bilingual_alignment_data(self, alignment_data: AlignmentData,
                                       target_language: str,
                                       translation_service: TranslationService,
                                       include_fallback: bool = True) -> Optional[AlignmentData]:
        """
        Create bilingual alignment data by translating segments.
        
        Args:
            alignment_data: Original alignment data
            target_language: Target language for translation
            translation_service: Translation service to use
            include_fallback: Whether to include fallback handling
            
        Returns:
            AlignmentData with bilingual segments or None if failed
        """
        try:
            # Check if translation service is available
            if not self.translation_service.is_service_available(translation_service):
                if include_fallback:
                    self.logger.warning(f"Translation service {translation_service.value} not available, using original text only")
                    return alignment_data  # Return original data as fallback
                else:
                    self.logger.error(f"Translation service {translation_service.value} not available")
                    return None
            
            # Generate bilingual subtitles using translation service
            bilingual_data = self.translation_service.generate_bilingual_subtitles(
                alignment_data, target_language, translation_service)
            
            return bilingual_data
            
        except Exception as e:
            self.logger.error(f"Failed to create bilingual alignment data: {e}")
            
            if include_fallback:
                self.logger.warning("Using original alignment data as fallback")
                return alignment_data
            else:
                return None
    
    def _has_translations(self, alignment_data: AlignmentData) -> bool:
        """
        Check if alignment data contains actual translations.
        
        Args:
            alignment_data: Alignment data to check
            
        Returns:
            True if translations are present, False otherwise
        """
        if not alignment_data or not alignment_data.segments:
            return False
        
        # Check if any segment has bilingual text (contains newline)
        for segment in alignment_data.segments:
            if '\n' in segment.text:
                lines = segment.text.split('\n')
                if len(lines) >= 2 and lines[0].strip() != lines[1].strip():
                    return True
        
        return False
    
    def _build_output_path(self, output_directory: str, base_filename: str,
                          format_type: ExportFormat, target_language: str) -> str:
        """
        Build output file path for bilingual subtitle file.
        
        Args:
            output_directory: Output directory
            base_filename: Base filename
            format_type: Export format
            target_language: Target language
            
        Returns:
            Complete output file path
        """
        # Create bilingual filename
        name_parts = Path(base_filename).stem
        bilingual_filename = f"{name_parts}_bilingual_{target_language}.{format_type.value}"
        
        return str(Path(output_directory) / bilingual_filename)
    
    def _generate_format_specific_file(self, alignment_data: AlignmentData,
                                     output_path: str, format_type: ExportFormat,
                                     target_language: str, word_level: bool = False,
                                     words_per_subtitle: Optional[int] = None,
                                     style_options: Dict[str, Any] = None) -> SubtitleFile:
        """
        Generate subtitle file for specific format.
        
        Args:
            alignment_data: Bilingual alignment data
            output_path: Output file path
            format_type: Export format
            target_language: Target language
            word_level: Whether to use word-level timing
            words_per_subtitle: Number of words per subtitle (if applicable)
            style_options: Styling options (for ASS format)
            
        Returns:
            SubtitleFile object with metadata
            
        Raises:
            ValueError: If format is not supported or parameters are invalid
        """
        return self.subtitle_generator.generate_bilingual_subtitle_file(
            alignment_data=alignment_data,
            output_path=output_path,
            format_type=format_type,
            target_language=target_language,
            word_level=word_level,
            words_per_subtitle=words_per_subtitle,
            style_options=style_options
        )
    
    def set_translation_api_key(self, service: TranslationService, api_key: str) -> None:
        """
        Set API key for translation service.
        
        Args:
            service: Translation service
            api_key: API key to set
            
        Raises:
            ValueError: If API key is invalid
        """
        self.translation_service.set_api_key(service, api_key)
        self.logger.info(f"API key set for {service.value}")
    
    def check_translation_service_availability(self, service: TranslationService) -> bool:
        """
        Check if translation service is available.
        
        Args:
            service: Translation service to check
            
        Returns:
            True if service is available, False otherwise
        """
        return self.translation_service.is_service_available(service)
    
    def get_supported_languages(self, service: TranslationService) -> List[str]:
        """
        Get list of supported languages for translation service.
        
        Args:
            service: Translation service
            
        Returns:
            List of supported language names
        """
        return self.translation_service.get_supported_languages(service)
    
    def validate_bilingual_options(self, options: Dict[str, Any]) -> List[str]:
        """
        Validate bilingual subtitle generation options.
        
        Args:
            options: Options dictionary to validate
            
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        
        # Validate word-level options
        if options.get('word_level', False):
            words_per_subtitle = options.get('words_per_subtitle')
            if words_per_subtitle is not None:
                if not isinstance(words_per_subtitle, int) or words_per_subtitle < 1:
                    errors.append("words_per_subtitle must be a positive integer")
        
        # Validate style options for ASS format
        style_options = options.get('style_options', {})
        if style_options:
            if 'font_size' in style_options:
                try:
                    font_size = int(style_options['font_size'])
                    if font_size < 8 or font_size > 72:
                        errors.append("font_size must be between 8 and 72")
                except (ValueError, TypeError):
                    errors.append("font_size must be a valid integer")
        
        return errors
    
    def generate_preview(self, alignment_data: AlignmentData, target_language: str,
                        translation_service: TranslationService, format_type: ExportFormat,
                        max_segments: int = 5) -> str:
        """
        Generate a preview of bilingual subtitles for testing.
        
        Args:
            alignment_data: Original alignment data
            target_language: Target language for translation
            translation_service: Translation service to use
            format_type: Format to preview
            max_segments: Maximum number of segments to include in preview
            
        Returns:
            Preview content as string
            
        Raises:
            ValueError: If parameters are invalid
        """
        if not alignment_data or not alignment_data.segments:
            raise ValueError("Alignment data must contain segments")
        
        # Create preview data with limited segments
        preview_segments = alignment_data.segments[:max_segments]
        preview_word_segments = [
            ws for ws in alignment_data.word_segments 
            if any(ws.segment_id == seg.segment_id for seg in preview_segments)
        ]
        
        preview_alignment = AlignmentData(
            segments=preview_segments,
            word_segments=preview_word_segments,
            confidence_scores=alignment_data.confidence_scores[:max_segments],
            audio_duration=preview_segments[-1].end_time if preview_segments else 0.0,
            source_file=alignment_data.source_file
        )
        
        # Generate bilingual preview data
        bilingual_preview = self._create_bilingual_alignment_data(
            preview_alignment, target_language, translation_service, include_fallback=True)
        
        if not bilingual_preview:
            raise ValueError("Failed to create bilingual preview data")
        
        # Generate preview content
        if format_type == ExportFormat.SRT:
            return self.subtitle_generator.generate_bilingual_srt(bilingual_preview)
        elif format_type == ExportFormat.ASS:
            return self.subtitle_generator.generate_bilingual_ass_karaoke(bilingual_preview)
        elif format_type == ExportFormat.VTT:
            return self.subtitle_generator.generate_bilingual_vtt(bilingual_preview)
        elif format_type == ExportFormat.JSON:
            return self.subtitle_generator.export_bilingual_json_alignment(bilingual_preview, target_language)
        else:
            raise ValueError(f"Unsupported preview format: {format_type}")