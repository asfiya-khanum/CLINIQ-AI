from contextlib import asynccontextmanager
import io
import json
from typing import Annotated

import fitz
import pytesseract
from PIL import Image
from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.clinical import (
    build_patient_timeline,
    deserialize_flags,
    detect_abnormal_flags,
    generate_clinical_summary,
    normalize_optional_patient_id,
    parse_study_date,
    resolve_patient_id,
    serialize_flags,
    sort_reports_chronologically,
)
from backend.database import get_db, init_db
from backend.extractor import extract_medical_info
from backend.intelligence import (
    CLINICAL_DISCLAIMER,
    build_patient_clinical_analysis,
    build_report_clinical_analysis,
    compare_patient_reports,
)
from backend.models import MedicalReport, Patient


# Tesseract OCR installation path
pytesseract.pytesseract.tesseract_cmd = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="CLINIQ AI",
    description="Clinical Intelligence Backend",
    version="1.1.0",
    lifespan=lifespan,
)

# Allow frontend applications (e.g., React/Vite/Next.js) to connect to the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _serialize_patient(patient: Patient, report_count: int) -> dict:
    return {
        "patient_id": patient.patient_id,
        "name": patient.name,
        "age": patient.age,
        "sex": patient.sex,
        "report_count": report_count,
        "created_at": patient.created_at.isoformat() if patient.created_at else None,
        "updated_at": patient.updated_at.isoformat() if patient.updated_at else None,
    }


def _serialize_report(report: MedicalReport, include_pages: bool = False) -> dict:
    flags = deserialize_flags(report.abnormal_flags_json)
    payload = {
        "report_id": report.id,
        "patient_id": report.patient_id,
        "filename": report.filename,
        "page_count": report.page_count,
        "medical_info": {
            "patient_id": report.patient_id,
            "patient_name": report.patient_name,
            "patient_age": report.patient_age,
            "patient_sex": report.patient_sex,
            "study_name": report.study_name,
            "study_date": report.study_date,
            "findings": report.findings,
            "impression": report.impression,
        },
        "study_date_iso": (
            report.study_date_parsed.isoformat() if report.study_date_parsed else None
        ),
        "clinical_summary": report.clinical_summary,
        "abnormal_flags": flags,
        "severity": report.severity or "normal",
        "created_at": report.created_at.isoformat() if report.created_at else None,
    }
    if include_pages:
        try:
            payload["pages"] = json.loads(report.pages_json) if report.pages_json else []
        except (ValueError, TypeError):
            payload["pages"] = []
        payload["raw_text"] = report.raw_text
    return payload


def _upsert_patient(
    db: Session,
    patient_id: str,
    medical_info: dict,
) -> Patient:
    clean_patient_id = normalize_optional_patient_id(patient_id)
    if not clean_patient_id:
        raise HTTPException(
            status_code=400,
            detail="Invalid patient_id: blank, placeholder, or non-alphanumeric IDs are not allowed.",
        )

    patient = db.query(Patient).filter(Patient.patient_id == clean_patient_id).first()
    if not patient:
        patient = Patient(
            patient_id=clean_patient_id,
            name=medical_info.get("patient_name"),
            age=medical_info.get("patient_age"),
            sex=medical_info.get("patient_sex"),
        )
        db.add(patient)
        db.flush()
    else:
        if not patient.name and medical_info.get("patient_name"):
            patient.name = medical_info.get("patient_name")
        if not patient.age and medical_info.get("patient_age"):
            patient.age = medical_info.get("patient_age")
        if not patient.sex and medical_info.get("patient_sex"):
            patient.sex = medical_info.get("patient_sex")
    return patient


@app.get("/")
def home():
    return {
        "project": "CLINIQ AI",
        "message": "Backend is running!",
        "status": "active",
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "CLINIQ AI Backend",
    }


