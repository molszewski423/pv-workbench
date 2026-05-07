# Task Spec: Module 3 — Signal Detection Interpretation Layer

## Objective

Implement `interpret_signals()` in `src/modules/signal_detection.py`.
The statistical pipeline (`run_signal_detection()`) is already working.
This task adds the LLM interpretation layer that translates PRR/chi² outputs
into plain-language clinical assessments.

## File to Edit

```
~/pv-workbench/src/modules/signal_detection.py
```

## Environment

```bash
cd ~/pv-workbench
source .venv/bin/activate
# All commands with:
PYTHONPATH=src python ...
```

## Current State

`run_signal_detection()` returns a list of dicts, each with:
```python
{
    "reaction_pt": str,   # MedDRA Preferred Term (lowercase)
    "drug_cases": int,    # N — number of cases for this drug+reaction
    "prr": float,         # Proportional Reporting Ratio
    "chi2": float,        # Chi-squared statistic
    "signal": bool,       # True if PRR>=2, N>=3, chi2>=4 (Evans criteria)
}
```

`interpret_signals()` currently raises `NotImplementedError`.

## What to Implement

```python
def interpret_signals(
    signals: list[dict],
    drug_name: str,
) -> list[SignalInterpretation]:
```

### SignalInterpretation dataclass (already defined — do not modify)

```python
@dataclass
class SignalInterpretation:
    reaction_pt: str
    drug_cases: int
    prr: float
    chi2: float
    signal: bool
    clinical_assessment: str = ""
    confounding_likely: bool = False
    regulatory_action: str = ""   # "expedited" | "routine" | "monitor" | "none"
    reviewer_notes: str = ""
```

## Implementation Requirements

### 1. Filter before prompting
Only pass `signal=True` rows to the LLM. Non-signal rows get a
`SignalInterpretation` with defaults and `regulatory_action="none"`.

### 2. Batch the prompt — do not call LLM per signal
Format all positive signals into a single prompt table. One LLM call
per `interpret_signals()` invocation.

### 3. Model
Use `REASON_MODEL` (`gemma4:26b`) from `config.py`.
`ChatOllama(model=REASON_MODEL, base_url=OLLAMA_BASE_URL, temperature=0)`

### 4. System prompt (use verbatim)

```
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
---
```

### 5. Human message format

```
Drug: {drug_name}
Background comparator: meropenem (n=5000)

Positive signals (Evans criteria met):
| Reaction PT | N | PRR | Chi² |
|---|---|---|---|
{table rows for signal=True only}

Provide a clinical interpretation for each signal above.
```

### 6. Parse the response

Split on `---` to get per-signal blocks. For each block extract:
- `REACTION:` → match back to the signal dict by `reaction_pt`
- `ASSESSMENT:` → `clinical_assessment`
- `CONFOUNDING:` → `confounding_likely` (True if "Yes")
- `ACTION:` → `regulatory_action` (lowercase, strip)
- `NOTES:` → `reviewer_notes`

Non-signal rows: construct `SignalInterpretation` with all defaults,
`regulatory_action="none"`.

Return the full list (signals + non-signals) sorted by PRR descending.

## Acceptance Criteria

Run this test and verify all assertions pass:

```bash
PYTHONPATH=src python tasks/test_module3.py
```

Create `tasks/test_module3.py`:
```python
import sys
sys.path.insert(0, "src")
from modules.signal_detection import SignalInterpretation, interpret_signals

# Minimal synthetic signals matching real cefiderocol output
mock_signals = [
    {"reaction_pt": "treatment failure", "drug_cases": 54, "prr": 9.88, "chi2": 312.1, "signal": True},
    {"reaction_pt": "death",             "drug_cases": 109, "prr": 9.34, "chi2": 801.2, "signal": True},
    {"reaction_pt": "rhinorrhoea",       "drug_cases": 7,  "prr": 1.1,  "chi2": 0.4,  "signal": False},
]

results = interpret_signals(mock_signals, "cefiderocol")

assert len(results) == 3, f"Expected 3 results, got {len(results)}"

sig_results = [r for r in results if r.signal]
assert len(sig_results) == 2, "Expected 2 signal=True results"

for r in sig_results:
    assert isinstance(r, SignalInterpretation)
    assert r.clinical_assessment, f"Empty assessment for {r.reaction_pt}"
    assert r.regulatory_action in ("expedited", "routine", "monitor", "none"), \
        f"Invalid action: {r.regulatory_action}"

non_sig = [r for r in results if not r.signal]
assert len(non_sig) == 1
assert non_sig[0].regulatory_action == "none"
assert non_sig[0].reaction_pt == "rhinorrhoea"

# Death in last-resort antibiotic should be flagged as confounding
death = next(r for r in results if r.reaction_pt == "death")
assert death.confounding_likely, "Death in cefiderocol should be confounding by indication"

print("All assertions passed.")
for r in sig_results:
    print(f"\n{r.reaction_pt.upper()} (PRR={r.prr}, N={r.drug_cases})")
    print(f"  Assessment: {r.clinical_assessment}")
    print(f"  Confounding: {r.confounding_likely} | Action: {r.regulatory_action}")
```

## Constraints

- Do NOT modify `run_signal_detection()` or the `SignalInterpretation` dataclass
- Do NOT modify `INTERPRETATION_PROMPT` constant — it is used by the Streamlit page
- One LLM call per `interpret_signals()` invocation (not per signal)
- All `SignalInterpretation` objects must be returned (signal and non-signal)
- `regulatory_action` must be one of: `"expedited"`, `"routine"`, `"monitor"`, `"none"`

## Integration

After implementation, the Streamlit page at
`src/dashboard/pages/3_Signal_Detection.py` will call `interpret_signals()`
automatically — the UI is already wired for it in Phase 3.

## Reference

The existing `INTERPRETATION_PROMPT` in `signal_detection.py` is a placeholder.
Replace its usage with the system prompt above (or update the constant to match).
Vault notes covering PRR interpretation are indexed in ChromaDB under
`Guidelines/Evans Criteria PRR Signal Detection.md`.
