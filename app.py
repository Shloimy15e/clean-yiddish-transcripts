"""
Flask web application for cleaning Yiddish transcripts.
"""
from dotenv import load_dotenv
import os
import shutil
from flask import Flask, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename
from document_processor import DocumentProcessor
from drive_downloader import DriveDownloader
from cleaner import TranscriptCleaner
from sheet_processor import SheetProcessor
from llm_processor import process_with_llm, get_default_prompt, get_available_providers

load_dotenv()  # Load .env file at the top of app.py


app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['TEMP_FOLDER'] = 'temp'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['ALLOWED_EXTENSIONS'] = {'docx', 'doc'}

# Ensure folders exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['TEMP_FOLDER'], exist_ok=True)

processor = DocumentProcessor()

# Cache for cleaning profiles to avoid repeated instantiation
_cached_profiles = None


def get_cleaner_profiles():
    """Get available cleaning profiles (cached)."""
    global _cached_profiles
    if _cached_profiles is None:
        cleaner = TranscriptCleaner()
        _cached_profiles = cleaner.get_available_profiles()
    return _cached_profiles


def allowed_file(filename):
    """Check if file has allowed extension."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


@app.route('/')
def index():
    """Render the main page."""
    return render_template('index.html')


@app.route('/profiles', methods=['GET'])
def get_profiles():
    """Get available cleaning profiles."""
    profiles = get_cleaner_profiles()
    return jsonify(profiles)


@app.route('/processors', methods=['GET'])
def get_processors():
    """Get available processing plugins."""
    cleaner = TranscriptCleaner()
    processors = cleaner.get_available_processors()
    return jsonify(processors)


@app.route('/formats', methods=['GET'])
def get_formats():
    """Get available output formats."""
    formats = processor.get_available_formats()
    return jsonify(formats)


@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle file upload and processing."""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'Invalid file type. Please upload a .docx or .doc file'}), 400
        
        # Get processors list from form data (comma-separated or JSON array)
        processors_str = request.form.get('processors', '')
        if processors_str:
            # Parse as JSON array or comma-separated
            import json
            try:
                processors_list = json.loads(processors_str)
            except json.JSONDecodeError:
                processors_list = [p.strip() for p in processors_str.split(',') if p.strip()]
        else:
            processors_list = None  # Will use default
        
        # Save uploaded file
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Process the document with selected processors
        result = processor.process_document(filepath, filename, processors=processors_list)
        
        # Clean up uploaded file
        os.remove(filepath)
        
        return jsonify(result)
    
    except Exception as e:
        return jsonify({'error': str(e), 'success': False}), 500


@app.route('/process-drive', methods=['POST'])
def process_drive():
    """Handle Google Drive file or folder processing."""
    try:
        data = request.get_json()
        drive_url = data.get('drive_url', '').strip()
        processors_list = data.get('processors', None)  # List of processor names
        
        if not drive_url:
            return jsonify({'error': 'No Google Drive URL provided'}), 400
        
        # Check if Google credentials exist
        if not os.path.exists('credentials.json'):
            return jsonify({
                'error': 'Google Drive credentials not configured. Please see README for setup instructions.',
                'success': False
            }), 400
        
        # Download documents from Drive (handles both files and folders)
        downloader = DriveDownloader()
        downloaded_files = downloader.process_drive_url(drive_url, app.config['TEMP_FOLDER'])
        
        if not downloaded_files:
            return jsonify({'error': 'No documents found or unable to access the resource', 'success': False}), 404
        
        # Process each downloaded file
        results = []
        for file_info in downloaded_files:
            try:
                result = processor.process_document(file_info['path'], file_info['name'], processors=processors_list)
                results.append(result)
                # Clean up temp file
                os.remove(file_info['path'])
            except Exception as e:
                results.append({
                    'filename': file_info['name'],
                    'error': str(e),
                    'success': False
                })
        
        return jsonify({
            'success': True,
            'results': results,
            'total_files': len(results)
        })
    
    except Exception as e:
        # Clean up temp files on error
        if os.path.exists(app.config['TEMP_FOLDER']):
            shutil.rmtree(app.config['TEMP_FOLDER'])
            os.makedirs(app.config['TEMP_FOLDER'], exist_ok=True)
        
        return jsonify({'error': str(e), 'success': False}), 500


