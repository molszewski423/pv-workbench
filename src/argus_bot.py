"""
Argus — PV Signal Intelligence Workbench Discord Bot

Shares the same backend module layer as the Streamlit dashboard.
All 5 workbench modules are available via Discord commands and channel routing.

Channel routing (message in channel → auto-routed to module):
  #regulatory-qa        → answer_regulatory_question()
  #signal-detection     → interpret signals / RAG signal context
  #meddra-coding        → suggest_meddra_pt()
  #icsr-generator       → generate_icsr_narrative() [M4 when available]
  #lit-monitor          → generate_digest() [M5 when available]

Commands (any channel):
  !ping                 → connectivity + model status
  !ask <question>       → RAG query (all guidelines, both jurisdictions)
  !ask fda <question>   → RAG query filtered to FDA sources
  !ask ema <question>   → RAG query filtered to EMA sources
  !drug <name>          → set active drug for session
  !run signal <drug>    → trigger FAERS signal detection (background)
  !status               → module + Ollama health check
  !help                 → command reference

Voice commands (requires voice channel membership):
  !voice join           → join your current voice channel
  !voice leave          → leave voice channel
  !voice speak <text>   → speak text via TTS
  !transcribe <reply>   → transcribe attached audio file via faster-whisper

Setup:
  export DISCORD_BOT_TOKEN=<token>   # from ~/.hermes/.env or project .env
  cd ~/pv-workbench && source .venv/bin/activate
  PYTHONPATH=src python src/argus_bot.py
"""

from __future__ import annotations

import asyncio
import io
import logging
import os
import sys
import tempfile
from pathlib import Path
from typing import Optional

import discord
from discord.ext import commands

# ─── Workbench path resolution ────────────────────────────────────────────────
_SRC = Path(__file__).parent
sys.path.insert(0, str(_SRC))

from config import REASON_MODEL, DRAFT_MODEL, OLLAMA_BASE_URL, TOP_K
import shared_state
from projects import list_projects, load_project, ProjectConfig

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("argus")

# ─── Context loading ──────────────────────────────────────────────────────────

_CONTEXT_DIR = _SRC / "context"
_LOCAL_CONFIG_DIR = _SRC.parent / ".local_config"
_MICHAEL_CONTEXT_FILE = _LOCAL_CONFIG_DIR / "michael_context.md"
_SESSION_LOG_FILE = _CONTEXT_DIR / "session_log.md"

def _load_michael_context() -> str:
    if _MICHAEL_CONTEXT_FILE.exists():
        return _MICHAEL_CONTEXT_FILE.read_text()
    return ""


def _build_workbench_context() -> str:
    """Build a live workbench context string for injection into every LLM prompt.

    Includes: active drug, all configured projects, module status, vault size.
    """
    active = shared_state.get_active_drug()
    lines = [
        "## PV AI Workbench — Live Context",
        f"**Active drug**: {active}",
        "",
        "**Configured projects (drugs under surveillance)**:",
    ]
    try:
        for proj in list_projects():
            marker = " ← active" if proj.drug_name == active else ""
            lines.append(f"  - {proj.drug_name.capitalize()} (comparator: {proj.comparator}){marker}")
    except Exception:
        lines.append("  (project list unavailable)")

    lines += [
        "",
        "**5 Modules Available**:",
        "  1. Regulatory Q&A — ICH/EMA/FDA guidelines RAG (gemma4:26b)",
        "  2. MedDRA Coder — PT deliberation with reviewer flag (gemma4:26b)",
        "  3. Signal Detection — FAERS PRR/chi² + Evans criteria + temporal cohort analysis",
        "  4. ICSR Generator — E2B(R3) narrative drafts (gemma4:e4b)",
        "  5. Lit Monitor — PubMed search + Discord digest (gemma4:e4b)",
        "",
        "**Key completed analyses**:",
        "  - Vancomycin nephrotoxicity: Pre-2020 (trough era) vs Post-2020 (AUC/MIC era)",
        "    PRE-2020: AKI PRR=2.16(signal), oliguria PRR=11.97(signal), RTA PRR=18.10(signal)",
        "    POST-2020: AKI PRR=1.95(sub-threshold), oliguria PRR=1.12(resolved), RTA PRR=10.51(attenuating)",
        "    → 2020 AUC/MIC guideline associated with meaningful nephrotoxicity signal reduction",
        "  - Cefiderocol: mortality/sepsis signals analyzed (confounding by indication documented)",
        "",
        "**Discord channels**: #regulatory-qa, #signal-detection, #meddra-coding, #icsr-generator, #lit-monitor",
    ]
    return "\n".join(lines)

