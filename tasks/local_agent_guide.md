# Local Coding Agent Guide

How to delegate development tasks to Hermes/Gemma 4 26B locally, reducing dependence on Claude Code and Gemini CLI.

---

## Quick Start

```bash
# Interactive session with full pv-workbench context
bash scripts/local_agent.sh

# One-shot task (prints result, non-interactive)
bash scripts/local_agent.sh "Fix the relevance threshold in lit_monitor.py to use 0.5 instead of 0.6"
```

---

## When to Use Which Agent

| Task Type | Use | Notes |
|---|---|---|
| Add/edit a vault note | **Hermes/Gemma 4** | Straightforward; runs benchmark to verify |
| Fix a bug in a module | **Hermes/Gemma 4** | Well-specified bugs work well |
| Implement from a task spec | **Hermes/Gemma 4** | Point at tasks/*.md file |
| Update a dashboard page | **Hermes/Gemma 4** | Streamlit UI changes are well within scope |
| New module architecture | **Claude Code** | Requires broad context + design judgment |
| Cross-module refactoring | **Claude Code** | Multi-file coherence is Claude's strength |
| Statistical methodology | **Claude Code** | PRR/chi² decisions need domain awareness |
| Security/compliance review | **Claude Code** | Regulatory and privacy considerations |
| Large-context doc auditing | **Gemini CLI** | 1M token window useful for full codebase scan |

**Rule of thumb**: If you can write a clear spec (what to change, where, why), Hermes can implement it. If the task requires deciding *what* to build or requires understanding the full system's constraints, use Claude Code.

---

## Structuring Tasks for Best Local LLM Performance

Hermes/Gemma 4 performs best with:

1. **Specific file targets** — "Edit `src/modules/lit_monitor.py` line 171" beats "fix the relevance issue"
2. **Test verification** — "After editing, run `PYTHONPATH=src python tasks/test_module5.py` and confirm all assertions pass"
3. **Explicit constraints** — List what NOT to change (e.g., "do not modify the LitResult or LitDigest dataclasses")
4. **Acceptance criteria** — "The function should return True if channel found, False otherwise"

### Good task spec example:
```
Read src/modules/lit_monitor.py.
In score_relevance(), change the relevance threshold from 0.6 to 0.5 in generate_digest().
After editing, run: PYTHONPATH=src python tasks/test_module5.py
Confirm the test passes and the change is minimal (no other modifications).
Commit: git add src/modules/lit_monitor.py && git commit -m "Lower relevance threshold to 0.5 in generate_digest"
```

---

## Validating Local Agent Output

After any local agent task:

1. **Review the diff**: `git diff` or `git show` — never accept large unexplained changes
2. **Run the relevant test**: `PYTHONPATH=src python tasks/test_module<N>.py`
3. **Run the benchmark**: `PYTHONPATH=src python tests/benchmark/run_benchmark.py` — verify P@5 still 100%
4. **Check for regressions**: Import all 5 modules and verify no import errors
5. **Smoke test the dashboard**: `PYTHONPATH=src streamlit run src/dashboard/app.py`

---

## Hermes CLI Reference

```bash
# Interactive session
hermes --skills pv-workbench

# One-shot with Gemma 4
hermes --skills pv-workbench -m gemma4-stable:latest -z "task description"

# Load context file explicitly
hermes --skills pv-workbench -z "$(cat tasks/hermes-master-prompt.md)

Your task: [task here]"

# Continue a previous session
hermes --continue [session-name]
```

---

## Honest Capability Assessment (as of 2026-05-06)

### What local agents (Hermes + Gemma 4 26B) can do as well as Claude Code:
- Implement well-specified module functions from task specs
- Fix clearly-described bugs in isolated files
- Add vault notes and verify benchmark passes
- Update Streamlit pages given clear UI requirements
- Run tests and iterate on assertion failures
- Write git commits

### What they can do adequately with supervision:
- Multi-file changes (risk of missing downstream effects)
- Debugging subtle logic errors (may need multiple iterations)
- Following architectural patterns across the codebase
- Updating documentation to match code changes

### What still requires Claude Code or Gemini CLI:
- New module design from scratch (architectural judgment)
- Cross-module refactoring with coherence guarantees
- Statistical correctness review (PRR/chi² methodology)
- Security review of token handling and API access
- Large-context audits of the full codebase
- Resolving conflicts between system components

### Current Local Agent Gaps (2026-05-06):
- **Qwen3 30B not pulled** — `ollama pull qwen3:30b` needed for coding-specialized tasks
- **MedGemma 27B not pulled** — `ollama pull medgemma:27b` needed for medical NLP
- **Hermes gateway is stopped** — Discord gateway intentionally disabled (Argus takes Discord)
- **No automated test runner** — Hermes must be explicitly told to run tests; no CI
- **Context window**: Gemma 4 26B has 256K context; very large files may need chunking

### Recommended workflow going forward:
```
Routine task → Hermes + Gemma 4 26B via scripts/local_agent.sh
Complex architecture → Claude Code (brief session, focused)
Large codebase audit → Gemini CLI (1M context window)
Production verification → Human review + test suite
```

---

## Models to Pull for Full Local Stack

```bash
# Code-specialized reasoning
ollama pull qwen3:30b

# Medical entity extraction and MedDRA coding
ollama pull medgemma:27b
```

Note: Both models at 16GB fit within 16GB VRAM; running simultaneously requires system RAM offloading.
