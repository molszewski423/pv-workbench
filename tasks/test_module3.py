import sys
sys.path.insert(0, "src")
from modules.signal_detection import SignalInterpretation, interpret_signals

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

death = next(r for r in results if r.reaction_pt == "death")
assert death.confounding_likely, "Death in cefiderocol should be flagged as confounding by indication"

print("All assertions passed.\n")
for r in sig_results:
    print(f"{r.reaction_pt.upper()} (PRR={r.prr}, N={r.drug_cases})")
    print(f"  Assessment:  {r.clinical_assessment}")
    print(f"  Confounding: {r.confounding_likely} | Action: {r.regulatory_action}")
    if r.reviewer_notes:
        print(f"  Notes:       {r.reviewer_notes}")
    print()
