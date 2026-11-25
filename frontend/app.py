import importlib
import os
import re
import sys

import pandas as pd
import plotly.graph_objects as go
import streamlit as st


def _load_frontend_modules():
    try:
        from frontend import api_client, components, demo_data, document_handler
    except ModuleNotFoundError:
        import api_client
        import components
        import demo_data
        import document_handler

    # Track file mtimes across Streamlit reruns so edits to submodules take effect immediately
    mtimes = getattr(sys, "_cliniq_frontend_mtimes", None)
    if mtimes is None:
        mtimes = {}
        setattr(sys, "_cliniq_frontend_mtimes", mtimes)

    for mod in (api_client, components, demo_data, document_handler):
        mod_file = getattr(mod, "__file__", None)
        if mod_file and os.path.exists(mod_file):
            mtime = os.path.getmtime(mod_file)
            prev_mtime = mtimes.get(mod.__name__)
            if prev_mtime is not None and prev_mtime != mtime:
                importlib.reload(mod)
            mtimes[mod.__name__] = mtime

    return api_client, components, demo_data, document_handler


_api_client, _components, _demo_data, _document_handler = _load_frontend_modules()
CliniqApiClient = _api_client.CliniqApiClient
DEFAULT_API_URL = _api_client.DEFAULT_API_URL
app_footer = _components.app_footer
conflict_card = _components.conflict_card
demo_mode_banner = _components.demo_mode_banner
document_card = _components.document_card
empty_state = _components.empty_state
info_card = _components.info_card
load_custom_css = _components.load_custom_css
metric_card = _components.metric_card
page_header = _components.page_header
patient_banner = _components.patient_banner
section_header = _components.section_header
severity_badge_color = _components.severity_badge_color
terminology_card = _components.terminology_card
timeline_item = _components.timeline_item
DEMO_CONFLICTS = _demo_data.DEMO_CONFLICTS
DEMO_DOCUMENTS = _demo_data.DEMO_DOCUMENTS
DEMO_MEDICATIONS = _demo_data.DEMO_MEDICATIONS
DEMO_PATIENT = _demo_data.DEMO_PATIENT
DEMO_TIMELINE = _demo_data.DEMO_TIMELINE
document_upload_section = _document_handler.document_upload_section


# =========================================================
# PAGE CONFIGURATION & THEME
# =========================================================

st.set_page_config(
    page_title="CLINIQ AI | Agentic Clinical Intelligence",
    page_icon=":material/local_hospital:",
    layout="wide",
    initial_sidebar_state="expanded",
)

load_custom_css()

CHART_LAYOUT = {
    "paper_bgcolor": "rgba(0,0,0,0)",
    "plot_bgcolor": "rgba(0,0,0,0)",
    "font": {"color": "#0F172A", "family": "Inter, sans-serif", "size": 12},
    "margin": dict(l=16, r=16, t=24, b=16),
    "legend": dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
}

MEDICATION_DOSE_PATTERN = re.compile(
    r"\b([A-Z][a-zA-Z]{2,}(?:\s+[A-Z][a-zA-Z]+)?)\s+(\d+(?:\.\d+)?\s*(?:mg|mcg|g|ml|iu|units))\b",
    re.IGNORECASE,
)


def get_api_client() -> CliniqApiClient:
    api_url = st.session_state.get("cliniq_api_url") or DEFAULT_API_URL
    return CliniqApiClient(base_url=api_url)


def navigate_to(page_key: str):
    st.session_state.active_page = page_key
    st.rerun()


def show_backend_offline_notice(error_message: str | None = None):
    st.error(
        error_message or f"FastAPI backend is not reachable at {get_api_client().base_url}.",
        title="Backend connection unavailable",
        icon=":material/cloud_off:",
    )
    st.info(
        "Start the FastAPI backend in a separate terminal with:\n"
        "`python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000` (using `.venv`), "
        "or switch Data source to Fictional Demo Dataset in the sidebar to preview UI layouts.",
        icon=":material/terminal:",
    )


def show_no_patients_notice():
    empty_state(
        "No patient reports are stored in SQLite yet. Upload one or more PDF reports in Document Center to begin.",
        icon=":material/upload_file:",
    )


def load_patient_analysis(client: CliniqApiClient, patient_id: str | None) -> dict | None:
    if not patient_id:
        return None
    with st.spinner("Loading clinical intelligence from FastAPI..."):
        resp = client.get_patient_analysis(patient_id)
    if not resp["ok"]:
        st.error(resp["error"], title="Unable to load patient analysis", icon=":material/error:")
        return None
    return resp["data"]


# =========================================================
# SIDEBAR NAVIGATION & BACKEND STATUS
# =========================================================

if "active_page" not in st.session_state:
    st.session_state.active_page = "dashboard"

if "cliniq_api_url" not in st.session_state:
    st.session_state.cliniq_api_url = os.getenv("CLINIQ_API_URL") or DEFAULT_API_URL

if "data_source_mode" not in st.session_state:
    st.session_state.data_source_mode = "Live FastAPI Backend"

client = get_api_client()
health_resp = client.check_health()
backend_online = health_resp["ok"]

patients_list: list[dict] = []
patients_error = None
if backend_online:
    patients_resp = client.list_patients()
    if patients_resp["ok"]:
        patients_list = patients_resp["data"].get("patients", [])
    else:
        patients_error = patients_resp["error"]

