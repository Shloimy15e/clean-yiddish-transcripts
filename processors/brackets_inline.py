"""
Processor that removes inline bracketed content while keeping full bracketed paragraphs.

Inline brackets like [note] are typically editorial notes and should be removed.
Full paragraphs wrapped in brackets are typically spoken content and should be kept.
"""

import re
from typing import Tuple, List, Dict, Any, Optional

from registry import ProcessorRegistry
from processors.base import BaseProcessor


def is_full_paragraph_bracket(para_text: str) -> bool:
    """
    Check if the paragraph is entirely wrapped in a single pair of brackets.
    
    Returns True for paragraphs like:
        "[This entire paragraph is in brackets]"
    
    Returns False for paragraphs like:
        "Some text [with a note] in the middle"
        "[First bracket] and [second bracket]"
    """
    stripped = para_text.strip()
    if not stripped.startswith('[') or not stripped.endswith(']'):
        return False
    
    # Check if this is a single bracket pair wrapping the whole paragraph
    # by counting bracket balance
    depth = 0
    for i, char in enumerate(stripped):
        if char == '[':
            depth += 1
        elif char == ']':
            depth -= 1
            # If we reach depth 0 before the end, there are multiple bracket pairs
            if depth == 0 and i < len(stripped) - 1:
                return False
    
    return depth == 0


@ProcessorRegistry.register
class BracketsInlineProcessor(BaseProcessor):
    """
    Processor that removes inline bracketed [notes] while preserving
    full paragraphs that are wrapped in brackets.
    
    This is useful because:
    - Inline brackets like [note from editor] are typically non-speech
    - Full bracketed paragraphs are typically spoken content
    """
    
    name = "brackets_inline"
    description = "Removes inline [bracketed notes] but keeps full bracketed paragraphs"
    
    # Pattern to match bracketed content
    BRACKET_PATTERN = re.compile(r'\[.*?\]')
    
    def __init__(self, exception_patterns: Optional[List[str]] = None):
        """
        Args:
            exception_patterns: List of regex patterns - content matching these won't be removed
        """
        self.exception_patterns = exception_patterns or []
    
    def _matches_exception(self, text: str) -> bool:
        """Check if text matches any exception pattern."""
        for pattern in self.exception_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False
    
    def _create_replacer(self, removed_brackets: List[str]):
        """Create a replacement function that tracks removed brackets."""
        def replacer(match):
            matched_text = match.group(0)
            if self._matches_exception(matched_text):
                return matched_text
            if matched_text not in removed_brackets:
                removed_brackets.append(matched_text)
            return ''
        return replacer
    
    def process(self, text: str, context: Optional[Dict[str, Any]] = None) -> Tuple[str, List[Dict[str, Any]]]:
        removed_items = []
        removed_brackets = []
        replacer = self._create_replacer(removed_brackets)
        
        # If we have paragraph context, process paragraph by paragraph
        if context and 'paragraphs' in context:
            for meta in context['paragraphs']:
                para_text = meta.get('text', '')
                
                # Skip if this is a full bracketed paragraph (keep it)
                if is_full_paragraph_bracket(para_text):
                    continue
                
                # Remove inline brackets from paragraph text
                meta['text'] = self.BRACKET_PATTERN.sub(replacer, para_text)
        
        # Also process the raw text (for non-context mode)
        lines = text.split('\n')
        processed_lines = []
        
        for line in lines:
            if is_full_paragraph_bracket(line):
                # Keep full bracketed paragraphs as-is
                processed_lines.append(line)
            else:
                # Remove inline brackets
                processed_lines.append(self.BRACKET_PATTERN.sub(replacer, line))
        
        cleaned = '\n'.join(processed_lines)
        
        if removed_brackets:
            removed_items.append({
                'pattern': 'Inline bracketed notes',
                'matches': removed_brackets[:10],
                'count': len(removed_brackets)
            })
        
        return cleaned, removed_items
