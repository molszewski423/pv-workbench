"""
Module 4 — ICSR Narrative Generator

Drafts E2B(R3)-aligned Individual Case Safety Report narratives using
gemma4:e4b (prose/drafting model). The narrative is structured for
senior clinical review before submission.

Output follows ICH E2B(R3) narrative conventions:
- Patient demographics and medical history
- Drug exposure (dose, indication, dates)
- Adverse event description and course
- Outcome and causality assessment
- Reporter information

All outputs are DRAFTS — mandatory senior reviewer sign-off before submission.

Implementation: Hermes Agent (Phase 2)
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date
import sys
from pathlib import Path

from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import DRAFT_MODEL, OLLAMA_BASE_URL

NARRATIVE_PROMPT = """\
You are drafting an E2B(R3)-compliant ICSR narrative for senior clinical review.
Write in third person, past tense, clinical prose. Be precise and factual.
Do not infer or extrapolate beyond the information provided.

Structure the narrative as:
1. Patient: age, sex, weight if available, relevant medical history
2. Drug exposure: suspect drug, dose, route, indication, dates
3. Concomitant medications (if provided)
4. Adverse event: onset, description, clinical course, laboratory findings
5. Treatment of adverse event and outcome
6. Causality assessment: reporter's assessment (do not add your own)
7. Additional information (de-challenge, re-challenge if applicable)

End with: "This narrative is a DRAFT for senior clinical pharmacovigilance review."
"""


@dataclass
class CaseData:
    """Structured input for ICSR narrative generation."""
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
    reporter_type: str = ""     # HCP, Consumer, Regulatory authority
    country: str = ""


@dataclass
class ICSRDraft:
    case_data: CaseData
    narrative: str
    meddra_pts: list[str] = field(default_factory=list)
    seriousness_criteria: list[str] = field(default_factory=list)
    expectedness: str = ""      # Expected / Unexpected per SmPC
    is_draft: bool = True       # Always True — requires senior sign-off


def generate_icsr_narrative(case_data: CaseData) -> ICSRDraft:
    """
    Draft an E2B(R3)-compliant narrative from structured case data.

    Args:
        case_data: Structured CaseData with all available case details

    Returns:
        ICSRDraft marked as requiring senior clinical reviewer sign-off
    """
    seriousness_criteria = assess_seriousness(case_data)
    
    lines = []
    weight_str = f", {case_data.patient_weight}" if case_data.patient_weight else ""
    if case_data.patient_age or case_data.patient_sex or weight_str:
        lines.append(f"Patient: {case_data.patient_age}-year-old {case_data.patient_sex}{weight_str}")
    if case_data.medical_history:
        lines.append(f"Medical history: {case_data.medical_history}")
    if case_data.suspect_drug:
        lines.append(f"Suspect drug: {case_data.suspect_drug}, {case_data.dose}, {case_data.route}, indication: {case_data.indication}")
    if case_data.start_date or case_data.stop_date:
        lines.append(f"Exposure: {case_data.start_date} to {case_data.stop_date}")
    if case_data.concomitant_meds:
        lines.append(f"Concomitant medications: {', '.join(case_data.concomitant_meds)}")
    if case_data.adverse_event:
        lines.append(f"Adverse event: {case_data.adverse_event}")
    if case_data.event_onset:
        lines.append(f"Onset: {case_data.event_onset}")
    if case_data.clinical_course:
        lines.append(f"Clinical course: {case_data.clinical_course}")
    if case_data.outcome:
        lines.append(f"Outcome: {case_data.outcome}")
    if case_data.reporter_causality:
        lines.append(f"Reporter causality: {case_data.reporter_causality}")
    if case_data.reporter_type:
        lines.append(f"Reporter type: {case_data.reporter_type}")
    if case_data.country:
        lines.append(f"Country: {case_data.country}")

    human_message = "\n".join(lines)
    
    llm = ChatOllama(model=DRAFT_MODEL, base_url=OLLAMA_BASE_URL, temperature=0.1)
    prompt = ChatPromptTemplate.from_messages([
        ("system", NARRATIVE_PROMPT),
        ("human", "{human_message}"),
    ])
    chain = prompt | llm | StrOutputParser()
    
    response = chain.invoke({"human_message": human_message})
    
    return ICSRDraft(
        case_data=case_data,
        narrative=response,
        seriousness_criteria=seriousness_criteria,
        is_draft=True
    )


def assess_seriousness(case_data: CaseData) -> list[str]:
    """
    Apply ICH E2A seriousness criteria to case data.

    Returns list of applicable seriousness criteria:
    ["death", "life-threatening", "hospitalization", "disability",
     "congenital-anomaly", "medically-important"]
    """
    outcome = case_data.outcome.lower()
    ae = case_data.adverse_event.lower()
    criteria = []

    if any(k in outcome for k in ["fatal", "death", "died"]):
        criteria.append("death")
    if any(k in outcome for k in ["life-threatening", "life threatening"]):
        criteria.append("life-threatening")
    if "hospitali" in outcome or "hospitali" in ae:
        criteria.append("hospitalization")
    if any(k in outcome for k in ["disab", "permanent", "irreversible"]):
        criteria.append("disability")
    if any(k in ae for k in ["congenital", "birth defect", "fetal"]):
        criteria.append("congenital-anomaly")

    if not criteria and ae.strip():
        criteria.append("medically-important")

    return criteria
