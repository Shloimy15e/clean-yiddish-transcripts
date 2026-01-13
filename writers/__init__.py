"""
Output writer plugins for document export.

Each writer handles a specific output format (docx, txt, etc.).
"""

from writers.base import OutputWriter
from writers.docx_writer import DocxWriter
from writers.txt_writer import TxtWriter

__all__ = [
    'OutputWriter',
    'DocxWriter',
    'TxtWriter',
]
