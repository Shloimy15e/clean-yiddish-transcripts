# Clean Yiddish Transcripts

A specialized web application designed for cleaning Yiddish transcripts by removing titles, headings, narrator notes, redactor notes, and other non-transcript content. This tool was built specifically to process Yiddish interview transcripts, oral histories, and similar documents where the pure spoken content needs to be extracted from editorial additions.

## Why This Tool Was Built for Yiddish Transcripts

Yiddish transcripts often contain:
- **Editorial notes** added by transcribers or redactors
- **Interviewer questions and labels** that interrupt the narrative flow
- **Chapter markers and section headings** added for organization
- **Timestamps** from original recordings
- **Narrator commentary** that isn't part of the original speech

This tool automates the extraction of pure spoken content, making it easier to:
- Create clean reading versions of oral histories
- Prepare transcripts for linguistic analysis
- Extract narrative content without editorial interference
- Process large collections of interviews consistently

## Features

- 🔤 **Clean Transcripts**: Automatically removes titles, headings, brackets, timestamps, and other non-transcript content
- 📄 **Single File Upload**: Upload and process individual Word documents (.doc, .docx)
- 📁 **Google Drive Integration**: Process entire folders of documents from Google Drive
- 📊 **Detailed Statistics**: See what was removed and what remains
- ⬇️ **Download Results**: Download cleaned transcripts as Word documents
- 🎨 **Modern UI**: Clean, responsive web interface with drag-and-drop support
- 🐳 **Docker Ready**: Easy deployment with Docker

## Cleaning Rules for Yiddish Transcripts

The application uses intelligent pattern matching to identify and remove non-transcript content. Here are the specific rules:

### 1. **Bracketed Content** (Narrator/Redactor Notes)
- **Pattern**: `[any content]` or `(any content)`
- **Examples**: 
  - `[Narrator: This is background information]`
  - `(Redactor note: The speaker paused here)`
  - `[laughing]`, `[inaudible]`
- **Why**: These are editorial additions, not part of the original speech

### 2. **Headings with Colons**
- **Pattern**: `ALL CAPS TEXT: anything`
- **Examples**: 
  - `INTERVIEWER: What happened next?`
  - `CHAPTER 1: Early Life`
- **Why**: Structural markers added during transcription

### 3. **Chapter and Section Headings**
- **Pattern**: `Chapter N`, `Section N` (where N is a number)
- **Examples**: 
  - `Chapter 1`, `Chapter 1: Childhood`
  - `Section 2`, `Section 2: Later Years`
- **Why**: Editorial structure not part of original narrative

### 4. **Timestamps**
- **Pattern**: `HH:MM:SS` or `[MM:SS]`
- **Examples**: 
  - `[12:34]`, `[01:23:45]`
  - `12:34:56`
- **Why**: Technical markers from recording playback

### 5. **Speaker Labels**
- **Pattern**: Lines starting with speaker identifiers
- **Examples**: 
  - `Speaker 1: ...`, `Speaker 2: ...`
  - `Interviewer: ...`
  - `Narrator: ...`
- **Why**: These label who is speaking but aren't part of the speech itself

### 6. **Page Numbers and Separator Lines**
- **Pattern**: Standalone numbers, "Page N", lines of dashes/equals
- **Examples**: 
  - `Page 2`, `Page 15`
  - `-------------------`
  - `===================`
- **Why**: Document formatting elements

### 7. **Special Characters**
- **Pattern**: Zero-width spaces, Byte Order Marks (BOM)
- **Why**: Hidden characters that can cause processing issues

### 8. **Excessive Whitespace**
- **Pattern**: Multiple consecutive blank lines, extra spaces
- **Result**: Normalized to single spaces and maximum 2 newlines
- **Why**: Clean, readable formatting

### Example: Before and After Cleaning

