import streamlit as st
import fitz  # PyMuPDF
import re

# ---------- PAGE SETUP ----------
st.set_page_config(page_title="MediSync - Hospital Intelligence", layout="wide", page_icon="🏥")

# ---------- CUSTOM CSS - PRO LOOK ----------
st.markdown("""
<style>
.main { background-color: #f8f9fa; }
.big-title { font-size: 32px; font-weight: 800; color: #0f2a44; margin-bottom: 0px; }
.sub-title { color: #5a6c7d; font-size: 15px; margin-top: 0px; }
.card { background: white; padding: 16px; border-radius: 12px; box-shadow: 0 2px 10px rgba(0,0,0,0.06); border-left: 4px solid #0f766e; }
.conflict-card { background: #fff7ed; padding: 18px; border-radius: 12px; border: 1px solid #fed7aa; }
.safe-card { background: #f0fdf4; padding: 18px; border-radius: 12px; border: 1px solid #bbf7d0; }
.info-card { background: #eff6ff; padding: 18px; border-radius: 12px; border: 1px solid #bfdbfe; }
</style>
""", unsafe_allow_html=True)

st.markdown('<p class="big-title">🏥 MediSync - Hospital Patient Intelligence</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">Compare Previous vs New Report • Detect Drug Conflicts • Generate Doctor Report</p>', unsafe_allow_html=True)

# ---------- TOP BAR: DOCTORS + DUTY ----------
col_d1, col_d2, col_d3 = st.columns([2, 2, 1])
with col_d1:
    doctors_list = ["Dr. Rivera", "Dr. Sharma", "Dr. Khan", "Dr. Patel", "Dr. Ayesha", "Dr. Singh"]
    selected = st.multiselect("Doctors on Duty", doctors_list, default=["Dr. Rivera"])
    new_doc = st.text_input("Add New Doctor", placeholder="e.g. Dr. Verma")
    if new_doc and new_doc not in selected:
        selected = selected + [new_doc]
with col_d2:
    duty = st.selectbox("Duty Time", ["Morning 8 AM - 2 PM", "Evening 2 PM - 8 PM", "Night 8 PM - 8 AM", "Full Day 8 AM - 8 PM"])
with col_d3:
    st.markdown("**Status**")
    st.markdown("🟢 **Live**")

names = ", ".join(selected) if selected else "Doctor"
st.success(f"Good morning, {names}  |  Duty: {duty}")

# ---------- DASHBOARD ----------
m1, m2, m3, m4 = st.columns(4)
m1.metric("Total Patients Today", "24", "+3")
m2.metric("Critical Cases", "3", "-1")
m3.metric("Stable Cases", "18", "+2")
m4.metric("Discharged", "3", "+1")

# ---------- PATIENT DETAILS ----------
st.divider()
st.markdown("### 🧑 Patient Details")
p1, p2, p3, p4 = st.columns(4)
patient_name = p1.text_input("Patient Name", "John Doe")
age = p2.number_input("Age", 0, 120, 45)
gender = p3.selectbox("Gender", ["Male", "Female", "Other"])
patient_id = p4.text_input("Patient ID", "P-001")

# ---------- DATA LISTS ----------
DIAGNOSIS_LIST = ["Hypertension", "Diabetes Type 2", "Diabetes Type 1", "Heart Disease", "Asthma", "COPD", "Kidney Disease", "Liver Disease", "Thyroid", "Anemia", "Arthritis", "Cancer", "Migraine", "Pneumonia", "COVID-19", "Other"]
MEDICINE_LIST = ["Warfarin", "Aspirin", "Metformin", "Amlodipine", "Insulin", "Paracetamol", "Atorvastatin", "Omeprazole", "Clopidogrel", "Ibuprofen"]
STATUS_LIST = ["Stable", "Critical", "Improved", "Worsened"]

