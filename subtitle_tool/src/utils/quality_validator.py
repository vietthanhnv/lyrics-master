"""
Quality validation utilities for subtitle generation.

This module provides comprehensive quality validation for subtitle content,
timing accuracy, and format compliance.
"""

import re
import json
import logging
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from enum import Enum

from ..models.data_models import AlignmentData, Segment, WordSegment


logger = logging.getLogger(__name__)


class ValidationSeverity(Enum):
    """Severity levels for validation issues."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class ValidationIssue:
    """Represents a validation issue."""
    
    severity: ValidationSeverity
    category: str
    message: str
    location: Optional[str] = None
    suggestion: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class ValidationResult:
    """Result of a validation operation."""
    
    is_valid: bool
    issues: List[ValidationIssue]
    score: float  # Quality score from 0.0 to 1.0
    metadata: Dict[str, Any]
    
    def get_issues_by_severity(self, severity: ValidationSeverity) -> List[ValidationIssue]:
        """Get issues filtered by severity."""
        return [issue for issue in self.issues if issue.severity == severity]
    
    def has_critical_issues(self) -> bool:
        """Check if there are any critical issues."""
        return any(issue.severity == ValidationSeverity.CRITICAL for issue in self.issues)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of validation results."""
        severity_counts = {}
        for severity in ValidationSeverity:
            severity_counts[severity.value] = len(self.get_issues_by_severity(severity))
        
        return {
            'is_valid': self.is_valid,
            'score': self.score,
            'total_issues': len(self.issues),
            'severity_counts': severity_counts,
            'has_critical_issues': self.has_critical_issues()
        }


