"""
Text cleaning utilities for Yiddish transcripts.
Removes titles, headings, narrator notes, redactor notes, etc.
"""
import re
from abc import ABC, abstractmethod

# Default cleaning profile
DEFAULT_PROFILE = 'titles_and_parentheses'


class BaseProcessor(ABC):
    """Base class for all text processors."""
    
    name: str = "base"
    description: str = "Base processor"
    
    @abstractmethod
    def process(self, text, context=None):
        """
        Process the text and return cleaned text with removal info.
        
        Args:
            text: The text to process
            context: Optional dict with processing context (paragraph styles, etc.)
            
        Returns:
            tuple: (processed_text, list of removed_items)
        """
        pass


class RegexProcessor(BaseProcessor):
    """Processor that applies regex patterns to remove content."""
    
    name = "regex"
    description = "Applies regex patterns"
    
    def __init__(self, patterns):
        """
        Args:
            patterns: List of (pattern, description) tuples
        """
        self.patterns = patterns
    
    def process(self, text, context=None):
        removed_items = []
        cleaned = text
        
        for pattern, description in self.patterns:
            matches = re.findall(pattern, cleaned, re.MULTILINE | re.IGNORECASE)
            if matches:
                removed_items.append({
                    'pattern': description,
                    'matches': matches[:10],
                    'count': len(matches)
                })
                
                if description == 'excessive newlines':
                    cleaned = re.sub(pattern, '\n\n', cleaned, flags=re.MULTILINE)
                else:
                    cleaned = re.sub(pattern, '', cleaned, flags=re.MULTILINE | re.IGNORECASE)
        
        return cleaned, removed_items


class SpecialCharsProcessor(BaseProcessor):
    """Processor that removes special/invisible characters."""
    
    name = "special_chars"
    description = "Removes special unicode characters"
    
    def __init__(self, chars=None):
        self.chars_to_remove = chars or [
            '\u200b',  # Zero-width space
            '\ufeff',  # BOM
        ]
    
    def process(self, text, context=None):
        removed_items = []
        cleaned = text
        
        for char in self.chars_to_remove:
            if char in cleaned:
                count = cleaned.count(char)
                cleaned = cleaned.replace(char, '')
                removed_items.append({
                    'pattern': f'Special character (unicode {ord(char):04x})',
                    'matches': [char] * count,
                    'count': count
                })
        
        return cleaned, removed_items


class WhitespaceProcessor(BaseProcessor):
    """Processor that normalizes whitespace."""
    
    name = "whitespace"
    description = "Normalizes whitespace"
    
    def process(self, text, context=None):
        cleaned = text
        cleaned = re.sub(r' +', ' ', cleaned)
        cleaned = re.sub(r'\n ', '\n', cleaned)
        cleaned = re.sub(r' \n', '\n', cleaned)
        cleaned = cleaned.strip()
        return cleaned, []


class ParagraphStyleProcessor(BaseProcessor):
    """Processor that handles paragraph-level styling and formatting."""
    
    name = "paragraph_style"
    description = "Processes paragraph styles and formatting"
    
    def __init__(self, style_rules=None):
        """
        Args:
            style_rules: Dict of style rules to apply
        """
        self.style_rules = style_rules or {}
    
    def process(self, text, context=None):
        removed_items = []
        paragraphs = text.split('\n\n')
        processed_paragraphs = []
        
        for para in paragraphs:
            processed_para, para_removed = self._process_paragraph(para, context)
            if processed_para:
                processed_paragraphs.append(processed_para)
            removed_items.extend(para_removed)
        
        return '\n\n'.join(processed_paragraphs), removed_items
    
    def _process_paragraph(self, paragraph, context):
        """Process a single paragraph. Override for custom behavior."""
        return paragraph, []


class TitleStyleProcessor(BaseProcessor):
    """
    Processor that removes paragraphs based on Word document styling:
    - Word heading styles (Heading 1, Heading 2, Title, etc.)
    - Short paragraphs (less than one line / few words)
    - Text larger than normal body text
    """
    
    name = "title_style"
    description = "Removes titles based on Word styles, size, and paragraph length"
    
    def __init__(self, min_words=5, size_threshold=1.2):
        """
        Args:
            min_words: Minimum words for a paragraph to be kept (default: 5)
            size_threshold: Multiplier for avg font size to consider "larger" (default: 1.2)
        """
        self.min_words = min_words
        self.size_threshold = size_threshold
    
    def process(self, text, context=None):
        if not context or 'paragraphs' not in context:
            return text, []
        
        paragraphs_meta = context['paragraphs']
        removed_items = []
        kept_paragraphs = []
        
        heading_removed = []
        short_removed = []
        large_font_removed = []
        
        for meta in paragraphs_meta:
            should_remove = False
            removal_reason = None
            
            if meta.get('is_heading_style'):
                should_remove = True
                removal_reason = 'heading_style'
                heading_removed.append(meta['text'][:100])
            
            elif meta.get('word_count', 0) < self.min_words:
                should_remove = True
                removal_reason = 'short_paragraph'
                short_removed.append(meta['text'][:100])
            
            elif meta.get('is_larger_than_normal'):
                should_remove = True
                removal_reason = 'large_font'
                large_font_removed.append(meta['text'][:100])
            
            if not should_remove:
                kept_paragraphs.append(meta['text'])
        
        if heading_removed:
            removed_items.append({
                'pattern': 'Word heading styles',
                'matches': heading_removed[:10],
                'count': len(heading_removed)
            })
        
        if short_removed:
            removed_items.append({
                'pattern': f'Short paragraphs (< {self.min_words} words)',
                'matches': short_removed[:10],
                'count': len(short_removed)
            })
        
        if large_font_removed:
            removed_items.append({
                'pattern': 'Larger than normal text',
                'matches': large_font_removed[:10],
                'count': len(large_font_removed)
            })
        
        return '\n'.join(kept_paragraphs), removed_items


