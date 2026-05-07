#!/usr/bin/env bash
# Start Argus Discord bot.
# Argus and Hermes share the same bot token and cannot run simultaneously.
# This script stops the Hermes gateway, then starts Argus.
# Run argus_stop.sh to reverse (stops Argus, restores Hermes gateway).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKBENCH="$(dirname "$SCRIPT_DIR")"
VENV="$WORKBENCH/.venv/bin/activate"
HERMES="$HOME/.hermes/hermes-agent/venv/bin/python"
ARGUS_PID_FILE="/tmp/argus.pid"

echo "=== Argus Startup ==="

# ── 1. Stop Hermes gateway if running ────────────────────────────────────────
if pgrep -f "hermes_cli.main gateway" >/dev/null 2>&1; then
    echo "[1/3] Stopping Hermes gateway..."
    "$HERMES" -m hermes_cli.main gateway stop 2>/dev/null || true
    sleep 2
    # Force-kill if still running
    if pgrep -f "hermes_cli.main gateway" >/dev/null 2>&1; then
        pkill -f "hermes_cli.main gateway" 2>/dev/null || true
        sleep 1
    fi
    echo "      Hermes gateway stopped."
else
    echo "[1/3] Hermes gateway not running — no action needed."
fi

# ── 2. Load Discord token from Hermes env ────────────────────────────────────
echo "[2/3] Loading environment..."
if [ -f "$HOME/.hermes/.env" ]; then
    # Extract the last real DISCORD_BOT_TOKEN (skips placeholder 'your_new_token').
    # The .env may contain duplicate lines; last real value wins.
    export DISCORD_BOT_TOKEN="$(grep '^DISCORD_BOT_TOKEN=' "$HOME/.hermes/.env" | grep -v 'your_new_token' | tail -1 | cut -d= -f2- | tr -d '"' | tr -d "'")"
    export DISCORD_ALLOWED_USERS="$(grep '^DISCORD_ALLOWED_USERS=' "$HOME/.hermes/.env" | tail -1 | cut -d= -f2- | tr -d '"' | tr -d "'" || echo "")"
    echo "      Token loaded from ~/.hermes/.env"
else
    echo "      WARNING: ~/.hermes/.env not found — DISCORD_BOT_TOKEN must be set manually"
fi

if [ -z "${DISCORD_BOT_TOKEN:-}" ]; then
    echo "ERROR: DISCORD_BOT_TOKEN is empty. Cannot start Argus."
    exit 1
fi

# ── 3. Start Argus ───────────────────────────────────────────────────────────
echo "[3/3] Starting Argus..."
source "$VENV"
cd "$WORKBENCH"

PYTHONPATH=src python src/argus_bot.py &
ARGUS_PID=$!
echo "$ARGUS_PID" > "$ARGUS_PID_FILE"

echo ""
echo "✅ Argus running (PID $ARGUS_PID)"
echo "   Logfile: /tmp/argus.log"
echo "   Stop:    bash scripts/argus_stop.sh"
echo "   Or:      kill $ARGUS_PID"
echo ""

wait "$ARGUS_PID"
