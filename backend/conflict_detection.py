import re

from backend.clinical import (
    NEGATION_PATTERN,
    _split_clauses,
    deserialize_flags,
    sort_reports_chronologically,
)


CONFLICT_DISCLAIMER = (
    "Rule-based record completeness and consistency check for clinician review only. "
    "Potential differences or contradictions do not represent confirmed medical errors."
)

# Explicit medication + status phrasing (e.g., "Metformin: discontinued", "Aspirin (active)")
MEDICATION_STATUS_PATTERN = re.compile(
    r"\b([A-Za-z][A-Za-z0-9\-]{2,}(?:\s+[A-Za-z0-9\-]+)?)"
    r"(?:\s+\d+(?:\.\d+)?\s*(?:mg|mcg|g|ml|iu|units))?"
    r"\s*(?:[:\-]|status\s*[:\-]?|\()\s*"
    r"(active|continued|ongoing|started|stopped|discontinued|held|paused)\b",
    re.IGNORECASE,
)

# Explicit numeric lab lines requiring test name, numeric value, and unit
LAB_VALUE_PATTERN = re.compile(
    r"\b(Hemoglobin|Hb|WBC|Platelets|INR|Glucose|Creatinine|Sodium|Potassium|HbA1c)\b"
    r"\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*"
    r"(g/dL|mg/dL|mmol/L|mEq/L|x10\^9/L|10\^9/L|K/uL|%|ratio)\b",
    re.IGNORECASE,
)


def check_missing_information(record: dict) -> dict:
    """
    Adapted from conflit_detection/hackathon/agent.py.
    Checks whether diagnosis/findings, date, and source are present in a record dict.
    """
    missing = []

    if not str(record.get("diagnosis") or "").strip():
        missing.append("diagnosis")

    if not str(record.get("date") or "").strip():
        missing.append("date")

    if not str(record.get("source") or "").strip():
        missing.append("source")

    if missing:
        return {
            "status": "INCOMPLETE",
            "missing_fields": missing,
            "needs_human_review": True,
        }

    return {
        "status": "COMPLETE",
        "missing_fields": [],
        "needs_human_review": False,
    }


def check_medication_conflict(old_record: dict, new_record: dict) -> dict:
    """
    Adapted from conflit_detection/hackathon/agent.py.
    Treats medication status differences as medication changes requiring clinician review,
    never as medication errors, and does not generate drug interaction alerts.
    """
    old_med = str(old_record.get("medication") or "").strip().lower()
    new_med = str(new_record.get("medication") or "").strip().lower()

    old_status = str(old_record.get("status") or "").strip().lower()
    new_status = str(new_record.get("status") or "").strip().lower()

    if old_med and new_med and old_med == new_med and old_status != new_status:
        return {
            "status": "REVIEW_REQUIRED",
            "type": "MEDICATION_CHANGE",
            "medication": old_med,
            "old_status": old_status,
            "new_status": new_status,
            "message": "Medication status changed across comparable reports; clinician review required.",
            "needs_human_review": True,
        }

    return {
        "status": "UNCHANGED",
        "needs_human_review": False,
    }


def reconcile(purana: dict, naya: dict) -> dict:
    """
    Adapted from conflit_detection/hackathon/agent.py.
    Compares shared structured keys without automatically labeling differences as medical errors.
    """
    differences = []

    for key in purana:
        if key in naya and purana[key] != naya.get(key):
            differences.append(
                {
                    "field": key,
                    "previous_value": purana[key],
                    "latest_value": naya.get(key),
                }
            )

    if differences:
        return {
            "status": "REVIEW_NEEDED",
            "differences": differences,
            "needs_human_review": True,
        }

    return {
        "status": "MATCH",
        "differences": [],
        "needs_human_review": False,
    }


NON_MEDICATION_PREFIXES = {"clinical", "patient", "study", "report", "status", "overall", "impression", "observation"}