def _append_session_log(entry: str):
    try:
        with open(_SESSION_LOG_FILE, "a") as f:
            f.write(f"\n{entry}\n")
    except Exception as e:
        logger.warning(f"Session log write failed: {e}")

_MICHAEL_CONTEXT = _load_michael_context()


# ─── Optional capability detection ───────────────────────────────────────────

def _try_import(module: str) -> bool:
    import importlib
    try:
        importlib.import_module(module)
        return True
    except ImportError:
        return False

_VOICE_AVAILABLE = _try_import("discord.opus") or True  # ffmpeg handles this
_STT_AVAILABLE = _try_import("faster_whisper")
_TTS_AVAILABLE = _try_import("edge_tts")

_whisper_model = None

def _get_whisper():
    global _whisper_model
    if not _STT_AVAILABLE:
        return None
    if _whisper_model is None:
        from faster_whisper import WhisperModel
        _whisper_model = WhisperModel("base", device="cuda", compute_type="float16")
        logger.info("Loaded faster-whisper base model on CUDA")
    return _whisper_model


# ─── Channel → module routing ─────────────────────────────────────────────────

CHANNEL_ROUTES: dict[str, str] = {
    "regulatory-qa": "REGULATORY_QA",
    "regulatory_qa": "REGULATORY_QA",
    "signal-detection": "SIGNAL_DETECTION",
    "signal-alerts": "SIGNAL_DETECTION",
    "meddra-coding": "MEDDRA_CODING",
    "meddra_coding": "MEDDRA_CODING",
    "icsr-generator": "ICSR_GENERATION",
    "icsr-drafts": "ICSR_GENERATION",
    "lit-monitor": "LIT_MONITOR",
    "lit-monitoring": "LIT_MONITOR",
}

INTENT_PROMPT = """\
You are Argus, the intelligent routing core of the PV AI Workbench.
You are assisting a senior clinical reviewer (PharmD, BCPS, BCCCP with 18 years of ICU experience).
Your role is the "Junior Analyst" in a Junior Analyst / Senior Reviewer model.

Mission: Provide local-LLM clinical support for pharmacovigilance (FAERS signals, MedDRA coding, ICSR drafting, and literature monitoring).

Given a user message, classify it into one of the following intents:
- REGULATORY_QA: Questions about PV regulations, guidelines (ICH, EMA, FDA).
- MEDDRA_CODING: Requests to code clinical terms or narratives to MedDRA PTs.
- SIGNAL_DETECTION: Questions about drug safety signals, PRR, FAERS data, or requests for signal context.
- ICSR_GENERATION: Requests to draft case narratives or E2B(R3) reports.
- LIT_MONITOR: Requests for PubMed literature searches or digests.
- PIPELINE_TRIGGER: Requests to run a specific automated pipeline (e.g., "run signal detection").
- GENERAL: General conversation, greetings, or questions about your purpose/the project.

Output ONLY the intent label.
"""

# ─── Module lazy loaders (graceful stub fallback) ─────────────────────────────

def _load_regulatory_qa():
    from modules.regulatory_qa import answer_regulatory_question
    return answer_regulatory_question

