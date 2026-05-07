import os
import requests
import json
import time
from collections import Counter
from pathlib import Path
from datetime import datetime, date

DRUG_NAME = "cefiderocol"
API_BASE = "https://api.fda.gov/drug/event.json"
LIMIT = 100
MAX_BG_REPORTS = 5000
FAERS_START_YEAR = 2004
OUTPUT_DIR = Path(os.environ.get("OUTPUT_DIR", "/app/output"))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Known FAERS data quality artifacts — exclude from all signal analyses.
# These are administrative/process PTs, not true adverse drug reactions.
ARTIFACT_PTS = frozenset({
    "no adverse event",
    "off label use",
    "drug ineffective",
    "product quality issue",
    "intentional product use issue",
    "drug use for unknown indication",
    "inappropriate schedule of drug administration process",
    "expired product administered",
    "wrong technique in drug usage process",
    "product substitution issue",
    "condition aggravated",             # non-specific, rarely actionable
    "therapeutic response unexpected",  # overlap with drug ineffective
})

_QUARTER_RANGES = {
    1: ("0101", "0331"),
    2: ("0401", "0630"),
    3: ("0701", "0930"),
    4: ("1001", "1231"),
}


def _fetch_page(search_term: str, skip: int) -> tuple[list, int]:
    """Single FAERS API page fetch. Returns (results, total_count)."""
    params = {"search": search_term, "limit": LIMIT, "skip": skip}
    try:
        r = requests.get(API_BASE, params=params, timeout=15)
    except requests.RequestException as e:
        print(f"  Network error: {e}")
        return [], 0
    if r.status_code == 404:
        return [], 0
    if r.status_code != 200:
        print(f"  API error {r.status_code}")
        return [], 0
    data = r.json()
    total = data.get("meta", {}).get("results", {}).get("total", 0)
    return data.get("results", []), total


def _fetch_quarter(drug_name: str, year: int, quarter: int) -> list:
    """
    Fetch all FAERS reports for one calendar quarter.

    Quarterly partitioning bypasses the OpenFDA hard cap of 5000 results
    per search query (skip cannot exceed ~4900). Each quarter is a separate
    search with a date range filter on receivedate.
    """
    start, end = _QUARTER_RANGES[quarter]
    search = (
        f'patient.drug.medicinalproduct:"{drug_name}"'
        f' AND receivedate:[{year}{start} TO {year}{end}]'
    )
    reports, total = _fetch_page(search, 0)
    if not reports:
        return []

    skip = LIMIT
    # FAERS hard cap per query is ~5000 — stay under it; quarterly partitioning
    # keeps each quarter well below this limit for all but the most-reported drugs.
    while skip < min(total, 4900):
        batch, _ = _fetch_page(search, skip)
        if not batch:
            break
        reports.extend(batch)
        skip += LIMIT
        time.sleep(0.25)

    return reports


def fetch_all_reports(
    drug_name: str,
    max_records: int | None = None,
    start_year: int = FAERS_START_YEAR,
) -> list:
    """
    Fetch FAERS adverse event reports using quarterly date-range partitioning.

    The OpenFDA API caps results at 5000 per search via the skip parameter.
    Partitioning by calendar quarter keeps each sub-query well under the cap
    while still returning the full dataset. Results are deduplicated across
    quarters by safetyreportid.

    Args:
        drug_name:   Drug name as indexed in FAERS medicinalproduct field.
        max_records: Hard cap on total records returned (None = fetch all).
        start_year:  First year to query (FAERS data starts 2004).
    """
    seen_ids: set[str] = set()
    all_reports: list = []
    today = date.today()
    current_quarter = (today.month - 1) // 3 + 1

    for year in range(start_year, today.year + 1):
        max_q = current_quarter if year == today.year else 4
        for q in range(1, max_q + 1):
            if max_records and len(all_reports) >= max_records:
                print(f"  Capped at {max_records} records")
                return all_reports

            batch = _fetch_quarter(drug_name, year, q)
            added = 0
            for rep in batch:
                rid = rep.get("safetyreportid", "")
                if rid not in seen_ids:
                    seen_ids.add(rid)
                    all_reports.append(rep)
                    added += 1

            if added:
                print(f"  {year}-Q{q}: +{added} reports (total {len(all_reports)})")

            time.sleep(0.1)

    return all_reports


def extract_reactions(reports: list) -> list[str]:
    reactions = []
    for case in reports:
        try:
            pts = [
                r["reactionmeddrapt"].strip().lower()
                for r in case["patient"]["reaction"]
                if "reactionmeddrapt" in r
            ]
            reactions.extend(pts)
        except (KeyError, TypeError):
            continue
    return reactions


