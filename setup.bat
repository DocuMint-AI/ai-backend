@echo off
REM Setup script for AI Backend OCR Pipeline (Windows)
REM Creates virtual environment and installs dependencies

echo 🚀 Setting up AI Backend OCR Pipeline...

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python is not installed or not in PATH
    exit /b 1
)

echo ✅ Python found

REM Create virtual environment if it doesn't exist
if not exist "venv" (
    echo 📦 Creating virtual environment...
    python -m venv venv
) else (
    echo ✅ Virtual environment already exists
)

REM Activate virtual environment
echo 🔧 Activating virtual environment...
call venv\Scripts\activate.bat

REM Upgrade pip
echo ⬆️ Upgrading pip...
python -m pip install --upgrade pip

REM Install dependencies
echo 📋 Installing dependencies from requirements.txt...
pip install -r requirements.txt

REM Create data directories if they don't exist
echo 📁 Setting up data directories...
if not exist "data\.cheetah\gcloud" mkdir data\.cheetah\gcloud
if not exist "data\uploads" mkdir data\uploads
if not exist "data\processed" mkdir data\processed

REM Check if .env file exists
if not exist ".env" (
    echo ⚙️ Creating .env template...
    (
        echo # Google Cloud Configuration
        echo GOOGLE_CLOUD_PROJECT_ID=your-project-id
        echo GOOGLE_APPLICATION_CREDENTIALS=./data/.cheetah/gcloud/vision-credentials.json
        echo.
        echo # OCR Configuration
        echo OCR_LANGUAGE_HINTS=en,es,fr
        echo MAX_FILE_SIZE_MB=50
        echo PDF_DPI=300
        echo PDF_FORMAT=PNG
        echo.
        echo # Server Configuration
        echo SERVER_HOST=0.0.0.0
        echo SERVER_PORT=8000
        echo DEBUG=False
    ) > .env
    echo 📝 Please update .env file with your Google Cloud project ID and credentials
) else (
    echo ✅ .env file already exists
)

echo.
echo 🎉 Setup complete!
echo.
echo Available commands:
echo 1. Activate the environment and start the server:
echo    venv\Scripts\activate.bat
echo    python services\processing-handler.py
echo.
echo 2. Test the API:
echo    curl http://localhost:8000/health
echo.
echo 3. Run API tests:
echo    python tests\test_api_endpoints.py
echo.
echo 4. Data management:
echo    python scripts\purge.py --quick       # Clean uploads and temp files
echo    python scripts\purge.py --full        # Clean all processing data
echo    python scripts\purge.py --dry-run     # Preview what would be deleted
echo.
echo Next steps:
echo 1. Place your Google Cloud service account credentials in:
echo    .\data\.cheetah\gcloud\vision-credentials.json
echo.
echo 2. Update .env file with your project ID
echo.