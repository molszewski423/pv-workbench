"""Module 5 — Literature Monitoring Agent"""

import sys
from pathlib import Path
import streamlit as st
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from modules.lit_monitor import search_pubmed, score_relevance, generate_digest, send_discord_digest

st.set_page_config(page_title="Literature Monitor", page_icon="📚", layout="wide")
st.title("📚 Literature Monitoring Agent")
st.caption("PubMed search · gemma4:e4b digest · Discord delivery · GVP Module VI cadence")

active_project = st.session_state.get("active_project")
default_drug = active_project.drug_name if active_project else "cefiderocol"

col1, col2 = st.columns([2, 1])
with col1:
    drug = st.text_input("Drug to monitor", value=default_drug)
    days_back = st.slider("Look-back window (days)", 1, 365, 30)
with col2:
    max_results = st.number_input("Max results", value=50, step=10, min_value=5)
    send_discord = st.checkbox("Send to Discord #lit-monitor", value=False)
    min_score = st.slider("Min relevance score", 0.0, 1.0, 0.3, step=0.05)

run_col, _ = st.columns([1, 3])
with run_col:
    run = st.button("Run Literature Search", type="primary", use_container_width=True)

if run:
    with st.spinner(f"Querying PubMed for {drug} (last {days_back} days)..."):
        try:
            results = search_pubmed(drug, days_back=days_back, max_results=int(max_results))
        except Exception as e:
            st.error(f"PubMed search failed: {e}")
            st.stop()

    if not results:
        st.info(f"No new publications found for {drug} in the last {days_back} days.")
        st.stop()

    with st.spinner(f"Scoring {len(results)} results for PV relevance..."):
        scored = score_relevance(results, drug)

    filtered = [r for r in scored if r.relevance_score >= min_score]
    st.success(f"Found {len(results)} papers · {len(filtered)} above relevance threshold ({min_score:.2f})")

    if not filtered:
        st.warning("No papers met the relevance threshold. Lower the score threshold or expand the date range.")
        st.stop()

    with st.spinner("Generating digest with gemma4:e4b..."):
        try:
            digest = generate_digest(drug, filtered)
        except Exception as e:
            st.error(f"Digest generation failed: {e}")
            st.stop()

    # Escalation alerts
    if digest.escalations:
        st.error(f"⚠️ {len(digest.escalations)} ESCALATION(S) DETECTED — Immediate review required")
        for esc in digest.escalations:
            with st.container(border=True):
                st.markdown(f"**ESCALATE: {esc.title}**")
                st.caption(f"PMID: {esc.pmid} · {esc.journal} · {esc.pub_date}")
                st.markdown(esc.summary)

    tab1, tab2 = st.tabs(["📄 Digest", "📊 Results Table"])

    with tab1:
        st.markdown(f"### Pharmacovigilance Literature Digest — {drug.capitalize()}")
        st.caption(f"Search period: last {days_back} days · {len(filtered)} papers · Generated {digest.search_date}")
        st.markdown(digest.digest_text)

        if send_discord:
            with st.spinner("Delivering to Discord..."):
                ok = send_discord_digest(digest)
                if ok:
                    st.success("✓ Delivered to #lit-monitor")
                else:
                    st.warning("Discord delivery failed — check DISCORD_BOT_TOKEN")

    with tab2:
        rows = []
        for r in sorted(scored, key=lambda x: x.relevance_score, reverse=True):
            rows.append({
                "PMID": r.pmid,
                "Title": r.title[:90] + "…" if len(r.title) > 90 else r.title,
                "Journal": r.journal[:30] if r.journal else "",
                "Date": r.pub_date,
                "Relevance": round(r.relevance_score, 3),
                "Action": r.action,
            })
        df = pd.DataFrame(rows)

        def color_action(val):
            colors = {"Escalate": "background-color: #ffcccc", "Validate": "background-color: #ffe4b5",
                      "Monitor": "background-color: #e8f4fd", "None": ""}
            return colors.get(val, "")

        st.dataframe(
            df.style.applymap(color_action, subset=["Action"]),
            use_container_width=True,
            height=min(700, 40 + len(df) * 35),
        )

        csv = df.to_csv(index=False)
        st.download_button(
            "Download results CSV",
            csv,
            file_name=f"{drug}_lit_monitor_{digest.search_date}.csv",
            mime="text/csv",
        )

st.divider()
with st.expander("GVP Module VI Monitoring Schedule"):
    st.markdown("""
| Signal Type | Monitoring Frequency |
|---|---|
| Newly marketed drugs (first 2 years) | Monthly |
| Established products with known signals | Weekly |
| Routine post-approval surveillance | Monthly |
| PSUR/PADER submission preparation | Per reporting period |

*GVP Module VI (EMA) recommends continuous monitoring with minimum weekly review for active signals.*
    """)
