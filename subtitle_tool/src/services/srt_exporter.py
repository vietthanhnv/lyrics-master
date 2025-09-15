"""
SRT subtitle format exporter.

This module provides functionality to export alignment data to SRT (SubRip Subtitle) format,
supporting both sentence-level and word-level subtitle generation with proper timing
formatting and text escaping.
"""

import re
from typing import List, Optional
from ..models.data_models import AlignmentData, Segment, WordSegment, ExportFormat


class SRTExporter:
    """Handles export of alignment data to SRT subtitle format."""
    
    def __init__(self):
        """Initialize the SRT exporter."""
        pass
    
    def generate_sentence_level(self, alignment_data: AlignmentData) -> str:
        """
        Generate sentence-level SRT subtitles from alignment data.
        
        Args:
            alignment_data: The alignment data containing segments and timing
            
        Returns:
            SRT formatted subtitle content as string
            
        Raises:
            ValueError: If alignment data is invalid
        """
        if not alignment_data or not alignment_data.segments:
            raise ValueError("Alignment data must contain at least one segment")
        
        srt_content = []
        
        for i, segment in enumerate(alignment_data.segments, 1):
            # Format timing
            start_time = self._format_timestamp(segment.start_time)
            end_time = self._format_timestamp(segment.end_time)
            
            # Escape and clean text
            text = self._escape_text(segment.text)
            
            # Build SRT entry
            srt_entry = f"{i}\n{start_time} --> {end_time}\n{text}\n"
            srt_content.append(srt_entry)
        
        return "\n".join(srt_content)
    
    def generate_word_level(self, alignment_data: AlignmentData) -> str:
        """
        Generate word-level SRT subtitles from alignment data.
        
        Args:
            alignment_data: The alignment data containing word segments and timing
            
        Returns:
            SRT formatted subtitle content as string
            
        Raises:
            ValueError: If alignment data is invalid
        """
        if not alignment_data or not alignment_data.word_segments:
            raise ValueError("Alignment data must contain at least one word segment")
        
        srt_content = []
        
        for i, word_segment in enumerate(alignment_data.word_segments, 1):
            # Format timing
            start_time = self._format_timestamp(word_segment.start_time)
            end_time = self._format_timestamp(word_segment.end_time)
            
            # Escape and clean text
            text = self._escape_text(word_segment.word)
            
            # Build SRT entry
            srt_entry = f"{i}\n{start_time} --> {end_time}\n{text}\n"
            srt_content.append(srt_entry)
        
        return "\n".join(srt_content)
    
    def generate_grouped_words(self, alignment_data: AlignmentData, words_per_subtitle: int = 3) -> str:
        """
        Generate SRT subtitles with multiple words grouped together.
        
        Args:
            alignment_data: The alignment data containing word segments
            words_per_subtitle: Number of words to group per subtitle entry
            
        Returns:
            SRT formatted subtitle content as string
            
        Raises:
            ValueError: If alignment data is invalid or words_per_subtitle < 1
        """
        if not alignment_data or not alignment_data.word_segments:
            raise ValueError("Alignment data must contain at least one word segment")
        
        if words_per_subtitle < 1:
            raise ValueError("words_per_subtitle must be at least 1")
        
        srt_content = []
        word_segments = alignment_data.word_segments
        
        for i in range(0, len(word_segments), words_per_subtitle):
            # Get group of words
            word_group = word_segments[i:i + words_per_subtitle]
            
            # Calculate timing from first to last word in group
            start_time = self._format_timestamp(word_group[0].start_time)
            end_time = self._format_timestamp(word_group[-1].end_time)
            
            # Combine words into text
            words = [self._escape_text(ws.word) for ws in word_group]
            text = " ".join(words)
            
            # Build SRT entry
            subtitle_number = (i // words_per_subtitle) + 1
            srt_entry = f"{subtitle_number}\n{start_time} --> {end_time}\n{text}\n"
            srt_content.append(srt_entry)
        
        return "\n".join(srt_content)
    
    def _format_timestamp(self, seconds: float) -> str:
        """
        Format timestamp in SRT format (HH:MM:SS,mmm).
        
        Args:
            seconds: Time in seconds
            
        Returns:
            Formatted timestamp string
        """
        # Round to avoid floating point precision issues
        seconds = round(seconds, 3)
        
        # Convert to hours, minutes, seconds, milliseconds
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        milliseconds = int(round((seconds % 1) * 1000))
        
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"
    
    def _escape_text(self, text: str) -> str:
        """
        Escape and clean text for SRT format.
        
        Args:
            text: Raw text to escape
            
        Returns:
            Escaped and cleaned text
        """
        if not text:
            return ""
        
        # Remove or replace problematic characters
        text = text.strip()
        
        # Replace multiple whitespace with single space
        text = re.sub(r'\s+', ' ', text)
        
        # Remove control characters except newlines
        text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
        
        # Handle common HTML entities that might appear
        text = text.replace('&amp;', '&')
        text = text.replace('&lt;', '<')
        text = text.replace('&gt;', '>')
        text = text.replace('&quot;', '"')
        text = text.replace('&#39;', "'")
        
        # Ensure text doesn't exceed reasonable line length
        # Split long lines at word boundaries
        if len(text) > 80:
            words = text.split()
            lines = []
            current_line = []
            current_length = 0
            
            for word in words:
                if current_length + len(word) + 1 > 80 and current_line:
                    lines.append(' '.join(current_line))
                    current_line = [word]
                    current_length = len(word)
                else:
                    current_line.append(word)
                    current_length += len(word) + (1 if current_line else 0)
            
            if current_line:
                lines.append(' '.join(current_line))
            
            text = '\n'.join(lines)
        
        return text
    
    def validate_srt_content(self, srt_content: str) -> List[str]:
        """
        Validate SRT content format and return list of issues found.
        
        Args:
            srt_content: SRT content to validate
            
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        
        if not srt_content.strip():
            errors.append("SRT content is empty")
            return errors
        
        # Split into subtitle blocks
        blocks = srt_content.strip().split('\n\n')
        
        for i, block in enumerate(blocks, 1):
            lines = block.strip().split('\n')
            
            if len(lines) < 3:
                errors.append(f"Block {i}: Insufficient lines (expected at least 3)")
                continue
            
            # Check subtitle number
            try:
                subtitle_num = int(lines[0])
                if subtitle_num != i:
                    errors.append(f"Block {i}: Subtitle number mismatch (expected {i}, got {subtitle_num})")
            except ValueError:
                errors.append(f"Block {i}: Invalid subtitle number '{lines[0]}'")
            
            # Check timing format
            timing_line = lines[1]
            if ' --> ' not in timing_line:
                errors.append(f"Block {i}: Invalid timing format (missing ' --> ')")
            else:
                start_time, end_time = timing_line.split(' --> ', 1)
                if not self._validate_timestamp(start_time):
                    errors.append(f"Block {i}: Invalid start timestamp '{start_time}'")
                if not self._validate_timestamp(end_time):
                    errors.append(f"Block {i}: Invalid end timestamp '{end_time}'")
            
            # Check text content
            text_lines = lines[2:]
            if not any(line.strip() for line in text_lines):
                errors.append(f"Block {i}: Empty text content")
        
        return errors
    
    def generate_bilingual_sentence_level(self, alignment_data: AlignmentData) -> str:
        """
        Generate bilingual sentence-level SRT subtitles from alignment data.
        Expects alignment data where segments contain bilingual text (original + translation).
        
        Args:
            alignment_data: The alignment data containing bilingual segments
            
        Returns:
            SRT formatted bilingual subtitle content as string
            
        Raises:
            ValueError: If alignment data is invalid
        """
        if not alignment_data or not alignment_data.segments:
            raise ValueError("Alignment data must contain at least one segment")
        
        srt_content = []
        
        for i, segment in enumerate(alignment_data.segments, 1):
            # Format timing
            start_time = self._format_timestamp(segment.start_time)
            end_time = self._format_timestamp(segment.end_time)
            
            # Handle bilingual text - split by newline if present
            text_lines = segment.text.split('\n')
            if len(text_lines) > 1:
                # Format as bilingual with original on top, translation below
                formatted_text = '\n'.join(self._escape_text(line) for line in text_lines)
            else:
                # Single line text
                formatted_text = self._escape_text(segment.text)
            
            # Build SRT entry
            srt_entry = f"{i}\n{start_time} --> {end_time}\n{formatted_text}\n"
            srt_content.append(srt_entry)
        
        return "\n".join(srt_content)
    
    def generate_bilingual_word_level(self, alignment_data: AlignmentData, 
                                    translated_words: List[str] = None) -> str:
        """
        Generate bilingual word-level SRT subtitles from alignment data.
        
        Args:
            alignment_data: The alignment data containing word segments
            translated_words: Optional list of translated words corresponding to word_segments
            
        Returns:
            SRT formatted bilingual subtitle content as string
            
        Raises:
            ValueError: If alignment data is invalid
        """
        if not alignment_data or not alignment_data.word_segments:
            raise ValueError("Alignment data must contain at least one word segment")
        
        srt_content = []
        
        for i, word_segment in enumerate(alignment_data.word_segments, 1):
            # Format timing
            start_time = self._format_timestamp(word_segment.start_time)
            end_time = self._format_timestamp(word_segment.end_time)
            
            # Create bilingual text
            original_word = self._escape_text(word_segment.word)
            if translated_words and i <= len(translated_words):
                translated_word = self._escape_text(translated_words[i-1])
                bilingual_text = f"{original_word}\n{translated_word}"
            else:
                bilingual_text = original_word
            
            # Build SRT entry
            srt_entry = f"{i}\n{start_time} --> {end_time}\n{bilingual_text}\n"
            srt_content.append(srt_entry)
        
        return "\n".join(srt_content)
    
    def generate_bilingual_grouped_words(self, alignment_data: AlignmentData, 
                                       translated_words: List[str] = None,
                                       words_per_subtitle: int = 3) -> str:
        """
        Generate bilingual SRT subtitles with multiple words grouped together.
        
        Args:
            alignment_data: The alignment data containing word segments
            translated_words: Optional list of translated words corresponding to word_segments
            words_per_subtitle: Number of words to group per subtitle entry
            
        Returns:
            SRT formatted bilingual subtitle content as string
            
        Raises:
            ValueError: If alignment data is invalid or words_per_subtitle < 1
        """
        if not alignment_data or not alignment_data.word_segments:
            raise ValueError("Alignment data must contain at least one word segment")
        
        if words_per_subtitle < 1:
            raise ValueError("words_per_subtitle must be at least 1")
        
        srt_content = []
        word_segments = alignment_data.word_segments
        
        for i in range(0, len(word_segments), words_per_subtitle):
            # Get group of words
            word_group = word_segments[i:i + words_per_subtitle]
            
            # Calculate timing from first to last word in group
            start_time = self._format_timestamp(word_group[0].start_time)
            end_time = self._format_timestamp(word_group[-1].end_time)
            
            # Combine original words
            original_words = [self._escape_text(ws.word) for ws in word_group]
            original_text = " ".join(original_words)
            
            # Combine translated words if available
            if translated_words:
                start_idx = i
                end_idx = min(i + words_per_subtitle, len(translated_words))
                translated_group = translated_words[start_idx:end_idx]
                translated_text = " ".join(self._escape_text(word) for word in translated_group)
                bilingual_text = f"{original_text}\n{translated_text}"
            else:
                bilingual_text = original_text
            
            # Build SRT entry
            subtitle_number = (i // words_per_subtitle) + 1
            srt_entry = f"{subtitle_number}\n{start_time} --> {end_time}\n{bilingual_text}\n"
            srt_content.append(srt_entry)
        
        return "\n".join(srt_content)

    def _validate_timestamp(self, timestamp: str) -> bool:
        """
        Validate SRT timestamp format.
        
        Args:
            timestamp: Timestamp string to validate
            
        Returns:
            True if valid, False otherwise
        """
        # SRT format: HH:MM:SS,mmm
        pattern = r'^\d{2}:\d{2}:\d{2},\d{3}$'
        return bool(re.match(pattern, timestamp))