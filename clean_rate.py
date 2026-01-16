"""
Clean Rate Scoring System.

Calculates a confidence score (0-100) for how "clean" a document processing was.
Higher score = more confident that the correct content was removed.
Lower score = more uncertainty about whether removed content should have been kept.

The system is modular - rules can be added, modified, or removed easily.
"""

from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod


class CleanRateRule(ABC):
    """Base class for clean rate scoring rules."""
    
    # Rule metadata
    name: str = "base_rule"
    description: str = "Base rule"
    
    # Maximum penalty this rule can apply (for capping)
    max_penalty: int = 100
    
    @abstractmethod
    def calculate_penalty(self, removed_item: Dict[str, Any], 
                          context: Optional[Dict[str, Any]] = None) -> int:
        """
        Calculate penalty points for a removed item.
        
        Args:
            removed_item: Dict with info about what was removed, including:
                - 'text': The removed text
                - 'reason': Why it was removed (processor name + details)
                - 'processor': Which processor removed it
                - 'confidence': Optional confidence level from processor
                - Other processor-specific fields
            context: Optional processing context (paragraph styles, etc.)
            
        Returns:
            int: Penalty points to subtract (0 = no penalty, higher = more uncertain)
        """
        pass
    
    def applies_to(self, removed_item: Dict[str, Any]) -> bool:
        """Check if this rule applies to the given removed item."""
        return True


class BracketRemovalRule(CleanRateRule):
    """
    Penalize removal of bracketed content.
    
    Brackets are often editorial notes, but sometimes contain spoken content.
    Inline brackets are more likely editorial; full paragraphs less certain.
    """
    
    name = "bracket_removal"
    description = "Penalizes removal of bracketed content (uncertain if editorial or spoken)"
    max_penalty = 30
    
    # Points per bracket removal
    INLINE_BRACKET_PENALTY = 2  # Inline brackets are usually editorial
    FULL_PARAGRAPH_BRACKET_PENALTY = 8  # Full bracketed paragraphs more uncertain
    
    def applies_to(self, removed_item: Dict[str, Any]) -> bool:
        reason = removed_item.get('reason', '').lower()
        processor = removed_item.get('processor', '').lower()
        return 'bracket' in reason or 'bracket' in processor
    
    def calculate_penalty(self, removed_item: Dict[str, Any],
                          context: Optional[Dict[str, Any]] = None) -> int:
        if not self.applies_to(removed_item):
            return 0
        
        text = removed_item.get('text', '')
        reason = removed_item.get('reason', '').lower()
        
        # Check if it's inline or full paragraph
        if 'inline' in reason:
            return self.INLINE_BRACKET_PENALTY
        elif 'full paragraph' in reason or 'entire paragraph' in reason:
            return self.FULL_PARAGRAPH_BRACKET_PENALTY
        else:
            # Default bracket penalty
            # Longer text = more uncertain
            if len(text) > 100:
                return 5
            return self.INLINE_BRACKET_PENALTY


class ParenthesesRemovalRule(CleanRateRule):
    """
    Penalize removal of parenthetical content.
    
    In Yiddish transcripts, most parenthetical content is spoken.
    Removing it is risky unless it matches known editorial patterns.
    """
    
    name = "parentheses_removal"
    description = "Penalizes removal of parenthetical content (often spoken in Yiddish transcripts)"
    max_penalty = 40
    
    CITATION_PENALTY = 1  # Citations are clearly editorial
    STAGE_DIRECTION_PENALTY = 2  # Stage directions usually editorial
    UNKNOWN_PARENS_PENALTY = 6  # Unknown parenthetical - risky
    
    def applies_to(self, removed_item: Dict[str, Any]) -> bool:
        reason = removed_item.get('reason', '').lower()
        processor = removed_item.get('processor', '').lower()
        return 'parenthes' in reason or 'parenthes' in processor or 'parens' in reason
    
    def calculate_penalty(self, removed_item: Dict[str, Any],
                          context: Optional[Dict[str, Any]] = None) -> int:
        if not self.applies_to(removed_item):
            return 0
        
        reason = removed_item.get('reason', '').lower()
        
        if 'citation' in reason or 'source' in reason or 'reference' in reason:
            return self.CITATION_PENALTY
        elif 'stage direction' in reason or 'editorial' in reason:
            return self.STAGE_DIRECTION_PENALTY
        else:
            return self.UNKNOWN_PARENS_PENALTY


