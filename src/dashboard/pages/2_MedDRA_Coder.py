"""Module 2 — MedDRA Coding Assistant"""

import sys
from pathlib import Path
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from modules.meddra_coder import suggest_meddra_pt

st.set_page_config(page_title="MedDRA Coder", page_icon="🏷️", layout="wide")
st.title("🏷️ MedDRA Coding Assistant")
st.caption("gemma4:26b Thinking Mode deliberation · All suggestions require senior reviewer sign-off")

st.warning("**Clinical Oversight Required** — MedDRA coding suggestions are AI-generated drafts. Final coding decisions must be made by a qualified pharmacovigilance professional.")

narrative = st.text_area(
    "Clinical narrative or adverse event description",
    placeholder="e.g. Patient reported sudden onset difficulty breathing with chest tightness 30 minutes after drug administration...",
    height=150,
)

verbatim = st.text_input(
    "Verbatim term (optional)",
    placeholder="e.g. 'difficulty breathing and chest tightness'",
)

if st.button("Suggest MedDRA PT", type="primary") and narrative:
    with st.spinner("Deliberating..."):
        result = suggest_meddra_pt(narrative, verbatim_term=verbatim if verbatim else None)

    col1, col2 = st.columns([2, 1])
    with col1:
        st.subheader("Suggestion")
        st.success(f"**Primary PT**: {result.primary_pt}")
        st.info(f"**SOC**: {result.soc}")
        
        st.subheader("Coding Notes")
        st.markdown(result.coding_notes)
        
    with col2:
        st.subheader("Metrics")
        st.write(f"Confidence: **{result.confidence}**")
        if result.reviewer_flag:
            st.error("⚠️ Mandatory Senior Review Required")
        else:
            st.success("✅ Routine Review")
            
        if result.alternative_pts:
            st.subheader("Alternatives")
            for alt in result.alternative_pts:
                st.markdown(f"- {alt}")