with st.sidebar:
    st.markdown("## :material/local_hospital: CLINIQ AI")
    st.caption("Agentic Clinical Intelligence for Patient Reconstruction")

    st.caption("WORKSPACE")

    pages = [
        ("Executive Dashboard", "dashboard", ":material/dashboard:"),
        ("Patient Intelligence", "patient", ":material/person_search:"),
        ("Document Center", "documents", ":material/upload_file:"),
        ("Clinical Timeline", "timeline", ":material/timeline:"),
        ("Medication Reconciliation", "medications", ":material/medication:"),
        ("Conflict Intelligence", "conflicts", ":material/compare_arrows:"),
        ("AI Reconstruction", "reconstruction", ":material/neurology:"),
    ]

    for label, key, icon in pages:
        if st.button(
            label,
            key=f"nav_{key}",
            icon=icon,
            width="stretch",
            type=("primary" if st.session_state.active_page == key else "secondary"),
        ):
            st.session_state.active_page = key
            st.rerun()

    st.space("small")

    st.radio(
        "Data source",
        ["Live FastAPI Backend", "Fictional Demo Dataset"],
        key="data_source_mode",
        help="Live mode reads real SQLite records from FastAPI. Fictional Demo mode previews illustrative layouts.",
    )

    is_demo_mode = st.session_state.data_source_mode == "Fictional Demo Dataset"

    selected_patient_id = None
    if not is_demo_mode and backend_online:
        if patients_list:
            patient_ids = [p["patient_id"] for p in patients_list]
            pending_patient_id = st.session_state.pop("pending_selected_patient_id", None)
            if pending_patient_id:
                if pending_patient_id in patient_ids:
                    st.session_state["selected_patient_id"] = pending_patient_id
                elif st.session_state.get("selected_patient_id") not in patient_ids:
                    st.session_state["selected_patient_id"] = patient_ids[0]
            elif st.session_state.get("selected_patient_id") not in patient_ids:
                st.session_state["selected_patient_id"] = patient_ids[0]

            labels_by_id = {
                p["patient_id"]: f"{p['patient_id']} — {p.get('name') or 'Unnamed'} ({p.get('report_count', 0)})"
                for p in patients_list
            }
            selected_patient_id = st.selectbox(
                "Active patient",
                patient_ids,
                format_func=lambda pid: labels_by_id.get(pid, pid),
                key="selected_patient_id",
                help="Select a patient persisted in SQLite to inspect their clinical intelligence.",
            )
        else:
            if not patients_error:
                st.session_state.pop("pending_selected_patient_id", None)
            st.caption("No patients stored in backend yet.")

    with st.container(border=True):
        st.caption("SYSTEM STATUS")
        if backend_online:
            st.badge("Backend Connected", icon=":material/check_circle:", color="green")
            if patients_error:
                st.caption("FastAPI connected • Patient list unavailable")
            else:
                st.caption(f"{len(patients_list)} patient(s) in SQLite")
        else:
            st.badge("Backend Offline", icon=":material/cloud_off:", color="red")
            st.caption(health_resp["error"] or "Start uvicorn on port 8000")
        st.caption(f"Endpoint: `{client.base_url}`")

    if st.button(
        "Refresh connection",
        icon=":material/refresh:",
        key="refresh_backend_btn",
        width="stretch",
    ):
        st.rerun()

    st.caption("CLINIQ AI · v1.2.0")


# =========================================================
# HERO WORKFLOW BANNER
# =========================================================

def render_welcome_banner(is_demo: bool):
    with st.container(border=True):
        top_left, top_right = st.columns([3, 1], vertical_alignment="center")
        with top_left:
            st.markdown("### :material/clinical_notes: Agentic Clinical Intelligence for Patient Reconstruction")
            st.write(
                "Transform scattered medical PDFs into chronological timelines, plain-language "
                "terminology explanations, and conservative cross-report comparisons."
            )
        with top_right:
            if is_demo:
                st.badge("Fictional Demo Dataset", icon=":material/science:", color="orange")
            elif backend_online:
                st.badge("Live FastAPI + SQLite", icon=":material/database:", color="green")
            else:
                st.badge("Backend Offline", icon=":material/cloud_off:", color="red")

        step_cols = st.columns(4)
        steps = [
            ("1. Upload reports", "PDF upload & OCR", ":material/upload_file:"),
            ("2. Extract records", "Metadata & findings", ":material/fact_check:"),
            ("3. Review intelligence", "Flags & terminology", ":material/insights:"),
            ("4. Compare history", "Longitudinal diffs", ":material/compare_arrows:"),
        ]
        for col, (title, desc, icon) in zip(step_cols, steps):
            with col:
                st.markdown(f"**{icon} {title}**")
                st.caption(desc)

        with st.container(horizontal=True):
            if st.button("Upload medical PDFs", icon=":material/cloud_upload:", type="primary", key="hero_go_docs"):
                navigate_to("documents")
            if st.button("Open patient intelligence", icon=":material/person_search:", key="hero_go_patient"):
                navigate_to("patient")
            if st.button("Compare reports", icon=":material/compare_arrows:", key="hero_go_compare"):
                navigate_to("conflicts")


# =========================================================
# PAGE 1: EXECUTIVE DASHBOARD
# =========================================================