class TimingValidator:
    """Validator for subtitle timing accuracy."""
    
    def __init__(self, tolerance: float = 0.1):
        """
        Initialize timing validator.
        
        Args:
            tolerance: Acceptable timing tolerance in seconds
        """
        self.tolerance = tolerance
    
    def validate_alignment_timing(self, alignment_data: AlignmentData) -> ValidationResult:
        """
        Validate timing accuracy of alignment data.
        
        Args:
            alignment_data: The alignment data to validate
            
        Returns:
            ValidationResult with timing validation results
        """
        issues = []
        metadata = {}
        
        # Validate segment timing
        segment_issues = self._validate_segment_timing(alignment_data.segments)
        issues.extend(segment_issues)
        
        # Validate word timing
        word_issues = self._validate_word_timing(alignment_data.word_segments)
        issues.extend(word_issues)
        
        # Validate timing consistency between segments and words
        consistency_issues = self._validate_timing_consistency(
            alignment_data.segments, alignment_data.word_segments
        )
        issues.extend(consistency_issues)
        
        # Calculate timing statistics
        timing_stats = self._calculate_timing_statistics(alignment_data)
        metadata.update(timing_stats)
        
        # Calculate quality score
        score = self._calculate_timing_score(issues, len(alignment_data.segments))
        
        # Determine if valid (no critical or error issues)
        is_valid = not any(
            issue.severity in [ValidationSeverity.CRITICAL, ValidationSeverity.ERROR] 
            for issue in issues
        )
        
        return ValidationResult(
            is_valid=is_valid,
            issues=issues,
            score=score,
            metadata=metadata
        )
    
    def _validate_segment_timing(self, segments: List[Segment]) -> List[ValidationIssue]:
        """Validate timing of segments."""
        issues = []
        
        for i, segment in enumerate(segments):
            # Check for invalid timing
            if segment.end_time <= segment.start_time:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.CRITICAL,
                    category="timing",
                    message=f"Segment {i} has invalid timing: end ({segment.end_time:.3f}s) <= start ({segment.start_time:.3f}s)",
                    location=f"segment_{i}",
                    suggestion="Check transcription alignment process"
                ))
            
            # Check for very short segments
            duration = segment.end_time - segment.start_time
            if duration < 0.1:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    category="timing",
                    message=f"Segment {i} is very short: {duration:.3f}s",
                    location=f"segment_{i}",
                    suggestion="Consider merging with adjacent segments"
                ))
            
            # Check for very long segments
            if duration > 10.0:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    category="timing",
                    message=f"Segment {i} is very long: {duration:.3f}s",
                    location=f"segment_{i}",
                    suggestion="Consider splitting into smaller segments"
                ))
        
        # Check for overlapping segments
        for i in range(len(segments) - 1):
            current = segments[i]
            next_seg = segments[i + 1]
            
            if current.end_time > next_seg.start_time + self.tolerance:
                overlap = current.end_time - next_seg.start_time
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    category="timing",
                    message=f"Segments {i} and {i+1} overlap by {overlap:.3f}s",
                    location=f"segments_{i}_{i+1}",
                    suggestion="Adjust segment boundaries to eliminate overlap"
                ))
        
        # Check for large gaps between segments
        for i in range(len(segments) - 1):
            current = segments[i]
            next_seg = segments[i + 1]
            
            gap = next_seg.start_time - current.end_time
            if gap > 2.0:  # Gap larger than 2 seconds
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.INFO,
                    category="timing",
                    message=f"Large gap ({gap:.3f}s) between segments {i} and {i+1}",
                    location=f"gap_{i}_{i+1}",
                    suggestion="Check if content is missing in the gap"
                ))
        
        return issues
    
    def _validate_word_timing(self, word_segments: List[WordSegment]) -> List[ValidationIssue]:
        """Validate timing of word segments."""
        issues = []
        
        for i, word in enumerate(word_segments):
            # Check for invalid word timing
            if word.end_time <= word.start_time:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.CRITICAL,
                    category="timing",
                    message=f"Word '{word.word}' has invalid timing: end ({word.end_time:.3f}s) <= start ({word.start_time:.3f}s)",
                    location=f"word_{i}",
                    suggestion="Check word-level alignment process"
                ))
            
            # Check for very short words (might indicate alignment issues)
            duration = word.end_time - word.start_time
            if duration < 0.05 and len(word.word.strip()) > 2:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    category="timing",
                    message=f"Word '{word.word}' is very short: {duration:.3f}s",
                    location=f"word_{i}",
                    suggestion="Check word alignment accuracy"
                ))
            
            # Check for very long words
            if duration > 3.0:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    category="timing",
                    message=f"Word '{word.word}' is very long: {duration:.3f}s",
                    location=f"word_{i}",
                    suggestion="Check if word contains multiple words or silence"
                ))
        
        return issues
    
    def _validate_timing_consistency(self, segments: List[Segment], 
                                   word_segments: List[WordSegment]) -> List[ValidationIssue]:
        """Validate consistency between segment and word timing."""
        issues = []
        
        # Group words by segment
        words_by_segment = {}
        for word in word_segments:
            if word.segment_id not in words_by_segment:
                words_by_segment[word.segment_id] = []
            words_by_segment[word.segment_id].append(word)
        
        # Check each segment
        for segment in segments:
            segment_words = words_by_segment.get(segment.segment_id, [])
            
            if not segment_words:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    category="consistency",
                    message=f"Segment {segment.segment_id} has no associated words",
                    location=f"segment_{segment.segment_id}",
                    suggestion="Check word-level alignment for this segment"
                ))
                continue
            
            # Check if word timing is within segment bounds
            for word in segment_words:
                if word.start_time < segment.start_time - self.tolerance:
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        category="consistency",
                        message=f"Word '{word.word}' starts before its segment",
                        location=f"word_{word.word}_segment_{segment.segment_id}",
                        suggestion="Adjust word or segment timing"
                    ))
                
                if word.end_time > segment.end_time + self.tolerance:
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        category="consistency",
                        message=f"Word '{word.word}' ends after its segment",
                        location=f"word_{word.word}_segment_{segment.segment_id}",
                        suggestion="Adjust word or segment timing"
                    ))
        
        return issues
    
    def _calculate_timing_statistics(self, alignment_data: AlignmentData) -> Dict[str, Any]:
        """Calculate timing statistics."""
        stats = {}
        
        if alignment_data.segments:
            segment_durations = [seg.end_time - seg.start_time for seg in alignment_data.segments]
            stats.update({
                'segment_count': len(alignment_data.segments),
                'avg_segment_duration': sum(segment_durations) / len(segment_durations),
                'min_segment_duration': min(segment_durations),
                'max_segment_duration': max(segment_durations),
                'total_speech_duration': sum(segment_durations)
            })
        
        if alignment_data.word_segments:
            word_durations = [word.end_time - word.start_time for word in alignment_data.word_segments]
            stats.update({
                'word_count': len(alignment_data.word_segments),
                'avg_word_duration': sum(word_durations) / len(word_durations),
                'min_word_duration': min(word_durations),
                'max_word_duration': max(word_durations)
            })
        
        stats['audio_duration'] = alignment_data.audio_duration
        stats['speech_ratio'] = stats.get('total_speech_duration', 0) / alignment_data.audio_duration
        
        return stats
    
    def _calculate_timing_score(self, issues: List[ValidationIssue], segment_count: int) -> float:
        """Calculate timing quality score."""
        if segment_count == 0:
            return 0.0
        
        # Start with perfect score
        score = 1.0
        
        # Deduct points based on issue severity
        for issue in issues:
            if issue.severity == ValidationSeverity.CRITICAL:
                score -= 0.2
            elif issue.severity == ValidationSeverity.ERROR:
                score -= 0.1
            elif issue.severity == ValidationSeverity.WARNING:
                score -= 0.05
            elif issue.severity == ValidationSeverity.INFO:
                score -= 0.01
        
        return max(0.0, score)


