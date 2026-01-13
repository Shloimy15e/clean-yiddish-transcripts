"""
Processor that removes editorial Hebrew content while keeping spoken Hebrew.

In Yiddish transcripts, spoken content naturally contains Hebrew words, pesukim,
and religious terminology. This processor distinguishes between:

SPOKEN Hebrew (KEEP):
- Torah/Tanach quotes (pesukim)
- Religious terms (mitzvah, bracha, tefillah)
- Sefer names when being quoted in speech
- Chassidic phrases and terminology

EDITORIAL Hebrew (REMOVE):
- Source citations with chapter/verse (ראה שמות כ, ג)
- Cross-references (עיין לעיל, ראה שם)
- Position markers (לעיל, לקמן, הנ"ל, כנ"ל)
- Editor notes (הערה, הערת המתקן)
"""

import re
from typing import Tuple, List, Dict, Any, Optional

from registry import ProcessorRegistry
from processors.base import BaseProcessor


@ProcessorRegistry.register
class EditorialHebrewProcessor(BaseProcessor):
    """
    Processor that removes editorial Hebrew patterns while preserving
    spoken Hebrew content like pesukim and religious terminology.
    """
    
    name = "editorial_hebrew"
    description = "Removes editorial Hebrew (citations, references, cross-refs) while keeping spoken Hebrew"
    
    # Patterns that indicate EDITORIAL content (not spoken)
    # These are designed to match editorial vocabulary, not spoken pesukim
    EDITORIAL_PATTERNS = [
        # Cross-references - "see X", "refer to X"
        r'\bראה\s+(?:לעיל|לקמן|שם|הנ"ל|כנ"ל)',  # "see above/below/there/aforementioned"
        r'\bעיי?ן\s+(?:לעיל|לקמן|שם|הנ"ל|כנ"ל|ב[א-ת]+)',  # "refer to above/below/in..."
        r'\bעי[\'׳]\s+[א-ת]+',  # "see (abbreviation)"
        
        # Position/reference markers
        r'\bלעיל\s+(?:סעיף|אות|פרק|סי[\'׳]|סימן)',  # "above section/letter/chapter"
        r'\bלקמן\s+(?:סעיף|אות|פרק|סי[\'׳]|סימן)',  # "below section/letter/chapter"
        r'\bכנ"ל\b',  # "as above" (abbreviation)
        r'\bהנ"ל\b',  # "the aforementioned" (abbreviation)
        r'\bנ"ל\b',   # "aforementioned" (abbreviation)
        r'\bוכנ"ל\b', # "and as above"
        r'\bכדלעיל\b', # "as above"
        r'\bכדלקמן\b', # "as below"
        r'(?<!\S)שם(?=[\s\.,;:]|$)',  # "ibid" - standalone or end of sentence
        
        # Source citations with page/chapter references
        r'\bדף\s+[א-ת]{1,3}[\',׳]?\s*[עב]?[\',׳]?(?:\s*[-–]\s*[א-ת]{1,3}[\',׳]?\s*[עב]?[\',׳]?)?',  # "page [gematria] [a/b]"
        r'\bעמ?[\',׳]\s*\d+',  # "page [number]"
        r'\bע[\'׳]\s*\d+',  # "page [number]" short form
        r'\bפרק\s+[א-ת]{1,3}',  # "chapter [gematria]"
        r'\bסעיף\s+[א-ת]{1,3}',  # "section [gematria]"
        r'\bסי[\'׳]מן?\s+[א-ת]{1,3}',  # "siman [gematria]"
        r'\bאות\s+[א-ת]{1,3}',  # "letter [gematria]"
        r'\bהלכה\s+[א-ת]{1,3}',  # "halacha [gematria]"
        r'\bמשנה\s+[א-ת]{1,3}',  # "mishna [gematria]"
        
        # Editor/transcriber notes
        r'\bהערה\b',  # "note"
        r'\bהע[\'׳]\b',  # "note" abbreviation
        r'\bהערת\s+(?:המתקן|המעתיק|העורך|המהדיר)',  # "note of the corrector/transcriber/editor"
        r'\bהוספת\s+(?:המתקן|המעתיק|העורך)',  # "addition of the..."
        r'\bתיקון\s+(?:המעתיק|העורך)',  # "correction of..."
        
        # Continuation/structural markers
        r'\(המשך\)',  # "(continuation)"
        r'\(סיום\)',  # "(end)"
        r'\(ראה\s+[^)]+\)',  # "(see ...)" in parentheses
        r'\(עיין\s+[^)]+\)',  # "(refer to ...)" in parentheses
        r'\(שם\)',  # "(ibid)" in parentheses
        r'\(הנ"ל\)',  # "(aforementioned)" in parentheses
        r'\(כנ"ל\)',  # "(as above)" in parentheses
        
        # Citations in parentheses (book + chapter + verse format)
        r'\([א-ת]+\s+[א-ת]{1,3}[\',׳]?\s*[,:]?\s*[א-ת]{1,3}\)',  # (Book ch, v) - gematria
        r'\([א-ת]+\s+\d+\s*[,:]\s*\d+\)',  # (Book 1:1) - numbers
    ]
    
    def __init__(self, 
                 additional_patterns: Optional[List[str]] = None,
                 exception_patterns: Optional[List[str]] = None,
                 remove_inline_only: bool = True):
        """
        Args:
            additional_patterns: Extra regex patterns to match as editorial
            exception_patterns: Patterns that should never be removed
            remove_inline_only: If True, only remove inline matches (not whole paragraphs)
        """
        self.patterns = self.EDITORIAL_PATTERNS.copy()
        if additional_patterns:
            self.patterns.extend(additional_patterns)
        
        self.exception_patterns = exception_patterns or []
        self.remove_inline_only = remove_inline_only
        
        # Compile patterns for efficiency
        self._compiled_patterns = [
            re.compile(p, re.IGNORECASE) for p in self.patterns
        ]
        self._compiled_exceptions = [
            re.compile(p, re.IGNORECASE) for p in self.exception_patterns
        ]
    
    def _matches_exception(self, text: str) -> bool:
        """Check if text matches any exception pattern."""
        for pattern in self._compiled_exceptions:
            if pattern.search(text):
                return True
        return False
    
    def _find_editorial_matches(self, text: str) -> List[Dict[str, Any]]:
        """Find all editorial patterns in text and return their positions."""
        matches = []
        
        for pattern in self._compiled_patterns:
            for match in pattern.finditer(text):
                matched_text = match.group(0)
                
                # Skip if matches exception
                if self._matches_exception(matched_text):
                    continue
                
                matches.append({
                    'start': match.start(),
                    'end': match.end(),
                    'text': matched_text,
                    'pattern': pattern.pattern
                })
        
        return matches
    
    def _remove_matches(self, text: str, matches: List[Dict[str, Any]]) -> str:
        """Remove matched editorial content from text."""
        if not matches:
            return text
        
        # Sort by position (reverse order to preserve indices while removing)
        sorted_matches = sorted(matches, key=lambda x: x['start'], reverse=True)
        
        result = text
        for match in sorted_matches:
            # Remove the match and clean up any extra whitespace
            before = result[:match['start']]
            after = result[match['end']:]
            
            # Clean up whitespace: if we're between words, leave one space
            if before and after:
                before = before.rstrip()
                after = after.lstrip()
                if before and after and not before[-1] in '.,;:!?' and not after[0] in '.,;:!?':
                    result = before + ' ' + after
                else:
                    result = before + after
            else:
                result = before + after
        
        return result
    
    def process(self, text: str, context: Optional[Dict[str, Any]] = None) -> Tuple[str, List[Dict[str, Any]]]:
        removed_items = []
        all_matches = []
        
        # Process paragraph by paragraph if context available
        if context and 'paragraphs' in context:
            for meta in context['paragraphs']:
                para_text = meta.get('text', '')
                matches = self._find_editorial_matches(para_text)
                
                if matches:
                    for m in matches:
                        # Adjust positions to be relative to full text
                        m['start'] += meta.get('start_pos', 0)
                        m['end'] += meta.get('start_pos', 0)
                    all_matches.extend(matches)
                    
                    # Update paragraph text
                    meta['text'] = self._remove_matches(para_text, 
                        self._find_editorial_matches(para_text))
        
        # Also process the raw text
        raw_matches = self._find_editorial_matches(text)
        cleaned_text = self._remove_matches(text, raw_matches)
        
        # Use raw matches for position tracking if no context
        if not all_matches:
            all_matches = raw_matches
        
        if all_matches:
            # Group by pattern type for cleaner reporting
            pattern_groups = {}
            for m in all_matches:
                key = 'Editorial Hebrew references'
                if key not in pattern_groups:
                    pattern_groups[key] = []
                pattern_groups[key].append(m)
            
            for pattern_name, matches in pattern_groups.items():
                removed_items.append({
                    'pattern': pattern_name,
                    'matches': [m['text'] for m in matches[:10]],
                    'positions': [{
                        'start': m['start'],
                        'end': m['end'],
                        'text': m['text'],
                        'reason': 'Editorial Hebrew reference'
                    } for m in matches],
                    'count': len(matches)
                })
        
        return cleaned_text, removed_items