def dashboard_page(is_demo: bool):
    page_header(
        "Executive dashboard",
        "Unified overview of stored clinical reports, severity distribution, and patient findings.",
    )

    render_welcome_banner(is_demo)

    if is_demo:
        demo_mode_banner()
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            metric_card("Total documents (demo)", "24", "Fictional dataset")
        with c2:
            metric_card("Records reviewed (demo)", "18", "Fictional count")
        with c3:
            metric_card("Open conflicts (demo)", "03", "Fictional alerts")
        with c4:
            metric_card("Reconciliation (demo)", "75%", "Fictional progress")

        patient_banner(
            DEMO_PATIENT["name"],
            DEMO_PATIENT["patient_id"],
            DEMO_PATIENT["age"],
            DEMO_PATIENT["sex"],
            DEMO_PATIENT["department"],
        )

        left, right = st.columns([1.35, 1])
        with left:
            with st.container(border=True):
                section_header("Document processing overview (demo)", "Illustrative fictional counts")
                fig = go.Figure(
                    go.Bar(
                        x=["Admission", "Lab Reports", "Prescriptions", "Discharge"],
                        y=[8, 6, 5, 5],
                        marker=dict(color=["#0F766E", "#1D4ED8", "#0EA5E9", "#475569"]),
                        text=[8, 6, 5, 5],
                        textposition="outside",
                    )
                )
                fig.update_layout(**CHART_LAYOUT, height=300, showlegend=False)
                st.plotly_chart(fig, alt="Illustrative document processing bar chart")

        with right:
            with st.container(border=True):
                section_header("Review distribution (demo)", "Illustrative fictional status")
                fig2 = go.Figure(
                    data=[
                        go.Pie(
                            labels=["Reviewed", "Pending", "Needs Review"],
                            values=[18, 3, 3],
                            hole=0.68,
                            marker=dict(colors=["#0F766E", "#1D4ED8", "#D97706"]),
                            textinfo="label+percent",
                        )
                    ]
                )
                fig2.update_layout(**CHART_LAYOUT, height=300, showlegend=False)
                st.plotly_chart(fig2, alt="Illustrative review status donut chart")
        return

    if not backend_online:
        show_backend_offline_notice(health_resp["error"])
        return

    with st.spinner("Loading dashboard overview from FastAPI..."):
        overview_resp = client.get_dashboard_overview()

    if not overview_resp["ok"]:
        st.error(overview_resp["error"], title="Failed to load dashboard", icon=":material/error:")
        return

    overview = overview_resp["data"]
    cards = overview.get("cards", {})
    sev_dist = overview.get("severity_distribution", {})
    cat_breakdown = overview.get("category_breakdown", {})
    recent_reports = overview.get("recent_reports", [])

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        metric_card("Total patients", cards.get("total_patients", 0), "Stored in SQLite")
    with c2:
        metric_card("Total reports", cards.get("total_reports", 0), "Processed PDF reports")
    with c3:
        metric_card(
            "Attention needed",
            cards.get("attention_needed_reports", 0),
            "High-priority rule flags",
        )
    with c4:
        metric_card(
            "Review recommended",
            cards.get("review_recommended_reports", 0),
            "Moderate rule flags",
        )

    analysis = load_patient_analysis(client, selected_patient_id) if selected_patient_id else None
    if analysis:
        p = analysis["patient"]
        patient_banner(
            p.get("name"),
            p.get("patient_id"),
            p.get("age"),
            p.get("sex"),
            f"{p.get('report_count', 0)} report(s) on file",
            severity=analysis["dashboard"]["cards"].get("overall_severity"),
        )

    left, right = st.columns([1.35, 1])
    with left:
        with st.container(border=True):
            section_header(
                "Flagged findings by clinical category",
                "Rule-based detections across all stored reports",
            )
            if cat_breakdown:
                cats = list(cat_breakdown.keys())
                vals = list(cat_breakdown.values())
                fig = go.Figure(
                    go.Bar(
                        x=cats,
                        y=vals,
                        marker=dict(color="#0F766E"),
                        text=vals,
                        textposition="outside",
                    )
                )
                fig.update_layout(
                    **CHART_LAYOUT,
                    height=310,
                    showlegend=False,
                    xaxis=dict(showgrid=False),
                    yaxis=dict(showgrid=True, gridcolor="#E2E8F0", title="Flag count"),
                )
                st.plotly_chart(fig, alt="Bar chart of flagged findings by clinical category")
            else:
                empty_state("No abnormal category flags recorded yet.", icon=":material/bar_chart:")

    with right:
        with st.container(border=True):
            section_header(
                "Report severity distribution",
                "Rule-based classification across uploaded reports",
            )
            labels = ["Attention Needed", "Review Recommended", "Normal"]
            values = [
                sev_dist.get("attention_needed", 0),
                sev_dist.get("review_recommended", 0),
                sev_dist.get("normal", 0),
            ]
            if sum(values) > 0:
                fig2 = go.Figure(
                    data=[
                        go.Pie(
                            labels=labels,
                            values=values,
                            hole=0.68,
                            marker=dict(colors=["#DC2626", "#D97706", "#0F766E"]),
                            textinfo="label+value",
                        )
                    ]
                )
                fig2.update_layout(**CHART_LAYOUT, height=310, showlegend=False)
                st.plotly_chart(fig2, alt="Donut chart of report severity distribution")
            else:
                empty_state("Upload PDF reports to view severity distribution.", icon=":material/pie_chart:")

    left, right = st.columns([1.2, 1])
    with left:
        section_header("Recent uploaded reports", "Latest records persisted in SQLite")
        if recent_reports:
            for rep in recent_reports[:4]:
                info = rep.get("medical_info", {})
                timeline_item(
                    f"{rep.get('study_date_iso') or info.get('study_date') or 'Undated'} · Patient `{rep.get('patient_id')}`",
                    f"Report #{rep.get('report_id')} — {info.get('study_name') or rep.get('filename')}",
                    rep.get("clinical_summary") or "Processed report stored in database.",
                    severity=rep.get("severity"),
                )
        else:
            show_no_patients_notice()

    with right:
        section_header("Active patient rule flags", "Highlighted observations for the selected patient")
        if analysis:
            flags = analysis.get("rule_based_observations", {}).get("abnormal_flags", [])
            if flags:
                for flag in flags[:4]:
                    conflict_card(
                        f"{flag.get('term', '').title()} ({flag.get('category', 'Clinical')})",
                        flag.get("context", ""),
                        flag.get("severity", "moderate"),
                    )
            else:
                info_card(
                    "No abnormal keywords flagged",
                    "Rule-based checks found no abnormal keywords for this patient.",
                    icon=":material/check_circle:",
                )
        else:
            empty_state("Select a patient in the sidebar or upload a PDF first.", icon=":material/person:")

    if overview.get("clinical_disclaimer"):
        st.caption(overview["clinical_disclaimer"])


