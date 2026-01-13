"""
Flask web application for cleaning Yiddish transcripts.
"""
import os
import shutil
from flask import Flask, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename
from document_processor import DocumentProcessor
from drive_downloader import DriveDownloader
from cleaner import TranscriptCleaner

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


if __name__ == '__main__':
    # Only enable debug mode if explicitly set via environment variable
    # In production, use a WSGI server like gunicorn instead
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    port = int(os.environ.get('PORT', 5050))
    app.run(host='0.0.0.0', port=port, debug=debug_mode)
