"""Module 5 — Literature Monitoring Agent"""

import sys
from pathlib import Path
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from modules.lit_monitor import search_pubmed, score_relevance, generate_digest, send_discord_digest

st.set_page_config(page_title="Literature Monitor", page_icon="📚", layout="wide")
st.title("📚 Literature Monitoring Agent")
st.caption("PubMed + EMA feed · gemma4:e4b digest · Weekly schedule · Discord delivery")

active_project = st.session_state.get("active_project")
default_drug = active_project.drug_name if active_project else "cefiderocol"

col1, col2 = st.columns(2)
with col1:
    drug = st.text_input("Drug to monitor", value=default_drug)
    days_back = st.slider("Look-back window (days)", 1, 90, 7)
with col2:
    max_results = st.number_input("Max results", value=50, step=10)
    send_discord = st.checkbox("Send Discord digest", value=True)

if st.button("Run Literature Search", type="primary"):
    with st.spinner("Querying PubMed and scoring relevance..."):
        try:
            results = search_pubmed(drug, days_back=days_back, max_results=int(max_results))
            if results:
                scored = score_relevance(results, drug)
                digest = generate_digest(drug, scored)
                
                st.subheader(f"Digest for {drug}")
                st.markdown(digest.digest_text)
                
                if digest.escalations:
                    st.error(f"⚠️ {len(digest.escalations)} ESCALATIONS DETECTED")
                    for esc in digest.escalations:
                        st.warning(f"**{esc.title}** (PMID:{esc.pmid})")
                
                if send_discord:
                    with st.spinner("Delivering to Discord..."):
                        if send_discord_digest(digest):
                            st.success("✅ Delivered to #lit-monitor")
                        else:
                            st.warning("⚠️ Discord delivery failed (check logs or token)")

                with st.expander("Full Results Table"):
                    st.table([
                        {"PMID": r.pmid, "Title": r.title[:80] + "...", "Score": r.relevance_score, "Action": r.action}
                        for r in scored
                    ])
            else:
                st.info("No new literature found for the selected period.")
        except Exception as e:
            st.error(f"Search failed: {e}")

st.divider()
st.subheader("Monitoring Schedule")
st.markdown("""
GVP Module VI recommends continuous monitoring with at minimum weekly review cadence.
""")