@app.route('/process-sheet', methods=['POST'])
def process_sheet():
    """Handle Google Sheet batch processing."""
    try:
        data = request.get_json()
        sheet_url = (data.get('sheet_url') or '').strip()
        row_limit = data.get('row_limit', 10)
        output_folder_url = (data.get('output_folder_url') or '').strip() or None
        processors_list = data.get('processors', None)
        
        if not sheet_url:
            return jsonify({'error': 'No Google Sheet URL provided'}), 400
        
        # Validate row_limit
        try:
            row_limit = int(row_limit)
            if row_limit < 1:
                row_limit = 1
            elif row_limit > 1000:
                row_limit = 1000  # Cap at 1000 for safety
        except (ValueError, TypeError):
            row_limit = 10
        
        # Check if Google credentials exist
        if not os.path.exists('credentials.json'):
            return jsonify({
                'error': 'Google Drive credentials not configured. Please see README for setup instructions.',
                'success': False
            }), 400
        
        # Process the sheet
        sheet_processor = SheetProcessor()
        result = sheet_processor.process_sheet(
            sheet_url=sheet_url,
            row_limit=row_limit,
            output_folder_url=output_folder_url,
            processors=processors_list,
            temp_dir=app.config['TEMP_FOLDER']
        )
        
        return jsonify(result)
    
    except Exception as e:
        # Clean up temp files on error
        if os.path.exists(app.config['TEMP_FOLDER']):
            shutil.rmtree(app.config['TEMP_FOLDER'])
            os.makedirs(app.config['TEMP_FOLDER'], exist_ok=True)
        
        return jsonify({'error': str(e), 'success': False}), 500


@app.route('/download-cleaned', methods=['POST'])
def download_cleaned():
    """Generate and download cleaned document in specified format."""
    try:
        data = request.get_json()
        cleaned_text = data.get('cleaned_text', '')
        original_filename = data.get('filename', 'cleaned_document')
        format_name = data.get('format', 'docx')  # Default to docx
        context = data.get('context', None)  # Optional context for formatting
        
        # Get format info
        formats = processor.get_available_formats()
        format_info = formats.get(format_name, formats.get('docx', {}))
        extension = format_info.get('extension', '.docx')
        mime_type = format_info.get('mime_type', 'application/octet-stream')
        
        # Build output filename
        base_name = original_filename.rsplit('.', 1)[0]
        output_filename = f"{base_name}_cleaned{extension}"
        
        # Get cleaned document as bytes
        file_bytes = processor.get_cleaned_bytes(cleaned_text, format_name, context)
        
        # Create a BytesIO object for sending
        from io import BytesIO
        buffer = BytesIO(file_bytes)
        buffer.seek(0)
        
        return send_file(
            buffer,
            as_attachment=True,
            download_name=output_filename,
            mimetype=mime_type
        )
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/health')
def health():
    """Health check endpoint."""
    return jsonify({'status': 'healthy'})


@app.route('/llm-providers', methods=['GET'])
def get_llm_providers():
    """Get available LLM providers and their models."""
    providers = get_available_providers()
    return jsonify(providers)


@app.route('/llm-prompt', methods=['GET'])
def get_llm_prompt():
    """Get the default LLM prompt template."""
    return jsonify({'prompt': get_default_prompt()})


@app.route('/process-llm', methods=['POST'])
def process_llm():
    """Process a single document using LLM."""
    try:
        # Check if file is provided
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'Invalid file type. Please upload a .docx or .doc file'}), 400
        
        # Get LLM parameters
        api_key = request.form.get('api_key', '').strip()
        provider = request.form.get('provider', 'openai')
        model = request.form.get('model', '').strip() or None
        prompt_template = request.form.get('prompt', get_default_prompt())
        
        # Only require API key for providers that need it (not Ollama)
        if not api_key and provider != 'ollama':
            return jsonify({'error': 'API key is required'}), 400
        
        # Save uploaded file
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        try:
            # Extract text from document using DocumentProcessor
            original_text, _ = processor.extract_paragraphs_with_metadata(filepath)
            
            # Process with LLM
            result = process_with_llm(
                document_text=original_text,
                prompt_template=prompt_template,
                api_key=api_key,
                provider=provider,
                model=model
            )
            
            if not result['success']:
                return jsonify({
                    'success': False,
                    'filename': filename,
                    'error': result.get('error', 'LLM processing failed')
                }), 400
            
            cleaned_text = result['cleaned_text']
            
            # Calculate statistics
            original_words = len(original_text.split())
            cleaned_words = len(cleaned_text.split())
            removed_words = original_words - cleaned_words
            reduction_pct = round((removed_words / original_words * 100), 1) if original_words > 0 else 0
            
            return jsonify({
                'success': True,
                'filename': filename,
                'original_text': original_text,
                'cleaned_text': cleaned_text,
                'removed_items': [],  # LLM doesn't provide granular removal info
                'processors': [f"LLM ({result.get('provider', provider)}: {result.get('model_used', model or 'default')})"],
                'statistics': {
                    'original_words': original_words,
                    'cleaned_words': cleaned_words,
                    'removed_words': removed_words,
                    'removed_lines': 0,  # Not tracked for LLM
                    'reduction_percentage': reduction_pct
                },
                'clean_rate': {
                    'score': 100,  # LLM output assumed clean
                    'category': 'llm-processed'
                }
            })
            
        finally:
            # Clean up uploaded file
            if os.path.exists(filepath):
                os.remove(filepath)
    
    except Exception as e:
        return jsonify({'error': str(e), 'success': False}), 500


