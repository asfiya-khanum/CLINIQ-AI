from collections import Counter
import re

from backend.clinical import (
    NEGATION_PATTERN,
    _split_clauses,
    build_patient_timeline,
    deduplicate_abnormal_flags,
    deserialize_flags,
    sort_reports_chronologically,
)
from backend.conflict_detection import analyze_patient_conflicts


CLINICAL_DISCLAIMER = (
    "CLINIQ AI provides structured clinical observations and plain-language "
    "terminology explanations for informational support only. It is not a "
    "diagnostic tool and does not replace evaluation by a qualified clinician."
)

IMPROVING_PATTERN = re.compile(
    r"\b(?:improv(?:ed|ing|ement)|resolv(?:ed|ing|ution)|decreas(?:ed|ing)|"
    r"reduc(?:ed|tion)|smaller|interval decrease|clear(?:ed|ing)|subsided|"
    r"diminished|regressed|less prominent)\b",
    re.IGNORECASE,
)

WORSENING_PATTERN = re.compile(
    r"\b(?:worsen(?:ed|ing)|progress(?:ed|ion|ive)|increas(?:ed|ing)|"
    r"enlarg(?:ed|ing|ement)|larger|interval increase|newly|new\b|"
    r"expanded|extending|more prominent|deteriorat(?:ed|ing)|aggravated)\b",
    re.IGNORECASE,
)

UNCHANGED_PATTERN = re.compile(
    r"\b(?:unchanged|stable|no significant change|no interval change|"
    r"similar to prior|persists|persistent|redemonstrated|stationary)\b",
    re.IGNORECASE,
)

SEVERITY_RANK = {
    "normal": 0,
    "moderate": 1,
    "review_recommended": 1,
    "high": 2,
    "attention_needed": 2,
}

