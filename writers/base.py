"""
Base output writer class for document export plugins.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, Optional, Union
from io import BytesIO

from registry import WriterRegistry


class OutputWriter(ABC):
    """
    Base class for output writers.
    
    Writers are registered via the @WriterRegistry.register decorator
    and handle exporting documents to specific formats.
    """
    
    # Class attributes for registration
    name: str = "base"
    title: str = "Base Writer"
    description: str = "Base output writer"
    extension: str = ""
    mime_type: str = "application/octet-stream"
    
    @abstractmethod
    def write(self, text: str, output: Union[str, Path, BytesIO], 
              context: Optional[Dict[str, Any]] = None) -> None:
        """
        Write the cleaned text to the specified output.
        
        Args:
            text: The cleaned text to write
            output: Output path (str/Path) or BytesIO stream
            context: Optional context with document metadata, formatting info, etc.
        """
        pass
    
    @abstractmethod
    def write_to_bytes(self, text: str, 
                       context: Optional[Dict[str, Any]] = None) -> bytes:
        """
        Write the cleaned text and return as bytes.
        
        Args:
            text: The cleaned text to write
            context: Optional context with document metadata, formatting info, etc.
            
        Returns:
            bytes: The output file content as bytes
        """
        pass
    
    def get_info(self) -> Dict[str, str]:
        """Get writer info for API responses."""
        return {
            'name': self.name,
            'title': self.title,
            'description': self.description,
            'extension': self.extension,
            'mime_type': self.mime_type,
        }
