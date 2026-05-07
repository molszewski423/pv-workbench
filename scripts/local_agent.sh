#!/usr/bin/env bash
# Local Coding Agent Launcher — Hermes + Gemma 4 26B
#
# Launches Hermes as a local coding agent for ~/pv-workbench tasks.
# Provides full project context (CLAUDE.md + michael_context.md) and
# tool access matching Claude Code: file read/write, bash, tests, git.
#
# Usage:
#   bash scripts/local_agent.sh              — interactive session
#   bash scripts/local_agent.sh "task desc"  — launch with task pre-loaded
#
# Replaces Claude Code / Gemini CLI for:
#   - Module updates and bug fixes
#   - Vault note additions and benchmark re-runs
#   - Streamlit page updates
#   - Routine maintenance tasks
#
# Escalate to Claude Code for:
#   - New module architecture
#   - Cross-module refactoring
#   - Statistical methodology decisions
#   - Security or regulatory compliance review

set -euo pipefail

WORKBENCH="$HOME/pv-workbench"
HERMES="$HOME/.hermes/hermes-agent/venv/bin/python"
VENV="$WORKBENCH/.venv"

# ── Environment setup ─────────────────────────────────────────────────────────
cd "$WORKBENCH"

# Load env vars (Ollama, Discord, etc.)
if [ -f "$HOME/.hermes/.env" ]; then
    set -a
    # shellcheck disable=SC1090
    source <(grep -v '^#' "$HOME/.hermes/.env" | grep -v '^$' | grep '=')
    set +a
fi

# Activate workbench venv so Python imports work in tool calls
export VIRTUAL_ENV="$VENV"
export PATH="$VENV/bin:$PATH"
export PYTHONPATH="$WORKBENCH/src"

# ── Context injection ─────────────────────────────────────────────────────────
CONTEXT_FILE="$WORKBENCH/src/context/michael_context.md"
CLAUDE_MD="$WORKBENCH/CLAUDE.md"
MASTER_PROMPT="$WORKBENCH/tasks/hermes-master-prompt.md"

# Build session context preamble
PREAMBLE="$(cat <<'PREAMBLE_END'
You are acting as a coding agent for the PV AI Workbench at ~/pv-workbench/.

CRITICAL RULES:
1. Read CLAUDE.md before any code changes — it has architecture constraints
2. Activate .venv before running Python: source .venv/bin/activate
3. Run all Python with: PYTHONPATH=src python ...
4. Never remove is_draft=True or reviewer_flag=True from any module
5. No hardcoded drug names — always parameterize
6. After any module change, verify: PYTHONPATH=src python tasks/test_module<N>.py
7. Commit changes via git with descriptive messages

Load the pv-workbench skill for full architecture context.
PREAMBLE_END
)"

echo "============================================================"
echo "  PV Workbench Local Coding Agent"
echo "  Model: gemma4-stable (Gemma 4 26B via Ollama)"
echo "  Skill: pv-workbench"
echo "  Working dir: $WORKBENCH"
echo "============================================================"
echo ""
echo "Context loaded:"
[ -f "$CLAUDE_MD" ] && echo "  ✓ CLAUDE.md"
[ -f "$CONTEXT_FILE" ] && echo "  ✓ michael_context.md"
[ -f "$MASTER_PROMPT" ] && echo "  ✓ hermes-master-prompt.md"
echo ""

# ── Launch Hermes ─────────────────────────────────────────────────────────────
if [ -n "${1:-}" ]; then
    # One-shot mode: inject full context + task into the prompt
    FULL_PROMPT="$(cat "$CLAUDE_MD")

## Michael's Profile
$(cat "$CONTEXT_FILE" 2>/dev/null || echo '')

## Your Task
$1"
    echo "Task: $1"
    echo ""
    "$HERMES" -m hermes_cli.main -m gemma4-stable:latest \
        --provider ollama \
        -z "$FULL_PROMPT"
else
    # Interactive mode: start with context pre-loaded as a message
    INIT_PROMPT="You are a coding agent for the PV AI Workbench. Read the following project context before accepting any tasks:

$(cat "$CLAUDE_MD")

## User Profile
$(cat "$CONTEXT_FILE" 2>/dev/null || echo '')

Context loaded. Ready for coding tasks in ~/pv-workbench/."
    "$HERMES" -m hermes_cli.main -m gemma4-stable:latest \
        --provider ollama \
        --skills pv-workbench \
        -z "$INIT_PROMPT" && \
    "$HERMES" -m hermes_cli.main -m gemma4-stable:latest \
        --provider ollama \
        --skills pv-workbench
fi
