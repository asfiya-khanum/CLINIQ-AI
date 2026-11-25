# MEDUSA-X / CLINIQ AI

**Agentic Clinical Intelligence for Patient Reconstruction**

CLINIQ AI is a healthcare clinical intelligence prototype built with **FastAPI**, **SQLite**, and **Streamlit**. Today, the system runs a **deterministic, rule-based clinical intelligence pipeline** (with multi-agent / agentic orchestration planned as future work). It ingests multi-page clinical PDFs (both selectable-text and scanned reports), extracts structured medical metadata, organizes patient studies chronologically, detects rule-based abnormal findings and potential record inconsistencies, compares previous vs. latest reports conservatively, and provides plain-language terminology explanations for clinician-supervised review.

---

## Problem Statement

Clinical records for a patient are frequently scattered across separate PDF reports from different dates and departments. Reviewing them manually makes it time-consuming to:
- Consolidate reports under the correct patient identifier
- Track how findings evolve chronologically across visits
- Spot missing metadata (such as missing study dates) or same-date opposing statements
- Translate technical radiology and clinical phrasing into plain language without altering clinical meaning

---

## Proposed Solution

CLINIQ AI currently implements a modular, **rule-based** clinical intelligence pipeline (providing the deterministic foundation for future agentic orchestration):
1. **PDF Ingestion & OCR**: Extracts selectable text with PyMuPDF and automatically falls back to Tesseract OCR for scanned pages.
2. **Structured Storage**: Persists patient profiles and reports in SQLite via SQLAlchemy with foreign-key enforcement and invalid/placeholder ID protection.
3. **Rule-Based Clinical Intelligence**: Parses study dates for chronological timelines, flags abnormal terms with negation awareness, explains medical terminology via a rule-based glossary, and separates missing information, potential contradictions, and clinical changes.
4. **Clinician Dashboard**: Presents a 7-section Streamlit interface connected to the FastAPI backend, with explicit separation between deterministic rule-based output and unconfigured external AI / agentic layers.

---

## Implemented Features

- **Multi-PDF Upload & Extraction (`POST /upload-pdfs`)**
  - Supports multiple `.pdf` files per request (rejects non-PDF, empty, corrupted, and password-protected PDFs).
  - Extracts selectable PDF text via PyMuPDF (`fitz`) and falls back to 2x-rendered Tesseract OCR (`pytesseract`) when a page has no text layer.
  - Extracts `patient_id` (`Patient ID`, `MRN`, `UHID`, `Patient No.`), `patient_name`, `patient_age`, `patient_sex`, `study_name`, `study_date`, `findings` (`Observation:` / `Findings:`), and `impression` (`IMPRESSION:` / `CONCLUSION:`).
- **Patient ID Protection & SQLite Persistence**
  - Resolves each uploaded PDF's patient ID independently, ignoring placeholder values (`string`, `unknown`, `placeholder`, `default`, `example`, `sample`, `-`, `--`, `none`, `null`, `n/a`, `na`, `undefined`) and non-alphanumeric IDs.
  - Prevents accidental merging of unrelated patients sharing a manual fallback ID.
  - Enforces SQLite `PRAGMA foreign_keys=ON` on every SQLAlchemy connection.
- **Chronological Medical Timeline (`GET /patients/{patient_id}/timeline`)**
  - Parses common medical date formats into ISO dates (`YYYY-MM-DD`) and orders studies chronologically (with undated reports placed at the end).
- **Rule-Based Clinical Summaries & Abnormal Flags**
  - Negation-aware keyword detection across `Critical / Acute`, `Cardiopulmonary`, `Musculoskeletal / Soft Tissue`, `Structural / Lesion`, `Fluid / Swelling`, and `Inflammation / Abnormality` categories, deduplicated across sections.
  - Generates plain-English report summaries preserving complete sentences.
- **Conservative Report Comparison & Conflict Detection (`GET /patients/{patient_id}/compare`, `GET /patients/{patient_id}/analysis`)**
  - Compares previous vs. latest comparable reports into `newly_appearing`, `improving`, `worsening`, `unchanged`, and `not_mentioned_in_latest`.
  - Guards against comparing identical-text uploads or different study types (`compatible_study_type=False`).
  - Separates **missing information** (`diagnosis`, `date`, `source`), **potential contradictions** (opposing assertions on comparable same-date studies), and **clinical changes** (longitudinal findings, medication status changes requiring review, and unit-matched numeric lab changes when explicitly extracted).
