# Clean Yiddish Transcripts

A web application for cleaning Yiddish transcripts—removing titles, narrator notes, timestamps, seif markers, and other editorial content to extract pure spoken content.

## Features

- 📄 Process Word documents (.doc, .docx)
- 📁 Google Drive folder integration
- 📊 Google Sheets batch processing with clean rate tracking
- 🔌 Modular plugin system for selective cleaning
- ⬇️ Export as .docx or .txt

## Quick Start

```bash
git clone https://github.com/Shloimy15e/clean-yiddish-transcripts.git
cd clean-yiddish-transcripts
pip install -r requirements.txt
python app.py
```

Open `http://localhost:5050`

**Docker:**
```bash
docker build -t yiddish-transcript-cleaner .
docker run -p 5050:5050 yiddish-transcript-cleaner
```

## Processing Plugins

| Plugin | Description | Default |
|--------|-------------|---------|
| **special_chars** | Removes invisible Unicode characters (zero-width spaces, BOMs) | ✅ |
| **seif_marker** | Removes Hebrew gematria markers (א. ב*. יב.) | ✅ |
| **title_style** | Removes titles based on Word styles, large fonts, short paragraphs | ✅ |
| **brackets_inline** | Removes inline [bracketed notes], keeps full bracketed paragraphs | ✅ |
| **whitespace** | Normalizes excessive whitespace | ✅ |
| **editorial_hebrew** | Removes editorial Hebrew (citations, cross-references) | ❌ |
| **parentheses_notes** | Removes non-speech parenthetical content | ❌ |
| **force_remove** | Force removes specific blocked patterns | ❌ |

## Cleaning Profiles

| Profile | Use Case |
|---------|----------|
| **5710-5711 Transcripts** | Basic cleaning without bracket removal |
| **5712+ Transcripts** | Standard cleaning with inline brackets removed |
| **With Editorial Removal** | Includes editorial Hebrew detection |
| **Heavy Cleaning** | All processors enabled |
| **Minimal** | Only special_chars + whitespace |

## What Gets Removed

- **Seif markers**: `א.`, `ב*.`, `יב.`
- **Headings**: Chapter/section titles, speaker labels (`INTERVIEWER:`)
- **Timestamps**: `[12:34]`, `[00:45:12]`
- **Inline brackets**: `[Narrator: note]`, `[laughing]`
- **Editorial citations**: `(תהלים קיט, א)`, `ראה שמות כ, ג`
- **Page markers**: `Page 2`, `-------------------`

**Kept**: Spoken content, parenthetical translations `(דער קליינער דארף)`, full bracketed paragraphs

## Clean Rate Score

Each document receives a confidence score (0-100):
- **90-100**: Excellent confidence
- **75-89**: Good confidence  
- **50-74**: Review recommended
- **Below 50**: Manual review needed

## Google Drive Setup (Optional)

1. Create a [Google Cloud Project](https://console.cloud.google.com/) and enable Drive API
2. Create OAuth 2.0 credentials (Desktop app)
3. Save as `credentials.json` in project root
4. Authenticate on first use

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `POST /upload` | Process single document |
| `POST /process-drive` | Process Google Drive folder |
| `POST /process-sheet` | Batch process from Google Sheet |
| `GET /processors` | List available plugins |
| `GET /health` | Health check |

## Development

### Add a Processor

```python
# processors/my_processor.py
from registry import ProcessorRegistry
from processors.base import BaseProcessor

@ProcessorRegistry.register
class MyProcessor(BaseProcessor):
    name = "my_processor"
    description = "Description for UI"
    
    def process(self, text, context=None):
        removed_items = []
        # Processing logic
        return cleaned_text, removed_items
```

### Project Structure

```
├── app.py                 # Flask application
├── cleaner.py             # Cleaning orchestration
├── clean_rate.py          # Scoring system
├── processors/            # Processing plugins
├── writers/               # Output format plugins
└── templates/index.html   # Web UI
```

## Deployment

**Heroku:**
```bash
heroku create your-app-name
git push heroku main
```

**Google Cloud Run:**
```bash
gcloud run deploy yiddish-transcript-cleaner --source . --allow-unauthenticated
```

**Production checklist:**
- Set `FLASK_ENV=production`
- Set secure `SECRET_KEY`
- Configure HTTPS

## License

MIT License