# Plain-language medical glossary that preserves original clinical meaning
# without turning descriptive findings into diagnoses.
MEDICAL_GLOSSARY = [
    {
        "term": "bone marrow edema",
        "patterns": ("bone marrow edema", "marrow edema"),
        "category": "Musculoskeletal / Soft Tissue",
        "plain_meaning": (
            "Increased fluid signal inside the spongy inner part of a bone, "
            "often linked to stress, bruising, inflammation, or nearby joint irritation."
        ),
    },
    {
        "term": "subcutaneous edema",
        "patterns": ("subcutaneous edema", "soft tissue edema"),
        "category": "Musculoskeletal / Soft Tissue",
        "plain_meaning": (
            "Swelling caused by extra fluid in the soft tissue layer just under the skin."
        ),
    },
    {
        "term": "periarticular fluid",
        "patterns": ("periarticular fluid", "intra and periarticular fluid", "joint effusion"),
        "category": "Musculoskeletal / Soft Tissue",
        "plain_meaning": (
            "Extra fluid inside or directly around a joint space, commonly seen with "
            "joint irritation, strain, or inflammation."
        ),
    },
    {
        "term": "fluid collection",
        "patterns": ("fluid collection",),
        "category": "Musculoskeletal / Soft Tissue",
        "plain_meaning": (
            "A localized pocket of fluid seen on imaging; clinical correlation is "
            "needed to determine its underlying cause."
        ),
    },
    {
        "term": "synovitis",
        "patterns": ("synovitis",),
        "category": "Musculoskeletal / Soft Tissue",
        "plain_meaning": (
            "Inflammation of the thin lining (synovium) that surrounds a joint."
        ),
    },
    {
        "term": "osteomyelitis",
        "patterns": ("osteomyelitis",),
        "category": "Critical / Acute",
        "plain_meaning": (
            "Inflammation or possible infection involving bone tissue; when noted "
            "as a possibility on imaging, doctors correlate with exams and lab tests."
        ),
    },
    {
        "term": "pleural effusion",
        "patterns": ("pleural effusion",),
        "category": "Cardiopulmonary",
        "plain_meaning": (
            "Extra fluid in the thin space between the lungs and the chest wall."
        ),
    },
    {
        "term": "pulmonary edema",
        "patterns": ("pulmonary edema",),
        "category": "Cardiopulmonary",
        "plain_meaning": (
            "Fluid buildup in the air spaces or tissue of the lungs."
        ),
    },
    {
        "term": "cardiomegaly",
        "patterns": ("cardiomegaly",),
        "category": "Cardiopulmonary",
        "plain_meaning": (
            "An enlarged heart shadow seen on imaging compared with typical size limits."
        ),
    },
    {
        "term": "consolidation",
        "patterns": ("consolidation",),
        "category": "Cardiopulmonary",
        "plain_meaning": (
            "An area of lung tissue filled with fluid or inflammatory cells instead of air, "
            "often seen with lung infection such as pneumonia."
        ),
    },
    {
        "term": "pneumonia",
        "patterns": ("pneumonia",),
        "category": "Cardiopulmonary",
        "plain_meaning": (
            "Lung inflammation or infection affecting the small air sacs."
        ),
    },
    {
        "term": "atelectasis",
        "patterns": ("atelectasis",),
        "category": "Cardiopulmonary",
        "plain_meaning": (
            "Partial collapse or incomplete expansion of a small area of the lung."
        ),
    },
    {
        "term": "pneumothorax",
        "patterns": ("pneumothorax",),
        "category": "Critical / Acute",
        "plain_meaning": (
            "Air trapped in the space between the lung and the chest wall."
        ),
    },
    {
        "term": "opacity",
        "patterns": ("opacity",),
        "category": "Cardiopulmonary",
        "plain_meaning": (
            "A denser or whiter-looking area on an X-ray or scan that blocks more rays "
            "than surrounding tissue."
        ),
    },
    {
        "term": "fracture",
        "patterns": ("fracture",),
        "category": "Critical / Acute",
        "plain_meaning": (
            "A break or crack in the continuity of a bone."
        ),
    },
    {
        "term": "nodule",
        "patterns": ("nodule",),
        "category": "Structural / Lesion",
        "plain_meaning": (
            "A small, rounded spot or growth of tissue seen on a scan."
        ),
    },
    {
        "term": "lesion",
        "patterns": ("lesion",),
        "category": "Structural / Lesion",
        "plain_meaning": (
            "A general term for an area of tissue that looks changed or abnormal on imaging."
        ),
    },
    {
        "term": "cyst",
        "patterns": ("cyst",),
        "category": "Structural / Lesion",
        "plain_meaning": (
            "A closed sac-like pocket that usually contains fluid."
        ),
    },
    {
        "term": "stenosis",
        "patterns": ("stenosis",),
        "category": "Structural / Lesion",
        "plain_meaning": (
            "Narrowing of a passage, canal, or blood vessel."
        ),
    },
    {
        "term": "herniation",
        "patterns": ("herniation", "disc bulge"),
        "category": "Musculoskeletal / Soft Tissue",
        "plain_meaning": (
            "A spinal disc bulging or pushing outward beyond its usual boundary."
        ),
    },
    {
        "term": "edema",
        "patterns": ("edema",),
        "category": "Fluid / Swelling",
        "plain_meaning": (
            "Swelling caused by excess fluid trapped in body tissues."
        ),
    },
    {
        "term": "effusion",
        "patterns": ("effusion",),
        "category": "Fluid / Swelling",
        "plain_meaning": (
            "An abnormal buildup of fluid inside a body cavity or joint space."
        ),
    },
    {
        "term": "tibiotalar and subtalar joint",
        "patterns": ("tibiotalar", "subtalar"),
        "category": "Anatomy",
        "plain_meaning": (
            "The main ankle joint (tibiotalar) and the joint just below it in the hindfoot (subtalar)."
        ),
    },
    {
        "term": "talus and calcaneum",
        "patterns": ("talus", "calcaneum"),
        "category": "Anatomy",
        "plain_meaning": (
            "The ankle bone (talus) and the heel bone (calcaneum/calcaneus)."
        ),
    },
    {
        "term": "interphalangeal joint",
        "patterns": ("interphalageal", "interphalangeal", "proximal phalanx"),
        "category": "Anatomy",
        "plain_meaning": (
            "Small bones (phalanges) and joints of the toes or fingers."
        ),
    },
    {
        "term": "cardiac silhouette",
        "patterns": ("cardiac silhouette",),
        "category": "Anatomy",
        "plain_meaning": (
            "The outline of the heart as seen on a chest X-ray."
        ),
    },
]


