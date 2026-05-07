"""
Vancomycin Nephrotoxicity FAERS Analysis — Pre vs Post 2020 AUC/MIC Guideline

Runs FAERS PRR/chi² signal detection for two temporal cohorts:
  - Pre-2020: 2015-2019 (trough-guided era)
  - Post-2020: 2020-2025 (AUC/MIC-guided era)

Comparator: linezolid (same gram-positive indication, similar MRSA use context)
Focus: nephrotoxicity MedDRA PTs (AKI, creatinine increase, renal failure, etc.)

Output: JSON + summary report saved to ~/Desktop/vancomycin_pv_analysis/
"""

from __future__ import annotations
import json
import sys
import os
from pathlib import Path
from datetime import datetime

# Setup path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
os.environ.setdefault("OUTPUT_DIR", str(Path.home() / "pv_workbench" / "output"))

from modules.signal_detection import run_signal_detection, interpret_signals

DRUG = "vancomycin"
COMPARATOR = "linezolid"  # More appropriate comparator than meropenem for MRSA-active agents
MAX_BG = 3000

NEPHROTOXICITY_PTS = {
    "acute kidney injury",
    "blood creatinine increased",
    "renal failure",
    "renal impairment",
    "nephrotoxicity",
    "blood urea increased",
    "oliguria",
    "anuria",
    "renal failure acute",
    "renal tubular necrosis",
    "creatinine renal clearance decreased",
    "glomerular filtration rate decreased",
}

OUTPUT_DIR = Path.home() / "Desktop" / "vancomycin_pv_analysis"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")


def extract_nephrotox_signals(signals: list[dict]) -> list[dict]:
    return [s for s in signals if s["reaction_pt"].lower() in NEPHROTOXICITY_PTS]


def run_era(label: str, start: int, end: int) -> dict:
    print(f"\n{'='*60}")
    print(f"  {label}: {start}-{end}")
    print(f"{'='*60}")
    signals = run_signal_detection(
        DRUG, COMPARATOR, MAX_BG,
        start_year=start, end_year=end,
    )
    nephro = extract_nephrotox_signals(signals)
    positive_nephro = [s for s in nephro if s["signal"]]
    total_positive = [s for s in signals if s["signal"]]

    print(f"\nTotal PTs: {len(signals)} | Positive signals: {len(total_positive)}")
    print(f"Nephrotoxicity PTs detected: {len(nephro)}")
    print(f"Nephrotoxicity signals (Evans+): {len(positive_nephro)}")
    for s in sorted(nephro, key=lambda x: x["prr"], reverse=True):
        flag = "SIGNAL" if s["signal"] else "sub-threshold"
        print(f"  [{flag}] {s['reaction_pt']}: PRR={s['prr']:.2f}, N={s['drug_cases']}, chi²={s['chi2']:.1f}")

    return {
        "era": label,
        "years": f"{start}-{end}",
        "all_signals": signals,
        "nephro_pts": nephro,
        "positive_nephro": positive_nephro,
        "total_positive_count": len(total_positive),
        "drug_total_reports": sum(s["drug_cases"] for s in signals[:1]),  # proxy
    }