# Drug Interaction Knowledge Base
INTERACTIONS = {
    ("Warfarin", "Aspirin"): ("HIGH RISK - Bleeding", "Both thin the blood. Together bleeding risk increases 2x-3x. Risk of nose bleeding, bleeding gums, stomach internal bleeding."),
    ("Warfarin", "Ibuprofen"): ("HIGH RISK - Bleeding", "Ibuprofen increases Warfarin effect and causes stomach bleeding."),
    ("Warfarin", "Clopidogrel"): ("HIGH RISK - Bleeding", "Dual blood thinner combination. Very high bleeding risk."),
    ("Aspirin", "Ibuprofen"): ("MEDIUM RISK - Stomach Ulcer", "Both damage stomach lining. Risk of ulcer and stomach bleeding."),
    ("Metformin", "Insulin"): ("MEDIUM RISK - Low Sugar", "Both lower blood sugar. Risk of hypoglycemia - dizziness, fainting."),
}

def get_interaction(m1, m2):
    if m1 == m2:
        return None
    key = (m1, m2) if (m1, m2) in INTERACTIONS else (m2, m1) if (m2, m1) in INTERACTIONS else None
    if key:
        return INTERACTIONS[key]
    return None

def extract_text(uploaded_file):
    if uploaded_file is None:
        return ""
    try:
        uploaded_file.seek(0)
        data = uploaded_file.read()
        doc = fitz.open(stream=data, filetype="pdf")
        text = ""
        for page in doc:
            text += page.get_text() + "\n"
        doc.close()
        return text.strip()
    except Exception as e:
        return f"Could not read PDF: {e}"

def find_keywords(text, keywords):
    found = []
    low = text.lower()
    for k in keywords:
        if k.lower() in low:
            # find line containing keyword
            for line in text.split("\n"):
                if k.lower() in line.lower() and line.strip():
                    found.append(line.strip())
                    break
    return found

# ---------- COMPARISON ----------
st.divider()
st.markdown("### 📊 Compare Previous vs New Report")
left, right = st.columns(2)

with left:
    st.markdown("#### 📄 Previous Record")
    prev_diag = st.selectbox("Previous Diagnosis", DIAGNOSIS_LIST, key="prev_diag")
    prev_med = st.selectbox("Previous Medicine", MEDICINE_LIST, key="prev_med")
    prev_dose = st.text_input("Previous Dose", "5 mg - Once Daily", key="prev_dose")
    prev_status = st.selectbox("Previous Status", STATUS_LIST, key="prev_status")
    prev_file = st.file_uploader("Upload Previous Report (PDF)", type=["pdf"], key="prev_file")

with right:
    st.markdown("#### 📄 New Record")
    new_diag = st.selectbox("New Diagnosis", DIAGNOSIS_LIST, index=1, key="new_diag")
    new_med = st.selectbox("New Medicine", MEDICINE_LIST, index=1, key="new_med")
    new_dose = st.text_input("New Dose", "75 mg - Once Daily", key="new_dose")
    new_status = st.selectbox("New Status", STATUS_LIST, key="new_status")
    new_file = st.file_uploader("Upload New Report (PDF)", type=["pdf"], key="new_file")

# ---------- ANALYZE BUTTON - PRO VERSION ----------
st.divider()
analyze = st.button("🔍 Analyze Now - Generate Complete Report", type="primary", use_container_width=True)

