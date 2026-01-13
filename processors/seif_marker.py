"""
Processor that removes seif markers (gematria followed by period) from paragraph beginnings.
"""

import re
from typing import Tuple, List, Dict, Any, Optional

from registry import ProcessorRegistry
from processors.base import BaseProcessor
from utils import is_valid_gematria


@ProcessorRegistry.register
class SeifMarkerProcessor(BaseProcessor):
    """Processor that removes seif markers (Hebrew numerals) from paragraph starts."""
    
    name = "seif_marker"
    description = "Removes seif markers (Hebrew numerals like א. ב. etc.) from paragraph starts"
    
    # Matches gematria with optional asterisk before the period (e.g., "א." or "א*.")
    SEIF_PATTERN = re.compile(r'^([א-ת]+)\*?\.\s*')
    
    def process(self, text: str, context: Optional[Dict[str, Any]] = None) -> Tuple[str, List[Dict[str, Any]]]:
        removed_items = []
        seif_positions = []
        
        # Work directly on Word paragraphs from context
        if context and 'paragraphs' in context:
            for meta in context['paragraphs']:
                para_text = meta.get('text', '')
                match = self.SEIF_PATTERN.match(para_text)
                if match:
                    potential_gematria = match.group(1)
                    if is_valid_gematria(potential_gematria):
                        # Track position in original text
                        seif_positions.append({
                            'start': meta.get('start_pos', 0),
                            'end': meta.get('start_pos', 0) + match.end(),
                            'text': match.group(0).strip(),
                            'reason': 'Seif markers (gematria)'
                        })
                        # Update the paragraph text directly
                        meta['text'] = para_text[match.end():]
        
        if seif_positions:
            removed_items.append({
                'pattern': 'Seif markers (gematria)',
                'matches': [],  # Empty for pattern matching
                'positions': seif_positions,  # Use positions instead
                'count': len(seif_positions)
            })
        
        # Return original text unchanged - the real work is done on context['paragraphs']
        return text, removed_items