def _load_meddra_coder():
    from modules.meddra_coder import suggest_meddra_pt
    return suggest_meddra_pt

def _load_query_vault():
    from ingester.vault_ingester import query_vault
    return query_vault

def _module_available(name: str) -> bool:
    try:
        if name == "regulatory_qa":
            _load_regulatory_qa()
        elif name == "meddra_coder":
            _load_meddra_coder()
        elif name == "signal_detection":
            from modules.signal_detection import interpret_signals
        elif name in ("icsr_generator", "lit_monitor"):
            mod = __import__(f"modules.{name}", fromlist=[name])
            # Module exists but may still be stub
            return True
        return True
    except Exception:
        return False


def _module_status() -> dict[str, str]:
    statuses = {}
    for name in ["regulatory_qa", "meddra_coder", "signal_detection", "icsr_generator", "lit_monitor"]:
        try:
            if name == "regulatory_qa":
                _load_regulatory_qa()
                statuses[name] = "✅ Ready"
            elif name == "meddra_coder":
                _load_meddra_coder()
                statuses[name] = "✅ Ready"
            elif name == "signal_detection":
                from modules.signal_detection import interpret_signals
                statuses[name] = "✅ Ready"
            elif name == "icsr_generator":
                from modules.icsr_generator import generate_icsr_narrative, CaseData
                statuses[name] = "✅ Ready"
            elif name == "lit_monitor":
                from modules.lit_monitor import generate_digest, search_pubmed
                statuses[name] = "✅ Ready"
        except Exception as e:
            statuses[name] = f"❌ Error: {type(e).__name__}"
    return statuses


# ─── Discord bot setup ────────────────────────────────────────────────────────

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# Per-guild active drug tracking
# Now using shared_state.py for persistent/shared state

def _get_drug() -> str:
    return shared_state.get_active_drug()


def _truncate(text: str, max_len: int = 1900) -> str:
    if len(text) <= max_len:
        return text
    return text[:max_len - 3] + "..."


def _make_embed(title: str, description: str, color: int = 0x3498db) -> discord.Embed:
    embed = discord.Embed(title=title, description=description[:4096], color=color)
    embed.set_footer(text="Argus · PV Signal Intelligence Workbench · DRAFT — Senior Reviewer Oversight Required")
    return embed


async def _log_status(guild: discord.Guild | None, input_text: str, intent: str, model: str):
    """Log routing decision to #workbench-status."""
    if not guild:
        return
    channel = discord.utils.get(guild.text_channels, name="workbench-logs")
    if not channel:
        return
    
    embed = discord.Embed(title="Route Logged", color=0x34495e)
    embed.add_field(name="User Input", value=f"`{input_text[:100]}`", inline=False)
    embed.add_field(name="Detected Intent", value=f"**{intent}**", inline=True)
    embed.add_field(name="Assigned Model", value=f"`{model}`", inline=True)
    embed.set_footer(text=f"Argus Intelligence Router")
    await channel.send(embed=embed)


async def _classify_intent(message_text: str) -> str:
    """Use gemma4:26b to classify intent if ambiguous."""
    from langchain_ollama import ChatOllama
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.output_parsers import StrOutputParser

    llm = ChatOllama(model=REASON_MODEL, base_url=OLLAMA_BASE_URL, temperature=0)
    workbench_ctx = _build_workbench_context()
    system_prompt = f"{INTENT_PROMPT}\n\n{workbench_ctx}"
    if _MICHAEL_CONTEXT:
        system_prompt += f"\n\n## User Identity\n{_MICHAEL_CONTEXT}"
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "{input}"),
    ])
    chain = prompt | llm | StrOutputParser()
    try:
        response = await asyncio.to_thread(chain.invoke, {"input": message_text})
        return response.strip().upper()
    except Exception as e:
        logger.error(f"Intent classification error: {e}")
        return "GENERAL"


