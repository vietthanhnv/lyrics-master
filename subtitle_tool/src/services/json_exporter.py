"""
JSON alignment data exporter.

This module provides functionality to export alignment data to JSON format,
supporting detailed alignment data export with proper encoding handling and validation.
"""

import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from ..models.data_models import AlignmentData, Segment, WordSegment


class JSONExporter:
    """Handles export of alignment data to JSON format."""
    
    def __init__(self):
        """Initialize the JSON exporter."""
        pass
    
    def export_alignment_data(self, alignment_data: AlignmentData, 
                            include_metadata: bool = True,
                            include_statistics: bool = True) -> str:
        """
        Export complete alignment data to JSON format.
        
        Args:
            alignment_data: The alignment data to export
            include_metadata: Whether to include metadata information
            include_statistics: Whether to include statistical analysis
            
        Returns:
            JSON formatted alignment data as string
            
        Raises:
            ValueError: If alignment data is invalid
        """
        if not alignment_data:
            raise ValueError("Alignment data cannot be None")
        
        # Build the JSON structure
        json_data = {}
        
        # Add metadata if requested
        if include_metadata:
            json_data["metadata"] = self._generate_metadata(alignment_data)
        
        # Add segments
        json_data["segments"] = [self._segment_to_dict(segment) for segment in alignment_data.segments]
        
        # Add word segments
        json_data["word_segments"] = [self._word_segment_to_dict(word_segment) for word_segment in alignment_data.word_segments]
        
        # Add confidence scores
        json_data["confidence_scores"] = alignment_data.confidence_scores
        
        # Add audio information
        json_data["audio"] = {
            "duration": alignment_data.audio_duration,
            "source_file": alignment_data.source_file
        }
        
        # Add statistics if requested
        if include_statistics:
            json_data["statistics"] = self._generate_statistics(alignment_data)
        
        return json.dumps(json_data, indent=2, ensure_ascii=False)
    
    def export_segments_only(self, alignment_data: AlignmentData) -> str:
        """
        Export only segment data to JSON format.
        
        Args:
            alignment_data: The alignment data containing segments
            
        Returns:
            JSON formatted segments as string
            
        Raises:
            ValueError: If alignment data is invalid
        """
        if not alignment_data or not alignment_data.segments:
            raise ValueError("Alignment data must contain at least one segment")
        
        segments_data = {
            "segments": [self._segment_to_dict(segment) for segment in alignment_data.segments],
            "total_segments": len(alignment_data.segments),
            "audio_duration": alignment_data.audio_duration
        }
        
        return json.dumps(segments_data, indent=2, ensure_ascii=False)
    
    def export_words_only(self, alignment_data: AlignmentData) -> str:
        """
        Export only word segment data to JSON format.
        
        Args:
            alignment_data: The alignment data containing word segments
            
        Returns:
            JSON formatted word segments as string
            
        Raises:
            ValueError: If alignment data is invalid
        """
        if not alignment_data or not alignment_data.word_segments:
            raise ValueError("Alignment data must contain at least one word segment")
        
        words_data = {
            "word_segments": [self._word_segment_to_dict(word_segment) for word_segment in alignment_data.word_segments],
            "total_words": len(alignment_data.word_segments),
            "audio_duration": alignment_data.audio_duration
        }
        
        return json.dumps(words_data, indent=2, ensure_ascii=False)
    
    def export_subtitle_format(self, alignment_data: AlignmentData, format_type: str = "segments") -> str:
        """
        Export alignment data in a subtitle-friendly JSON format.
        
        Args:
            alignment_data: The alignment data to export
            format_type: Type of export ("segments", "words", or "both")
            
        Returns:
            JSON formatted subtitle data as string
            
        Raises:
            ValueError: If alignment data is invalid or format_type is unsupported
        """
        if not alignment_data:
            raise ValueError("Alignment data cannot be None")
        
        if format_type not in ["segments", "words", "both"]:
            raise ValueError("format_type must be 'segments', 'words', or 'both'")
        
        subtitle_data = {
            "format": "subtitle_json",
            "version": "1.0",
            "audio_duration": alignment_data.audio_duration,
            "source_file": alignment_data.source_file
        }
        
        if format_type in ["segments", "both"]:
            subtitle_data["subtitles"] = []
            for i, segment in enumerate(alignment_data.segments, 1):
                subtitle_entry = {
                    "id": i,
                    "start": round(segment.start_time, 3),
                    "end": round(segment.end_time, 3),
                    "duration": round(segment.end_time - segment.start_time, 3),
                    "text": segment.text,
                    "confidence": round(segment.confidence, 3)
                }
                subtitle_data["subtitles"].append(subtitle_entry)
        
        if format_type in ["words", "both"]:
            subtitle_data["words"] = []
            for i, word_segment in enumerate(alignment_data.word_segments, 1):
                word_entry = {
                    "id": i,
                    "word": word_segment.word,
                    "start": round(word_segment.start_time, 3),
                    "end": round(word_segment.end_time, 3),
                    "duration": round(word_segment.end_time - word_segment.start_time, 3),
                    "confidence": round(word_segment.confidence, 3),
                    "segment_id": word_segment.segment_id
                }
                subtitle_data["words"].append(word_entry)
        
        return json.dumps(subtitle_data, indent=2, ensure_ascii=False)
    
    def export_for_editing(self, alignment_data: AlignmentData) -> str:
        """
        Export alignment data in a format optimized for manual editing.
        
        Args:
            alignment_data: The alignment data to export
            
        Returns:
            JSON formatted data optimized for editing as string
            
        Raises:
            ValueError: If alignment data is invalid
        """
        if not alignment_data:
            raise ValueError("Alignment data cannot be None")
        
        editing_data = {
            "project": {
                "name": f"Subtitle Project - {alignment_data.source_file}",
                "created": datetime.now().isoformat(),
                "audio_file": alignment_data.source_file,
                "duration": alignment_data.audio_duration
            },
            "segments": [],
            "settings": {
                "default_confidence_threshold": 0.5,
                "min_segment_duration": 0.1,
                "max_segment_duration": 10.0,
                "word_level_editing": True
            }
        }
        
        # Group words by segments for easier editing
        segments_with_words = self._group_words_by_segments(alignment_data)
        
        for segment_id, (segment, words) in segments_with_words.items():
            segment_entry = {
                "id": segment_id,
                "start_time": round(segment.start_time, 3),
                "end_time": round(segment.end_time, 3),
                "text": segment.text,
                "confidence": round(segment.confidence, 3),
                "editable": True,
                "words": []
            }
            
            for word in words:
                word_entry = {
                    "word": word.word,
                    "start_time": round(word.start_time, 3),
                    "end_time": round(word.end_time, 3),
                    "confidence": round(word.confidence, 3),
                    "editable": True
                }
                segment_entry["words"].append(word_entry)
            
            editing_data["segments"].append(segment_entry)
        
        return json.dumps(editing_data, indent=2, ensure_ascii=False)
    
    def _segment_to_dict(self, segment: Segment) -> Dict[str, Any]:
        """
        Convert a Segment object to dictionary.
        
        Args:
            segment: The segment to convert
            
        Returns:
            Dictionary representation of the segment
        """
        return {
            "start_time": round(segment.start_time, 3),
            "end_time": round(segment.end_time, 3),
            "duration": round(segment.end_time - segment.start_time, 3),
            "text": segment.text,
            "confidence": round(segment.confidence, 3),
            "segment_id": segment.segment_id
        }
    
    def _word_segment_to_dict(self, word_segment: WordSegment) -> Dict[str, Any]:
        """
        Convert a WordSegment object to dictionary.
        
        Args:
            word_segment: The word segment to convert
            
        Returns:
            Dictionary representation of the word segment
        """
        return {
            "word": word_segment.word,
            "start_time": round(word_segment.start_time, 3),
            "end_time": round(word_segment.end_time, 3),
            "duration": round(word_segment.end_time - word_segment.start_time, 3),
            "confidence": round(word_segment.confidence, 3),
            "segment_id": word_segment.segment_id
        }
    
    def _generate_metadata(self, alignment_data: AlignmentData) -> Dict[str, Any]:
        """
        Generate metadata for the alignment data.
        
        Args:
            alignment_data: The alignment data
            
        Returns:
            Dictionary containing metadata
        """
        return {
            "export_timestamp": datetime.now().isoformat(),
            "format_version": "1.0",
            "exporter": "lyric-to-subtitle-app",
            "total_segments": len(alignment_data.segments),
            "total_words": len(alignment_data.word_segments),
            "audio_duration": alignment_data.audio_duration,
            "source_file": alignment_data.source_file,
            "average_confidence": round(alignment_data.get_average_confidence(), 3)
        }
    
    def _generate_statistics(self, alignment_data: AlignmentData) -> Dict[str, Any]:
        """
        Generate statistical analysis of the alignment data.
        
        Args:
            alignment_data: The alignment data
            
        Returns:
            Dictionary containing statistics
        """
        if not alignment_data.segments or not alignment_data.word_segments:
            return {}
        
        # Segment statistics
        segment_durations = [seg.end_time - seg.start_time for seg in alignment_data.segments]
        segment_confidences = [seg.confidence for seg in alignment_data.segments]
        
        # Word statistics
        word_durations = [word.end_time - word.start_time for word in alignment_data.word_segments]
        word_confidences = [word.confidence for word in alignment_data.word_segments]
        
        # Calculate statistics
        stats = {
            "segments": {
                "count": len(alignment_data.segments),
                "average_duration": round(sum(segment_durations) / len(segment_durations), 3),
                "min_duration": round(min(segment_durations), 3),
                "max_duration": round(max(segment_durations), 3),
                "average_confidence": round(sum(segment_confidences) / len(segment_confidences), 3),
                "min_confidence": round(min(segment_confidences), 3),
                "max_confidence": round(max(segment_confidences), 3)
            },
            "words": {
                "count": len(alignment_data.word_segments),
                "average_duration": round(sum(word_durations) / len(word_durations), 3),
                "min_duration": round(min(word_durations), 3),
                "max_duration": round(max(word_durations), 3),
                "average_confidence": round(sum(word_confidences) / len(word_confidences), 3),
                "min_confidence": round(min(word_confidences), 3),
                "max_confidence": round(max(word_confidences), 3)
            },
            "quality": {
                "high_confidence_segments": len([s for s in alignment_data.segments if s.confidence >= 0.8]),
                "medium_confidence_segments": len([s for s in alignment_data.segments if 0.5 <= s.confidence < 0.8]),
                "low_confidence_segments": len([s for s in alignment_data.segments if s.confidence < 0.5]),
                "high_confidence_words": len([w for w in alignment_data.word_segments if w.confidence >= 0.8]),
                "medium_confidence_words": len([w for w in alignment_data.word_segments if 0.5 <= w.confidence < 0.8]),
                "low_confidence_words": len([w for w in alignment_data.word_segments if w.confidence < 0.5])
            }
        }
        
        return stats
    
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
    
    def validate_json_content(self, json_content: str) -> List[str]:
        """
        Validate JSON content format and return list of issues found.
        
        Args:
            json_content: JSON content to validate
            
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        
        if not json_content.strip():
            errors.append("JSON content is empty")
            return errors
        
        try:
            data = json.loads(json_content)
        except json.JSONDecodeError as e:
            errors.append(f"Invalid JSON format: {str(e)}")
            return errors
        
        # Validate structure based on expected format
        if isinstance(data, dict):
            # Check for required fields in alignment data format
            if "segments" in data or "word_segments" in data:
                if "segments" in data and not isinstance(data["segments"], list):
                    errors.append("'segments' field must be a list")
                
                if "word_segments" in data and not isinstance(data["word_segments"], list):
                    errors.append("'word_segments' field must be a list")
                
                # Validate segment structure
                if "segments" in data:
                    for i, segment in enumerate(data["segments"]):
                        if not isinstance(segment, dict):
                            errors.append(f"Segment {i}: must be an object")
                            continue
                        
                        # For bilingual segments, check for either 'text' or bilingual fields
                        has_text = "text" in segment or "bilingual_text" in segment
                        has_bilingual = "original_text" in segment and "translated_text" in segment
                        
                        if not has_text and not has_bilingual:
                            errors.append(f"Segment {i}: missing text field (must have 'text', 'bilingual_text', or both 'original_text' and 'translated_text')")
                        
                        # Check timing fields
                        required_timing_fields = ["start_time", "end_time"]
                        for field in required_timing_fields:
                            if field not in segment:
                                errors.append(f"Segment {i}: missing required field '{field}'")
                
                # Validate word segment structure
                if "word_segments" in data:
                    for i, word_segment in enumerate(data["word_segments"]):
                        if not isinstance(word_segment, dict):
                            errors.append(f"Word segment {i}: must be an object")
                            continue
                        
                        required_fields = ["word", "start_time", "end_time"]
                        for field in required_fields:
                            if field not in word_segment:
                                errors.append(f"Word segment {i}: missing required field '{field}'")
        else:
            errors.append("JSON root must be an object")
        
        return errors
    
    def export_bilingual_alignment_data(self, alignment_data: AlignmentData, 
                                      target_language: str,
                                      include_metadata: bool = True,
                                      include_statistics: bool = True) -> str:
        """
        Export bilingual alignment data to JSON format.
        Expects alignment data where segments contain bilingual text (original + translation).
        
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
        if not alignment_data:
            raise ValueError("Alignment data cannot be None")
        
        # Build the JSON structure
        json_data = {}
        
        # Add metadata if requested
        if include_metadata:
            metadata = self._generate_metadata(alignment_data)
            metadata["bilingual"] = True
            metadata["target_language"] = target_language
            json_data["metadata"] = metadata
        
        # Add bilingual segments
        json_data["segments"] = [self._bilingual_segment_to_dict(segment) for segment in alignment_data.segments]
        
        # Add word segments (original language)
        json_data["word_segments"] = [self._word_segment_to_dict(word_segment) for word_segment in alignment_data.word_segments]
        
        # Add confidence scores
        json_data["confidence_scores"] = alignment_data.confidence_scores
        
        # Add audio information
        json_data["audio"] = {
            "duration": alignment_data.audio_duration,
            "source_file": alignment_data.source_file
        }
        
        # Add translation information
        json_data["translation"] = {
            "target_language": target_language,
            "bilingual_format": True
        }
        
        # Add statistics if requested
        if include_statistics:
            json_data["statistics"] = self._generate_statistics(alignment_data)
        
        return json.dumps(json_data, indent=2, ensure_ascii=False)
    
    def export_bilingual_subtitle_format(self, alignment_data: AlignmentData, 
                                       target_language: str,
                                       format_type: str = "segments") -> str:
        """
        Export bilingual alignment data in a subtitle-friendly JSON format.
        
        Args:
            alignment_data: The bilingual alignment data to export
            target_language: The target language for translation
            format_type: Type of export ("segments", "words", or "both")
            
        Returns:
            JSON formatted bilingual subtitle data as string
            
        Raises:
            ValueError: If alignment data is invalid or format_type is unsupported
        """
        if not alignment_data:
            raise ValueError("Alignment data cannot be None")
        
        if format_type not in ["segments", "words", "both"]:
            raise ValueError("format_type must be 'segments', 'words', or 'both'")
        
        subtitle_data = {
            "format": "bilingual_subtitle_json",
            "version": "1.0",
            "audio_duration": alignment_data.audio_duration,
            "source_file": alignment_data.source_file,
            "target_language": target_language,
            "bilingual": True
        }
        
        if format_type in ["segments", "both"]:
            subtitle_data["subtitles"] = []
            for i, segment in enumerate(alignment_data.segments, 1):
                # Parse bilingual text
                text_lines = segment.text.split('\n')
                original_text = text_lines[0] if len(text_lines) > 0 else segment.text
                translated_text = text_lines[1] if len(text_lines) > 1 else ""
                
                subtitle_entry = {
                    "id": i,
                    "start": round(segment.start_time, 3),
                    "end": round(segment.end_time, 3),
                    "duration": round(segment.end_time - segment.start_time, 3),
                    "original_text": original_text,
                    "translated_text": translated_text,
                    "confidence": round(segment.confidence, 3)
                }
                subtitle_data["subtitles"].append(subtitle_entry)
        
        if format_type in ["words", "both"]:
            subtitle_data["words"] = []
            for i, word_segment in enumerate(alignment_data.word_segments, 1):
                word_entry = {
                    "id": i,
                    "word": word_segment.word,
                    "start": round(word_segment.start_time, 3),
                    "end": round(word_segment.end_time, 3),
                    "duration": round(word_segment.end_time - word_segment.start_time, 3),
                    "confidence": round(word_segment.confidence, 3),
                    "segment_id": word_segment.segment_id
                }
                subtitle_data["words"].append(word_entry)
        
        return json.dumps(subtitle_data, indent=2, ensure_ascii=False)
    
    def export_bilingual_for_editing(self, alignment_data: AlignmentData, target_language: str) -> str:
        """
        Export bilingual alignment data in a format optimized for manual editing.
        
        Args:
            alignment_data: The bilingual alignment data to export
            target_language: The target language for translation
            
        Returns:
            JSON formatted bilingual data optimized for editing as string
            
        Raises:
            ValueError: If alignment data is invalid
        """
        if not alignment_data:
            raise ValueError("Alignment data cannot be None")
        
        editing_data = {
            "project": {
                "name": f"Bilingual Subtitle Project - {alignment_data.source_file}",
                "created": datetime.now().isoformat(),
                "audio_file": alignment_data.source_file,
                "duration": alignment_data.audio_duration,
                "target_language": target_language,
                "bilingual": True
            },
            "segments": [],
            "settings": {
                "default_confidence_threshold": 0.5,
                "min_segment_duration": 0.1,
                "max_segment_duration": 10.0,
                "word_level_editing": True,
                "bilingual_editing": True
            }
        }
        
        # Group words by segments for easier editing
        segments_with_words = self._group_words_by_segments(alignment_data)
        
        for segment_id, (segment, words) in segments_with_words.items():
            # Parse bilingual text
            text_lines = segment.text.split('\n')
            original_text = text_lines[0] if len(text_lines) > 0 else segment.text
            translated_text = text_lines[1] if len(text_lines) > 1 else ""
            
            segment_entry = {
                "id": segment_id,
                "start_time": round(segment.start_time, 3),
                "end_time": round(segment.end_time, 3),
                "original_text": original_text,
                "translated_text": translated_text,
                "confidence": round(segment.confidence, 3),
                "editable": True,
                "words": []
            }
            
            for word in words:
                word_entry = {
                    "word": word.word,
                    "start_time": round(word.start_time, 3),
                    "end_time": round(word.end_time, 3),
                    "confidence": round(word.confidence, 3),
                    "editable": True
                }
                segment_entry["words"].append(word_entry)
            
            editing_data["segments"].append(segment_entry)
        
        return json.dumps(editing_data, indent=2, ensure_ascii=False)
    
    def _bilingual_segment_to_dict(self, segment: Segment) -> Dict[str, Any]:
        """
        Convert a bilingual Segment object to dictionary.
        
        Args:
            segment: The bilingual segment to convert
            
        Returns:
            Dictionary representation of the bilingual segment
        """
        # Parse bilingual text
        text_lines = segment.text.split('\n')
        original_text = text_lines[0] if len(text_lines) > 0 else segment.text
        translated_text = text_lines[1] if len(text_lines) > 1 else ""
        
        return {
            "start_time": round(segment.start_time, 3),
            "end_time": round(segment.end_time, 3),
            "duration": round(segment.end_time - segment.start_time, 3),
            "original_text": original_text,
            "translated_text": translated_text,
            "bilingual_text": segment.text,
            "confidence": round(segment.confidence, 3),
            "segment_id": segment.segment_id
        }

    def parse_json_to_alignment_data(self, json_content: str) -> AlignmentData:
        """
        Parse JSON content back to AlignmentData object.
        
        Args:
            json_content: JSON content to parse
            
        Returns:
            AlignmentData object parsed from JSON
            
        Raises:
            ValueError: If JSON content is invalid or cannot be parsed
        """
        validation_errors = self.validate_json_content(json_content)
        if validation_errors:
            raise ValueError(f"Invalid JSON content: {'; '.join(validation_errors)}")
        
        try:
            data = json.loads(json_content)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse JSON: {str(e)}")
        
        # Extract segments
        segments = []
        if "segments" in data:
            for seg_data in data["segments"]:
                segment = Segment(
                    start_time=float(seg_data["start_time"]),
                    end_time=float(seg_data["end_time"]),
                    text=seg_data["text"],
                    confidence=float(seg_data.get("confidence", 1.0)),
                    segment_id=int(seg_data.get("segment_id", 0))
                )
                segments.append(segment)
        
        # Extract word segments
        word_segments = []
        if "word_segments" in data:
            for word_data in data["word_segments"]:
                word_segment = WordSegment(
                    word=word_data["word"],
                    start_time=float(word_data["start_time"]),
                    end_time=float(word_data["end_time"]),
                    confidence=float(word_data.get("confidence", 1.0)),
                    segment_id=int(word_data.get("segment_id", 0))
                )
                word_segments.append(word_segment)
        
        # Extract other data
        confidence_scores = data.get("confidence_scores", [])
        audio_duration = float(data.get("audio", {}).get("duration", 0.0))
        source_file = data.get("audio", {}).get("source_file", "")
        
        return AlignmentData(
            segments=segments,
            word_segments=word_segments,
            confidence_scores=confidence_scores,
            audio_duration=audio_duration,
            source_file=source_file
        )