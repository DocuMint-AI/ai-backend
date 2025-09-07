# Google Vision API Setup Guide

This guide provides step-by-step instructions for setting up Google Vision API for use with the AI backend system.

---

## 1. Google Cloud Platform Setup

### 1.1 Create Google Cloud Account
- Go to https://console.cloud.google.com/
- Sign in and set up billing (required for API usage)

### 1.2 Create a New Project
- Click "Select a project" > "New Project"
- Enter project name (e.g., `ai-backend-ocr`)
- Click "Create" and select your new project

---

## 2. Enable Vision API
- Go to "APIs & Services" > "Library"
- Search for "Cloud Vision API"
- Click and "Enable" the API
- Confirm it appears in "Enabled APIs"

---

## 3. Create Service Account & Download Credentials

### 3.1 Create Service Account
- Go to "IAM & Admin" > "Service Accounts"
- Click "Create Service Account"
- Name: `ai-backend-vision-sa`
- Click "Create and Continue"
- Grant roles: "Cloud Vision API Service Agent" and (optionally) "Storage Object Viewer"
- Click "Done"

### 3.2 Download Credentials JSON
- Click your service account's email
- Go to "Keys" tab > "Add Key" > "Create new key"
- Select "JSON" and download the file
- Move it to a secure location (e.g., `~/.config/gcloud/vision-credentials.json`)
- Set permissions: `chmod 600 ~/.config/gcloud/vision-credentials.json`

---

## 4. Configure Environment

### 4.1 .env File Example
```
GOOGLE_CLOUD_PROJECT_ID=ai-backend-ocr
GOOGLE_CLOUD_CREDENTIALS_PATH=/home/sborra/.config/gcloud/vision-credentials.json
LANGUAGE_HINTS=en,es,fr
DATA_ROOT=/home/sborra/Documents/nainovate/ai-backend/data
IMAGE_FORMAT=PNG
IMAGE_DPI=300
```

### 4.2 (Optional) System Environment Variables
```
export GOOGLE_APPLICATION_CREDENTIALS="/home/sborra/.config/gcloud/vision-credentials.json"
export GOOGLE_CLOUD_PROJECT="ai-backend-ocr"
```

---

## 5. Install Dependencies
```
pip install google-cloud-vision python-dotenv Pillow PyMuPDF fastapi uvicorn
# Or: pip install -r requirements.txt
```

---

## 6. Test Your Setup

### 6.1 Test Script
Create `test_vision_setup.py`:
```python
import os
from google.cloud import vision
from dotenv import load_dotenv

load_dotenv()

def test_vision_api():
    try:
        client = vision.ImageAnnotatorClient()
        print("✅ Vision API client created successfully!")
        print(f"Project ID: {os.getenv('GOOGLE_CLOUD_PROJECT_ID')}")
        print(f"Credentials path: {os.getenv('GOOGLE_CLOUD_CREDENTIALS_PATH')}")
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    test_vision_api()
```

### 6.2 Run the Test
```
python test_vision_setup.py
```

---

## 7. Start the FastAPI Service
```
cd services
python processing-handler.py
# Or:
uvicorn processing-handler:app --host 0.0.0.0 --port 8000 --reload
```

---

## 8. Troubleshooting
- **Authentication Error**: Check credentials path and permissions
- **Permission Denied**: Ensure service account has correct roles
- **API Not Enabled**: Enable Vision API in Google Cloud Console
- **Project Not Found**: Verify project ID in .env matches Google Cloud Console

---

## 9. Security Best Practices
- Never commit credentials.json or .env to git
- Use `.gitignore` to exclude sensitive files
- Store credentials securely and set correct permissions

---

Your Google Vision API is now ready for use with the AI backend OCR pipeline!
