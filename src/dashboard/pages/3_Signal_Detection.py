"""Module 3 — FAERS Signal Detection"""

import sys
from pathlib import Path
import streamlit as st
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from modules.signal_detection import run_signal_detection, interpret_signals

st.set_page_config(page_title="Signal Detection", page_icon="📊", layout="wide")
st.title("📊 FAERS Signal Detection")
st.caption("PRR/chi² disproportionality · Evans criteria · gemma4:26b clinical interpretation")

active_project = st.session_state.get("active_project")
default_drug = active_project.drug_name if active_project else "cefiderocol"
default_comparator = active_project.comparator if active_project else "meropenem"

col1, col2, col3 = st.columns(3)
with col1:
    drug_name = st.text_input("Drug name", value=default_drug)
with col2:
    comparator = st.text_input("Comparator (background)", value=default_comparator)
with col3:
    max_bg = st.number_input("Max background records", value=5000, step=500)

with st.expander("Temporal Filter (optional — for pre/post guideline analysis)"):
    tc1, tc2 = st.columns(2)
    with tc1:
        start_year = st.number_input("Start year", min_value=2004, max_value=2026, value=2004, step=1)
    with tc2:
        end_year_raw = st.number_input("End year (0 = present)", min_value=0, max_value=2026, value=0, step=1)
    end_year = int(end_year_raw) if end_year_raw > 0 else None

if st.button("Run Signal Detection", type="primary"):
    with st.spinner(f"Fetching FAERS data for {drug_name}..."):
        try:
            signals = run_signal_detection(
                drug_name, comparator, int(max_bg),
                start_year=int(start_year),
                end_year=end_year,
            )
            df = pd.DataFrame(signals)
            df_signals = df[df["signal"]].copy()

            col_a, col_b, col_c = st.columns(3)
            col_a.metric("Total PTs analyzed", len(df))
            col_b.metric("Signals (Evans criteria)", len(df_signals))
            period_label = f"{int(start_year)}–{end_year or 'present'}"
            col_c.metric("Period", period_label)

            if not df_signals.empty:
                st.subheader("Statistical Signals")
                st.dataframe(
                    df_signals[["reaction_pt", "drug_cases", "prr", "chi2", "background_cases", "continuity_corrected"]],
                    use_container_width=True,
                )

                with st.spinner("Generating clinical interpretations..."):
                    results = interpret_signals(signals, drug_name)

                st.subheader("Clinical Interpretation")
                for r in results:
                    if not r.signal:
                        continue
                    with st.expander(f"**{r.reaction_pt.upper()}** (PRR={r.prr:.2f}, N={r.drug_cases})"):
                        st.markdown(f"**Clinical Assessment**: {r.clinical_assessment}")
                        st.markdown(f"**Confounding Likely**: {r.confounding_likely}")
                        st.markdown(f"**Regulatory Action**: {r.regulatory_action.upper()}")
                        if r.reviewer_notes:
                            st.markdown(f"**Reviewer Notes**: {r.reviewer_notes}")
            else:
                st.success("No signals detected.")

        except Exception as e:
            st.error(f"Pipeline error: {e}")
