"""
Google Sheets integration for batch document processing.

Reads document links from a Google Sheet, processes them, calculates clean rates,
and updates the sheet with results.
"""
import os
import re
from typing import Optional, Dict, Any, List, Tuple
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from drive_downloader import DriveDownloader
from document_processor import DocumentProcessor


# Scopes needed for reading/writing sheets and downloading docs
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',  # Read/write sheets
    'https://www.googleapis.com/auth/drive',  # Full drive access (read/write all files)
]

# Column names we look for and create
DOC_LINK_COL = 'Doc Link'
CLEAN_RATE_COL = 'Clean Rate'
CLEANED_LINK_COL = 'Cleaned Link'
STATUS_COL = 'Status'
SESSION_ID_COL = 'Session ID'
PROCESSED_AT_COL = 'Processed At'

# Processing status values
STATUS_PENDING = ''
STATUS_PROCESSING = 'Processing'
STATUS_COMPLETED = 'Completed'
STATUS_FAILED = 'Failed'
STATUS_SKIPPED = 'Skipped'


class SheetProcessor:
    """Processes documents from a Google Sheet and updates results."""
    
    def __init__(self, credentials_path: str = 'credentials.json'):
        """
        Initialize the Sheet processor.
        
        Args:
            credentials_path: Path to the credentials.json file
        """
        self.credentials_path = credentials_path
        self.sheets_service = None
        self.drive_service = None
        self.drive_downloader = None
        self.doc_processor = DocumentProcessor()
        self.creds = None
        self.last_uploaded_link = None  # Track last uploaded file link
    
    def authenticate(self) -> bool:
        """Authenticate with Google Sheets and Drive APIs."""
        creds = None
        
        # The file token_sheets.json stores the user's access and refresh tokens
        token_file = 'token_sheets.json'
        if os.path.exists(token_file):
            creds = Credentials.from_authorized_user_file(token_file, SCOPES)
        
        # If there are no (valid) credentials available, let the user log in
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            elif os.path.exists(self.credentials_path):
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, SCOPES)
                creds = flow.run_local_server(port=0)
            else:
                raise Exception("credentials.json not found. Please provide Google API credentials.")
            
            # Save the credentials for the next run
            with open(token_file, 'w') as token:
                token.write(creds.to_json())
        
        self.creds = creds
        self.sheets_service = build('sheets', 'v4', credentials=creds)
        self.drive_service = build('drive', 'v3', credentials=creds)
        
        # Initialize drive downloader with same credentials
        self.drive_downloader = DriveDownloader(self.credentials_path)
        self.drive_downloader.service = self.drive_service
        
        return True
    
    def extract_sheet_id(self, sheet_url: str) -> str:
        """
        Extract the spreadsheet ID from a Google Sheets URL.
        
        Args:
            sheet_url: Google Sheets URL
            
        Returns:
            str: Spreadsheet ID
        """
        # Pattern for sheets URLs: /spreadsheets/d/{ID}/
        patterns = [
            r'/spreadsheets/d/([a-zA-Z0-9-_]+)',
            r'id=([a-zA-Z0-9-_]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, sheet_url)
            if match:
                return match.group(1)
        
        # If no pattern matches, assume the input is already a sheet ID
        return sheet_url
    
    def get_sheet_data(self, spreadsheet_id: str, sheet_name: Optional[str] = None) -> Tuple[List[List[str]], str, Dict[Tuple[int, int], str]]:
        """
        Get all data from a Google Sheet, including hyperlinks.
        
        Args:
            spreadsheet_id: The spreadsheet ID
            sheet_name: Optional specific sheet name (defaults to first sheet)
            
        Returns:
            Tuple of (data rows, sheet name used, hyperlinks dict)
            hyperlinks dict maps (row, col) to URL
        """
        if not self.sheets_service:
            self.authenticate()
        
        # Get sheet metadata to find the first sheet name if not provided
        if not sheet_name:
            spreadsheet = self.sheets_service.spreadsheets().get(
                spreadsheetId=spreadsheet_id
            ).execute()
            sheet_name = spreadsheet['sheets'][0]['properties']['title']
        
        # Get all data from the sheet (plain values)
        result = self.sheets_service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=f"'{sheet_name}'"
        ).execute()
        
        values = result.get('values', [])
        
        # Also get the sheet with hyperlink data
        hyperlinks = {}
        try:
            spreadsheet_data = self.sheets_service.spreadsheets().get(
                spreadsheetId=spreadsheet_id,
                ranges=[f"'{sheet_name}'"],
                fields='sheets.data.rowData.values(hyperlink,textFormatRuns,formattedValue)'
            ).execute()
            
            print(f"DEBUG: Spreadsheet data keys: {spreadsheet_data.keys()}")
            sheets = spreadsheet_data.get('sheets', [])
            print(f"DEBUG: Number of sheets: {len(sheets)}")
            
            if sheets and 'data' in sheets[0]:
                for grid_data in sheets[0]['data']:
                    row_data = grid_data.get('rowData', [])
                    print(f"DEBUG: Number of rows: {len(row_data)}")
                    for row_idx, row in enumerate(row_data):
                        cell_values = row.get('values', [])
                        for col_idx, cell in enumerate(cell_values):
                            # Debug: print cell structure for first few rows
                            if row_idx < 3:
                                print(f"DEBUG: Cell ({row_idx}, {col_idx}): {cell}")
                            
                            # Check for hyperlink
                            if 'hyperlink' in cell:
                                hyperlinks[(row_idx, col_idx)] = cell['hyperlink']
                                print(f"DEBUG: Found hyperlink at ({row_idx}, {col_idx}): {cell['hyperlink']}")
                            # Also check for rich text links
                            elif 'textFormatRuns' in cell:
                                for run in cell['textFormatRuns']:
                                    if 'format' in run and 'link' in run['format']:
                                        link = run['format']['link']
                                        if 'uri' in link:
                                            hyperlinks[(row_idx, col_idx)] = link['uri']
                                            print(f"DEBUG: Found textFormatRuns link at ({row_idx}, {col_idx}): {link['uri']}")
                                            break
            
            print(f"DEBUG: Total hyperlinks found: {len(hyperlinks)}")
            print(f"DEBUG: Hyperlinks dict: {hyperlinks}")
        except Exception as e:
            print(f"Warning: Could not fetch hyperlinks: {e}")
            import traceback
            traceback.print_exc()
        
        return values, sheet_name, hyperlinks
    
    def find_or_create_columns(self, spreadsheet_id: str, sheet_name: str, 
                                headers: List[str]) -> Dict[str, int]:
        """
        Find column indices for required columns, creating them if they don't exist.
        
        Args:
            spreadsheet_id: The spreadsheet ID
            sheet_name: The sheet name
            headers: Current header row
            
        Returns:
            Dict mapping column names to their 0-based indices
        """
        column_indices = {}
        columns_to_add = []
        
        # All columns we need to find or create
        required_columns = [
            (DOC_LINK_COL, True),   # (name, is_required)
            (CLEAN_RATE_COL, False),
            (CLEANED_LINK_COL, False),
            (STATUS_COL, False),
            (SESSION_ID_COL, False),
            (PROCESSED_AT_COL, False),
        ]
        
        # Find existing columns
        for col_name, is_required in required_columns:
            found = False
            for i, header in enumerate(headers):
                if header and header.strip().lower() == col_name.lower():
                    column_indices[col_name] = i
                    found = True
                    break
            
            if not found:
                if is_required:
                    raise Exception(f"'{col_name}' column not found in the sheet. Please add a column with document links.")
                else:
                    columns_to_add.append(col_name)
        
        # Add missing columns
        if columns_to_add:
            new_col_start = len(headers)
            
            # Prepare values to add to header row
            new_headers = [[col] for col in columns_to_add]
            
            # Update the header row with new columns
            for i, col_name in enumerate(columns_to_add):
                col_index = new_col_start + i
                column_indices[col_name] = col_index
                
                # Add the header
                col_letter = self._col_index_to_letter(col_index)
                self.sheets_service.spreadsheets().values().update(
                    spreadsheetId=spreadsheet_id,
                    range=f"'{sheet_name}'!{col_letter}1",
                    valueInputOption='RAW',
                    body={'values': [[col_name]]}
                ).execute()
        
        return column_indices
    
    def _col_index_to_letter(self, index: int) -> str:
        """Convert 0-based column index to letter (A, B, ..., Z, AA, AB, ...)."""
        result = ""
        while index >= 0:
            result = chr(index % 26 + ord('A')) + result
            index = index // 26 - 1
        return result
    
    def upload_file_to_drive(self, file_path: str, file_name: str, 
                              folder_id: Optional[str] = None) -> str:
        """
        Upload a file to Google Drive and return the shareable link.
        
        Args:
            file_path: Local path to the file
            file_name: Name for the file in Drive
            folder_id: Optional folder ID to upload to
            
        Returns:
            str: Shareable link to the file
        """
        if not self.drive_service:
            self.authenticate()
        
        from googleapiclient.http import MediaFileUpload
        
        file_metadata = {'name': file_name}
        if folder_id:
            file_metadata['parents'] = [folder_id]
        
        media = MediaFileUpload(file_path, mimetype='text/plain')
        
        file = self.drive_service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, webViewLink'
        ).execute()
        
        # Make the file viewable by anyone with the link
        self.drive_service.permissions().create(
            fileId=file['id'],
            body={'type': 'anyone', 'role': 'reader'}
        ).execute()
        
        return file.get('webViewLink', f"https://drive.google.com/file/d/{file['id']}/view")
    
    def extract_folder_id(self, folder_url: str) -> Optional[str]:
        """
        Extract folder ID from a Google Drive folder URL.
        
        Args:
            folder_url: Google Drive folder URL
            
        Returns:
            str: Folder ID or None if invalid
        """
        if not folder_url:
            return None
        
        patterns = [
            r'/folders/([a-zA-Z0-9-_]+)',
            r'id=([a-zA-Z0-9-_]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, folder_url)
            if match:
                return match.group(1)
        
        # If no pattern matches, check if it's a valid folder ID
        if re.match(r'^[a-zA-Z0-9-_]+$', folder_url):
            return folder_url
        
        return None
    
    def process_sheet(self, sheet_url: str, row_limit: int = 10,
                       output_folder_url: Optional[str] = None,
                       processors: Optional[List[str]] = None,
                       temp_dir: str = 'temp') -> Dict[str, Any]:
        """
        Process documents from a Google Sheet.
        
        Args:
            sheet_url: URL to the Google Sheet
            row_limit: Maximum number of rows to process
            output_folder_url: Optional Google Drive folder URL for output files
            processors: Optional list of processor names to use
            temp_dir: Directory for temporary files
            
        Returns:
            Dict with processing results and statistics
        """
        if not self.sheets_service:
            self.authenticate()
        
        # Extract IDs
        spreadsheet_id = self.extract_sheet_id(sheet_url)
        output_folder_id = self.extract_folder_id(output_folder_url) if output_folder_url else None
        
        # Get sheet data (including hyperlinks)
        data, sheet_name, hyperlinks = self.get_sheet_data(spreadsheet_id)
        
        if not data or len(data) < 2:
            return {
                'success': False,
                'error': 'Sheet is empty or has no data rows',
                'processed': 0,
                'results': []
            }
        
        # Get headers and find/create columns
        headers = data[0]
        print(f"DEBUG: Headers: {headers}")
        column_indices = self.find_or_create_columns(spreadsheet_id, sheet_name, headers)
        print(f"DEBUG: Column indices: {column_indices}")
        
        doc_link_col_idx = column_indices[DOC_LINK_COL]
        print(f"DEBUG: Doc Link column index: {doc_link_col_idx}")
        
        # Process rows (skip header)
        results = []
        processed_count = 0
        
        # Ensure temp directory exists
        os.makedirs(temp_dir, exist_ok=True)
        
        for row_idx, row in enumerate(data[1:], start=2):  # start=2 because row 1 is header
            if processed_count >= row_limit:
                break
            
            # Get doc link from this row - check hyperlinks first, then cell value
            if len(row) <= doc_link_col_idx:
                print(f"DEBUG: Row {row_idx} has {len(row)} cells, need index {doc_link_col_idx}")
                continue
            
            # row_idx is 1-based for the sheet, but hyperlinks dict uses 0-based
            hyperlink_key = (row_idx - 1, doc_link_col_idx)
            print(f"DEBUG: Looking for hyperlink at key {hyperlink_key}")
            doc_link = hyperlinks.get(hyperlink_key, '')
            print(f"DEBUG: Hyperlink found: {doc_link}")
            
            # If no hyperlink, try the cell value
            if not doc_link:
                doc_link = row[doc_link_col_idx].strip() if row[doc_link_col_idx] else ''
                print(f"DEBUG: Fallback to cell value: {doc_link}")
            
            if not doc_link:
                continue
            
            # Process this document
            try:
                result = self._process_single_doc(
                    doc_link=doc_link,
                    row_index=row_idx,
                    spreadsheet_id=spreadsheet_id,
                    sheet_name=sheet_name,
                    column_indices=column_indices,
                    output_folder_id=output_folder_id,
                    processors=processors,
                    temp_dir=temp_dir
                )
                results.append(result)
                processed_count += 1
                
            except Exception as e:
                results.append({
                    'row': row_idx,
                    'doc_link': doc_link,
                    'success': False,
                    'error': str(e)
                })
                processed_count += 1
        
        return {
            'success': True,
            'processed': processed_count,
            'results': results,
            'spreadsheet_id': spreadsheet_id,
            'sheet_name': sheet_name
        }
    
    def _process_single_doc(self, doc_link: str, row_index: int,
                             spreadsheet_id: str, sheet_name: str,
                             column_indices: Dict[str, int],
                             output_folder_id: Optional[str],
                             processors: Optional[List[str]],
                             temp_dir: str) -> Dict[str, Any]:
        """
        Process a single document and update the sheet.
        
        Args:
            doc_link: Google Drive document link
            row_index: 1-based row index in the sheet
            spreadsheet_id: The spreadsheet ID
            sheet_name: The sheet name
            column_indices: Dict of column names to indices
            output_folder_id: Optional folder ID for output files
            processors: Optional list of processor names
            temp_dir: Temporary directory for downloads
            
        Returns:
            Dict with processing result
        """
        # Download the document
        downloaded_files = self.drive_downloader.process_drive_url(doc_link, temp_dir)
        
        if not downloaded_files:
            raise Exception("Could not download document")
        
        file_info = downloaded_files[0]
        file_path = file_info['path']
        file_name = file_info['name']
        
        try:
            # Process the document
            result = self.doc_processor.process_document(
                file_path, file_name, processors=processors
            )
            
            # Get clean rate from document processor result
            clean_rate_info = result.get('clean_rate', {})
            clean_rate = clean_rate_info.get('score', 50)  # Default to 50 if missing
            
            # Upload cleaned file if output folder specified
            cleaned_link = None
            if output_folder_id:
                # Save cleaned text to temp file
                base_name = os.path.splitext(file_name)[0]
                cleaned_filename = f"{base_name}_cleaned.txt"
                cleaned_path = os.path.join(temp_dir, cleaned_filename)
                
                with open(cleaned_path, 'w', encoding='utf-8') as f:
                    f.write(result.get('cleaned_text', ''))
                
                # Upload to Drive
                cleaned_link = self.upload_file_to_drive(
                    cleaned_path, cleaned_filename, output_folder_id
                )
                
                # Clean up temp cleaned file
                os.remove(cleaned_path)
            
            # Update the sheet
            self.update_sheet_row(
                spreadsheet_id=spreadsheet_id,
                sheet_name=sheet_name,
                row_index=row_index,
                column_indices=column_indices,
                clean_rate=clean_rate,
                cleaned_link=cleaned_link
            )
            
            return {
                'row': row_index,
                'doc_link': doc_link,
                'filename': file_name,
                'success': True,
                'clean_rate': clean_rate,
                'clean_rate_details': clean_rate_info,
                'cleaned_link': cleaned_link,
                'statistics': result.get('statistics', {})
            }
            
        finally:
            # Clean up downloaded file
            if os.path.exists(file_path):
                os.remove(file_path)

    def get_files_from_sheet(self, sheet_url: str, row_limit: int = 10, 
                              skip_completed: bool = True, skip_processing: bool = True) -> Dict[str, Any]:
        """
        Get list of files from a Google Sheet for LLM processing.
        
        Args:
            sheet_url: URL to the Google Sheet
            row_limit: Maximum number of rows to process
            skip_completed: Skip rows with status 'Completed'
            skip_processing: Skip rows with status 'Processing'
            
        Returns:
            Dict with files list and metadata for updating status
        """
        if not self.sheets_service:
            self.authenticate()
        
        spreadsheet_id = self.extract_sheet_id(sheet_url)
        data, sheet_name, hyperlinks = self.get_sheet_data(spreadsheet_id)
        
        if not data or len(data) < 2:
            return {'files': [], 'spreadsheet_id': spreadsheet_id, 'sheet_name': sheet_name, 'column_indices': {}}
        
        headers = data[0]
        column_indices = self.find_or_create_columns(spreadsheet_id, sheet_name, headers)
        
        doc_link_col_idx = column_indices.get(DOC_LINK_COL)
        status_col_idx = column_indices.get(STATUS_COL)
        
        if doc_link_col_idx is None:
            raise Exception(f"'{DOC_LINK_COL}' column not found in the sheet.")
        
        files = []
        for row_idx, row in enumerate(data[1:], start=2):
            if len(files) >= row_limit:
                break
            
            if len(row) <= doc_link_col_idx:
                continue
            
            # Check status if filtering is enabled
            if status_col_idx is not None and len(row) > status_col_idx:
                status = row[status_col_idx].strip() if row[status_col_idx] else ''
                if skip_completed and status == STATUS_COMPLETED:
                    continue
                if skip_processing and status == STATUS_PROCESSING:
                    continue
            
            # Check hyperlink first
            hyperlink_key = (row_idx - 1, doc_link_col_idx)
            doc_link = hyperlinks.get(hyperlink_key, '')
            
            # Fallback to cell value
            if not doc_link:
                doc_link = row[doc_link_col_idx].strip() if row[doc_link_col_idx] else ''
            
            if not doc_link:
                continue
            
            # Get display text (cell value or extracted filename)
            display_text = row[doc_link_col_idx].strip() if row[doc_link_col_idx] else doc_link
            
            files.append({
                'row': row_idx,
                'doc_link': doc_link,
                'display_text': display_text
            })
        
        return {
            'files': files,
            'spreadsheet_id': spreadsheet_id,
            'sheet_name': sheet_name,
            'column_indices': column_indices
        }
    
    def update_row_status(self, spreadsheet_id: str, sheet_name: str, 
                          row_index: int, column_indices: Dict[str, int],
                          status: str, session_id: str = None,
                          timestamp: str = None) -> None:
        """
        Update the status and session ID of a row in the sheet.
        
        Args:
            spreadsheet_id: The spreadsheet ID
            sheet_name: The sheet name
            row_index: 1-based row index
            column_indices: Dict of column names to indices
            status: Status value (STATUS_PROCESSING, STATUS_COMPLETED, STATUS_FAILED, etc.)
            session_id: Optional session identifier
            timestamp: Optional timestamp string (defaults to current time)
        """
        if not self.sheets_service:
            self.authenticate()
        
        from datetime import datetime
        
        updates = []
        
        if STATUS_COL in column_indices:
            col_letter = self._col_index_to_letter(column_indices[STATUS_COL])
            updates.append({
                'range': f"'{sheet_name}'!{col_letter}{row_index}",
                'values': [[status]]
            })
        
        if session_id and SESSION_ID_COL in column_indices:
            col_letter = self._col_index_to_letter(column_indices[SESSION_ID_COL])
            updates.append({
                'range': f"'{sheet_name}'!{col_letter}{row_index}",
                'values': [[session_id]]
            })
        
        if status in (STATUS_COMPLETED, STATUS_FAILED) and PROCESSED_AT_COL in column_indices:
            if timestamp is None:
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            col_letter = self._col_index_to_letter(column_indices[PROCESSED_AT_COL])
            updates.append({
                'range': f"'{sheet_name}'!{col_letter}{row_index}",
                'values': [[timestamp]]
            })
        
        if updates:
            self.sheets_service.spreadsheets().values().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body={
                    'valueInputOption': 'RAW',
                    'data': updates
                }
            ).execute()

    def update_sheet_row(self, sheet_url: str = None, spreadsheet_id: str = None,
                          sheet_name: str = None, row_number: int = None,
                          row_index: int = None, column_indices: Dict[str, int] = None,
                          clean_rate: Optional[int] = None, 
                          cleaned_link: Optional[str] = None,
                          cleaned_text: str = None,
                          output_folder_url: str = None,
                          filename: str = None) -> None:
        """
        Update a row in the sheet with clean rate and/or cleaned link.
        Supports both legacy dict-based column indices and direct sheet URL mode.
        
        Args:
            sheet_url: Google Sheet URL (alternative to spreadsheet_id)
            spreadsheet_id: The spreadsheet ID
            sheet_name: The sheet name
            row_number: 1-based row number (alias for row_index)
            row_index: 1-based row index
            column_indices: Dict of column names to indices (legacy mode)
            clean_rate: Optional clean rate to set
            cleaned_link: Optional cleaned file link to set
            cleaned_text: Optional cleaned text to upload
            output_folder_url: Optional folder URL to upload cleaned file
            filename: Original filename for naming the cleaned file
        """
        if not self.sheets_service:
            self.authenticate()
        
        # Support row_number as alias for row_index
        if row_index is None:
            row_index = row_number
        
        # If sheet_url provided, extract spreadsheet_id and get columns
        if sheet_url and not spreadsheet_id:
            spreadsheet_id = self.extract_sheet_id(sheet_url)
            data, sheet_name, _ = self.get_sheet_data(spreadsheet_id)
            if data:
                column_indices = self.find_or_create_columns(spreadsheet_id, sheet_name, data[0])
        
        # Handle cleaned text upload if provided
        if cleaned_text and output_folder_url and filename:
            output_folder_id = self.extract_folder_id(output_folder_url)
            if output_folder_id:
                import tempfile
                base_name = os.path.splitext(filename)[0]
                cleaned_filename = f"{base_name}_cleaned.txt"
                
                with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
                    f.write(cleaned_text)
                    temp_path = f.name
                
                try:
                    cleaned_link = self.upload_file_to_drive(temp_path, cleaned_filename, output_folder_id)
                    self.last_uploaded_link = cleaned_link
                finally:
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
        
        if not column_indices:
            return
        
        updates = []
        
        if clean_rate is not None and CLEAN_RATE_COL in column_indices:
            col_letter = self._col_index_to_letter(column_indices[CLEAN_RATE_COL])
            updates.append({
                'range': f"'{sheet_name}'!{col_letter}{row_index}",
                'values': [[clean_rate]]
            })
        
        if cleaned_link is not None and CLEANED_LINK_COL in column_indices:
            col_letter = self._col_index_to_letter(column_indices[CLEANED_LINK_COL])
            updates.append({
                'range': f"'{sheet_name}'!{col_letter}{row_index}",
                'values': [[cleaned_link]]
            })
        
        if updates:
            self.sheets_service.spreadsheets().values().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body={
                    'valueInputOption': 'RAW',
                    'data': updates
                }
            ).execute()

