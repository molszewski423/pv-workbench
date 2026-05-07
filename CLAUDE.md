# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project: PV AI Workbench

A local-LLM-powered clinical pharmacovigilance platform built for portfolio demonstration and real PV workflow support. The system uses an AI Junior Analyst / Senior Reviewer oversight model — AI identifies patterns, retrieves guidelines, and drafts outputs; the human reviewer (PharmD, BCPS, BCCCP, 18 years ICU) provides clinical judgment and regulatory sign-off.

**Two repos coexist:**
- `~/pv_workbench/` (underscore) — original FAERS pipeline (3 scripts, working, Docker-containerized)
- `~/pv-workbench/` (hyphen, this repo) — full multi-module workbench being built

## Hardware & Model Stack

| Layer | Detail |
|---|---|
| GPU | RTX 5060 Ti 16 GB VRAM |
| RAM | 32 GB system |
| LLM serving | Ollama @ `http://127.0.0.1:11434` |
| Reasoning model | `gemma4:26b` (256K context, Thinking Mode) — signal analysis, MedDRA deliberation, regulatory Q&A |
| Drafting model | `gemma4:e4b` — ICSR narratives, literature digests, prose |
| Embedding model | `nomic-embed-text` — vault RAG |
| Hermes Agent | Gemma4-based, complex tool calls, handles module implementation in Phase 2 |

## Environment Setup

```bash
# Create venv (use Python 3.11 — chromadb may not have py3.13 wheels)
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Pull embedding model (required before ingestion)
ollama pull nomic-embed-text
```

## Key Commands

```bash
# Ingest vault into ChromaDB
PYTHONPATH=src python -m ingester.vault_ingester

# Query vault (CLI)
PYTHONPATH=src python -m ingester.vault_ingester --query "Evans PRR criteria" --n 5

# Run 30-question retrieval benchmark
PYTHONPATH=src python tests/benchmark/run_benchmark.py

# Launch Streamlit dashboard
PYTHONPATH=src streamlit run src/dashboard/app.py

# Run original FAERS pipeline (in pv_workbench repo)
OUTPUT_DIR=~/pv_workbench/output python3 ~/pv_workbench/src/fda_api_client.py
```

## Project Structure

```
pv-workbench/
├── vault/                    # Obsidian knowledge base
│   ├── .obsidian/
│   └── Guidelines/           # ICH E2A, E2B(R3), E2E, GVP VI, Evans, MedDRA
├── src/
│   ├── config.py             # Central config: paths, model names, chunk sizes
│   ├── ingester/
│   │   ├── chunker.py        # Header-aware markdown chunker (strips wikilinks)
│   │   └── vault_ingester.py # Vault → ChromaDB pipeline + query_vault()
│   ├── modules/
│   │   ├── regulatory_qa.py  # Module 1: RAG Q&A over guidelines
│   │   ├── meddra_coder.py   # Module 2: Thinking Mode PT suggestions
│   │   ├── signal_detection.py # Module 3: PRR/ROR + LLM interpretation
│   │   ├── icsr_generator.py # Module 4: E2B(R3) narrative drafting
│   │   └── lit_monitor.py    # Module 5: PubMed + Telegram digest
│   └── dashboard/
│       ├── app.py            # Streamlit entry point
│       └── pages/            # One page per module (auto-discovered)
├── chroma_db/                # Persistent ChromaDB (gitignored)
├── tests/benchmark/
│   ├── gold_standard_qa.json # 30 PV questions with expected source notes
│   └── run_benchmark.py      # Reports precision@5 and MRR
├── requirements.txt
└── .gitignore
```

## Architecture: How the RAG Pipeline Works

1. **Ingestion** (`vault_ingester.py`): walks `vault/**/*.md`, parses frontmatter with `python-frontmatter`, chunks by H1/H2/H3 headers via `chunker.py`, strips `[[wikilinks]]`, upserts to ChromaDB with metadata (source_note, folder, section_header, tags). IDs are SHA-256 of `path::chunk_index` — re-ingestion is idempotent.

2. **Retrieval** (`query_vault()`): ChromaDB semantic search with `nomic-embed-text` embeddings, optional folder filter, returns top-k chunks with source metadata and distance scores.

3. **Generation** (Phase 2 modules): each module builds a prompt from retrieved chunks + system instructions, calls Ollama via LangChain, and returns a structured response requiring senior reviewer sign-off.

## Five Modules — Status

| Module | Model | Status | Notes |
|---|---|---|---|
| 1. Regulatory Q&A | gemma4:26b | ✅ Complete | Tested, jurisdiction filtering added |
| 2. MedDRA Coder | gemma4:26b | ✅ Complete | 3 scenarios validated; reviewer_flag logic patched |
| 3. Signal Detection | gemma4:26b + PRR | ✅ Complete | `interpret_signals()` done; FAERS statistical fixes applied |
| 4. ICSR Generator | gemma4:e4b | ✅ Complete | E2B(R3) draft narratives; validated with `test_module4.py` |
| 5. Lit Monitor | gemma4:e4b + PubMed | ✅ Complete | Discord delivery; validated with `test_module5.py` |

## Build Strategy (4-Week Plan)