def compute_prr(
    drug_reactions: Counter,
    total_drug: int,
    background_reactions: Counter,
    total_bg: int,
    min_cases: int = 3,
) -> list[dict]:
    """
    Compute Proportional Reporting Ratio (PRR) with Evans chi-square signal detection.

    Statistical adjustments applied:
    - Artifact exclusion: FAERS administrative PTs in ARTIFACT_PTS are skipped.
    - Continuity correction: b=0 (reaction unseen in background) uses b=0.5
      instead of being discarded. This preserves novel drug-specific signals.
    - Yates' chi-square correction: applied when any expected cell count < 5,
      reducing false positives from small-sample disproportionality.

    Signal threshold (Evans criteria): PRR >= 2.0 AND N >= 3 AND chi² >= 4.0

    Returns:
        List of signal dicts sorted by PRR descending. Each dict includes:
        reaction_pt, drug_cases, background_cases, prr, chi2,
        continuity_corrected (bool), signal (bool).
    """
    signals = []

    for pt, a in drug_reactions.items():
        if pt in ARTIFACT_PTS:
            continue
        if a < min_cases:
            continue

        b = background_reactions.get(pt, 0)
        c = total_drug - a
        d = total_bg - b

        if c <= 0 or d <= 0:
            continue

        # Continuity correction: substitute 0.5 when background count is zero.
        # Without this, b=0 reactions are silently dropped, losing signals for
        # drug-specific reactions not yet observed in the comparator.
        continuity_corrected = b == 0
        b_adj = 0.5 if b == 0 else float(b)
        d_adj = float(total_bg) - b_adj  # maintain column total consistency

        prr = (a / total_drug) / (b_adj / total_bg)

        # 2×2 contingency table (corrected values)
        n = float(a) + b_adj + float(c) + d_adj
        e_a = (a + b_adj) * (a + c) / n
        e_b = (a + b_adj) * (b_adj + d_adj) / n
        e_c = (c + d_adj) * (a + c) / n
        e_d = (c + d_adj) * (b_adj + d_adj) / n
        expected = [e_a, e_b, e_c, e_d]
        observed = [float(a), b_adj, float(c), d_adj]

        # Yates' correction reduces chi² inflation when expected cell counts are
        # small (< 5), which is common for novel drugs with limited FAERS data.
        use_yates = min(e for e in expected if e > 0) < 5
        if use_yates:
            chi2 = sum(
                max(abs(o - e) - 0.5, 0.0) ** 2 / e
                for o, e in zip(observed, expected)
                if e > 0
            )
        else:
            chi2 = sum(
                (o - e) ** 2 / e
                for o, e in zip(observed, expected)
                if e > 0
            )

        signals.append({
            "reaction_pt": pt,
            "drug_cases": a,
            "background_cases": b,
            "prr": round(prr, 3),
            "chi2": round(chi2, 2),
            "continuity_corrected": continuity_corrected,
            "signal": prr >= 2.0 and a >= 3 and chi2 >= 4.0,
        })

    return sorted(signals, key=lambda x: x["prr"], reverse=True)


def main():
    print(f"\n=== OpenFDA FAERS Pipeline: {DRUG_NAME.upper()} ===\n")

    print("[1/3] Fetching cefiderocol reports (quarterly partitioning)...")
    drug_reports = fetch_all_reports(DRUG_NAME)
    print(f"  Total: {len(drug_reports)} reports\n")
    if not drug_reports:
        print("No reports found.")
        return

    print(f"[2/3] Fetching meropenem background (capped at {MAX_BG_REPORTS})...")
    bg_reports = fetch_all_reports("meropenem", max_records=MAX_BG_REPORTS)

    drug_reactions = Counter(extract_reactions(drug_reports))
    bg_reactions = Counter(extract_reactions(bg_reports))
    signals = compute_prr(drug_reactions, len(drug_reports), bg_reactions, len(bg_reports))

    detected = sum(1 for s in signals if s["signal"])
    corrected = sum(1 for s in signals if s["signal"] and s["continuity_corrected"])
    print(f"\n  PRR signals detected: {detected} ({corrected} with continuity correction)")

    print("\n[3/3] Top 10 Reactions by PRR:")
    print(f"{'Reaction PT':<40} {'N':>5} {'BG':>6} {'PRR':>7} {'Chi²':>7} {'Signal':>8}")
    print("-" * 82)
    for s in signals[:10]:
        bg_str = f"{s['background_cases']}†" if s["continuity_corrected"] else str(s["background_cases"])
        flag = "YES*" if s["signal"] and s["continuity_corrected"] else ("YES" if s["signal"] else "-")
        print(f"{s['reaction_pt']:<40} {s['drug_cases']:>5} {bg_str:>6} {s['prr']:>7.2f} {s['chi2']:>7.2f} {flag:>8}")

    print("\n† b=0.5 continuity correction applied  * Evans criteria met with correction")

    ts = datetime.now().strftime("%Y%m%d_%H%M")
    out = OUTPUT_DIR / f"cefiderocol_signals_{ts}.json"
    with open(out, "w") as f:
        json.dump(signals, f, indent=2)
    print(f"\nSaved: {out}")


if __name__ == "__main__":
    main()
