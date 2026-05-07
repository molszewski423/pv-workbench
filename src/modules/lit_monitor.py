"""
Module 5 — Literature Monitoring Agent

Scheduled PubMed and EMA feed monitoring. Fetches new publications,
filters for pharmacovigilance relevance, summarizes findings with
gemma4:e4b, and delivers signal digests via Telegram.

Schedule: configured via cron or Hermes scheduler (see Phase 4).
Default interval: weekly (aligned with GVP Module VI recommendations).

Implementation: Hermes Agent (Phase 2)
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date
import sys
from pathlib import Path
from Bio import Entrez
import asyncio
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
import os
import re

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import DRAFT_MODEL, OLLAMA_BASE_URL
from ingester.vault_ingester import query_vault
from discord_utils import send_discord_message

# PubMed search terms per drug — extend as new drugs are monitored
DEFAULT_SEARCH_TERMS: dict[str, list[str]] = {
    "cefiderocol": [
        "cefiderocol[tiab] AND (adverse[tiab] OR safety[tiab] OR pharmacovigilance[tiab])",
        "cefiderocol[tiab] AND (resistance[tiab] OR failure[tiab])",
    ],
    "vancomycin": [
        "vancomycin[tiab] AND nephrotoxicity[tiab]",
        "vancomycin[tiab] AND (AUC[tiab] OR \"area under the curve\"[tiab]) AND (monitoring[tiab] OR toxicity[tiab])",
        "vancomycin[tiab] AND (acute kidney injury[tiab] OR AKI[tiab] OR renal[tiab]) AND safety[tiab]",
        "vancomycin[tiab] AND (trough[tiab] OR pharmacokinetic[tiab]) AND (nephrotoxicity[tiab] OR toxicity[tiab])",
    ],
}

DIGEST_PROMPT = """\
You are summarizing pharmacovigilance literature for a senior clinical reviewer.
For each paper, provide:
- KEY FINDING: 1-2 sentences on the safety-relevant finding
- SIGNAL RELEVANCE: Supports / Refutes / Adds nuance / Unrelated to known signals
- ACTION: None / Monitor / Validate / Escalate

