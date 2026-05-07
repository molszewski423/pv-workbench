# Hermes Master Orchestration Prompt — PV AI Workbench

Paste this into a Hermes session to give Gemma 4 full context for autonomous
workbench completion. Update the STATUS section each session.

---

## Context

You are implementing the **PV AI Workbench** — a local-LLM pharmacovigilance
platform at `~/pv-workbench/`. The workbench is designed to support a PV
consultant workflow across multiple client drugs running in parallel.

**Clinical oversight model:** All AI outputs are DRAFTS. The human reviewer
(PharmD, BCPS, BCCCP, 18 years ICU) provides clinical judgment and sign-off.
Never remove or bypass the `is_draft=True` / `reviewer_flag=True` fields.

**Skill available:** Load the `pv-workbench` skill before starting work.
It contains full architecture, environment setup, and module-specific
implementation patterns.

---

## Environment

```bash
cd ~/pv-workbench
source .venv/bin/activate
# All module commands:
PYTHONPATH=src python ...
```

Python 3.11 venv. Key packages: `chromadb 1.5.9`, `langchain 1.2.17`,
`langchain-ollama`, `langchain-chroma`, `streamlit`, `ollama`, `biopython`,
`python-telegram-bot`.

---

## Model Assignments

| Task | Model | Config key |
|---|---|---|
| Regulatory Q&A, MedDRA, Signal interpretation | `gemma4:26b` | `REASON_MODEL` |
| ICSR narratives, Literature digests | `gemma4:e4b` | `DRAFT_MODEL` |
| Embeddings | `nomic-embed-text` | `EMBED_MODEL` |

All served by Ollama at `http://127.0.0.1:11434`. Config in `src/config.py`.

---

## Architecture

```
vault/Guidelines/        → shared regulatory knowledge (6 notes, 97 chunks)
vault/Drugs/<Drug>/      → per-drug notes (signals, cases, literature)
chroma_db/               → ChromaDB persistent store
  collection: pv_vault   → Guidelines chunks (shared)
  collection: pv_<drug>  → per-drug chunks (separate per ProjectConfig)
src/
  config.py              → paths, model names, chunk sizes
  projects.py            → ProjectConfig dataclass, multi-drug management
  ingester/
    chunker.py           → header-aware markdown chunker
    vault_ingester.py    → ingest_vault(), query_vault()
  modules/
    regulatory_qa.py     ✅ COMPLETE — answer_regulatory_question()
    meddra_coder.py      ✅ COMPLETE — suggest_meddra_pt()
    signal_detection.py  ✅ COMPLETE — run_signal_detection(), interpret_signals()
    icsr_generator.py    🔨 TODO — assess_seriousness(), generate_icsr_narrative()
    lit_monitor.py       🔨 TODO — search_pubmed(), score_relevance(), generate_digest(), send_telegram_digest()
  dashboard/
    app.py               ← Streamlit entry point (update project selector)
    pages/               ← one page per module
tasks/
  module4-icsr-generator.md    ← full spec for icsr_generator.py
  module5-lit-monitor.md       ← full spec for lit_monitor.py
  test_module4.py              ← create and run to verify module 4
  test_module5.py              ← create and run to verify module 5
```

---

## Current Status (update each session)

| Item | Status |
|---|---|
| Phase 1: Environment + vault + benchmark | ✅ Complete (100% P@5) |
| Module 1: Regulatory Q&A | ✅ Complete |
| Module 2: MedDRA Coder | ✅ Complete |
| Module 3: Signal Detection interpretation | ✅ Complete |
| Module 4: ICSR Generator | 🔨 Spec written — implement next |
| Module 5: Lit Monitor | 🔨 Spec written — implement after 4 |
| Dashboard: project selector + module wiring | 🔨 After modules complete |
| Multi-drug project layer | ✅ `src/projects.py` complete — ProjectConfig, load/save/list |
| GitHub portfolio publication | ✅ README.md written (Mermaid arch diagram, signal spotlight) |

---

## Implementation Order for This Session

### Step 1 — Implement Module 4 (ICSR Generator)

Read: `tasks/module4-icsr-generator.md`
Edit: `src/modules/icsr_generator.py`
Test: `PYTHONPATH=src python tasks/test_module4.py`