if analyze:
    # Extract
    prev_text = extract_text(prev_file)
    new_text = extract_text(new_file)

    st.markdown("## 📋 Complete Analysed Report")
    st.caption(f"Patient: {patient_name} | ID: {patient_id} | Age: {age} | Gender: {gender} | Doctor: {names}")

    # 1. SUMMARY TABLE
    st.markdown("### 1️⃣ Patient Summary")
    st.table({
        "Details": ["Patient", "Diagnosis", "Medicine", "Dose", "Status", "Document"],
        "Previous Record": [patient_name, prev_diag, prev_med, prev_dose, prev_status, prev_file.name if prev_file else "No File Uploaded"],
        "New Record": [patient_name, new_diag, new_med, new_dose, new_status, new_file.name if new_file else "No File Uploaded"]
    })

    # 2. CONFLICT ANALYSIS
    st.markdown("### 2️⃣ Actual Conflict Analysis")
    interaction = get_interaction(prev_med, new_med)

    if interaction:
        level, detail = interaction
        st.markdown(f'<div class="conflict-card"><h4>⚠️ Conflict Found: {prev_med} + {new_med}</h4><p><b>Risk Level:</b> {level}</p><p><b>What is the Conflict?</b><br>{detail}</p><p><b>What Should Be Done?</b><br>1. Do not give both medicines together without doctor approval<br>2. Ask the doctor which one medicine should be stopped<br>3. Do blood test - INR / CBC to check bleeding risk<br>4. Advise patient to avoid injury, report any bleeding immediately</p></div>', unsafe_allow_html=True)
    elif prev_med == new_med and prev_diag == new_diag:
        st.markdown('<div class="safe-card"><h4>✅ No Conflict Found</h4><p>Diagnosis is same and Medicine is same. No change found. Treatment is going correctly. Continue same medicine.</p></div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="info-card"><h4>📝 Change Detected - Verification Needed</h4><p><b>Diagnosis changed:</b> {prev_diag} → {new_diag}<br><b>Medicine changed:</b> {prev_med} → {new_med}<br><b>Status changed:</b> {prev_status} → {new_status}<br><br>Doctor should verify - Is the new medicine safe with previous condition and previous medicine history?</p></div>', unsafe_allow_html=True)

    # 3. WHAT CHANGED
    st.markdown("### 3️⃣ What Changed?")
    changes = []
    if prev_diag != new_diag:
        changes.append(f"Diagnosis: {prev_diag} → {new_diag}")
    if prev_med != new_med:
        changes.append(f"Medicine: {prev_med} → {new_med}")
    if prev_dose != new_dose:
        changes.append(f"Dose: {prev_dose} → {new_dose}")
    if prev_status != new_status:
        changes.append(f"Status: {prev_status} → {new_status}")
    if changes:
        for c in changes:
            st.write(f"- {c}")
    else:
        st.write("- No changes. All values are same.")

    # 4. REPORT CONTENT
    st.markdown("### 4️⃣ What Was Written Inside The Reports?")
    with st.expander("📄 Previous Report - Full Text", expanded=False):
        st.write(prev_text[:5000] if prev_text else "No file uploaded or no text found in PDF.")
        if prev_text:
            kw = find_keywords(prev_text, [prev_med, prev_diag, "BP", "Sugar", "INR", "Hemoglobin"])
            if kw:
                st.markdown("**Key Lines Found:**")
                for line in kw:
                    st.write(f"- {line}")

    with st.expander("📄 New Report - Full Text", expanded=False):
        st.write(new_text[:5000] if new_text else "No file uploaded or no text found in PDF.")
        if new_text:
            kw = find_keywords(new_text, [new_med, new_diag, "BP", "Sugar", "INR", "Hemoglobin"])
            if kw:
                st.markdown("**Key Lines Found:**")
                for line in kw:
                    st.write(f"- {line}")

    # 5. FINAL RECOMMENDATION
    st.markdown("### 5️⃣ Final Recommendation For Doctor")
    if interaction:
        st.info(f"RECOMMENDATION: Do NOT continue {prev_med} + {new_med} together. Consult senior doctor, select one blood thinner, do INR test within 24 hours, and monitor patient for bleeding signs.")
    elif prev_med == new_med and prev_diag == new_diag:
        st.info("RECOMMENDATION: Continue current treatment. Schedule next follow-up as planned.")
    else:
        st.info(f"RECOMMENDATION: Verify new prescription {new_med} for {new_diag}. Check allergy, kidney function and previous medicine interaction before starting.")

    st.markdown("---")
    st.caption("Generated by MediSync | This is a decision support tool, not a final medical diagnosis. Doctor approval required.")

# ---------- FOOTER ----------
st.divider()
st.caption("MediSync v2.0 | For Demo Purpose | Built with Streamlit + PyMuPDF")