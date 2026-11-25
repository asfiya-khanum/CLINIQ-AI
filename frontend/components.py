import html
import streamlit as st


def safe(value):
    if value is None:
        return "—"
    return html.escape(str(value))


def load_custom_css():
    """
    Theme colors, typography, radii, and sidebar contrast are configured
    natively in .streamlit/config.toml. Keep this hook for backward compatibility.
    """
    return None


def page_header(title, subtitle=""):
    st.title(str(title))
    if subtitle:
        st.caption(str(subtitle))


def section_header(title, subtitle=""):
    st.subheader(str(title))
    if subtitle:
        st.caption(str(subtitle))


def metric_card(label, value, caption="", delta=None):
    st.metric(
        label=str(label),
        value=value,
        delta=delta if delta is not None else (str(caption) if caption else None),
        delta_color="off" if delta is None else "normal",
        border=True,
        height="stretch",
    )


def severity_to_badge_type(severity: str | None) -> str:
    sev = (severity or "").lower()
    if sev in {"attention_needed", "high", "danger"}:
        return "danger"
    if sev in {"review_recommended", "moderate", "medium", "warning"}:
        return "warning"
    if sev in {"normal", "success", "low"}:
        return "success"
    return "info"


def severity_badge_color(severity: str | None) -> str:
    mapping = {
        "danger": "red",
        "warning": "orange",
        "success": "green",
        "info": "blue",
    }
    return mapping.get(severity_to_badge_type(severity), "blue")


def status_badge(label, status="info", icon=None):
    color_map = {
        "success": "green",
        "warning": "orange",
        "danger": "red",
        "info": "blue",
    }
    st.badge(
        str(label),
        icon=icon,
        color=color_map.get(status, "blue"),
    )


def patient_banner(
    name,
    patient_id,
    age,
    gender,
    department="Clinical Intelligence",
    severity=None,
):
    with st.container(border=True):
        top_left, top_right = st.columns([3, 1], vertical_alignment="center")
        with top_left:
            st.markdown(f"### :material/person: {name or 'Unnamed Patient'}")
            st.caption(
                f"Patient ID: `{patient_id or '—'}`  •  "
                f"Age: {age or '—'}  •  "
                f"Sex: {gender or '—'}  •  "
                f"{department or 'Clinical Intelligence'}"
            )
        with top_right:
            if severity:
                label = str(severity).replace("_", " ").title()
                st.badge(
                    label,
                    icon=":material/clinical_notes:",
                    color=severity_badge_color(severity),
                )


def info_card(title, description, icon=":material/article:"):
    with st.container(border=True):
        st.markdown(f"**{icon} {title}**")
        st.write(description if description not in (None, "") else "—")


def conflict_card(title, description, severity="High"):
    badge_color = severity_badge_color(severity)
    sev_label = str(severity or "info").replace("_", " ").title()
    with st.container(border=True):
        col_title, col_badge = st.columns([4, 1], vertical_alignment="center")
        with col_title:
            st.markdown(f"**:material/warning: {title}**")
        with col_badge:
            st.badge(sev_label, color=badge_color)
        st.write(description if description else "—")


def timeline_item(date, title, description, severity=None):
    with st.container(border=True):
        head_left, head_right = st.columns([4, 1], vertical_alignment="center")
        with head_left:
            st.caption(f":material/event: {date}")
            st.markdown(f"**{title}**")
        with head_right:
            if severity:
                st.badge(
                    str(severity).replace("_", " ").title(),
                    color=severity_badge_color(severity),
                )
        if description:
            st.write(description)


def document_card(name, document_type, status="Uploaded"):
    with st.container(border=True):
        col_left, col_right = st.columns([4, 1], vertical_alignment="center")
        with col_left:
            st.markdown(f"**:material/description: {name}**")
            st.caption(str(document_type))
        with col_right:
            sev_color = "green" if "normal" in str(status).lower() or "processed" in str(status).lower() else "blue"
            if "attention" in str(status).lower() or "ocr" in str(status).lower():
                sev_color = "red" if "attention" in str(status).lower() else "orange"
            elif "review" in str(status).lower():
                sev_color = "orange"
            st.badge(str(status), color=sev_color)


def terminology_card(term, plain_meaning, category, status_in_report, source_context):
    is_normal = status_in_report == "negated_or_normal"
    status_label = "Absent / normal in report" if is_normal else "Noted in report"
    badge_color = "green" if is_normal else "blue"

    with st.expander(f"{str(term).title()}  •  {category} ({status_label})", icon=":material/menu_book:"):
        st.badge(f"{category} · {status_label}", color=badge_color)
        st.markdown(plain_meaning)
        st.caption(f'Original report context: "{source_context}"')


def demo_mode_banner():
    st.warning(
        "You are viewing illustrative fictional demo records. Switch to Live FastAPI Backend in the sidebar to work with real uploaded PDFs and SQLite records.",
        title="Fictional Demo Dataset Active",
        icon=":material/science:",
    )


def empty_state(message, icon=":material/folder_open:"):
    with st.container(border=True):
        st.markdown(f"**{icon} Nothing to display yet**")
        st.caption(str(message))


def app_footer():
    st.caption(
        "CLINIQ AI · Agentic Clinical Intelligence for Patient Reconstruction · "
        "Informational support only — not a diagnostic tool. Qualified healthcare professional supervision is required."
    )