def _extract_explicit_medications(text: str) -> list[dict]:
    if not text:
        return []
    found: list[dict] = []
    seen: set[str] = set()
    for line in text.splitlines():
        match = MEDICATION_STATUS_PATTERN.search(line)
        if not match:
            continue
        med_name = re.sub(r"\s+", " ", match.group(1)).strip()
        if med_name.lower() in NON_MEDICATION_PREFIXES:
            continue
        status = match.group(2).strip().lower()
        key = med_name.lower()
        if key in seen:
            continue
        seen.add(key)
        found.append({
            "medication": med_name,
            "status": status,
            "context": line.strip()[:220],
        })
    return found


def _extract_explicit_labs(text: str) -> dict[str, dict]:
    """
    Extract numeric lab entries only when test name, numeric value, unit,
    and line context are all explicitly present.
    """
    if not text:
        return {}
    labs: dict[str, dict] = {}
    for line in text.splitlines():
        match = LAB_VALUE_PATTERN.search(line)
        if not match:
            continue
        test_name = match.group(1).strip()
        value = float(match.group(2))
        unit = match.group(3).strip()
        labs[test_name.lower()] = {
            "test_name": test_name,
            "value": value,
            "unit": unit,
            "context": line.strip()[:220],
        }
    return labs


def report_to_reconciliation_dict(report) -> dict:
    """Convert a MedicalReport ORM/object into a structured dict for conflict checks."""
    diagnosis_text = (getattr(report, "impression", None) or getattr(report, "findings", None) or "").strip()
    parsed_date = getattr(report, "study_date_parsed", None)
    date_str = parsed_date.isoformat() if parsed_date else (getattr(report, "study_date", None) or "").strip()
    source_str = (getattr(report, "study_name", None) or getattr(report, "filename", None) or "").strip()
    raw_text = getattr(report, "raw_text", None) or ""

    return {
        "report_id": getattr(report, "id", None),
        "filename": getattr(report, "filename", None),
        "study_name": getattr(report, "study_name", None),
        "study_date": getattr(report, "study_date", None),
        "study_date_iso": parsed_date.isoformat() if parsed_date else None,
        "diagnosis": diagnosis_text,
        "date": date_str,
        "source": source_str,
        "medications": _extract_explicit_medications(raw_text),
        "labs": _extract_explicit_labs(raw_text),
    }


def _extract_negated_terms(clauses: list[str], candidate_terms: set[str]) -> dict[str, str]:
    """Return {term_lower: clause} for terms explicitly negated in clauses."""
    negated: dict[str, str] = {}
    for term_key in candidate_terms:
        pattern = re.compile(rf"\b{re.escape(term_key)}\b", re.IGNORECASE)
        for clause in clauses:
            match = pattern.search(clause)
            if match and NEGATION_PATTERN.search(clause[: match.start()]):
                negated[term_key] = clause
                break
    return negated


