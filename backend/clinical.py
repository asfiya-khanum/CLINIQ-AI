from collections.abc import Callable
from datetime import date, datetime
import json
import re
import uuid


DATE_FORMATS = (
    "%Y-%m-%d",
    "%Y/%m/%d",
    "%d-%m-%Y",
    "%d/%m/%Y",
    "%d.%m.%Y",
    "%m/%d/%Y",
    "%m-%d-%Y",
    "%d %b %Y",
    "%d %B %Y",
    "%d-%b-%Y",
    "%d-%B-%Y",
    "%b %d, %Y",
    "%B %d, %Y",
    "%b %d %Y",
    "%B %d %Y",
)

PLACEHOLDER_PATIENT_IDS = {
    "string",
    "none",
    "null",
    "n/a",
    "na",
    "undefined",
    "unknown",
    "placeholder",
    "default",
    "example",
    "sample",
    "-",
    "--",
}

NEGATION_PATTERN = re.compile(
    r"\b(?:no|no evidence of|without|negative for|absent|ruled out|free of|neither|nor|normal|unremarkable)\b[^.;,\n]*$",
    re.IGNORECASE,
)

# Ordered from specific multi-word anatomical/clinical phrases to general terms
# so specialized findings (e.g. bone marrow edema) match before generic ones (edema).
CLINICAL_FLAG_RULES = [
    {
        "category": "Critical / Acute",
        "severity": "high",
        "keywords": (
            "pneumothorax",
            "hemorrhage",
            "bleeding",
            "infarction",
            "infarct",
            "stroke",
            "ischemia",
            "embolism",
            "aneurysm",
            "perforation",
            "obstruction",
            "malignancy",
            "carcinoma",
            "tumor",
            "metastasis",
            "fracture",
            "osteomyelitis",
            "critical",
        ),
    },
    {
        "category": "Cardiopulmonary",
        "severity": "moderate",
        "keywords": (
            "pulmonary edema",
            "pleural effusion",
            "pericardial effusion",
            "cardiomegaly",
            "pneumonia",
            "consolidation",
            "atelectasis",
            "infiltrate",
            "opacity",
        ),
    },
    {
        "category": "Musculoskeletal / Soft Tissue",
        "severity": "moderate",
        "keywords": (
            "bone marrow edema",
            "marrow edema",
            "subcutaneous edema",
            "soft tissue edema",
            "joint effusion",
            "periarticular fluid",
            "fluid collection",
            "synovitis",
            "disc bulge",
            "herniation",
            "degenerative",
            "tendon tear",
            "ligament tear",
        ),
    },
    {
        "category": "Structural / Lesion",
        "severity": "moderate",
        "keywords": (
            "mass",
            "lesion",
            "nodule",
            "cyst",
            "calcification",
            "stone",
            "calculus",
            "stenosis",
            "thrombosis",
            "hypertrophy",
            "enlargement",
            "enlarged",
        ),
    },
    {
        "category": "Fluid / Swelling",
        "severity": "moderate",
        "keywords": (
            "effusion",
            "edema",
        ),
    },
    {
        "category": "Inflammation / Abnormality",
        "severity": "moderate",
        "keywords": (
            "infection",
            "inflammation",
            "abnormality",
            "abnormal",
            "elevated",
            "decreased",
            "reduced",
            "positive",
            "reactive",
        ),
    },
]


def normalize_optional_patient_id(raw_id: str | None) -> str | None:
    """
    Return a clean patient ID or None if blank, a known placeholder,
    or lacking any alphanumeric character.
    """
    if not raw_id:
        return None
    cleaned = raw_id.strip()
    if not cleaned or cleaned.lower() in PLACEHOLDER_PATIENT_IDS:
        return None
    if not re.search(r"[A-Za-z0-9]", cleaned):
        return None
    return cleaned


def _normalize_person_name(name: str | None) -> str:
    if not name:
        return ""
    return re.sub(r"\s+", " ", name.strip().upper())


