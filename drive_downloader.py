"""
Google Drive integration for downloading documents.
"""
import os
import io
import re
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload


# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

# Supported document MIME types
SUPPORTED_MIME_TYPES = [
    'application/vnd.google-apps.document',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/msword'
]


class DriveDownloader:
    """Downloads documents from Google Drive."""
    
    def __init__(self, credentials_path='credentials.json'):
        """
        Initialize the Drive downloader.
        
        Args:
            credentials_path: Path to the credentials.json file
        """
        self.credentials_path = credentials_path
        self.service = None
    
    def authenticate(self):
        """Authenticate with Google Drive API."""
        creds = None
        
        # The file token.json stores the user's access and refresh tokens
        if os.path.exists('token.json'):
            creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        
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
            with open('token.json', 'w') as token:
                token.write(creds.to_json())
        
        self.service = build('drive', 'v3', credentials=creds)
        return True
    
    def extract_file_id(self, drive_url):
        """
        Extract file ID from a Google Drive URL.
        
        Args:
            drive_url: Google Drive file URL
            
        Returns:
            str: File ID
        """
        # Patterns for file URLs
        patterns = [
            r'/file/d/([a-zA-Z0-9-_]+)',
            r'/open\?id=([a-zA-Z0-9-_]+)',
            r'id=([a-zA-Z0-9-_]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, drive_url)
            if match:
                return match.group(1)
        
        # If no pattern matches, assume the input is already a file ID
        return drive_url
    
    def extract_folder_id(self, drive_url):
        """
        Extract folder ID from a Google Drive URL.
        
        Args:
            drive_url: Google Drive folder URL
            
        Returns:
            str: Folder ID
        """
        # Pattern for folder URLs
        patterns = [
            r'/folders/([a-zA-Z0-9-_]+)',
            r'id=([a-zA-Z0-9-_]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, drive_url)
            if match:
                return match.group(1)
        
        # If no pattern matches, assume the input is already a folder ID
        return drive_url
    
    def is_folder(self, resource_id):
        """
        Check if a Google Drive resource ID is a folder.
        
        Args:
            resource_id: Google Drive resource ID
            
        Returns:
            bool: True if resource is a folder, False if it's a file
        """
        if not self.service:
            self.authenticate()
        
        try:
            file = self.service.files().get(
                fileId=resource_id,
                fields='mimeType'
            ).execute()
            
            return file.get('mimeType') == 'application/vnd.google-apps.folder'
        except Exception as e:
            raise Exception(f"Error checking resource type: {str(e)}")
    
    def list_documents_in_folder(self, folder_id, recursive=True):
        """
        List all documents in a Google Drive folder.
        
        Args:
            folder_id: Google Drive folder ID
            recursive: If True, recursively search subfolders
            
        Returns:
            list: List of document metadata dicts
        """
        if not self.service:
            self.authenticate()
        
        documents = []
        
        # Query for documents in folder
        mime_types = [f"mimeType='{mime}'" for mime in SUPPORTED_MIME_TYPES]
        query = f"'{folder_id}' in parents and ({' or '.join(mime_types)})"
        
        results = self.service.files().list(
            q=query,
            fields="files(id, name, mimeType)",
            pageSize=100
        ).execute()
        
        documents.extend(results.get('files', []))
        
        # If recursive, also search subfolders
        if recursive:
            folder_query = f"'{folder_id}' in parents and mimeType='application/vnd.google-apps.folder'"
            folder_results = self.service.files().list(
                q=folder_query,
                fields="files(id, name)",
                pageSize=100
            ).execute()
            
            subfolders = folder_results.get('files', [])
            
            # Recursively get documents from each subfolder
            for subfolder in subfolders:
                try:
                    subdocs = self.list_documents_in_folder(subfolder['id'], recursive=True)
                    documents.extend(subdocs)
                except Exception as e:
                    print(f"Error processing subfolder {subfolder['name']}: {str(e)}")
        
        return documents
    
    def download_document(self, file_id, file_name, output_dir='temp'):
        """
        Download a document from Google Drive.
        
        Args:
            file_id: Google Drive file ID
            file_name: Name of the file
            output_dir: Directory to save the file
            
        Returns:
            str: Path to downloaded file
        """
        if not self.service:
            self.authenticate()
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Get file metadata
        file = self.service.files().get(fileId=file_id, fields='mimeType').execute()
        mime_type = file.get('mimeType')
        
        # Handle Google Docs (convert to .docx)
        if mime_type == 'application/vnd.google-apps.document':
            request = self.service.files().export_media(
                fileId=file_id,
                mimeType='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            )
            if not file_name.endswith('.docx'):
                file_name += '.docx'
        else:
            # Download Word documents directly
            request = self.service.files().get_media(fileId=file_id)
        
        # Download file
        file_path = os.path.join(output_dir, file_name)
        fh = io.FileIO(file_path, 'wb')
        downloader = MediaIoBaseDownload(fh, request)
        
        done = False
        while done is False:
            status, done = downloader.next_chunk()
        
        fh.close()
        return file_path
    
    def download_folder(self, folder_url, output_dir='temp', recursive=True):
        """
        Download all documents from a Google Drive folder.
        
        Args:
            folder_url: Google Drive folder URL or ID
            output_dir: Directory to save files
            recursive: If True, recursively process subfolders (default: True)
            
        Returns:
            list: List of downloaded file paths
        """
        folder_id = self.extract_folder_id(folder_url)
        documents = self.list_documents_in_folder(folder_id, recursive=recursive)
        
        downloaded_files = []
        for doc in documents:
            try:
                file_path = self.download_document(doc['id'], doc['name'], output_dir)
                downloaded_files.append({
                    'path': file_path,
                    'name': doc['name'],
                    'id': doc['id']
                })
            except Exception as e:
                print(f"Error downloading {doc['name']}: {str(e)}")
        
        return downloaded_files
    
    def process_drive_url(self, drive_url, output_dir='temp'):
        """
        Process a Google Drive URL - automatically detects if it's a file or folder
        and handles accordingly.
        
        Args:
            drive_url: Google Drive file or folder URL
            output_dir: Directory to save files
            
        Returns:
            list: List of downloaded file info dicts with 'path', 'name', and 'id'
        """
        if not self.service:
            self.authenticate()
        
        # Try to extract file ID first
        if '/file/d/' in drive_url or '/open?id=' in drive_url:
            # This is likely a file URL
            file_id = self.extract_file_id(drive_url)
            
            # Verify it's actually a file
            try:
                file_metadata = self.service.files().get(
                    fileId=file_id,
                    fields='id, name, mimeType'
                ).execute()
                
                mime_type = file_metadata.get('mimeType')
                
                if mime_type in SUPPORTED_MIME_TYPES:
                    # Download single file
                    file_path = self.download_document(
                        file_metadata['id'],
                        file_metadata['name'],
                        output_dir
                    )
                    return [{
                        'path': file_path,
                        'name': file_metadata['name'],
                        'id': file_metadata['id']
                    }]
                elif mime_type == 'application/vnd.google-apps.folder':
                    # It's actually a folder, process as folder
                    return self.download_folder(file_id, output_dir)
                else:
                    raise Exception(f"Unsupported file type: {mime_type}. Only Word documents (.doc, .docx) and Google Docs are supported.")
            except Exception as e:
                # If file processing fails, try as folder
                print(f"Failed to process as file, trying as folder: {str(e)}")
                pass
        
        # Try processing as folder
        folder_id = self.extract_folder_id(drive_url)
        
        # Check if it's actually a folder
        try:
            if self.is_folder(folder_id):
                return self.download_folder(folder_id, output_dir)
            else:
                # It's a file, download it
                file_metadata = self.service.files().get(
                    fileId=folder_id,
                    fields='id, name, mimeType'
                ).execute()
                
                # Validate file type
                mime_type = file_metadata.get('mimeType')
                if mime_type not in SUPPORTED_MIME_TYPES:
                    raise Exception(f"Unsupported file type: {mime_type}. Only Word documents (.doc, .docx) and Google Docs are supported.")
                
                file_path = self.download_document(
                    file_metadata['id'],
                    file_metadata['name'],
                    output_dir
                )
                return [{
                    'path': file_path,
                    'name': file_metadata['name'],
                    'id': file_metadata['id']
                }]
        except Exception as e:
            raise Exception(f"Unable to process Drive URL: {str(e)}")
