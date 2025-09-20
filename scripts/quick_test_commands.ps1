# Orchestration Quick Test Commands
# Copy and paste these commands to quickly validate the orchestration system

# ===== QUICK VALIDATION =====

# 1. Basic health check
uv run python -c "from fastapi.testclient import TestClient; from main import app; client = TestClient(app); print(f'Health: {client.get('/api/v1/health').status_code}')"

# 2. Run comprehensive test
uv run python tests/test_complete_orchestration.py

# 3. Check user session folders
Get-ChildItem "data\processed" | Where-Object { $_.PSIsContainer } | Sort-Object CreationTime -Descending | Select-Object Name, CreationTime -First 5

# ===== DETAILED VALIDATION =====

# 4. Test PDF processing directly
uv run python -c "import sys; from pathlib import Path; sys.path.insert(0, str(Path.cwd())); from services.util_services import PDFToImageConverter; from services.project_utils import get_username_from_env; username = get_username_from_env(); converter = PDFToImageConverter(data_root='./data', username=username); uid, images, metadata = converter.convert_pdf_to_images('data/uploads/testing-ocr-pdf-1.pdf'); print(f'✅ Processed: {username}-{uid}, Images: {len(images)}')"

# 5. Verify folder structure
$newest = Get-ChildItem "data\processed" | Where-Object { $_.PSIsContainer -and $_.Name -match "^.*-.*$" } | Sort-Object CreationTime -Descending | Select-Object -First 1; if ($newest) { echo "📁 $($newest.Name)"; Get-ChildItem $newest.FullName | Select-Object Name, PSIsContainer | Format-Table }

# 6. Test user session utilities
uv run python -c "import sys; from pathlib import Path; sys.path.insert(0, str(Path.cwd())); from services.project_utils import get_username_from_env, generate_user_uid, get_user_session_structure; username = get_username_from_env(); uid = generate_user_uid('test.pdf'); session = get_user_session_structure('test.pdf', username, uid); print(f'✅ Session: {session[\"user_session_id\"]}'); print(f'📁 Path: {session[\"base_path\"]}')"

# ===== INTEGRATION TESTING =====

# 7. Run full integration test
uv run python tests/test_complete_orchestration.py --integration

# 8. Test vision-to-docai pipeline
uv run python scripts/test_vision_to_docai_simple.py

# ===== VALIDATION CHECKS =====

# 9. Check naming convention
Get-ChildItem "data\processed" | Where-Object { $_.PSIsContainer } | ForEach-Object { $name = $_.Name; if ($name -match "^[a-zA-Z0-9_]+-[a-zA-Z0-9_-]+$") { echo "✅ $name" } else { echo "⚠️ $name" } }

# 10. Count files in user sessions
$user_folders = Get-ChildItem "data\processed" | Where-Object { $_.PSIsContainer -and $_.Name -match "^.*-.*$" }; foreach ($folder in $user_folders) { $files = Get-ChildItem $folder.FullName -Recurse -File; echo "$($folder.Name): $($files.Count) files" }

# ===== CLEANUP =====

# 11. List test artifacts (don't delete automatically)
Get-ChildItem "data\processed" | Where-Object { $_.Name -like "test_user-*" -or $_.Name -like "*-metadata_*" } | Select-Object Name, CreationTime

# 12. Generate test report
uv run python tests/test_complete_orchestration.py 2>&1 | Tee-Object -FilePath "orchestration_test_results.log"

# ===== SUCCESS INDICATORS =====
# Look for:
# - User session folders with format: username-UID
# - Subdirectories: artifacts/, uploads/, pipeline/, metadata/, diagnostics/
# - Test success rate: 93%+ (14+ tests passing)
# - PDF processing: 6 PNG images generated
# - Health endpoint: 200 status code