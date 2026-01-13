"""
Document model for representing parsed documents.

Provides a format-agnostic representation that preserves formatting
through the cleaning pipeline.
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Optional, Dict, Any


class Alignment(Enum):
    """Paragraph alignment options."""
    LEFT = auto()
    CENTER = auto()
    RIGHT = auto()
    JUSTIFY = auto()


@dataclass
class RunStyle:
    """Formatting options for a text run within a paragraph."""
    bold: Optional[bool] = None
    italic: Optional[bool] = None
    underline: Optional[bool] = None
    font_size: Optional[float] = None  # in points
    font_name: Optional[str] = None
    color_rgb: Optional[tuple] = None  # (R, G, B) tuple
    highlight_color: Optional[str] = None
    all_caps: Optional[bool] = None
    small_caps: Optional[bool] = None
    strike: Optional[bool] = None
    superscript: Optional[bool] = None
    subscript: Optional[bool] = None


@dataclass
class TextRun:
    """A run of text with consistent formatting within a paragraph."""
    text: str
    style: RunStyle = field(default_factory=RunStyle)
    
    def is_empty(self) -> bool:
        """Check if run has no text content."""
        return not self.text.strip()


@dataclass
class ParagraphFormat:
    """Formatting options for a paragraph."""
    alignment: Alignment = Alignment.RIGHT
    right_to_left: bool = True
    left_indent: Optional[float] = None  # in points
    right_indent: Optional[float] = None
    first_line_indent: Optional[float] = None
    space_before: Optional[float] = None
    space_after: Optional[float] = None
    line_spacing: Optional[float] = None


@dataclass
class Paragraph:
    """A paragraph in a document."""
    runs: List[TextRun] = field(default_factory=list)
    format: ParagraphFormat = field(default_factory=ParagraphFormat)
    style_name: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Metadata fields carried over from original extraction
    original_text: Optional[str] = None
    start_pos: int = 0
    end_pos: int = 0
    is_heading_style: bool = False
    is_bold: bool = False
    font_size: Optional[float] = None
    is_larger_than_normal: bool = False
    
    @property
    def text(self) -> str:
        """Get the full text of the paragraph."""
        return "".join(run.text for run in self.runs)
    
    @text.setter
    def text(self, value: str):
        """Set paragraph text (replaces all runs with a single run)."""
        if self.runs:
            # Preserve the style of the first run
            first_style = self.runs[0].style
            self.runs = [TextRun(text=value, style=first_style)]
        else:
            self.runs = [TextRun(text=value)]
    
    def add_run(self, text: str, style: Optional[RunStyle] = None) -> TextRun:
        """Add a text run to the paragraph."""
        run = TextRun(text=text, style=style or RunStyle())
        self.runs.append(run)
        return run
    
    def is_empty(self) -> bool:
        """Check if paragraph has no text content."""
        return not self.text.strip()
    
    @property
    def char_count(self) -> int:
        """Get character count of the paragraph."""
        return len(self.text)
    
    @property
    def word_count(self) -> int:
        """Get word count of the paragraph."""
        return len(self.text.split())


@dataclass
class DocumentMetadata:
    """Metadata for a document."""
    filename: Optional[str] = None
    source_file: Optional[str] = None
    profile: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Document:
    """
    A format-agnostic document representation.
    
    This class serves as the intermediary between input readers, processors,
    and output writers. Preserves formatting through the cleaning pipeline.
    """
    paragraphs: List[Paragraph] = field(default_factory=list)
    metadata: DocumentMetadata = field(default_factory=DocumentMetadata)
    
    # Statistics tracking
    original_text: Optional[str] = None
    cleaned_text: Optional[str] = None
    removed_items: List[Dict[str, Any]] = field(default_factory=list)
    
    def add_paragraph(self, text: str = "", 
                      format: Optional[ParagraphFormat] = None) -> Paragraph:
        """Add a paragraph to the document."""
        para = Paragraph(format=format or ParagraphFormat())
        if text:
            para.add_run(text)
        self.paragraphs.append(para)
        return para
    
    def get_text(self) -> str:
        """Get all text as a single string."""
        return "\n".join(p.text for p in self.paragraphs if not p.is_empty())
    
    def get_paragraphs_text(self) -> List[str]:
        """Get text of each paragraph as a list."""
        return [p.text for p in self.paragraphs]
    
    @property
    def total_chars(self) -> int:
        """Get total character count."""
        return sum(p.char_count for p in self.paragraphs)
    
    @property
    def total_words(self) -> int:
        """Get total word count."""
        return sum(p.word_count for p in self.paragraphs)
    
    @property
    def paragraph_count(self) -> int:
        """Get number of non-empty paragraphs."""
        return len([p for p in self.paragraphs if not p.is_empty()])