def generate_comparison_report(pre: dict, post: dict) -> str:
    lines = [
        "# Vancomycin Nephrotoxicity Signal Analysis",
        f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"**Drug**: {DRUG.capitalize()}",
        f"**Comparator**: {COMPARATOR.capitalize()} (same gram-positive spectrum, MRSA indication)",
        f"**Statistical method**: PRR/chi² — Evans criteria (PRR≥2, N≥3, chi²≥4)",
        "",
        "## Temporal Cohorts",
        f"- **Pre-2020 (trough-guided era)**: {pre['years']}",
        f"- **Post-2020 (AUC/MIC era)**: {post['years']}",
        "",
        "---",
        "",
        "## Nephrotoxicity Signal Comparison",
        "",
        "| MedDRA PT | Pre-2020 PRR | Pre-2020 N | Pre-2020 Signal | Post-2020 PRR | Post-2020 N | Post-2020 Signal | Trend |",
        "|---|---|---|---|---|---|---|---|",
    ]

    pre_lookup = {s["reaction_pt"]: s for s in pre["nephro_pts"]}
    post_lookup = {s["reaction_pt"]: s for s in post["nephro_pts"]}
    all_pts = sorted(NEPHROTOXICITY_PTS & (set(pre_lookup) | set(post_lookup)))

    for pt in all_pts:
        p = pre_lookup.get(pt, {})
        q = post_lookup.get(pt, {})
        p_prr = f"{p['prr']:.2f}" if p else "—"
        p_n = str(p.get("drug_cases", "—")) if p else "—"
        p_sig = "✓" if p.get("signal") else "—"
        q_prr = f"{q['prr']:.2f}" if q else "—"
        q_n = str(q.get("drug_cases", "—")) if q else "—"
        q_sig = "✓" if q.get("signal") else "—"

        if p and q:
            if p["prr"] > q["prr"] + 0.5:
                trend = "↓ Attenuating"
            elif q["prr"] > p["prr"] + 0.5:
                trend = "↑ Increasing"
            else:
                trend = "→ Stable"
        elif p and not q:
            trend = "↓ Resolved"
        elif not p and q:
            trend = "↑ Emerged"
        else:
            trend = "—"

        lines.append(f"| {pt} | {p_prr} | {p_n} | {p_sig} | {q_prr} | {q_n} | {q_sig} | {trend} |")

    lines += [
        "",
        "---",
        "",
        "## Summary Statistics",
        f"| | Pre-2020 ({pre['years']}) | Post-2020 ({post['years']}) |",
        "|---|---|---|",
        f"| Total Evans-positive signals | {pre['total_positive_count']} | {post['total_positive_count']} |",
        f"| Nephrotox Evans signals | {len(pre['positive_nephro'])} | {len(post['positive_nephro'])} |",
        "",
        "---",
        "",
        "## Clinical Interpretation Notes",
        "",
        "**Methodological caveats:**",
        "- FAERS disproportionality does not establish causation; it identifies reporting anomalies.",
        "- Post-2020 guideline adoption was gradual; institutions transitioned at varying rates.",
        "- Confounders: piperacillin-tazobactam combination, aminoglycosides, IV contrast, baseline CKD.",
        "- Comparator (linezolid) has minimal nephrotoxicity — a high-specificity background for renal signals.",
        "- Confounding by indication expected: critically ill patients (baseline renal compromise) predominate.",
        "",
        "**PV Interpretation:**",
        "- A falling PRR for AKI/creatinine PTs post-2020 supports guideline effectiveness.",
        "- A persistent signal warrants further investigation: adoption lag vs. residual risk in high-risk patients.",
        "- This temporal analysis is suitable for PSUR Section 8 (Signal and Risk Evaluation) or PADER narrative.",
        "",
        "**Senior Reviewer Sign-Off Required** — This is an AI-generated draft analysis.",
        f"Generated by PV AI Workbench (gemma4:26b) · {datetime.now().strftime('%Y-%m-%d')}",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    print(f"Vancomycin Nephrotoxicity Analysis — Pre/Post 2020 AUC/MIC Guideline")
    print(f"Comparator: {COMPARATOR}")
    print(f"Output: {OUTPUT_DIR}")

    pre = run_era("Pre-2020 (trough era)", 2015, 2019)
    post = run_era("Post-2020 (AUC/MIC era)", 2020, 2025)

    # Save raw JSON
    data = {
        "generated": datetime.now().isoformat(),
        "drug": DRUG,
        "comparator": COMPARATOR,
        "pre_2020": {
            "era": pre["era"],
            "years": pre["years"],
            "nephro_signals": pre["nephro_pts"],
            "total_positive": pre["total_positive_count"],
        },
        "post_2020": {
            "era": post["era"],
            "years": post["years"],
            "nephro_signals": post["nephro_pts"],
            "total_positive": post["total_positive_count"],
        },
    }
    json_path = OUTPUT_DIR / f"vancomycin_nephrotox_{timestamp}.json"
    json_path.write_text(json.dumps(data, indent=2))
    print(f"\nRaw data → {json_path}")

    # Save markdown report
    report = generate_comparison_report(pre, post)
    md_path = OUTPUT_DIR / f"vancomycin_nephrotox_report_{timestamp}.md"
    md_path.write_text(report)
    print(f"Report → {md_path}")

    # Generate visualization
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.patches as mpatches
        import numpy as np

        pre_lookup = {s["reaction_pt"]: s for s in pre["nephro_pts"]}
        post_lookup = {s["reaction_pt"]: s for s in post["nephro_pts"]}
        all_pts = sorted(NEPHROTOXICITY_PTS & (set(pre_lookup) | set(post_lookup)))

        pre_prrs = [pre_lookup.get(pt, {}).get("prr", 0) for pt in all_pts]
        post_prrs = [post_lookup.get(pt, {}).get("prr", 0) for pt in all_pts]
        pre_ns = [pre_lookup.get(pt, {}).get("drug_cases", 0) for pt in all_pts]
        post_ns = [post_lookup.get(pt, {}).get("drug_cases", 0) for pt in all_pts]

        x = np.arange(len(all_pts))
        width = 0.35

        fig, axes = plt.subplots(2, 1, figsize=(14, 10))
        fig.suptitle(
            f"Vancomycin Nephrotoxicity: Pre-2020 (Trough) vs Post-2020 (AUC/MIC)\n"
            f"Comparator: {COMPARATOR.capitalize()} · Evans Criteria · FAERS",
            fontsize=13, fontweight="bold",
        )

        # PRR comparison
        ax1 = axes[0]
        bars1 = ax1.bar(x - width/2, pre_prrs, width, label="Pre-2020 (2015–2019)", color="#d62728", alpha=0.8)
        bars2 = ax1.bar(x + width/2, post_prrs, width, label="Post-2020 (2020–2025)", color="#1f77b4", alpha=0.8)
        ax1.axhline(y=2.0, color="black", linestyle="--", linewidth=1, label="Evans threshold PRR=2")
        ax1.set_xticks(x)
        ax1.set_xticklabels([pt.replace(" ", "\n") for pt in all_pts], fontsize=8)
        ax1.set_ylabel("PRR (Proportional Reporting Ratio)")
        ax1.set_title("PRR by Nephrotoxicity PT")
        ax1.legend()
        ax1.set_ylim(bottom=0)

        # Case count comparison
        ax2 = axes[1]
        ax2.bar(x - width/2, pre_ns, width, label="Pre-2020 (2015–2019)", color="#d62728", alpha=0.8)
        ax2.bar(x + width/2, post_ns, width, label="Post-2020 (2020–2025)", color="#1f77b4", alpha=0.8)
        ax2.axhline(y=3, color="black", linestyle="--", linewidth=1, label="Evans min N=3")
        ax2.set_xticks(x)
        ax2.set_xticklabels([pt.replace(" ", "\n") for pt in all_pts], fontsize=8)
        ax2.set_ylabel("Case Count (N)")
        ax2.set_title("Reported Cases by Nephrotoxicity PT")
        ax2.legend()

        plt.tight_layout()
        chart_path = OUTPUT_DIR / f"vancomycin_nephrotox_chart_{timestamp}.png"
        plt.savefig(chart_path, dpi=150, bbox_inches="tight")
        plt.close()
        print(f"Chart → {chart_path}")

    except Exception as e:
        print(f"Chart generation failed: {e}")

    print(f"\nAll outputs saved to {OUTPUT_DIR}")
    print("\n" + "="*60)
    print(report)
