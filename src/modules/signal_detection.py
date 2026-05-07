"""
Module 3 — FAERS Signal Detection

Wraps the existing PRR/chi² pipeline from pv_workbench/src/fda_api_client.py
and adds a gemma4:26b interpretation layer that translates statistical outputs
into plain-language clinical assessments with confounding analysis.

Signal criteria: Evans (PRR ≥ 2, N ≥ 3, chi² ≥ 4) — aligned with ICH E2E.
"""

from __future__ import annotations
import re
import sys
from pathlib import Path
from dataclasses import dataclass, field

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import REASON_MODEL, OLLAMA_BASE_URL

# fda_api_client is imported lazily inside run_signal_detection() — its module-level
# OUTPUT_DIR.mkdir() would fail if /app doesn't exist (outside Docker).
_PV_SRC = Path(__file__).parent.parent.parent.parent / "pv_workbench" / "src"

from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

INTERPRETATION_PROMPT = """\
You are a clinical pharmacovigilance analyst with expertise in FAERS
disproportionality analysis. You will receive PRR signal detection results
for a drug and must provide a clinical interpretation for each positive signal.

Evans criteria (PRR>=2, N>=3, chi2>=4) define a positive signal.

For each signal assess:
1. Whether it is expected given the drug's mechanism and indication
2. Whether confounding by indication is likely (especially mortality/ICU
   outcomes in last-resort antibiotics)
3. Whether it warrants regulatory action under ICH E2A
4. Recommended action: "expedited" (fatal/unexpected SUSAR), "routine"
   (non-urgent signal), "monitor" (low confidence, watch), or "none"

Output one block per reaction using EXACTLY this format:
REACTION: <reaction_pt>
ASSESSMENT: <1-2 sentence clinical assessment>
CONFOUNDING: <Yes / No>
ACTION: <expedited / routine / monitor / none>
NOTES: <any additional reviewer notes>
---"""


@dataclass
class SignalInterpretation:
    reaction_pt: str
    drug_cases: int
    prr: float
    chi2: float
    signal: bool
    clinical_assessment: str = ""
    confounding_likely: bool = False
    regulatory_action: str = ""      # "expedited" | "routine" | "monitor" | "none"
    reviewer_notes: str = ""


def _build_signal_table(positive_signals: list[dict]) -> str:
    rows = "\n".join(
        f"| {s['reaction_pt']} | {s['drug_cases']} | {s['prr']:.2f} | {s['chi2']:.1f} |"
        for s in positive_signals
    )
    return f"| Reaction PT | N | PRR | Chi² |\n|---|---|---|---|\n{rows}"


def _parse_interpretation_blocks(
    response: str,
    positive_signals: list[dict],
) -> dict[str, dict]:
    """
    Parse ---delimited response blocks into a dict keyed by reaction_pt.
    Fuzzy-matches REACTION: labels back to original signal keys.
    """
    valid_actions = {"expedited", "routine", "monitor", "none"}
    parsed: dict[str, dict] = {}

    blocks = re.split(r'\n---+\n?', response)
    for block in blocks:
        block = block.strip()
        if not block:
            continue

        def get(label: str) -> str:
            m = re.search(rf"^{label}:\s*(.+?)(?=\n[A-Z]+:|$)", block, re.M | re.S)
            return m.group(1).strip() if m else ""

        reaction_raw = get("REACTION").lower().strip()
        if not reaction_raw:
            continue

        # Match back to original signal — exact first, then partial
        matched_pt = None
        for s in positive_signals:
            if s["reaction_pt"].lower() == reaction_raw:
                matched_pt = s["reaction_pt"]
                break
        if matched_pt is None:
            for s in positive_signals:
                if reaction_raw in s["reaction_pt"].lower() or s["reaction_pt"].lower() in reaction_raw:
                    matched_pt = s["reaction_pt"]
                    break
        if matched_pt is None:
            continue

        action = get("ACTION").lower().split()[0] if get("ACTION") else "monitor"
        if action not in valid_actions:
            action = "monitor"

        parsed[matched_pt] = {
            "clinical_assessment": get("ASSESSMENT"),
            "confounding_likely": get("CONFOUNDING").lower().startswith("yes"),
            "regulatory_action": action,
            "reviewer_notes": get("NOTES"),
        }

    return parsed


