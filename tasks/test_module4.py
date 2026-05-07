import sys
import os
from pathlib import Path

# Add src to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

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