def _detect_opposing_assertions(prev_report, latest_report, same_study_date: bool) -> list[dict]:
    """
    Flag potential contradictions only when comparable reports make mutually opposing
    assertions on the same finding/concept on the same study date (or explicit direct
    contradiction on same-day studies), never routine follow-up wording differences.
    """
    if not same_study_date:
        # On different dates, present -> negated reflects clinical resolution, not contradiction.
        return []

    prev_flags = deserialize_flags(getattr(prev_report, "abnormal_flags_json", None))
    latest_flags = deserialize_flags(getattr(latest_report, "abnormal_flags_json", None))

    prev_by_term = {f["term"].lower(): f for f in prev_flags}
    latest_by_term = {f["term"].lower(): f for f in latest_flags}

    prev_clauses = _split_clauses(
        "\n".join(p for p in (prev_report.impression, prev_report.findings) if p)
    )
    latest_clauses = _split_clauses(
        "\n".join(p for p in (latest_report.impression, latest_report.findings) if p)
    )

    prev_negated = _extract_negated_terms(prev_clauses, set(latest_by_term.keys()))
    latest_negated = _extract_negated_terms(latest_clauses, set(prev_by_term.keys()))

    contradictions: list[dict] = []

    for term_key, l_flag in latest_by_term.items():
        if term_key in prev_negated:
            contradictions.append({
                "type": "OPPOSING_ASSERTION",
                "finding": l_flag["term"],
                "message": (
                    f"Same-date reports make opposing statements regarding '{l_flag['term']}' "
                    "(absent/negated in one report, noted in the other)."
                ),
                "previous_report": {
                    "report_id": prev_report.id,
                    "filename": prev_report.filename,
                    "study_date": prev_report.study_date_parsed.isoformat() if prev_report.study_date_parsed else prev_report.study_date,
                    "evidence": prev_negated[term_key][:240],
                },
                "latest_report": {
                    "report_id": latest_report.id,
                    "filename": latest_report.filename,
                    "study_date": latest_report.study_date_parsed.isoformat() if latest_report.study_date_parsed else latest_report.study_date,
                    "evidence": (l_flag.get("context") or "")[:240],
                },
                "needs_human_review": True,
            })

    for term_key, p_flag in prev_by_term.items():
        if term_key in latest_negated:
            contradictions.append({
                "type": "OPPOSING_ASSERTION",
                "finding": p_flag["term"],
                "message": (
                    f"Same-date reports make opposing statements regarding '{p_flag['term']}' "
                    "(noted in one report, absent/negated in the other)."
                ),
                "previous_report": {
                    "report_id": prev_report.id,
                    "filename": prev_report.filename,
                    "study_date": prev_report.study_date_parsed.isoformat() if prev_report.study_date_parsed else prev_report.study_date,
                    "evidence": (p_flag.get("context") or "")[:240],
                },
                "latest_report": {
                    "report_id": latest_report.id,
                    "filename": latest_report.filename,
                    "study_date": latest_report.study_date_parsed.isoformat() if latest_report.study_date_parsed else latest_report.study_date,
                    "evidence": latest_negated[term_key][:240],
                },
                "needs_human_review": True,
            })

    return contradictions


