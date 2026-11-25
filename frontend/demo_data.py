"""
Clearly labelled fictional demo dataset used ONLY when the user explicitly
selects 'Fictional Demo Dataset' preview mode. Never shown as real backend data.
"""

DEMO_PATIENT = {
    "name": "Alex Morgan (Fictional Demo)",
    "patient_id": "DEMO-CLQ-001",
    "age": "46",
    "sex": "Male",
    "department": "Internal Medicine (Demo)",
    "blood_group": "O+",
    "admission_date": "24 November 2026",
    "status": "Under Review (Demo)",
    "report_count": 4,
}

DEMO_DOCUMENTS = [
    {"name": "Demo_Admission_Summary.pdf", "type": "Admission Note", "status": "Processed"},
    {"name": "Demo_Blood_Report.pdf", "type": "Laboratory Report", "status": "Processed"},
    {"name": "Demo_Prescription.docx", "type": "Prescription", "status": "Review Required"},
    {"name": "Demo_Discharge_Summary.pdf", "type": "Discharge Summary", "status": "Pending"},
]

DEMO_MEDICATIONS = [
    {
        "name": "Metformin",
        "dosage": "500 mg",
        "frequency": "Twice daily",
        "source": "Fictional Prescription",
        "status": "Needs Review",
    },
    {
        "name": "Amlodipine",
        "dosage": "5 mg",
        "frequency": "Once daily",
        "source": "Fictional Admission Note",
        "status": "Consistent",
    },
    {
        "name": "Atorvastatin",
        "dosage": "10 mg",
        "frequency": "Once daily",
        "source": "Fictional Old Record",
        "status": "Outdated Record",
    },
]

DEMO_CONFLICTS = [
    {
        "title": "Fictional Medication Dosage Mismatch",
        "description": (
            "Illustrative example: dosage recorded in two fictional documents "
            "differs and would require clinician verification."
        ),
        "severity": "High",
    },
    {
        "title": "Fictional Missing Laboratory Result",
        "description": (
            "Illustrative example: a referenced lab result is not present "
            "in the fictional sample document set."
        ),
        "severity": "Medium",
    },
    {
        "title": "Fictional Date Inconsistency",
        "description": (
            "Illustrative example: dates in two fictional records differ "
            "and require manual review."
        ),
        "severity": "Low",
    },
]

DEMO_TIMELINE = [
    {
        "date": "24 Nov 2026 | 09:30 AM",
        "title": "Fictional Patient Admission",
        "description": "Sample admission record added to the fictional demo file.",
    },
    {
        "date": "24 Nov 2026 | 11:15 AM",
        "title": "Fictional Laboratory Report Uploaded",
        "description": "Sample laboratory report added for demo review.",
    },
    {
        "date": "24 Nov 2026 | 01:00 PM",
        "title": "Fictional Medication Record Updated",
        "description": "Sample medication information entered into the demo record.",
    },
    {
        "date": "24 Nov 2026 | 03:30 PM",
        "title": "Fictional Clinical Review Pending",
        "description": "Sample reconciliation note requiring human verification.",
    },
]
