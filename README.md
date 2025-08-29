# Legal AI Platform

An AI-powered legal document analysis and Q&A system.  
Built on **FastAPI/Vertex AI/Google Cloud (backend)**.

---

## 🚀 Project Overview

### Minimum Viable Prototype (MVP)
- Upload single documents (`.pdf`, `.docx`, `.txt`).
- Store documents in Google Cloud Storage.
- Normalize and parse with OCR + Document AI.
- Classify main document type with Vertex AI.
- Use InLegalBert for Knowledge-Augmented Generation (KAG).
- Q&A agent responds via chat window with inline insights.
- Logs stored in Cloud Logging + BigQuery.

### Full Product
- Multi-document upload & session management.
- Advanced parsing pipelines tailored for Indian legal docs.
- Hierarchical classification (type + subtype).
- Fine-tuned InLegalBert + dynamic knowledge graph integration.
- Dedicated Insights Agent for deep risk analysis.
- Semantic comparison across multiple documents.
- Voice input support (Google STT).
- Secure, compliant with legal standards (encryption, audit logs).
- Continuous feedback → retraining loop.

---

## 📂 Backend Project Structure

```bash
legal-ai-platform/
│
├── backend/                 # All backend logic
│   ├── main.py              # Entry point (FastAPI/Express)
│   ├── services/            # Core pipeline steps
│   │   ├── storage.py       # GCS upload + metadata
│   │   ├── preprocessing.py # Normalization + OCR
│   │   ├── parsing.py       # DocAI client
│   │   ├── classification.py# Vertex AI model
│   │   ├── kag.py           # InLegalBert + KB
│   │   ├── agents.py        # QnA + Insights
│   │   ├── comparison.py    # Multi-doc semantic search
│   │   └── monitoring.py    # Logging + feedback
│   └── security.py          # Auth, audit logs, compliance
│
├── models/                  # Model configs
│   ├── inlegalbert_config.json
│   └── classification_config.json
│
├── infra/                   # Deployment
│   ├── dockerfiles/
│   ├── k8s/
│   └── ci_cd/
│
├── tests/                   # Tests for backend & frontend
│
├── docs/                    # Documentation
│   ├── mvp_pipeline.md
│   └── full_pipeline.md
│
└── README.md