# =========================================================
# PAGE 2: PATIENT INTELLIGENCE
# =========================================================

def patient_page(is_demo: bool):
    page_header(
        "Patient intelligence",
        "Centralized patient profile, extracted clinical findings, and plain-language terminology explanations.",
    )

    if is_demo:
        demo_mode_banner()
        patient_banner(
            DEMO_PATIENT["name"],
            DEMO_PATIENT["patient_id"],
            DEMO_PATIENT["age"],
            DEMO_PATIENT["sex"],
            DEMO_PATIENT["department"],
        )
        c1, c2, c3 = st.columns(3)
        with c1:
            info_card("Blood group (demo)", DEMO_PATIENT["blood_group"], icon=":material/bloodtype:")
        with c2:
            info_card("Admission date (demo)", DEMO_PATIENT["admission_date"], icon=":material/event:")
        with c3:
            info_card("Current status (demo)", DEMO_PATIENT["status"], icon=":material/info:")
        return

    if not backend_online:
        show_backend_offline_notice(health_resp["error"])
        return

    if not selected_patient_id:
        show_no_patients_notice()
        return

    analysis = load_patient_analysis(client, selected_patient_id)
    if not analysis:
        return

    p = analysis["patient"]
    latest = analysis.get("latest_report") or {}
    rule_obs = analysis.get("rule_based_observations", {})
    explanations = analysis.get("patient_friendly_explanations", {})
    ai_info = analysis.get("ai_generated_explanations", {})

    patient_banner(
        p.get("name"),
        p.get("patient_id"),
        p.get("age"),
        p.get("sex"),
        f"{p.get('report_count', 0)} report(s) stored",
        severity=rule_obs.get("overall_severity"),
    )

    c1, c2, c3 = st.columns(3)
    with c1:
        info_card("Latest study", latest.get("study_name") or "N/A", icon=":material/radiology:")
    with c2:
        info_card(
            "Latest study date",
            latest.get("study_date_iso") or latest.get("study_date") or "Undated",
            icon=":material/calendar_today:",
        )
    with c3:
        info_card(
            "Rule-based overview",
            rule_obs.get("overview_summary") or "No summary available.",
            icon=":material/rule:",
        )

    if latest:
        section_header(
            "Latest report findings & impression",
            f"Source: Report #{latest.get('report_id', '—')} ({latest.get('filename', 'N/A')})",
        )
        a, b = st.columns(2)
        with a:
            info_card(
                "Extracted findings",
                latest.get("findings") or "No findings section extracted.",
                icon=":material/find_in_page:",
            )
        with b:
            info_card(
                "Extracted impression",
                latest.get("impression") or "No impression section extracted.",
                icon=":material/summarize:",
            )

    section_header("Patient metadata")
    patient_table = pd.DataFrame(
        [
            ["Patient Name", p.get("name") or "Not specified"],
            ["Patient ID", p.get("patient_id")],
            ["Age", p.get("age") or "Not specified"],
            ["Sex", p.get("sex") or "Not specified"],
            ["Total Reports", str(p.get("report_count", 0))],
            ["Overall Severity (Rule-Based)", str(rule_obs.get("overall_severity", "normal")).replace("_", " ")],
        ],
        columns=["Field", "Value"],
    )
    st.dataframe(patient_table, hide_index=True, alt="Patient record metadata")

    section_header(
        "Patient-friendly terminology explanations",
        "Deterministic medical glossary definitions grounded in the original report text",
    )
    with st.container(horizontal=True):
        st.badge("Rule-Based Glossary (ai_generated: false)", icon=":material/rule:", color="blue")
        st.badge(
            "External AI: Enabled" if ai_info.get("enabled") else "External AI: Not Configured",
            icon=":material/neurology:",
            color="green" if ai_info.get("enabled") else "gray",
        )

    if explanations.get("plain_language_summary"):
        st.info(
            explanations["plain_language_summary"],
            title="Rule-based terminology summary",
            icon=":material/menu_book:",
        )

    terms = explanations.get("terminology_explanations", [])
    if terms:
        for item in terms:
            terminology_card(
                item.get("term"),
                item.get("plain_meaning"),
                item.get("category"),
                item.get("status_in_report"),
                item.get("source_context"),
            )
    else:
        empty_state("No glossary medical terms matched in the latest report.", icon=":material/menu_book:")

    st.caption(analysis.get("clinical_disclaimer", ""))


# =========================================================
# PAGE 3: DOCUMENT CENTER
# =========================================================

