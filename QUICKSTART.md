# 🚀 Quick Start Guide - AI Backend OCR Pipeline

Get your DocAI-compliant OCR pipeline running in 5 minutes!

## Prerequisites ✅

- **Python 3.8+** (check: `python3 --version`)
- **Google Cloud Project** with billing enabled
- **Service Account** with Vision API permissions

## Step 1: Clone & Setup ⚡

```bash
# Clone the repository
git clone <repository-url>
cd ai-backend

# Run automated setup
./setup.sh                    # Linux/macOS
# OR
setup.bat                     # Windows

# This creates virtual environment and installs all dependencies
```

## Step 2: Google Cloud Configuration 🔧

### 2.1 Get Your Credentials
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create/select your project
3. Enable **Cloud Vision API**
4. Create **Service Account** → Download JSON credentials

### 2.2 Place Credentials
```bash
# Save your credentials file as:
cp your-downloaded-file.json data/.cheetah/gcloud/vision-credentials.json
```

### 2.3 Update Project ID
Edit `.env` file:
```env
GOOGLE_CLOUD_PROJECT_ID=your-actual-project-id
```

## Step 3: Test Everything 🧪

```bash
# Activate environment
source venv/bin/activate       # Linux/macOS
# venv\\Scripts\\activate.bat   # Windows

# Test connection
python test_vision_connection.py

# Expected output:
# ✓ OCR instance created successfully
# ✓ OCR processing completed successfully  
# ✓ DocAI document created successfully
# 🎉 SUCCESS: Google Vision API is working correctly!
```

## Step 4: Start the Server 🌐

```bash
# Start FastAPI server
python services/processing-handler.py

# Server starts on: http://localhost:8000
```

## Step 5: Test the API 📡

### Health Check
```bash
curl http://localhost:8000/health
```

### Upload a Document
```bash
curl -X POST "http://localhost:8000/upload" \\
     -F "file=@your-document.pdf"

# Returns: {"uid": "doc_20250915_...", "status": "uploaded"}
```

### Process with OCR
```bash
curl -X POST "http://localhost:8000/ocr-process" \\
     -H "Content-Type: application/json" \\
     -d '{"uid": "your-uid-from-upload"}'

# Returns: {"status": "completed", "docai_format": true}
```

### Get Results (DocAI Format)
```bash
curl http://localhost:8000/results/your-uid

# Returns complete DocAI-compliant JSON
```

## 🎯 That's It! Your Pipeline is Ready

### What You Get:
- ✅ **DocAI-compliant output** with stable identifiers
- ✅ **Multi-language OCR** (EN, ES, FR)
- ✅ **Production-ready API** with health monitoring
- ✅ **Automatic documentation** at http://localhost:8000/docs

## Quick Commands Reference 📚

```bash
# Activate environment
source venv/bin/activate

# Start server
python services/processing-handler.py

# Test connection
python test_vision_connection.py

# Run tests
python -m pytest tests/

# Check health
curl http://localhost:8000/health
```

## Troubleshooting 🔧

| Issue | Solution |
|-------|----------|
| `403 Billing disabled` | Enable billing in Google Cloud Console |
| `Credentials not found` | Check `.env` file and credentials path |
| `Import errors` | Activate venv: `source venv/bin/activate` |
| `Permission denied` | Ensure service account has Vision API role |

## Next Steps 🚀

1. **API Documentation**: Visit http://localhost:8000/docs
2. **Test with Real Documents**: Upload PDFs through the API
3. **Integration**: Use the API endpoints in your application
4. **Production**: See `docs/README-COMPLETE.md` for deployment guide

## Support 💬

- **Health Check**: `curl http://localhost:8000/health`
- **Test Script**: `python test_vision_connection.py`
- **Logs**: Check terminal output for detailed error messages
- **Documentation**: See `docs/README-COMPLETE.md` for full guide

---

**🎉 Congratulations!** Your DocAI-compliant OCR pipeline is now ready for production use!