class CleaningProfile:
    """A cleaning profile that chains multiple processors."""
    
    def __init__(self, name, description, processors):
        """
        Args:
            name: Profile name
            description: Profile description
            processors: List of BaseProcessor instances to run in order
        """
        self.name = name
        self.description = description
        self.processors = processors
    
    def process(self, text, context=None):
        """
        Run all processors in sequence.
        
        Returns:
            tuple: (cleaned_text, all_removed_items)
        """
        all_removed = []
        current_text = text
        
        for processor in self.processors:
            current_text, removed = processor.process(current_text, context)
            all_removed.extend(removed)
        
        return current_text, all_removed


# Common regex patterns
TITLE_PATTERNS = [
    (r'^[A-Z\s]+:.*$', 'headings with colon'),
    (r'^Chapter \d+.*$', 'chapter headings'),
    (r'^Section \d+.*$', 'section headings'),
    (r'\d{1,2}:\d{2}:\d{2}', 'timestamps'),
    (r'\[\d{1,2}:\d{2}\]', 'bracketed timestamps'),
    (r'^Speaker \d+:.*$', 'speaker labels'),
    (r'^Interviewer:.*$', 'interviewer labels'),
    (r'^Narrator:.*$', 'narrator labels'),
    (r'\n{3,}', 'excessive newlines'),
    (r'^[\d\s\-_=]+$', 'separator lines'),
    (r'^\s*Page \d+\s*$', 'page numbers'),
    (r'^\s*\d+\s*$', 'standalone numbers'),
]

BRACKET_PATTERNS = [
    (r'\[.*?\]\s*\(.*?\)', 'brackets followed by parentheses'),
    (r'\[.*?\]', 'bracketed notes'),
    (r'\(.*?\)', 'parenthetical notes'),
]


class TranscriptCleaner:
    """Cleans Yiddish transcripts by removing non-transcript content."""
    
    def __init__(self):
        # Build cleaning profiles from processors
        self.profiles = {
            'titles_only': CleaningProfile(
                name='titles_only',
                description='Removes titles using Word heading styles, short paragraphs, and larger-than-normal text',
                processors=[
                    SpecialCharsProcessor(),
                    TitleStyleProcessor(min_words=5, size_threshold=1.2),
                    WhitespaceProcessor(),
                ]
            ),
            'titles_and_parentheses': CleaningProfile(
                name='titles_and_parentheses',
                description='Removes titles/headings AND all bracketed/parenthetical content',
                processors=[
                    SpecialCharsProcessor(),
                    TitleStyleProcessor(min_words=5, size_threshold=1.2),
                    RegexProcessor(BRACKET_PATTERNS),
                    WhitespaceProcessor(),
                ]
            ),
        }
    
    def get_available_profiles(self):
        """
        Get list of available cleaning profiles.
        
        Returns:
            dict: Dictionary of profile names to their descriptions
        """
        return {
            name: profile.description 
            for name, profile in self.profiles.items()
        }
    
    def clean_text(self, text, profile=None, context=None):
        """
        Clean the transcript text and return both cleaned text and removed content.
        
        Args:
            text: The original transcript text
            profile: The cleaning profile to use (default: DEFAULT_PROFILE constant)
                     Available profiles: 'titles_only', 'titles_and_parentheses'
            context: Optional dict with processing context (paragraph styles, etc.)
            
        Returns:
            tuple: (cleaned_text, removed_items, profile_name)
                - cleaned_text: The text after cleaning
                - removed_items: List of dicts with 'pattern', 'matches', and 'count'
                - profile_name: The name of the profile used
        """
        if profile is None:
            profile = DEFAULT_PROFILE
            
        if profile not in self.profiles:
            profile = DEFAULT_PROFILE
        
        cleaning_profile = self.profiles[profile]
        cleaned_text, removed_items = cleaning_profile.process(text, context)
        
        return cleaned_text, removed_items, profile
    
    def get_statistics(self, original_text, cleaned_text):
        """
        Get statistics about the cleaning process.
        
        Args:
            original_text: The original text
            cleaned_text: The cleaned text
            
        Returns:
            dict: Statistics about the cleaning
        """
        original_lines = len(original_text.split('\n'))
        cleaned_lines = len(cleaned_text.split('\n'))
        original_words = len(original_text.split())
        cleaned_words = len(cleaned_text.split())
        
        # Calculate reduction percentage
        if len(original_text) > 0:
            reduction_percentage = round((1 - len(cleaned_text) / len(original_text)) * 100, 2)
        else:
            reduction_percentage = 0.0
        
        return {
            'original_chars': len(original_text),
            'cleaned_chars': len(cleaned_text),
            'removed_chars': len(original_text) - len(cleaned_text),
            'original_lines': original_lines,
            'cleaned_lines': cleaned_lines,
            'removed_lines': original_lines - cleaned_lines,
            'original_words': original_words,
            'cleaned_words': cleaned_words,
            'removed_words': original_words - cleaned_words,
            'reduction_percentage': reduction_percentage
        }