class TitleStyleRemovalRule(CleanRateRule):
    """
    Reward (no penalty) for removing content with clear title indicators.
    
    High confidence removals:
    - Word heading styles (Heading 1, Title, etc.)
    - Large font combined with bold
    - Very short "paragraphs" (likely headers)
    
    Lower confidence:
    - Just bold text
    - Just large font
    """
    
    name = "title_style_removal"
    description = "Scores based on confidence of title detection"
    max_penalty = 15
    
    def applies_to(self, removed_item: Dict[str, Any]) -> bool:
        reason = removed_item.get('reason', '').lower()
        processor = removed_item.get('processor', '').lower()
        return 'title' in reason or 'title' in processor or 'heading' in reason
    
    def calculate_penalty(self, removed_item: Dict[str, Any],
                          context: Optional[Dict[str, Any]] = None) -> int:
        if not self.applies_to(removed_item):
            return 0
        
        reason = removed_item.get('reason', '').lower()
        
        # Check confidence indicators
        has_heading_style = 'heading style' in reason or 'word style' in reason
        has_large_font = 'large font' in reason or 'larger than' in reason
        has_bold = 'bold' in reason
        is_short = 'short paragraph' in reason or 'few words' in reason
        
        # Count confidence indicators
        confidence_indicators = sum([has_heading_style, has_large_font, has_bold, is_short])
        
        if confidence_indicators >= 3:
            return 0  # Very confident - no penalty
        elif confidence_indicators == 2:
            return 1  # Confident
        elif confidence_indicators == 1:
            return 3  # Somewhat confident
        else:
            return 5  # Low confidence title removal


class ForceRemoveRule(CleanRateRule):
    """
    No penalty for force-removed patterns.
    
    Force remove patterns are explicitly configured by the user,
    so we have high confidence they should be removed.
    """
    
    name = "force_remove"
    description = "No penalty for explicitly configured removal patterns"
    max_penalty = 0
    
    def applies_to(self, removed_item: Dict[str, Any]) -> bool:
        reason = removed_item.get('reason', '').lower()
        processor = removed_item.get('processor', '').lower()
        return 'force' in reason or 'force' in processor
    
    def calculate_penalty(self, removed_item: Dict[str, Any],
                          context: Optional[Dict[str, Any]] = None) -> int:
        return 0  # User explicitly wanted this removed


class SeifMarkerRemovalRule(CleanRateRule):
    """
    Minimal penalty for seif marker removal.
    
    Seif markers (Hebrew gematria numbering) are clearly structural,
    not spoken content. High confidence removal.
    """
    
    name = "seif_marker_removal"
    description = "Minimal penalty for seif/gematria markers (clearly structural)"
    max_penalty = 5
    
    def applies_to(self, removed_item: Dict[str, Any]) -> bool:
        reason = removed_item.get('reason', '').lower()
        processor = removed_item.get('processor', '').lower()
        return 'seif' in reason or 'seif' in processor or 'gematria' in reason
    
    def calculate_penalty(self, removed_item: Dict[str, Any],
                          context: Optional[Dict[str, Any]] = None) -> int:
        return 0  # Seif markers are clearly not spoken


class EditorialHebrewRemovalRule(CleanRateRule):
    """
    Score based on editorial Hebrew detection confidence.
    
    Some Hebrew is clearly editorial (citations, cross-references).
    Some is uncertain (could be quotes or spoken content).
    """
    
    name = "editorial_hebrew_removal"
    description = "Scores based on editorial Hebrew detection confidence"
    max_penalty = 25
    
    def applies_to(self, removed_item: Dict[str, Any]) -> bool:
        reason = removed_item.get('reason', '').lower()
        processor = removed_item.get('processor', '').lower()
        return 'editorial' in reason or 'editorial' in processor or 'hebrew' in processor
    
    def calculate_penalty(self, removed_item: Dict[str, Any],
                          context: Optional[Dict[str, Any]] = None) -> int:
        if not self.applies_to(removed_item):
            return 0
        
        reason = removed_item.get('reason', '').lower()
        
        # High confidence editorial patterns
        if any(pattern in reason for pattern in ['citation', 'reference', 'cross-ref', 'see ', 'עיין', 'ראה']):
            return 0
        elif 'position marker' in reason:
            return 1
        else:
            return 4  # Unknown editorial Hebrew