def analyze_patient_conflicts(
    reports: list,
    prev_report=None,
    latest_report=None,
    comparison_changes: dict | None = None,
    compatible_study_type: bool = True,
    identical_content: bool = False,
) -> dict:
    """
    Separate record analysis cleanly into:
      1. missing_information (report completeness)
      2. potential_contradictions (comparable opposing assertions only)
      3. clinical_changes (longitudinal findings, medication status changes, explicit lab changes)
    """
    ordered = sort_reports_chronologically(reports, descending=False)

    incomplete_reports: list[dict] = []
    for report in ordered:
        rec = report_to_reconciliation_dict(report)
        miss = check_missing_information(rec)
        if miss["status"] == "INCOMPLETE":
            incomplete_reports.append({
                "report_id": rec["report_id"],
                "filename": rec["filename"],
                "study_name": rec["study_name"],
                "study_date": rec["study_date_iso"] or rec["study_date"] or "Undated",
                "missing_fields": miss["missing_fields"],
                "needs_human_review": True,
            })

    missing_info_block = {
        "total_checked": len(ordered),
        "incomplete_count": len(incomplete_reports),
        "status": "INCOMPLETE" if incomplete_reports else "COMPLETE",
        "incomplete_reports": incomplete_reports,
    }

    if prev_report is None or latest_report is None:
        if len(ordered) >= 2:
            prev_report = ordered[-2]
            latest_report = ordered[-1]

    if not prev_report or not latest_report or prev_report.id == latest_report.id:
        return {
            "status": "INCOMPLETE_RECORDS" if incomplete_reports else "NO_CONTRADICTIONS_DETECTED",
            "comparability": {
                "comparable": False,
                "reason": "At least two distinct reports are required for cross-report checks.",
                "previous_report_id": getattr(prev_report, "id", None),
                "latest_report_id": getattr(latest_report, "id", None),
            },
            "missing_information": missing_info_block,
            "potential_contradictions": [],
            "clinical_changes": {
                "findings": comparison_changes or {},
                "medication_changes": [],
                "lab_changes": [],
            },
            "counts": {
                "incomplete_reports": len(incomplete_reports),
                "potential_contradictions": 0,
                "medication_changes": 0,
                "lab_changes": 0,
            },
            "disclaimer": CONFLICT_DISCLAIMER,
        }

    if identical_content:
        comparability_reason = (
            "Both selected records contain identical extracted clinical text; "
            "cross-report contradiction checks were skipped."
        )
        is_comparable = False
    elif not compatible_study_type:
        comparability_reason = (
            "Reports represent different study types; different study types are not treated as conflicts."
        )
        is_comparable = False
    else:
        comparability_reason = "Reports share comparable study types."
        is_comparable = True

    potential_contradictions: list[dict] = []
    medication_changes: list[dict] = []
    lab_changes: list[dict] = []

    if is_comparable:
        same_study_date = (
            prev_report.study_date_parsed is not None
            and prev_report.study_date_parsed == latest_report.study_date_parsed
        )
        potential_contradictions = _detect_opposing_assertions(
            prev_report,
            latest_report,
            same_study_date=same_study_date,
        )

        prev_dict = report_to_reconciliation_dict(prev_report)
        latest_dict = report_to_reconciliation_dict(latest_report)

        # Medication changes requiring review (not labeled as medication errors; no interaction alerts)
        for old_med in prev_dict["medications"]:
            for new_med in latest_dict["medications"]:
                res = check_medication_conflict(old_med, new_med)
                if res["status"] == "REVIEW_REQUIRED":
                    medication_changes.append({
                        **res,
                        "previous_report": {
                            "report_id": prev_report.id,
                            "filename": prev_report.filename,
                            "study_date": prev_dict["date"] or "Undated",
                            "context": old_med["context"],
                        },
                        "latest_report": {
                            "report_id": latest_report.id,
                            "filename": latest_report.filename,
                            "study_date": latest_dict["date"] or "Undated",
                            "context": new_med["context"],
                        },
                    })

        # Numeric lab changes only when test name, value, unit, and context are explicitly extracted and units match
        for test_key, old_lab in prev_dict["labs"].items():
            new_lab = latest_dict["labs"].get(test_key)
            if not new_lab:
                continue
            if old_lab["unit"].lower() != new_lab["unit"].lower():
                continue
            if old_lab["value"] != new_lab["value"]:
                lab_changes.append({
                    "type": "LAB_VALUE_CHANGE",
                    "test_name": old_lab["test_name"],
                    "unit": old_lab["unit"],
                    "previous_value": old_lab["value"],
                    "latest_value": new_lab["value"],
                    "previous_report": {
                        "report_id": prev_report.id,
                        "filename": prev_report.filename,
                        "study_date": prev_dict["date"] or "Undated",
                        "context": old_lab["context"],
                    },
                    "latest_report": {
                        "report_id": latest_report.id,
                        "filename": latest_report.filename,
                        "study_date": latest_dict["date"] or "Undated",
                        "context": new_lab["context"],
                    },
                    "message": (
                        f"{old_lab['test_name']} changed from {old_lab['value']} {old_lab['unit']} "
                        f"to {new_lab['value']} {new_lab['unit']}; clinician review advised."
                    ),
                    "needs_human_review": True,
                })

    if potential_contradictions or medication_changes or lab_changes or incomplete_reports:
        overall_status = "REVIEW_RECOMMENDED"
    else:
        overall_status = "NO_CONTRADICTIONS_DETECTED"

    return {
        "status": overall_status,
        "comparability": {
            "comparable": is_comparable,
            "reason": comparability_reason,
            "previous_report_id": prev_report.id,
            "latest_report_id": latest_report.id,
        },
        "missing_information": missing_info_block,
        "potential_contradictions": potential_contradictions,
        "clinical_changes": {
            "findings": comparison_changes or {},
            "medication_changes": medication_changes,
            "lab_changes": lab_changes,
        },
        "counts": {
            "incomplete_reports": len(incomplete_reports),
            "potential_contradictions": len(potential_contradictions),
            "medication_changes": len(medication_changes),
            "lab_changes": len(lab_changes),
        },
        "disclaimer": CONFLICT_DISCLAIMER,
    }
