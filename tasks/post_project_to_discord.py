"""
Post vancomycin project details to appropriate Discord channels.
Run once from ~/pv-workbench: PYTHONPATH=src python tasks/post_project_to_discord.py
"""

import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from discord_utils import send_discord_message

NAVY  = 0x0F2A48
TEAL  = 0x168A8A
RED   = 0xC0392B
GREEN = 0x27AE60
AMBER = 0xD35400
PURPLE = 0x9B59B6

def post(channel, title, description, color):
    embed = {"title": title, "description": description, "color": color}
    for attempt in range(3):
        ok = send_discord_message(channel, embed=embed)
        if ok:
            print(f"  [OK] #{channel}: {title}")
            time.sleep(1.5)
            return
        time.sleep(1.0 + attempt)
    print(f"  [FAILED] #{channel}: {title}")


print("Posting vancomycin project details to Discord channels...\n")

# ── #signal-detection ─────────────────────────────────────────────────────────
post(
    "signal-detection",
    "Vancomycin Nephrotoxicity — FAERS Signal Results",
    (
        "**Drug**: Vancomycin | **Comparator**: Linezolid | **FAERS 2015-2025**\n"
        "**Method**: PRR/chi2, Evans criteria (PRR>=2, N>=3, chi2>=4)\n\n"
        "**PRE-2020 cohort** (trough-guided, 22,200 reports):\n"
        "```\n"
        "Renal tubular necrosis  PRR=18.10  N=363   SIGNAL\n"
        "Oliguria                PRR=11.97  N=80    SIGNAL\n"
        "Acute kidney injury     PRR=2.16   N=2364  SIGNAL\n"
        "Renal failure           PRR=1.76   N=716   sub-threshold\n"
        "```\n"
        "**POST-2020 cohort** (AUC/MIC-guided, 31,793 reports):\n"
        "```\n"
        "Renal tubular necrosis  PRR=10.51  N=399   SIGNAL (attenuating)\n"
        "Oliguria                PRR=1.12   N=85    RESOLVED\n"
        "Acute kidney injury     PRR=1.95   N=2966  below threshold\n"
        "Renal failure           PRR=1.11   N=642   sub-threshold\n"
        "```\n"
        "**Conclusion**: AUC/MIC guideline adoption associated with meaningful signal reduction. "
        "Oliguria fully resolved. AKI dropped below Evans threshold. "
        "RTN persists — **primary regulatory priority for continued monitoring.**"
    ),
    TEAL,
)

# ── #regulatory-qa ────────────────────────────────────────────────────────────
post(
    "regulatory-qa",
    "Vancomycin — Regulatory & PSUR Implications",
    (
        "**Guideline**: Rybak et al. ASHP/IDSA/SIDP consensus, Am J Health Syst Pharm 2020;77(11):835-864\n"
        "Paradigm shift from trough-based (15-20 mg/L) to AUC/MIC-guided monitoring (AUC24/MIC 400-600 mg.h/L)\n\n"
        "**Regulatory applicability**:\n"
        "- **PSUR Section 8.2** (Signal & Risk Evaluation): document PRR attenuation as evidence of risk-minimization effectiveness\n"
        "- **PSUR Section 16** (Risk Management): 2020 guideline as additional risk minimization activity\n"
        "- **FDA PBRER Section 6.3**: update AKI/nephrotoxicity risk with FAERS temporal trend\n"
        "- **EMA GVP Module VI**: RTN signal (PRR=10.51) requires continued close monitoring\n\n"
        "**Recommended actions**:\n"
        "1. VALIDATE: Characterize RTN at-risk population (dose, duration, monitoring status)\n"
        "2. LABEL UPDATE: Strengthen SmPC/USPI language on AUC/MIC as current standard of care\n"
        "3. SIGNAL COMMUNICATION: Consider DHCP letter in markets where trough-based monitoring persists\n"
        "4. CONTINUE MONITORING: Track RTN quarterly through next PSUR cycle\n\n"
        "_Full analysis: DRAFT — requires senior reviewer sign-off before regulatory use._"
    ),
    NAVY,
)

