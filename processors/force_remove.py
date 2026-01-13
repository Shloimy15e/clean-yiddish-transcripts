"""
Processor that removes paragraphs containing force remove patterns.
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
class ForceRemoveProcessor(BaseProcessor):
    """Processor that removes paragraphs containing blocked patterns."""
    
    name = "force_remove"
    description = "Removes paragraphs containing blocked words/phrases (regex patterns)"
    
    def __init__(self, force_remove_patterns: Optional[List[str]] = None):
        """
        Args:
            force_remove_patterns: List of regex patterns - paragraphs matching any will be removed
        """
        self.force_remove_patterns = force_remove_patterns or []
    
    def process(self, text: str, context: Optional[Dict[str, Any]] = None) -> Tuple[str, List[Dict[str, Any]]]:
        removed_items = []
        force_removed = []
        
        # Use context paragraphs if available (from Word document)
        if context and 'paragraphs' in context:
            kept_paragraphs = []
            for meta in context['paragraphs']:
                para_text = meta.get('text', '')
                if matches_any_pattern(para_text, self.force_remove_patterns):
                    force_removed.append(para_text[:100])
                else:
                    kept_paragraphs.append(para_text)
            result_text = '\n'.join(kept_paragraphs)
        else:
            # Fallback: split by newlines
            paragraphs = text.split('\n')
            kept_paragraphs = []
            for para in paragraphs:
                if para.strip() and matches_any_pattern(para, self.force_remove_patterns):
                    force_removed.append(para[:100])
                else:
                    kept_paragraphs.append(para)
            result_text = '\n'.join(kept_paragraphs)
        
        if force_removed:
            removed_items.append({
                'pattern': 'Force removed (contains blocked patterns)',
                'matches': force_removed[:10],
                'count': len(force_removed)
            })
        
        return result_text, removed_items
