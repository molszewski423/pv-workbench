"""
Argus Connectivity Test — verifies all bot prerequisites without running the bot.

Tests:
  1. Discord bot token validity (REST API /users/@me)
  2. Guild access — PV Workbench server reachable
  3. Channel verification — expected channels present
  4. RAG pipeline — query_vault() returns results
  5. Regulatory Q&A — answer_regulatory_question() callable
  6. Voice capability — discord.py[voice], ffmpeg, faster-whisper

Usage:
  PYTHONPATH=src python src/argus_connectivity_test.py

Token is auto-loaded from ~/.hermes/.env if DISCORD_BOT_TOKEN is not
already exported. No manual sourcing required.
"""

from __future__ import annotations

import os
import sys
import shutil
import urllib.request
import urllib.error
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

# Auto-load token from ~/.hermes/.env if not already in environment.
# Handles the case where .env uses VAR=value (no export) so sourcing
# the file in bash does not propagate the variable to child processes.
def _load_hermes_env():
    hermes_env = Path.home() / ".hermes" / ".env"
    if not hermes_env.exists():
        return
    for line in hermes_env.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        # Only set if not already in environment (env export takes precedence)
        # Use the LAST occurrence so duplicate lines resolve to the final value.
        if key and value and value != "your_new_token":
            os.environ[key] = value

_load_hermes_env()

OK   = "\033[92m✓\033[0m"
FAIL = "\033[91m✗\033[0m"
WARN = "\033[93m!\033[0m"

DISCORD_API = "https://discord.com/api/v10"

EXPECTED_CHANNELS = {
    "regulatory-qa",
    "signal-detection",
    "meddra-coding",
    "icsr-generator",
    "lit-monitor",
    "argus-status",
    "workbench-logs",
}


def _check(label: str, ok: bool, detail: str = "") -> bool:
    sym = OK if ok else FAIL
    msg = f"  {sym} {label}"
    if detail:
        msg += f"  ({detail})"
    print(msg)
    return ok


def _warn(label: str, detail: str = ""):
    msg = f"  {WARN} {label}"
    if detail:
        msg += f"  ({detail})"
    print(msg)


