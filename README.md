# Clean Yiddish Transcripts

A specialized web application designed for cleaning Yiddish transcripts by removing titles, headings, narrator notes, redactor notes, and other non-transcript content. This tool was built specifically to process Yiddish interview transcripts, oral histories, and similar documents where the pure spoken content needs to be extracted from editorial additions.

## Why This Tool Was Built for Yiddish Transcripts

Yiddish transcripts often contain:
- **Editorial notes** added by transcribers or redactors
- **Interviewer questions and labels** that interrupt the narrative flow
- **Chapter markers and section headings** added for organization
- **Timestamps** from original recordings
- **Narrator commentary** that isn't part of the original speech
- **Seif markers** (Hebrew gematria numbering like א. ב. יב*.)

This tool automates the extraction of pure spoken content, making it easier to:
- Create clean reading versions of oral histories
- Prepare transcripts for linguistic analysis
- Extract narrative content without editorial interference
- Process large collections of interviews consistently

## Features

- 🔤 **Clean Transcripts**: Automatically removes titles, headings, brackets, timestamps, and other non-transcript content
- 🔌 **Modular Plugin System**: Select which processing plugins to apply via checkboxes
- 📄 **Single File Upload**: Upload and process individual Word documents (.doc, .docx)
- 📁 **Google Drive Integration**: Process entire folders of documents from Google Drive
- 📊 **Detailed Statistics**: See what was removed and what remains
- ⬇️ **Multi-Format Download**: Download cleaned transcripts as Word (.docx) or plain text (.txt)
- 🎨 **Modern UI**: Clean, responsive web interface with drag-and-drop support
- 🐳 **Docker Ready**: Easy deployment with Docker

## Cleaning Profiles

The application includes preset profiles that auto-select processor combinations for common use cases:

| Profile | Description | Processors |
|---------|-------------|------------|
| **5710-5711 Transcripts** | Basic cleaning without bracket removal | special_chars, seif_marker, title_style, whitespace |
| **5712+ Transcripts** | Standard cleaning with inline brackets removed | special_chars, seif_marker, title_style, brackets_inline, whitespace |
| **With Editorial Removal** | Includes editorial Hebrew detection (citations, references) | special_chars, seif_marker, title_style, brackets_inline, editorial_hebrew, whitespace |
| **Heavy Cleaning** | All processors including parentheses and force remove | All processors enabled |
| **Minimal** | Only basic text cleanup | special_chars, whitespace |
| **Custom** | Manual selection of processors | User-defined |

Select a profile from the dropdown to quickly apply a preset, or choose "Custom" to manually select individual processors.

## Processing Plugins

The application uses a modular plugin architecture. You can select which processors to apply:

| Plugin | Description | Default |
|--------|-------------|---------|
| **special_chars** | Removes zero-width spaces, BOMs, and invisible Unicode characters | ✅ On |
| **seif_marker** | Removes Hebrew gematria markers (א. ב*. יב.) from paragraph starts | ✅ On |
| **title_style** | Removes titles based on Word styles, large fonts, and short paragraphs | ✅ On |
| **brackets_inline** | Removes inline [bracketed notes] but keeps full bracketed paragraphs | ✅ On |
| **whitespace** | Normalizes excessive whitespace | ✅ On |
| **editorial_hebrew** | Removes editorial Hebrew (citations, cross-references) while keeping spoken Hebrew | ❌ Off |
| **parentheses_notes** | Removes specific non-speech (parenthetical) content - citations, stage directions | ❌ Off |
| **force_remove** | Force removes paragraphs containing specific blocked patterns | ❌ Off |
| **regex** | General regex pattern matching for custom removals | ❌ Off |

### Editorial Hebrew Processor

The `editorial_hebrew` processor distinguishes between:

**Spoken Hebrew (KEPT):**
- Torah/Tanach quotes (pesukim)
- Religious terms (mitzvah, bracha, tefillah, etc.)
- Sefer names when being quoted in speech
- Chassidic phrases and terminology