@app.route('/process-drive-llm', methods=['POST'])
def process_drive_llm():
    """Process Google Drive files using LLM."""
    try:
        data = request.get_json()
        drive_url = data.get('drive_url', '').strip()
        api_key = data.get('api_key', '').strip()
        provider = data.get('provider', 'openai')
        model = data.get('model', '').strip() or None
        prompt_template = data.get('prompt', get_default_prompt())
        
        if not drive_url:
            return jsonify({'error': 'No Google Drive URL provided'}), 400
        
        # Only require API key for providers that need it (not Ollama)
        if not api_key and provider != 'ollama':
            return jsonify({'error': 'API key is required'}), 400
        
        # Check if Google credentials exist
        if not os.path.exists('credentials.json'):
            return jsonify({
                'error': 'Google Drive credentials not configured. Please see README for setup instructions.',
                'success': False
            }), 400
        
        # Download documents from Drive
        downloader = DriveDownloader()
        downloaded_files = downloader.process_drive_url(drive_url, app.config['TEMP_FOLDER'])
        
        if not downloaded_files:
            return jsonify({'error': 'No documents found or unable to access the resource', 'success': False}), 404
        
        # Process each file with LLM
        results = []
        for file_info in downloaded_files:
            try:
                # Extract text from document using DocumentProcessor
                original_text, _ = processor.extract_paragraphs_with_metadata(file_info['path'])
                
                # Process with LLM
                llm_result = process_with_llm(
                    document_text=original_text,
                    prompt_template=prompt_template,
                    api_key=api_key,
                    provider=provider,
                    model=model
                )
                
                if llm_result['success']:
                    cleaned_text = llm_result['cleaned_text']
                    original_words = len(original_text.split())
                    cleaned_words = len(cleaned_text.split())
                    removed_words = original_words - cleaned_words
                    reduction_pct = round((removed_words / original_words * 100), 1) if original_words > 0 else 0
                    
                    results.append({
                        'success': True,
                        'filename': file_info['name'],
                        'original_text': original_text,
                        'cleaned_text': cleaned_text,
                        'removed_items': [],
                        'processors': [f"LLM ({llm_result.get('provider', provider)}: {llm_result.get('model_used', model or 'default')})"],
                        'statistics': {
                            'original_words': original_words,
                            'cleaned_words': cleaned_words,
                            'removed_words': removed_words,
                            'removed_lines': 0,
                            'reduction_percentage': reduction_pct
                        },
                        'clean_rate': {
                            'score': 100,
                            'category': 'llm-processed'
                        }
                    })
                else:
                    results.append({
                        'success': False,
                        'filename': file_info['name'],
                        'error': llm_result.get('error', 'LLM processing failed')
                    })
                
                # Clean up temp file
                os.remove(file_info['path'])
            except Exception as e:
                results.append({
                    'filename': file_info['name'],
                    'error': str(e),
                    'success': False
                })
        
        return jsonify({
            'success': True,
            'results': results,
            'total_files': len(results)
        })
    
    except Exception as e:
        # Clean up temp files on error
        if os.path.exists(app.config['TEMP_FOLDER']):
            shutil.rmtree(app.config['TEMP_FOLDER'])
            os.makedirs(app.config['TEMP_FOLDER'], exist_ok=True)
        
        return jsonify({'error': str(e), 'success': False}), 500