Key constraints:
- `assess_seriousness()` is rule-based, no LLM
- `generate_icsr_narrative()` uses `DRAFT_MODEL` (gemma4:e4b), temperature=0.1
- `is_draft=True` always — never override
- Narrative must contain "DRAFT" (the NARRATIVE_PROMPT already enforces this)

### Step 2 — Implement Module 5 (Literature Monitor)

Read: `tasks/module5-lit-monitor.md`
Edit: `src/modules/lit_monitor.py`
Test: `PYTHONPATH=src python tasks/test_module5.py`

Key constraints:
- Always set `Entrez.email = "molszewski423@gmail.com"` before any PubMed call
- Telegram credentials from env vars only: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`
- `send_telegram_digest()` returns False gracefully if credentials missing
- One LLM call in `generate_digest()` — batch all papers, not one call per paper

### Step 3 — Shared State Mechanism

Create: `src/shared_state.py`
Establish a simple JSON-backed state for the active project and pipeline statuses.
- `get_active_drug()` / `set_active_drug(name)`
- `get_pipeline_status(name)` / `set_pipeline_status(name, status)`

### Step 4 — Argus Intent Router (Gemma 4 26B)

Edit: `src/argus_bot.py`
1. **Intelligent Router**: Enhance `_route_message` to use `gemma4:26b` for intent classification if the channel-based route is ambiguous or a general query is received.
2. **MedGemma Integration**: If intent is clinical entity extraction, route to `medgemma:27b` (requires `ollama pull medgemma:27b`).
3. **Route Logging**: Log every dispatch to the `#workbench-status` channel with an embed showing:
   - User Input
   - Detected Intent
   - Assigned Model
   - Processing Status
4. **Hermes Trigger**: If intent is a pipeline action (e.g. "run signal"), trigger the corresponding module function and update shared state.

### Step 5 — Wire dashboard pages to implemented modules

Update all pages in `src/dashboard/pages/` to call the completed module functions.
Ensure `st.session_state` reads from `src/shared_state.py` to sync with Discord actions.

### Step 6 — Add project selector to dashboard

Edit `src/dashboard/app.py`:
- Sync project selection with `src/shared_state.py`.

---

## Drug-Agnostic Design Rules (apply to all module work)

1. **No hardcoded drug names** — always use `drug_name` parameter or `ProjectConfig.drug_name`
2. **Configurable comparator** — always use `ProjectConfig.comparator`, default `"meropenem"`
3. **Per-drug ChromaDB collection** — use `ProjectConfig.collection_name` for drug-specific notes
4. **Shared Guidelines collection** — `pv_vault` is shared; always query it for regulatory Q&A
5. **Per-drug vault folder** — drug-specific notes go in `vault/Drugs/<DrugName>/`
6. **Parameterized PubMed queries** — use `ProjectConfig.pubmed_terms` list

---

## Verification After All Modules Complete

```bash
# Benchmark still passes
PYTHONPATH=src python tests/benchmark/run_benchmark.py
# Target: P@5=100%, MRR>=0.85

# All module acceptance tests pass
PYTHONPATH=src python tasks/test_module4.py
PYTHONPATH=src python tasks/test_module5.py

# Dashboard launches without errors
PYTHONPATH=src streamlit run src/dashboard/app.py
```

---

## What NOT to Do

- Do not modify `SignalInterpretation`, `CaseData`, `ICSRDraft`, `MedDRACodingSuggestion` dataclasses
- Do not set `is_draft=False` or `reviewer_flag=False` (except when model confidence=High + explicit No)
- Do not hardcode drug names, API keys, or file paths (use config.py / projects.py / env vars)
- Do not call LLM once per item — always batch (one call per function invocation)
- Do not import `fda_api_client` at module level (it runs `OUTPUT_DIR.mkdir()` which fails outside Docker)
 Docker)
o not hardcode drug names, API keys, or file paths (use config.py / projects.py / env vars)
- Do not call LLM once per item — always batch (one call per function invocation)
- Do not import `fda_api_client` at module level (it runs `OUTPUT_DIR.mkdir()` which fails outside Docker)
