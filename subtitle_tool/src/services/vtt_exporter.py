"""
VTT subtitle format exporter.

This module provides functionality to export alignment data to VTT (WebVTT) format,
supporting web-compatible subtitle generation with proper timing formatting and text escaping.
"""

import re
from typing import List, Optional
from ..models.data_models import AlignmentData, Segment, WordSegment


class VTTExporter:
    """Handles export of alignment data to VTT (WebVTT) subtitle format."""
    
    def __init__(self):
        """Initialize the VTT exporter."""
        pass
    
    def generate_sentence_level(self, alignment_data: AlignmentData) -> str:
        """
        Generate sentence-level VTT subtitles from alignment data.
        
        Args:
            alignment_data: The alignment data containing segments and timing
            
        Returns:
            VTT formatted subtitle content as string
            
        Raises:
            ValueError: If alignment data is invalid
        """
        if not alignment_data or not alignment_data.segments:
            raise ValueError("Alignment data must contain at least one segment")
        
        vtt_content = ["WEBVTT", ""]  # VTT files must start with "WEBVTT"
        
        for segment in alignment_data.segments:
            # Format timing
            start_time = self._format_timestamp(segment.start_time)
            end_time = self._format_timestamp(segment.end_time)
            
            # Escape and clean text
            text = self._escape_text(segment.text)
            
            # Build VTT entry
            vtt_entry = f"{start_time} --> {end_time}\n{text}"
            vtt_content.append(vtt_entry)
        
        return "\n\n".join(vtt_content)
    
    def generate_word_level(self, alignment_data: AlignmentData) -> str:
        """
        Generate word-level VTT subtitles from alignment data.
        
        Args:
            alignment_data: The alignment data containing word segments and timing
            
        Returns:
            VTT formatted subtitle content as string
            
        Raises:
            ValueError: If alignment data is invalid
        """
        if not alignment_data or not alignment_data.word_segments:
            raise ValueError("Alignment data must contain at least one word segment")
        
        vtt_content = ["WEBVTT", ""]  # VTT files must start with "WEBVTT"
        
        for word_segment in alignment_data.word_segments:
            # Format timing
            start_time = self._format_timestamp(word_segment.start_time)
            end_time = self._format_timestamp(word_segment.end_time)
            
            # Escape and clean text
            text = self._escape_text(word_segment.word)
            
            # Build VTT entry
            vtt_entry = f"{start_time} --> {end_time}\n{text}"
            vtt_content.append(vtt_entry)
        
        return "\n\n".join(vtt_content)
    
    def generate_grouped_words(self, alignment_data: AlignmentData, words_per_subtitle: int = 3) -> str:
        """
        Generate VTT subtitles with multiple words grouped together.
        
        Args:
            alignment_data: The alignment data containing word segments
            words_per_subtitle: Number of words to group per subtitle entry
            
        Returns:
            VTT formatted subtitle content as string
            
        Raises:
            ValueError: If alignment data is invalid or words_per_subtitle < 1
        """
        if not alignment_data or not alignment_data.word_segments:
            raise ValueError("Alignment data must contain at least one word segment")
        
        if words_per_subtitle < 1:
            raise ValueError("words_per_subtitle must be at least 1")
        
        vtt_content = ["WEBVTT", ""]  # VTT files must start with "WEBVTT"
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
            
            # Build VTT entry
            vtt_entry = f"{start_time} --> {end_time}\n{text}"
            vtt_content.append(vtt_entry)
        
        return "\n\n".join(vtt_content)
    
    def generate_with_cues(self, alignment_data: AlignmentData, include_speaker_labels: bool = False) -> str:
        """
        Generate VTT subtitles with cue identifiers and optional speaker labels.
        
        Args:
            alignment_data: The alignment data containing segments and timing
            include_speaker_labels: Whether to include speaker identification
            
        Returns:
            VTT formatted subtitle content with cues as string
            
        Raises:
            ValueError: If alignment data is invalid
        """
        if not alignment_data or not alignment_data.segments:
            raise ValueError("Alignment data must contain at least one segment")
        
        vtt_content = ["WEBVTT", ""]
        
        for i, segment in enumerate(alignment_data.segments, 1):
            # Format timing
            start_time = self._format_timestamp(segment.start_time)
            end_time = self._format_timestamp(segment.end_time)
            
            # Escape and clean text
            text = self._escape_text(segment.text)
            
            # Add speaker label if requested
            if include_speaker_labels:
                text = f"<v Speaker>{text}"
            
            # Build VTT entry with cue identifier
            cue_id = f"cue-{i}"
            vtt_entry = f"{cue_id}\n{start_time} --> {end_time}\n{text}"
            vtt_content.append(vtt_entry)
        
        return "\n\n".join(vtt_content)
    
    def _format_timestamp(self, seconds: float) -> str:
        """
        Format timestamp in VTT format (HH:MM:SS.mmm).
        
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
        
        return f"{hours:02d}:{minutes:02d}:{secs:02d}.{milliseconds:03d}"
    
    def _escape_text(self, text: str) -> str:
        """
        Escape and clean text for VTT format.
        
        Args:
            text: Raw text to escape
            
        Returns:
            Escaped and cleaned text
        """
        if not text:
            return ""
        
        # Remove or replace problematic characters
        text = text.strip()
        
        # Replace multiple whitespace with single space (but preserve newlines)
        text = re.sub(r'[ \t]+', ' ', text)
        
        # Remove control characters except newlines
        text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
        
        # Handle common HTML entities that might appear
        text = text.replace('&amp;', '&')
        text = text.replace('&lt;', '<')
        text = text.replace('&gt;', '>')
        text = text.replace('&quot;', '"')
        text = text.replace('&#39;', "'")
        
        # VTT allows some HTML-like tags, but we need to escape others
        # Escape angle brackets that aren't part of allowed tags
        allowed_tags = ['<c>', '</c>', '<i>', '</i>', '<b>', '</b>', '<u>', '</u>', '<v>', '</v>']
        
        # Simple approach: only allow basic formatting tags
        # For now, we'll escape all angle brackets to be safe
        text = text.replace('<', '&lt;')
        text = text.replace('>', '&gt;')
        
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
    
    def validate_vtt_content(self, vtt_content: str) -> List[str]:
        """
        Validate VTT content format and return list of issues found.
        
        Args:
            vtt_content: VTT content to validate
            
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        
        if not vtt_content.strip():
            errors.append("VTT content is empty")
            return errors
        
        lines = vtt_content.strip().split('\n')
        
        # Check for WEBVTT header
        if not lines[0].strip().startswith('WEBVTT'):
            errors.append("VTT file must start with 'WEBVTT'")
        
        # Split into cue blocks (separated by empty lines)
        blocks = vtt_content.strip().split('\n\n')
        
        # Skip the header block and filter out empty blocks
        cue_blocks = [block for block in blocks[1:] if block.strip()] if len(blocks) > 1 else []
        
        for i, block in enumerate(cue_blocks, 1):
            block_lines = block.strip().split('\n')
            
            if len(block_lines) < 2:
                errors.append(f"Cue {i}: Insufficient lines (expected at least 2)")
                continue
            
            # Check if first line is a cue identifier or timing line
            timing_line_index = 0
            if ' --> ' not in block_lines[0]:
                # First line is cue identifier, timing is on second line
                timing_line_index = 1
                if len(block_lines) < 3:
                    errors.append(f"Cue {i}: Insufficient lines with cue identifier (expected at least 3)")
                    continue
            
            # Check timing format
            if timing_line_index < len(block_lines):
                timing_line = block_lines[timing_line_index]
                if ' --> ' not in timing_line:
                    errors.append(f"Cue {i}: Invalid timing format (missing ' --> ')")
                else:
                    start_time, end_time = timing_line.split(' --> ', 1)
                    if not self._validate_timestamp(start_time.strip()):
                        errors.append(f"Cue {i}: Invalid start timestamp '{start_time.strip()}'")
                    if not self._validate_timestamp(end_time.strip()):
                        errors.append(f"Cue {i}: Invalid end timestamp '{end_time.strip()}'")
            
            # Check text content
            text_lines = block_lines[timing_line_index + 1:]
            if not any(line.strip() for line in text_lines):
                errors.append(f"Cue {i}: Empty text content")
        
        return errors
    
    def _validate_timestamp(self, timestamp: str) -> bool:
        """
        Validate VTT timestamp format.
        
        Args:
            timestamp: Timestamp string to validate
            
        Returns:
            True if valid, False otherwise
        """
        # VTT format: HH:MM:SS.mmm or MM:SS.mmm
        pattern = r'^(\d{2}:)?\d{2}:\d{2}\.\d{3}$'
        if not re.match(pattern, timestamp):
            return False
        
        # Additional validation for time ranges
        parts = timestamp.split(':')
        if len(parts) == 3:  # HH:MM:SS.mmm format
            hours = int(parts[0])
            minutes = int(parts[1])
            seconds_parts = parts[2].split('.')
            seconds = int(seconds_parts[0])
            
            # Validate ranges
            if hours > 23 or minutes > 59 or seconds > 59:
                return False
        elif len(parts) == 2:  # MM:SS.mmm format
            minutes = int(parts[0])
            seconds_parts = parts[1].split('.')
            seconds = int(seconds_parts[0])
            
            # Validate ranges
            if minutes > 59 or seconds > 59:
                return False
        
        return True
    
    def generate_bilingual_sentence_level(self, alignment_data: AlignmentData) -> str:
        """
        Generate bilingual sentence-level VTT subtitles from alignment data.
        Expects alignment data where segments contain bilingual text (original + translation).
        
        Args:
            alignment_data: The alignment data containing bilingual segments and timing
            
        Returns:
            VTT formatted bilingual subtitle content as string
            
        Raises:
            ValueError: If alignment data is invalid
        """
        if not alignment_data or not alignment_data.segments:
            raise ValueError("Alignment data must contain at least one segment")
        
        vtt_content = ["WEBVTT", ""]  # VTT files must start with "WEBVTT"
        
        for segment in alignment_data.segments:
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
            
            # Build VTT entry
            vtt_entry = f"{start_time} --> {end_time}\n{formatted_text}"
            vtt_content.append(vtt_entry)
        
        return "\n\n".join(vtt_content)
    
    def generate_bilingual_word_level(self, alignment_data: AlignmentData, 
                                    translated_words: List[str] = None) -> str:
        """
        Generate bilingual word-level VTT subtitles from alignment data.
        
        Args:
            alignment_data: The alignment data containing word segments and timing
            translated_words: Optional list of translated words corresponding to word_segments
            
        Returns:
            VTT formatted bilingual subtitle content as string
            
        Raises:
            ValueError: If alignment data is invalid
        """
        if not alignment_data or not alignment_data.word_segments:
            raise ValueError("Alignment data must contain at least one word segment")
        
        vtt_content = ["WEBVTT", ""]  # VTT files must start with "WEBVTT"
        
        for i, word_segment in enumerate(alignment_data.word_segments):
            # Format timing
            start_time = self._format_timestamp(word_segment.start_time)
            end_time = self._format_timestamp(word_segment.end_time)
            
            # Create bilingual text
            original_word = self._escape_text(word_segment.word)
            if translated_words and i < len(translated_words):
                translated_word = self._escape_text(translated_words[i])
                bilingual_text = f"{original_word}\n{translated_word}"
            else:
                bilingual_text = original_word
            
            # Build VTT entry
            vtt_entry = f"{start_time} --> {end_time}\n{bilingual_text}"
            vtt_content.append(vtt_entry)
        
        return "\n\n".join(vtt_content)
    
    def generate_bilingual_grouped_words(self, alignment_data: AlignmentData, 
                                       translated_words: List[str] = None,
                                       words_per_subtitle: int = 3) -> str:
        """
        Generate bilingual VTT subtitles with multiple words grouped together.
        
        Args:
            alignment_data: The alignment data containing word segments
            translated_words: Optional list of translated words corresponding to word_segments
            words_per_subtitle: Number of words to group per subtitle entry
            
        Returns:
            VTT formatted bilingual subtitle content as string
            
        Raises:
            ValueError: If alignment data is invalid or words_per_subtitle < 1
        """
        if not alignment_data or not alignment_data.word_segments:
            raise ValueError("Alignment data must contain at least one word segment")
        
        if words_per_subtitle < 1:
            raise ValueError("words_per_subtitle must be at least 1")
        
        vtt_content = ["WEBVTT", ""]  # VTT files must start with "WEBVTT"
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
            
            # Build VTT entry
            vtt_entry = f"{start_time} --> {end_time}\n{bilingual_text}"
            vtt_content.append(vtt_entry)
        
        return "\n\n".join(vtt_content)
    
    def generate_bilingual_with_cues(self, alignment_data: AlignmentData, 
                                   include_speaker_labels: bool = False) -> str:
        """
        Generate bilingual VTT subtitles with cue identifiers and optional speaker labels.
        
        Args:
            alignment_data: The alignment data containing bilingual segments and timing
            include_speaker_labels: Whether to include speaker identification
            
        Returns:
            VTT formatted bilingual subtitle content with cues as string
            
        Raises:
            ValueError: If alignment data is invalid
        """
        if not alignment_data or not alignment_data.segments:
            raise ValueError("Alignment data must contain at least one segment")
        
        vtt_content = ["WEBVTT", ""]
        
        for i, segment in enumerate(alignment_data.segments, 1):
            # Format timing
            start_time = self._format_timestamp(segment.start_time)
            end_time = self._format_timestamp(segment.end_time)
            
            # Handle bilingual text - split by newline if present
            text_lines = segment.text.split('\n')
            if len(text_lines) > 1:
                # Format as bilingual with original on top, translation below
                original_text = self._escape_text(text_lines[0])
                translated_text = self._escape_text(text_lines[1])
                
                # Add speaker labels if requested
                if include_speaker_labels:
                    original_text = f"<v Original>{original_text}"
                    translated_text = f"<v Translation>{translated_text}"
                
                formatted_text = f"{original_text}\n{translated_text}"
            else:
                # Single line text
                formatted_text = self._escape_text(segment.text)
                if include_speaker_labels:
                    formatted_text = f"<v Speaker>{formatted_text}"
            
            # Build VTT entry with cue identifier
            cue_id = f"cue-{i}"
            vtt_entry = f"{cue_id}\n{start_time} --> {end_time}\n{formatted_text}"
            vtt_content.append(vtt_entry)
        
        return "\n\n".join(vtt_content)

    def add_styling_cues(self, alignment_data: AlignmentData, style_classes: dict = None) -> str:
        """
        Generate VTT subtitles with CSS styling cues.
        
        Args:
            alignment_data: The alignment data containing segments and timing
            style_classes: Dictionary mapping confidence levels to CSS classes
            
        Returns:
            VTT formatted subtitle content with styling as string
            
        Raises:
            ValueError: If alignment data is invalid
        """
        if not alignment_data or not alignment_data.segments:
            raise ValueError("Alignment data must contain at least one segment")
        
        # Default style classes based on confidence
        if style_classes is None:
            style_classes = {
                'high': 'high-confidence',    # confidence >= 0.8
                'medium': 'medium-confidence', # 0.5 <= confidence < 0.8
                'low': 'low-confidence'       # confidence < 0.5
            }
        
        vtt_content = ["WEBVTT", ""]
        
        for i, segment in enumerate(alignment_data.segments, 1):
            # Format timing
            start_time = self._format_timestamp(segment.start_time)
            end_time = self._format_timestamp(segment.end_time)
            
            # Determine style class based on confidence
            if segment.confidence >= 0.8:
                css_class = style_classes.get('high', 'high-confidence')
            elif segment.confidence >= 0.5:
                css_class = style_classes.get('medium', 'medium-confidence')
            else:
                css_class = style_classes.get('low', 'low-confidence')
            
            # Escape and clean text with styling
            text = self._escape_text(segment.text)
            styled_text = f"<c.{css_class}>{text}</c>"
            
            # Build VTT entry
            cue_id = f"cue-{i}"
            vtt_entry = f"{cue_id}\n{start_time} --> {end_time}\n{styled_text}"
            vtt_content.append(vtt_entry)
        
        return "\n\n".join(vtt_content)