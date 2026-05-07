import nbformat as nbf
import json
import glob
import os

# Load the most recent signals file
output_dir = os.path.expanduser("~/pv_workbench/output")
files = glob.glob(f"{output_dir}/cefiderocol_signals_*.json")
latest = sorted(files)[-1]

with open(latest) as f:
    signals = json.load(f)

nb = nbf.v4.new_notebook()

cells = []

# Title cell
cells.append(nbf.v4.new_markdown_cell("""# Cefiderocol FAERS Signal Detection Analysis
**Pharmacovigilance Data Science Portfolio**  
**Author:** Michael Olszewski, PharmD, BCPS, BCCCP  
**Data Source:** OpenFDA FAERS API  
**Methodology:** Proportional Reporting Ratio (PRR) — Evans' Criteria  
**Date:** 2026-05-05

---
"""))

# Background
cells.append(nbf.v4.new_markdown_cell("""## 1. Background

Cefiderocol is a siderophore cephalosporin active against carbapenem-resistant 
Gram-negative organisms including *Pseudomonas aeruginosa*, *Acinetobacter baumannii*, 
and carbapenem-resistant Enterobacteriaceae. Given its last-resort status in critically 
ill patients, robust post-marketing pharmacovigilance is essential.

This analysis demonstrates a reproducible signal detection pipeline using the OpenFDA 
FAERS API, implementing PRR disproportionality analysis against a beta-lactam reference 
population (meropenem, n=5,000).

**Regulatory context:** ICH E2C(R2), ICH E2E — signal detection methodology aligned 
with Evans et al. (2001) classical threshold criteria: PRR ≥ 2, N ≥ 3, χ² ≥ 4.
"""))

# Data acquisition
cells.append(nbf.v4.new_markdown_cell("## 2. Data Acquisition"))
cells.append(nbf.v4.new_code_cell("""import requests
import json
import time
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
import seaborn as sns
from collections import Counter
from pathlib import Path
from datetime import datetime

# OpenFDA API configuration
API_BASE = "https://api.fda.gov/drug/event.json"

def fetch_reports(drug_name, max_records=None, limit=100):
    reports, skip = [], 0
    while True:
        if max_records and len(reports) >= max_records:
            break
        params = {"search": f"patient.drug.medicinalproduct:{drug_name}",
                  "limit": limit, "skip": skip}
        r = requests.get(API_BASE, params=params, timeout=15)
        if r.status_code != 200:
            break
        batch = r.json().get("results", [])
        if not batch:
            break
        reports.extend(batch)
        if len(batch) < limit:
            break
        skip += limit
        time.sleep(0.25)
    return reports

print("Loading pre-fetched signal data from pipeline run...")
print(f"Data source: OpenFDA FAERS API")
print(f"Drug: Cefiderocol | Reference: Meropenem (n=5,000)")
print(f"Pipeline completed: 2026-05-05")
"""))

# Load and display results
cells.append(nbf.v4.new_markdown_cell("## 3. PRR Signal Detection Results"))
cells.append(nbf.v4.new_code_cell(f"""# Load pipeline results
signals = {json.dumps(signals, indent=2).replace("true", "True").replace("false", "False")}

df = pd.DataFrame(signals)
df_signals = df[df['signal'] == True].copy()
df_all = df.copy()

print(f"Total reaction PTs analyzed: {{len(df)}}")
print(f"Signals detected (PRR≥2, N≥3, χ²≥4): {{len(df_signals)}}")
print()
print("=" * 70)
print(f"{{' Cefiderocol FAERS Signal Detection — Top 20 by PRR ':=^70}}")
print("=" * 70)
display(df_signals[['reaction_pt','drug_cases','prr','chi2']].head(20).rename(columns={{
    'reaction_pt': 'MedDRA PT',
    'drug_cases': 'N (cases)',
    'prr': 'PRR',
    'chi2': 'Chi²'
}}).reset_index(drop=True))
"""))