class TextQualityValidator:
    """Validator for text quality in transcriptions."""
    
    def validate_text_quality(self, alignment_data: AlignmentData) -> ValidationResult:
        """
        Validate text quality of transcription.
        
        Args:
            alignment_data: The alignment data to validate
            
        Returns:
            ValidationResult with text quality validation results
        """
        issues = []
        metadata = {}
        
        # Validate segment text
        text_issues = self._validate_segment_text(alignment_data.segments)
        issues.extend(text_issues)
        
        # Validate confidence scores
        confidence_issues = self._validate_confidence_scores(alignment_data)
        issues.extend(confidence_issues)
        
        # Calculate text statistics
        text_stats = self._calculate_text_statistics(alignment_data)
        metadata.update(text_stats)
        
        # Calculate quality score
        score = self._calculate_text_score(alignment_data, issues)
        
        # Determine if valid
        is_valid = not any(
            issue.severity in [ValidationSeverity.CRITICAL, ValidationSeverity.ERROR] 
            for issue in issues
        )
        
        return ValidationResult(
            is_valid=is_valid,
            issues=issues,
            score=score,
            metadata=metadata
        )
    
    def _validate_segment_text(self, segments: List[Segment]) -> List[ValidationIssue]:
        """Validate text content of segments."""
        issues = []
        
        for i, segment in enumerate(segments):
            text = segment.text.strip()
            
            # Check for empty segments
            if not text:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    category="text_quality",
                    message=f"Segment {i} is empty",
                    location=f"segment_{i}",
                    suggestion="Check if segment should be removed or contains silence"
                ))
                continue
            
            # Check for very short text
            if len(text) < 3:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    category="text_quality",
                    message=f"Segment {i} has very short text: '{text}'",
                    location=f"segment_{i}",
                    suggestion="Consider merging with adjacent segments"
                ))
            
            # Check for repeated characters (might indicate transcription errors)
            if re.search(r'(.)\1{4,}', text):  # 5 or more repeated characters
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    category="text_quality",
                    message=f"Segment {i} contains repeated characters: '{text}'",
                    location=f"segment_{i}",
                    suggestion="Check transcription accuracy"
                ))
            
            # Check for unusual characters or encoding issues
            if re.search(r'[^\w\s\.,!?;:\'"()-]', text):
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.INFO,
                    category="text_quality",
                    message=f"Segment {i} contains unusual characters: '{text}'",
                    location=f"segment_{i}",
                    suggestion="Verify character encoding and transcription accuracy"
                ))
            
            # Check for all caps (might indicate shouting or transcription issue)
            if text.isupper() and len(text) > 10:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.INFO,
                    category="text_quality",
                    message=f"Segment {i} is all uppercase: '{text}'",
                    location=f"segment_{i}",
                    suggestion="Check if capitalization is intentional"
                ))
        
        return issues
    
    def _validate_confidence_scores(self, alignment_data: AlignmentData) -> List[ValidationIssue]:
        """Validate confidence scores."""
        issues = []
        
        # Check segment confidence scores
        low_confidence_segments = []
        for i, segment in enumerate(alignment_data.segments):
            if segment.confidence < 0.5:
                low_confidence_segments.append((i, segment.confidence))
        
        if low_confidence_segments:
            if len(low_confidence_segments) > len(alignment_data.segments) * 0.3:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    category="confidence",
                    message=f"Many segments have low confidence: {len(low_confidence_segments)}/{len(alignment_data.segments)}",
                    suggestion="Consider using a different model or improving audio quality"
                ))
            else:
                for seg_id, confidence in low_confidence_segments:
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.INFO,
                        category="confidence",
                        message=f"Segment {seg_id} has low confidence: {confidence:.3f}",
                        location=f"segment_{seg_id}",
                        suggestion="Review transcription accuracy for this segment"
                    ))
        
        # Check word confidence scores
        if alignment_data.word_segments:
            low_confidence_words = [
                word for word in alignment_data.word_segments 
                if word.confidence < 0.4
            ]
            
            if len(low_confidence_words) > len(alignment_data.word_segments) * 0.2:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    category="confidence",
                    message=f"Many words have low confidence: {len(low_confidence_words)}/{len(alignment_data.word_segments)}",
                    suggestion="Consider improving audio quality or using a larger model"
                ))
        
        return issues
    
    def _calculate_text_statistics(self, alignment_data: AlignmentData) -> Dict[str, Any]:
        """Calculate text quality statistics."""
        stats = {}
        
        if alignment_data.segments:
            total_chars = sum(len(seg.text.strip()) for seg in alignment_data.segments)
            empty_segments = sum(1 for seg in alignment_data.segments if not seg.text.strip())
            short_segments = sum(1 for seg in alignment_data.segments if 0 < len(seg.text.strip()) < 3)
            
            confidence_scores = [seg.confidence for seg in alignment_data.segments]
            
            stats.update({
                'total_segments': len(alignment_data.segments),
                'total_characters': total_chars,
                'empty_segments': empty_segments,
                'short_segments': short_segments,
                'avg_segment_length': total_chars / len(alignment_data.segments),
                'avg_confidence': sum(confidence_scores) / len(confidence_scores),
                'min_confidence': min(confidence_scores),
                'max_confidence': max(confidence_scores)
            })
        
        if alignment_data.word_segments:
            word_confidence_scores = [word.confidence for word in alignment_data.word_segments]
            stats.update({
                'total_words': len(alignment_data.word_segments),
                'avg_word_confidence': sum(word_confidence_scores) / len(word_confidence_scores),
                'min_word_confidence': min(word_confidence_scores),
                'max_word_confidence': max(word_confidence_scores)
            })
        
        return stats
    
    def _calculate_text_score(self, alignment_data: AlignmentData, issues: List[ValidationIssue]) -> float:
        """Calculate text quality score."""
        if not alignment_data.segments:
            return 0.0
        
        # Base score from confidence
        avg_confidence = sum(seg.confidence for seg in alignment_data.segments) / len(alignment_data.segments)
        score = avg_confidence
        
        # Adjust based on text quality issues
        empty_segments = sum(1 for seg in alignment_data.segments if not seg.text.strip())
        short_segments = sum(1 for seg in alignment_data.segments if 0 < len(seg.text.strip()) < 3)
        
        # Penalize empty and short segments
        quality_penalty = (empty_segments + short_segments) / len(alignment_data.segments)
        score *= (1.0 - quality_penalty)
        
        # Deduct points for issues
        for issue in issues:
            if issue.severity == ValidationSeverity.CRITICAL:
                score -= 0.2
            elif issue.severity == ValidationSeverity.ERROR:
                score -= 0.1
            elif issue.severity == ValidationSeverity.WARNING:
                score -= 0.05
        
        return max(0.0, min(1.0, score))