- **Patient-Friendly Terminology Glossary**
  - Maps medical and anatomical terms found in the report to plain-language definitions while citing the exact source context and preserving negated/normal status.
- **7-Page Streamlit Frontend**
  - `Executive Dashboard`, `Patient Intelligence`, `Document Center`, `Clinical Timeline`, `Medication Reconciliation`, `Conflict Intelligence`, and `AI Reconstruction`.
  - Includes live FastAPI connection status, CORS middleware, and an explicit **Fictional Demo Dataset** toggle clearly labeled as non-live sample data.

---

## Technology Stack

- **Backend**: Python 3.13, FastAPI, Uvicorn, SQLAlchemy, SQLite
- **PDF & OCR Processing**: PyMuPDF (`pymupdf`), `pytesseract`, Pillow (`PIL`), `python-multipart`
- **Frontend**: Streamlit, `requests`, Pandas, Plotly, `python-docx`

---

## System Architecture

```text
+--------------------------+        HTTP / JSON        +-------------------------------+
|    Streamlit Frontend    | ------------------------> |        FastAPI Backend        |
|    (frontend/app.py)     | <------------------------ |       (backend/main.py)       |
|  - 7 Dashboard Views     |    CliniqApiClient        |  - /upload-pdfs, /patients/*  |
|  - PDF/DOCX/TXT Uploader |                           |  - /reports/*, /dashboard/*   |
+--------------------------+                           +---------------+---------------+
                                                                       |
                                        +------------------------------+------------------------------+
                                        |                              |                              |
                                        v                              v                              v
                           +-------------------------+    +-------------------------+    +-------------------------+
                           |   backend/extractor.py  |    |   backend/clinical.py   |    | backend/intelligence.py |
                           |  Metadata, Findings &   |    |  ID Validation, Dates,  |    |  Comparison, Glossary,  |
                           |  Impression Extraction  |    |  Flags & Timeline Sort  |    |  conflict_detection.py  |
                           +-------------------------+    +------------+------------+    +------------+------------+
                                                                       |                              |
                                                                       +--------------+---------------+
                                                                                      |
                                                                                      v
                                                                       +-----------------------------+
                                                                       |  SQLite via SQLAlchemy      |
                                                                       |  (backend/database.py,      |
                                                                       |   models.py -> cliniq.db)   |
                                                                       +-----------------------------+
```

---

## Project Folder Structure

```text
MEDUSA_X HACK/
├── .streamlit/
│   └── config.toml                # Light healthcare theme + navy sidebar configuration
├── backend/
│   ├── __init__.py
│   ├── clinical.py                # Patient ID validation, date parsing, flags, timeline sorting
│   ├── conflict_detection.py      # Missing info, potential contradictions, med/lab change rules
│   ├── database.py                # SQLite engine, session dependency, PRAGMA foreign_keys=ON
│   ├── extractor.py               # Regex extraction for patient/study fields & sections
│   ├── intelligence.py            # Report comparison, terminology glossary, unified analysis
│   ├── main.py                    # FastAPI app, CORS, upload & retrieval endpoints
│   └── models.py                  # SQLAlchemy Patient and MedicalReport ORM models
├── frontend/
│   ├── __init__.py
│   ├── api_client.py              # Requests HTTP client for FastAPI (CLINIQ_API_URL)
│   ├── app.py                     # 7-page Streamlit dashboard
│   ├── components.py              # Reusable UI cards, banners, badges, terminology expanders
│   ├── demo_data.py               # Explicitly labeled fictional demo dataset
│   ├── document_handler.py        # Document Center upload workflow & local DOCX/TXT preview
│   └── requirements.txt           # Frontend Python dependencies
├── conflit_detection/             # Original standalone reconciliation prototype & unit tests
├── .gitignore
├── README.md
└── requirements.txt               # Backend Python dependencies
```

---

## Installation Instructions (Windows)

1. **Clone the repository and open the project folder** in PowerShell:
   ```powershell
   cd "MEDUSA_X HACK"
   ```

