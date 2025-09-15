"""
ASS subtitle format exporter with karaoke styling.

This module provides functionality to export alignment data to ASS (Advanced SubStation Alpha) format,
supporting karaoke-style word highlighting with customizable styling options and color effects.
"""

import re
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from ..models.data_models import AlignmentData, Segment, WordSegment


@dataclass
class ASSStyle:
    """Configuration for ASS subtitle styling."""
    # Font settings
    font_name: str = "Arial"
    font_size: int = 20
    bold: bool = True
    italic: bool = False
    underline: bool = False
    strike_out: bool = False
    
    # Colors (in BGR format for ASS)
    primary_color: str = "&H00FFFFFF"  # White
    secondary_color: str = "&H000000FF"  # Red (for karaoke highlighting)
    outline_color: str = "&H00000000"  # Black
    shadow_color: str = "&H80000000"  # Semi-transparent black
    
    # Positioning and effects
    alignment: int = 2  # Bottom center
    margin_left: int = 10
    margin_right: int = 10
    margin_vertical: int = 10
    outline_width: float = 2.0
    shadow_depth: float = 0.0
    
    # Karaoke-specific settings
    karaoke_fill_color: str = "&H0000FFFF"  # Yellow
    karaoke_border_color: str = "&H00FF0000"  # Blue
    transition_duration: float = 0.1  # Duration of color transition in seconds