class SpecialCharsRemovalRule(CleanRateRule):
    """
    No penalty for special character removal.
    
    Zero-width spaces, BOMs, and invisible Unicode are never spoken content.
    """
    
    name = "special_chars_removal"
    description = "No penalty for invisible character removal"
    max_penalty = 0
    
    def applies_to(self, removed_item: Dict[str, Any]) -> bool:
        reason = removed_item.get('reason', '').lower()
        processor = removed_item.get('processor', '').lower()
        return 'special' in processor or 'unicode' in reason or 'zero-width' in reason
    
    def calculate_penalty(self, removed_item: Dict[str, Any],
                          context: Optional[Dict[str, Any]] = None) -> int:
        return 0  # Invisible characters are never spoken


class WhitespaceRemovalRule(CleanRateRule):
    """
    No penalty for whitespace normalization.
    
    Normalizing whitespace doesn't remove content.
    """
    
    name = "whitespace_removal"
    description = "No penalty for whitespace normalization"
    max_penalty = 0
    
    def applies_to(self, removed_item: Dict[str, Any]) -> bool:
        reason = removed_item.get('reason', '').lower()
        processor = removed_item.get('processor', '').lower()
        return 'whitespace' in processor or 'whitespace' in reason
    
    def calculate_penalty(self, removed_item: Dict[str, Any],
                          context: Optional[Dict[str, Any]] = None) -> int:
        return 0


class RegexRemovalRule(CleanRateRule):
    """
    Moderate penalty for generic regex removals.
    
    Regex patterns are user-defined but can be broad.
    Apply moderate penalty unless pattern is well-known.
    """
    
    name = "regex_removal"
    description = "Moderate penalty for regex pattern removals"
    max_penalty = 20
    
    # Known safe patterns (no penalty)
    SAFE_PATTERNS = ['timestamp', 'page number', 'separator']
    
    def applies_to(self, removed_item: Dict[str, Any]) -> bool:
        processor = removed_item.get('processor', '').lower()
        return processor == 'regex'
    
    def calculate_penalty(self, removed_item: Dict[str, Any],
                          context: Optional[Dict[str, Any]] = None) -> int:
        if not self.applies_to(removed_item):
            return 0
        
        reason = removed_item.get('reason', '').lower()
        
        # Check for known safe patterns
        if any(safe in reason for safe in self.SAFE_PATTERNS):
            return 0
        
        return 4  # Generic regex removal


class UnknownRemovalRule(CleanRateRule):
    """
    Default penalty for unrecognized removals.
    
    If we don't recognize the removal type, apply moderate penalty.
    """
    
    name = "unknown_removal"
    description = "Default penalty for unrecognized removal types"
    max_penalty = 30
    
    def applies_to(self, removed_item: Dict[str, Any]) -> bool:
        return True  # Fallback rule
    
    def calculate_penalty(self, removed_item: Dict[str, Any],
                          context: Optional[Dict[str, Any]] = None) -> int:
        # This should only be called if no other rule matched
        return 3


# =============================================================================
# Clean Rate Calculator
# =============================================================================

