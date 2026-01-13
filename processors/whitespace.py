"""
Processor that normalizes whitespace.
"""

import re
from typing import Tuple, List, Dict, Any, Optional

from registry import ProcessorRegistry
from processors.base import BaseProcessor


@ProcessorRegistry.register
class WhitespaceProcessor(BaseProcessor):
    """Processor that normalizes whitespace."""
    
    name = "whitespace"
    description = "Normalizes whitespace (multiple spaces, trailing spaces, etc.)"
    
    def process(self, text: str, context: Optional[Dict[str, Any]] = None) -> Tuple[str, List[Dict[str, Any]]]:
        cleaned = text
        
        # Multiple spaces to single space
        cleaned = re.sub(r' +', ' ', cleaned)
        
        # Remove spaces before/after newlines
        cleaned = re.sub(r'\n ', '\n', cleaned)
        cleaned = re.sub(r' \n', '\n', cleaned)
        
        # Trim leading/trailing whitespace
        cleaned = cleaned.strip()
        
        # No need to track removed whitespace in detail
        return cleaned, []