def _build_generated_patient_id(patient_name: str | None) -> str:
    if patient_name and patient_name.strip():
        slug = re.sub(r"[^A-Za-z0-9]+", "-", patient_name.strip().upper()).strip("-")
        if slug:
            return f"PAT-{slug[:32]}"
    return f"PAT-{uuid.uuid4().hex[:8].upper()}"


def resolve_patient_id(
    extracted_patient_id: str | None,
    fallback_patient_id: str | None,
    patient_name: str | None,
    existing_name_lookup: Callable[[str], str | None] | None = None,
) -> tuple[str, str]:
    """
    Resolve a patient ID independently per PDF:
    1. Always prefer the patient ID extracted from the PDF itself.
    2. Use manual fallback_patient_id only when the PDF has no ID, and refuse to
       share that fallback ID if it already belongs to a different patient name.
    3. Otherwise generate a patient-specific ID.
    Returns (patient_id, source_label).
    """
    clean_extracted = normalize_optional_patient_id(extracted_patient_id)
    if clean_extracted:
        return clean_extracted, "extracted"

    clean_fallback = normalize_optional_patient_id(fallback_patient_id)
    if clean_fallback:
        existing_name = existing_name_lookup(clean_fallback) if existing_name_lookup else None
        norm_existing = _normalize_person_name(existing_name)
        norm_incoming = _normalize_person_name(patient_name)

        if norm_existing and norm_incoming and norm_existing != norm_incoming:
            return _build_generated_patient_id(patient_name), "generated_conflict_safe"

        return clean_fallback, "manual_fallback"

    return _build_generated_patient_id(patient_name), "generated"


def parse_study_date(date_str: str | None) -> date | None:
    """Parse common medical report date strings into a Python date."""
    if not date_str:
        return None

    cleaned = date_str.strip()
    cleaned = re.split(r"[T\s]+\d{1,2}:\d{2}", cleaned, maxsplit=1)[0].strip()
    cleaned = re.sub(r"(\d+)(st|nd|rd|th)\b", r"\1", cleaned, flags=re.IGNORECASE)
    cleaned = cleaned.strip(" ,.-")

    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(cleaned, fmt).date()
        except ValueError:
            continue

    match = re.search(
        r"(\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4}|\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4})",
        cleaned,
    )
    if match and match.group(1) != cleaned:
        return parse_study_date(match.group(1))

    return None


def _unwrap_clinical_text(text: str) -> list[str]:
    """
    Join soft line wraps inside clinical prose while keeping bullets and
    blank-line paragraph breaks intact.
    """
    cleaned = re.sub(r"\bEND OF REPORT\b", "", text, flags=re.IGNORECASE)
    lines = cleaned.splitlines()

    items: list[str] = []
    current_parts: list[str] = []

    def flush_current():
        if current_parts:
            joined = re.sub(r"\s+", " ", " ".join(current_parts)).strip()
            if joined:
                items.append(joined)
            current_parts.clear()

    for raw_line in lines:
        stripped = raw_line.strip()
        if not stripped:
            flush_current()
            continue

        is_bullet = bool(re.match(r"^(?:[-•▪*]|\d+[.)])\s+", stripped))
        if is_bullet:
            flush_current()
            stripped = re.sub(r"^(?:[-•▪*]|\d+[.)])\s+", "", stripped).strip()
            if stripped:
                current_parts.append(stripped)
        else:
            current_parts.append(stripped)

    flush_current()
    return items


def _split_clauses(text: str) -> list[str]:
    """Split unwrapped clinical text into complete sentences/clauses."""
    clauses: list[str] = []
    for block in _unwrap_clinical_text(text):
        for sentence in re.split(r"(?<=[.!?])\s+", block):
            cleaned = sentence.strip(" -\t")
            if cleaned:
                clauses.append(cleaned)
    return clauses


def _span_overlaps(span: tuple[int, int], covered_spans: list[tuple[int, int]]) -> bool:
    start, end = span
    return any(start < cov_end and end > cov_start for cov_start, cov_end in covered_spans)