Be concise. Format each paper as:
PMID: <pmid>
KEY FINDING: <finding>
SIGNAL RELEVANCE: <assessment>
ACTION: <action>
---
"""


@dataclass
class LitResult:
    pmid: str
    title: str
    authors: str
    journal: str
    pub_date: str
    abstract: str
    relevance_score: float = 0.0
    summary: str = ""
    signal_relevance: str = ""
    action: str = "None"        # None / Monitor / Validate / Escalate


@dataclass
class LitDigest:
    drug_name: str
    search_date: str
    results: list[LitResult] = field(default_factory=list)
    escalations: list[LitResult] = field(default_factory=list)
    digest_text: str = ""


def search_pubmed(
    drug_name: str,
    days_back: int = 7,
    max_results: int = 50,
) -> list[LitResult]:
    """
    Query PubMed via Biopython Entrez for recent publications.
    """
    Entrez.email = "molszewski423@gmail.com"
    queries = DEFAULT_SEARCH_TERMS.get(drug_name.lower(), [f"{drug_name}[tiab] AND (adverse[tiab] OR safety[tiab])"])
    
    all_results = {}
    
    try:
        for query in queries:
            handle = Entrez.esearch(db="pubmed", term=query, reldate=days_back, datetype="pdat", retmax=max_results)
            record = Entrez.read(handle)
            handle.close()
            id_list = record["IdList"]
            
            if not id_list:
                continue
                
            handle = Entrez.efetch(db="pubmed", id=",".join(id_list), rettype="xml", retmode="xml")
            records = Entrez.read(handle)
            handle.close()
            
            for article in records.get("PubmedArticle", []):
                medline = article.get("MedlineCitation", {})
                pmid = str(medline.get("PMID", ""))
                if pmid in all_results:
                    continue
                
                article_data = medline.get("Article", {})
                title = article_data.get("ArticleTitle", "No Title")
                
                # Authors
                authors_list = article_data.get("AuthorList", [])
                author_names = []
                for author in authors_list:
                    last_name = author.get("LastName", "")
                    initials = author.get("Initials", "")
                    if last_name:
                        author_names.append(f"{last_name} {initials}")
                authors = ", ".join(author_names)
                
                # Journal
                journal = article_data.get("Journal", {}).get("Title", "Unknown Journal")
                
                # PubDate
                pub_date_data = article_data.get("Journal", {}).get("JournalIssue", {}).get("PubDate", {})
                year = pub_date_data.get("Year", "")
                month = pub_date_data.get("Month", "")
                day = pub_date_data.get("Day", "")
                pub_date = f"{year}-{month}-{day}".strip("-")
                
                # Abstract
                abstract_data = article_data.get("Abstract", {}).get("AbstractText", [])
                abstract = " ".join([str(a) for a in abstract_data])
                
                all_results[pmid] = LitResult(
                    pmid=pmid,
                    title=title,
                    authors=authors,
                    journal=journal,
                    pub_date=pub_date,
                    abstract=abstract
                )
    except Exception as e:
        print(f"Warning: PubMed search failed: {e}")
        return []

    return list(all_results.values())


def score_relevance(results: list[LitResult], drug_name: str) -> list[LitResult]:
    """
    Score each result for PV relevance using semantic similarity
    against the vault's signal notes for this drug.
    """
    for result in results:
        hits = query_vault(f"{result.title} {result.abstract[:200]}", n_results=3)
        result.relevance_score = round(1.0 - hits[0]["distance"], 3) if hits else 0.0
    
    results.sort(key=lambda x: x.relevance_score, reverse=True)
    return results


def generate_digest(drug_name: str, results: list[LitResult]) -> LitDigest:
    """
    Summarize filtered results and generate a signal digest with gemma4:e4b.
    """
    relevant_results = [r for r in results if r.relevance_score >= 0.6]
    if not relevant_results:
        relevant_results = results[:3]
    
    if not relevant_results:
        return LitDigest(drug_name=drug_name, search_date=str(date.today()), digest_text="No results found.")

    llm = ChatOllama(model=DRAFT_MODEL, base_url=OLLAMA_BASE_URL, temperature=0.1)
    prompt = ChatPromptTemplate.from_messages([
        ("system", DIGEST_PROMPT),
        ("human", "Drug: {drug_name}\nSearch date: {today}\nPapers to review ({n} of {total} results above relevance threshold):\n\n{papers}"),
    ])
    chain = prompt | llm | StrOutputParser()
    
    papers_text = ""
    for r in relevant_results:
        papers_text += f"PMID: {r.pmid}\nTitle: {r.title}\nAbstract: {r.abstract[:300]}\n\n"
    
    response = chain.invoke({
        "drug_name": drug_name,
        "today": str(date.today()),
        "n": len(relevant_results),
        "total": len(results),
        "papers": papers_text
    })
    
    # Parse response
    blocks = response.split("---")
    for block in blocks:
        pmid_match = re.search(r"PMID:\s*(\d+)", block)
        if pmid_match:
            pmid = pmid_match.group(1)
            finding_match = re.search(r"KEY FINDING:\s*(.+?)(?=SIGNAL RELEVANCE:|ACTION:|$)", block, re.S)
            relevance_match = re.search(r"SIGNAL RELEVANCE:\s*(.+?)(?=ACTION:|PMID:|$)", block, re.S)
            action_match = re.search(r"ACTION:\s*(.+?)(?=PMID:|---|$)", block, re.S)
            
            for r in results:
                if r.pmid == pmid:
                    if finding_match: r.summary = finding_match.group(1).strip()
                    if relevance_match: r.signal_relevance = relevance_match.group(1).strip()
                    if action_match: r.action = action_match.group(1).strip()
                    break
    
    digest_lines = []
    for r in results:
        if r.summary:
            digest_lines.append(f"**{r.title}** (PMID:{r.pmid})\n{r.summary}")
            
    digest = LitDigest(
        drug_name=drug_name,
        search_date=str(date.today()),
        results=results,
        escalations=[r for r in results if r.action == "Escalate"],
        digest_text="\n\n".join(digest_lines),
    )
    return digest


def send_discord_digest(digest: LitDigest, channel_name: str = "lit-monitor") -> bool:
    """
    Deliver digest to Discord. Escalated findings are formatted with
    a warning color and header. Returns True on successful delivery.
    """
    header = f"📚 **PV Literature Digest — {digest.drug_name} ({digest.search_date})**\n"
    header += f"{len(digest.results)} papers | {len(digest.escalations)} escalations\n\n"

    embed = {
        "title": f"Literature Digest: {digest.drug_name}",
        "description": digest.digest_text[:4000],
        "color": 0x9b59b6,
        "fields": []
    }

    if digest.escalations:
        embed["color"] = 0xe74c3c # Red for escalations
        esc_list = "\n".join([f"• {r.title} (PMID:{r.pmid})" for r in digest.escalations])
        embed["fields"].append({
            "name": "⚠️ ESCALATIONS REQUIRING REVIEW",
            "value": esc_list[:1024]
        })

    return send_discord_message(channel_name, content=header, embed=embed)