def documents_page(is_demo: bool):
    page_header(
        "Document center",
        "Upload PDF reports to FastAPI (PyMuPDF + Tesseract OCR + SQLite) and inspect stored records.",
    )

    if is_demo:
        demo_mode_banner()
        section_header("Illustrative demo documents", "Fictional sample document list")
        for doc in DEMO_DOCUMENTS:
            document_card(doc["name"], doc["type"], doc["status"])
        return

    document_upload_section(api_client=client, backend_online=backend_online)

    if not backend_online:
        return

    section_header(
        "Stored backend reports",
        "Reports persisted in SQLite for the active patient",
    )

    if not selected_patient_id:
        show_no_patients_notice()
        return

    with st.spinner("Fetching stored reports from FastAPI..."):
        reports_resp = client.get_patient_reports(selected_patient_id, order="desc")

    if not reports_resp["ok"]:
        st.error(reports_resp["error"], title="Unable to fetch reports", icon=":material/error:")
        return

    reports = reports_resp["data"].get("reports", [])
    if not reports:
        show_no_patients_notice()
        return

    for rep in reports:
        info = rep.get("medical_info", {})
        document_card(
            f"Report #{rep['report_id']} — {rep['filename']}",
            f"{info.get('study_name') or 'Clinical Report'}  •  Date: {rep.get('study_date_iso') or info.get('study_date') or 'Undated'}",
            str(rep.get("severity", "normal")).replace("_", " ").title(),
        )

    selected_id = st.selectbox(
        "Inspect stored report details",
        [r["report_id"] for r in reports],
        format_func=lambda rid: next(
            (f"Report #{r['report_id']} — {r['filename']}" for r in reports if r["report_id"] == rid),
            str(rid),
        ),
        key="inspect_backend_report_id",
    )

    detail_resp = client.get_report(selected_id)
    if detail_resp["ok"]:
        rep_detail = detail_resp["data"].get("report", {})
        rep_info = rep_detail.get("medical_info", {})
        tab_structured, tab_raw = st.tabs(["Structured Extraction", "Raw Extracted Text"])
        with tab_structured:
            if rep_detail.get("clinical_summary"):
                st.info(rep_detail["clinical_summary"], title="Clinical summary", icon=":material/summarize:")
            col_a, col_b = st.columns(2)
            with col_a:
                info_card("Findings", rep_info.get("findings") or "None extracted", icon=":material/find_in_page:")
            with col_b:
                info_card("Impression", rep_info.get("impression") or "None extracted", icon=":material/fact_check:")
        with tab_raw:
            st.text_area(
                "Stored raw extracted text",
                value=rep_detail.get("raw_text", ""),
                height=260,
                disabled=True,
                label_visibility="collapsed",
            )
    else:
        st.error(detail_resp["error"], icon=":material/error:")


# =========================================================
# PAGE 4: CLINICAL TIMELINE
# =========================================================

def timeline_page(is_demo: bool):
    page_header(
        "Clinical timeline",
        "Chronological medical study timeline ordered by parsed study dates.",
    )

    if is_demo:
        demo_mode_banner()
        patient_banner(
            DEMO_PATIENT["name"],
            DEMO_PATIENT["patient_id"],
            DEMO_PATIENT["age"],
            DEMO_PATIENT["sex"],
            DEMO_PATIENT["department"],
        )
        for item in DEMO_TIMELINE:
            timeline_item(item["date"], item["title"], item["description"])
        return

    if not backend_online:
        show_backend_offline_notice(health_resp["error"])
        return

    if not selected_patient_id:
        show_no_patients_notice()
        return

    analysis = load_patient_analysis(client, selected_patient_id)
    if not analysis:
        return

    p = analysis["patient"]
    timeline_data = analysis.get("timeline", {})
    events = timeline_data.get("timeline", [])
    date_range = timeline_data.get("date_range", {})

    patient_banner(
        p.get("name"),
        p.get("patient_id"),
        p.get("age"),
        p.get("sex"),
        f"{p.get('report_count', 0)} report(s)",
        severity=timeline_data.get("overall_severity"),
    )

    c1, c2, c3 = st.columns(3)
    with c1:
        metric_card("Total studies", timeline_data.get("total_reports", 0), "Chronological order")
    with c2:
        metric_card("Earliest study", date_range.get("earliest") or "Undated", "ISO study date")
    with c3:
        metric_card("Latest study", date_range.get("latest") or "Undated", "ISO study date")

    section_header("Chronological study events", timeline_data.get("overview_summary", ""))

    if not events:
        show_no_patients_notice()
        return

    for event in events:
        date_label = event.get("study_date_iso") or event.get("study_date") or "Undated"
        flags = event.get("abnormal_flags", [])
        sev = event.get("severity", "normal")
        with st.container(border=True):
            top_l, top_r = st.columns([4, 1], vertical_alignment="center")
            with top_l:
                st.caption(
                    f":material/event: Step #{event.get('sequence')}  •  {date_label}  •  "
                    f"Report #{event.get('report_id')} ({event.get('filename')})"
                )
                st.markdown(f"**{event.get('study_name') or event.get('filename')}**")
            with top_r:
                st.badge(
                    str(sev).replace("_", " ").title(),
                    color=severity_badge_color(sev),
                )

            if event.get("clinical_summary"):
                st.write(event["clinical_summary"])

            with st.expander("View findings, impression & flagged terms", icon=":material/expand_more:"):
                if flags:
                    st.caption("Flagged terms: " + ", ".join(f"{f['term']} ({f['category']})" for f in flags))
                else:
                    st.caption("No abnormal keywords flagged for this study.")
                col_f, col_i = st.columns(2)
                with col_f:
                    st.markdown("**Findings**")
                    st.write(event.get("findings") or "—")
                with col_i:
                    st.markdown("**Impression**")
                    st.write(event.get("impression") or "—")

    st.caption(analysis.get("clinical_disclaimer", ""))


# =========================================================
# PAGE 5: MEDICATION RECONCILIATION
# =========================================================