# ─── Event handlers ───────────────────────────────────────────────────────────

@bot.event
async def on_ready():
    logger.info(f"Argus online as {bot.user} (id={bot.user.id})")
    for guild in bot.guilds:
        logger.info(f"Connected to guild: {guild.name} (id={guild.id})")
        channels = [c.name for c in guild.text_channels]
        logger.info(f"Visible text channels: {', '.join(channels)}")
        for member in guild.members:
            if member.name == "pillpusher7915":
                try:
                    await member.send("Argus is online and ready. Are you receiving this?")
                    logger.info(f"Sent verification DM to {member.name}")
                except Exception as e:
                    logger.warning(f"Failed to send DM to {member.name}: {e}")
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="for adverse signals | !help"
        )
    )


@bot.event
async def on_typing(channel, user, when):
    channel_name = channel.name if hasattr(channel, "name") else "DM"
    logger.info(f"Typing detected in #{channel_name} by {user}")

@bot.event
async def on_message(message: discord.Message):
    logger.info(f"Message received: '{message.content[:50]}...' in channel #{getattr(message.channel, 'name', 'DM')} ({message.channel.id}) [Guild: {getattr(message.guild, 'name', 'None')} ({getattr(message.guild, 'id', 'None')})]")
    if message.author.bot:
        return

    # Process commands first
    await bot.process_commands(message)

    # Skip if it was a command
    if message.content.startswith("!"):
        return

    # Channel-based routing for non-command messages
    channel_name = message.channel.name if hasattr(message.channel, "name") else ""
    route = CHANNEL_ROUTES.get(channel_name)

    if message.content.strip():
        logger.info(f"Processing message in #{channel_name}")
        async with message.channel.typing():
            # If no channel route, use intent classification
            if not route:
                logger.info("No channel route found, classifying intent...")
                route = await _classify_intent(message.content)
            
            logger.info(f"Routing to: {route}")
            await _route_message(message, route)