**Editorial Hebrew (REMOVED):**
- Source citations: `ראה שמות כ, ג`, `עיין לעיל`
- Cross-references: `לעיל סעיף ג`, `לקמן פרק ב`
- Position markers: `כנ"ל`, `הנ"ל`, `שם`
- Editor notes: `הערה`, `הערת המתקן`
- Page/chapter references: `דף כ"ג ע"א`, `עמ' 15`

## Cleaning Rules for Yiddish Transcripts

The application uses intelligent pattern matching to identify and remove non-transcript content. Here are the specific rules:

### 1. **Inline Bracketed Content** (Editor/Narrator Notes)
- **Removes**: `[note]` when it's **inline** within a paragraph
- **Keeps**: Paragraphs that are **entirely** wrapped in brackets (these are typically spoken content)
- **Examples removed**:
  - `He said [Narrator: background info] and continued`
  - `[laughing]`, `[inaudible]`
- **Examples kept**:
  - `[This entire paragraph is actually spoken content that was bracketed for emphasis]`
- **Why**: Inline brackets are editorial additions; full bracketed paragraphs are often spoken

### 2. **Parenthetical Content** (Smart Detection)
- **Most parenthetical content is KEPT** (translations, clarifications are spoken)
- **Only removes** specific non-speech patterns:
  - Source citations: `(תהלים קיט, א)`, `(בראשית 1:1)`
  - Editorial markers: `(המשך)`, `(סיום)`, `(ראה ...)`
  - Stage directions: `(צוחק)`, `(מחיאות כפיים)`, `(לא נשמע)`
- **Why**: In Yiddish transcripts, most parenthetical content is actually spoken

### 3. **Seif Markers** (Hebrew Gematria Numbering)
- **Pattern**: Hebrew letters followed by optional asterisk and period at paragraph start
- **Examples**:
  - `א. ` → removed
  - `א*. ` → removed (with asterisk)
  - `יב. ` → removed (multi-letter gematria)
  - `קכא*. ` → removed
- **Why**: These are structural numbering added during transcription

### 4. **Title/Heading Detection**
Removes paragraphs that appear to be titles based on:
- **Word heading styles** (Heading 1, Title, etc.)
- **Short paragraphs** (less than 5 words)
- **Large font size** (larger than document average)
- **Bold short text** (bold paragraphs under 15 words)

### 5. **Headings with Colons**
- **Pattern**: `ALL CAPS TEXT: anything`
- **Examples**: 
  - `INTERVIEWER: What happened next?`
  - `CHAPTER 1: Early Life`
- **Why**: Structural markers added during transcription

### 6. **Chapter and Section Headings**
- **Pattern**: `Chapter N`, `Section N` (where N is a number)
- **Examples**: 
  - `Chapter 1`, `Chapter 1: Childhood`
  - `Section 2`, `Section 2: Later Years`
- **Why**: Editorial structure not part of original narrative

### 7. **Timestamps**
- **Pattern**: `HH:MM:SS` or `[MM:SS]`
- **Examples**: 
  - `[12:34]`, `[01:23:45]`
  - `12:34:56`
- **Why**: Technical markers from recording playback

### 8. **Speaker Labels**
- **Pattern**: Lines starting with speaker identifiers
- **Examples**: 
  - `Speaker 1: ...`, `Speaker 2: ...`
  - `Interviewer: ...`
  - `Narrator: ...`
- **Why**: These label who is speaking but aren't part of the speech itself

### 9. **Page Numbers and Separator Lines**
- **Pattern**: Standalone numbers, "Page N", lines of dashes/equals
- **Examples**: 
  - `Page 2`, `Page 15`
  - `-------------------`
  - `===================`
- **Why**: Document formatting elements

### 10. **Special Characters**
- **Pattern**: Zero-width spaces, Byte Order Marks (BOM)
- **Why**: Hidden characters that can cause processing issues

### 11. **Excessive Whitespace**
- **Pattern**: Multiple consecutive blank lines, extra spaces
- **Result**: Normalized to single spaces and maximum 2 newlines
- **Why**: Clean, readable formatting

