"""
Subtitle generation service.

This module provides the main subtitle generation service that coordinates
different format exporters and implements the ISubtitleGenerator interface.
"""

import os
import json
from typing import Dict, Any, Optional, List
from pathlib import Path

from .interfaces import ISubtitleGenerator
from .srt_exporter import SRTExporter
from .ass_exporter import ASSExporter
from .vtt_exporter import VTTExporter
from .json_exporter import JSONExporter
from ..models.data_models import AlignmentData, ExportFormat, SubtitleFile


class SubtitleGenerator(ISubtitleGenerator):
    """Main subtitle generation service coordinating different format exporters."""
    
    def __init__(self):
        """Initialize the subtitle generator with format exporters."""
        self.srt_exporter = SRTExporter()
        self.ass_exporter = ASSExporter()
        self.vtt_exporter = VTTExporter()
        self.json_exporter = JSONExporter()
    
    def generate_srt(self, alignment_data: AlignmentData, word_level: bool = False) -> str:
        """
        Generate SRT format subtitles.
        
        Args:
            alignment_data: The alignment data containing segments and timing
            word_level: If True, generate word-level subtitles; otherwise sentence-level
            
        Returns:
            SRT formatted subtitle content as string
            
        Raises:
            ValueError: If alignment data is invalid
        """
        if word_level:
            return self.srt_exporter.generate_word_level(alignment_data)
        else:
            return self.srt_exporter.generate_sentence_level(alignment_data)
    
    def generate_srt_grouped_words(self, alignment_data: AlignmentData, words_per_subtitle: int = 3) -> str:
        """
        Generate SRT format subtitles with grouped words.
        
        Args:
            alignment_data: The alignment data containing word segments
            words_per_subtitle: Number of words to group per subtitle entry
            
        Returns:
            SRT formatted subtitle content as string
            
        Raises:
            ValueError: If alignment data is invalid
        """
        return self.srt_exporter.generate_grouped_words(alignment_data, words_per_subtitle)
    
    def generate_ass_karaoke(self, alignment_data: AlignmentData, style_options: Dict[str, Any] = None) -> str:
        """
        Generate ASS format subtitles with karaoke styling.
        
        Args:
            alignment_data: The alignment data containing segments and timing
            style_options: Optional styling configuration
            
        Returns:
            ASS formatted subtitle content as string
            
        Raises:
            ValueError: If alignment data is invalid
        """
        return self.ass_exporter.generate_karaoke_subtitles(alignment_data, style_options)
    
    def generate_vtt(self, alignment_data: AlignmentData) -> str:
        """
        Generate VTT format subtitles.
        
        Args:
            alignment_data: The alignment data containing segments and timing
            
        Returns:
            VTT formatted subtitle content as string
            
        Raises:
            ValueError: If alignment data is invalid
        """
        return self.vtt_exporter.generate_sentence_level(alignment_data)
    
    def export_json_alignment(self, alignment_data: AlignmentData) -> str:
        """
        Export alignment data as JSON.
        
        Args:
            alignment_data: The alignment data to export
            
        Returns:
            JSON formatted alignment data as string
            
        Raises:
            ValueError: If alignment data is invalid
        """
        return self.json_exporter.export_alignment_data(alignment_data)
    
    def save_subtitle_file(self, content: str, file_path: str, format_type: ExportFormat) -> bool:
        """
        Save subtitle content to file.
        
        Args:
            content: The subtitle content to save
            file_path: Path where to save the file
            format_type: The format type for validation
            
        Returns:
            True if file was saved successfully, False otherwise
            
        Raises:
            ValueError: If content is empty or file path is invalid
            OSError: If file cannot be written
        """
        if not content.strip():
            raise ValueError("Content cannot be empty")
        
        if not file_path:
            raise ValueError("File path cannot be empty")
        
        try:
            # Ensure directory exists
            file_path_obj = Path(file_path)
            file_path_obj.parent.mkdir(parents=True, exist_ok=True)
            
            # Validate content based on format
            if format_type == ExportFormat.SRT:
                validation_errors = self.srt_exporter.validate_srt_content(content)
                if validation_errors:
                    raise ValueError(f"Invalid SRT content: {'; '.join(validation_errors)}")
            elif format_type == ExportFormat.ASS:
                validation_errors = self.ass_exporter.validate_ass_content(content)
                if validation_errors:
                    raise ValueError(f"Invalid ASS content: {'; '.join(validation_errors)}")
            elif format_type == ExportFormat.VTT:
                validation_errors = self.vtt_exporter.validate_vtt_content(content)
                if validation_errors:
                    raise ValueError(f"Invalid VTT content: {'; '.join(validation_errors)}")
            elif format_type == ExportFormat.JSON:
                validation_errors = self.json_exporter.validate_json_content(content)
                if validation_errors:
                    raise ValueError(f"Invalid JSON content: {'; '.join(validation_errors)}")
            
            # Write file with UTF-8 encoding
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return True
            
        except (OSError, IOError) as e:
            raise OSError(f"Failed to write file {file_path}: {str(e)}")
    
    def generate_subtitle_file(self, alignment_data: AlignmentData, output_path: str, 
                             format_type: ExportFormat, word_level: bool = False,
                             words_per_subtitle: Optional[int] = None) -> SubtitleFile:
        """
        Generate and save a complete subtitle file.
        
        Args:
            alignment_data: The alignment data containing segments and timing
            output_path: Path where to save the subtitle file
            format_type: The subtitle format to generate
            word_level: If True, generate word-level subtitles (SRT only)
            words_per_subtitle: If specified, group words (SRT only)
            
        Returns:
            SubtitleFile object with metadata about the generated file
            
        Raises:
            ValueError: If parameters are invalid
            NotImplementedError: If format is not yet supported
        """
        # Generate content based on format
        if format_type == ExportFormat.SRT:
            if words_per_subtitle is not None:
                content = self.generate_srt_grouped_words(alignment_data, words_per_subtitle)
            else:
                content = self.generate_srt(alignment_data, word_level)
        elif format_type == ExportFormat.ASS:
            content = self.generate_ass_karaoke(alignment_data)
        elif format_type == ExportFormat.VTT:
            content = self.generate_vtt(alignment_data)
        elif format_type == ExportFormat.JSON:
            content = self.export_json_alignment(alignment_data)
        else:
            raise ValueError(f"Unsupported format: {format_type}")
        
        # Save the file
        self.save_subtitle_file(content, output_path, format_type)
        
        # Count words in content
        word_count = self._count_words_in_content(content, format_type)
        
        # Get file size
        file_size = os.path.getsize(output_path) if os.path.exists(output_path) else 0
        
        return SubtitleFile(
            path=output_path,
            format=format_type,
            content=content,
            word_count=word_count,
            duration=alignment_data.audio_duration
        )
    
    def _count_words_in_content(self, content: str, format_type: ExportFormat) -> int:
        """
        Count words in subtitle content.
        
        Args:
            content: The subtitle content
            format_type: The format type for parsing
            
        Returns:
            Number of words in the content
        """
        if format_type == ExportFormat.SRT:
            # For SRT, extract text lines and count words
            lines = content.split('\n')
            text_lines = []
            
            for i, line in enumerate(lines):
                # Skip subtitle numbers and timing lines
                if i % 4 >= 2:  # Text lines are at positions 2, 3, 6, 7, etc.
                    if line.strip() and '-->' not in line and not line.strip().isdigit():
                        text_lines.append(line.strip())
            
            # Count words in all text lines
            word_count = 0
            for text_line in text_lines:
                word_count += len(text_line.split())
            
            return word_count
        
        # For other formats, simple word count
        return len(content.split())
    
    def get_supported_formats(self) -> list[ExportFormat]:
        """
        Get list of currently supported export formats.
        
        Returns:
            List of supported ExportFormat values
        """
        return [ExportFormat.SRT, ExportFormat.ASS, ExportFormat.VTT, ExportFormat.JSON]
    
    def generate_vtt_word_level(self, alignment_data: AlignmentData) -> str:
        """
        Generate word-level VTT subtitles.
        
        Args:
            alignment_data: The alignment data containing word segments
            
        Returns:
            VTT formatted subtitle content as string
            
        Raises:
            ValueError: If alignment data is invalid
        """
        return self.vtt_exporter.generate_word_level(alignment_data)
    
    def generate_vtt_grouped_words(self, alignment_data: AlignmentData, words_per_subtitle: int = 3) -> str:
        """
        Generate VTT subtitles with grouped words.
        
        Args:
            alignment_data: The alignment data containing word segments
            words_per_subtitle: Number of words to group per subtitle entry
            
        Returns:
            VTT formatted subtitle content as string
            
        Raises:
            ValueError: If alignment data is invalid
        """
        return self.vtt_exporter.generate_grouped_words(alignment_data, words_per_subtitle)
    
    def generate_vtt_with_cues(self, alignment_data: AlignmentData, include_speaker_labels: bool = False) -> str:
        """
        Generate VTT subtitles with cue identifiers.
        
        Args:
            alignment_data: The alignment data containing segments
            include_speaker_labels: Whether to include speaker identification
            
        Returns:
            VTT formatted subtitle content with cues as string
            
        Raises:
            ValueError: If alignment data is invalid
        """
        return self.vtt_exporter.generate_with_cues(alignment_data, include_speaker_labels)
    
    def export_json_segments_only(self, alignment_data: AlignmentData) -> str:
        """
        Export only segment data to JSON format.
        
        Args:
            alignment_data: The alignment data containing segments
            
        Returns:
            JSON formatted segments as string
            
        Raises:
            ValueError: If alignment data is invalid
        """
        return self.json_exporter.export_segments_only(alignment_data)
    
    def export_json_words_only(self, alignment_data: AlignmentData) -> str:
        """
        Export only word segment data to JSON format.
        
        Args:
            alignment_data: The alignment data containing word segments
            
        Returns:
            JSON formatted word segments as string
            
        Raises:
            ValueError: If alignment data is invalid
        """
        return self.json_exporter.export_words_only(alignment_data)
    
    def export_json_subtitle_format(self, alignment_data: AlignmentData, format_type: str = "segments") -> str:
        """
        Export alignment data in subtitle-friendly JSON format.
        
        Args:
            alignment_data: The alignment data to export
            format_type: Type of export ("segments", "words", or "both")
            
        Returns:
            JSON formatted subtitle data as string
            
        Raises:
            ValueError: If alignment data is invalid
        """
        return self.json_exporter.export_subtitle_format(alignment_data, format_type)
    
    def export_json_for_editing(self, alignment_data: AlignmentData) -> str:
        """
        Export alignment data optimized for manual editing.
        
        Args:
            alignment_data: The alignment data to export
            
        Returns:
            JSON formatted data optimized for editing as string
            
        Raises:
            ValueError: If alignment data is invalid
        """
        return self.json_exporter.export_for_editing(alignment_data)
    
    def generate_bilingual_srt(self, alignment_data: AlignmentData, word_level: bool = False,
                             translated_words: List[str] = None, words_per_subtitle: Optional[int] = None) -> str:
        """
        Generate bilingual SRT format subtitles.
        
        Args:
            alignment_data: The alignment data containing segments and timing
            word_level: If True, generate word-level subtitles; otherwise sentence-level
            translated_words: Optional list of translated words for word-level subtitles
            words_per_subtitle: If specified, group words for word-level subtitles
            
        Returns:
            SRT formatted bilingual subtitle content as string
            
        Raises:
            ValueError: If alignment data is invalid
        """
        if word_level:
            if words_per_subtitle is not None:
                return self.srt_exporter.generate_bilingual_grouped_words(
                    alignment_data, translated_words, words_per_subtitle)
            else:
                return self.srt_exporter.generate_bilingual_word_level(alignment_data, translated_words)
        else:
            return self.srt_exporter.generate_bilingual_sentence_level(alignment_data)
    
    def generate_bilingual_ass_karaoke(self, alignment_data: AlignmentData, 
                                     style_options: Dict[str, Any] = None,
                                     sentence_level: bool = False) -> str:
        """
        Generate bilingual ASS format subtitles with karaoke styling.
        
        Args:
            alignment_data: The alignment data containing segments and timing
            style_options: Optional styling configuration
            sentence_level: If True, generate sentence-level; otherwise word-level karaoke
            
        Returns:
            ASS formatted bilingual subtitle content as string
            
        Raises:
            ValueError: If alignment data is invalid
        """
        if sentence_level:
            return self.ass_exporter.generate_bilingual_sentence_level_karaoke(alignment_data, style_options)
        else:
            return self.ass_exporter.generate_bilingual_karaoke_subtitles(alignment_data, style_options)
    
    def generate_bilingual_vtt(self, alignment_data: AlignmentData, word_level: bool = False,
                             translated_words: List[str] = None, words_per_subtitle: Optional[int] = None,
                             include_cues: bool = False, include_speaker_labels: bool = False) -> str:
        """
        Generate bilingual VTT format subtitles.
        
        Args:
            alignment_data: The alignment data containing segments and timing
            word_level: If True, generate word-level subtitles; otherwise sentence-level
            translated_words: Optional list of translated words for word-level subtitles
            words_per_subtitle: If specified, group words for word-level subtitles
            include_cues: Whether to include cue identifiers
            include_speaker_labels: Whether to include speaker labels
            
        Returns:
            VTT formatted bilingual subtitle content as string
            
        Raises:
            ValueError: If alignment data is invalid
        """
        if word_level:
            if words_per_subtitle is not None:
                return self.vtt_exporter.generate_bilingual_grouped_words(
                    alignment_data, translated_words, words_per_subtitle)
            else:
                return self.vtt_exporter.generate_bilingual_word_level(alignment_data, translated_words)
        else:
            if include_cues:
                return self.vtt_exporter.generate_bilingual_with_cues(alignment_data, include_speaker_labels)
            else:
                return self.vtt_exporter.generate_bilingual_sentence_level(alignment_data)
    
    def export_bilingual_json_alignment(self, alignment_data: AlignmentData, target_language: str,
                                      include_metadata: bool = True, include_statistics: bool = True) -> str:
        """
        Export bilingual alignment data as JSON.
        
        Args:
            alignment_data: The bilingual alignment data to export
            target_language: The target language for translation
            include_metadata: Whether to include metadata information
            include_statistics: Whether to include statistical analysis
            
        Returns:
            JSON formatted bilingual alignment data as string
            
        Raises:
            ValueError: If alignment data is invalid
        """
        return self.json_exporter.export_bilingual_alignment_data(
            alignment_data, target_language, include_metadata, include_statistics)
    
    def generate_bilingual_subtitle_file(self, alignment_data: AlignmentData, output_path: str, 
                                       format_type: ExportFormat, target_language: str,
                                       word_level: bool = False, words_per_subtitle: Optional[int] = None,
                                       translated_words: List[str] = None,
                                       style_options: Dict[str, Any] = None) -> SubtitleFile:
        """
        Generate and save a complete bilingual subtitle file.
        
        Args:
            alignment_data: The bilingual alignment data containing segments and timing
            output_path: Path where to save the subtitle file
            format_type: The subtitle format to generate
            target_language: The target language for translation
            word_level: If True, generate word-level subtitles (SRT/VTT only)
            words_per_subtitle: If specified, group words (SRT/VTT only)
            translated_words: Optional list of translated words for word-level subtitles
            style_options: Optional styling configuration (ASS only)
            
        Returns:
            SubtitleFile object with metadata about the generated file
            
        Raises:
            ValueError: If parameters are invalid
            NotImplementedError: If format is not yet supported
        """
        # Generate bilingual content based on format
        if format_type == ExportFormat.SRT:
            content = self.generate_bilingual_srt(alignment_data, word_level, translated_words, words_per_subtitle)
        elif format_type == ExportFormat.ASS:
            content = self.generate_bilingual_ass_karaoke(alignment_data, style_options, sentence_level=not word_level)
        elif format_type == ExportFormat.VTT:
            content = self.generate_bilingual_vtt(alignment_data, word_level, translated_words, words_per_subtitle)
        elif format_type == ExportFormat.JSON:
            content = self.export_bilingual_json_alignment(alignment_data, target_language)
        else:
            raise ValueError(f"Unsupported format: {format_type}")
        
        # Save the file
        self.save_subtitle_file(content, output_path, format_type)
        
        # Count words in content
        word_count = self._count_words_in_content(content, format_type)
        
        # Get file size
        file_size = os.path.getsize(output_path) if os.path.exists(output_path) else 0
        
        return SubtitleFile(
            path=output_path,
            format=format_type,
            content=content,
            word_count=word_count,
            duration=alignment_data.audio_duration
        )

    def validate_alignment_data(self, alignment_data: AlignmentData) -> list[str]:
        """
        Validate alignment data for subtitle generation.
        
        Args:
            alignment_data: The alignment data to validate
            
        Returns:
            List of validation error messages (empty if valid)
        """
        return alignment_data.validate() if alignment_data else ["Alignment data is None"]