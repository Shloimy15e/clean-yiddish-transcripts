"""
Processor that removes specific parenthetical non-speech content.

Most parenthetical content in transcripts is SPOKEN (translations, clarifications),
so this processor is DISABLED by default. It only removes content matching
specific non-speech patterns like source citations and editorial markers.
"""

import re
from typing import Tuple, List, Dict, Any, Optional

from registry import ProcessorRegistry
from processors.base import BaseProcessor


# Default patterns for non-speech parenthetical content
# These are common editorial notes and source references that weren't spoken
DEFAULT_NON_SPEECH_PATTERNS = [
    # Source citations (book references)
    r'\([א-ת]+\s+[א-ת]{1,2}[\',׳]?\s*,?\s*[א-ת]{1,2}\)',  # (תהלים קיט, א)
    r'\([א-ת]+\s+\d+[,:\s]+\d+\)',  # (בראשית 1:1) or (בראשית 1, 1)
    
    # Editorial markers
    r'\(המשך\)',  # (continuation)
    r'\(סיום\)',  # (end)
    r'\(ראה\s+[^)]+\)',  # (see ...)
    r'\(עיין\s+[^)]+\)',  # (refer to ...)
    
    # Stage directions / non-verbal
    r'\(צוחק\)',  # (laughing)
    r'\(צוחקים\)',  # (they laugh)
    r'\(מחיאות\s*כפיים\)',  # (applause)
    r'\(הפסקה\)',  # (break/pause)
    r'\(לא\s+נשמע\)',  # (inaudible)
    r'\(לא\s+ברור\)',  # (unclear)
    r'\(חסר\)',  # (missing)
]


@ProcessorRegistry.register
class ParenthesesNotesProcessor(BaseProcessor):
    """
    Processor that removes specific parenthetical non-speech content.
    
    This processor is DISABLED by default because most parenthetical content
    in Yiddish transcripts is actually spoken (translations, clarifications).
    
    Only removes content matching specific non-speech patterns like:
    - Source citations (פסוק references)
    - Editorial markers (המשך, סיום)
    - Stage directions (צוחקים, מחיאות כפיים)
    """
    
    name = "parentheses_notes"
    description = "Removes parenthetical (notes) matching non-speech patterns - OFF by default since most parens are spoken"
    
    # General pattern to find all parenthetical content
    PAREN_PATTERN = re.compile(r'\([^)]+\)')
    
    def __init__(self, 
                 non_speech_patterns: Optional[List[str]] = None,
                 exception_patterns: Optional[List[str]] = None,
                 remove_all: bool = False):
        """
        Args:
            non_speech_patterns: List of regex patterns that identify non-speech content
                                 If None, uses DEFAULT_NON_SPEECH_PATTERNS
            exception_patterns: List of regex patterns - content matching these won't be removed
            remove_all: If True, removes ALL parenthetical content (not recommended)
        """
        self.non_speech_patterns = non_speech_patterns or DEFAULT_NON_SPEECH_PATTERNS
        self.exception_patterns = exception_patterns or []
        self.remove_all = remove_all
        
        # Compile non-speech patterns
        self._compiled_patterns = [
            re.compile(p, re.IGNORECASE) for p in self.non_speech_patterns
        ]
    
    def _matches_exception(self, text: str) -> bool:
        """Check if text matches any exception pattern."""
        for pattern in self.exception_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False
    
    def _is_non_speech(self, paren_content: str) -> bool:
        """Check if the parenthetical content is non-speech."""
        if self.remove_all:
            return True
        
        for pattern in self._compiled_patterns:
            if pattern.search(paren_content):
                return True
        return False
    
    def process(self, text: str, context: Optional[Dict[str, Any]] = None) -> Tuple[str, List[Dict[str, Any]]]:
        removed_items = []
        removed_parens = []
        
        def replace_paren(match):
            matched_text = match.group(0)
            
            # Check exception patterns first
            if self._matches_exception(matched_text):
                return matched_text
            
            # Check if this is non-speech content
            if self._is_non_speech(matched_text):
                removed_parens.append(matched_text)
                return ''
            
            # Keep spoken content
            return matched_text
        
        # Process paragraph context if available
        if context and 'paragraphs' in context:
            for meta in context['paragraphs']:
                para_text = meta.get('text', '')
                meta['text'] = self.PAREN_PATTERN.sub(replace_paren, para_text)
        
        # Process raw text
        cleaned = self.PAREN_PATTERN.sub(replace_paren, text)
        
        if removed_parens:
            removed_items.append({
                'pattern': 'Parenthetical non-speech notes',
                'matches': removed_parens[:10],
                'count': len(removed_parens)
            })
        
        return cleaned, removed_items
