"""
Document format converter for .doc to .docx conversion.

Supports LibreOffice (Linux/macOS) and Word COM automation (Windows).
"""

import shutil
import subprocess
import tempfile
from pathlib import Path

# Try to import pywin32 (Windows only)
try:
    import win32com.client  # type: ignore
    import pythoncom  # type: ignore
    _PYWIN32_AVAILABLE = True
except ImportError:
    _PYWIN32_AVAILABLE = False
    win32com = None  # type: ignore
    pythoncom = None  # type: ignore


def _check_libreoffice_available() -> bool:
    """Check if LibreOffice is available for .doc conversion."""
    # Use shutil.which for cross-platform compatibility
    return shutil.which('lowriter') is not None


def _check_word_available() -> bool:
    """Check if Microsoft Word is available via COM (Windows only)."""
    return _PYWIN32_AVAILABLE


# Module-level availability flags (evaluated once at import)
LIBREOFFICE_AVAILABLE = _check_libreoffice_available()
WORD_AVAILABLE = _check_word_available()


class DocConverter:
    """
    Converts .doc files to .docx format.
    
    Uses LibreOffice on Linux/macOS or Word COM automation on Windows.
    """
    
    def __init__(self):
        """Initialize the converter."""
    
    def convert(self, doc_path: str) -> str:
        """
        Convert a .doc file to .docx format.
        
        Args:
            doc_path: Path to the .doc file
            
        Returns:
            str: Path to the temporary .docx file (caller must clean up)
            
        Raises:
            ValueError: If the file is not a .doc file
            RuntimeError: If no conversion method is available or conversion fails
        """
        path = Path(doc_path)
        
        if path.suffix.lower() == '.docx':
            # Already a .docx file, return as-is
            return str(path)
        
        if path.suffix.lower() != '.doc':
            raise ValueError(f"Expected .doc file, got: {path.suffix}")
        
        if not path.exists():
            raise FileNotFoundError(f"File not found: {doc_path}")
        
        # Try LibreOffice first (works on Linux/macOS/Windows if installed)
        if LIBREOFFICE_AVAILABLE:
            return self._convert_with_libreoffice(path)
        
        # Fall back to Word COM (Windows only)
        if WORD_AVAILABLE:
            return self._convert_with_word_com(path)
        
        raise RuntimeError(
            "No .doc conversion method available. "
            "On Linux/macOS: Install LibreOffice. "
            "On Windows: Install Microsoft Word and pywin32 ('pip install pywin32')."
        )
    
    def _convert_with_libreoffice(self, doc_path: Path) -> str:
        """
        Convert .doc to .docx using LibreOffice.
        
        Args:
            doc_path: Path to the .doc file
            
        Returns:
            str: Path to the temporary .docx file
        """
        # Create temp directory for output
        temp_dir = tempfile.mkdtemp()
        
        try:
            # Run LibreOffice conversion (check=False because we handle returncode)
            result = subprocess.run(
                [
                    'lowriter',
                    '--headless',
                    '--convert-to', 'docx',
                    '--outdir', temp_dir,
                    str(doc_path.absolute())
                ],
                capture_output=True,
                text=True,
                timeout=60,
                check=False
            )
            
            if result.returncode != 0:
                shutil.rmtree(temp_dir, ignore_errors=True)
                raise RuntimeError(f"LibreOffice conversion failed: {result.stderr}")
            
            # LibreOffice outputs to --outdir with original filename + .docx
            expected_output = Path(temp_dir) / doc_path.with_suffix('.docx').name
            
            if not expected_output.exists():
                shutil.rmtree(temp_dir, ignore_errors=True)
                raise RuntimeError(
                    f"LibreOffice conversion completed but output file not found. "
                    f"Expected: {expected_output}"
                )
            
            # Move to a proper temp file location
            final_temp = tempfile.NamedTemporaryFile(delete=False, suffix='.docx')
            final_temp.close()
            shutil.move(str(expected_output), final_temp.name)
            
            # Clean up temp directory
            shutil.rmtree(temp_dir, ignore_errors=True)
            
            return final_temp.name
            
        except subprocess.TimeoutExpired as e:
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise RuntimeError("LibreOffice conversion timed out after 60 seconds") from e
        except RuntimeError:
            raise
        except Exception as e:
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise RuntimeError(f"LibreOffice conversion failed: {e}") from e
    
    def _convert_with_word_com(self, doc_path: Path) -> str:
        """
        Convert .doc to .docx using Word COM automation (Windows only).
        
        Args:
            doc_path: Path to the .doc file
            
        Returns:
            str: Path to the temporary .docx file
        """
        if not _PYWIN32_AVAILABLE:
            raise RuntimeError("pywin32 is not installed")
        
        # Create temp file for output
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.docx')
        temp_file.close()
        temp_path = temp_file.name
        
        word = None
        com_initialized = False
        
        try:
            # Initialize COM for this thread
            pythoncom.CoInitialize()
            com_initialized = True
            
            # Create Word application
            word = win32com.client.Dispatch("Word.Application")
            word.Visible = False
            word.DisplayAlerts = False
            
            # Open the .doc file
            doc = word.Documents.Open(str(doc_path.absolute()))
            
            # Save as .docx (FileFormat=16 is wdFormatXMLDocument)
            doc.SaveAs(temp_path, FileFormat=16)
            doc.Close(SaveChanges=False)
            
            return temp_path
            
        except Exception as e:
            # Clean up temp file on failure
            if Path(temp_path).exists():
                Path(temp_path).unlink()
            raise RuntimeError(f"Word COM conversion failed: {e}") from e
        finally:
            # Clean up Word application
            if word is not None:
                try:
                    word.Quit()
                except Exception:
                    pass
            
            # Uninitialize COM
            if com_initialized:
                try:
                    pythoncom.CoUninitialize()
                except Exception:
                    pass


def convert_doc_to_docx(doc_path: str) -> str:
    """
    Convenience function to convert a .doc file to .docx.
    
    Args:
        doc_path: Path to the .doc file
        
    Returns:
        str: Path to the temporary .docx file (caller must clean up)
        
    Raises:
        ValueError: If the file is not a .doc file
        RuntimeError: If conversion fails
    """
    converter = DocConverter()
    return converter.convert(doc_path)


def is_conversion_available() -> bool:
    """Check if any conversion method is available."""
    return LIBREOFFICE_AVAILABLE or WORD_AVAILABLE


def get_available_methods() -> list[str]:
    """Get list of available conversion methods."""
    methods = []
    if LIBREOFFICE_AVAILABLE:
        methods.append('libreoffice')
    if WORD_AVAILABLE:
        methods.append('word_com')
    return methods
