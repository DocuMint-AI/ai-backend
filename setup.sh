#!/bin/bash
# Setup script for AI Backend OCR Pipeline
# Creates virtual environment and installs dependencies using uv

set -e

echo "🚀 Setting up AI Backend OCR Pipeline..."

# Check if uv is available
if ! command -v uv &> /dev/null; then
    echo "📦 uv not found, installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    source $HOME/.cargo/env
    if ! command -v uv &> /dev/null; then
        echo "❌ Failed to install uv"
        exit 1
    fi
    echo "✅ uv installed successfully"
else
    echo "✅ uv found"
fi

# Create virtual environment using uv
if [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment with uv..."
    uv venv
else
    echo "✅ Virtual environment already exists"
fi

# Install dependencies using uv
echo "📋 Installing dependencies from requirements.txt..."
uv pip install -r requirements.txt

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
echo "1. Start the server:"
echo "   uv run main.py"
echo ""
echo "2. Test the API:"
echo "   curl http://localhost:8000/health"
echo ""
echo "3. Run API tests:"
echo "   uv run tests/test_api_endpoints.py"
echo ""
echo "4. Data management:"
echo "   uv run scripts/purge.py --quick       # Clean uploads and temp files"
echo "   uv run scripts/purge.py --full        # Clean all processing data"
echo "   uv run scripts/purge.py --dry-run     # Preview what would be deleted"
echo ""
echo "Next steps:"
echo "1. Place your Google Cloud service account credentials in:"
echo "   ./data/.cheetah/gcloud/vision-credentials.json"
echo ""
echo "2. Update .env file with your project ID"
echo ""