def medications_page(is_demo: bool):
    page_header(
        "Medication reconciliation",
        "Review medication mentions and record clinician verification notes.",
    )

    if is_demo:
        demo_mode_banner()
        c1, c2, c3 = st.columns(3)
        with c1:
            metric_card("Medication entries (demo)", "03", "Fictional demo entries")
        with c2:
            metric_card("Consistent (demo)", "01", "Fictional status")
        with c3:
            metric_card("Review required (demo)", "02", "Fictional status")

        med_df = pd.DataFrame(DEMO_MEDICATIONS)
        med_df.columns = ["Medication", "Dosage", "Frequency", "Source", "Review Status"]
        st.dataframe(med_df, hide_index=True, alt="Fictional demo medication table")

        selected = st.selectbox("Inspect fictional medication", [m["name"] for m in DEMO_MEDICATIONS])
        current = next(m for m in DEMO_MEDICATIONS if m["name"] == selected)
        a, b = st.columns(2)
        with a:
            info_card("Medication", current["name"], icon=":material/medication:")
            info_card("Dosage", current["dosage"], icon=":material/science:")
        with b:
            info_card("Frequency", current["frequency"], icon=":material/schedule:")
            info_card("Source", current["source"], icon=":material/description:")
    else:
        if not backend_online:
            show_backend_offline_notice(health_resp["error"])
            return
        if not selected_patient_id:
            show_no_patients_notice()
            return

        st.info(
            "The current FastAPI backend extracts study metadata, findings, and impressions. "
            "Dedicated structured medication extraction is not yet implemented in the backend. "
            "Any explicit dosage patterns (such as mg, mcg, or ml) found in stored report text are listed below for review.",
            title="Structured medication extraction not yet implemented",
            icon=":material/info:",
        )

        with st.spinner("Scanning extracted report text for dosage mentions..."):
            reports_resp = client.get_patient_reports(selected_patient_id, include_pages=True)

        if not reports_resp["ok"]:
            st.error(reports_resp["error"], icon=":material/error:")
            return

        reports = reports_resp["data"].get("reports", [])
        detected_meds = []
        for rep in reports:
            text = rep.get("raw_text") or ""
            for match in MEDICATION_DOSE_PATTERN.finditer(text):
                detected_meds.append({
                    "Candidate Term": match.group(1),
                    "Detected Dose": match.group(2),
                    "Source Report": f"Report #{rep['report_id']} ({rep['filename']})",
                    "Study Date": rep.get("study_date_iso") or "Undated",
                    "Status": "Needs Clinician Verification",
                })

        if detected_meds:
            st.dataframe(
                pd.DataFrame(detected_meds),
                hide_index=True,
                alt="Dosage mentions detected in stored reports",
            )
        else:
            empty_state(
                "No medication dosage patterns (e.g., mg, mcg, ml) were detected in this patient's stored reports.",
                icon=":material/medication:",
            )

    st.warning(
        "CLINIQ AI does not prescribe, recommend, or modify medications. "
        "All medication reconciliation decisions must remain under licensed healthcare professional supervision.",
        title="Clinician supervision required",
        icon=":material/health_and_safety:",
    )

    notes = st.text_area(
        "Clinician reviewer notes (current session only)",
        placeholder="Enter verification notes for a qualified reviewer...",
        height=100,
        key="medication_review_notes",
    )
    if st.button("Save session review notes", icon=":material/save:", key="save_medication_notes"):
        if notes.strip():
            st.session_state["saved_medication_note"] = notes.strip()
            st.success("Session review note saved (not persisted to medical database).")
        else:
            st.warning("Enter review notes before saving.")

    if st.session_state.get("saved_medication_note"):
        st.caption(f"Last saved session note: {st.session_state['saved_medication_note']}")


# =========================================================
# PAGE 6: CONFLICT INTELLIGENCE
# =========================================================

