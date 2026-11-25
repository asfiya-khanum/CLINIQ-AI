
import re


def extract_medical_info(text: str):
    """
    Extract basic medical information from PDF text.
    """

    def find_line(pattern):
        match = re.search(pattern, text, re.IGNORECASE)
        return match.group(1).strip() if match else None

    def find_section(pattern):
        match = re.search(
            pattern,
            text,
            re.IGNORECASE | re.DOTALL
        )

        if match:
            return match.group(1).strip()

        return None

    def find_first(patterns):
        for pattern in patterns:
            value = find_line(pattern)
            if value:
                return value
        return None

    findings = find_section(
        r"Observation\s*:\s*-?\s*(.*?)(?=\n\s*IMPRESSION\s*:|$)"
    )
    if not findings:
        findings = find_section(
            r"Findings\s*:\s*-?\s*(.*?)(?=\n\s*(?:IMPRESSION|CONCLUSION)\s*:|$)"
        )

    impression = find_section(
        r"IMPRESSION\s*:\s*(.*?)(?=\n\s*(?:Patient\s*ID\s*:|END OF REPORT)|$)"
    )
    if not impression:
        impression = find_section(
            r"CONCLUSION\s*:\s*(.*?)(?=\n\s*(?:Patient\s*ID\s*:|END OF REPORT)|$)"
        )

    # Clean bullet symbols while preserving the text
    if impression:
        impression = re.sub(
            r"(?m)^\s*[•▪]\s*",
            "- ",
            impression
        )
        impression = re.sub(
            r"\n*\s*END OF REPORT\s*$",
            "",
            impression,
            flags=re.IGNORECASE,
        ).strip()

    patient_id = find_first([
        r"Patient\s*ID\s*[:\-][ \t]*([^\r\n]+)",
        r"MRN\s*[:\-][ \t]*([^\r\n]+)",
        r"UHID\s*[:\-][ \t]*([^\r\n]+)",
        r"Patient\s*No\.?\s*[:\-][ \t]*([^\r\n]+)",
    ])

    medical_info = {
        "patient_id": patient_id,
        "patient_name": find_line(r"Patient Name\s*:[ \t]*([^\r\n]+)"),
        "patient_age": find_line(r"Age\s*:[ \t]*([^\r\n]+)"),
        "patient_sex": find_line(r"Sex\s*:[ \t]*([^\r\n]+)"),
        "study_name": find_line(r"Study\s*:[ \t]*([^\r\n]+)"),
        "study_date": find_line(r"Study Date\s*:[ \t]*([^\r\n]+)"),
        "findings": findings,
        "impression": impression
    }

    return medical_info