**Original Transcript:**
```
CHAPTER 1: INTRODUCTION

[Narrator: The following is a transcript from an interview conducted in 2023]

Interviewer: Tell me about your childhood.

This is the actual transcript content that should remain. It tells the story 
of growing up in a small village.

[12:34] Another important memory from those days.

(Redactor note: The interviewee became emotional at this point)

The village had a beautiful synagogue where everyone would gather. We had 
wonderful celebrations there.

Speaker 1: What about the festivals?

The festivals were the highlight of the year. Everyone would come together 
and celebrate with traditional songs and dances.

-------------------
Page 2
-------------------

SECTION 2: LATER YEARS

As I grew older, things began to change. [00:45:12] The community evolved 
and adapted to modern times while maintaining our traditions.
```

**Cleaned Transcript:**
```
This is the actual transcript content that should remain. It tells the story 
of growing up in a small village.

Another important memory from those days.

The village had a beautiful synagogue where everyone would gather. We had 
wonderful celebrations there.

The festivals were the highlight of the year. Everyone would come together 
and celebrate with traditional songs and dances.

As I grew older, things began to change. The community evolved and adapted 
to modern times while maintaining our traditions.
```

**Statistics from this example:**
- **Reduction**: 39.52%
- **Words removed**: 46
- **Lines removed**: 6
- **Pure transcript preserved**: 80 words of actual spoken content

The application shows you exactly what was removed in each category (bracketed notes, timestamps, headings, etc.) so you can verify the cleaning was done correctly.

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
   Navigate to `http://localhost:5000`

### Docker Deployment

1. **Build the Docker image**
   ```bash
   docker build -t yiddish-transcript-cleaner .
   ```

2. **Run the container**
   ```bash
   docker run -p 5000:5000 yiddish-transcript-cleaner
   ```

3. **Access the application**
   Navigate to `http://localhost:5000`

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
2. Drag and drop a Word document or click to browse
3. Click "Process Document"
4. View the results:
   - Statistics showing what was removed
   - Side-by-side comparison of original and cleaned text
   - Detailed list of removed content
5. Download the cleaned document

### Processing Google Drive Folders

1. Click on the "📁 Google Drive" tab
2. Paste the Google Drive folder URL
3. Click "Process Drive Folder"
4. View results for all documents in the folder
5. Download cleaned versions individually

## API Endpoints

The application provides the following REST API endpoints:

- `GET /` - Main web interface
- `POST /upload` - Upload and process a single document
- `POST /process-drive` - Process documents from Google Drive folder
- `POST /download-cleaned` - Download a cleaned document
- `GET /health` - Health check endpoint

## Development

### Project Structure

```
clean-yiddish-transcripts/
├── app.py                  # Flask application
├── cleaner.py             # Text cleaning logic
├── document_processor.py  # Document processing
├── drive_downloader.py    # Google Drive integration
├── requirements.txt       # Python dependencies
├── Dockerfile            # Docker configuration
├── templates/
│   └── index.html        # Web UI
├── uploads/              # Temporary upload storage
└── temp/                 # Temporary file storage
```

### Customizing Cleaning Rules

To modify what content gets removed, edit the `removal_patterns` list in `cleaner.py`. Each pattern is a tuple of:
- Regular expression pattern
- Description of what it matches

Example:
```python
(r'\[.*?\]', 'bracketed notes'),
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
- Open your browser and navigate to `http://localhost:5000`
- The application will run on port 5000 by default

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
docker run -d -p 5000:5000 --name yiddish-cleaner yiddish-transcript-cleaner
```
- `-d`: Run in detached mode (background)
- `-p 5000:5000`: Map port 5000 from container to host
- `--name`: Give the container a friendly name

**Step 4: Verify It's Running**
```bash
docker ps
```
You should see your container listed as running.

**Step 5: Access the Application**
- Open your browser and navigate to `http://localhost:5000`

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

Google Cloud Run is a serverless platform that automatically scales your application.

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
  --allow-unauthenticated
```

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