def conflicts_page(is_demo: bool):
    page_header(
        "Conflict & comparison intelligence",
        "Compare previous vs. latest reports and review conservative rule-based clinical flags.",
    )

    if is_demo:
        demo_mode_banner()
        c1, c2, c3 = st.columns(3)
        with c1:
            metric_card("High priority (demo)", "01", "Fictional alert")
        with c2:
            metric_card("Medium priority (demo)", "01", "Fictional alert")
        with c3:
            metric_card("Low priority (demo)", "01", "Fictional alert")

        for item in DEMO_CONFLICTS:
            conflict_card(item["title"], item["description"], item["severity"])
        return

    if not backend_online:
        show_backend_offline_notice(health_resp["error"])
        return
    if not selected_patient_id:
        show_no_patients_notice()
        return

    analysis = load_patient_analysis(client, selected_patient_id)
    if not analysis:
        return

    comparison = analysis.get("comparison", {})
    counts = comparison.get("rule_based_observations", {}).get("counts", {})
    flags = analysis.get("rule_based_observations", {}).get("abnormal_flags", [])
    conflict_det = analysis.get("conflict_detection") or comparison.get("conflict_detection") or {}
    missing_info = conflict_det.get("missing_information", {})
    contradictions = conflict_det.get("potential_contradictions", [])
    med_changes = conflict_det.get("clinical_changes", {}).get("medication_changes", [])
    lab_changes = conflict_det.get("clinical_changes", {}).get("lab_changes", [])

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        metric_card("Newly appearing", counts.get("newly_appearing", 0), "Vs. previous report")
    with c2:
        metric_card("Improving", counts.get("improving", 0), "Explicit improvement/resolved")
    with c3:
        metric_card("Worsening", counts.get("worsening", 0), "Explicit progression/escalation")
    with c4:
        metric_card("Unchanged", counts.get("unchanged", 0), "Stable across reports")

    section_header(
        "Record completeness & potential contradictions",
        "Separates missing fields, potential opposing assertions on comparable studies, and clinical changes",
    )

    comp_cols = st.columns(3)
    with comp_cols[0]:
        metric_card(
            "Incomplete records",
            missing_info.get("incomplete_count", 0),
            f"Of {missing_info.get('total_checked', 0)} checked",
        )
    with comp_cols[1]:
        metric_card(
            "Potential contradictions",
            len(contradictions),
            "Opposing same-date findings",
        )
    with comp_cols[2]:
        metric_card(
            "Med / lab changes",
            len(med_changes) + len(lab_changes),
            "Require clinician review",
        )

    incomplete_reports = missing_info.get("incomplete_reports", [])
    if incomplete_reports:
        for inc in incomplete_reports:
            conflict_card(
                f"Missing Information — Report #{inc.get('report_id')} ({inc.get('filename')})",
                f"Study date: {inc.get('study_date')} | Missing fields: {', '.join(inc.get('missing_fields', []))}",
                "moderate",
            )
    else:
        st.badge("All checked records include diagnosis/findings, date, and source", icon=":material/check_circle:", color="green")

    comparability = conflict_det.get("comparability", {})
    if comparability and not comparability.get("comparable", True):
        st.caption(f"Comparability check: {comparability.get('reason')}")

    if contradictions:
        for item in contradictions:
            prev_ev = item.get("previous_report", {})
            lat_ev = item.get("latest_report", {})
            conflict_card(
                f"Potential Contradiction: {str(item.get('finding', '')).title()} (Clinician Review Needed)",
                (
                    f"{item.get('message')} | "
                    f"Report #{prev_ev.get('report_id')} ({prev_ev.get('study_date')}, {prev_ev.get('filename')}): \"{prev_ev.get('evidence')}\" | "
                    f"Report #{lat_ev.get('report_id')} ({lat_ev.get('study_date')}, {lat_ev.get('filename')}): \"{lat_ev.get('evidence')}\""
                ),
                "high",
            )

    if med_changes:
        for mc in med_changes:
            prev_ev = mc.get("previous_report", {})
            lat_ev = mc.get("latest_report", {})
            conflict_card(
                f"Medication Change Requiring Review: {str(mc.get('medication', '')).title()}",
                (
                    f"{mc.get('old_status')} → {mc.get('new_status')} | "
                    f"Report #{prev_ev.get('report_id')} ({prev_ev.get('study_date')}) vs. "
                    f"Report #{lat_ev.get('report_id')} ({lat_ev.get('study_date')}). Clinician verification required."
                ),
                "moderate",
            )

    if lab_changes:
        for lc in lab_changes:
            prev_ev = lc.get("previous_report", {})
            lat_ev = lc.get("latest_report", {})
            conflict_card(
                f"Lab Value Change Requiring Review: {lc.get('test_name')}",
                (
                    f"{lc.get('previous_value')} {lc.get('unit')} → {lc.get('latest_value')} {lc.get('unit')} | "
                    f"Report #{prev_ev.get('report_id')} ({prev_ev.get('study_date')}) vs. "
                    f"Report #{lat_ev.get('report_id')} ({lat_ev.get('study_date')})."
                ),
                "moderate",
            )

    section_header(
        "Previous vs. latest report comparison",
        "Conservative rule-based comparison (reports only findings backed by extracted text)",
    )

    if not comparison.get("comparison_available"):
        st.info(
            comparison.get("reason", "Upload at least two distinct reports for this patient to compare changes."),
            title="Comparison unavailable",
            icon=":material/info:",
        )
    else:
        prev_r = comparison["previous_report"]
        latest_r = comparison["latest_report"]
        compat = comparison.get("study_compatibility", {})

        a, b = st.columns(2)
        with a:
            with st.container(border=True):
                st.badge("Previous record", color="gray")
                st.markdown(
                    f"**Report #{prev_r.get('report_id')} — {prev_r.get('study_name') or prev_r.get('filename')}**"
                )
                st.caption(
                    f"Study date: {prev_r.get('study_date_iso') or prev_r.get('study_date') or 'Undated'}  •  "
                    f"File: {prev_r.get('filename')}"
                )
                st.badge(
                    str(prev_r.get("severity", "normal")).replace("_", " ").title(),
                    color=severity_badge_color(prev_r.get("severity")),
                )

        with b:
            with st.container(border=True):
                st.badge("Latest record", color="blue")
                st.markdown(
                    f"**Report #{latest_r.get('report_id')} — {latest_r.get('study_name') or latest_r.get('filename')}**"
                )
                st.caption(
                    f"Study date: {latest_r.get('study_date_iso') or latest_r.get('study_date') or 'Undated'}  •  "
                    f"File: {latest_r.get('filename')}"
                )
                st.badge(
                    str(latest_r.get("severity", "normal")).replace("_", " ").title(),
                    color=severity_badge_color(latest_r.get("severity")),
                )

        if compat.get("identical_content") or compat.get("same_study_date") or not compat.get("compatible_study_type", True):
            st.warning(
                compat.get("note"),
                title="Comparison context notice",
                icon=":material/info:",
            )

        st.info(
            comparison["rule_based_observations"]["summary"],
            title="Rule-based comparison summary",
            icon=":material/compare_arrows:",
        )

        changes = comparison.get("changes", {})
        bucket_specs = [
            ("worsening", "Worsening findings", "high", "red"),
            ("newly_appearing", "Newly appearing findings", "moderate", "orange"),
            ("unchanged", "Unchanged / persistent findings", "low", "blue"),
            ("improving", "Improving / resolved findings", "low", "green"),
            ("not_mentioned_in_latest", "Not mentioned in latest report", "low", "gray"),
        ]
        for bucket_key, heading, tone, badge_color in bucket_specs:
            items = changes.get(bucket_key, [])
            if items:
                st.markdown(f"**{heading}** :{badge_color}-badge[{len(items)}]")
                for item in items:
                    detail = item.get("evidence_latest") or item.get("note") or item.get("evidence_previous") or ""
                    conflict_card(
                        f"{item.get('finding', '').title()} ({item.get('category', 'Clinical')})",
                        detail,
                        tone,
                    )

    section_header("Rule-based abnormal findings across history", f"{len(flags)} flag(s) detected")
    if flags:
        for flag in flags:
            conflict_card(
                f"{flag.get('term', '').title()} — {flag.get('study_name') or 'Study'} ({flag.get('study_date') or 'Undated'})",
                f"Category: {flag.get('category')} | Evidence: {flag.get('context')}",
                flag.get("severity", "moderate"),
            )
    else:
        info_card(
            "No abnormal flags",
            "No abnormal keywords were flagged in this patient's reports.",
            icon=":material/check_circle:",
        )

    comments = st.text_area(
        "Clinician conflict review notes (session only)",
        placeholder="Add verification comments for clinician handoff...",
        key="conflict_comments",
    )
    if st.button("Save conflict review note", icon=":material/save:", key="submit_conflict_review"):
        if comments.strip():
            st.session_state["saved_conflict_note"] = comments.strip()
            st.success("Session review note saved (not stored in medical database).")
        else:
            st.warning("Enter review comments before saving.")

    st.caption(analysis.get("clinical_disclaimer", ""))


