from datetime import datetime
import hashlib
import io
from pathlib import Path

from docx import Document
import fitz
import streamlit as st


# ============================================================
# CLINIQ-AI | DOCUMENT INTELLIGENCE CENTER
# ============================================================

MAX_FILE_SIZE = 20 * 1024 * 1024
SUPPORTED_EXTENSIONS = ["pdf", "docx", "txt"]

SESSION_KEY = "cliniq_processed_documents"
HASH_KEY = "cliniq_document_hashes"
UPLOAD_RESULTS_KEY = "cliniq_last_upload_results"
PENDING_PATIENT_KEY = "pending_selected_patient_id"


def load_document_css():
    """Preserved for backward compatibility; theme styling lives in .streamlit/config.toml."""
    return None


# ============================================================
# SESSION MANAGEMENT
# ============================================================

def initialize_document_session():
    if SESSION_KEY not in st.session_state:
        st.session_state[SESSION_KEY] = []
    if HASH_KEY not in st.session_state:
        st.session_state[HASH_KEY] = set()
    if UPLOAD_RESULTS_KEY not in st.session_state:
        st.session_state[UPLOAD_RESULTS_KEY] = []


def get_processed_documents():
    initialize_document_session()
    return st.session_state[SESSION_KEY]


def clear_document_session():
    st.session_state[SESSION_KEY] = []
    st.session_state[HASH_KEY] = set()
    st.session_state[UPLOAD_RESULTS_KEY] = []


# ============================================================
# FILE UTILITIES & LOCAL TEXT EXTRACTION
# ============================================================

def format_file_size(size):
    if size < 1024:
        return f"{size} B"
    if size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    return f"{size / (1024 * 1024):.2f} MB"


def generate_file_hash(file_bytes):
    return hashlib.sha256(file_bytes).hexdigest()


def _get_extension(filename: str) -> str:
    return Path(filename).suffix.lstrip(".").lower()


def validate_file(uploaded_file):
    extension = _get_extension(uploaded_file.name)
    if extension not in SUPPORTED_EXTENSIONS:
        return False, "Unsupported document format."
    if uploaded_file.size == 0:
        return False, "The selected document is empty."
    if uploaded_file.size > MAX_FILE_SIZE:
        return False, "Maximum file size is 20 MB."
    return True, "Validation successful."


def extract_pdf_text(file_bytes):
    pdf = fitz.open(stream=file_bytes, filetype="pdf")
    pages = []
    try:
        for number, page in enumerate(pdf):
            text = page.get_text("text")
            if text.strip():
                pages.append(f"--- PAGE {number + 1} ---\n{text}")
    finally:
        pdf.close()
    return "\n\n".join(pages).strip()


def extract_docx_text(file_bytes):
    document = Document(io.BytesIO(file_bytes))
    content = [p.text for p in document.paragraphs if p.text.strip()]
    for table in document.tables:
        for row in table.rows:
            content.append(" | ".join(cell.text.strip() for cell in row.cells))
    return "\n".join(content).strip()


def extract_txt_text(file_bytes):
    return file_bytes.decode("utf-8-sig", errors="replace").strip()


def process_document(uploaded_file):
    """Process a document locally in Streamlit session (for DOCX/TXT or offline preview)."""
    initialize_document_session()
    try:
        file_bytes = uploaded_file.getvalue()
        valid, message = validate_file(uploaded_file)
        if not valid:
            return {"success": False, "message": message}

        file_hash = generate_file_hash(file_bytes)
        if file_hash in st.session_state[HASH_KEY]:
            return {"success": False, "message": "Duplicate document in current session."}

        extension = _get_extension(uploaded_file.name)
        if extension == "pdf":
            extracted_text = extract_pdf_text(file_bytes)
        elif extension == "docx":
            extracted_text = extract_docx_text(file_bytes)
        else:
            extracted_text = extract_txt_text(file_bytes)

        ocr_required = extension == "pdf" and not extracted_text
        if not extracted_text and not ocr_required:
            return {"success": False, "message": "No readable text found."}

        status = "OCR Required" if ocr_required else "Processed"
        document = {
            "name": uploaded_file.name,
            "type": extension.upper(),
            "size": uploaded_file.size,
            "size_display": format_file_size(uploaded_file.size),
            "status": status,
            "text": extracted_text,
            "hash": file_hash,
            "uploaded_at": datetime.now().strftime("%d %b %Y | %I:%M %p"),
            "ocr_required": ocr_required,
            "message": (
                "Scanned PDF detected; upload to FastAPI backend for Tesseract OCR."
                if ocr_required
                else "Local text extraction completed."
            ),
        }
        st.session_state[SESSION_KEY].append(document)
        st.session_state[HASH_KEY].add(file_hash)
        return {"success": True, "message": document["message"], "document": document}
    except Exception as error:
        return {"success": False, "message": str(error)}


def metric_box(label, value, icon=""):
    st.metric(
        label=f"{icon} {label}".strip(),
        value=value,
        border=True,
        height="stretch",
    )


def display_document_card(document):
    with st.container(border=True):
        col_left, col_right = st.columns([4, 1], vertical_alignment="center")
        with col_left:
            st.markdown(f"**:material/description: {document['name']}**")
            st.caption(
                f"{document['type']}  •  {document['size_display']}  •  {document['uploaded_at']}"
            )
        with col_right:
            is_ok = document["status"] == "Processed"
            st.badge(
                "Processed" if is_ok else "OCR required",
                color="green" if is_ok else "orange",
            )


