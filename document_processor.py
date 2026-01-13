"""
Document processor for handling Word documents.
"""
import os
from docx import Document
from docx.shared import Pt
from cleaner import TranscriptCleaner, DEFAULT_PROFILE


class DocumentProcessor:
    """Processes Word documents and extracts text."""
    
    def __init__(self):
        self.cleaner = TranscriptCleaner()
    
    def extract_text_from_docx(self, file_path):
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
    
    def extract_paragraphs_with_metadata(self, file_path):
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
    
    def _is_paragraph_bold(self, para):
        """Check if the entire paragraph is bold."""
        if not para.runs:
            return False
        for run in para.runs:
            if run.text.strip() and not run.bold:
                return False
        return len(para.runs) > 0 and any(r.text.strip() for r in para.runs)
    
    def _get_paragraph_font_size(self, para, doc_default_size=None):
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
    
    def process_document(self, file_path, filename, profile=None):
        """
        Process a document: extract text, clean it, and return results.
        
        Args:
            file_path: Path to the document file
            filename: Original filename
            profile: Cleaning profile to use (default: DEFAULT_PROFILE constant)
            
        Returns:
            dict: Processing results including original, cleaned, removed items, and stats
        """
        if profile is None:
            profile = DEFAULT_PROFILE
        
        original_text, paragraphs_meta = self.extract_paragraphs_with_metadata(file_path)
        
        context = {
            'paragraphs': paragraphs_meta,
        }
        
        cleaned_text, removed_items, profile_used = self.cleaner.clean_text(
            original_text, profile, context
        )
        
        stats = self.cleaner.get_statistics(original_text, cleaned_text)
        
        return {
            'filename': filename,
            'original_text': original_text,
            'cleaned_text': cleaned_text,
            'removed_items': removed_items,
            'statistics': stats,
            'profile': profile_used,
            'success': True
        }
    
    def save_cleaned_document(self, cleaned_text, output_path):
        """
        Save cleaned text to a new Word document.
        
        Args:
            cleaned_text: The cleaned text to save
            output_path: Path where to save the document
        """
        doc = Document()
        
        # Split text into paragraphs and add to document
        paragraphs = cleaned_text.split('\n')
        for para_text in paragraphs:
            if para_text.strip():
                doc.add_paragraph(para_text)
        
        doc.save(output_path)
        return output_path
