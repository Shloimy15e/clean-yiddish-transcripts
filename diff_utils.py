"""
Diff utilities for comparing original and cleaned text.
Provides line-by-line and word-by-word diff generation.
"""
import difflib
from typing import List, Dict, Tuple
import re


def generate_line_diff(original: str, cleaned: str) -> Dict:
    """
    Generate a line-by-line diff between original and cleaned text.
    
    Args:
        original: The original text
        cleaned: The cleaned/modified text
        
    Returns:
        Dict containing diff information with line-by-line changes
    """
    original_lines = original.splitlines(keepends=True)
    cleaned_lines = cleaned.splitlines(keepends=True)
    
    # Use unified diff for a clear view
    diff = list(difflib.unified_diff(
        original_lines, 
        cleaned_lines,
        fromfile='Original',
        tofile='Cleaned',
        lineterm=''
    ))
    
    # Generate side-by-side comparison data
    matcher = difflib.SequenceMatcher(None, original_lines, cleaned_lines)
    
    changes = []
    stats = {
        'lines_removed': 0,
        'lines_added': 0,
        'lines_modified': 0,
        'lines_unchanged': 0
    }
    
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == 'equal':
            for idx, line in enumerate(original_lines[i1:i2]):
                changes.append({
                    'type': 'unchanged',
                    'original_line': i1 + idx + 1,
                    'cleaned_line': j1 + idx + 1,
                    'original': line.rstrip('\n\r'),
                    'cleaned': line.rstrip('\n\r')
                })
                stats['lines_unchanged'] += 1
                
        elif tag == 'replace':
            # Lines were modified - show both old and new
            orig_chunk = original_lines[i1:i2]
            clean_chunk = cleaned_lines[j1:j2]
            
            # Match lines within the chunk for better granularity
            max_len = max(len(orig_chunk), len(clean_chunk))
            for idx in range(max_len):
                orig_line = orig_chunk[idx].rstrip('\n\r') if idx < len(orig_chunk) else None
                clean_line = clean_chunk[idx].rstrip('\n\r') if idx < len(clean_chunk) else None
                
                if orig_line is not None and clean_line is not None:
                    # Both exist - it's a modification
                    word_diff = generate_word_diff(orig_line, clean_line)
                    changes.append({
                        'type': 'modified',
                        'original_line': i1 + idx + 1 if idx < len(orig_chunk) else None,
                        'cleaned_line': j1 + idx + 1 if idx < len(clean_chunk) else None,
                        'original': orig_line,
                        'cleaned': clean_line,
                        'word_diff': word_diff
                    })
                    stats['lines_modified'] += 1
                elif orig_line is not None:
                    # Only original exists - it was removed
                    changes.append({
                        'type': 'removed',
                        'original_line': i1 + idx + 1,
                        'cleaned_line': None,
                        'original': orig_line,
                        'cleaned': None
                    })
                    stats['lines_removed'] += 1
                else:
                    # Only cleaned exists - it was added
                    changes.append({
                        'type': 'added',
                        'original_line': None,
                        'cleaned_line': j1 + idx + 1,
                        'original': None,
                        'cleaned': clean_line
                    })
                    stats['lines_added'] += 1
                    
        elif tag == 'delete':
            for idx, line in enumerate(original_lines[i1:i2]):
                changes.append({
                    'type': 'removed',
                    'original_line': i1 + idx + 1,
                    'cleaned_line': None,
                    'original': line.rstrip('\n\r'),
                    'cleaned': None
                })
                stats['lines_removed'] += 1
                
        elif tag == 'insert':
            for idx, line in enumerate(cleaned_lines[j1:j2]):
                changes.append({
                    'type': 'added',
                    'original_line': None,
                    'cleaned_line': j1 + idx + 1,
                    'original': None,
                    'cleaned': line.rstrip('\n\r')
                })
                stats['lines_added'] += 1
    
    return {
        'changes': changes,
        'stats': stats,
        'unified_diff': '\n'.join(diff)
    }


def generate_word_diff(original_line: str, cleaned_line: str) -> List[Dict]:
    """
    Generate word-by-word diff for a single line.
    
    Returns list of word segments with their change type.
    """
    # Split into words while preserving whitespace
    def tokenize(text):
        # Split on word boundaries, keeping punctuation attached
        return re.findall(r'\S+|\s+', text)
    
    orig_words = tokenize(original_line)
    clean_words = tokenize(cleaned_line)
    
    matcher = difflib.SequenceMatcher(None, orig_words, clean_words)
    
    result = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == 'equal':
            result.append({
                'type': 'unchanged',
                'text': ''.join(orig_words[i1:i2])
            })
        elif tag == 'replace':
            if i1 < i2:
                result.append({
                    'type': 'removed',
                    'text': ''.join(orig_words[i1:i2])
                })
            if j1 < j2:
                result.append({
                    'type': 'added',
                    'text': ''.join(clean_words[j1:j2])
                })
        elif tag == 'delete':
            result.append({
                'type': 'removed',
                'text': ''.join(orig_words[i1:i2])
            })
        elif tag == 'insert':
            result.append({
                'type': 'added',
                'text': ''.join(clean_words[j1:j2])
            })
    
    return result