class ASSExporter:
    """Handles export of alignment data to ASS subtitle format with karaoke styling."""
    
    def __init__(self):
        """Initialize the ASS exporter."""
        self.default_style = ASSStyle()
    
    def generate_karaoke_subtitles(self, alignment_data: AlignmentData, 
                                 style_options: Optional[Dict[str, Any]] = None) -> str:
        """
        Generate ASS format subtitles with karaoke-style word highlighting.
        
        Args:
            alignment_data: The alignment data containing word segments and timing
            style_options: Optional styling configuration dictionary
            
        Returns:
            ASS formatted subtitle content as string
            
        Raises:
            ValueError: If alignment data is invalid
        """
        if not alignment_data or not alignment_data.word_segments:
            raise ValueError("Alignment data must contain at least one word segment")
        
        # Apply custom styling if provided
        style = self._create_style_from_options(style_options)
        
        # Generate ASS content
        ass_content = []
        
        # Add ASS header
        ass_content.append(self._generate_header())
        
        # Add styles section
        ass_content.append(self._generate_styles_section(style))
        
        # Add events section
        ass_content.append(self._generate_events_section(alignment_data, style))
        
        return "\n".join(ass_content)
    
    def generate_sentence_level_karaoke(self, alignment_data: AlignmentData,
                                      style_options: Optional[Dict[str, Any]] = None) -> str:
        """
        Generate sentence-level ASS subtitles with karaoke effects.
        
        Args:
            alignment_data: The alignment data containing segments
            style_options: Optional styling configuration dictionary
            
        Returns:
            ASS formatted subtitle content as string
            
        Raises:
            ValueError: If alignment data is invalid
        """
        if not alignment_data or not alignment_data.segments:
            raise ValueError("Alignment data must contain at least one segment")
        
        # Apply custom styling if provided
        style = self._create_style_from_options(style_options)
        
        # Generate ASS content
        ass_content = []
        
        # Add ASS header
        ass_content.append(self._generate_header())
        
        # Add styles section
        ass_content.append(self._generate_styles_section(style))
        
        # Add events section for sentences
        ass_content.append(self._generate_sentence_events_section(alignment_data, style))
        
        return "\n".join(ass_content)
    
    def _create_style_from_options(self, style_options: Optional[Dict[str, Any]]) -> ASSStyle:
        """
        Create ASSStyle object from options dictionary.
        
        Args:
            style_options: Dictionary of style options
            
        Returns:
            ASSStyle object with applied options
        """
        style = ASSStyle()
        
        if style_options:
            # Font settings
            if "font_name" in style_options:
                style.font_name = style_options["font_name"]
            if "font_size" in style_options:
                style.font_size = int(style_options["font_size"])
            if "bold" in style_options:
                style.bold = bool(style_options["bold"])
            if "italic" in style_options:
                style.italic = bool(style_options["italic"])
            
            # Colors
            if "primary_color" in style_options:
                style.primary_color = self._format_color(style_options["primary_color"])
            if "secondary_color" in style_options:
                style.secondary_color = self._format_color(style_options["secondary_color"])
            if "karaoke_fill_color" in style_options:
                style.karaoke_fill_color = self._format_color(style_options["karaoke_fill_color"])
            if "karaoke_border_color" in style_options:
                style.karaoke_border_color = self._format_color(style_options["karaoke_border_color"])
            
            # Positioning
            if "alignment" in style_options:
                style.alignment = int(style_options["alignment"])
            if "margin_left" in style_options:
                style.margin_left = int(style_options["margin_left"])
            if "margin_right" in style_options:
                style.margin_right = int(style_options["margin_right"])
            if "margin_vertical" in style_options:
                style.margin_vertical = int(style_options["margin_vertical"])
            
            # Effects
            if "outline_width" in style_options:
                style.outline_width = float(style_options["outline_width"])
            if "shadow_depth" in style_options:
                style.shadow_depth = float(style_options["shadow_depth"])
            if "transition_duration" in style_options:
                style.transition_duration = float(style_options["transition_duration"])
        
        return style
    
    def _format_color(self, color: str) -> str:
        """
        Format color string for ASS format.
        
        Args:
            color: Color in various formats (hex, rgb, etc.)
            
        Returns:
            ASS-formatted color string
        """
        # If already in ASS format, return as-is
        if color.startswith("&H"):
            return color
        
        # Handle hex colors (#RRGGBB or #RGB)
        if color.startswith("#"):
            color = color[1:]
            if len(color) == 3:
                # Expand #RGB to #RRGGBB
                color = "".join([c*2 for c in color])
            
            if len(color) == 6:
                # Convert RGB to BGR for ASS
                r, g, b = color[0:2], color[2:4], color[4:6]
                return f"&H00{b.upper()}{g.upper()}{r.upper()}"
        
        # Default to white if format not recognized
        return "&H00FFFFFF"
    
    def _generate_header(self) -> str:
        """Generate ASS file header."""
        return """[Script Info]
Title: Karaoke Subtitles
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.601
PlayResX: 1920
PlayResY: 1080

[Aegisub Project]
Audio File: 
Video File: 
Video AR Mode: 4
Video AR Value: 1.777778
Video Zoom Percent: 0.500000
Scroll Position: 0
Active Line: 0
Video Position: 0"""
    
    def _generate_styles_section(self, style: ASSStyle) -> str:
        """
        Generate styles section of ASS file.
        
        Args:
            style: ASSStyle configuration
            
        Returns:
            Styles section as string
        """
        # Convert boolean values to integers for ASS format
        bold = -1 if style.bold else 0
        italic = -1 if style.italic else 0
        underline = -1 if style.underline else 0
        strike_out = -1 if style.strike_out else 0
        
        styles_section = f"""
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{style.font_name},{style.font_size},{style.primary_color},{style.secondary_color},{style.outline_color},{style.shadow_color},{bold},{italic},{underline},{strike_out},100,100,0,0,1,{style.outline_width},{style.shadow_depth},{style.alignment},{style.margin_left},{style.margin_right},{style.margin_vertical},1
Style: Karaoke,{style.font_name},{style.font_size},{style.karaoke_fill_color},{style.karaoke_border_color},{style.outline_color},{style.shadow_color},{bold},{italic},{underline},{strike_out},100,100,0,0,1,{style.outline_width},{style.shadow_depth},{style.alignment},{style.margin_left},{style.margin_right},{style.margin_vertical},1"""
        
        return styles_section
    
    def _generate_events_section(self, alignment_data: AlignmentData, style: ASSStyle) -> str:
        """
        Generate events section with karaoke effects for word-level highlighting.
        
        Args:
            alignment_data: The alignment data
            style: ASSStyle configuration
            
        Returns:
            Events section as string
        """
        events = ["\n[Events]"]
        events.append("Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text")
        
        # Group words by segments for better organization
        segments_with_words = self._group_words_by_segments(alignment_data)
        
        for segment_id, (segment, words) in segments_with_words.items():
            if not words:
                continue
            
            # Create karaoke line for this segment
            start_time = self._format_ass_timestamp(segment.start_time)
            end_time = self._format_ass_timestamp(segment.end_time)
            
            # Generate karaoke text with timing
            karaoke_text = self._generate_karaoke_text(words, segment.start_time, style)
            
            # Add dialogue line
            events.append(f"Dialogue: 0,{start_time},{end_time},Karaoke,,0,0,0,,{karaoke_text}")
        
        return "\n".join(events)
    
    def _generate_sentence_events_section(self, alignment_data: AlignmentData, style: ASSStyle) -> str:
        """
        Generate events section for sentence-level karaoke effects.
        
        Args:
            alignment_data: The alignment data
            style: ASSStyle configuration
            
        Returns:
            Events section as string
        """
        events = ["\n[Events]"]
        events.append("Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text")
        
        for i, segment in enumerate(alignment_data.segments):
            start_time = self._format_ass_timestamp(segment.start_time)
            end_time = self._format_ass_timestamp(segment.end_time)
            
            # For sentence-level, create a simple fade-in effect
            text = self._escape_ass_text(segment.text)
            karaoke_text = f"{{\\fad(300,300)}}{text}"
            
            # Add dialogue line
            events.append(f"Dialogue: 0,{start_time},{end_time},Default,,0,0,0,,{karaoke_text}")
        
        return "\n".join(events)
    
    def _group_words_by_segments(self, alignment_data: AlignmentData) -> Dict[int, tuple]:
        """
        Group word segments by their parent segments.
        
        Args:
            alignment_data: The alignment data
            
        Returns:
            Dictionary mapping segment_id to (segment, words) tuple
        """
        # Create mapping of segment_id to segment
        segments_map = {seg.segment_id: seg for seg in alignment_data.segments}
        
        # Group words by segment_id
        words_by_segment = {}
        for word in alignment_data.word_segments:
            segment_id = word.segment_id
            if segment_id not in words_by_segment:
                words_by_segment[segment_id] = []
            words_by_segment[segment_id].append(word)
        
        # Combine segments with their words
        result = {}
        for segment_id, words in words_by_segment.items():
            if segment_id in segments_map:
                # Sort words by start time
                words.sort(key=lambda w: w.start_time)
                result[segment_id] = (segments_map[segment_id], words)
        
        return result
    
    def _generate_karaoke_text(self, words: List[WordSegment], segment_start: float, style: ASSStyle) -> str:
        """
        Generate karaoke text with timing tags for word highlighting.
        
        Args:
            words: List of word segments
            segment_start: Start time of the segment
            style: ASSStyle configuration
            
        Returns:
            Karaoke text with ASS timing tags
        """
        karaoke_parts = []
        
        for i, word in enumerate(words):
            # Calculate timing relative to segment start (in centiseconds)
            word_start_cs = int((word.start_time - segment_start) * 100)
            word_duration_cs = int((word.end_time - word.start_time) * 100)
            
            # Ensure minimum duration for visibility
            if word_duration_cs < 10:  # Minimum 0.1 seconds
                word_duration_cs = 10
            
            # Escape the word text
            escaped_word = self._escape_ass_text(word.word)
            
            # Add karaoke timing tag
            karaoke_parts.append(f"{{\\k{word_duration_cs}}}{escaped_word}")
            
            # Add space between words (except for the last word)
            if i < len(words) - 1:
                karaoke_parts.append(" ")
        
        return "".join(karaoke_parts)
    
    def _format_ass_timestamp(self, seconds: float) -> str:
        """
        Format timestamp in ASS format (H:MM:SS.cc).
        
        Args:
            seconds: Time in seconds
            
        Returns:
            Formatted timestamp string
        """
        # Round to avoid floating point precision issues
        seconds = round(seconds, 2)
        
        # Convert to hours, minutes, seconds, centiseconds
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        centiseconds = int(round((seconds % 1) * 100))
        
        return f"{hours}:{minutes:02d}:{secs:02d}.{centiseconds:02d}"
    
    def _escape_ass_text(self, text: str) -> str:
        """
        Escape text for ASS format.
        
        Args:
            text: Raw text to escape
            
        Returns:
            Escaped text suitable for ASS format
        """
        if not text:
            return ""
        
        # Remove or replace problematic characters
        text = text.strip()
        
        # Handle line breaks first (before whitespace normalization)
        text = text.replace('\r\n', '\n')  # Normalize Windows line endings
        text = text.replace('\r', '\n')    # Normalize Mac line endings
        text = text.replace('\n', '\\N')   # Convert to ASS format
        
        # Replace multiple whitespace with single space (but preserve \N)
        text = re.sub(r'[ \t]+', ' ', text)
        
        # Remove control characters except our converted newlines
        text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
        
        # Escape ASS-specific characters (order matters - backslash first)
        text = text.replace('\\', '\\\\')
        text = text.replace('{', '\\{')
        text = text.replace('}', '\\}')
        
        # Restore the \N sequences that got escaped
        text = text.replace('\\\\N', '\\N')
        
        return text
    
    def validate_ass_content(self, ass_content: str) -> List[str]:
        """
        Validate ASS content format and return list of issues found.
        
        Args:
            ass_content: ASS content to validate
            
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        
        if not ass_content.strip():
            errors.append("ASS content is empty")
            return errors
        
        # Check for required sections
        required_sections = ["[Script Info]", "[V4+ Styles]", "[Events]"]
        for section in required_sections:
            if section not in ass_content:
                errors.append(f"Missing required section: {section}")
        
        # Check for at least one style definition
        if "[V4+ Styles]" in ass_content:
            styles_section = ass_content.split("[V4+ Styles]")[1].split("[Events]")[0] if "[Events]" in ass_content else ass_content.split("[V4+ Styles]")[1]
            if "Style:" not in styles_section:
                errors.append("No style definitions found in [V4+ Styles] section")
        
        # Check for at least one dialogue line
        if "[Events]" in ass_content:
            events_section = ass_content.split("[Events]")[1]
            if "Dialogue:" not in events_section:
                errors.append("No dialogue lines found in [Events] section")
        
        return errors
    
    def generate_bilingual_karaoke_subtitles(self, alignment_data: AlignmentData, 
                                           style_options: Optional[Dict[str, Any]] = None) -> str:
        """
        Generate bilingual ASS format subtitles with karaoke-style word highlighting.
        Expects alignment data where segments contain bilingual text (original + translation).
        
        Args:
            alignment_data: The alignment data containing bilingual word segments and timing
            style_options: Optional styling configuration dictionary
            
        Returns:
            ASS formatted bilingual subtitle content as string
            
        Raises:
            ValueError: If alignment data is invalid
        """
        if not alignment_data or not alignment_data.word_segments:
            raise ValueError("Alignment data must contain at least one word segment")
        
        # Apply custom styling if provided
        style = self._create_style_from_options(style_options)
        
        # Generate ASS content
        ass_content = []
        
        # Add ASS header
        ass_content.append(self._generate_header())
        
        # Add styles section with bilingual styles
        ass_content.append(self._generate_bilingual_styles_section(style))
        
        # Add events section for bilingual karaoke
        ass_content.append(self._generate_bilingual_events_section(alignment_data, style))
        
        return "\n".join(ass_content)
    
    def generate_bilingual_sentence_level_karaoke(self, alignment_data: AlignmentData,
                                                style_options: Optional[Dict[str, Any]] = None) -> str:
        """
        Generate bilingual sentence-level ASS subtitles with karaoke effects.
        
        Args:
            alignment_data: The alignment data containing bilingual segments
            style_options: Optional styling configuration dictionary
            
        Returns:
            ASS formatted bilingual subtitle content as string
            
        Raises:
            ValueError: If alignment data is invalid
        """
        if not alignment_data or not alignment_data.segments:
            raise ValueError("Alignment data must contain at least one segment")
        
        # Apply custom styling if provided
        style = self._create_style_from_options(style_options)
        
        # Generate ASS content
        ass_content = []
        
        # Add ASS header
        ass_content.append(self._generate_header())
        
        # Add styles section with bilingual styles
        ass_content.append(self._generate_bilingual_styles_section(style))
        
        # Add events section for bilingual sentences
        ass_content.append(self._generate_bilingual_sentence_events_section(alignment_data, style))
        
        return "\n".join(ass_content)
    
    def _generate_bilingual_styles_section(self, style: ASSStyle) -> str:
        """
        Generate styles section with bilingual styles.
        
        Args:
            style: ASSStyle configuration
            
        Returns:
            Styles section as string with bilingual styles
        """
        # Convert boolean values to integers for ASS format
        bold = -1 if style.bold else 0
        italic = -1 if style.italic else 0
        underline = -1 if style.underline else 0
        strike_out = -1 if style.strike_out else 0
        
        # Calculate positions for bilingual display
        top_margin = max(10, style.margin_vertical - 30)
        bottom_margin = style.margin_vertical
        
        styles_section = f"""
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{style.font_name},{style.font_size},{style.primary_color},{style.secondary_color},{style.outline_color},{style.shadow_color},{bold},{italic},{underline},{strike_out},100,100,0,0,1,{style.outline_width},{style.shadow_depth},{style.alignment},{style.margin_left},{style.margin_right},{bottom_margin},1
Style: Karaoke,{style.font_name},{style.font_size},{style.karaoke_fill_color},{style.karaoke_border_color},{style.outline_color},{style.shadow_color},{bold},{italic},{underline},{strike_out},100,100,0,0,1,{style.outline_width},{style.shadow_depth},{style.alignment},{style.margin_left},{style.margin_right},{bottom_margin},1
Style: Original,{style.font_name},{max(14, style.font_size - 4)},{style.primary_color},{style.secondary_color},{style.outline_color},{style.shadow_color},{bold},{italic},{underline},{strike_out},100,100,0,0,1,{style.outline_width},{style.shadow_depth},8,{style.margin_left},{style.margin_right},{top_margin},1
Style: Translation,{style.font_name},{style.font_size},{style.karaoke_fill_color},{style.karaoke_border_color},{style.outline_color},{style.shadow_color},{bold},{italic},{underline},{strike_out},100,100,0,0,1,{style.outline_width},{style.shadow_depth},2,{style.margin_left},{style.margin_right},{bottom_margin},1"""
        
        return styles_section
    
    def _generate_bilingual_events_section(self, alignment_data: AlignmentData, style: ASSStyle) -> str:
        """
        Generate events section with bilingual karaoke effects for word-level highlighting.
        
        Args:
            alignment_data: The alignment data
            style: ASSStyle configuration
            
        Returns:
            Events section as string
        """
        events = ["\n[Events]"]
        events.append("Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text")
        
        # Group words by segments for better organization
        segments_with_words = self._group_words_by_segments(alignment_data)
        
        for segment_id, (segment, words) in segments_with_words.items():
            if not words:
                continue
            
            # Parse bilingual text from segment
            text_lines = segment.text.split('\n')
            original_text = text_lines[0] if len(text_lines) > 0 else ""
            translated_text = text_lines[1] if len(text_lines) > 1 else ""
            
            start_time = self._format_ass_timestamp(segment.start_time)
            end_time = self._format_ass_timestamp(segment.end_time)
            
            # Add original text line (top)
            if original_text:
                original_karaoke = self._generate_karaoke_text(words, segment.start_time, style)
                events.append(f"Dialogue: 0,{start_time},{end_time},Original,,0,0,0,,{original_karaoke}")
            
            # Add translated text line (bottom)
            if translated_text:
                escaped_translation = self._escape_ass_text(translated_text)
                translation_effect = f"{{\\fad(300,300)}}{escaped_translation}"
                events.append(f"Dialogue: 0,{start_time},{end_time},Translation,,0,0,0,,{translation_effect}")
        
        return "\n".join(events)
    
    def _generate_bilingual_sentence_events_section(self, alignment_data: AlignmentData, style: ASSStyle) -> str:
        """
        Generate events section for bilingual sentence-level karaoke effects.
        
        Args:
            alignment_data: The alignment data
            style: ASSStyle configuration
            
        Returns:
            Events section as string
        """
        events = ["\n[Events]"]
        events.append("Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text")
        
        for i, segment in enumerate(alignment_data.segments):
            start_time = self._format_ass_timestamp(segment.start_time)
            end_time = self._format_ass_timestamp(segment.end_time)
            
            # Parse bilingual text from segment
            text_lines = segment.text.split('\n')
            original_text = text_lines[0] if len(text_lines) > 0 else ""
            translated_text = text_lines[1] if len(text_lines) > 1 else ""
            
            # Add original text line (top)
            if original_text:
                original_escaped = self._escape_ass_text(original_text)
                original_effect = f"{{\\fad(300,300)}}{original_escaped}"
                events.append(f"Dialogue: 0,{start_time},{end_time},Original,,0,0,0,,{original_effect}")
            
            # Add translated text line (bottom)
            if translated_text:
                translated_escaped = self._escape_ass_text(translated_text)
                translation_effect = f"{{\\fad(300,300)}}{translated_escaped}"
                events.append(f"Dialogue: 0,{start_time},{end_time},Translation,,0,0,0,,{translation_effect}")
        
        return "\n".join(events)

    def get_default_style_options(self) -> Dict[str, Any]:
        """
        Get default style options as dictionary.
        
        Returns:
            Dictionary of default style options
        """
        return {
            "font_name": self.default_style.font_name,
            "font_size": self.default_style.font_size,
            "bold": self.default_style.bold,
            "italic": self.default_style.italic,
            "primary_color": self.default_style.primary_color,
            "secondary_color": self.default_style.secondary_color,
            "karaoke_fill_color": self.default_style.karaoke_fill_color,
            "karaoke_border_color": self.default_style.karaoke_border_color,
            "alignment": self.default_style.alignment,
            "margin_left": self.default_style.margin_left,
            "margin_right": self.default_style.margin_right,
            "margin_vertical": self.default_style.margin_vertical,
            "outline_width": self.default_style.outline_width,
            "shadow_depth": self.default_style.shadow_depth,
            "transition_duration": self.default_style.transition_duration
        }