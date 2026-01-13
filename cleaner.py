"""
Text cleaning utilities for Yiddish transcripts.
Removes titles, headings, narrator notes, redactor notes, etc.
"""
import re
from abc import ABC, abstractmethod
from utils import is_valid_gematria

# Default cleaning profile
DEFAULT_PROFILE = 'titles_and_parentheses'

# Exception words - if a snippet contains any of these words, it will NOT be removed
# Add words/phrases that should prevent removal of a snippet
EXCEPTION_WORDS = [
    # Add exception words here, e.g.:
    # 'important term',
    'לחיים'
]

# Force remove words - if a snippet contains any of these words, it WILL be removed
# Add words/phrases that should force removal of a snippet
FORCE_REMOVE_WORDS = [
    # Add force remove words here, e.g.:
    # 'narrator',
    # 'editor note',
    'בס"ד',
    'כ"ק אד"ש צוה'
]


def contains_exception_word(text, exception_words=None):
    """
    Check if text contains any exception words.
    
    Args:
        text: The text to check
        exception_words: List of exception words (uses EXCEPTION_WORDS if None)
        
    Returns:
        bool: True if text contains any exception word
    """
    if exception_words is None:
        exception_words = EXCEPTION_WORDS
    
    if not exception_words:
        return False
    
    text_lower = text.lower()
    for word in exception_words:
        if word.lower() in text_lower:
            return True
    return False


def contains_force_remove_word(text, force_remove_words=None):
    """
    Check if text contains any force remove words.
    
    Args:
        text: The text to check
        force_remove_words: List of force remove words (uses FORCE_REMOVE_WORDS if None)
        
    Returns:
        bool: True if text contains any force remove word
    """
    if force_remove_words is None:
        force_remove_words = FORCE_REMOVE_WORDS
    
    if not force_remove_words:
        return False
    
    text_lower = text.lower()
    for word in force_remove_words:
        if word.lower() in text_lower:
            return True
    return False


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
                # Filter out matches that contain exception words
                actual_matches = [m for m in matches if not contains_exception_word(m if isinstance(m, str) else str(m))]
                
                if actual_matches:
                    removed_items.append({
                        'pattern': description,
                        'matches': actual_matches[:10],
                        'count': len(actual_matches)
                    })
                    
                    if description == 'excessive newlines':
                        cleaned = re.sub(pattern, '\n\n', cleaned, flags=re.MULTILINE)
                    else:
                        # Only remove matches that don't contain exception words
                        def replace_if_no_exception(match):
                            matched_text = match.group(0)
                            if contains_exception_word(matched_text):
                                return matched_text  # Keep it
                            return ''  # Remove it
                        cleaned = re.sub(pattern, replace_if_no_exception, cleaned, flags=re.MULTILINE | re.IGNORECASE)
        
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


class SeifMarkerProcessor(BaseProcessor):
    """Processor that removes seif markers (gematria followed by period) from paragraph beginnings."""
    
    name = "seif_marker"
    description = "Removes seif markers (Hebrew numerals) from paragraph starts"
    
    SEIF_PATTERN = re.compile(r'^([א-ת]+)\.\s*')
    
    def process(self, text, context=None):
        removed_items = []
        seif_positions = []
        
        # Work directly on Word paragraphs from context
        if context and 'paragraphs' in context:
            for meta in context['paragraphs']:
                match = self.SEIF_PATTERN.match(meta['text'])
                if match:
                    potential_gematria = match.group(1)
                    if is_valid_gematria(potential_gematria):
                        # Track position in original text
                        seif_positions.append({
                            'start': meta['start_pos'],
                            'end': meta['start_pos'] + match.end(),
                            'text': match.group(0).strip(),
                            'reason': 'Seif markers (gematria)'
                        })
                        # Update the paragraph text directly
                        meta['text'] = meta['text'][match.end():]
        
        if seif_positions:
            removed_items.append({
                'pattern': 'Seif markers (gematria)',
                'matches': [],  # Empty for pattern matching
                'positions': seif_positions,  # Use positions instead
                'count': len(seif_positions)
            })
        
        # Return original text unchanged - the real work is done on context['paragraphs']
        return text, removed_items


