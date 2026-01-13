"""
Utility functions for Yiddish text processing.
"""

GEMATRIA_VALUES = {
    'א': 1, 'ב': 2, 'ג': 3, 'ד': 4, 'ה': 5,
    'ו': 6, 'ז': 7, 'ח': 8, 'ט': 9, 'י': 10,
    'כ': 20, 'ך': 20, 'ל': 30, 'מ': 40, 'ם': 40,
    'נ': 50, 'ן': 50, 'ס': 60, 'ע': 70, 'פ': 80,
    'ף': 80, 'צ': 90, 'ץ': 90, 'ק': 100, 'ר': 200,
    'ש': 300, 'ת': 400,
}

GEMATRIA_LETTERS = set(GEMATRIA_VALUES.keys())


def is_valid_gematria(text):
    """
    Check if text is a valid gematria (Hebrew numeral).
    
    Args:
        text: String to check
        
    Returns:
        bool: True if text represents a valid gematria
    """
    if not text:
        return False
    
    text = text.strip()
    if not text:
        return False
    
    for char in text:
        if char not in GEMATRIA_LETTERS:
            return False
    
    if len(text) == 1:
        return True
    
    values = [GEMATRIA_VALUES[c] for c in text]
    
    for i in range(len(values) - 1):
        if values[i] < values[i + 1]:
            return False
    
    return True


def get_gematria_value(text):
    """
    Calculate the numeric value of a gematria string.
    
    Args:
        text: Gematria string
        
    Returns:
        int: Numeric value, or 0 if invalid
    """
    if not is_valid_gematria(text):
        return 0
    
    return sum(GEMATRIA_VALUES.get(c, 0) for c in text)


def sanitize_xml_text(text: str) -> str:
    """
    Remove characters that are not valid in XML.
    
    XML 1.0 valid characters: #x9 | #xA | #xD | [#x20-#xD7FF] | [#xE000-#xFFFD]
    
    This prevents corrupted docx files from invalid characters.
    
    Args:
        text: Text to sanitize
        
    Returns:
        str: Text with invalid XML characters removed
    """
    def is_valid_xml_char(c):
        codepoint = ord(c)
        return (
            codepoint == 0x09  # Tab
            or codepoint == 0x0A  # Line feed
            or codepoint == 0x0D  # Carriage return
            or (0x20 <= codepoint <= 0xD7FF)
            or (0xE000 <= codepoint <= 0xFFFD)
        )
    
    return "".join(c for c in text if is_valid_xml_char(c))
