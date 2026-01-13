"""
Base processor class for document cleaning plugins.
"""

from abc import ABC, abstractmethod
from typing import Tuple, List, Dict, Any, Optional

from registry import ProcessorRegistry


class BaseProcessor(ABC):
    """
    Base class for all text processors.
    
    Processors are registered via the @ProcessorRegistry.register decorator
    and can be composed into cleaning profiles.
    """
    
    # Class attributes for registration
    name: str = "base"
    description: str = "Base processor"
    
    @abstractmethod
    def process(self, text: str, context: Optional[Dict[str, Any]] = None) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Process the text and return cleaned text with removal info.
        
        Args:
            text: The text to process
            context: Optional dict with processing context (paragraph metadata, etc.)
            
        Returns:
            tuple: (processed_text, list of removed_items)
                - processed_text: The text after processing
                - removed_items: List of dicts with 'pattern', 'matches', 'count', and optionally 'positions'
        """
        pass
    
    def get_info(self) -> Dict[str, str]:
        """Get processor info for API responses."""
        return {
            'name': self.name,
            'description': self.description,
        }
