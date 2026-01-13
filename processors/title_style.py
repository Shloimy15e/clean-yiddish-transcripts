"""
Processor that removes paragraphs based on Word document styling.
"""

import re
from typing import Tuple, List, Dict, Any, Optional

from registry import ProcessorRegistry
from processors.base import BaseProcessor


def matches_any_pattern(text: str, patterns: List[str]) -> bool:
    """Check if text matches any of the given regex patterns."""
    for pattern in patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False


@ProcessorRegistry.register
class TitleStyleProcessor(BaseProcessor):
    """
    Processor that removes paragraphs based on Word document styling:
    - Word heading styles (Heading 1, Heading 2, Title, etc.)
    - Short paragraphs (less than one line / few words)
    - Text larger than normal body text
    """
    
    name = "title_style"
    description = "Removes titles based on Word styles, size, and paragraph length"
    
    def __init__(self, min_words: int = 5, size_threshold: float = 1.2,
                 exception_patterns: Optional[List[str]] = None,
                 force_remove_patterns: Optional[List[str]] = None):
        """
        Args:
            min_words: Minimum words for a paragraph to be kept (default: 5)
            size_threshold: Multiplier for avg font size to consider "larger" (default: 1.2)
            exception_patterns: List of regex patterns - content matching these won't be removed
            force_remove_patterns: List of regex patterns - content matching these will always be removed
        """
        self.min_words = min_words
        self.size_threshold = size_threshold
        self.exception_patterns = exception_patterns or []
        self.force_remove_patterns = force_remove_patterns or []
    
    def _matches_exception(self, text: str) -> bool:
        """Check if text matches any exception pattern."""
        return matches_any_pattern(text, self.exception_patterns)
    
    def _matches_force_remove(self, text: str) -> bool:
        """Check if text matches any force remove pattern."""
        return matches_any_pattern(text, self.force_remove_patterns)
    
    def process(self, text: str, context: Optional[Dict[str, Any]] = None) -> Tuple[str, List[Dict[str, Any]]]:
        if not context or 'paragraphs' not in context:
            return text, []
        
        paragraphs_meta = context['paragraphs']
        removed_items = []
        kept_paragraphs = []
        
        # Track positions for each removal type
        heading_positions = []
        short_positions = []
        large_font_positions = []
        force_positions = []
        
        for meta in paragraphs_meta:
            should_remove = False
            removal_reason = None
            
            # Use the current text (may have been modified by SeifMarkerProcessor)
            current_text = meta.get('text', '')
            original_text = meta.get('original_text', current_text)
            
            # Recalculate word count based on current text
            current_word_count = len(current_text.split())
            
            # Check for force remove patterns - if found, always remove this paragraph
            if self._matches_force_remove(current_text):
                force_positions.append({
                    'start': meta.get('start_pos', 0),
                    'end': meta.get('end_pos', 0),
                    'text': original_text[:100],
                    'reason': 'Force removed (contains blocked patterns)'
                })
                continue
            
            # Check for exception patterns - if found, never remove this paragraph
            if self._matches_exception(current_text):
                kept_paragraphs.append(current_text)
                continue
            
            if meta.get('is_heading_style'):
                should_remove = True
                removal_reason = 'Word heading styles'
                heading_positions.append({
                    'start': meta.get('start_pos', 0),
                    'end': meta.get('end_pos', 0),
                    'text': original_text[:100],
                    'reason': removal_reason
                })
            
            elif current_word_count < self.min_words:
                should_remove = True
                removal_reason = f'Short paragraphs (< {self.min_words} words)'
                short_positions.append({
                    'start': meta.get('start_pos', 0),
                    'end': meta.get('end_pos', 0),
                    'text': original_text[:100],
                    'reason': removal_reason
                })
            
            elif meta.get('is_larger_than_normal'):
                should_remove = True
                removal_reason = 'Larger than normal text'
                large_font_positions.append({
                    'start': meta.get('start_pos', 0),
                    'end': meta.get('end_pos', 0),
                    'text': original_text[:100],
                    'reason': removal_reason
                })
            
            elif meta.get('is_bold') and current_word_count < 15:
                should_remove = True
                removal_reason = 'Word heading styles'
                heading_positions.append({
                    'start': meta.get('start_pos', 0),
                    'end': meta.get('end_pos', 0),
                    'text': original_text[:100],
                    'reason': removal_reason
                })
            
            if not should_remove:
                kept_paragraphs.append(current_text)
        
        if heading_positions:
            removed_items.append({
                'pattern': 'Word heading styles',
                'matches': [p['text'] for p in heading_positions[:10]],
                'positions': heading_positions,
                'count': len(heading_positions)
            })
        
        if short_positions:
            removed_items.append({
                'pattern': f'Short paragraphs (< {self.min_words} words)',
                'matches': [p['text'] for p in short_positions[:10]],
                'positions': short_positions,
                'count': len(short_positions)
            })
        
        if large_font_positions:
            removed_items.append({
                'pattern': 'Larger than normal text',
                'matches': [p['text'] for p in large_font_positions[:10]],
                'positions': large_font_positions,
                'count': len(large_font_positions)
            })
        
        if force_positions:
            removed_items.append({
                'pattern': 'Force removed (contains blocked patterns)',
                'matches': [p['text'] for p in force_positions[:10]],
                'positions': force_positions,
                'count': len(force_positions)
            })
        
        return '\n'.join(kept_paragraphs), removed_items