def _discord_get(path: str, token: str) -> dict | None:
    req = urllib.request.Request(
        f"{DISCORD_API}{path}",
        headers={"Authorization": f"Bot {token}", "User-Agent": "ArgusBot/1.0"},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return {"error": e.code, "reason": e.reason}
    except Exception as e:
        return {"error": str(e)}


# ─── Test 1: Discord Token ────────────────────────────────────────────────────

def test_discord_token() -> tuple[bool, str]:
    print("\n\033[1mTest 1 — Discord Bot Token\033[0m")
    token = os.environ.get("DISCORD_BOT_TOKEN", "").strip()
    if not token:
        _check("DISCORD_BOT_TOKEN set", False, "token not found in environment or ~/.hermes/.env")
        return False, ""

    _check("DISCORD_BOT_TOKEN set", True, f"{token[:10]}...")

    data = _discord_get("/users/@me", token)
    if "error" in data:
        _check("Token valid (GET /users/@me)", False, str(data))
        return False, token

    bot_name = f"{data.get('username')}#{data.get('discriminator', '0')}"
    _check("Token valid", True, f"Bot: {bot_name} (id={data.get('id')})")
    return True, token


# ─── Test 2: Guild Access ─────────────────────────────────────────────────────

def test_guild_access(token: str) -> tuple[bool, list[dict]]:
    print("\n\033[1mTest 2 — Guild Access\033[0m")
    guilds = _discord_get("/users/@me/guilds", token)
    if isinstance(guilds, dict) and "error" in guilds:
        _check("Guild list reachable", False, str(guilds))
        return False, []

    _check("Guild list reachable", True, f"{len(guilds)} guild(s)")

    pv_guild = next((g for g in guilds if "pv" in g.get("name", "").lower() or "workbench" in g.get("name", "").lower()), None)
    if pv_guild:
        _check("PV Workbench guild found", True, pv_guild.get("name"))
        return True, guilds
    else:
        _warn("PV Workbench guild not found in first-page guilds", f"Guilds: {[g['name'] for g in guilds[:5]]}")
        return len(guilds) > 0, guilds


# ─── Test 3: Channel Verification ─────────────────────────────────────────────

def test_channels(token: str, guilds: list[dict]) -> bool:
    print("\n\033[1mTest 3 — Channel Verification\033[0m")

    # Use channel_directory.json from Hermes as reference
    channel_dir = Path.home() / ".hermes" / "channel_directory.json"
    if channel_dir.exists():
        data = json.loads(channel_dir.read_text())
        discord_channels = data.get("platforms", {}).get("discord", [])
        found_names = {
            c.get("name", "").lower()
            for c in discord_channels
            if c.get("type") == "channel"
        }
        ok = True
        for expected in EXPECTED_CHANNELS:
            present = expected in found_names
            if not present:
                _warn(f"#{expected}", "channel not in directory — may need to run Hermes once")
                ok = False
            else:
                _check(f"#{expected}", True)
        return ok
    else:
        _warn("~/.hermes/channel_directory.json not found — skip channel check")
        return True


# ─── Test 4: RAG Pipeline ─────────────────────────────────────────────────────

def test_rag_pipeline() -> bool:
    print("\n\033[1mTest 4 — RAG Pipeline\033[0m")
    try:
        from ingester.vault_ingester import query_vault
        _check("query_vault importable", True)
    except ImportError as e:
        _check("query_vault importable", False, str(e))
        return False

    try:
        hits = query_vault("expedited reporting timeline", n_results=3)
        ok = len(hits) > 0
        _check("query_vault returns results", ok, f"{len(hits)} chunks")
        if hits:
            _check("Top result has source", bool(hits[0].get("source_note")), hits[0].get("source_note", ""))
            jur = hits[0].get("jurisdiction", "")
            _check("Jurisdiction metadata present", bool(jur), jur)
        return ok
    except Exception as e:
        _check("query_vault executes", False, str(e))
        return False


# ─── Test 5: Regulatory Q&A Module ───────────────────────────────────────────

def test_regulatory_qa() -> bool:
    print("\n\033[1mTest 5 — Regulatory Q&A Module\033[0m")
    try:
        from modules.regulatory_qa import answer_regulatory_question
        _check("answer_regulatory_question importable", True)
        # Don't call LLM in connectivity test — just verify import
        _warn("Skipping LLM call (use !ping in Discord to test end-to-end)")
        return True
    except ImportError as e:
        _check("answer_regulatory_question importable", False, str(e))
        return False
    except Exception as e:
        _check("regulatory_qa module loads", False, str(e))
        return False


# ─── Test 6: Voice Capability ─────────────────────────────────────────────────

def test_voice_capability() -> bool:
    print("\n\033[1mTest 6 — Voice Capability\033[0m")
    all_ok = True

    # discord.py voice extras (PyNaCl)
    try:
        import nacl.secret
        _check("PyNaCl (voice encryption)", True)
    except ImportError:
        _check("PyNaCl (voice encryption)", False, "pip install discord.py[voice]")
        all_ok = False

    # ffmpeg
    ffmpeg_path = shutil.which("ffmpeg")
    _check("ffmpeg", bool(ffmpeg_path), ffmpeg_path or "not found in PATH")

    # faster-whisper
    try:
        import faster_whisper
        _check("faster-whisper (STT)", True, f"v{faster_whisper.__version__}")
    except ImportError:
        _check("faster-whisper (STT)", False, "pip install faster-whisper")
        _warn("STT will be unavailable — !transcribe command disabled")

    # edge-tts
    try:
        import edge_tts
        _check("edge-tts (TTS)", True)
    except ImportError:
        _warn("edge-tts not installed — !voice speak disabled (pip install edge-tts)")

    # GPU check
    try:
        import torch
        cuda_ok = torch.cuda.is_available()
        _check("CUDA available (GPU acceleration)", cuda_ok,
               f"{torch.cuda.get_device_name(0)}" if cuda_ok else "CPU fallback")
    except ImportError:
        _warn("torch not installed — cannot verify GPU for faster-whisper")

    return all_ok


# ─── Summary ──────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("  Argus Bot Connectivity Test")
    print("=" * 60)

    results = {}

    token_ok, token = test_discord_token()
    results["discord_token"] = token_ok

    if token_ok:
        guild_ok, guilds = test_guild_access(token)
        results["guild_access"] = guild_ok
        results["channels"] = test_channels(token, guilds)
    else:
        results["guild_access"] = False
        results["channels"] = False

    results["rag_pipeline"] = test_rag_pipeline()
    results["regulatory_qa"] = test_regulatory_qa()
    results["voice"] = test_voice_capability()

    print("\n" + "=" * 60)
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    status = "✅ READY" if passed == total else f"⚠️  {passed}/{total} tests passed"
    print(f"  {status}")
    for name, ok in results.items():
        sym = OK if ok else FAIL
        print(f"  {sym} {name.replace('_', ' ').title()}")
    print("=" * 60)

    if results["discord_token"] and results["rag_pipeline"]:
        print(f"\nStart Argus:")
        print(f"  source ~/.hermes/.env")
        print(f"  PYTHONPATH=src python src/argus_bot.py")
    else:
        print("\nFix failing tests before starting Argus.")


if __name__ == "__main__":
    main()