# Visualization
cells.append(nbf.v4.new_markdown_cell("## 4. Visualization"))
cells.append(nbf.v4.new_code_cell("""matplotlib.use('Agg')

fig, axes = plt.subplots(1, 2, figsize=(16, 7))
fig.suptitle('Cefiderocol FAERS Disproportionality Analysis\\nPRR Signal Detection vs Meropenem Reference Population',
             fontsize=13, fontweight='bold', y=1.02)

# Plot 1: Top 15 signals by PRR
top15 = df_signals.nlargest(15, 'prr')
# Filter out data quality artifact
top15 = top15[top15['reaction_pt'] != 'no adverse event']

colors = ['#c0392b' if p >= 10 else '#e67e22' if p >= 5 else '#f1c40f' for p in top15['prr']]
bars = axes[0].barh(top15['reaction_pt'], top15['prr'], color=colors)
axes[0].axvline(x=2, color='black', linestyle='--', alpha=0.5, label='PRR threshold (2.0)')
axes[0].set_xlabel('Proportional Reporting Ratio (PRR)', fontsize=11)
axes[0].set_title('Top Signals by PRR Magnitude', fontsize=11, fontweight='bold')
axes[0].legend()
axes[0].invert_yaxis()

# Add value labels
for bar, val in zip(bars, top15['prr']):
    axes[0].text(bar.get_width() + 0.3, bar.get_y() + bar.get_height()/2,
                f'{val:.1f}', va='center', fontsize=8)

# Plot 2: PRR vs N bubble chart
clinical = df_signals[df_signals['reaction_pt'] != 'no adverse event']
scatter = axes[1].scatter(clinical['drug_cases'], clinical['prr'],
                          s=clinical['chi2']*3, alpha=0.6,
                          c=clinical['prr'], cmap='YlOrRd')
axes[1].axhline(y=2, color='black', linestyle='--', alpha=0.5)
axes[1].set_xlabel('Number of Cases (N)', fontsize=11)
axes[1].set_ylabel('PRR', fontsize=11)
axes[1].set_title('PRR vs Case Count\\n(bubble size = χ² magnitude)', fontsize=11, fontweight='bold')
plt.colorbar(scatter, ax=axes[1], label='PRR')

# Label key points
for _, row in clinical[clinical['drug_cases'] > 10].iterrows():
    axes[1].annotate(row['reaction_pt'],
                    (row['drug_cases'], row['prr']),
                    fontsize=7, xytext=(5, 5),
                    textcoords='offset points')

plt.tight_layout()
plt.savefig(Path.home() / 'pv_workbench/output/cefiderocol_prr_chart.png',
            dpi=150, bbox_inches='tight')
plt.show()
print("Chart saved.")
"""))

# Clinical interpretation
cells.append(nbf.v4.new_markdown_cell("""## 5. Clinical Interpretation

### Key Signals — ICU Pharmacist Perspective

| MedDRA PT | N | PRR | Clinical Assessment |
|---|---|---|---|
| Pneumonia pseudomonal | 8 | 16.10 | **Expected** — cefiderocol's primary indication; confirms on-label use in resistant pseudomonal pneumonia |
| Treatment failure | 54 | 9.88 | **Clinically significant** — aligns with published RCTs showing non-inferiority concerns vs carbapenems in some subgroups |
| Death | 109 | 9.34 | **Confounding by indication** — reflects critically ill, last-resort patient population; not a de novo safety signal |
| Therapy non-responder | 11 | 17.71 | **Warrants monitoring** — may reflect emerging resistance; correlates with MIC creep literature |
| Ischaemic hepatitis | 3 | 24.16 | **Hypothesis-generating** — low N but high PRR; requires further evaluation against complete FAERS database |
| Complications of transplanted lung | 3 | 24.16 | **Population signal** — lung transplant recipients are a core cefiderocol use case; not unexpected |

### Methodological Limitations

1. **Confounding by indication**: Cefiderocol patients are inherently sicker than the meropenem reference population — high PRR for mortality-related PTs is expected and does not imply causality
2. **OpenFDA subset**: The API exposes a subset of total FAERS reports; a regulatory-grade analysis would use the complete quarterly ASCII files
3. **Reference population**: Meropenem was selected as a clinically relevant comparator; PRR values would differ with a broader background population
4. **Underreporting bias**: Standard FAERS limitation — actual event rates are higher than reported
5. **MedDRA coding variability**: Reporter coding practices affect PT-level analysis
"""))

# Regulatory context
cells.append(nbf.v4.new_markdown_cell("""## 6. Regulatory & Technical Context

### Pipeline Architecture
- **Data source**: OpenFDA FAERS API (REST/JSON)
- **Processing**: Python 3.12, containerized via Docker on Debian Linux
- **Signal method**: PRR with Evans' criteria (ICH E2C-aligned)
- **Reference**: Meropenem comparator population (n=5,000)
- **Output**: JSON signal file + formatted report

### Applicability to Vault Safety / Argus Workflows
This pipeline demonstrates the signal detection logic that underlies aggregate 
analysis modules in systems like Veeva Vault Safety and Oracle Argus. The PRR/ROR 
methodology implemented here is consistent with ICH E2E signal management guidance 
and maps directly to the quantitative signal detection workflows used in PSUR/PBRER 
preparation.
"""))

nb.cells = cells

output_path = os.path.expanduser("~/pv_workbench/output/cefiderocol_signal_analysis.ipynb")
with open(output_path, 'w') as f:
    nbf.write(nb, f)

print(f"Notebook generated: {output_path}")
