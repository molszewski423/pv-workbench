"""
Module 1 — Regulatory Document Q&A

RAG pipeline over the Guidelines/ vault folder using gemma4:26b.
Retrieves relevant chunks from ChromaDB, constructs a cited prompt, returns
an answer with source references for senior reviewer validation.
"""

from __future__ import annotations
import re
from dataclasses import dataclass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import REASON_MODEL, TOP_K, OLLAMA_BASE_URL
from ingester.vault_ingester import query_vault

from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

SYSTEM_PROMPT = """\
You are a regulatory pharmacovigilance expert. Answer based solely on the
provided guideline context. Cite the source document and section for every
claim. If the context is insufficient, state that explicitly — do not
extrapolate beyond what is provided.

Format your answer as:
ANSWER: <concise authoritative answer>
CITATIONS: <source note + section for each claim>
CONFIDENCE: <High / Medium / Low, with one-sentence rationale>"""


@dataclass
class RegulatoryAnswer:
    question: str
    answer: str
    citations: list[str]
    confidence: str
    retrieved_chunks: list[dict]


def _build_context(hits: list[dict]) -> str:
    return "\n\n---\n\n".join(
        f"[{h['source_note']} › {h['section_header']}]\n{h['text']}"
        for h in hits
    )


def _parse_response(response: str) -> tuple[str, list[str], str]:
    """Extract ANSWER, CITATIONS, CONFIDENCE blocks from model output."""
    answer = ""
    citations: list[str] = []
    confidence = ""

    answer_m = re.search(r"ANSWER:\s*(.+?)(?=CITATIONS:|CONFIDENCE:|$)", response, re.S)
    if answer_m:
        answer = answer_m.group(1).strip()

    citations_m = re.search(r"CITATIONS:\s*(.+?)(?=CONFIDENCE:|$)", response, re.S)
    if citations_m:
        raw = citations_m.group(1).strip()
        citations = [line.lstrip("•-– ").strip() for line in raw.splitlines() if line.strip()]

    confidence_m = re.search(r"CONFIDENCE:\s*(.+)", response, re.S)
    if confidence_m:
        confidence = confidence_m.group(1).strip()

    # Fallback: if parsing failed, return full response as answer
    if not answer:
        answer = response.strip()

    return answer, citations, confidence


def answer_regulatory_question(
    question: str,
    n_context: int = TOP_K,
    folder: str = "Guidelines",
) -> RegulatoryAnswer:
    """
    Retrieve guideline chunks and generate a cited regulatory answer.

    Args:
        question:  Natural-language regulatory question
        n_context: Number of chunks to retrieve
        folder:    Vault subfolder to restrict retrieval (default "Guidelines")

    Returns:
        RegulatoryAnswer with answer text, citations, and source chunks
    """
    hits = query_vault(question, n_results=n_context, folder=folder)
    context = _build_context(hits)

    llm = ChatOllama(model=REASON_MODEL, base_url=OLLAMA_BASE_URL, temperature=0)
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        ("human", "Guideline context:\n\n{context}\n\nQuestion: {question}"),
    ])
    chain = prompt | llm | StrOutputParser()

    response = chain.invoke({"context": context, "question": question})
    answer, citations, confidence = _parse_response(response)

    return RegulatoryAnswer(
        question=question,
        answer=answer,
        citations=citations,
        confidence=confidence,
        retrieved_chunks=hits,
    )


if __name__ == "__main__":
    import sys
    q = " ".join(sys.argv[1:]) or "What are the expedited reporting timelines for SUSARs under ICH E2A?"
    print(f"Q: {q}\n")
    result = answer_regulatory_question(q)
    print(f"ANSWER:\n{result.answer}\n")
    print(f"CITATIONS:\n" + "\n".join(f"  • {c}" for c in result.citations))
    print(f"\nCONFIDENCE: {result.confidence}")
    print(f"\nSources retrieved:")
    for h in result.retrieved_chunks:
        print(f"  [{h['distance']:.3f}] {h['source_note']} › {h['section_header']}")