def detect_abnormal_flags(
    findings: str | None,
    impression: str | None,
    raw_text: str = "",
) -> tuple[list[dict], str]:
    """
    Detect rule-based abnormal clinical findings with negation handling,
    anatomical category accuracy, and cross-section deduplication.
    """
    sections = []
    if impression:
        sections.append(("impression", impression))
    if findings:
        sections.append(("findings", findings))
    if not sections and raw_text:
        sections.append(("report", raw_text))

    flags: list[dict] = []
    flags_by_term: dict[str, dict] = {}

    for source_name, section_text in sections:
        for clause in _split_clauses(section_text):
            covered_spans: list[tuple[int, int]] = []

            for rule in CLINICAL_FLAG_RULES:
                for keyword in rule["keywords"]:
                    pattern = re.compile(rf"\b{re.escape(keyword)}\b", re.IGNORECASE)
                    for match in pattern.finditer(clause):
                        span = (match.start(), match.end())
                        if _span_overlaps(span, covered_spans):
                            continue

                        prefix = clause[: match.start()]
                        if NEGATION_PATTERN.search(prefix):
                            continue

                        covered_spans.append(span)
                        term_key = keyword.lower()

                        if term_key in flags_by_term:
                            existing = flags_by_term[term_key]
                            if source_name not in existing["sources"]:
                                existing["sources"].append(source_name)
                            continue

                        flag_entry = {
                            "term": keyword,
                            "category": rule["category"],
                            "severity": rule["severity"],
                            "source": source_name,
                            "sources": [source_name],
                            "context": clause[:280],
                        }
                        flags_by_term[term_key] = flag_entry
                        flags.append(flag_entry)

    severities = {flag["severity"] for flag in flags}
    if "high" in severities:
        overall_severity = "attention_needed"
    elif "moderate" in severities:
        overall_severity = "review_recommended"
    else:
        overall_severity = "normal"

    return flags, overall_severity


def _ensure_period(text: str) -> str:
    cleaned = text.strip().rstrip(".!? ")
    return f"{cleaned}." if cleaned else ""


def generate_clinical_summary(
    medical_info: dict,
    abnormal_flags: list[dict],
    severity: str,
) -> str:
    """Create a readable plain-English summary preserving complete sentences."""
    study = medical_info.get("study_name") or "Clinical study"
    study_date = medical_info.get("study_date") or "unspecified date"
    impression = medical_info.get("impression")
    findings = medical_info.get("findings")

    parts = [f"{study} ({study_date})."]

    if impression:
        sentences = _split_clauses(impression)
        selected = [_ensure_period(s) for s in sentences[:3] if s.strip()]
        if selected:
            parts.append(f"Key impression: {' '.join(selected)}")
    elif findings:
        sentences = _split_clauses(findings)
        selected = [_ensure_period(s) for s in sentences[:3] if s.strip()]
        if selected:
            parts.append(f"Key observations: {' '.join(selected)}")
    else:
        parts.append("No structured findings or impression section was detected.")

    if abnormal_flags:
        flagged_terms = ", ".join(flag["term"] for flag in abnormal_flags[:6])
        parts.append(
            f"Status: {severity.replace('_', ' ')} — flagged terms: {flagged_terms}."
        )
    else:
        parts.append("Status: normal — no abnormal keywords flagged by basic rules.")

    return " ".join(parts)


def deduplicate_abnormal_flags(flags: list[dict] | None) -> list[dict]:
    """Deduplicate abnormal flags case-insensitively by term while merging sources."""
    if not flags:
        return []
    deduped: list[dict] = []
    by_term: dict[str, dict] = {}
    for raw_flag in flags:
        if not isinstance(raw_flag, dict):
            continue
        term = str(raw_flag.get("term") or "").strip()
        if not term:
            continue
        term_key = term.lower()

        raw_sources = raw_flag.get("sources")
        if isinstance(raw_sources, list) and raw_sources:
            incoming_sources = [str(s) for s in raw_sources if s]
        elif raw_flag.get("source"):
            incoming_sources = [str(raw_flag["source"])]
        else:
            incoming_sources = []

        if term_key in by_term:
            existing = by_term[term_key]
            for src in incoming_sources:
                if src not in existing["sources"]:
                    existing["sources"].append(src)
            continue

        entry = dict(raw_flag)
        entry["term"] = term
        entry["sources"] = incoming_sources
        by_term[term_key] = entry
        deduped.append(entry)
    return deduped