@app.post("/upload-pdfs")
async def upload_pdfs(
    files: Annotated[
        list[UploadFile],
        File(description="Select PDF files"),
    ],
    patient_id: Annotated[
        str | None,
        Form(description="Optional fallback Patient ID (used only when a PDF has no Patient ID)"),
    ] = None,
    db: Session = Depends(get_db),
):
    results = []
    batch_patient_names: dict[str, str] = {}

    def lookup_existing_name(candidate_id: str) -> str | None:
        if candidate_id in batch_patient_names:
            return batch_patient_names[candidate_id]
        existing_patient = db.query(Patient).filter(Patient.patient_id == candidate_id).first()
        return existing_patient.name if existing_patient else None

    for uploaded_file in files:
        filename = uploaded_file.filename or "unnamed.pdf"

        if not filename.lower().endswith(".pdf"):
            results.append({
                "filename": filename,
                "status": "error",
                "message": "Only PDF files are allowed.",
            })
            await uploaded_file.close()
            continue

        try:
            file_bytes = await uploaded_file.read()

            if not file_bytes:
                results.append({
                    "filename": filename,
                    "status": "error",
                    "message": "The file is empty.",
                })
                continue

            try:
                document = fitz.open(
                    stream=file_bytes,
                    filetype="pdf",
                )
            except Exception:
                results.append({
                    "filename": filename,
                    "status": "error",
                    "message": "Invalid or unreadable PDF.",
                })
                continue

            with document:
                if document.needs_pass:
                    results.append({
                        "filename": filename,
                        "status": "error",
                        "message": "PDF is password-protected.",
                    })
                    continue

                pages = []

                for page_number, page in enumerate(
                    document,
                    start=1,
                ):
                    # First try normal PDF text extraction
                    page_text = page.get_text("text").strip()

                    # If no text is available, use OCR
                    if not page_text:
                        pix = page.get_pixmap(
                            matrix=fitz.Matrix(2, 2),
                            alpha=False,
                        )

                        image = Image.open(
                            io.BytesIO(pix.tobytes("png"))
                        )

                        page_text = pytesseract.image_to_string(
                            image,
                            lang="eng",
                        ).strip()

                    pages.append({
                        "page_number": page_number,
                        "text": page_text,
                    })

                # Combine text from all PDF pages
                full_text = "\n".join(
                    page["text"] for page in pages
                )

                # Extract structured medical information
                medical_info = extract_medical_info(full_text)

                resolved_patient_id, patient_id_source = resolve_patient_id(
                    medical_info.get("patient_id"),
                    patient_id,
                    medical_info.get("patient_name"),
                    existing_name_lookup=lookup_existing_name,
                )
                medical_info["patient_id"] = resolved_patient_id
                if medical_info.get("patient_name"):
                    batch_patient_names.setdefault(
                        resolved_patient_id,
                        medical_info["patient_name"],
                    )

                parsed_date = parse_study_date(medical_info.get("study_date"))
                abnormal_flags, severity = detect_abnormal_flags(
                    medical_info.get("findings"),
                    medical_info.get("impression"),
                    full_text,
                )
                clinical_summary = generate_clinical_summary(
                    medical_info,
                    abnormal_flags,
                    severity,
                )

                _upsert_patient(db, resolved_patient_id, medical_info)

                report = MedicalReport(
                    patient_id=resolved_patient_id,
                    filename=filename,
                    page_count=document.page_count,
                    raw_text=full_text,
                    pages_json=json.dumps(pages),
                    patient_name=medical_info.get("patient_name"),
                    patient_age=medical_info.get("patient_age"),
                    patient_sex=medical_info.get("patient_sex"),
                    study_name=medical_info.get("study_name"),
                    study_date=medical_info.get("study_date"),
                    study_date_parsed=parsed_date,
                    findings=medical_info.get("findings"),
                    impression=medical_info.get("impression"),
                    clinical_summary=clinical_summary,
                    abnormal_flags_json=serialize_flags(abnormal_flags),
                    severity=severity,
                )
                db.add(report)
                db.commit()
                db.refresh(report)

                results.append({
                    "filename": filename,
                    "status": "success",
                    "report_id": report.id,
                    "patient_id": resolved_patient_id,
                    "patient_id_source": patient_id_source,
                    "page_count": document.page_count,
                    "pages": pages,
                    "medical_info": medical_info,
                    "study_date_iso": parsed_date.isoformat() if parsed_date else None,
                    "clinical_summary": clinical_summary,
                    "abnormal_flags": abnormal_flags,
                    "severity": severity,
                })

        except Exception as error:
            db.rollback()
            results.append({
                "filename": filename,
                "status": "error",
                "message": str(error),
            })

        finally:
            await uploaded_file.close()

    return {
        "project": "CLINIQ AI",
        "total_files": len(files),
        "files": results,
    }


@app.get("/patients")
def list_patients(db: Session = Depends(get_db)):
    rows = (
        db.query(Patient, func.count(MedicalReport.id))
        .outerjoin(MedicalReport, Patient.patient_id == MedicalReport.patient_id)
        .group_by(Patient.id)
        .order_by(Patient.updated_at.desc())
        .all()
    )
    return {
        "project": "CLINIQ AI",
        "total_patients": len(rows),
        "patients": [_serialize_patient(patient, count) for patient, count in rows],
    }


@app.get("/patients/{patient_id}")
def get_patient(patient_id: str, db: Session = Depends(get_db)):
    patient = db.query(Patient).filter(Patient.patient_id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail=f"Patient '{patient_id}' not found.")

    reports = (
        db.query(MedicalReport)
        .filter(MedicalReport.patient_id == patient_id)
        .all()
    )
    timeline_data = build_patient_timeline(reports)
    return {
        "project": "CLINIQ AI",
        "patient": _serialize_patient(patient, len(reports)),
        "summary": {
            "overall_severity": timeline_data["overall_severity"],
            "date_range": timeline_data["date_range"],
            "flagged_terms": timeline_data["flagged_terms"],
            "overview_summary": timeline_data["overview_summary"],
        },
    }