def _brief_report_ref(report) -> dict:
    return {
        "report_id": report.id,
        "filename": report.filename,
        "study_name": report.study_name,
        "study_date": report.study_date,
        "study_date_iso": (
            report.study_date_parsed.isoformat() if report.study_date_parsed else None
        ),
        "uploaded_at": report.created_at.isoformat() if report.created_at else None,
        "severity": report.severity or "normal",
        "clinical_summary": report.clinical_summary,
    }


def _study_names_compatible(prev_name: str | None, latest_name: str | None) -> bool:
    if not prev_name or not latest_name:
        return True
    p_tokens = set(re.findall(r"[a-z]+", prev_name.lower()))
    l_tokens = set(re.findall(r"[a-z]+", latest_name.lower()))
    stop = {"plain", "contrast", "followup", "follow", "up", "initial", "study", "report"}
    p_core = p_tokens - stop
    l_core = l_tokens - stop
    if not p_core or not l_core:
        return True
    return bool(p_core & l_core)


def _clause_negates_term(clause: str, term: str) -> bool:
    match = re.search(rf"\b{re.escape(term)}\b", clause, re.IGNORECASE)
    if not match:
        return False
    return bool(NEGATION_PATTERN.search(clause[: match.start()]))


def _find_matching_clause(clauses: list[str], term: str) -> str | None:
    pattern = re.compile(rf"\b{re.escape(term)}\b", re.IGNORECASE)
    for clause in clauses:
        if pattern.search(clause):
            return clause
    return None


def explain_medical_terminology(
    findings: str | None,
    impression: str | None,
    abnormal_flags: list[dict] | None = None,
) -> dict:
    """
    Generate patient-friendly, rule-based glossary explanations for medical terms
    found in the report text while preserving the original context and meaning.
    """
    sections = []
    if impression:
        sections.append(("impression", _split_clauses(impression)))
    if findings:
        sections.append(("findings", _split_clauses(findings)))

    explanations: list[dict] = []
    covered_patterns: list[str] = []

    for entry in MEDICAL_GLOSSARY:
        matched_clause = None
        matched_source = None
        matched_phrase = None

        for pattern_text in entry["patterns"]:
            # Avoid duplicating generic "edema" when a specific edema phrase already matched
            if pattern_text in {"edema", "effusion"} and any(
                pattern_text in prev and prev != pattern_text for prev in covered_patterns
            ):
                continue

            regex = re.compile(rf"\b{re.escape(pattern_text)}\b", re.IGNORECASE)
            for source_name, clauses in sections:
                for clause in clauses:
                    if regex.search(clause):
                        matched_clause = clause
                        matched_source = source_name
                        matched_phrase = pattern_text
                        break
                if matched_clause:
                    break
            if matched_clause:
                break

        if not matched_clause:
            continue

        covered_patterns.append(matched_phrase)
        is_negated = _clause_negates_term(matched_clause, matched_phrase)
        context_note = (
            "Reported as absent or normal in this statement."
            if is_negated
            else "Reported as present or noted for clinical correlation."
        )

        explanations.append({
            "term": entry["term"],
            "matched_phrase": matched_phrase,
            "category": entry["category"],
            "plain_meaning": entry["plain_meaning"],
            "status_in_report": "negated_or_normal" if is_negated else "noted",
            "context_note": context_note,
            "source": matched_source,
            "source_context": matched_clause[:260],
            "explanation_source": "rule_based_glossary",
        })

    # Deduplicate abnormal flags case-insensitively before building the plain-language overview
    unique_flags = deduplicate_abnormal_flags(abnormal_flags)
    flag_count = len(unique_flags)
    if flag_count == 0:
        plain_summary = (
            "Rule-based review did not flag abnormal keywords in the extracted "
            "findings or impression. Review the full report with your clinician."
        )
    else:
        terms_text = ", ".join(f["term"] for f in unique_flags[:5])
        plain_summary = (
            f"Rule-based review highlighted {flag_count} notable finding term(s) "
            f"({terms_text}). See the terminology explanations below for plain-language "
            "definitions grounded in your report text."
        )

    return {
        "source": "rule_based_glossary",
        "ai_generated": False,
        "plain_language_summary": plain_summary,
        "terminology_count": len(explanations),
        "terminology_explanations": explanations,
    }