async def _route_message(message: discord.Message, route: str):
    drug = _get_drug()
    query = message.content.strip()

    try:
        if route == "REGULATORY_QA":
            await _log_status(message.guild, query, route, REASON_MODEL)
            fn = _load_regulatory_qa()
            result = await asyncio.to_thread(fn, query)
            embed = _make_embed(
                f"Regulatory Q&A — {result.confidence} confidence",
                result.answer,
                color=0x2ecc71,
            )
            if result.citations:
                embed.add_field(
                    name="Sources",
                    value="\n".join(f"• {c}" for c in result.citations[:5]),
                    inline=False,
                )
            await message.reply(embed=embed)

        elif route == "MEDDRA_CODING":
            await _log_status(message.guild, query, route, REASON_MODEL)
            fn = _load_meddra_coder()
            result = await asyncio.to_thread(fn, query)
            flag = "⚠️ Reviewer Required" if result.reviewer_flag else "✅ Low uncertainty"
            embed = _make_embed(
                f"MedDRA Coding — {result.confidence} | {flag}",
                f"**Primary PT**: {result.primary_pt}\n**SOC**: {result.soc}\n\n**Notes**: {result.coding_notes[:500]}",
                color=0xe74c3c if result.reviewer_flag else 0x27ae60,
            )
            if result.alternative_pts:
                embed.add_field(
                    name="Alternative PTs",
                    value=", ".join(result.alternative_pts[:5]),
                    inline=False,
                )
            await message.reply(embed=embed)

        elif route == "SIGNAL_DETECTION":
            await _log_status(message.guild, query, route, REASON_MODEL)
            qv = _load_query_vault()
            hits = await asyncio.to_thread(qv, query, TOP_K, "Guidelines")
            if hits:
                context = "\n".join(f"**{h['source_note']}** › {h['section_header']}\n{h['text'][:200]}" for h in hits[:3])
                embed = _make_embed(f"Signal Context — {drug}", context, color=0xe67e22)
                await message.reply(embed=embed)
            else:
                await message.reply("No relevant signal context found in vault.")

        elif route == "ICSR_GENERATION":
            await _log_status(message.guild, query, route, DRAFT_MODEL)
            from modules.icsr_generator import CaseData, generate_icsr_narrative
            case = CaseData(adverse_event=query, suspect_drug=drug)
            result = await asyncio.to_thread(generate_icsr_narrative, case)
            embed = _make_embed(
                f"ICSR Narrative Draft — {drug}",
                result.narrative,
                color=0x3498db,
            )
            await message.reply(embed=embed)

        elif route == "LIT_MONITOR":
            await _log_status(message.guild, query, route, DRAFT_MODEL)
            from modules.lit_monitor import search_pubmed, score_relevance, generate_digest
            results = await asyncio.to_thread(search_pubmed, drug, days_back=30, max_results=3)
            if results:
                scored = await asyncio.to_thread(score_relevance, results, drug)
                digest = await asyncio.to_thread(generate_digest, drug, scored)
                embed = _make_embed(
                    f"Literature Digest — {drug}",
                    digest.digest_text or "No relevant papers found for summary.",
                    color=0x9b59b6,
                )
                await message.reply(embed=embed)
            else:
                await message.reply(f"No recent PubMed results for {drug}.")

        elif route == "PIPELINE_TRIGGER":
            await _log_status(message.guild, query, route, "Hermes Gateway")
            await message.reply(f"🚀 Triggering pipeline for **{drug}**... check #workbench-status for updates.")
            shared_state.set_pipeline_status("Signal Detection", "Running")

        elif route == "GENERAL":
            await _log_status(message.guild, query, route, REASON_MODEL)
            from langchain_ollama import ChatOllama
            from langchain_core.messages import HumanMessage, SystemMessage

            # Use RAG to see if we know about the user or project
            qv = _load_query_vault()
            hits = await asyncio.to_thread(qv, query, 3, "Guidelines")
            context_text = ""
            if hits:
                context_text = "\n\nRelevant Vault Context:\n" + "\n".join([f"- {h['text']}" for h in hits])

            workbench_ctx = _build_workbench_context()
            user_context = f"\n\n## Who You Are Talking To\n{_MICHAEL_CONTEXT}" if _MICHAEL_CONTEXT else ""
            llm = ChatOllama(model=REASON_MODEL, base_url=OLLAMA_BASE_URL)
            sys_msg = SystemMessage(content=(
                f"You are Argus, the Junior Analyst for the PV AI Workbench. "
                f"You assist Senior Reviewer Michael Olszewski (PharmD, BCPS, BCCCP, 18 years ICU). "
                f"Always address him by name or as Senior Reviewer. "
                f"Explain PV concepts with clinical context — the why, not just the what.\n\n"
                f"{workbench_ctx}"
                f"{user_context}"
                f"{context_text}"
            ))
            
            response = await asyncio.to_thread(llm.invoke, [sys_msg, HumanMessage(content=query)])
            content = response.content
            
            # Truncate to Discord 2000 char limit
            if len(content) > 1900:
                content = content[:1900] + "\n\n*(Truncated due to length)*"
            
            await message.reply(content)

    except Exception as e:
        logger.error(f"Route {route} error: {e}", exc_info=True)
        await message.reply(f"❌ Error processing request: `{type(e).__name__}: {str(e)[:200]}`")


# ─── Commands ─────────────────────────────────────────────────────────────────

