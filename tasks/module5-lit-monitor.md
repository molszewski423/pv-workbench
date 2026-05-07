# Task Spec: Module 5 — Literature Monitoring Agent

## Objective

Implement four functions in `src/modules/lit_monitor.py`:
1. `search_pubmed()` — Biopython Entrez query
2. `score_relevance()` — semantic scoring via query_vault
3. `generate_digest()` — gemma4:e4b summarization
4. `send_telegram_digest()` — Telegram bot delivery

## File to Edit

`~/pv-workbench/src/modules/lit_monitor.py`

## Activate Environment

```bash
cd ~/pv-workbench && source .venv/bin/activate
```

## Existing Definitions (do not modify)

```python
DEFAULT_SEARCH_TERMS: dict[str, list[str]]  # PubMed queries per drug

@dataclass
class LitResult:
    pmid: str; title: str; authors: str; journal: str; pub_date: str; abstract: str
    relevance_score: float = 0.0; summary: str = ""; signal_relevance: str = ""
    action: str = "None"  # None | Monitor | Validate | Escalate

@dataclass
class LitDigest:
    drug_name: str; search_date: str
    results: list[LitResult] = field(default_factory=list)
    escalations: list[LitResult] = field(default_factory=list)
    digest_text: str = ""
```

## Function 1: search_pubmed

```python
def search_pubmed(drug_name: str, days_back: int = 7, max_results: int = 50) -> list[LitResult]:
```

Use `Bio.Entrez` (biopython is installed). **Always set `Entrez.email`** before any call.

```python
from Bio import Entrez
Entrez.email = "molszewski423@gmail.com"
```

Steps:
1. Get search query: `DEFAULT_SEARCH_TERMS.get(drug_name.lower(), [f"{drug_name}[tiab] AND (adverse[tiab] OR safety[tiab])"])`
2. For each query string, call `Entrez.esearch(db="pubmed", term=query, reldate=days_back, datetype="pdat", retmax=max_results)`
3. Fetch records: `Entrez.efetch(db="pubmed", id=",".join(id_list), rettype="xml", retmode="xml")`
4. Parse XML with `Entrez.read()` to extract: PMID, ArticleTitle, AuthorList, Journal/Title, PubDate, AbstractText
5. Deduplicate by PMID across multiple queries
6. Return list of `LitResult` objects (relevance_score=0.0 at this stage)

Handle network errors with try/except — return empty list on failure, print warning.

## Function 2: score_relevance

```python
def score_relevance(results: list[LitResult], drug_name: str) -> list[LitResult]:
```

For each result, use `query_vault()` to score semantic relevance:

```python
from ingester.vault_ingester import query_vault
hits = query_vault(f"{result.title} {result.abstract[:200]}", n_results=3)
# relevance_score = 1 - min(distance) across hits (lower distance = more relevant)
result.relevance_score = round(1.0 - hits[0]["distance"], 3) if hits else 0.0
```

Sort results by `relevance_score` descending. Return the modified list.

## Function 3: generate_digest

```python
def generate_digest(drug_name: str, results: list[LitResult]) -> LitDigest:
```

### Filter before prompting
Only pass results with `relevance_score >= 0.6` to the LLM.
If none meet the threshold, pass top-3 by score regardless.

### Model
`DRAFT_MODEL` (`gemma4:e4b`)
`ChatOllama(model=DRAFT_MODEL, base_url=OLLAMA_BASE_URL, temperature=0.1)`

### System prompt
```
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
```

### Human message
```
Drug: {drug_name}
Search date: {today}
Papers to review ({n} of {total} results above relevance threshold):

{for each result: PMID, Title, Abstract[:300]}
```

### Parse response
Split on `---`. For each block extract PMID, KEY FINDING → `summary`,
SIGNAL RELEVANCE → `signal_relevance`, ACTION → `action`.
Match back to `LitResult` by PMID. Update in place.

### Build LitDigest
```python
from datetime import date
digest = LitDigest(
    drug_name=drug_name,
    search_date=str(date.today()),
    results=results,
    escalations=[r for r in results if r.action == "Escalate"],
    digest_text="\n\n".join(f"**{r.title}** (PMID:{r.pmid})\n{r.summary}" for r in results if r.summary),
)
```

## Function 4: send_discord_digest

```python
def send_discord_digest(digest: LitDigest, channel_name: str = "lit-monitor") -> bool:
```

Use `discord_utils.send_discord_message` to deliver the digest to the specified channel.

Steps:
1. Format a header with drug name and paper counts.
2. Build a Discord embed with the digest text.
3. If escalations exist, set color to red and list them in a dedicated field.
4. Call `send_discord_message` and return success status.

## Acceptance Test

Update `tasks/test_module5.py` to test `send_discord_digest` instead of `send_telegram_digest`.

Run: `PYTHONPATH=src python tasks/test_module5.py`

## Notes

- Telegram credentials are never hardcoded — always from environment variables
- `send_telegram_digest` is safe to call with empty `bot_token` — return False gracefully
- The weekly schedule (Phase 4) will be configured via Hermes cron, not implemented here