@app.route('/process-sheet-llm-preview', methods=['POST'])
def process_sheet_llm_preview():
    """Get list of files from sheet for LLM processing with per-file prompts."""
    try:
        data = request.get_json()
        sheet_url = (data.get('sheet_url') or '').strip()
        row_limit = data.get('row_limit', 10)
        
        if not sheet_url:
            return jsonify({'error': 'No Google Sheet URL provided'}), 400
        
        # Validate row_limit
        try:
            row_limit = int(row_limit)
            if row_limit < 1:
                row_limit = 1
            elif row_limit > 1000:
                row_limit = 1000
        except (ValueError, TypeError):
            row_limit = 10
        
        # Check if Google credentials exist
        if not os.path.exists('credentials.json'):
            return jsonify({
                'error': 'Google Drive credentials not configured.',
                'success': False
            }), 400
        
        # Get file list from sheet
        sheet_processor = SheetProcessor()
        files = sheet_processor.get_files_from_sheet(sheet_url, row_limit)
        
        return jsonify({
            'success': True,
            'files': files,
            'default_prompt': get_default_prompt()
        })
    
    except Exception as e:
        return jsonify({'error': str(e), 'success': False}), 500


@app.route('/process-sheet-llm-file', methods=['POST'])
def process_sheet_llm_file():
    """Process a single file from sheet using LLM."""
    try:
        data = request.get_json()
        file_url = data.get('file_url', '').strip()
        row_number = data.get('row_number')
        api_key = data.get('api_key', '').strip()
        provider = data.get('provider', 'openai')
        model = data.get('model', '').strip() or None
        prompt_template = data.get('prompt', get_default_prompt())
        sheet_url = data.get('sheet_url', '').strip()
        output_folder_url = data.get('output_folder_url', '').strip() or None
        
        if not file_url:
            return jsonify({'error': 'No file URL provided'}), 400
        
        # Only require API key for providers that need it (not Ollama)
        if not api_key and provider != 'ollama':
            return jsonify({'error': 'API key is required'}), 400
        
        # Download the file
        downloader = DriveDownloader()
        downloaded_files = downloader.process_drive_url(file_url, app.config['TEMP_FOLDER'])
        
        if not downloaded_files:
            return jsonify({
                'success': False,
                'error': 'Could not download file',
                'row': row_number
            }), 404
        
        file_info = downloaded_files[0]
        
        try:
            # Extract text from document using DocumentProcessor
            original_text, _ = processor.extract_paragraphs_with_metadata(file_info['path'])
            
            # Process with LLM
            llm_result = process_with_llm(
                document_text=original_text,
                prompt_template=prompt_template,
                api_key=api_key,
                provider=provider,
                model=model
            )
            
            if not llm_result['success']:
                return jsonify({
                    'success': False,
                    'filename': file_info['name'],
                    'row': row_number,
                    'error': llm_result.get('error', 'LLM processing failed')
                }), 400
            
            cleaned_text = llm_result['cleaned_text']
            
            # Calculate stats
            original_words = len(original_text.split())
            cleaned_words = len(cleaned_text.split())
            removed_words = original_words - cleaned_words
            reduction_pct = round((removed_words / original_words * 100), 1) if original_words > 0 else 0
            
            result = {
                'success': True,
                'filename': file_info['name'],
                'row': row_number,
                'original_text': original_text,
                'cleaned_text': cleaned_text,
                'clean_rate': 100,
                'statistics': {
                    'original_words': original_words,
                    'cleaned_words': cleaned_words,
                    'removed_words': removed_words,
                    'reduction_percentage': reduction_pct
                }
            }
            
            # Update sheet and upload if needed
            if sheet_url:
                sheet_processor = SheetProcessor()
                # Update clean rate in sheet
                sheet_processor.update_sheet_row(
                    sheet_url=sheet_url,
                    row_number=row_number,
                    clean_rate=100,
                    cleaned_text=cleaned_text,
                    output_folder_url=output_folder_url,
                    filename=file_info['name']
                )
                
                if output_folder_url:
                    result['cleaned_link'] = sheet_processor.last_uploaded_link
            
            return jsonify(result)
            
        finally:
            # Clean up temp file
            if os.path.exists(file_info['path']):
                os.remove(file_info['path'])
    
    except Exception as e:
        return jsonify({'error': str(e), 'success': False}), 500


if __name__ == '__main__':
    # Only enable debug mode if explicitly set via environment variable
    # In production, use a WSGI server like gunicorn instead
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    port = int(os.environ.get('PORT', 5050))
    
    if debug_mode:
        from flask_livereload import LiveReload
        LiveReload(app)
    
    app.run(host='0.0.0.0', port=port, debug=debug_mode)
