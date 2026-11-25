# CLINIQ AI | MEDUSA-X

### Agentic Clinical Intelligence for Patient Reconstruction

**Transforming fragmented medical records into structured, chronological, and clinically meaningful patient histories.**

CLINIQ AI is a healthcare intelligence prototype designed to help organize and analyze fragmented clinical records. It uses PDF text extraction, OCR, structured patient records, chronological timelines, rule-based clinical observations, and conservative report comparison to support clinician-supervised review.

The project combines a **FastAPI + SQLite backend** with two frontend interfaces:
- **React + Vite:** Modern healthcare SaaS dashboard.
- **Streamlit:** Original clinical dashboard.

> **Current implementation:** The clinical intelligence pipeline is deterministic and rule-based. Autonomous multi-agent orchestration and external AI integration are future development goals.

---

## 1. The Problem

Patient medical histories are frequently scattered across multiple reports, departments, and dates.

This creates several challenges:

- Reviewing multiple medical reports manually is time-consuming.
- Patient information may be distributed across different documents.
- Important clinical changes can be difficult to track.
- Missing dates, incomplete information, and inconsistent statements can be overlooked.
- Medical terminology can be difficult for patients and non-specialist reviewers to understand.

## 2. Our Solution

CLINIQ AI creates a centralized patient record from uploaded clinical PDFs.

It extracts available information, organizes reports chronologically, identifies selected clinical patterns, compares compatible reports, and provides plain-language terminology explanations.

### Core Workflow

1. Upload medical PDF reports.
2. Extract text using PyMuPDF or Tesseract OCR.
3. Identify patient and study information.
4. Store extracted records in SQLite.
5. Build patient-specific clinical timelines.
6. Analyze selected findings using deterministic rules.
7. Compare previous and latest compatible reports.
8. Present results through an interactive dashboard.

---

## 3. Key Features

### A. Document Intelligence
- Multiple PDF upload.
- Selectable-text extraction using PyMuPDF.
- OCR fallback using Tesseract.
- Extraction of available patient details, study information, findings, and impressions.
- PDF report storage and retrieval.

### B. Patient Management
- Patient identification and organization.
- Patient-specific report repository.
- Patient demographics and report counts.
- Centralized patient selection across dashboard pages.

### C. Patient Intelligence
- Combined patient analysis.
- Latest report overview.
- Rule-based clinical observations.
- Plain-language medical terminology explanations.
- Source-context visibility.

### D. Clinical Timeline
- Chronological report organization.
- Parsed study dates.
- Dated and undated report handling.
- Historical findings and impressions.

### E. Conflict Intelligence
Separates three important categories:

- **Missing Information:** Incomplete dates, diagnoses, and source information.
- **Potential Contradictions:** Selected opposing assertions in comparable records.
- **Clinical Changes:** Newly appearing, improving, worsening, unchanged, and no-longer-mentioned findings.

Also supports limited medication-status and unit-matched numeric laboratory comparisons when explicitly extracted.

### F. Patient Reconstruction
- Consolidated patient overview.
- Historical report information.
- Longitudinal clinical observations.
- Missing information disclosure.
- Keyword search across available patient report content.

### G. Medication Reconciliation
- Displays medication-status changes identified by the existing rule-based analyzer.
- Shows previous and latest report context when available.
- Supports session-only clinician review notes.

**Limitation:** Structured medication rosters, dosage and frequency extraction, drug interaction alerts, and persistent medication review workflows are not implemented.

### H. Modern React Dashboard
The React frontend contains eight connected pages:

1. Overview Dashboard
2. Patient Management
3. Patient Intelligence
4. Document Center
5. Clinical Timeline
6. Conflict Intelligence
7. Patient Reconstruction
8. Medication Reconciliation

The React application communicates with the existing FastAPI backend through HTTP APIs.

---

## 4. Technology Stack

| Layer | Technologies |
|---|---|
| Backend | Python, FastAPI, Uvicorn |
| Database | SQLite, SQLAlchemy |
| PDF Processing | PyMuPDF |
| OCR | Tesseract, Pytesseract |
| Original Frontend | Streamlit |
| Modern Frontend | React, Vite |
| Styling | Tailwind CSS |
| Routing | React Router |
| API Communication | Axios |
| Charts | Recharts |
| Icons | Lucide React |

---

## 5. System Architecture

```text
                 MEDICAL PDF REPORTS
                         |
                         v
              PDF EXTRACTION & OCR
               PyMuPDF + Tesseract
                         |
                         v
                 FASTAPI BACKEND
                         |
             +-----------+-----------+
             |           |           |
             v           v           v
         Extractor   Clinical    Intelligence
                     Analysis     Engine
             |           |           |
             +-----------+-----------+
                         |
                         v
                  SQLITE DATABASE
                         |
                         v
                  FASTAPI REST API
                         |
                +--------+--------+
                |                 |
                v                 v
           REACT FRONTEND    STREAMLIT FRONTEND
           Modern SaaS       Original Dashboard
           8 Pages           7 Sections
```

### Main Backend Components