def compare_patient_reports(
    reports: list,
    previous_report_id: int | None = None,
    latest_report_id: int | None = None,
) -> dict:
    """
    Compare a patient's previous and latest medical reports conservatively,
    identifying newly appearing, improving, worsening, and unchanged findings
    only when supported by available report data.
    """
    ordered = sort_reports_chronologically(reports, descending=False)

    if len(ordered) < 2:
        conflict_data = analyze_patient_conflicts(ordered)
        return {
            "comparison_available": False,
            "reason": "At least two reports are required to compare changes over time.",
            "previous_report": None,
            "latest_report": _brief_report_ref(ordered[-1]) if ordered else None,
            "study_compatibility": None,
            "changes": {
                "newly_appearing": [],
                "improving": [],
                "worsening": [],
                "unchanged": [],
                "not_mentioned_in_latest": [],
            },
            "conflict_detection": conflict_data,
            "rule_based_observations": {
                "source": "rule_based_comparison",
                "ai_generated": False,
                "summary": (
                    "Only one report is on file for this patient; longitudinal "
                    "comparison will become available after another study is uploaded."
                ),
                "counts": {
                    "newly_appearing": 0,
                    "improving": 0,
                    "worsening": 0,
                    "unchanged": 0,
                    "not_mentioned_in_latest": 0,
                },
            },
        }

    by_id = {r.id: r for r in ordered}
    if previous_report_id is not None or latest_report_id is not None:
        if previous_report_id not in by_id or latest_report_id not in by_id:
            return {
                "comparison_available": False,
                "reason": "Requested report IDs were not found for this patient.",
                "previous_report": None,
                "latest_report": None,
                "study_compatibility": None,
                "changes": {
                    "newly_appearing": [],
                    "improving": [],
                    "worsening": [],
                    "unchanged": [],
                    "not_mentioned_in_latest": [],
                },
                "rule_based_observations": {
                    "source": "rule_based_comparison",
                    "ai_generated": False,
                    "summary": "Requested reports could not be compared.",
                    "counts": {
                        "newly_appearing": 0,
                        "improving": 0,
                        "worsening": 0,
                        "unchanged": 0,
                        "not_mentioned_in_latest": 0,
                    },
                },
            }
        prev_report = by_id[previous_report_id]
        latest_report = by_id[latest_report_id]
    else:
        prev_report = ordered[-2]
        latest_report = ordered[-1]

    if prev_report.id == latest_report.id:
        conflict_data = analyze_patient_conflicts(
            ordered,
            prev_report=prev_report,
            latest_report=latest_report,
        )
        return {
            "comparison_available": False,
            "reason": "Two distinct report records are required; cannot compare a report with itself.",
            "previous_report": _brief_report_ref(prev_report),
            "latest_report": _brief_report_ref(latest_report),
            "study_compatibility": None,
            "changes": {
                "newly_appearing": [],
                "improving": [],
                "worsening": [],
                "unchanged": [],
                "not_mentioned_in_latest": [],
            },
            "conflict_detection": conflict_data,
            "rule_based_observations": {
                "source": "rule_based_comparison",
                "ai_generated": False,
                "summary": "Comparison skipped because the same report record was selected twice.",
                "counts": {
                    "newly_appearing": 0,
                    "improving": 0,
                    "worsening": 0,
                    "unchanged": 0,
                    "not_mentioned_in_latest": 0,
                },
            },
        }

    same_study_date = (
        prev_report.study_date_parsed is not None
        and prev_report.study_date_parsed == latest_report.study_date_parsed
    )
    identical_content = (
        (prev_report.raw_text or "").strip() == (latest_report.raw_text or "").strip()
        and (prev_report.findings or "").strip() == (latest_report.findings or "").strip()
        and (prev_report.impression or "").strip() == (latest_report.impression or "").strip()
    )

    prev_flags = deserialize_flags(prev_report.abnormal_flags_json)
    latest_flags = deserialize_flags(latest_report.abnormal_flags_json)

    prev_by_term = {f["term"].lower(): f for f in prev_flags}
    latest_by_term = {f["term"].lower(): f for f in latest_flags}

    latest_clauses = _split_clauses(
        "\n".join(part for part in (latest_report.impression, latest_report.findings) if part)
    )

    compatible = _study_names_compatible(prev_report.study_name, latest_report.study_name)

    newly_appearing: list[dict] = []
    improving: list[dict] = []
    worsening: list[dict] = []
    unchanged: list[dict] = []
    not_mentioned_in_latest: list[dict] = []

    for term_key, l_flag in latest_by_term.items():
        clause = _find_matching_clause(latest_clauses, l_flag["term"]) or l_flag.get("context", "")
        has_improving_cue = bool(IMPROVING_PATTERN.search(clause))
        has_worsening_cue = bool(WORSENING_PATTERN.search(clause))
        has_unchanged_cue = bool(UNCHANGED_PATTERN.search(clause))

        if term_key not in prev_by_term:
            # If the latest report itself explicitly states the finding is improving/resolving,
            # report that cue honestly rather than calling an improving item brand-new.
            if has_improving_cue and not has_worsening_cue:
                improving.append({
                    "finding": l_flag["term"],
                    "category": l_flag["category"],
                    "severity": l_flag["severity"],
                    "evidence_previous": None,
                    "evidence_latest": clause[:260],
                    "basis": "explicit_improving_wording_in_latest",
                })
            else:
                newly_appearing.append({
                    "finding": l_flag["term"],
                    "category": l_flag["category"],
                    "severity": l_flag["severity"],
                    "evidence_previous": None,
                    "evidence_latest": clause[:260],
                    "basis": (
                        "explicit_new_wording_and_not_in_previous"
                        if has_worsening_cue
                        else "present_in_latest_not_flagged_in_previous"
                    ),
                })
            continue

        p_flag = prev_by_term[term_key]
        prev_rank = SEVERITY_RANK.get(p_flag.get("severity", "moderate"), 1)
        latest_rank = SEVERITY_RANK.get(l_flag.get("severity", "moderate"), 1)

        if has_improving_cue and not has_worsening_cue:
            improving.append({
                "finding": l_flag["term"],
                "category": l_flag["category"],
                "severity": l_flag["severity"],
                "evidence_previous": p_flag.get("context"),
                "evidence_latest": clause[:260],
                "basis": "explicit_improving_wording",
            })
        elif has_worsening_cue or latest_rank > prev_rank:
            worsening.append({
                "finding": l_flag["term"],
                "category": l_flag["category"],
                "severity": l_flag["severity"],
                "evidence_previous": p_flag.get("context"),
                "evidence_latest": clause[:260],
                "basis": (
                    "explicit_worsening_wording"
                    if has_worsening_cue
                    else "severity_increase"
                ),
            })
        else:
            unchanged.append({
                "finding": l_flag["term"],
                "category": l_flag["category"],
                "severity": l_flag["severity"],
                "evidence_previous": p_flag.get("context"),
                "evidence_latest": clause[:260],
                "basis": (
                    "explicit_stable_wording"
                    if has_unchanged_cue
                    else "flagged_in_both_reports_without_change_cue"
                ),
            })

    # Check findings from previous report that were NOT flagged in latest report
    for term_key, p_flag in prev_by_term.items():
        if term_key in latest_by_term:
            continue

        matching_clause = _find_matching_clause(latest_clauses, p_flag["term"])
        if matching_clause and (
            _clause_negates_term(matching_clause, p_flag["term"])
            or IMPROVING_PATTERN.search(matching_clause)
        ):
            improving.append({
                "finding": p_flag["term"],
                "category": p_flag["category"],
                "severity": "normal",
                "evidence_previous": p_flag.get("context"),
                "evidence_latest": matching_clause[:260],
                "basis": "resolved_or_negated_in_latest",
            })
        else:
            not_mentioned_in_latest.append({
                "finding": p_flag["term"],
                "category": p_flag["category"],
                "previous_severity": p_flag["severity"],
                "evidence_previous": p_flag.get("context"),
                "note": (
                    "Flagged in the previous report but not mentioned in the latest report; "
                    "not automatically marked improved because absence of text is not confirmation."
                ),
            })

    summary_parts = [
        f"Compared Report #{prev_report.id} '{prev_report.study_name or prev_report.filename}' "
        f"({prev_report.study_date or 'undated'}) with Report #{latest_report.id} "
        f"'{latest_report.study_name or latest_report.filename}' ({latest_report.study_date or 'undated'})."
    ]
    if same_study_date:
        summary_parts.append(
            "Both records share the same study date and were ordered by upload timestamp and report ID."
        )
    if identical_content:
        summary_parts.append(
            "Both records contain identical extracted report text (possible duplicate upload); no clinical change is inferred."
        )
    if not compatible:
        summary_parts.append(
            "Note: these reports appear to be different study types, so cross-study differences may reflect different body areas rather than progression."
        )
    summary_parts.append(
        f"Counts — newly appearing: {len(newly_appearing)}, improving: {len(improving)}, "
        f"worsening: {len(worsening)}, unchanged: {len(unchanged)}, "
        f"not mentioned in latest: {len(not_mentioned_in_latest)}."
    )

    changes_payload = {
        "newly_appearing": newly_appearing,
        "improving": improving,
        "worsening": worsening,
        "unchanged": unchanged,
        "not_mentioned_in_latest": not_mentioned_in_latest,
    }
    conflict_data = analyze_patient_conflicts(
        ordered,
        prev_report=prev_report,
        latest_report=latest_report,
        comparison_changes=changes_payload,
        compatible_study_type=compatible,
        identical_content=identical_content,
    )

    return {
        "comparison_available": True,
        "previous_report": _brief_report_ref(prev_report),
        "latest_report": _brief_report_ref(latest_report),
        "study_compatibility": {
            "compatible_study_type": compatible,
            "same_study_date": same_study_date,
            "identical_content": identical_content,
            "note": (
                "Identical clinical text detected across two separate records (ordered by upload time / ID)."
                if identical_content
                else (
                    "Same study date across two separate records (ordered by upload time / ID)."
                    if same_study_date
                    else (
                        "Comparable study types."
                        if compatible
                        else "Different study types detected; interpret differences with clinical context."
                    )
                )
            ),
        },
        "changes": changes_payload,
        "conflict_detection": conflict_data,
        "rule_based_observations": {
            "source": "rule_based_comparison",
            "ai_generated": False,
            "summary": " ".join(summary_parts),
            "counts": {
                "newly_appearing": len(newly_appearing),
                "improving": len(improving),
                "worsening": len(worsening),
                "unchanged": len(unchanged),
                "not_mentioned_in_latest": len(not_mentioned_in_latest),
            },
        },
    }