def generate_html_diff(original: str, cleaned: str, context_lines: int = 3) -> str:
    """
    Generate an HTML representation of the diff.
    
    Args:
        original: Original text
        cleaned: Cleaned text
        context_lines: Number of unchanged lines to show around changes
        
    Returns:
        HTML string with styled diff
    """
    diff_data = generate_line_diff(original, cleaned)
    
    html_parts = ['<div class="diff-container">']
    
    # Add summary stats
    stats = diff_data['stats']
    html_parts.append(f'''
        <div class="diff-stats">
            <span class="stat-removed">−{stats['lines_removed']} removed</span>
            <span class="stat-added">+{stats['lines_added']} added</span>
            <span class="stat-modified">~{stats['lines_modified']} modified</span>
        </div>
    ''')
    
    html_parts.append('<div class="diff-content">')
    
    for change in diff_data['changes']:
        change_type = change['type']
        orig_num = change.get('original_line', '')
        clean_num = change.get('cleaned_line', '')
        
        if change_type == 'unchanged':
            html_parts.append(f'''
                <div class="diff-line unchanged">
                    <span class="line-num">{orig_num}</span>
                    <span class="line-num">{clean_num}</span>
                    <span class="line-content">{_escape_html(change['original'])}</span>
                </div>
            ''')
        elif change_type == 'removed':
            html_parts.append(f'''
                <div class="diff-line removed">
                    <span class="line-num">{orig_num}</span>
                    <span class="line-num"></span>
                    <span class="line-content">−{_escape_html(change['original'])}</span>
                </div>
            ''')
        elif change_type == 'added':
            html_parts.append(f'''
                <div class="diff-line added">
                    <span class="line-num"></span>
                    <span class="line-num">{clean_num}</span>
                    <span class="line-content">+{_escape_html(change['cleaned'])}</span>
                </div>
            ''')
        elif change_type == 'modified':
            # Show inline word diff
            word_diff_html = _render_word_diff(change.get('word_diff', []))
            html_parts.append(f'''
                <div class="diff-line modified">
                    <span class="line-num">{orig_num}</span>
                    <span class="line-num">{clean_num}</span>
                    <span class="line-content">{word_diff_html}</span>
                </div>
            ''')
    
    html_parts.append('</div></div>')
    
    return ''.join(html_parts)


def _escape_html(text: str) -> str:
    """Escape HTML special characters."""
    if text is None:
        return ''
    return (text
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('"', '&quot;')
            .replace("'", '&#39;'))


def _render_word_diff(word_diff: List[Dict]) -> str:
    """Render word diff as HTML with inline styling."""
    parts = []
    for segment in word_diff:
        text = _escape_html(segment['text'])
        if segment['type'] == 'unchanged':
            parts.append(text)
        elif segment['type'] == 'removed':
            parts.append(f'<del class="word-removed">{text}</del>')
        elif segment['type'] == 'added':
            parts.append(f'<ins class="word-added">{text}</ins>')
    return ''.join(parts)


def get_diff_summary(original: str, cleaned: str) -> Dict:
    """
    Get a quick summary of changes between original and cleaned text.
    
    Returns basic statistics without full diff details.
    """
    original_lines = original.splitlines()
    cleaned_lines = cleaned.splitlines()
    
    original_words = len(original.split())
    cleaned_words = len(cleaned.split())
    
    original_chars = len(original)
    cleaned_chars = len(cleaned)
    
    # Quick line comparison
    matcher = difflib.SequenceMatcher(None, original_lines, cleaned_lines)
    similarity = matcher.ratio()
    
    return {
        'original_lines': len(original_lines),
        'cleaned_lines': len(cleaned_lines),
        'original_words': original_words,
        'cleaned_words': cleaned_words,
        'original_chars': original_chars,
        'cleaned_chars': cleaned_chars,
        'words_removed': original_words - cleaned_words,
        'lines_changed': len(original_lines) - len(cleaned_lines),
        'similarity_ratio': round(similarity * 100, 1)
    }