### Example: Before and After Cleaning

**Original Transcript:**
```
CHAPTER 1: INTRODUCTION

[Narrator: The following is a transcript from an interview conducted in 2023]

א. Interviewer: Tell me about your childhood.

This is the actual transcript content that should remain. It tells the story 
of growing up in a small village (דער קליינער דארף).

[12:34] ב*. Another important memory from those days.

(Redactor note: The interviewee became emotional at this point)

The village had a beautiful synagogue where everyone would gather. We had 
wonderful celebrations there (תהלים קיט, א).

Speaker 1: What about the festivals?

יב. The festivals were the highlight of the year. Everyone would come together 
and celebrate with traditional songs and dances.

-------------------
Page 2
-------------------

SECTION 2: LATER YEARS

As I grew older, things began to change. [00:45:12] The community evolved 
and adapted to modern times while maintaining our traditions.

[This entire bracketed paragraph is actually spoken content that should remain 
in the final transcript.]
```

**Cleaned Transcript:**
```
This is the actual transcript content that should remain. It tells the story 
of growing up in a small village (דער קליינער דארף).

Another important memory from those days.

The village had a beautiful synagogue where everyone would gather. We had 
wonderful celebrations there.

The festivals were the highlight of the year. Everyone would come together 
and celebrate with traditional songs and dances.

As I grew older, things began to change. The community evolved and adapted 
to modern times while maintaining our traditions.

[This entire bracketed paragraph is actually spoken content that should remain 
in the final transcript.]
```

**What was removed:**
- Seif markers: `א.`, `ב*.`, `יב.`
- Chapter/section headings: `CHAPTER 1: INTRODUCTION`, `SECTION 2: LATER YEARS`
- Narrator notes: `[Narrator: ...]`
- Speaker labels: `Interviewer:`, `Speaker 1:`
- Timestamps: `[12:34]`, `[00:45:12]`
- Source citation: `(תהלים קיט, א)`
- Page separators and numbers

**What was kept:**
- All spoken content
- Parenthetical translation `(דער קליינער דארף)` - this is spoken
- Full bracketed paragraph at the end

The application shows you exactly what was removed in each category so you can verify the cleaning was done correctly.

## Installation

### Prerequisites

- Python 3.8 or higher
- pip package manager

### Local Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/Shloimy15e/clean-yiddish-transcripts.git
   cd clean-yiddish-transcripts
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application**
   ```bash
   python app.py
   ```
   
   For development with debug mode enabled:
   ```bash
   FLASK_DEBUG=true python app.py
   ```

4. **Open your browser**
   Navigate to `http://localhost:5050`

### Docker Deployment

1. **Build the Docker image**
   ```bash
   docker build -t yiddish-transcript-cleaner .
   ```

2. **Run the container**
   ```bash
   docker run -p 5050:5050 yiddish-transcript-cleaner
   ```

3. **Access the application**
   Navigate to `http://localhost:5050`

## Google Drive Integration (Optional)

To use the Google Drive folder processing feature:

1. **Create a Google Cloud Project**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project
   - Enable the Google Drive API

2. **Create OAuth 2.0 Credentials**
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "OAuth client ID"
   - Choose "Desktop app" as application type
   - Download the credentials JSON file

3. **Setup Credentials**
   - Rename the downloaded file to `credentials.json`
   - Place it in the root directory of the application

4. **First-time Authentication**
   - The first time you use the Drive feature, a browser window will open
   - Sign in with your Google account and grant permissions
   - The authentication token will be saved for future use

## Usage

### Processing a Single File

1. Click on the "📄 Upload File" tab
2. **Select processing plugins** using the checkboxes (defaults are pre-selected)
3. Drag and drop a Word document or click to browse
4. Click "Process Document"
5. View the results:
   - Statistics showing what was removed
   - Text display with removed content highlighted
   - List of which processors were applied
6. **Select output format(s)** (DOCX, TXT, or both)
7. Download the cleaned document

### Processing Google Drive Folders