class SubtitleFormatValidator:
    """Validator for subtitle format compliance."""
    
    def validate_srt_format(self, content: str) -> ValidationResult:
        """Validate SRT format compliance."""
        issues = []
        metadata = {}
        
        lines = content.strip().split('\n')
        subtitle_count = 0
        
        i = 0
        while i < len(lines):
            # Skip empty lines
            if not lines[i].strip():
                i += 1
                continue
            
            # Check subtitle number
            try:
                subtitle_num = int(lines[i].strip())
                if subtitle_num != subtitle_count + 1:
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        category="format",
                        message=f"Subtitle number {subtitle_num} is not sequential (expected {subtitle_count + 1})",
                        location=f"line_{i+1}"
                    ))
                subtitle_count += 1
            except (ValueError, IndexError):
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    category="format",
                    message=f"Invalid subtitle number at line {i + 1}: '{lines[i]}'",
                    location=f"line_{i+1}"
                ))
                i += 1
                continue
            
            # Check timing line
            i += 1
            if i >= len(lines):
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.CRITICAL,
                    category="format",
                    message=f"Missing timing line for subtitle {subtitle_num}",
                    location=f"subtitle_{subtitle_num}"
                ))
                break
            
            timing_line = lines[i].strip()
            if not self._validate_srt_timing(timing_line):
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    category="format",
                    message=f"Invalid timing format at line {i + 1}: '{timing_line}'",
                    location=f"line_{i+1}",
                    suggestion="Use format: HH:MM:SS,mmm --> HH:MM:SS,mmm"
                ))
            
            # Skip text lines until next subtitle or end
            i += 1
            text_lines = 0
            while i < len(lines) and lines[i].strip() and not lines[i].strip().isdigit():
                text_lines += 1
                i += 1
            
            if text_lines == 0:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    category="format",
                    message=f"Subtitle {subtitle_num} has no text content",
                    location=f"subtitle_{subtitle_num}"
                ))
        
        metadata['subtitle_count'] = subtitle_count
        
        score = max(0.0, 1.0 - (len([i for i in issues if i.severity in [ValidationSeverity.ERROR, ValidationSeverity.CRITICAL]]) / max(1, subtitle_count)))
        is_valid = not any(issue.severity == ValidationSeverity.CRITICAL for issue in issues)
        
        return ValidationResult(
            is_valid=is_valid,
            issues=issues,
            score=score,
            metadata=metadata
        )
    
    def validate_vtt_format(self, content: str) -> ValidationResult:
        """Validate WebVTT format compliance."""
        issues = []
        metadata = {}
        
        lines = content.strip().split('\n')
        
        # Check WEBVTT header
        if not lines or not lines[0].strip().startswith('WEBVTT'):
            issues.append(ValidationIssue(
                severity=ValidationSeverity.CRITICAL,
                category="format",
                message="Missing WEBVTT header",
                location="line_1",
                suggestion="File must start with 'WEBVTT'"
            ))
        
        # Count cues and validate timing
        cue_count = 0
        for i, line in enumerate(lines):
            if ' --> ' in line:
                cue_count += 1
                if not self._validate_vtt_timing(line.strip()):
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        category="format",
                        message=f"Invalid VTT timing format at line {i + 1}: '{line.strip()}'",
                        location=f"line_{i+1}",
                        suggestion="Use format: HH:MM:SS.mmm --> HH:MM:SS.mmm"
                    ))
        
        metadata['cue_count'] = cue_count
        
        score = max(0.0, 1.0 - (len([i for i in issues if i.severity in [ValidationSeverity.ERROR, ValidationSeverity.CRITICAL]]) / max(1, cue_count)))
        is_valid = not any(issue.severity == ValidationSeverity.CRITICAL for issue in issues)
        
        return ValidationResult(
            is_valid=is_valid,
            issues=issues,
            score=score,
            metadata=metadata
        )
    
    def validate_json_format(self, content: str) -> ValidationResult:
        """Validate JSON format compliance."""
        issues = []
        metadata = {}
        
        try:
            data = json.loads(content)
            
            # Check required top-level fields
            required_fields = ['segments', 'words', 'metadata']
            for field in required_fields:
                if field not in data:
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        category="format",
                        message=f"Missing required field: {field}",
                        suggestion=f"Add '{field}' field to JSON structure"
                    ))
            
            # Validate segments structure
            if 'segments' in data:
                if not isinstance(data['segments'], list):
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        category="format",
                        message="'segments' field must be a list"
                    ))
                else:
                    for i, segment in enumerate(data['segments']):
                        if not isinstance(segment, dict):
                            issues.append(ValidationIssue(
                                severity=ValidationSeverity.ERROR,
                                category="format",
                                message=f"Segment {i} must be a dictionary"
                            ))
                            continue
                        
                        required_seg_fields = ['start', 'end', 'text']
                        for field in required_seg_fields:
                            if field not in segment:
                                issues.append(ValidationIssue(
                                    severity=ValidationSeverity.ERROR,
                                    category="format",
                                    message=f"Segment {i} missing required field: {field}"
                                ))
                
                metadata['segment_count'] = len(data['segments'])
            
            # Validate words structure
            if 'words' in data and isinstance(data['words'], list):
                metadata['word_count'] = len(data['words'])
            
        except json.JSONDecodeError as e:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.CRITICAL,
                category="format",
                message=f"Invalid JSON: {e}",
                suggestion="Fix JSON syntax errors"
            ))
        
        score = 1.0 if not issues else max(0.0, 1.0 - len(issues) * 0.2)
        is_valid = not any(issue.severity == ValidationSeverity.CRITICAL for issue in issues)
        
        return ValidationResult(
            is_valid=is_valid,
            issues=issues,
            score=score,
            metadata=metadata
        )
    
    def _validate_srt_timing(self, timing_line: str) -> bool:
        """Validate SRT timing format."""
        pattern = r'^\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3}$'
        return bool(re.match(pattern, timing_line))
    
    def _validate_vtt_timing(self, timing_line: str) -> bool:
        """Validate VTT timing format."""
        pattern = r'^\d{2}:\d{2}:\d{2}\.\d{3} --> \d{2}:\d{2}:\d{2}\.\d{3}$'
        return bool(re.match(pattern, timing_line))