# =========================================================
# PAGE 7: AI AND RULE-BASED RECONSTRUCTION
# =========================================================

def reconstruction_page(is_demo: bool):
    page_header(
        "AI & rule-based reconstruction",
        "Transparent separation between deterministic clinical rules and external AI capabilities.",
    )

    if is_demo:
        demo_mode_banner()

    stages = [
        ("01", "Document ingestion", "PDF upload & PyMuPDF/OCR", ":material/upload_file:"),
        ("02", "Clinical extraction", "Metadata, findings & impression", ":material/fact_check:"),
        ("03", "Timeline & compare", "Date sorting & progression", ":material/timeline:"),
        ("04", "Rule-based flags", "Negation-aware terminology", ":material/rule:"),
        ("05", "Clinician review", "Human verification required", ":material/verified_user:"),
    ]
    cols = st.columns(5)
    for col, (num, title, desc, icon) in zip(cols, stages):
        with col:
            with st.container(border=True, height="stretch"):
                st.caption(f"STEP {num}")
                st.markdown(f"**{icon} {title}**")
                st.caption(desc)

    if is_demo:
        empty_state(
            "Switch to Live FastAPI Backend in the sidebar to reconstruct a stored patient's clinical record.",
            icon=":material/neurology:",
        )
        return

    if not backend_online:
        show_backend_offline_notice(health_resp["error"])
        return
    if not selected_patient_id:
        show_no_patients_notice()
        return

    analysis = load_patient_analysis(client, selected_patient_id)
    if not analysis:
        return

    rule_obs = analysis.get("rule_based_observations", {})
    ai_info = analysis.get("ai_generated_explanations", {})
    explanations = analysis.get("patient_friendly_explanations", {})

    left, right = st.columns(2)
    with left:
        with st.container(border=True, height="stretch"):
            st.badge("Rule-Based Engine Active (ai_generated: false)", icon=":material/rule:", color="green")
            st.subheader("Rule-based reconstruction")
            st.markdown("**Timeline overview**")
            st.write(rule_obs.get("overview_summary") or "No overview available.")
            st.markdown("**Plain-language terminology summary**")
            st.write(explanations.get("plain_language_summary") or "N/A")

    with right:
        with st.container(border=True, height="stretch"):
            ai_enabled = bool(ai_info.get("enabled"))
            st.badge(
                "AI Enabled" if ai_enabled else "External AI Not Configured",
                icon=":material/neurology:",
                color="blue" if ai_enabled else "orange",
            )
            st.subheader("AI-generated explanation layer")
            st.write(
                ai_info.get("note")
                or "No paid/external AI API is configured. All displayed clinical summaries and comparisons are rule-based."
            )

    section_header(
        "Search patient clinical history",
        "Search across this patient's stored report text using exact keyword matching",
    )

    with st.container(horizontal=True, vertical_alignment="bottom"):
        query = st.text_input(
            "Clinical keyword",
            placeholder="Example: edema, effusion, consolidation, fracture...",
            key="reconstruction_query",
        )
        search_clicked = st.button(
            "Search stored reports",
            type="primary",
            icon=":material/search:",
            key="reconstruction_search_btn",
        )

    if search_clicked:
        if not query.strip():
            st.warning("Enter a clinical keyword to search.")
        else:
            with st.spinner("Searching stored reports..."):
                reports_resp = client.get_patient_reports(selected_patient_id, include_pages=True)
            if not reports_resp["ok"]:
                st.error(reports_resp["error"], icon=":material/error:")
            else:
                matches_found = 0
                needle = query.strip().lower()
                for rep in reports_resp["data"].get("reports", []):
                    raw = rep.get("raw_text", "")
                    matching_lines = [
                        line.strip()
                        for line in raw.splitlines()
                        if needle in line.lower() and line.strip()
                    ]
                    if matching_lines:
                        matches_found += 1
                        with st.container(border=True):
                            st.markdown(
                                f"**:material/description: Report #{rep['report_id']} "
                                f"({rep.get('study_date_iso') or rep['filename']})**"
                            )
                            for line in matching_lines[:5]:
                                st.write(f"• {line}")
                if matches_found == 0:
                    st.info(f"No lines containing '{query.strip()}' were found in this patient's reports.")

    st.warning(
        analysis.get(
            "clinical_disclaimer",
            "CLINIQ AI is a clinical support prototype, not a diagnostic system.",
        ),
        title="Medical responsibility notice",
        icon=":material/health_and_safety:",
    )


# =========================================================
# MAIN PAGE ROUTER
# =========================================================

is_demo = st.session_state.data_source_mode == "Fictional Demo Dataset"
current_page = st.session_state.active_page

if current_page == "dashboard":
    dashboard_page(is_demo)
elif current_page == "patient":
    patient_page(is_demo)
elif current_page == "documents":
    documents_page(is_demo)
elif current_page == "timeline":
    timeline_page(is_demo)
elif current_page == "medications":
    medications_page(is_demo)
elif current_page == "conflicts":
    conflicts_page(is_demo)
elif current_page == "reconstruction":
    reconstruction_page(is_demo)


# =========================================================
# FOOTER
# =========================================================

st.space("medium")
app_footer()
