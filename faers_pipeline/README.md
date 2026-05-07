# FAERS Signal Detection Pipeline

Original cefiderocol pipeline — the starting point for the PV AI Workbench.

Three Python scripts, Docker-containerized, querying OpenFDA FAERS and computing PRR/chi² disproportionality statistics for adverse event signal detection.

## What It Does

1. **`src/fda_api_client.py`** — Fetches FAERS adverse event reports using quarterly date-range partitioning (bypasses OpenFDA's 5000-result/query cap), computes PRR and chi² against a meropenem comparator, and writes a signal JSON.

2. **`src/generate_report.py`** — Reads the signal JSON and generates a self-contained HTML report with an embedded base64 PRR chart.

3. **`src/generate_notebook.py`** — Reads the signal JSON and builds a Jupyter notebook with code cells and signal visualizations.

## Statistical Rigor

Three production-grade adjustments over a naive PRR implementation:

| Fix | Problem Solved |
|---|---|
| **Artifact exclusion** — 12 administrative FAERS PTs filtered | Removes non-adverse-event records (`"no adverse event"`, `"drug ineffective"`, etc.) that inflate false signals |
| **Continuity correction** — b=0 uses b=0.5 | Preserves novel drug-specific signals instead of silently discarding reactions with zero background |
| **Yates' chi² correction** — applied when any expected cell < 5 | Reduces false positives from small-sample disproportionality, common for new drugs |

Signal threshold: **Evans criteria** — PRR ≥ 2.0 AND N ≥ 3 AND χ² ≥ 4.0 (all three required)

## Run

```bash
# Docker (recommended — no dependency conflicts)
docker build -t faers-pipeline .
docker run --rm -v $(pwd)/output:/app/output faers-pipeline

# Local Python 3.12+
pip install requests
python src/fda_api_client.py

# Generate report from signal JSON
pip install matplotlib pandas scipy
python src/generate_report.py    # → output/cefiderocol_report.html
python src/generate_notebook.py  # → output/cefiderocol_signal_analysis.ipynb
```

## Cefiderocol Output

See `output/` for the actual pipeline run results. The HTML report and notebook are pre-generated and viewable without running the pipeline.
