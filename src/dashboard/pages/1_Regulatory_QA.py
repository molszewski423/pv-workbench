"""Module 1 — Regulatory Document Q&A"""

import sys
from pathlib import Path
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from modules.regulatory_qa import answer_regulatory_question

st.set_page_config(page_title="Regulatory Q&A", page_icon="📋", layout="wide")
st.title("📋 Regulatory Document Q&A")
st.caption("RAG over EMA GVP modules, ICH guidelines · gemma4:26b Thinking Mode · Citations required")

active_project = st.session_state.get("active_project")
if not active_project:
    st.warning("Please select a project in the sidebar.")
    st.stop()

st.info(f"Active Context: **{active_project.drug_name}** | Jurisdiction: **Both**")

question = st.text_area(
    "Regulatory question",
    placeholder="e.g. What are the expedited reporting timelines under ICH E2A for unexpected SUSARs?",
    height=100,
)

col1, col2 = st.columns([1, 3])
with col1:
    folder_filter = st.selectbox("Restrict to folder", ["All", "Guidelines", "Signals", "Literature"])
    n_chunks = st.slider("Context chunks", 3, 10, 5)

if st.button("Ask", type="primary") and question:
    with st.spinner("Thinking..."):
        folder = None if folder_filter == "All" else folder_filter
        result = answer_regulatory_question(question, n_context=n_chunks, folder=folder)

    st.subheader("Answer")
    st.markdown(result.answer)
    
    st.subheader("Citations")
    for cit in result.citations:
        st.markdown(f"- {cit}")
        
    st.subheader("Confidence")
    st.write(result.confidence)

    with st.expander("Retrieved Source Chunks"):
        for i, h in enumerate(result.retrieved_chunks, 1):
            st.markdown(f"**[{i}] {h['source_note']} › {h['section_header']}** (dist={h['distance']})")
            st.markdown(h["text"])
            st.markdown("---")