class ForceRemoveProcessor(BaseProcessor):
    """Processor that removes paragraphs containing force remove words."""
    
    name = "force_remove"
    description = "Removes paragraphs containing blocked words/phrases"
    
    def process(self, text, context=None):
        removed_items = []
        force_removed = []
        
        # Use context paragraphs if available (from Word document)
        if context and 'paragraphs' in context:
            kept_paragraphs = []
            for meta in context['paragraphs']:
                if contains_force_remove_word(meta['text']):
                    force_removed.append(meta['text'][:100])
                else:
                    kept_paragraphs.append(meta['text'])
            result_text = '\n'.join(kept_paragraphs)
        else:
            # Fallback: split by newlines
            paragraphs = text.split('\n')
            kept_paragraphs = []
            for para in paragraphs:
                if para.strip() and contains_force_remove_word(para):
                    force_removed.append(para[:100])
                else:
                    kept_paragraphs.append(para)
            result_text = '\n'.join(kept_paragraphs)
        
        if force_removed:
            removed_items.append({
                'pattern': 'Force removed (contains blocked words)',
                'matches': force_removed[:10],
                'count': len(force_removed)
            })
        
        return result_text, removed_items


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
        
        # Track positions for each removal type
        heading_positions = []
        short_positions = []
        large_font_positions = []
        force_positions = []
        
        for meta in paragraphs_meta:
            should_remove = False
            removal_reason = None
            
            # Use the current text (may have been modified by SeifMarkerProcessor)
            current_text = meta['text']
            original_text = meta.get('original_text', current_text)
            
            # Recalculate word count based on current text
            current_word_count = len(current_text.split())
            
            # Check for force remove words - if found, always remove this paragraph
            if contains_force_remove_word(current_text):
                force_positions.append({
                    'start': meta['start_pos'],
                    'end': meta['end_pos'],
                    'text': original_text[:100],
                    'reason': 'Force removed (contains blocked words)'
                })
                continue
            
            # Check for exception words - if found, never remove this paragraph
            if contains_exception_word(current_text):
                kept_paragraphs.append(current_text)
                continue
            
            if meta.get('is_heading_style'):
                should_remove = True
                removal_reason = 'Word heading styles'
                heading_positions.append({
                    'start': meta['start_pos'],
                    'end': meta['end_pos'],
                    'text': original_text[:100],
                    'reason': removal_reason
                })
            
            elif current_word_count < self.min_words:
                should_remove = True
                removal_reason = f'Short paragraphs (< {self.min_words} words)'
                short_positions.append({
                    'start': meta['start_pos'],
                    'end': meta['end_pos'],
                    'text': original_text[:100],
                    'reason': removal_reason
                })
            
            elif meta.get('is_larger_than_normal'):
                should_remove = True
                removal_reason = 'Larger than normal text'
                large_font_positions.append({
                    'start': meta['start_pos'],
                    'end': meta['end_pos'],
                    'text': original_text[:100],
                    'reason': removal_reason
                })
            
            elif meta.get('is_bold') and current_word_count < 15:
                should_remove = True
                removal_reason = 'Word heading styles'
                heading_positions.append({
                    'start': meta['start_pos'],
                    'end': meta['end_pos'],
                    'text': original_text[:100],
                    'reason': removal_reason
                })
            
            if not should_remove:
                kept_paragraphs.append(current_text)
        
        if heading_positions:
            removed_items.append({
                'pattern': 'Word heading styles',
                'matches': [p['text'] for p in heading_positions[:10]],
                'positions': heading_positions,
                'count': len(heading_positions)
            })
        
        if short_positions:
            removed_items.append({
                'pattern': f'Short paragraphs (< {self.min_words} words)',
                'matches': [p['text'] for p in short_positions[:10]],
                'positions': short_positions,
                'count': len(short_positions)
            })
        
        if large_font_positions:
            removed_items.append({
                'pattern': 'Larger than normal text',
                'matches': [p['text'] for p in large_font_positions[:10]],
                'positions': large_font_positions,
                'count': len(large_font_positions)
            })
        
        if force_positions:
            removed_items.append({
                'pattern': 'Force removed (contains blocked words)',
                'matches': [p['text'] for p in force_positions[:10]],
                'positions': force_positions,
                'count': len(force_positions)
            })
        
        return '\n'.join(kept_paragraphs), removed_items


class CleaningProfile:
    """A cleaning profile that chains multiple processors."""
    
    def __init__(self, name, title, description, processors):
        """
        Args:
            name: Profile identifier (internal use)
            title: User-friendly display title
            description: Detailed description of what the profile removes
            processors: List of BaseProcessor instances to run in order
        """
        self.name = name
        self.title = title
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
                title='5710-5711 Transcripts',
                description='Removes titles based on Word heading styles, short paragraphs (less than 5 words), and larger-than-normal font size. Keeps bracketed/parenthetical notes.',
                processors=[
                    SpecialCharsProcessor(),
                    SeifMarkerProcessor(),
                    TitleStyleProcessor(min_words=5, size_threshold=1.2),
                    WhitespaceProcessor(),
                ]
            ),
            'titles_and_parentheses': CleaningProfile(
                name='titles_and_parentheses',
                title='5712+ Transcripts',
                description='Removes titles/headings (Word styles, short paragraphs, large fonts) AND all bracketed [notes] and parenthetical (notes) content.',
                processors=[
                    SpecialCharsProcessor(),
                    SeifMarkerProcessor(),
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
            dict: Dictionary of profile names to their title and description
        """
        return {
            name: {
                'title': profile.title,
                'description': profile.description
            }
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
