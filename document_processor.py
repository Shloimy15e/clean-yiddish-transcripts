"""
Document processor for handling Word documents.

Uses the plugin-based architecture for cleaning and output writers.
"""

from typing import Dict, Any, Optional, List

from docx import Document

from cleaner import TranscriptCleaner
from registry import WriterRegistry

# Import writers to register them (side effect: registers them)
import writers.docx_writer  # noqa: F401
import writers.txt_writer  # noqa: F401

# Default processors to use when none specified
DEFAULT_PROCESSORS = ['special_chars', 'seif_marker', 'title_style', 'regex', 'whitespace']


class DocumentProcessor:
    """Processes Word documents and extracts text."""
    
    def __init__(self):
        self.cleaner = TranscriptCleaner()
    
    def extract_text_from_docx(self, file_path: str) -> str:
        """
        Extract text from a .docx file.
        
        Args:
            file_path: Path to the .docx file
            
        Returns:
            str: Extracted text
        """
        try:
            doc = Document(file_path)
            paragraphs = []
            
            for para in doc.paragraphs:
                if para.text.strip():
                    paragraphs.append(para.text)
            
            return '\n'.join(paragraphs)
        except Exception as e:
            raise Exception(f"Error reading document: {str(e)}")
    
    def extract_paragraphs_with_metadata(self, file_path: str) -> tuple:
        """
        Extract paragraphs with their metadata (style, font size, etc.).
        
        Args:
            file_path: Path to the .docx file
            
        Returns:
            tuple: (full_text, list of paragraph metadata dicts)
        """
        try:
            doc = Document(file_path)
            paragraphs_meta = []
            all_font_sizes = []
            
            doc_default_size = 12
            try:
                normal_style = doc.styles['Normal']
                if normal_style.font and normal_style.font.size:
                    doc_default_size = normal_style.font.size.pt
            except KeyError:
                pass
            
            current_pos = 0
            for para in doc.paragraphs:
                if not para.text.strip():
                    continue
                
                style_name = para.style.name if para.style else None
                is_heading_style = style_name and ('heading' in style_name.lower() or 'title' in style_name.lower())
                
                font_size = self._get_paragraph_font_size(para, doc_default_size)
                if font_size:
                    all_font_sizes.append(font_size)
                
                is_bold = self._is_paragraph_bold(para)
                
                # Extract runs with formatting
                runs = self._extract_runs(para)
                
                para_len = len(para.text)
                paragraphs_meta.append({
                    'text': para.text,
                    'original_text': para.text,  # Keep original for highlighting
                    'start_pos': current_pos,
                    'end_pos': current_pos + para_len,
                    'style_name': style_name,
                    'is_heading_style': is_heading_style,
                    'is_bold': is_bold,
                    'font_size': font_size,
                    'char_count': para_len,
                    'word_count': len(para.text.split()),
                    'runs': runs,  # Store run formatting for output
                })
                # +1 for the newline separator
                current_pos += para_len + 1
            
            avg_font_size = sum(all_font_sizes) / len(all_font_sizes) if all_font_sizes else 12
            
            for meta in paragraphs_meta:
                meta['is_larger_than_normal'] = (
                    meta['font_size'] is not None and 
                    meta['font_size'] > avg_font_size * 1.2
                )
                meta['avg_font_size'] = avg_font_size
            
            full_text = '\n'.join(p['text'] for p in paragraphs_meta)
            return full_text, paragraphs_meta
            
        except Exception as e:
            raise Exception(f"Error reading document metadata: {str(e)}")
    
    def _extract_runs(self, para) -> List[Dict[str, Any]]:
        """Extract runs with their formatting from a paragraph."""
        runs = []
        for run in para.runs:
            run_data = {
                'text': run.text,
                'style': {
                    'bold': run.font.bold,
                    'italic': run.font.italic,
                    'underline': run.font.underline is not None and run.font.underline,
                    'font_size': run.font.size.pt if run.font.size else None,
                    'font_name': run.font.name,
                    'strike': run.font.strike,
                    'superscript': run.font.superscript,
                    'subscript': run.font.subscript,
                }
            }
            # Extract color if present
            if run.font.color and run.font.color.rgb:
                try:
                    rgb_obj = run.font.color.rgb
                    hex_color = str(rgb_obj)
                    if len(hex_color) == 6:
                        r = int(hex_color[0:2], 16)
                        g = int(hex_color[2:4], 16)
                        b = int(hex_color[4:6], 16)
                        run_data['style']['color_rgb'] = (r, g, b)
                except Exception:
                    pass
            
            runs.append(run_data)
        
        return runs
    
    def _is_paragraph_bold(self, para) -> bool:
        """Check if the entire paragraph is bold."""
        if not para.runs:
            return False
        for run in para.runs:
            if run.text.strip() and not run.bold:
                return False
        return len(para.runs) > 0 and any(r.text.strip() for r in para.runs)
    
    def _get_paragraph_font_size(self, para, doc_default_size=None) -> Optional[float]:
        """Get the font size of a paragraph (from first run, style, or default)."""
        for run in para.runs:
            if run.font.size:
                return run.font.size.pt
        
        if para.style and para.style.font and para.style.font.size:
            return para.style.font.size.pt
        
        style = para.style
        while style:
            if style.font and style.font.size:
                return style.font.size.pt
            style = style.base_style
        
        return doc_default_size
    
    def process_document(self, file_path: str, filename: str, 
                         processors: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Process a document: extract text, clean it, and return results.
        
        Args:
            file_path: Path to the document file
            filename: Original filename
            processors: List of processor names to apply (default: DEFAULT_PROCESSORS)
            
        Returns:
            dict: Processing results including original, cleaned, removed items, and stats
        """
        original_text, paragraphs_meta = self.extract_paragraphs_with_metadata(file_path)
        
        context = {
            'paragraphs': paragraphs_meta,
        }
        
        # Use provided processors or default set
        processor_list = processors if processors else DEFAULT_PROCESSORS
        
        cleaned_text, removed_items = self.cleaner.clean_with_processors(
            original_text, processor_list, context
        )
        
        stats = self.cleaner.get_statistics(original_text, cleaned_text)
        
        return {
            'filename': filename,
            'original_text': original_text,
            'cleaned_text': cleaned_text,
            'removed_items': removed_items,
            'statistics': stats,
            'processors': processor_list,
            'context': context,  # Include context for writers
            'success': True
        }
    
    def save_cleaned_document(self, cleaned_text: str, output_path: str,
                              format_name: str = 'docx',
                              context: Optional[Dict[str, Any]] = None) -> str:
        """
        Save cleaned text to a document using the specified writer.
        
        Args:
            cleaned_text: The cleaned text to save
            output_path: Path where to save the document
            format_name: Output format ('docx', 'txt', etc.)
            context: Optional context with paragraph metadata for formatting
            
        Returns:
            str: The output path
        """
        writer = WriterRegistry.get_writer(format_name)
        if not writer:
            # Fallback to docx
            writer = WriterRegistry.get_writer('docx')
        
        if writer:
            writer.write(cleaned_text, output_path, context)
        else:
            # Ultimate fallback - basic docx
            from docx import Document as DocxDoc
            doc = DocxDoc()
            for para_text in cleaned_text.split('\n'):
                if para_text.strip():
                    doc.add_paragraph(para_text)
            doc.save(output_path)
        
        return output_path
    
    def get_cleaned_bytes(self, cleaned_text: str, format_name: str = 'docx',
                          context: Optional[Dict[str, Any]] = None) -> bytes:
        """
        Get cleaned document as bytes for download.
        
        Args:
            cleaned_text: The cleaned text
            format_name: Output format ('docx', 'txt', etc.)
            context: Optional context with paragraph metadata
            
        Returns:
            bytes: The document content as bytes
        """
        writer = WriterRegistry.get_writer(format_name)
        if not writer:
            writer = WriterRegistry.get_writer('docx')
        
        if writer:
            return writer.write_to_bytes(cleaned_text, context)
        else:
            # Fallback
            return cleaned_text.encode('utf-8')
    
    def get_available_formats(self) -> Dict[str, Dict[str, str]]:
        """Get available output formats."""
        return WriterRegistry.get_formats()
