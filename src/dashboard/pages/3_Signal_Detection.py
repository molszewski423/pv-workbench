"""Module 3 — FAERS Signal Detection"""

import sys
from pathlib import Path
import streamlit as st
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from modules.signal_detection import run_signal_detection, interpret_signals

st.set_page_config(page_title="Signal Detection", page_icon="📊", layout="wide")

import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).parent.parent.parent))
from auth import require_auth, auth_sidebar
require_auth()

with st.sidebar:
    auth_sidebar()

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

with st.expander("Temporal Filter — Pre/Post Guideline Comparison"):
    tc1, tc2 = st.columns(2)
    with tc1:
        start_year = st.number_input("Start year", min_value=2004, max_value=2026, value=2004, step=1)
    with tc2:
        end_year_raw = st.number_input("End year (0 = present)", min_value=0, max_value=2026, value=0, step=1)
    end_year = int(end_year_raw) if end_year_raw > 0 else None
    st.caption("Example: Vancomycin nephrotoxicity — Pre-2020 (2015–2019) vs Post-2020 (2020–present)")

run_col, _ = st.columns([1, 3])
with run_col:
    run = st.button("Run Signal Detection", type="primary", use_container_width=True)

if run:
    with st.spinner(f"Fetching FAERS data for {drug_name} ({int(start_year)}–{end_year or 'present'})..."):
        try:
            signals = run_signal_detection(
                drug_name, comparator, int(max_bg),
                start_year=int(start_year),
                end_year=end_year,
            )
        except Exception as e:
            st.error(f"FAERS fetch failed: {e}")
            st.stop()

    df = pd.DataFrame(signals)
    if df.empty:
        st.warning("No FAERS reports found for this drug/period.")
        st.stop()

    df_signals = df[df["signal"]].copy()
    period_label = f"{int(start_year)}–{end_year or 'present'}"

    # Summary metrics
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Period", period_label)
    m2.metric("PTs analyzed", len(df))
    m3.metric("Evans signals", len(df_signals))
    total_cases = df["drug_cases"].sum()
    m4.metric("Total drug reports", f"{total_cases:,}")

    st.markdown("---")

    if not df_signals.empty:
        tab1, tab2, tab3 = st.tabs(["📊 Chart", "📋 Data Table", "🧠 Clinical Interpretation"])

        with tab1:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            import matplotlib.patches as mpatches
            import numpy as np

            top_n = df_signals.nlargest(min(20, len(df_signals)), "prr")
            labels = [pt[:35] + "…" if len(pt) > 35 else pt for pt in top_n["reaction_pt"]]
            prrs = top_n["prr"].values
            ns = top_n["drug_cases"].values

            fig, ax = plt.subplots(figsize=(12, max(5, len(labels) * 0.45)))
            colors = ["#d62728" if p >= 5 else "#ff7f0e" if p >= 3 else "#1f77b4" for p in prrs]
            bars = ax.barh(range(len(labels)), prrs, color=colors, alpha=0.85, edgecolor="white")
            ax.axvline(x=2.0, color="black", linestyle="--", linewidth=1.2, label="Evans PRR threshold (2.0)")
            ax.set_yticks(range(len(labels)))
            ax.set_yticklabels(labels, fontsize=9)
            ax.set_xlabel("Proportional Reporting Ratio (PRR)", fontsize=10)
            ax.set_title(
                f"{drug_name.capitalize()} — FAERS Signal Detection\n"
                f"Period: {period_label} · Comparator: {comparator.capitalize()} · Evans criteria",
                fontsize=11, fontweight="bold",
            )
            ax.legend(fontsize=9)
            ax.invert_yaxis()

            # Case count annotations
            for i, (p, n) in enumerate(zip(prrs, ns)):
                ax.text(p + 0.05, i, f"N={n}", va="center", fontsize=8, color="dimgray")

            patches = [
                mpatches.Patch(color="#d62728", alpha=0.85, label="PRR ≥ 5 (strong)"),
                mpatches.Patch(color="#ff7f0e", alpha=0.85, label="PRR 3–5 (moderate)"),
                mpatches.Patch(color="#1f77b4", alpha=0.85, label="PRR 2–3 (threshold)"),
            ]
            ax.legend(handles=patches + [plt.Line2D([0], [0], color="black", linestyle="--", label="Evans threshold")],
                      fontsize=8, loc="lower right")

            plt.tight_layout()
            st.pyplot(fig)
            plt.close()

        with tab2:
            display_cols = ["reaction_pt", "drug_cases", "background_cases", "prr", "chi2", "continuity_corrected"]
            st.dataframe(
                df_signals[display_cols].rename(columns={
                    "reaction_pt": "MedDRA PT",
                    "drug_cases": "Drug N",
                    "background_cases": "Background N",
                    "prr": "PRR",
                    "chi2": "chi²",
                    "continuity_corrected": "Continuity Corr.",
                }).sort_values("PRR", ascending=False),
                use_container_width=True,
                height=min(600, 40 + len(df_signals) * 35),
            )

            csv = df_signals.to_csv(index=False)
            st.download_button(
                "Download signals CSV",
                csv,
                file_name=f"{drug_name}_signals_{period_label.replace('–', '-')}.csv",
                mime="text/csv",
            )

        with tab3:
            with st.spinner("Interpreting signals with gemma4:26b..."):
                try:
                    results = interpret_signals(signals, drug_name)
                except Exception as e:
                    st.error(f"Interpretation failed: {e}")
                    st.stop()

            try:
                from shared.pdf_report import save_signal_detection_report, generate_signal_discussion
                with st.spinner("Generating clinical discussion narrative..."):
                    discussion = generate_signal_discussion(drug_name, comparator, results)
                pdf_path = save_signal_detection_report(drug_name, comparator, results, raw_signals=signals, discussion=discussion)
                st.success(f"PDF saved → {pdf_path.name}")
            except Exception as e:
                st.warning(f"PDF save failed: {e}")

            action_colors = {"expedited": "error", "routine": "warning", "monitor": "info", "none": "success"}

            for r in results:
                if not r.signal:
                    continue
                action = r.regulatory_action.lower()
                color = action_colors.get(action, "info")
                with st.expander(f"**{r.reaction_pt.upper()}** — PRR {r.prr:.2f} · N={r.drug_cases} · chi²={r.chi2:.1f}"):
                    c1, c2 = st.columns([3, 1])
                    with c1:
                        st.markdown(f"**Assessment**: {r.clinical_assessment}")
                        if r.reviewer_notes:
                            st.markdown(f"**Notes**: {r.reviewer_notes}")
                    with c2:
                        getattr(st, color)(f"**{r.regulatory_action.upper()}**")
                        if r.confounding_likely:
                            st.warning("Confounding likely")

        st.markdown("---")
        st.caption(
            "Evans criteria: PRR ≥ 2.0 AND N ≥ 3 AND chi² ≥ 4.0 · "
            "Yates' correction applied for small expected cells · "
            "Background continuity correction applied when b=0 · "
            "All interpretations are AI-generated drafts requiring senior reviewer sign-off."
        )

    else:
        st.success(f"No Evans-positive signals detected for {drug_name} ({period_label}).")
        with st.expander("Sub-threshold signals (PRR < 2 or N < 3 or chi² < 4)"):
            st.dataframe(df[["reaction_pt", "drug_cases", "prr", "chi2"]].head(30), use_container_width=True)