# ── #meddra-coding ────────────────────────────────────────────────────────────
post(
    "meddra-coding",
    "Vancomycin Nephrotoxicity — MedDRA PT Reference",
    (
        "**Nephrotoxicity PT set used in FAERS analysis** (SOC: Renal and urinary disorders)\n\n"
        "| MedDRA PT | Pre-2020 PRR | Post-2020 PRR | Signal trend |\n"
        "|---|---|---|---|\n"
        "| Renal tubular necrosis | 18.10 (SIGNAL) | 10.51 (SIGNAL) | Attenuating |\n"
        "| Oliguria | 11.97 (SIGNAL) | 1.12 | Resolved |\n"
        "| Acute kidney injury | 2.16 (SIGNAL) | 1.95 | Below threshold |\n"
        "| Renal failure | 1.76 | 1.11 | Attenuating |\n"
        "| Blood creatinine increased | 1.27 | 1.40 | Stable |\n"
        "| Blood urea increased | 0.64 | 0.57 | Stable |\n"
        "| Renal impairment | 1.03 | 0.98 | Stable |\n"
        "| Anuria | 1.45 | 1.22 | Stable |\n\n"
        "**Coding note**: AKI (LLT: Acute renal failure, Nephrotoxicity) is the primary spontaneous "
        "reporting term. RTN (Renal tubular necrosis) is structural and distinct from functional AKI — "
        "should be coded separately when narrative supports histological or clinical evidence of tubular injury."
    ),
    AMBER,
)

# ── #lit-monitor ─────────────────────────────────────────────────────────────
post(
    "lit-monitor",
    "Vancomycin — Bayesian Dosing Methodology Literature",
    (
        "**Clinical question**: Is single-level or two-level Bayesian AUC estimation superior for "
        "vancomycin monitoring under the 2020 AUC/MIC guideline?\n\n"
        "**Key literature summary**:\n\n"
        "**Pai MP et al. (2014)** — Clin Pharmacokinet 53(5):467-480\n"
        "Single-level Bayesian (trough only): AUC within 15% of reference in 82% of stable ID patients. "
        "Two-level superior when CrCl <30 mL/min.\n\n"
        "**Neely MN et al. (2014)** — J Antimicrob Chemother 69(9):2431\n"
        "BestDose software validation. Single-level adequate for stable patients. "
        "Two mid-interval levels reduced AUC bias from -12% to -3% in CrCl <30 group.\n\n"
        "**Broeker A et al. (2018)** — Clin Microbiol Infect 24(9):1008\n"
        "Two-level reduced AUC error from 28% to 11% in patients with rapidly changing CL. "
        "Greatest benefit when true CL differs from population-predicted CL by >50%.\n\n"
        "**Heil EL et al. (2020)** — Open Forum Infect Dis 7(4)\n"
        "Real-world health system implementation. Single-level feasible at scale. "
        "Institutional protocols for two-level triggers in complex patients described.\n\n"
        "**Abdul-Aziz MH et al. (2022)** — Clin Pharmacol Ther 111(4):870\n"
        "Augmented renal clearance (CrCl >130) key driver of underexposure. Two-level required in ARC.\n\n"
        "**PV implication**: Residual RTN signal (PRR 10.51) mechanistically consistent with "
        "single-level use in ICU patients where two-level is pharmacologically warranted."
    ),
    PURPLE,
)

# ── #portfolio-dev ────────────────────────────────────────────────────────────
post(
    "portfolio-dev",
    "Vancomycin Project — Complete",
    (
        "**PV Signal Intelligence Workbench — Vancomycin Project Complete**\n\n"
        "**Deliverables**:\n"
        "- Full 12-page clinical pharmacovigilance PDF report\n"
        "  - Part I: FAERS statistical analysis (PRR/chi2, Evans criteria, temporal cohort)\n"
        "  - Part II: Clinical significance + regulatory implications + ICU perspective\n"
        "  - Part III: Bayesian dosing methodology (single-level vs two-level comparison)\n\n"
        "**Key findings**:\n"
        "- Oliguria signal resolved entirely post-2020 (PRR 11.97 -> 1.12)\n"
        "- AKI dropped below Evans threshold (PRR 2.16 -> 1.95)\n"
        "- RTN persists Evans-positive (18.10 -> 10.51) — regulatory priority\n"
        "- Residual RTN mechanistically linked to single-level Bayesian use in ICU outliers\n\n"
        "**Platform status**: All 5 modules operational across Streamlit + Discord\n"
        "**Vault**: 14 notes, 200 chunks, 100% P@5 retrieval\n"
        "**Next**: Cefiderocol deep-dive, MedGemma integration, scheduled monitoring automation\n\n"
        "GitHub: https://github.com/molszewskiPV/PV-Signal-Intelligence-Workbench"
    ),
    GREEN,
)

print("\nDone.")
