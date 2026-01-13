"""
Processor that removes special/invisible characters.
"""

from typing import Tuple, List, Dict, Any, Optional

from registry import ProcessorRegistry
from processors.base import BaseProcessor


@ProcessorRegistry.register
class SpecialCharsProcessor(BaseProcessor):
    """Processor that removes special/invisible unicode characters."""
    
    name = "special_chars"
    description = "Removes special unicode characters (zero-width spaces, BOM, etc.)"
    
    def __init__(self, chars: Optional[List[str]] = None):
        self.chars_to_remove = chars or [
            '\u200b',  # Zero-width space
            '\ufeff',  # BOM
            '\u200e',  # Left-to-right mark
            '\u200f',  # Right-to-left mark
        ]
    
    def process(self, text: str, context: Optional[Dict[str, Any]] = None) -> Tuple[str, List[Dict[str, Any]]]:
        removed_items = []
        cleaned = text
        
        for char in self.chars_to_remove:
            if char in cleaned:
                count = cleaned.count(char)
                cleaned = cleaned.replace(char, '')
                removed_items.append({
                    'pattern': f'Special character (unicode {ord(char):04x})',
                    'matches': [f'U+{ord(char):04X}'] * min(count, 10),
                    'count': count
                })
        
        return cleaned, removed_items