def serialize_flags(flags: list[dict]) -> str:
    return json.dumps(deduplicate_abnormal_flags(flags))


def deserialize_flags(flags_json: str | None) -> list[dict]:
    if not flags_json:
        return []
    try:
        data = json.loads(flags_json)
        return deduplicate_abnormal_flags(data) if isinstance(data, list) else []
    except (ValueError, TypeError):
        return []


def sort_reports_chronologically(reports: list, descending: bool = False) -> list:
    """
    Order reports by study_date_parsed, placing undated reports at the end.
    Identical study dates are broken deterministically by created_at and report id.
    """
    if descending:
        return sorted(
            reports,
            key=lambda r: (
                r.study_date_parsed is None,
                -(r.study_date_parsed.toordinal()) if r.study_date_parsed else 0,
                -(r.created_at.timestamp()) if r.created_at else 0,
                -(r.id or 0),
            ),
        )
    return sorted(
        reports,
        key=lambda r: (
            r.study_date_parsed is None,
            r.study_date_parsed or date.max,
            r.created_at,
            r.id or 0,
        ),
    )


def build_patient_timeline(reports: list) -> dict:
    """
    Order a patient's reports chronologically by study_date_parsed
    (undated reports placed at the end by upload time) and summarize them.
    """
    ordered = sort_reports_chronologically(reports, descending=False)

    events = []
    all_terms: list[str] = []
    highest_severity = "normal"
    dated_values: list[date] = []

    for index, report in enumerate(ordered, start=1):
        flags = deserialize_flags(report.abnormal_flags_json)
        for flag in flags:
            term = flag.get("term")
            if term and term not in all_terms:
                all_terms.append(term)

        if report.severity == "attention_needed":
            highest_severity = "attention_needed"
        elif report.severity == "review_recommended" and highest_severity == "normal":
            highest_severity = "review_recommended"

        if report.study_date_parsed:
            dated_values.append(report.study_date_parsed)

        events.append({
            "sequence": index,
            "report_id": report.id,
            "filename": report.filename,
            "study_name": report.study_name,
            "study_date": report.study_date,
            "study_date_iso": (
                report.study_date_parsed.isoformat() if report.study_date_parsed else None
            ),
            "severity": report.severity or "normal",
            "abnormal_flags": flags,
            "clinical_summary": report.clinical_summary,
            "findings": report.findings,
            "impression": report.impression,
            "uploaded_at": report.created_at.isoformat() if report.created_at else None,
        })

    if not ordered:
        overview = "No reports available for this patient."
    elif dated_values:
        start_iso = min(dated_values).isoformat()
        end_iso = max(dated_values).isoformat()
        overview = (
            f"{len(ordered)} report(s) spanning {start_iso} to {end_iso}. "
            f"Overall status: {highest_severity.replace('_', ' ')}."
        )
    else:
        overview = (
            f"{len(ordered)} report(s) on file (study dates could not be parsed). "
            f"Overall status: {highest_severity.replace('_', ' ')}."
        )

    if all_terms:
        overview += f" Flagged terms across history: {', '.join(all_terms[:8])}."

    return {
        "total_reports": len(ordered),
        "dated_reports": len(dated_values),
        "date_range": {
            "earliest": min(dated_values).isoformat() if dated_values else None,
            "latest": max(dated_values).isoformat() if dated_values else None,
        },
        "overall_severity": highest_severity,
        "flagged_terms": all_terms,
        "overview_summary": overview,
        "timeline": events,
    }