1. Click on the "📁 Google Drive" tab
2. **Select processing plugins** using the checkboxes
3. Paste the Google Drive folder URL
4. Click "Process Drive Folder"
5. View results for all documents in the folder
6. Download cleaned versions individually

## API Endpoints

The application provides the following REST API endpoints:

- `GET /` - Main web interface
- `GET /processors` - Get available processing plugins
- `GET /formats` - Get available output formats
- `GET /profiles` - Get predefined cleaning profiles (legacy)
- `POST /upload` - Upload and process a single document
- `POST /process-drive` - Process documents from Google Drive folder
- `POST /download-cleaned` - Download a cleaned document
- `GET /health` - Health check endpoint

## Development

### Project Structure

```
clean-yiddish-transcripts/
├── app.py                      # Flask application
├── cleaner.py                  # Cleaning profiles and orchestration
├── document_processor.py       # Document processing and extraction
├── drive_downloader.py         # Google Drive integration
├── registry.py                 # Plugin registry system
├── document_model.py           # Document data structures
├── utils.py                    # Utility functions (gematria, etc.)
├── requirements.txt            # Python dependencies
├── Dockerfile                  # Docker configuration
├── processors/                 # Processing plugins
│   ├── __init__.py
│   ├── base.py                 # Base processor class
│   ├── special_chars.py        # Remove invisible characters
│   ├── whitespace.py           # Normalize whitespace
│   ├── seif_marker.py          # Remove Hebrew gematria markers
│   ├── title_style.py          # Remove titles by style/size
│   ├── brackets_inline.py      # Remove inline [brackets]
│   ├── parentheses_notes.py    # Remove non-speech (parens)
│   ├── force_remove.py         # Force remove patterns
│   └── regex_processor.py      # General regex patterns
├── writers/                    # Output format plugins
│   ├── __init__.py
│   ├── base.py                 # Base writer class
│   ├── docx_writer.py          # Word document output
│   └── txt_writer.py           # Plain text output
├── templates/
│   └── index.html              # Web UI
├── uploads/                    # Temporary upload storage
└── temp/                       # Temporary file storage
```

### Creating Custom Processors

To add a new processor, create a file in `processors/`:

```python
from registry import ProcessorRegistry
from processors.base import BaseProcessor

@ProcessorRegistry.register
class MyCustomProcessor(BaseProcessor):
    name = "my_custom"
    description = "Description shown in UI"
    
    def process(self, text, context=None):
        removed_items = []
        # Your processing logic here
        cleaned_text = text
        return cleaned_text, removed_items
```

The processor will automatically appear in the UI checkboxes.

### Creating Custom Writers

To add a new output format, create a file in `writers/`:

```python
from registry import WriterRegistry
from writers.base import BaseWriter

@WriterRegistry.register
class MyFormatWriter(BaseWriter):
    name = "myformat"
    extension = ".myf"
    description = "My custom format"
    mime_type = "application/x-myformat"
    
    def write(self, text, output_path, context=None):
        # Write to file
        pass
    
    def write_to_bytes(self, text, context=None):
        # Return bytes for download
        return text.encode('utf-8')
```

### Customizing Exception and Force-Remove Patterns

Edit `cleaner.py` to modify:

```python
# Content matching these patterns will NOT be removed
EXCEPTION_PATTERNS = [
    r'לחיים',  # Keep "l'chaim" toasts
    # Add more patterns...
]

# Content matching these patterns WILL be forcibly removed
FORCE_REMOVE_PATTERNS = [
    r'בס"ד',  # Remove "B'S'D" header
    # Add more patterns...
]
```

## Deployment

This section provides detailed step-by-step instructions for deploying the Yiddish Transcript Cleaner to various platforms.

### Local Deployment (Development & Testing)

**Step 1: Install Python**
- Ensure Python 3.8 or higher is installed: `python --version`

**Step 2: Clone and Setup**
```bash
git clone https://github.com/Shloimy15e/clean-yiddish-transcripts.git
cd clean-yiddish-transcripts
pip install -r requirements.txt
```