# ============================================================
# DOCUMENT CENTER UPLOAD WORKSPACE
# ============================================================

def _render_backend_upload_results(results: list[dict]):
    if not results:
        return
    st.subheader("Latest upload results", icon=":material/task_alt:")
    for item in results:
        filename = item.get("filename", "Unknown file")
        if item.get("status") == "success":
            st.success(
                f"{filename} saved as Report #{item.get('report_id')} "
                f"(Patient ID: {item.get('patient_id')} via {item.get('patient_id_source', 'extracted')}, "
                f"Severity: {str(item.get('severity', 'normal')).replace('_', ' ')})",
                icon=":material/check_circle:",
            )
            if item.get("clinical_summary"):
                st.caption(item["clinical_summary"])
        else:
            st.error(f"{filename}: {item.get('message', 'Upload failed.')}", icon=":material/error:")


def document_upload_section(api_client=None, backend_online: bool = False):
    initialize_document_session()

    with st.container(border=True):
        st.subheader("Upload clinical documents", icon=":material/cloud_upload:")
        st.caption(
            "Drag and drop one or more PDF reports to extract text (PyMuPDF + Tesseract OCR), "
            "save records to SQLite, and generate clinical intelligence. DOCX and TXT files are previewed locally."
        )

        fallback_patient_id = st.text_input(
            "Optional fallback patient ID",
            value="",
            placeholder="Leave blank to extract Patient ID automatically from each PDF",
            help="Only used if a PDF does not contain an explicit Patient ID, MRN, or UHID.",
            key="upload_fallback_patient_id",
        )

        uploaded_files = st.file_uploader(
            "Select or drag clinical files (PDF, DOCX, TXT — max 20 MB each)",
            type=SUPPORTED_EXTENSIONS,
            accept_multiple_files=True,
            key="cliniq_premium_uploader",
        )

        if uploaded_files:
            st.caption(f"{len(uploaded_files)} file(s) ready for upload.")

            if st.button(
                "Process and upload documents",
                type="primary",
                icon=":material/upload:",
                width="stretch",
                key="process_upload_btn",
            ):
                pdf_batch = []
                local_files = []

                for f in uploaded_files:
                    valid, msg = validate_file(f)
                    if not valid:
                        st.error(f"{f.name}: {msg}")
                        continue
                    if _get_extension(f.name) == "pdf" and api_client is not None and backend_online:
                        pdf_batch.append((f.name, f.getvalue()))
                    else:
                        local_files.append(f)

                upload_feedback = []

                if pdf_batch:
                    with st.spinner("Uploading PDFs to FastAPI (PyMuPDF + OCR + SQLite)..."):
                        resp = api_client.upload_pdfs(pdf_batch, patient_id=fallback_patient_id or None)
                    if resp["ok"]:
                        upload_feedback = resp["data"].get("files", [])
                        st.session_state[UPLOAD_RESULTS_KEY] = upload_feedback
                        for item in upload_feedback:
                            if item.get("status") == "success" and item.get("patient_id"):
                                st.session_state[PENDING_PATIENT_KEY] = item["patient_id"]
                                break
                    else:
                        st.error(resp["error"], icon=":material/error:")

                if local_files:
                    if any(_get_extension(f.name) == "pdf" for f in local_files) and not backend_online:
                        st.warning(
                            "FastAPI backend is offline, so PDFs were only previewed locally "
                            "and were not saved to SQLite or processed with OCR.",
                            title="Backend offline",
                            icon=":material/cloud_off:",
                        )
                    for f in local_files:
                        res = process_document(f)
                        if res["success"]:
                            st.success(f"{f.name}: {res['message']}")
                        else:
                            st.warning(f"{f.name}: {res['message']}")

                if upload_feedback:
                    st.rerun()

    _render_backend_upload_results(st.session_state.get(UPLOAD_RESULTS_KEY, []))

    documents = get_processed_documents()
    if documents:
        st.subheader("Local session previews", icon=":material/folder:")
        total = len(documents)
        processed = sum(doc["status"] == "Processed" for doc in documents)
        ocr = sum(doc["status"] == "OCR Required" for doc in documents)
        total_size = sum(doc["size"] for doc in documents)

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            metric_box("Session files", total)
        with col2:
            metric_box("Extracted", processed)
        with col3:
            metric_box("OCR needed", ocr)
        with col4:
            metric_box("Session size", format_file_size(total_size))

        for document in reversed(documents):
            display_document_card(document)

        readable_documents = [doc for doc in documents if doc["text"].strip()]
        if readable_documents:
            selected_name = st.selectbox(
                "Select local session document to preview",
                [doc["name"] for doc in readable_documents],
                key="cliniq_preview_select",
            )
            selected = next(doc for doc in readable_documents if doc["name"] == selected_name)
            st.text_area(
                "Extracted content",
                value=selected["text"],
                height=240,
                disabled=True,
                label_visibility="collapsed",
            )

        if st.button(
            "Clear local session previews",
            type="secondary",
            icon=":material/delete_sweep:",
            key="clear_local_docs_btn",
        ):
            clear_document_session()
            st.rerun()