def run_signal_detection(
    drug_name: str,
    comparator: str = "meropenem",
    max_bg_records: int = 5000,
    start_year: int | None = None,
    end_year: int | None = None,
) -> list[dict]:
    """
    Fetch FAERS reports and compute PRR/chi² signals.

    Args:
        drug_name:      Target drug name.
        comparator:     Background reference drug.
        max_bg_records: Cap on background report count.
        start_year:     First year to include (default: 2004).
        end_year:       Last year to include inclusive (default: current year).
    """
    import os, collections
    os.environ.setdefault("OUTPUT_DIR", str(Path.home() / "pv_workbench" / "output"))
    sys.path.insert(0, str(_PV_SRC))
    from fda_api_client import fetch_all_reports, extract_reactions, compute_prr, FAERS_START_YEAR

    fetch_kwargs: dict = {}
    if start_year is not None:
        fetch_kwargs["start_year"] = start_year
    if end_year is not None:
        fetch_kwargs["end_year"] = end_year

    print(f"Fetching {drug_name} reports{f' ({start_year}-{end_year})' if start_year or end_year else ''}...")
    drug_reports = fetch_all_reports(drug_name, **fetch_kwargs)
    print(f"Fetching {comparator} background (cap {max_bg_records})...")
    bg_reports = fetch_all_reports(comparator, max_records=max_bg_records, **fetch_kwargs)

    drug_reactions = collections.Counter(extract_reactions(drug_reports))
    bg_reactions = collections.Counter(extract_reactions(bg_reports))

    return compute_prr(drug_reactions, len(drug_reports), bg_reactions, len(bg_reports))


def interpret_signals(
    signals: list[dict],
    drug_name: str,
) -> list[SignalInterpretation]:
    """
    Run gemma4:26b clinical interpretation over PRR signal outputs.

    One LLM call batches all positive signals. Non-signal rows pass through
    with regulatory_action="none". Returns full list sorted by PRR descending.

    Args:
        signals:   Output of compute_prr() — list of signal dicts
        drug_name: Drug name for clinical context

    Returns:
        List of SignalInterpretation with clinical assessments for signal=True rows
    """
    positive = [s for s in signals if s["signal"]]
    lookup: dict[str, dict] = {}

    if positive:
        table = _build_signal_table(positive)
        human_msg = (
            f"Drug: {drug_name}\n"
            f"Background comparator: meropenem (n=5000)\n\n"
            f"Positive signals (Evans criteria met):\n{table}\n\n"
            f"Provide a clinical interpretation for each signal above."
        )

        llm = ChatOllama(model=REASON_MODEL, base_url=OLLAMA_BASE_URL, temperature=0)
        prompt = ChatPromptTemplate.from_messages([
            ("system", INTERPRETATION_PROMPT),
            ("human", "{input}"),
        ])
        chain = prompt | llm | StrOutputParser()
        response = chain.invoke({"input": human_msg})
        lookup = _parse_interpretation_blocks(response, positive)

    results: list[SignalInterpretation] = []
    for s in signals:
        interp = lookup.get(s["reaction_pt"], {})
        results.append(SignalInterpretation(
            reaction_pt=s["reaction_pt"],
            drug_cases=s["drug_cases"],
            prr=s["prr"],
            chi2=s["chi2"],
            signal=s["signal"],
            clinical_assessment=interp.get("clinical_assessment", ""),
            confounding_likely=interp.get("confounding_likely", False),
            regulatory_action=interp.get("regulatory_action", "none"),
            reviewer_notes=interp.get("reviewer_notes", ""),
        ))

    return sorted(results, key=lambda r: r.prr, reverse=True)


if __name__ == "__main__":
    import json
    import glob
    from pathlib import Path

    # Load latest cached signals rather than re-fetching
    output_dir = Path.home() / "pv_workbench" / "output"
    files = sorted(glob.glob(str(output_dir / "cefiderocol_signals_*.json")))
    if not files:
        print("No cached signal file found — run fda_api_client.py first")
        sys.exit(1)

    with open(files[-1]) as f:
        raw_signals = json.load(f)

    print(f"Loaded {len(raw_signals)} signals from {Path(files[-1]).name}")
    positive_count = sum(1 for s in raw_signals if s["signal"])
    print(f"Interpreting {positive_count} positive signals...\n")

    results = interpret_signals(raw_signals, "cefiderocol")

    for r in results:
        if not r.signal:
            continue
        print(f"\n{'='*60}")
        print(f"{r.reaction_pt.upper()}  (PRR={r.prr:.2f}, N={r.drug_cases}, chi²={r.chi2:.1f})")
        print(f"Assessment:  {r.clinical_assessment}")
        print(f"Confounding: {r.confounding_likely}  |  Action: {r.regulatory_action}")
        if r.reviewer_notes:
            print(f"Notes:       {r.reviewer_notes}")
