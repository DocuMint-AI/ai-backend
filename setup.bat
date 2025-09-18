@echo off
REM Setup script for AI Backend OCR Pipeline (Windows)
REM Creates virtual environment and installs dependencies using uv

echo 🚀 Setting up AI Backend OCR Pipeline...

REM Check if uv is available
uv --version >nul 2>&1
if errorlevel 1 (
    echo 📦 uv not found, installing uv...
    powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
    if errorlevel 1 (
        echo ❌ Failed to install uv
        exit /b 1
    )
    echo ✅ uv installed successfully
) else (
    echo ✅ uv found
)

REM Create virtual environment using uv
if not exist ".venv" (
    echo 📦 Creating virtual environment with uv...
    uv venv
) else (
    echo ✅ Virtual environment already exists
)

REM Install dependencies using uv
echo 📋 Installing dependencies from requirements.txt...
uv pip install -r requirements.txt

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
echo 1. Start the server:
echo    uv run main.py
echo.
echo 2. Test the API:
echo    curl http://localhost:8000/health
echo.
echo 3. Run API tests:
echo    uv run tests\test_api_endpoints.py
echo.
echo 4. Data management:
echo    uv run scripts\purge.py --quick       # Clean uploads and temp files
echo    uv run scripts\purge.py --full        # Clean all processing data
echo    uv run scripts\purge.py --dry-run     # Preview what would be deleted
echo.
echo Next steps:
echo 1. Place your Google Cloud service account credentials in:
echo    .\data\.cheetah\gcloud\vision-credentials.json
echo.
echo 2. Update .env file with your project ID
echo.