"""
Processor plugins for document cleaning.

Each processor handles a specific type of content removal or transformation.
"""

from processors.base import BaseProcessor
from processors.special_chars import SpecialCharsProcessor
from processors.whitespace import WhitespaceProcessor
from processors.title_style import TitleStyleProcessor
from processors.seif_marker import SeifMarkerProcessor
from processors.regex_processor import RegexProcessor
from processors.force_remove import ForceRemoveProcessor
from processors.brackets_inline import BracketsInlineProcessor
from processors.parentheses_notes import ParenthesesNotesProcessor
from processors.editorial_hebrew import EditorialHebrewProcessor

__all__ = [
    'BaseProcessor',
    'SpecialCharsProcessor',
    'WhitespaceProcessor',
    'TitleStyleProcessor',
    'SeifMarkerProcessor',
    'RegexProcessor',
    'ForceRemoveProcessor',
    'BracketsInlineProcessor',
    'ParenthesesNotesProcessor',
    'EditorialHebrewProcessor',
]