class CleanRateCalculator:
    """
    Calculates clean rate scores using registered rules.
    
    The calculator maintains a list of rules that are applied to each removed item.
    Rules are checked in order, and the first matching rule's penalty is used.
    """
    
    # Default rules in priority order (first match wins)
    DEFAULT_RULES: List[CleanRateRule] = [
        SpecialCharsRemovalRule(),
        WhitespaceRemovalRule(),
        SeifMarkerRemovalRule(),
        ForceRemoveRule(),
        TitleStyleRemovalRule(),
        BracketRemovalRule(),
        ParenthesesRemovalRule(),
        EditorialHebrewRemovalRule(),
        RegexRemovalRule(),
        UnknownRemovalRule(),  # Fallback - must be last
    ]
    
    def __init__(self, rules: Optional[List[CleanRateRule]] = None):
        """
        Initialize the calculator with rules.
        
        Args:
            rules: List of rules to use. If None, uses DEFAULT_RULES.
        """
        self.rules = rules if rules is not None else self.DEFAULT_RULES.copy()
    
    def add_rule(self, rule: CleanRateRule, priority: Optional[int] = None) -> None:
        """
        Add a rule to the calculator.
        
        Args:
            rule: The rule to add
            priority: Position in the rule list (lower = higher priority).
                     If None, adds before the fallback rule.
        """
        if priority is not None:
            self.rules.insert(priority, rule)
        else:
            # Insert before the last rule (fallback)
            self.rules.insert(-1, rule)
    
    def remove_rule(self, rule_name: str) -> bool:
        """
        Remove a rule by name.
        
        Args:
            rule_name: Name of the rule to remove
            
        Returns:
            bool: True if rule was found and removed
        """
        for i, rule in enumerate(self.rules):
            if rule.name == rule_name:
                self.rules.pop(i)
                return True
        return False
    
    def get_rule_info(self) -> List[Dict[str, Any]]:
        """Get information about all registered rules."""
        return [
            {
                'name': rule.name,
                'description': rule.description,
                'max_penalty': rule.max_penalty,
            }
            for rule in self.rules
        ]
    
    def calculate(self, removed_items: List[Dict[str, Any]],
                  statistics: Optional[Dict[str, Any]] = None,
                  context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Calculate the clean rate for a processed document.
        
        Args:
            removed_items: List of removed item dicts from processors
            statistics: Optional processing statistics
            context: Optional processing context
            
        Returns:
            Dict with:
                - 'score': Final clean rate (0-100)
                - 'penalties': List of penalties applied
                - 'total_penalty': Total penalty points
                - 'details': Detailed breakdown
        """
        total_penalty = 0
        penalties = []
        
        for item in removed_items:
            # Find first matching rule
            for rule in self.rules:
                if rule.applies_to(item):
                    penalty = rule.calculate_penalty(item, context)
                    if penalty > 0:
                        total_penalty += penalty
                        penalties.append({
                            'rule': rule.name,
                            'penalty': penalty,
                            'text_preview': (item.get('text', '')[:50] + '...') 
                                           if len(item.get('text', '')) > 50 
                                           else item.get('text', ''),
                            'reason': item.get('reason', 'unknown'),
                        })
                    break  # First matching rule wins
        
        # Calculate final score (100 - penalties, capped at 0)
        score = max(0, 100 - total_penalty)
        
        # Build result
        result = {
            'score': score,
            'total_penalty': total_penalty,
            'penalties': penalties,
            'items_processed': len(removed_items),
            'items_penalized': len(penalties),
        }
        
        # Add category based on score
        if score >= 90:
            result['category'] = 'excellent'
            result['description'] = 'Very high confidence in cleaning accuracy'
        elif score >= 75:
            result['category'] = 'good'
            result['description'] = 'Good confidence in cleaning accuracy'
        elif score >= 50:
            result['category'] = 'moderate'
            result['description'] = 'Moderate confidence - review recommended'
        elif score >= 25:
            result['category'] = 'low'
            result['description'] = 'Low confidence - manual review suggested'
        else:
            result['category'] = 'poor'
            result['description'] = 'Very low confidence - significant manual review needed'
        
        return result


# Global calculator instance
_calculator = CleanRateCalculator()


def calculate_clean_rate(removed_items: List[Dict[str, Any]],
                         statistics: Optional[Dict[str, Any]] = None,
                         context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Convenience function to calculate clean rate using the global calculator.
    
    Args:
        removed_items: List of removed item dicts from processors
        statistics: Optional processing statistics
        context: Optional processing context
        
    Returns:
        Dict with clean rate score and details
    """
    return _calculator.calculate(removed_items, statistics, context)


def get_clean_rate_rules() -> List[Dict[str, Any]]:
    """Get information about all registered clean rate rules."""
    return _calculator.get_rule_info()
