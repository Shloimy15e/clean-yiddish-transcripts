"""
Processor that applies regex patterns to remove content.
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
class RegexProcessor(BaseProcessor):
    """Processor that applies regex patterns to remove content."""
    
    name = "regex"
    description = "Applies regex patterns to remove matching content"
    
    def __init__(self, patterns: Optional[List[Tuple[str, str]]] = None,
                 exception_patterns: Optional[List[str]] = None):
        """
        Args:
            patterns: List of (pattern, description) tuples
            exception_patterns: List of regex patterns - content matching these won't be removed
        """
        self.patterns = patterns or []
        self.exception_patterns = exception_patterns or []
    
    def _matches_exception(self, text: str) -> bool:
        """Check if text matches any exception pattern."""
        return matches_any_pattern(text, self.exception_patterns)
    
    def process(self, text: str, context: Optional[Dict[str, Any]] = None) -> Tuple[str, List[Dict[str, Any]]]:
        removed_items = []
        cleaned = text
        
        for pattern, description in self.patterns:
            matches = re.findall(pattern, cleaned, re.MULTILINE | re.IGNORECASE)
            if matches:
                # Filter out matches that contain exception patterns
                actual_matches = [
                    m for m in matches 
                    if not self._matches_exception(m if isinstance(m, str) else str(m))
                ]
                
                if actual_matches:
                    removed_items.append({
                        'pattern': description,
                        'matches': actual_matches[:10],
                        'count': len(actual_matches)
                    })
                    
                    if description == 'excessive newlines':
                        cleaned = re.sub(pattern, '\n\n', cleaned, flags=re.MULTILINE)
                    else:
                        # Only remove matches that don't match exception patterns
                        def replace_if_no_exception(match):
                            matched_text = match.group(0)
                            if self._matches_exception(matched_text):
                                return matched_text  # Keep it
                            return ''  # Remove it
                        cleaned = re.sub(pattern, replace_if_no_exception, cleaned, 
                                       flags=re.MULTILINE | re.IGNORECASE)
        
        return cleaned, removed_items
