"""
Writer for plain text files.
"""

from pathlib import Path
from typing import Dict, Any, Optional, Union
from io import BytesIO

from registry import WriterRegistry
from writers.base import OutputWriter


@WriterRegistry.register
class TxtWriter(OutputWriter):
    """Writer for plain text files."""
    
    name = "txt"
    title = "Plain Text"
    description = "Plain text file (UTF-8 encoded)"
    extension = ".txt"
    mime_type = "text/plain; charset=utf-8"
    
    def write(self, text: str, output: Union[str, Path, BytesIO],
              context: Optional[Dict[str, Any]] = None) -> None:
        """
        Write the cleaned text to a .txt file.
        
        Args:
            text: The cleaned text to write
            output: Output path (str/Path) or BytesIO stream
            context: Optional context (not used for plain text)
        """
        if isinstance(output, BytesIO):
            output.write(text.encode('utf-8'))
        else:
            output_path = Path(output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(text, encoding='utf-8')
    
    def write_to_bytes(self, text: str,
                       context: Optional[Dict[str, Any]] = None) -> bytes:
        """
        Write the cleaned text and return as bytes.
        
        Args:
            text: The cleaned text to write
            context: Optional context (not used for plain text)
            
        Returns:
            bytes: The text encoded as UTF-8 bytes
        """
        return text.encode('utf-8')