def build_report_clinical_analysis(report) -> dict:
    """Build combined clinical analysis for a single report."""
    flags = deserialize_flags(report.abnormal_flags_json)
    explanations = explain_medical_terminology(
        report.findings,
        report.impression,
        flags,
    )
    category_counts = dict(Counter(f.get("category", "Other") for f in flags))

    return {
        "report": {
            **_brief_report_ref(report),
            "patient_id": report.patient_id,
            "page_count": report.page_count,
            "patient_name": report.patient_name,
            "patient_age": report.patient_age,
            "patient_sex": report.patient_sex,
            "findings": report.findings,
            "impression": report.impression,
        },
        "rule_based_observations": {
            "source": "rule_based_engine",
            "ai_generated": False,
            "severity": report.severity or "normal",
            "total_abnormal_flags": len(flags),
            "category_breakdown": category_counts,
            "abnormal_flags": flags,
            "clinical_summary": report.clinical_summary,
        },
        "patient_friendly_explanations": explanations,
        "ai_generated_explanations": {
            "enabled": False,
            "source": "ai_model",
            "summary": None,
            "note": (
                "No external AI model is configured; all observations and "
                "terminology explanations above are generated deterministically."
            ),
        },
        "clinical_disclaimer": CLINICAL_DISCLAIMER,
    }