@app.get("/patients/{patient_id}/reports")
def get_patient_reports(
    patient_id: str,
    order: Annotated[str, Query(pattern="^(asc|desc)$")] = "asc",
    include_pages: bool = False,
    db: Session = Depends(get_db),
):
    patient = db.query(Patient).filter(Patient.patient_id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail=f"Patient '{patient_id}' not found.")

    reports = (
        db.query(MedicalReport)
        .filter(MedicalReport.patient_id == patient_id)
        .all()
    )

    reports = sort_reports_chronologically(
        reports,
        descending=(order == "desc"),
    )

    return {
        "project": "CLINIQ AI",
        "patient": _serialize_patient(patient, len(reports)),
        "total_reports": len(reports),
        "reports": [_serialize_report(r, include_pages=include_pages) for r in reports],
    }


@app.get("/patients/{patient_id}/timeline")
def get_patient_timeline(patient_id: str, db: Session = Depends(get_db)):
    patient = db.query(Patient).filter(Patient.patient_id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail=f"Patient '{patient_id}' not found.")

    reports = (
        db.query(MedicalReport)
        .filter(MedicalReport.patient_id == patient_id)
        .all()
    )
    timeline_data = build_patient_timeline(reports)
    return {
        "project": "CLINIQ AI",
        "patient": _serialize_patient(patient, len(reports)),
        **timeline_data,
    }


@app.get("/reports/{report_id}")
def get_report(report_id: int, db: Session = Depends(get_db)):
    report = db.query(MedicalReport).filter(MedicalReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail=f"Report '{report_id}' not found.")

    return {
        "project": "CLINIQ AI",
        "report": _serialize_report(report, include_pages=True),
    }


@app.get("/reports/{report_id}/analysis")
def get_report_analysis(report_id: int, db: Session = Depends(get_db)):
    report = db.query(MedicalReport).filter(MedicalReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail=f"Report '{report_id}' not found.")

    return {
        "project": "CLINIQ AI",
        **build_report_clinical_analysis(report),
    }


@app.get("/patients/{patient_id}/compare")
def compare_reports(
    patient_id: str,
    previous_report_id: int | None = None,
    latest_report_id: int | None = None,
    db: Session = Depends(get_db),
):
    patient = db.query(Patient).filter(Patient.patient_id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail=f"Patient '{patient_id}' not found.")

    if (previous_report_id is None) != (latest_report_id is None):
        raise HTTPException(
            status_code=400,
            detail="Provide both previous_report_id and latest_report_id, or omit both.",
        )

    reports = (
        db.query(MedicalReport)
        .filter(MedicalReport.patient_id == patient_id)
        .all()
    )
    comparison = compare_patient_reports(
        reports,
        previous_report_id=previous_report_id,
        latest_report_id=latest_report_id,
    )
    if (
        previous_report_id is not None
        and not comparison["comparison_available"]
    ):
        raise HTTPException(status_code=404, detail=comparison["reason"])

    return {
        "project": "CLINIQ AI",
        "patient": _serialize_patient(patient, len(reports)),
        **comparison,
        "clinical_disclaimer": CLINICAL_DISCLAIMER,
    }


@app.get("/patients/{patient_id}/analysis")
def get_patient_analysis(patient_id: str, db: Session = Depends(get_db)):
    patient = db.query(Patient).filter(Patient.patient_id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail=f"Patient '{patient_id}' not found.")

    reports = (
        db.query(MedicalReport)
        .filter(MedicalReport.patient_id == patient_id)
        .all()
    )
    return {
        "project": "CLINIQ AI",
        **build_patient_clinical_analysis(patient, reports),
    }


@app.get("/dashboard/overview")
def get_dashboard_overview(db: Session = Depends(get_db)):
    total_patients = db.query(func.count(Patient.id)).scalar() or 0
    all_reports = (
        db.query(MedicalReport)
        .order_by(MedicalReport.created_at.desc())
        .all()
    )

    severity_counts = {
        "attention_needed": 0,
        "review_recommended": 0,
        "normal": 0,
    }
    category_counts: dict[str, int] = {}

    for report in all_reports:
        sev = report.severity or "normal"
        severity_counts[sev] = severity_counts.get(sev, 0) + 1
        for flag in deserialize_flags(report.abnormal_flags_json):
            cat = flag.get("category", "Other")
            category_counts[cat] = category_counts.get(cat, 0) + 1

    recent_reports = [_serialize_report(r, include_pages=False) for r in all_reports[:10]]

    return {
        "project": "CLINIQ AI",
        "cards": {
            "total_patients": total_patients,
            "total_reports": len(all_reports),
            "attention_needed_reports": severity_counts["attention_needed"],
            "review_recommended_reports": severity_counts["review_recommended"],
            "normal_reports": severity_counts["normal"],
        },
        "severity_distribution": severity_counts,
        "category_breakdown": category_counts,
        "recent_reports": recent_reports,
        "clinical_disclaimer": CLINICAL_DISCLAIMER,
    }