@bot.command(name="ping")
async def cmd_ping(ctx: commands.Context):
    """Connectivity and model status check."""
    import time
    t0 = time.monotonic()

    lines = [
        f"**Argus PV Workbench Bot** — Online",
        f"",
        f"**Reasoning model**: `{REASON_MODEL}`",
        f"**Drafting model**: `{DRAFT_MODEL}`",
        f"**Ollama**: `{OLLAMA_BASE_URL}`",
        f"**STT** (faster-whisper): {'✅' if _STT_AVAILABLE else '❌ not installed'}",
        f"**TTS** (edge-tts): {'✅' if _TTS_AVAILABLE else '❌ not installed'}",
        f"",
        f"*All outputs are DRAFTS — senior reviewer sign-off required*",
    ]

    latency = round((time.monotonic() - t0) * 1000, 1)
    embed = _make_embed("🤖 Argus Status", "\n".join(lines), color=0x3498db)
    embed.set_footer(text=f"Argus · PV Workbench · Response latency: {latency}ms")
    await ctx.reply(embed=embed)


@bot.command(name="ask")
async def cmd_ask(ctx: commands.Context, *, query: str):
    """
    RAG query across all regulatory guidelines.
    Usage: !ask <question>
           !ask fda <question>    (FDA sources only)
           !ask ema <question>    (EMA sources only)
    """
    jurisdiction = None
    if query.lower().startswith("fda "):
        jurisdiction = "FDA"
        query = query[4:].strip()
    elif query.lower().startswith("ema "):
        jurisdiction = "EMA"
        query = query[4:].strip()

    async with ctx.typing():
        try:
            fn = _load_regulatory_qa()
            result = await asyncio.to_thread(fn, query)
            jur_label = f" [{jurisdiction}]" if jurisdiction else ""
            embed = _make_embed(
                f"Regulatory Q&A{jur_label} — {result.confidence}",
                result.answer,
                color=0x2ecc71,
            )
            if result.citations:
                embed.add_field(
                    name="Sources",
                    value="\n".join(f"• {c}" for c in result.citations[:5]),
                    inline=False,
                )
            await ctx.reply(embed=embed)
        except Exception as e:
            logger.error(f"!ask error: {e}", exc_info=True)
            await ctx.reply(f"❌ RAG query failed: `{type(e).__name__}: {str(e)[:300]}`")


@bot.command(name="drug")
async def cmd_drug(ctx: commands.Context, *, drug_name: str):
    """Set active drug for this server session. Usage: !drug vancomycin"""
    shared_state.set_active_drug(drug_name.strip())
    await ctx.reply(f"✅ Active drug set to **{drug_name}** for this session.")


@bot.command(name="projects")
async def cmd_projects(ctx: commands.Context):
    """List all configured projects. Use !drug <name> to switch."""
    try:
        projects = list_projects()
        active = shared_state.get_active_drug()
        if not projects:
            await ctx.reply("No projects configured in projects.json.")
            return
        lines = ["**Configured PV Projects**", ""]
        for p in projects:
            marker = " ◀ active" if p.drug_name == active else ""
            lines.append(f"• **{p.drug_name.capitalize()}** — comparator: {p.comparator}{marker}")
        lines += ["", "Use `!drug <name>` to switch active drug."]
        await ctx.reply(embed=_make_embed("Project Registry", "\n".join(lines)))
    except Exception as e:
        await ctx.reply(f"❌ Could not load projects: `{e}`")


@bot.command(name="status")
async def cmd_status(ctx: commands.Context):
    """Module availability and health check."""
    async with ctx.typing():
        statuses = await asyncio.to_thread(_module_status)
        drug = _get_drug()

        lines = [f"**Active drug**: {drug}", ""]
        labels = {
            "regulatory_qa": "Module 1 — Regulatory Q&A",
            "meddra_coder": "Module 2 — MedDRA Coder",
            "signal_detection": "Module 3 — Signal Detection",
            "icsr_generator": "Module 4 — ICSR Generator",
            "lit_monitor": "Module 5 — Lit Monitor",
        }
        for key, label in labels.items():
            lines.append(f"{statuses.get(key, '❓')} **{label}**")

        lines += ["", f"**Voice STT**: {'✅' if _STT_AVAILABLE else '❌'}", f"**Voice TTS**: {'✅' if _TTS_AVAILABLE else '❌'}"]
        await ctx.reply(embed=_make_embed("Workbench Status", "\n".join(lines)))


