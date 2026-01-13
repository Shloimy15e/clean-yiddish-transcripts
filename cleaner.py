"""
Text cleaning utilities for Yiddish transcripts.
Removes titles, headings, narrator notes, redactor notes, etc.

Uses a plugin-based architecture for extensible cleaning processors.
"""

import re
from typing import List, Dict, Any, Optional, Tuple

from registry import ProcessorRegistry

# Import processors to register them
from processors.special_chars import SpecialCharsProcessor
from processors.whitespace import WhitespaceProcessor
from processors.title_style import TitleStyleProcessor
from processors.seif_marker import SeifMarkerProcessor
from processors.regex_processor import RegexProcessor
from processors.force_remove import ForceRemoveProcessor

# Default cleaning profile
DEFAULT_PROFILE = 'titles_and_parentheses'

# Exception patterns - content matching these regex patterns will NOT be removed
# These are regex patterns (not just words)
EXCEPTION_PATTERNS: List[str] = [
    r'לחיים',  # Keep "l'chaim" toasts
    # Add more patterns here, e.g.:
    # r'^ב״ה$',  # Keep standalone "B'H"
    # r'מרן.*הרב',  # Keep references to rabbis
]

# Force remove patterns - content matching these regex patterns WILL be removed
# These are regex patterns (not just words)
FORCE_REMOVE_PATTERNS: List[str] = [
    r'בס"ד',  # Remove "B'S'D" header
    r'כ"ק אד"ש צוה',  # Remove this specific phrase
    # Add more patterns here, e.g.:
    # r'^הערות המתקן:',  # Remove editor notes
    # r'\[.*מתרגם.*\]',  # Remove translator notes
]


# Common regex patterns for removal
TITLE_PATTERNS: List[Tuple[str, str]] = [
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

BRACKET_PATTERNS: List[Tuple[str, str]] = [
    (r'\[.*?\]\s*\(.*?\)', 'brackets followed by parentheses'),
    (r'\[.*?\]', 'bracketed notes'),
    (r'\(.*?\)', 'parenthetical notes'),
]


class CleaningProfile:
    """A cleaning profile that chains multiple processors."""
    
    def __init__(self, name: str, title: str, description: str, 
                 processor_configs: List[Dict[str, Any]]):
        """
        Args:
            name: Profile identifier (internal use)
            title: User-friendly display title
            description: Detailed description of what the profile removes
            processor_configs: List of processor configurations with 'name' and optional 'args'
        """
        self.name = name
        self.title = title
        self.description = description
        self.processor_configs = processor_configs
        self._processors: Optional[List[Any]] = None
    
    def _build_processors(self) -> List[Any]:
        """Build processor instances from configs."""
        processors = []
        for config in self.processor_configs:
            processor_name = config.get('name')
            processor_class = ProcessorRegistry.get(processor_name)
            
            if processor_class:
                args = config.get('args', {})
                processor = processor_class(**args)
                processors.append(processor)
        
        return processors
    
    @property
    def processors(self) -> List[Any]:
        """Get or build processor instances."""
        if self._processors is None:
            self._processors = self._build_processors()
        return self._processors
    
    def process(self, text: str, context: Optional[Dict[str, Any]] = None) -> Tuple[str, List[Dict[str, Any]]]:
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


# Define cleaning profiles with processor configurations
CLEANING_PROFILES: Dict[str, CleaningProfile] = {
            'titles_only': CleaningProfile(
                name='titles_only',
                title='5710-5711 Transcripts',
                description='Removes titles based on Word heading styles, short paragraphs (less than 5 words), and larger-than-normal font size. Keeps bracketed/parenthetical notes.',
        processor_configs=[
            {'name': 'special_chars'},
            {'name': 'seif_marker'},
            {
                'name': 'title_style',
                'args': {
                    'min_words': 5,
                    'size_threshold': 1.2,
                    'exception_patterns': EXCEPTION_PATTERNS,
                    'force_remove_patterns': FORCE_REMOVE_PATTERNS,
                }
            },
            {'name': 'whitespace'},
                ]
            ),
            'titles_and_parentheses': CleaningProfile(
                name='titles_and_parentheses',
                title='5712+ Transcripts',
                description='Removes titles/headings (Word styles, short paragraphs, large fonts) AND all bracketed [notes] and parenthetical (notes) content.',
        processor_configs=[
            {'name': 'special_chars'},
            {'name': 'seif_marker'},
            {
                'name': 'title_style',
                'args': {
                    'min_words': 5,
                    'size_threshold': 1.2,
                    'exception_patterns': EXCEPTION_PATTERNS,
                    'force_remove_patterns': FORCE_REMOVE_PATTERNS,
                }
            },
            {
                'name': 'regex',
                'args': {
                    'patterns': BRACKET_PATTERNS,
                    'exception_patterns': EXCEPTION_PATTERNS,
                }
            },
            {'name': 'whitespace'},
        ]
    ),
}


class TranscriptCleaner:
    """Cleans Yiddish transcripts by removing non-transcript content."""
    
    def __init__(self):
        self.profiles = CLEANING_PROFILES
    
    def get_available_profiles(self) -> Dict[str, Dict[str, str]]:
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
    
    def get_available_processors(self) -> Dict[str, Dict[str, str]]:
        """
        Get list of all registered processors with their info.
        
        Returns:
            dict: Dictionary of processor names to their description and class
        """
        return ProcessorRegistry.get_all_info()
    
    def clean_text(self, text: str, profile: Optional[str] = None, 
                   context: Optional[Dict[str, Any]] = None) -> Tuple[str, List[Dict[str, Any]], str]:
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
    
    def clean_with_processors(self, text: str, processor_names: List[str],
                               context: Optional[Dict[str, Any]] = None) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Clean text using a custom list of processors.
        
        Args:
            text: The original transcript text
            processor_names: List of processor names to apply in order
            context: Optional dict with processing context
            
        Returns:
            tuple: (cleaned_text, removed_items)
        """
        all_removed = []
        current_text = text
        
        for name in processor_names:
            processor_class = ProcessorRegistry.get(name)
            if processor_class:
                # Get default args for certain processors
                args = self._get_processor_args(name)
                processor = processor_class(**args)
                current_text, removed = processor.process(current_text, context)
                all_removed.extend(removed)
        
        return current_text, all_removed
    
    def _get_processor_args(self, processor_name: str) -> Dict[str, Any]:
        """Get default arguments for a processor."""
        default_args = {
            'title_style': {
                'min_words': 5,
                'size_threshold': 1.2,
                'exception_patterns': EXCEPTION_PATTERNS,
                'force_remove_patterns': FORCE_REMOVE_PATTERNS,
            },
            'regex': {
                'patterns': BRACKET_PATTERNS,
                'exception_patterns': EXCEPTION_PATTERNS,
            },
            'force_remove': {
                'force_remove_patterns': FORCE_REMOVE_PATTERNS,
            }
        }
        return default_args.get(processor_name, {})
    
    def get_statistics(self, original_text: str, cleaned_text: str) -> Dict[str, Any]:
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
    
    def add_profile(self, name: str, profile: CleaningProfile) -> None:
        """Add a new cleaning profile."""
        self.profiles[name] = profile
    
    def get_registered_processors(self) -> Dict[str, Dict[str, str]]:
        """Get info about all registered processors."""
        return ProcessorRegistry.get_all_info()