def build_patient_clinical_analysis(patient, reports: list) -> dict:
    """
    Combine patient profile, timeline, report comparison, abnormal flags,
    terminology explanations, and dashboard KPIs into one structured response.
    """
    timeline_data = build_patient_timeline(reports)
    comparison_data = compare_patient_reports(reports)
    ordered = sort_reports_chronologically(reports, descending=False)
    latest_report = ordered[-1] if ordered else None

    all_flags: list[dict] = []
    category_counter: Counter = Counter()
    severity_counter: Counter = Counter()

    for report in ordered:
        severity_counter[report.severity or "normal"] += 1
        flags = deserialize_flags(report.abnormal_flags_json)
        for flag in flags:
            category_counter[flag.get("category", "Other")] += 1
            all_flags.append({
                "report_id": report.id,
                "study_name": report.study_name,
                "study_date": report.study_date,
                **flag,
            })

    latest_flags = deserialize_flags(latest_report.abnormal_flags_json) if latest_report else []
    latest_explanations = (
        explain_medical_terminology(
            latest_report.findings,
            latest_report.impression,
            latest_flags,
        )
        if latest_report
        else {
            "source": "rule_based_glossary",
            "ai_generated": False,
            "plain_language_summary": "No reports available yet for terminology review.",
            "terminology_count": 0,
            "terminology_explanations": [],
        }
    )

    return {
        "patient": {
            "patient_id": patient.patient_id,
            "name": patient.name,
            "age": patient.age,
            "sex": patient.sex,
            "report_count": len(ordered),
        },
        "latest_report": (
            {
                **_brief_report_ref(latest_report),
                "findings": latest_report.findings,
                "impression": latest_report.impression,
                "abnormal_flags": latest_flags,
            }
            if latest_report
            else None
        ),
        "timeline": timeline_data,
        "comparison": comparison_data,
        "conflict_detection": comparison_data.get("conflict_detection"),
        "rule_based_observations": {
            "source": "rule_based_engine",
            "ai_generated": False,
            "overall_severity": timeline_data["overall_severity"],
            "overview_summary": timeline_data["overview_summary"],
            "total_abnormal_flags": len(all_flags),
            "flagged_terms": timeline_data["flagged_terms"],
            "abnormal_flags": all_flags,
        },
        "patient_friendly_explanations": latest_explanations,
        "ai_generated_explanations": {
            "enabled": False,
            "source": "ai_model",
            "summary": None,
            "note": (
                "No external AI model is configured; all observations, comparisons, "
                "and terminology explanations are rule-based."
            ),
        },
        "dashboard": {
            "cards": {
                "total_reports": len(ordered),
                "dated_reports": timeline_data["dated_reports"],
                "overall_severity": timeline_data["overall_severity"],
                "latest_study_date": (
                    latest_report.study_date_parsed.isoformat()
                    if latest_report and latest_report.study_date_parsed
                    else (latest_report.study_date if latest_report else None)
                ),
                "active_flags_in_latest": len(latest_flags),
                "comparison_available": comparison_data["comparison_available"],
            },
            "severity_distribution": {
                "attention_needed": severity_counter.get("attention_needed", 0),
                "review_recommended": severity_counter.get("review_recommended", 0),
                "normal": severity_counter.get("normal", 0),
            },
            "category_breakdown": dict(category_counter),
            "change_counts": comparison_data["rule_based_observations"]["counts"],
        },
        "clinical_disclaimer": CLINICAL_DISCLAIMER,
    }