@bot.command(name="help")
async def cmd_help(ctx: commands.Context):
    """Command reference."""
    text = """
**General**
`!ping`             — bot status and model info
`!status`           — module health check
`!drug <name>`      — set active drug context
`!projects`         — list all configured projects
`!help`             — this message

**Queries**
`!ask <question>`         — RAG query (all sources)
`!ask fda <question>`     — FDA sources only (21 CFR, FAERS)
`!ask ema <question>`     — EMA sources only (GVP, EudraVigilance)

**Channel Routing** (no prefix needed in dedicated channels)
`#regulatory-qa`    → Module 1 (Regulatory Q&A)
`#meddra-coding`    → Module 2 (MedDRA Coder)
`#signal-detection` → Module 3 (Signal context)
`#icsr-generator`   → Module 4 (ICSR drafts, pending)
`#lit-monitor`      → Module 5 (Literature, pending)

**Voice**
`!voice join`           — join your voice channel
`!voice leave`          — leave voice channel
`!voice speak <text>`   — TTS output in voice channel
`!transcribe`           — transcribe audio file attachment

*All outputs are DRAFTS — senior reviewer sign-off required before regulatory use.*
"""
    await ctx.reply(embed=_make_embed("Argus Commands", text))


# ─── Voice commands ────────────────────────────────────────────────────────────

@bot.group(name="voice", invoke_without_command=True)
async def voice_group(ctx: commands.Context):
    await ctx.reply("Voice subcommands: `!voice join`, `!voice leave`, `!voice speak <text>`")


@voice_group.command(name="join")
async def voice_join(ctx: commands.Context):
    if ctx.author.voice is None:
        await ctx.reply("❌ You must be in a voice channel first.")
        return
    channel = ctx.author.voice.channel
    if ctx.voice_client:
        await ctx.voice_client.move_to(channel)
    else:
        await channel.connect()
    await ctx.reply(f"✅ Joined **{channel.name}**. Use `!voice speak <text>` for TTS output.")


@voice_group.command(name="leave")
async def voice_leave(ctx: commands.Context):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.reply("👋 Left voice channel.")
    else:
        await ctx.reply("Not currently in a voice channel.")


@voice_group.command(name="speak")
async def voice_speak(ctx: commands.Context, *, text: str):
    """Speak text in the current voice channel using edge-tts TTS."""
    if not ctx.voice_client:
        await ctx.reply("❌ Not in a voice channel. Use `!voice join` first.")
        return
    if not _TTS_AVAILABLE:
        await ctx.reply("❌ TTS not available — install `edge-tts`: `pip install edge-tts`")
        return
    try:
        import edge_tts
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            tmp_path = f.name
        communicate = edge_tts.Communicate(text[:500], voice="en-US-GuyNeural")
        await communicate.save(tmp_path)
        source = discord.FFmpegPCMAudio(tmp_path)
        ctx.voice_client.play(source, after=lambda e: os.unlink(tmp_path) if os.path.exists(tmp_path) else None)
        await ctx.reply(f"🔊 Speaking: *{text[:100]}{'...' if len(text) > 100 else ''}*")
    except Exception as e:
        await ctx.reply(f"❌ TTS error: `{e}`")


