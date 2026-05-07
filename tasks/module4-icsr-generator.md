# Task Spec: Module 4 — ICSR Narrative Generator

## Objective

Implement two functions in `src/modules/icsr_generator.py`:
1. `assess_seriousness(case_data)` — rule-based, no LLM
2. `generate_icsr_narrative(case_data)` — gemma4:e4b narrative draft

## File to Edit

`~/pv-workbench/src/modules/icsr_generator.py`

## Activate Environment

```bash
cd ~/pv-workbench && source .venv/bin/activate
```

## Existing Definitions (do not modify)

```python
@dataclass
class CaseData:
    patient_age: str = ""
    patient_sex: str = ""
    patient_weight: str = ""
    medical_history: str = ""
    suspect_drug: str = ""
    dose: str = ""
    route: str = ""
    indication: str = ""
    start_date: str = ""
    stop_date: str = ""
    concomitant_meds: list[str] = field(default_factory=list)
    adverse_event: str = ""
    event_onset: str = ""
    clinical_course: str = ""
    outcome: str = ""
    reporter_causality: str = ""
    reporter_type: str = ""
    country: str = ""

@dataclass
class ICSRDraft:
    case_data: CaseData
    narrative: str
    meddra_pts: list[str] = field(default_factory=list)
    seriousness_criteria: list[str] = field(default_factory=list)
    expectedness: str = ""
    is_draft: bool = True   # NEVER set to False
```

## Function 1: assess_seriousness (rule-based, no LLM)

```python
def assess_seriousness(case_data: CaseData) -> list[str]:
```

Apply ICH E2A criteria to `case_data.outcome` and `case_data.adverse_event`.
Return a list containing any applicable strings from:
`["death", "life-threatening", "hospitalization", "disability", "congenital-anomaly", "medically-important"]`

Rules (keyword matching on outcome + adverse_event, case-insensitive):
- `"death"` → outcome contains "fatal", "death", "died"
- `"life-threatening"` → outcome contains "life-threatening", "life threatening"
- `"hospitalization"` → outcome contains "hospitali", or adverse_event contains "hospitali"
- `"disability"` → outcome contains "disab", "permanent", "irreversible"
- `"congenital-anomaly"` → adverse_event contains "congenital", "birth defect", "fetal"
- `"medically-important"` → if none of the above match AND adverse_event is non-empty, add this as a fallback for reviewer to adjudicate

Return `[]` if no case_data fields are populated.

## Function 2: generate_icsr_narrative

```python
def generate_icsr_narrative(case_data: CaseData) -> ICSRDraft:
```

### Model
`DRAFT_MODEL` (`gemma4:e4b`) — prose/drafting model
`ChatOllama(model=DRAFT_MODEL, base_url=OLLAMA_BASE_URL, temperature=0.1)`
(Slight temperature for narrative flow — not 0 like reasoning modules.)

### System prompt (use verbatim from NARRATIVE_PROMPT constant already in the file)

The constant already exists. Use it as the system message.

### Human message format

Build from CaseData fields. Only include lines where the field is non-empty:

```
Patient: {age}-year-old {sex}{weight_str}
Medical history: {medical_history}
Suspect drug: {suspect_drug}, {dose}, {route}, indication: {indication}
Exposure: {start_date} to {stop_date}
Concomitant medications: {', '.join(concomitant_meds)}
Adverse event: {adverse_event}
Onset: {event_onset}
Clinical course: {clinical_course}
Outcome: {outcome}
Reporter causality: {reporter_causality}
Reporter type: {reporter_type}
Country: {country}
```

### Steps

1. Call `assess_seriousness(case_data)` to populate `seriousness_criteria`
2. Build human message from non-empty CaseData fields
3. Invoke `NARRATIVE_PROMPT | llm | StrOutputParser()`
4. Return `ICSRDraft(case_data=case_data, narrative=response, seriousness_criteria=..., is_draft=True)`
   - `meddra_pts`: leave as `[]` (MedDRA coding is Module 2's responsibility)
   - `expectedness`: leave as `""` (requires SmPC comparison — reviewer adjudicates)

### Constraint

`is_draft` must always be `True`. Never set it to `False` under any condition.

## Acceptance Test

Create and run `tasks/test_module4.py`:

```python
import sys
sys.path.insert(0, "src")
from modules.icsr_generator import CaseData, ICSRDraft, assess_seriousness, generate_icsr_narrative

# Test 1: assess_seriousness (no LLM)
case_fatal = CaseData(adverse_event="septic shock", outcome="Patient died on day 7")
criteria = assess_seriousness(case_fatal)
assert "death" in criteria, f"Expected 'death' in criteria, got {criteria}"

case_hosp = CaseData(adverse_event="acute kidney injury", outcome="Hospitalized for 5 days")
criteria2 = assess_seriousness(case_hosp)
assert "hospitalization" in criteria2, f"Expected 'hospitalization', got {criteria2}"

case_empty = CaseData()
assert assess_seriousness(case_empty) == []

print("assess_seriousness: all assertions passed")

# Test 2: generate_icsr_narrative (LLM)
case = CaseData(
    patient_age="68", patient_sex="Male",
    medical_history="Type 2 diabetes, CKD stage 3",
    suspect_drug="cefiderocol", dose="2g IV q8h", route="intravenous",
    indication="Carbapenem-resistant Acinetobacter pneumonia",
    start_date="2026-04-10", stop_date="2026-04-17",
    concomitant_meds=["meropenem 2g IV q8h (prior)", "vancomycin 1.5g IV q12h"],
    adverse_event="Acute liver failure with jaundice",
    event_onset="Day 5 of treatment",
    clinical_course="LFTs elevated 10x ULN by day 5; drug discontinued; slow improvement over 2 weeks",
    outcome="Recovering — not fully resolved at time of report",
    reporter_causality="Possibly related",
    reporter_type="Physician",
    country="United States",
)

draft = generate_icsr_narrative(case)

assert isinstance(draft, ICSRDraft)
assert draft.is_draft is True, "is_draft must always be True"
assert len(draft.narrative) > 100, "Narrative too short"
assert "cefiderocol" in draft.narrative.lower(), "Suspect drug missing from narrative"
assert "DRAFT" in draft.narrative.upper(), "Draft disclaimer missing from narrative"

print("generate_icsr_narrative: all assertions passed")
print(f"\nNarrative ({len(draft.narrative)} chars):\n")
print(draft.narrative)
print(f"\nSeriousness criteria: {draft.seriousness_criteria}")
```

Run: `PYTHONPATH=src python tasks/test_module4.py`