2. **Create and activate a Python virtual environment**:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

3. **Install backend and frontend dependencies**:
   ```powershell
   .\.venv\Scripts\python.exe -m pip install -r requirements.txt
   .\.venv\Scripts\python.exe -m pip install -r frontend\requirements.txt
   ```

4. **Install Tesseract OCR (required for scanned image-only PDFs)**:
   - Install Tesseract OCR for Windows at the default path expected by `backend/main.py`:
     `C:\Program Files\Tesseract-OCR\tesseract.exe`

---

## Running the Application

Open **two separate PowerShell terminals** in the project root folder:

### 1. Start the FastAPI Backend
```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```
- Backend URL: `http://127.0.0.1:8000`
- Health Check: `http://127.0.0.1:8000/health`

### 2. Start the Streamlit Frontend
```powershell
.\.venv\Scripts\python.exe -m streamlit run frontend/app.py
```
- Frontend URL: `http://localhost:8501`
- Optional environment variable: set `CLINIQ_API_URL` (or `API_BASE_URL`) if the FastAPI backend runs on a non-default URL.

---

## API Documentation & Endpoints

Interactive Swagger UI and ReDoc documentation are automatically served when FastAPI is running:
- **Swagger UI**: `http://127.0.0.1:8000/docs`
- **ReDoc**: `http://127.0.0.1:8000/redoc`

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Basic backend status |
| `GET` | `/health` | Service health check |
| `POST` | `/upload-pdfs` | Upload one or more PDFs, extract text/OCR, analyze, and persist to SQLite |
| `GET` | `/dashboard/overview` | Global KPI counts, severity distribution, category breakdown, recent reports |
| `GET` | `/patients` | List all stored patients and report counts |
| `GET` | `/patients/{patient_id}` | Patient profile and history overview |
| `GET` | `/patients/{patient_id}/reports` | All reports for a patient (`order=asc\|desc`, `include_pages`) |
| `GET` | `/patients/{patient_id}/timeline` | Chronological study timeline ordered by parsed study date |
| `GET` | `/patients/{patient_id}/compare` | Conservative comparison between previous and latest reports |
| `GET` | `/patients/{patient_id}/analysis` | Combined patient profile, timeline, comparison, conflict detection, terminology, and dashboard payload |
| `GET` | `/reports/{report_id}` | Full single report details including raw extracted text |
| `GET` | `/reports/{report_id}/analysis` | Single-report flags and terminology explanations |

---

## Current Limitations & Future Work

- **Rule-Based Pipeline Today (Agentic Orchestration Is Future Work)**: All summaries, comparisons, conflict checks, and terminology explanations currently run through deterministic Python rules (`ai_generated_explanations.enabled` is `false`). No paid external LLM API or autonomous multi-agent orchestration is active yet.
- **No Full Structured Medication or Comprehensive Lab Extraction**: Structured medication table extraction and comprehensive laboratory panel parsing are **not** yet implemented in `backend/extractor.py` (only explicit medication-status lines and unit-matched numeric lab lines are evaluated when present, and no drug-interaction alerts are generated).
- **Report Format Coverage**: `extract_medical_info()` uses regex patterns tuned for standard headers (`Patient ID:`, `Patient Name:`, `Study:`, `Study Date:`, `Observation:`/`Findings:`, `IMPRESSION:`/`CONCLUSION:`); reports with substantially different layouts may yield partial metadata.
- **Tesseract Path**: `backend/main.py` sets `tesseract_cmd` to `C:\Program Files\Tesseract-OCR\tesseract.exe`; non-default or Linux/macOS paths require updating that setting or making it configurable via environment variable.
- **Future Work**: Agentic orchestration across specialized clinical tasks, broader structured medication and laboratory parsing, optional opt-in LLM summarization with source citations, authentication/role-based access control, and duplicate-file hash deduplication on upload.

---

## Clinical Safety Disclaimer

> **CLINIQ AI is a hackathon prototype built for informational clinical support only.**  
> It is **not** a medical device or diagnostic tool, does not prescribe or recommend treatments, and does not automatically classify report differences as medical errors. All extracted data, rule-based flags, timelines, and terminology explanations must be reviewed and verified by a qualified healthcare professional.