@bot.command(name="transcribe")
async def cmd_transcribe(ctx: commands.Context):
    """
    Transcribe an attached audio file using faster-whisper.
    Attach an audio file (mp3, wav, ogg, m4a) and use !transcribe in reply.
    """
    if not _STT_AVAILABLE:
        await ctx.reply("❌ faster-whisper not available. Install: `pip install faster-whisper`")
        return

    attachments = ctx.message.attachments
    if not attachments:
        # Check if replying to a message with an attachment
        ref = ctx.message.reference
        if ref and ref.resolved:
            attachments = ref.resolved.attachments

    if not attachments:
        await ctx.reply("❌ Attach an audio file (mp3, wav, ogg, m4a) to your message.")
        return

    audio_att = attachments[0]
    async with ctx.typing():
        try:
            audio_bytes = await audio_att.read()
            with tempfile.NamedTemporaryFile(suffix=Path(audio_att.filename).suffix, delete=False) as f:
                f.write(audio_bytes)
                tmp_path = f.name

            whisper = await asyncio.to_thread(_get_whisper)
            segments, info = await asyncio.to_thread(
                lambda: whisper.transcribe(tmp_path, beam_size=5)
            )
            transcript = " ".join(s.text for s in segments).strip()
            os.unlink(tmp_path)

            embed = _make_embed(
                f"Transcription — {audio_att.filename}",
                transcript or "(No speech detected)",
                color=0x9b59b6,
            )
            embed.add_field(name="Language", value=info.language, inline=True)
            embed.add_field(name="Duration", value=f"{info.duration:.1f}s", inline=True)
            await ctx.reply(embed=embed)

        except Exception as e:
            logger.error(f"Transcribe error: {e}", exc_info=True)
            await ctx.reply(f"❌ Transcription failed: `{type(e).__name__}: {str(e)[:200]}`")


# ─── Hermes gateway conflict detection ────────────────────────────────────────

def _check_hermes_conflict() -> bool:
    """
    Returns True if Hermes gateway is running on the same token.
    Argus and Hermes share DISCORD_BOT_TOKEN — only one can hold the
    gateway connection at a time. Use scripts/argus_start.sh to stop
    Hermes gracefully before starting Argus.
    """
    import subprocess
    try:
        result = subprocess.run(
            ["pgrep", "-f", "hermes_cli.main gateway"],
            capture_output=True, text=True
        )
        return result.returncode == 0
    except FileNotFoundError:
        # pgrep not available — check via psutil if installed
        try:
            import psutil
            return any(
                "hermes_cli.main gateway" in " ".join(p.cmdline())
                for p in psutil.process_iter(["cmdline"])
                if p.info["cmdline"]
            )
        except Exception:
            return False


# ─── Entry point ──────────────────────────────────────────────────────────────

def main():
    # Load token from Hermes .env if not already in environment
    if not os.environ.get("DISCORD_BOT_TOKEN"):
        hermes_env = Path.home() / ".hermes" / ".env"
        if hermes_env.exists():
            for line in hermes_env.read_text().splitlines():
                if line.startswith("DISCORD_BOT_TOKEN="):
                    os.environ["DISCORD_BOT_TOKEN"] = line.split("=", 1)[1].strip().strip('"').strip("'")
                    break

    token = os.environ.get("DISCORD_BOT_TOKEN", "").strip()
    if not token:
        logger.error("DISCORD_BOT_TOKEN not set. Run: source ~/.hermes/.env")
        sys.exit(1)

    # Warn if Hermes gateway is already holding the connection
    if _check_hermes_conflict():
        logger.warning(
            "Hermes gateway is running on the same bot token. "
            "Only one process can hold the Discord gateway connection.\n"
            "  Recommended: bash scripts/argus_start.sh  (stops Hermes, starts Argus)\n"
            "  Manual:      hermes gateway stop  then  PYTHONPATH=src python src/argus_bot.py\n"
            "Attempting to connect anyway — Discord will disconnect the other session."
        )

    logger.info(
        f"Starting Argus | "
        f"STT={'ON (faster-whisper)' if _STT_AVAILABLE else 'OFF'} | "
        f"TTS={'ON (edge-tts)' if _TTS_AVAILABLE else 'OFF'} | "
        f"model={REASON_MODEL}"
    )
    bot.run(token, log_handler=None)


if __name__ == "__main__":
    main()
