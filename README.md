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
backend/
├── backend/              # FastAPI + pipeline services
│   ├── main.py           # API entry point
│   └── services/         # Core pipeline steps (storage, parsing, etc.)
├── models/               # Model configs (InLegalBert, classifiers)
├── infra/                # Deployment (Docker, K8s, CI/CD)
├── tests/                # Unit & integration tests
├── docs/                 # Documentation
└── README.md
