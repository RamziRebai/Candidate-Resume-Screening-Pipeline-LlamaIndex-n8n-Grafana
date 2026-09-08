# Google Drive Integration Setup Guide

This guide explains how to configure Google Drive integration for automatic PDF uploads.

## Prerequisites

- Google account
- Google Cloud Console access
- Python environment with required packages installed

## Step 1: Install Required Dependencies

The Google Drive dependencies are declared in `pyproject.toml`. Install the locked backend environment:

```bash
uv sync
```

After installing playwright, run:
```bash
uv run playwright install chromium
```

## Step 2: Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the **Google Drive API**:
   - Navigate to "APIs & Services" > "Library"
   - Search for "Google Drive API"
   - Click "Enable"

## Step 3: Create OAuth 2.0 Credentials

1. Go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "OAuth client ID"
3. Configure the OAuth consent screen if prompted:
   - User Type: External (for testing) or Internal (for organization)
   - App name: "Resume Matcher PDF Uploader"
   - User support email: Your email
   - Developer contact: Your email
4. Create OAuth client ID:
   - Application type: **Desktop app**
   - Name: "Resume Matcher Desktop Client"
5. Download the credentials file
6. Rename the downloaded file to `credentials.json`
7. Place `credentials.json` in the `backend/` directory

## Step 4: Configure Environment Variables (Optional)

Add to your `.env` file:

```env
# Google Drive folder ID (optional - if not set, files upload to root)
GOOGLE_DRIVE_FOLDER_ID=your_folder_id_here
```

To get a folder ID:
1. Open Google Drive in your browser
2. Navigate to the folder where you want to upload PDFs
3. Copy the folder ID from the URL: `https://drive.google.com/drive/folders/FOLDER_ID_HERE`

## Step 5: First-Time Authentication

1. Start your FastAPI server:
   ```bash
   uv run python main.py
   ```

2. When a user clicks "Skip and Approve All" for the first time:
   - A browser window will open automatically
   - Log in to your Google account
   - Grant permissions to the application
   - A `token.json` file will be created automatically

3. Subsequent runs will use the saved `token.json` for authentication

## File Structure

After setup, your backend directory should contain:

```
backend/
├── main.py
├── workflow_components.py
├── pyproject.toml
├── uv.lock
├── credentials.json       # OAuth credentials (DON'T commit to git!)
├── token.json            # Auto-generated after first auth (DON'T commit to git!)
├── .env
└── uploads/
    └── {session_id}/
        └── resume_report_*.pdf
```

## Security Best Practices

⚠️ **IMPORTANT**: Add these files to your `.gitignore`:

```gitignore
# Google credentials
credentials.json
token.json

# Uploaded files
uploads/
*.pdf
```

## Testing the Integration

1. Upload a resume and application form
2. Process the workflow
3. Click "Skip and Approve All"
4. Check the logs for:
   - ✅ PDF generation success message
   - ☁️ Google Drive upload progress
   - ✅ Google Drive upload success with link

## Troubleshooting

### Issue: "credentials.json not found"
**Solution**: Download OAuth credentials from Google Cloud Console and place in backend directory.

### Issue: "Playwright browser not found"
**Solution**: Run `uv run playwright install chromium` to download browser binaries.

### Issue: "Google Drive upload failed"
**Solution**: 
- Check that Google Drive API is enabled
- Verify credentials.json is valid
- Re-authenticate by deleting token.json and trying again

### Issue: PDF generation fails
**Solution**:
- Ensure the backend dependencies are installed: `uv sync`
- Install browser: `uv run playwright install chromium`
- Check that resume data contains required fields (First Name, Last Name, etc.)

## Optional: Skip Google Drive Upload

If you don't want to use Google Drive upload:
- Simply don't create `credentials.json`
- The system will generate PDFs locally in `uploads/{session_id}/`
- A warning will be logged but the workflow will continue normally

## API Response Format

When PDF generation and upload succeeds, the results will include:

```json
{
  "status": "completed",
  "fields": [...],
  "pdf_info": {
    "pdf_generated": true,
    "pdf_path": "uploads/session_id/resume_report_John_Doe_20251115_143022.pdf",
    "uploaded_to_drive": true,
    "drive_info": {
      "file_id": "1abc123...",
      "file_name": "resume_report_John_Doe_20251115_143022.pdf",
      "web_view_link": "https://drive.google.com/file/d/1abc123.../view"
    },
    "error": null
  }
}
```

## Support

For issues or questions:
1. Check the logs in the FastAPI terminal
2. Verify all dependencies are installed
3. Ensure Google Cloud project is properly configured