**Step 3: Run the Application**
```bash
python app.py
```

**Step 4: Access the Application**
- Open your browser and navigate to `http://localhost:5050`
- The application will run on port 5050 by default

**For Development with Debug Mode:**
```bash
FLASK_DEBUG=true python app.py
```
⚠️ **Warning**: Never use debug mode in production!

---

### Docker Deployment (Recommended for Production)

Docker provides a consistent, isolated environment and is the recommended deployment method.

**Step 1: Install Docker**
- Download and install [Docker Desktop](https://www.docker.com/products/docker-desktop/) for your operating system

**Step 2: Build the Docker Image**
```bash
cd clean-yiddish-transcripts
docker build -t yiddish-transcript-cleaner .
```
This creates a Docker image with all dependencies pre-installed.

**Step 3: Run the Container**
```bash
docker run -d -p 5050:5050 --name yiddish-cleaner yiddish-transcript-cleaner
```
- `-d`: Run in detached mode (background)
- `-p 5050:5050`: Map port 5050 from container to host
- `--name`: Give the container a friendly name

**Step 4: Verify It's Running**
```bash
docker ps
```
You should see your container listed as running.

**Step 5: Access the Application**
- Open your browser and navigate to `http://localhost:5050`

**Managing the Container:**
```bash
# Stop the container
docker stop yiddish-cleaner

# Start the container
docker start yiddish-cleaner

# View logs
docker logs yiddish-cleaner

# Remove the container
docker rm yiddish-cleaner
```

---

### Heroku Deployment (Cloud Platform)

Heroku is a platform-as-a-service (PaaS) that makes deployment simple.

**Step 1: Install Heroku CLI**
- Download from [Heroku CLI](https://devcenter.heroku.com/articles/heroku-cli)
- Login: `heroku login`

**Step 2: Prepare Your Repository**
```bash
cd clean-yiddish-transcripts
git init  # if not already a git repository
```

**Step 3: Create a Heroku App**
```bash
heroku create your-unique-app-name
```
Replace `your-unique-app-name` with your desired app name (must be globally unique).

**Step 4: Set Environment Variables**
```bash
heroku config:set FLASK_ENV=production
heroku config:set SECRET_KEY=$(openssl rand -hex 32)
```

**Step 5: Deploy the Application**
```bash
git push heroku main
```
If your branch is named differently (e.g., `master`), use:
```bash
git push heroku master
```

**Step 6: Open Your Application**
```bash
heroku open
```
Your app will be available at `https://your-app-name.herokuapp.com`

**Step 7: View Logs (if needed)**
```bash
heroku logs --tail
```

**Scaling (if needed):**
```bash
# Scale up to 2 dynos
heroku ps:scale web=2

# Scale down to 1 dyno
heroku ps:scale web=1
```

---

### Google Cloud Run Deployment

Google Cloud Run is a serverless platform that automatically scales your application. This deployment includes support for both .docx and .doc files using LibreOffice for .doc conversion.

**Step 1: Install Google Cloud SDK**
- Download from [Google Cloud SDK](https://cloud.google.com/sdk/docs/install)
- Initialize: `gcloud init`

**Step 2: Authenticate and Set Project**
```bash
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
```

**Step 3: Enable Required APIs**
```bash
gcloud services enable run.googleapis.com
gcloud services enable containerregistry.googleapis.com
```

**Step 4: Deploy from Source**
```bash
cd clean-yiddish-transcripts
gcloud run deploy yiddish-transcript-cleaner \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 1Gi \
  --cpu 1 \
  --max-instances 10
```

**Note:** The deployment includes LibreOffice for .doc file conversion. The application will automatically detect and use LibreOffice when running on Linux (Cloud Run) or fall back to Microsoft Word COM when running on Windows.

**Step 5: Access Your Application**
After deployment completes, Cloud Run will provide a URL like:
`https://yiddish-transcript-cleaner-xxxxx-uc.a.run.app`

**Updating the Deployment:**
```bash
gcloud run deploy yiddish-transcript-cleaner --source .
```

**Viewing Logs:**
```bash
gcloud run services logs read yiddish-transcript-cleaner
```

---

### AWS Elastic Beanstalk Deployment

AWS Elastic Beanstalk provides a managed platform for web applications.

**Step 1: Install EB CLI**
```bash
pip install awsebcli
```

**Step 2: Configure AWS Credentials**
```bash
aws configure
```
Enter your AWS Access Key ID and Secret Access Key.

**Step 3: Initialize Elastic Beanstalk**
```bash
cd clean-yiddish-transcripts
eb init -p python-3.11 yiddish-transcript-cleaner --region us-east-1
```

**Step 4: Create an Environment and Deploy**
```bash
eb create yiddish-transcript-env
```
This creates an environment and deploys your application.

**Step 5: Open Your Application**
```bash
eb open
```

**Updating the Application:**
```bash
eb deploy
```

**Viewing Logs:**
```bash
eb logs
```

**Terminating (when done):**
```bash
eb terminate yiddish-transcript-env
```

---

### VPS Deployment (Ubuntu Server)

For deployment on a Virtual Private Server (VPS) like DigitalOcean, Linode, or AWS EC2.

**Step 1: Connect to Your Server**
```bash
ssh user@your-server-ip
```

**Step 2: Update System and Install Dependencies**
```bash
sudo apt update
sudo apt upgrade -y
sudo apt install python3 python3-pip git nginx -y
```

**Step 3: Clone the Repository**
```bash
cd /var/www
sudo git clone https://github.com/Shloimy15e/clean-yiddish-transcripts.git
cd clean-yiddish-transcripts
```

**Step 4: Install Python Dependencies**
```bash
sudo pip3 install -r requirements.txt
```

**Step 5: Create a Systemd Service**
```bash
sudo nano /etc/systemd/system/yiddish-cleaner.service
```

Add the following content:
```ini
[Unit]
Description=Yiddish Transcript Cleaner
After=network.target

[Service]
User=www-data
WorkingDirectory=/var/www/clean-yiddish-transcripts
Environment="PATH=/usr/bin"
ExecStart=/usr/local/bin/gunicorn --bind 0.0.0.0:8000 --workers 4 app:app

[Install]
WantedBy=multi-user.target
```

**Step 6: Start the Service**
```bash
sudo systemctl daemon-reload
sudo systemctl start yiddish-cleaner
sudo systemctl enable yiddish-cleaner
sudo systemctl status yiddish-cleaner
```

**Step 7: Configure Nginx as Reverse Proxy**
```bash
sudo nano /etc/nginx/sites-available/yiddish-cleaner
```

Add:
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

**Step 8: Enable the Site**
```bash
sudo ln -s /etc/nginx/sites-available/yiddish-cleaner /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

**Step 9: Setup SSL (Optional but Recommended)**
```bash
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d your-domain.com
```

Your application is now accessible at `http://your-domain.com` (or `https://` if SSL is configured).

---

### Environment Variables for Production

For all deployment methods, set these environment variables:

```bash
FLASK_ENV=production
SECRET_KEY=your-secret-key-here
PORT=5050  # Optional, defaults to 5050
```

Generate a secure secret key:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

**Never set `FLASK_DEBUG=true` in production!**

---

### Deployment Checklist

Before deploying to production:

- [ ] Set `FLASK_ENV=production`
- [ ] Set a secure `SECRET_KEY`
- [ ] Ensure `FLASK_DEBUG` is not set (or set to `false`)
- [ ] Configure HTTPS/SSL for secure connections
- [ ] Set up regular backups (if storing data)
- [ ] Configure firewall rules appropriately
- [ ] Monitor application logs
- [ ] Set up health check monitoring

## Security Notes

- The application does not store uploaded files permanently
- Files are deleted immediately after processing
- Google Drive credentials are stored locally and not shared
- Debug mode is disabled by default for security
- For production use, ensure proper authentication and HTTPS

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is open source and available under the MIT License.

## Support

For issues, questions, or suggestions, please open an issue on GitHub.
