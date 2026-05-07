"""
PV AI Workbench — Streamlit Dashboard

Entry point. Run from project root:
    PYTHONPATH=src streamlit run src/dashboard/app.py

Pages live in src/dashboard/pages/ — Streamlit auto-discovers them.
"""

import streamlit as st
import sys
import time
import json
import urllib.request
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))
import shared_state
from projects import list_projects, load_project
from config import CHROMA_PATH, COLLECTION_NAME, OLLAMA_BASE_URL, REASON_MODEL, DRAFT_MODEL

st.set_page_config(
    page_title="PV AI Workbench",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ── Sidebar ─────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## 🔬 PV AI Workbench")
    st.caption("Clinical Pharmacovigilance · Local LLM")

    # Project selection
    st.markdown("---")
    st.markdown("**Active Project**")
    projects = list_projects()
    if projects:
        current_drug = shared_state.get_active_drug()
        drug_names = [p.drug_name for p in projects]
        try:
            idx = drug_names.index(current_drug)
        except ValueError:
            idx = 0

        selected_name = st.selectbox("Drug", drug_names, index=idx, label_visibility="collapsed")
        if selected_name != current_drug:
            shared_state.set_active_drug(selected_name)
            st.rerun()

        active_project = load_project(selected_name)
        st.session_state["active_project"] = active_project

        proj = active_project
        st.markdown(f"**{proj.drug_name.capitalize()}**")
        if hasattr(proj, "indication") and proj.indication:
            st.caption(proj.indication)
        if hasattr(proj, "comparator") and proj.comparator:
            st.caption(f"Comparator: {proj.comparator}")
    else:
        st.warning("No projects configured.")

    # System status
    st.markdown("---")
    st.markdown("**System Status**")

    # Ollama check
    def _ollama_ok() -> tuple[bool, list[str]]:
        try:
            req = urllib.request.Request(f"{OLLAMA_BASE_URL}/api/tags", headers={"User-Agent": "pv-workbench"})
            with urllib.request.urlopen(req, timeout=2) as r:
                data = json.loads(r.read())
            names = [m["name"] for m in data.get("models", [])]
            return True, names
        except Exception:
            return False, []

    ollama_ok, models = _ollama_ok()
    if ollama_ok:
        st.success("Ollama ✓")
        reason_loaded = any(REASON_MODEL.split(":")[0] in m for m in models)
        draft_loaded = any(DRAFT_MODEL.split(":")[0] in m for m in models)
        st.caption(f"{'✓' if reason_loaded else '✗'} {REASON_MODEL}")
        st.caption(f"{'✓' if draft_loaded else '✗'} {DRAFT_MODEL}")
    else:
        st.error("Ollama offline")

    # Vault check
    try:
        import chromadb
        client = chromadb.PersistentClient(path=str(CHROMA_PATH))
        col = client.get_collection(COLLECTION_NAME)
        chunk_count = col.count()
        st.success(f"Vault ✓ ({chunk_count} chunks)")
    except Exception:
        st.error("Vault not indexed")
        st.caption("`python -m ingester.vault_ingester`")

    st.markdown("---")
    st.markdown("**Model Stack**")
    st.caption(f"Reasoning: `{REASON_MODEL}`")
    st.caption(f"Drafting: `{DRAFT_MODEL}`")
    st.caption("Embeddings: `nomic-embed-text`")
    st.caption("Vector DB: ChromaDB (local)")

    st.markdown("---")
    st.caption("All AI outputs require senior clinical reviewer sign-off before regulatory use.")


# ── Main Page ────────────────────────────────────────────────────────────────

st.title("PV AI Workbench")
st.caption("Pharmacovigilance Signal Intelligence · Local-First · Privacy-Preserving")

# Module status cards
st.markdown("### Modules")

modules = [
    ("📋", "Regulatory Q&A", "1_Regulatory_QA", "gemma4:26b", "RAG over ICH/EMA/FDA guidelines. Cited answers with confidence.", "Complete"),
    ("🏷️", "MedDRA Coder", "2_MedDRA_Coder", "gemma4:26b", "Thinking-mode PT deliberation. Reviewer-flag enforced on all outputs.", "Complete"),
    ("📊", "Signal Detection", "3_Signal_Detection", "gemma4:26b + PRR", "FAERS PRR/chi² · Evans criteria · Temporal cohort analysis.", "Complete"),
    ("📝", "ICSR Generator", "4_ICSR_Generator", "gemma4:e4b", "E2B(R3)-aligned narrative drafts. Seriousness auto-assessed.", "Complete"),
    ("📚", "Lit Monitor", "5_Lit_Monitor", "gemma4:e4b + PubMed", "PubMed search · Relevance scoring · Discord digest delivery.", "Complete"),
]

cols = st.columns(len(modules))
for col, (icon, name, page, model, desc, status) in zip(cols, modules):
    with col:
        with st.container(border=True):
            st.markdown(f"### {icon} {name}")
            st.caption(f"`{model}`")
            st.markdown(desc)
            st.success(f"✓ {status}")

st.markdown("---")

# Workflow guidance
col_a, col_b = st.columns(2)

with col_a:
    st.markdown("### Recommended Workflows")
    with st.expander("**New Signal Investigation**", expanded=False):
        st.markdown("""
1. **Signal Detection** → run PRR for drug of interest
2. **MedDRA Coder** → validate reaction terms against FAERS PTs
3. **Regulatory Q&A** → check reporting obligations (ICH E2A timelines)
4. **ICSR Generator** → draft initial case narrative
5. **Lit Monitor** → search for supporting literature
        """)

    with st.expander("**Pre/Post Guideline Change Analysis**", expanded=False):
        st.markdown("""
Use **Signal Detection** with temporal filter:
- Set *Start year* / *End year* to define cohort windows
- Compare PRR and case counts across time periods
- Example: Vancomycin nephrotoxicity, Pre-2020 (trough) vs Post-2020 (AUC/MIC)
        """)

    with st.expander("**Literature-Driven Signal Validation**", expanded=False):
        st.markdown("""
1. **Lit Monitor** → run search with custom date range
2. Review escalation flags (Escalate / Validate actions)
3. Cross-reference with **Signal Detection** PRR data
4. Generate ICSR narrative if a reportable case is identified
        """)

with col_b:
    st.markdown("### Quick Reference")
    with st.expander("**Evans Criteria (Signal Threshold)**"):
        st.markdown("""
All three must be met simultaneously:
- **PRR ≥ 2.0** (at least 2× overrepresented vs. background)
- **N ≥ 3** (minimum 3 drug-reaction co-reports)
- **chi² ≥ 4.0** (statistical significance threshold)

*Yates' correction applied when any expected cell < 5.*
*Continuity correction (b=0.5) applied for background zeros.*
        """)

    with st.expander("**Reporting Timelines (ICH E2A)**"):
        st.markdown("""
| Case Type | Timeline |
|---|---|
| Fatal/life-threatening SUSAR | 7 days (expedited) |
| Other serious unexpected SAR | 15 days (expedited) |
| Non-serious / expected | Periodic (PSUR/PADER) |
| Non-interventional post-approval | Per local regulation |
        """)

    with st.expander("**Seriousness Criteria (ICH E2A)**"):
        st.markdown("""
An adverse event is **serious** if it:
- Results in **death**
- Is **life-threatening**
- Requires **inpatient hospitalization** or prolongation
- Results in **persistent/significant disability**
- Is a **congenital anomaly**
- Is an **important medical event** (per regulatory judgment)
        """)

st.markdown("---")
st.caption(
    f"PV AI Workbench · Local LLM Stack · "
    f"gemma4:26b reasoning · gemma4:e4b drafting · "
    f"Built by Michael Olszewski, PharmD BCPS BCCCP"
)
