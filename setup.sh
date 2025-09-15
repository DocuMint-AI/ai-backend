#!/bin/bash
# Setup script for AI Backend OCR Pipeline
# Creates virtual environment and installs dependencies

set -e

echo "🚀 Setting up AI Backend OCR Pipeline..."

# Check if Python 3.8+ is available
python_version=$(python3 --version 2>&1 | grep -oP '\d+\.\d+' | head -1)
if [[ $(echo "$python_version < 3.8" | bc -l) -eq 1 ]]; then
    echo "❌ Python 3.8+ is required. Current version: $python_version"
    exit 1
fi

echo "✅ Python version: $python_version"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
else
    echo "✅ Virtual environment already exists"
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "⬆️ Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "📋 Installing dependencies from requirements.txt..."
pip install -r requirements.txt

# Create data directories if they don't exist
echo "📁 Setting up data directories..."
mkdir -p data/.cheetah/gcloud
mkdir -p data/uploads
mkdir -p data/processed

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "⚙️ Creating .env template..."
    cat > .env << EOF
# Google Cloud Configuration
GOOGLE_CLOUD_PROJECT_ID=your-project-id
GOOGLE_APPLICATION_CREDENTIALS=./data/.cheetah/gcloud/vision-credentials.json

# OCR Configuration
OCR_LANGUAGE_HINTS=en,es,fr
MAX_FILE_SIZE_MB=50
PDF_DPI=300
PDF_FORMAT=PNG

# Server Configuration
SERVER_HOST=0.0.0.0
SERVER_PORT=8000
DEBUG=False
EOF
    echo "📝 Please update .env file with your Google Cloud project ID and credentials"
else
    echo "✅ .env file already exists"
fi

echo ""
echo "🎉 Setup complete!"
echo ""
echo "Available commands:"
echo "1. Activate the environment and start the server:"
echo "   source venv/bin/activate"
echo "   python services/processing-handler.py"
echo ""
echo "2. Test the API:"
echo "   curl http://localhost:8000/health"
echo ""
echo "3. Run API tests:"
echo "   python tests/test_api_endpoints.py"
echo ""
echo "4. Data management:"
echo "   python scripts/purge.py --quick       # Clean uploads and temp files"
echo "   python scripts/purge.py --full        # Clean all processing data"
echo "   python scripts/purge.py --dry-run     # Preview what would be deleted"
echo ""
echo "Next steps:"
echo "1. Place your Google Cloud service account credentials in:"
echo "   ./data/.cheetah/gcloud/vision-credentials.json"
echo ""
echo "2. Update .env file with your project ID"
echo ""