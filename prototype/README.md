# AI-Backend Prototype — PDF → OCR → Classify → KAG → RAG

This `prototype/` folder contains a self-contained, runnable pipeline that converts a PDF into KAG-ready JSON and prepares chunks for a RAG QA/Insights system.

Targets
- Hybrid PDF rendering (PyMuPDF or pypdfium2 + pdfplumber)
- Google Vision OCR integration with per-page confidence aggregation
- Weighted, regex-based document classifier (dynamic keywords loader)
- KAG input generation and validation
- RAG adapter: chunking + metadata enrichment
- Smoke tests and reproducible run instructions (for hackathon submission)

---

## Quick Start (Linux / macOS / Windows PowerShell)

1. Create virtual env & install:
```bash
python -m venv .venv
source .venv/bin/activate        # macOS/Linux
# .venv\Scripts\Activate.ps1     # PowerShell Windows
pip install -r prototype/requirements.txt
```

2. Set Google credentials (if using Vision):

```bash
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/your/service-account.json"
# Windows (PowerShell):
# $env:GOOGLE_APPLICATION_CREDENTIALS="C:\path\to\service-account.json"
```

3. Run the orchestration on the sample PDF:

```bash
python prototype/orchestration/run_single_orchestration.py \
  --pdf prototype/data/test-files/testing-ocr-pdf-1.pdf \
  --out prototype/artifacts/run-001
```

4. Run smoke tests:

```bash
pytest -q prototype/tests/test_hybrid_pipeline.py
```

---

## Folder layout (prototype/)

```
prototype/
├─ orchestration/
│  └─ run_single_orchestration.py        # main entrypoint (refactored from test_single_orchestration.py)
├─ services/
│  ├─ util_services.py                   # hybrid PDF processing (pymupdf / pypdfium2 + pdfplumber)
│  ├─ ocr_processing.py                  # Google Vision OCR wrapper with confidence aggregation
│  ├─ kag_writer.py                       # KAG input generation & validation
│  ├─ rag_adapter.py                      # adapter: KAG -> RAG chunk format
│  └─ project_utils.py                    # path/session helpers
├─ template_matching/
│  ├─ regex_classifier.py                # weighted regex classifier
│  ├─ keywords_loader.py                 # dynamic loader for legal keywords (py or json)
│  └─ legal_keywords.py                  # your keyword dictionary (can be substituted with JSON)
├─ config/
│  └─ config.py                          # central config (env var wrappers)
├─ data/
│  └─ test-files/                        # sample PDFs used for smoke tests
├─ tests/
│  └─ test_hybrid_pipeline.py             # pytest smoke test (kag_input.json generation)
└─ README.md
```

---

## Important notes & best practices

* **Imports**: The `run_single_orchestration.py` uses relative imports within `prototype/`. If you run it from repo root, ensure `sys.path` or `PYTHONPATH` contains `prototype/` (the entrypoint sets this automatically if required).
* **Atomic writes**: All JSON outputs are written atomically (`.tmp` → final) to avoid half-written artifacts.
* **Logging**: Set `LOG_LEVEL=INFO` / `DEBUG` environment variable to get pipeline traces for debugging.
* **Classifier tuning**: Edit `template_matching/legal_keywords.py` or supply `template_matching/legal_keywords.json`. Use dict entries with `{"pattern": "...", "weight": X, "is_regex": bool}` for stronger signals.
* **OCR Confidence**: OCR module aggregates block/word/page confidence where available. If Vision returns `0.0`, module attempts reasonable estimations; inspect logs to verify.

---

## Troubleshooting

* If Vision returns authentication errors: ensure `GOOGLE_APPLICATION_CREDENTIALS` is set and the service account has Vision API permission.
* If images not created: verify `pypdfium2` or `PyMuPDF` is installed, fallback order is respected in `util_services.py`.
* If `kag_input.json` fails schema validation: open the artifact and confirm `parsed_document.full_text` exists and `metadata.source.gcs_uri` is set (the test runner uses `file://` URIs).

---

## Deliverables for Hackathon

* `prototype/orchestration/run_single_orchestration.py` — Entrypoint (single-command run)
* `prototype/tests/test_hybrid_pipeline.py` — Minimal smoke test for judges
* `prototype/README.md` & `requirements.txt` — Setup + run instructions