- **Phase 1** ✅ — Environment, vault (184 chunks), ChromaDB, benchmark 100% P@5
- **Phase 2** ✅ — Module implementation (All 1-5 done)
- **Phase 3** 🔨 — End-to-end integration testing with real PV cases (Discord + Dashboard)
- **Phase 4** — Streamlit dashboard polish, Discord notifications, GitHub portfolio publication

## Clinical Oversight Model

All AI outputs are **DRAFTS requiring explicit senior reviewer sign-off** before any regulatory use. The system never makes final clinical or regulatory determinations. This is enforced by design in all module interfaces and UI pages.

## Vault Knowledge Base

Six structured notes covering core PV regulatory framework (in `vault/Guidelines/`):
- `ICH E2A - Clinical Safety Data.md` — ICSR criteria, seriousness, expedited timelines
- `ICH E2B(R3) - Electronic Transmission.md` — data elements, narrative requirements
- `ICH E2E - Pharmacovigilance Planning.md` — signal management, PSUR, RMP
- `EMA GVP Module VI - Signal Management.md` — EU signal process, PRAC, EudraVigilance
- `Evans Criteria PRR Signal Detection.md` — PRR formula, thresholds, biases
- `MedDRA Coding Conventions.md` — hierarchy, PT selection rules, common decisions

All notes use frontmatter with `tags` and `source` fields, and Obsidian `[[wikilinks]]` for cross-references. The ingester handles both.

## Session Handoff — 2026-05-05 (Final Phase 2 Completion)

### Completed in this Session (Gemini CLI)

**1. Phase 2 Module Completion**:
- **Module 4 (ICSR Generator)**: Fully implemented in `src/modules/icsr_generator.py`. Includes rule-based seriousness assessment and `gemma4:e4b` narrative drafting. Verified with `tasks/test_module4.py`.
- **Module 5 (Lit Monitor)**: Fully implemented in `src/modules/lit_monitor.py`. PubMed search, semantic relevance scoring, and digest generation are active. Verified with `tasks/test_module5.py`.

**2. Argus "Intelligent Router" Upgrade**:
- **Intent Detection**: Upgraded `src/argus_bot.py` to use `gemma4:26b` for dynamic intent classification.
- **Auto-Routing**: Messages are now routed to specific modules (REGULATORY_QA, MEDDRA_CODING, SIGNAL_DETECTION, ICSR_GENERATION, LIT_MONITOR) or handled as general reasoning queries based on content, regardless of channel.
- **Route Logging**: Every request now logs an embed to `#workbench-status` showing the input, detected intent, and the model (Gemma4 26B or 4B) assigned.

**3. Shared State & Synchronization**:
- **Shared State Engine**: Created `src/shared_state.py` (JSON-backed).
- **Interface Sync**: The active drug and pipeline status are now synchronized between the Streamlit dashboard and Discord. `!drug <name>` in Discord updates the Streamlit sidebar instantly.
- **Dashboard Wiring**: All 5 Streamlit pages are fully wired to backend modules. The "Phase 2 Pending" placeholders have been removed.

**4. Discord Refactor (Telegram Removal)**:
- **Discord Alerts**: Created `src/discord_utils.py` for direct REST API communication.
- **Alert Delivery**: Literature digests and safety escalations are now delivered to the `#lit-monitor` Discord channel instead of Telegram.
- **Cleanup**: `python-telegram-bot` removed from `requirements.txt`.

**5. System Launch Readiness**:
- **Start Scripts**: `scripts/argus_start.sh` and `scripts/argus_stop.sh` handle the Hermes gateway conflict automatically.
- **Dashboard Port**: Streamlit configured to run on `localhost:8501`.

### Current State
- **Modules 1-5**: ✅ 100% Functional
- **Benchmark**: ✅ 100% P@5 (verified after vault expansion)
- **Interfaces**: ✅ Streamlit + Discord (Synced)
- **Voice/STT**: ✅ Active in Argus Bot

### Next Priorities for Next Session
1. **Phase 3 Integration Testing**: Execute complex clinical workflows (e.g., "Receive signal alert -> Verify MedDRA -> Draft ICSR") to ensure prompt stability.
2. **MedGemma Routing**: `ollama pull medgemma:27b` and add the specialized route for clinical entity extraction.
3. **Statistical Refinement**: Implement the "Universal Continuity Correction" (0.5 to all cells) and quarterly truncation warnings in `fda_api_client.py` as identified in the audit.
4. **Automation**: Transition from manual triggers to Phase 4 scheduled monitoring.

## Key Domain Concepts

- **PRR**: `(a/(a+c)) / (b/(b+d))` — disproportionality signal statistic
- **Evans criteria**: PRR ≥ 2 AND N ≥ 3 AND chi² ≥ 4 (all required simultaneously)
- **SUSAR**: Suspected Unexpected Serious Adverse Reaction — triggers expedited reporting
- **MedDRA PT**: Preferred Term — the coding level for regulatory adverse event reporting
- **E2B(R3)**: ICH standard for electronic ICSR submission (HL7 ICSR v3 XML)
- **Confounding by indication**: Last-resort drugs show high PRR for mortality not due to drug toxicity but patient severity
- **`"no adverse event"` PT**: Known FAERS data quality artifact — filter from all visualizations