class QualityValidator:
    """Main quality validator that combines all validation types."""
    
    def __init__(self, timing_tolerance: float = 0.1):
        """
        Initialize quality validator.
        
        Args:
            timing_tolerance: Acceptable timing tolerance in seconds
        """
        self.timing_validator = TimingValidator(timing_tolerance)
        self.text_validator = TextQualityValidator()
        self.format_validator = SubtitleFormatValidator()
    
    def validate_alignment_data(self, alignment_data: AlignmentData) -> ValidationResult:
        """
        Perform comprehensive validation of alignment data.
        
        Args:
            alignment_data: The alignment data to validate
            
        Returns:
            Combined validation result
        """
        all_issues = []
        all_metadata = {}
        
        # Timing validation
        timing_result = self.timing_validator.validate_alignment_timing(alignment_data)
        all_issues.extend(timing_result.issues)
        all_metadata['timing'] = timing_result.metadata
        
        # Text quality validation
        text_result = self.text_validator.validate_text_quality(alignment_data)
        all_issues.extend(text_result.issues)
        all_metadata['text_quality'] = text_result.metadata
        
        # Calculate combined score
        combined_score = (timing_result.score + text_result.score) / 2
        
        # Determine overall validity
        is_valid = timing_result.is_valid and text_result.is_valid
        
        return ValidationResult(
            is_valid=is_valid,
            issues=all_issues,
            score=combined_score,
            metadata=all_metadata
        )
    
    def validate_subtitle_format(self, content: str, format_type: str) -> ValidationResult:
        """
        Validate subtitle format compliance.
        
        Args:
            content: The subtitle content to validate
            format_type: Type of subtitle format ('srt', 'vtt', 'json')
            
        Returns:
            Format validation result
        """
        if format_type.lower() == 'srt':
            return self.format_validator.validate_srt_format(content)
        elif format_type.lower() == 'vtt':
            return self.format_validator.validate_vtt_format(content)
        elif format_type.lower() == 'json':
            return self.format_validator.validate_json_format(content)
        else:
            return ValidationResult(
                is_valid=False,
                issues=[ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    category="format",
                    message=f"Unknown format type: {format_type}",
                    suggestion="Use 'srt', 'vtt', or 'json'"
                )],
                score=0.0,
                metadata={}
            )
    
    def generate_quality_report(self, alignment_data: AlignmentData, 
                              subtitle_contents: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Generate a comprehensive quality report.
        
        Args:
            alignment_data: The alignment data to analyze
            subtitle_contents: Optional dictionary of format -> content for format validation
            
        Returns:
            Comprehensive quality report
        """
        report = {
            'timestamp': time.time(),
            'alignment_validation': self.validate_alignment_data(alignment_data).get_summary()
        }
        
        if subtitle_contents:
            format_validations = {}
            for format_type, content in subtitle_contents.items():
                validation_result = self.validate_subtitle_format(content, format_type)
                format_validations[format_type] = validation_result.get_summary()
            
            report['format_validations'] = format_validations
        
        # Calculate overall quality score
        scores = [report['alignment_validation']['score']]
        if 'format_validations' in report:
            scores.extend([v['score'] for v in report['format_validations'].values()])
        
        report['overall_quality_score'] = sum(scores) / len(scores) if scores else 0.0
        
        return report