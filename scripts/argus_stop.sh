#!/usr/bin/env bash
# Stop Argus and restore Hermes gateway.

set -euo pipefail

HERMES="$HOME/.hermes/hermes-agent/venv/bin/python"
ARGUS_PID_FILE="/tmp/argus.pid"

echo "=== Argus Shutdown ==="

# ── 1. Stop Argus ─────────────────────────────────────────────────────────────
if [ -f "$ARGUS_PID_FILE" ]; then
    ARGUS_PID="$(cat "$ARGUS_PID_FILE")"
    if kill -0 "$ARGUS_PID" 2>/dev/null; then
        echo "[1/2] Stopping Argus (PID $ARGUS_PID)..."
        kill "$ARGUS_PID"
        sleep 2
    fi
    rm -f "$ARGUS_PID_FILE"
else
    # Try by process name
    if pgrep -f "argus_bot.py" >/dev/null 2>&1; then
        echo "[1/2] Stopping Argus (by process name)..."
        pkill -f "argus_bot.py" 2>/dev/null || true
        sleep 1
    else
        echo "[1/2] Argus not running."
    fi
fi

# ── 2. Restart Hermes gateway ─────────────────────────────────────────────────
echo "[2/2] Restarting Hermes gateway..."
"$HERMES" -m hermes_cli.main gateway start 2>/dev/null || \
    nohup "$HERMES" -m hermes_cli.main gateway run --replace >/tmp/hermes-gateway.log 2>&1 &

sleep 2
if pgrep -f "hermes_cli.main gateway" >/dev/null 2>&1; then
    echo "✅ Hermes gateway restored."
else
    echo "⚠️  Hermes gateway did not restart — run manually: hermes gateway run"
fi
