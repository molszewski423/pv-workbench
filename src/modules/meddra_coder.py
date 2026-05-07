"""
Module 2 — MedDRA Coding Assistant

Uses gemma4:26b to deliberate on clinical narrative text before suggesting
Preferred Terms. The model reasons through differential MedDRA terms, SOC
hierarchy, and coding conventions before committing to a suggestion.

All outputs are DRAFTS — final coding decisions require senior reviewer sign-off.
"""

from __future__ import annotations
import re
from dataclasses import dataclass, field
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import REASON_MODEL, OLLAMA_BASE_URL
from ingester.vault_ingester import query_vault

from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

SYSTEM_PROMPT = """\
You are a MedDRA coding specialist. Given a clinical narrative or verbatim
adverse event description, suggest the most appropriate MedDRA Preferred Term(s).

Think through your reasoning step by step:
1. Identify all distinct clinical events in the narrative
2. Consider alternative PTs for each event
3. Apply LLT → PT → HLT → HLGT → SOC hierarchy logic
4. Flag any ambiguity or terms requiring regulatory confirmation

Output format (use these exact labels):
VERBATIM: <the term or phrase being coded>
PRIMARY_PT: <most appropriate Preferred Term>
SOC: <System Organ Class>
ALTERNATIVE_PTS: <comma-separated alternatives, or None>
CODING_NOTES: <rationale and coding conventions applied>
CONFIDENCE: <High / Medium / Low>
REVIEWER_FLAG: <Yes / No>"""


@dataclass
class MedDRACodingSuggestion:
    verbatim: str
    primary_pt: str
    soc: str
    alternative_pts: list[str] = field(default_factory=list)
    coding_notes: str = ""
    confidence: str = ""
    reviewer_flag: bool = True  # Always True — senior sign-off required


def _get_coding_context(verbatim: str) -> str:
    """Retrieve relevant MedDRA coding conventions from vault."""
    hits = query_vault(verbatim, n_results=3, folder="Guidelines")
    relevant = [h for h in hits if "MedDRA" in h["source_note"]]
    if not relevant:
        relevant = hits[:2]
    return "\n\n---\n\n".join(
        f"[{h['source_note']} › {h['section_header']}]\n{h['text']}"
        for h in relevant
    )


def _parse_response(response: str, verbatim_input: str) -> MedDRACodingSuggestion:
    """Parse structured output blocks into MedDRACodingSuggestion."""

    def extract(label: str) -> str:
        m = re.search(rf"{label}:\s*(.+?)(?=\n[A-Z_]{{3,}}:|$)", response, re.S)
        return m.group(1).strip() if m else ""

    verbatim    = extract("VERBATIM") or verbatim_input
    primary_pt  = extract("PRIMARY_PT")
    soc         = extract("SOC")
    alts_raw    = extract("ALTERNATIVE_PTS")
    coding_notes = extract("CODING_NOTES")
    confidence  = extract("CONFIDENCE")
    flag_raw    = extract("REVIEWER_FLAG")

    alternative_pts = []
    if alts_raw and alts_raw.lower() not in ("none", "n/a", ""):
        alternative_pts = [a.strip() for a in alts_raw.split(",") if a.strip()]

    # Reviewer flag is True unless model says No AND confidence is High
    reviewer_flag = not (flag_raw.strip().lower() == "no" and confidence.lower().startswith("high"))

    return MedDRACodingSuggestion(
        verbatim=verbatim,
        primary_pt=primary_pt,
        soc=soc,
        alternative_pts=alternative_pts,
        coding_notes=coding_notes,
        confidence=confidence,
        reviewer_flag=reviewer_flag,
    )


def suggest_meddra_pt(
    narrative: str,
    verbatim_term: str | None = None,
) -> MedDRACodingSuggestion:
    """
    Suggest a MedDRA Preferred Term for a clinical narrative or verbatim term.

    Retrieves relevant coding conventions from the vault, then prompts
    gemma4:26b to reason through the MedDRA hierarchy before committing
    to a suggestion.

    Args:
        narrative:     Full case narrative or adverse event description
        verbatim_term: Specific verbatim term to code (uses narrative if None)

    Returns:
        MedDRACodingSuggestion — always requires senior reviewer sign-off
    """
    term_to_code = verbatim_term or narrative
    context = _get_coding_context(term_to_code)

    human_msg = (
        f"MedDRA coding conventions (for reference):\n\n{context}\n\n"
        f"Narrative: {narrative}"
    )
    if verbatim_term and verbatim_term != narrative:
        human_msg += f"\n\nVerbatim term to code: {verbatim_term}"

    llm = ChatOllama(model=REASON_MODEL, base_url=OLLAMA_BASE_URL, temperature=0)
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        ("human", "{input}"),
    ])
    chain = prompt | llm | StrOutputParser()
    response = chain.invoke({"input": human_msg})

    return _parse_response(response, term_to_code)


if __name__ == "__main__":
    import sys

    cases = [
        ("Patient reported sudden difficulty breathing and chest tightness 30 minutes after drug administration.",
         "difficulty breathing and chest tightness"),
        ("Elevated liver enzymes with jaundice noted on day 5 of treatment.", None),
        ("The drug didn't work for the patient's infection.", "drug didn't work"),
    ]

    q_arg = " ".join(sys.argv[1:])
    if q_arg:
        cases = [(q_arg, None)]

    for narrative, verbatim in cases:
        print(f"\n{'='*60}")
        print(f"Narrative: {narrative}")
        if verbatim:
            print(f"Verbatim:  {verbatim}")
        result = suggest_meddra_pt(narrative, verbatim)
        print(f"\nPRIMARY_PT:      {result.primary_pt}")
        print(f"SOC:             {result.soc}")
        print(f"ALTERNATIVES:    {', '.join(result.alternative_pts) or 'None'}")
        print(f"CONFIDENCE:      {result.confidence}")
        print(f"REVIEWER_FLAG:   {result.reviewer_flag}")
        print(f"CODING_NOTES:\n  {result.coding_notes}")
