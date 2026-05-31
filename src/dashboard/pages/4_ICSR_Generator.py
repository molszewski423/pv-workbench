"""Module 4 — ICSR Narrative Generator"""

import sys
from pathlib import Path
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from modules.icsr_generator import CaseData, generate_icsr_narrative

st.set_page_config(page_title="ICSR Generator", page_icon="📝", layout="wide")

import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).parent.parent.parent))
from auth import require_auth, auth_sidebar
require_auth()

with st.sidebar:
    auth_sidebar()

st.title("📝 ICSR Narrative Generator")
st.caption("E2B(R3)-aligned · gemma4:e4b drafting · DRAFT only — mandatory senior clinical review before submission")

active_project = st.session_state.get("active_project")
default_drug = active_project.drug_name if active_project else "cefiderocol"

st.error("**DRAFT OUTPUT ONLY** — All narratives generated here are AI drafts. They must be reviewed, verified, and approved by a qualified pharmacovigilance professional before any regulatory submission.")

st.subheader("Case Data Entry")
col1, col2 = st.columns(2)

with col1:
    st.markdown("**Patient**")
    age = st.text_input("Age")
    sex = st.selectbox("Sex", ["", "Male", "Female", "Unknown"])
    weight = st.text_input("Weight (kg)")
    medical_history = st.text_area("Relevant medical history", height=80)

with col2:
    st.markdown("**Suspect Drug**")
    drug = st.text_input("Drug name", value=default_drug)
    dose = st.text_input("Dose and route")
    indication = st.text_input("Indication")
    start_date = st.text_input("Start date")
    stop_date = st.text_input("Stop date")

st.markdown("**Adverse Event**")
ae_description = st.text_area("Adverse event description", height=100)
outcome = st.selectbox("Outcome", ["", "Recovered", "Recovering", "Not recovered", "Fatal", "Unknown"])
causality = st.text_input("Reporter's causality assessment")

if st.button("Generate Draft Narrative", type="primary"):
    with st.spinner("Drafting narrative..."):
        case = CaseData(
            patient_age=age, patient_sex=sex, patient_weight=weight,
            medical_history=medical_history, suspect_drug=drug, dose=dose,
            indication=indication, start_date=start_date, stop_date=stop_date,
            adverse_event=ae_description, outcome=outcome,
            reporter_causality=causality
        )
        result = generate_icsr_narrative(case)
        
    try:
        from shared.pdf_report import save_icsr_report
        case_dict = {
            "patient_description": f"Age: {age}, Sex: {sex}, Weight: {weight}kg. History: {medical_history}",
            "drug_name": drug, "dose_route": dose, "indication": indication,
            "start_date": start_date, "stop_date": stop_date,
            "adverse_event": ae_description, "outcome": outcome,
        }
        pdf_path = save_icsr_report(case_dict, result)
        st.success(f"PDF saved → {pdf_path.name}")
    except Exception as e:
        st.warning(f"PDF save failed: {e}")

    st.subheader("Draft Narrative")
    st.text_area("Copy/Edit Narrative", value=result.narrative, height=400)
    
    st.subheader("Seriousness Criteria (Automatic)")
    if result.seriousness_criteria:
        st.write(", ".join(result.seriousness_criteria))
    else:
        st.write("No criteria met (Reviewer adjudication required)")