- `backend/main.py` — FastAPI application and API endpoints.
- `backend/extractor.py` — PDF text and medical metadata extraction.
- `backend/clinical.py` — Patient ID validation, date parsing, and clinical flags.
- `backend/intelligence.py` — Report comparison and terminology explanations.
- `backend/conflict_detection.py` — Missing information, potential contradictions, and selected clinical changes.
- `backend/database.py` — SQLite connection and database configuration.
- `backend/models.py` — SQLAlchemy database models.

---

## 6. Project Structure

```text
MEDUSA_X HACK/
│
├── backend/
│   ├── main.py
│   ├── extractor.py
│   ├── clinical.py
│   ├── intelligence.py
│   ├── conflict_detection.py
│   ├── database.py
│   └── models.py
│
├── frontend/
│   ├── app.py
│   ├── api_client.py
│   ├── components.py
│   ├── demo_data.py
│   ├── document_handler.py
│   └── requirements.txt
│
├── web-frontend/
│   ├── src/
│   │   ├── api/
│   │   ├── components/
│   │   ├── context/
│   │   ├── pages/
│   │   ├── data/
│   │   ├── App.jsx
│   │   └── main.jsx
│   ├── public/
│   ├── package.json
│   ├── package-lock.json
│   ├── vite.config.js
│   └── .env.example
│
├── conflit_detection/
├── .gitignore
├── requirements.txt
└── README.md
```

---

## 7. Installation

### Prerequisites

- Python 3.13
- Node.js and npm
- Tesseract OCR for scanned PDF processing
- Git

### Step 1: Clone the Repository

```powershell
git clone https://github.com/asfiya-khanum/CLINIQ-AI.git
cd CLINIQ-AI
```

### Step 2: Set Up Python Environment

```powershell
python -m venv .venv
```

Install backend dependencies:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Install Streamlit frontend dependencies:

```powershell
.\.venv\Scripts\python.exe -m pip install -r frontend\requirements.txt
```

### Step 3: Install Tesseract OCR

Install Tesseract OCR for Windows.

The current backend configuration expects:

```text
C:\Program Files\Tesseract-OCR\tesseract.exe
```

If Tesseract is installed elsewhere, update the configured executable path.

### Step 4: Install React Dependencies

```powershell
cd web-frontend
npm install
```

Optional: Configure the backend URL in `web-frontend/.env`:

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
```

Return to the project root when needed:

```powershell
cd ..
```

---

## 8. Running the Application

Start the backend first.

### Terminal 1: FastAPI Backend

From the project root:

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Backend:

http://127.0.0.1:8000

API documentation:

http://127.0.0.1:8000/docs

### Terminal 2: React Frontend

```powershell
cd web-frontend
npm run dev
```

React dashboard:

http://localhost:5173

### Optional: Original Streamlit Frontend

Open another terminal at the project root:

```powershell
.\.venv\Scripts\python.exe -m streamlit run frontend/app.py
```

Streamlit dashboard:

http://localhost:8501

---

## 9. API Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/` | Backend status |
| GET | `/health` | Health check |
| POST | `/upload-pdfs` | Upload and process PDFs |
| GET | `/dashboard/overview` | Dashboard statistics |
| GET | `/patients` | List patients |
| GET | `/patients/{id}` | Patient profile |
| GET | `/patients/{id}/reports` | Patient reports |
| GET | `/patients/{id}/timeline` | Clinical timeline |
| GET | `/patients/{id}/compare` | Compare reports |
| GET | `/patients/{id}/analysis` | Combined patient analysis |
| GET | `/reports/{id}` | Individual report |
| GET | `/reports/{id}/analysis` | Individual report analysis |

Interactive API documentation is available at:

http://127.0.0.1:8000/docs

---

## 10. Current Limitations

CLINIQ AI is an evolving hackathon prototype.

- **Rule-Based Intelligence:** Current clinical observations, comparisons, and terminology explanations use deterministic Python rules. Autonomous multi-agent orchestration is not implemented.
- **External AI:** No external LLM API is currently active.
- **Medication Extraction:** Comprehensive structured medication name, dosage, and frequency extraction is not implemented.
- **Laboratory Extraction:** Comprehensive laboratory panel parsing is not implemented.
- **Report Variability:** Extraction quality depends on report formatting and available text.
- **Authentication:** Production-grade authentication and role-based access control are future work.
- **Clinical Validation:** The system has not been clinically validated.

### Future Enhancements

- Specialized agentic clinical workflows.
- More comprehensive medication and laboratory extraction.
- Optional locally hosted AI models.
- Source-grounded clinical summarization.
- Authentication and access control.
- Improved report deduplication.
- Expanded testing across different medical report formats.

---

## 11. Clinical Safety Disclaimer

**CLINIQ AI is a hackathon prototype for informational clinical support.**

It is not a medical device, diagnostic system, or replacement for professional medical judgment.

All extracted information, clinical observations, report comparisons, and terminology explanations must be reviewed and verified by qualified healthcare professionals.

The system does not prescribe treatment, independently diagnose diseases, or automatically classify report differences as medical errors.

---

## 12. Project Repository

**GitHub:** https://github.com/asfiya-khanum/CLINIQ-AI

Built for the MEDUSA-X healthcare AI hackathon.

**Turning fragmented clinical records into structured patient intelligence.**