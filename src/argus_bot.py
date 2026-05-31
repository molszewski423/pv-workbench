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
import email.mime.application
import email.mime.multipart
import email.mime.text
import logging
import os
import smtplib
import sys
import tempfile
from pathlib import Path
from typing import Optional

import discord
from discord.ext import commands

# ─── Workbench path resolution ────────────────────────────────────────────────
_SRC = Path(__file__).parent
sys.path.insert(0, str(_SRC))

from config import REASON_MODEL, DRAFT_MODEL, CHAT_MODEL, OLLAMA_BASE_URL, TOP_K
import shared_state
from projects import list_projects, load_project, ProjectConfig

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("argus")


def _send_pdf_email(pdf_path: Path, subject: str, body: str) -> bool:
    """Send a PDF as an email attachment via Gmail SMTP. Returns True on success."""
    smtp_user = os.environ.get("REPORT_EMAIL_FROM", "")
    smtp_pass = os.environ.get("SMTP_APP_PASSWORD", "")
    to_addr   = os.environ.get("REPORT_EMAIL_TO", smtp_user)
    if not smtp_pass:
        logger.warning("SMTP_APP_PASSWORD not set — skipping email delivery")
        return False
    try:
        msg = email.mime.multipart.MIMEMultipart()
        msg["From"]    = smtp_user
        msg["To"]      = to_addr
        msg["Subject"] = subject
        msg.attach(email.mime.text.MIMEText(body, "plain"))
        with open(pdf_path, "rb") as f:
            part = email.mime.application.MIMEApplication(f.read(), Name=pdf_path.name)
        part["Content-Disposition"] = f'attachment; filename="{pdf_path.name}"'
        msg.attach(part)
        with smtplib.SMTP("smtp.gmail.com", 587) as srv:
            srv.starttls()
            srv.login(smtp_user, smtp_pass)
            srv.sendmail(smtp_user, to_addr, msg.as_string())
        logger.info(f"Email sent to {to_addr} with attachment {pdf_path.name}")
        return True
    except Exception as e:
        logger.warning(f"Email delivery failed: {e}")
        return False


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
    """Build a live workbench context string injected into every LLM prompt."""
    active = shared_state.get_active_drug()
    lines = [
        "## PV AI Workbench — Live Context",
        f"**Active drug**: {active}",
        "",
        "**Configured projects (drugs under surveillance)**:",
    ]
    try:
        for proj in list_projects():
            marker = " <- active" if proj.drug_name == active else ""
            lines.append(f"  - {proj.drug_name.capitalize()} (comparator: {proj.comparator}){marker}")
    except Exception:
        lines.append("  (project list unavailable)")

    lines += [
        "",
        "**5 Modules — All Operational**:",
        "  1. Regulatory Q&A — ICH/EMA/FDA guidelines RAG (gemma4:26b)",
        "  2. MedDRA Coder — PT deliberation with reviewer flag (gemma4:26b)",
        "  3. Signal Detection — FAERS PRR/chi2 + Evans criteria + temporal cohort analysis",
        "  4. ICSR Generator — E2B(R3) narrative drafts (gemma4:e4b)",
        "  5. Lit Monitor — PubMed search + Discord digest (gemma4:e4b)",
        "",
        "**Completed Analyses — Vancomycin Project**:",
        "  STUDY 1: Nephrotoxicity Pre/Post 2020 AUC/MIC Guideline (FAERS 2015-2025)",
        "    Drug: Vancomycin | Comparator: Linezolid | Method: PRR/chi2 Evans criteria",
        "    PRE-2020 cohort (2015-2019, 22,200 reports, trough-guided monitoring era):",
        "      - AKI PRR=2.16 SIGNAL (N=2364, chi2=19.4)",
        "      - Oliguria PRR=11.97 SIGNAL (N=312, chi2=58.2)",
        "      - Renal Tubular Necrosis PRR=18.10 SIGNAL (N=287, chi2=71.3)",
        "    POST-2020 cohort (2020-2025, 31,793 reports, AUC/MIC monitoring era):",
        "      - AKI PRR=1.95 (below Evans threshold - signal resolved)",
        "      - Oliguria PRR=1.12 (fully resolved)",
        "      - Renal Tubular Necrosis PRR=10.51 SIGNAL (attenuating, still Evans-positive)",
        "    KEY FINDING: 2020 AUC/MIC guideline associated with meaningful nephrotoxicity reduction.",
        "    Oliguria resolved completely. AKI dropped below Evans threshold. RTN persists (regulatory priority).",
        "",
        "  STUDY 2: Single-Level vs Two-Level Bayesian AUC Estimation (Clinical/Methodological Analysis)",
        "    Context: AUC/MIC monitoring uses Bayesian PK modeling with 1 or 2 serum levels.",
        "    Single-level (one trough): Adequate for stable patients. Published AUC accuracy within 15-25%.",
        "    Two-level (peak+trough or 2 troughs): Required in high-risk ICU scenarios:",
        "      - AKI/rapidly changing renal function (CL trajectory not captured by single level)",
        "      - CRRT or ECMO (extracorporeal CL unpredictable from population prior)",
        "      - Morbid obesity BMI>40 (Vd estimation unreliable from trough alone)",
        "      - Augmented renal clearance CrCl>130 (hyperclearance underestimated)",
        "      - Pediatrics (guideline-recommended)",
        "    PV IMPLICATION: Residual RTN signal mechanistically consistent with single-level use",
        "    in ICU patients where two-level is warranted. Incomplete guideline implementation",
        "    may account for the persistent structural nephrotoxicity burden post-2020.",
        "",
        "  OUTPUT: Full 13-page PDF report on Desktop (vancomycin_full_report_*.pdf)",
        "    Covers: statistical analysis + clinical interpretation + Bayesian dosing methodology",
        "    Status: DRAFT - requires senior reviewer sign-off before regulatory use",
        "",
        "**Completed Analyses — Other Projects**:",
        "  - Cefiderocol: mortality/sepsis signals analyzed (confounding by indication documented)",
        "  - Colistin: under surveillance (comparator: meropenem)",
        "",
        "**Portfolio**:",
        "  GitHub: https://github.com/molszewskiPV/PV-Signal-Intelligence-Workbench",
        "  Discord channels: #regulatory-qa, #signal-detection, #meddra-coding,",
        "                    #icsr-generator, #lit-monitor, #portfolio-dev",
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
    "portfolio-dev": "GENERAL",
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


_DISCORD_MSG_LIMIT = 2000
_DISCORD_EMBED_LIMIT = 4096
_FOOTER = "Argus · PV Signal Intelligence Workbench · DRAFT — Senior Reviewer Oversight Required"


def _split_text(text: str, max_len: int = _DISCORD_MSG_LIMIT) -> list[str]:
    """Split text into chunks ≤ max_len, breaking on paragraph → newline → word boundaries."""
    if len(text) <= max_len:
        return [text]

    chunks: list[str] = []
    remaining = text
    while len(remaining) > max_len:
        # Try paragraph break first, then single newline, then last space
        for sep in ("\n\n", "\n", " "):
            cut = remaining.rfind(sep, 0, max_len)
            if cut > 0:
                chunks.append(remaining[:cut].rstrip())
                remaining = remaining[cut:].lstrip()
                break
        else:
            # No good break point — hard cut
            chunks.append(remaining[:max_len])
            remaining = remaining[max_len:]
    if remaining:
        chunks.append(remaining)
    return chunks


async def _send_long(dest, text: str, reference=None) -> None:
    """Send text as one or more messages, respecting Discord's 2000-char limit."""
    chunks = _split_text(text, _DISCORD_MSG_LIMIT - 10)  # leave headroom
    for i, chunk in enumerate(chunks):
        if i == 0 and reference is not None:
            await reference.reply(chunk)
        else:
            await dest.send(chunk)


def _make_embed(title: str, description: str, color: int = 0x3498db) -> discord.Embed:
    embed = discord.Embed(title=title, description=description[:_DISCORD_EMBED_LIMIT], color=color)
    embed.set_footer(text=_FOOTER)
    return embed


def _make_embed_pages(title: str, description: str, color: int = 0x3498db) -> list[discord.Embed]:
    """Return one or more embeds if description exceeds the 4096-char embed limit."""
    chunks = _split_text(description, _DISCORD_EMBED_LIMIT)
    embeds = []
    for i, chunk in enumerate(chunks):
        page_title = title if len(chunks) == 1 else f"{title} ({i + 1}/{len(chunks)})"
        embed = discord.Embed(title=page_title, description=chunk, color=color)
        embed.set_footer(text=_FOOTER)
        embeds.append(embed)
    return embeds


async def _reply_embed(message: discord.Message, title: str, description: str, color: int = 0x3498db, extra_fields: list[tuple] | None = None) -> None:
    """Send embed reply, paginating if description exceeds 4096 chars."""
    pages = _make_embed_pages(title, description, color)
    for i, embed in enumerate(pages):
        if extra_fields and i == len(pages) - 1:
            for name, value, inline in extra_fields:
                embed.add_field(name=name, value=str(value)[:1024], inline=inline)
        if i == 0:
            await message.reply(embed=embed)
        else:
            await message.channel.send(embed=embed)


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
    """Classify intent using the fast chat model — routing labels don't need 26b."""
    from langchain_ollama import ChatOllama
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.output_parsers import StrOutputParser

    llm = ChatOllama(model=CHAT_MODEL, base_url=OLLAMA_BASE_URL, temperature=0)
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
            citations = "\n".join(f"• {c}" for c in result.citations[:5]) if result.citations else None
            extra = [("Sources", citations, False)] if citations else None
            await _reply_embed(
                message,
                f"Regulatory Q&A — {result.confidence} confidence",
                result.answer,
                color=0x2ecc71,
                extra_fields=extra,
            )

        elif route == "MEDDRA_CODING":
            await _log_status(message.guild, query, route, REASON_MODEL)
            fn = _load_meddra_coder()
            result = await asyncio.to_thread(fn, query)
            flag = "⚠️ Reviewer Required" if result.reviewer_flag else "✅ Low uncertainty"
            body = f"**Primary PT**: {result.primary_pt}\n**SOC**: {result.soc}\n\n**Notes**: {result.coding_notes}"
            alts = ", ".join(result.alternative_pts[:5]) if result.alternative_pts else None
            extra = [("Alternative PTs", alts, False)] if alts else None
            await _reply_embed(
                message,
                f"MedDRA Coding — {result.confidence} | {flag}",
                body,
                color=0xe74c3c if result.reviewer_flag else 0x27ae60,
                extra_fields=extra,
            )

        elif route == "SIGNAL_DETECTION":
            await _log_status(message.guild, query, route, REASON_MODEL)
            qv = _load_query_vault()
            hits = await asyncio.to_thread(qv, query, TOP_K, "Guidelines")
            if hits:
                context = "\n\n".join(
                    f"**{h['source_note']}** › {h['section_header']}\n{h['text'][:300]}"
                    for h in hits[:3]
                )
                await _reply_embed(message, f"Signal Context — {drug}", context, color=0xe67e22)
            else:
                await message.reply("No relevant signal context found in vault.")

        elif route == "ICSR_GENERATION":
            await _log_status(message.guild, query, route, DRAFT_MODEL)
            from modules.icsr_generator import CaseData, generate_icsr_narrative
            case = CaseData(adverse_event=query, suspect_drug=drug)
            result = await asyncio.to_thread(generate_icsr_narrative, case)
            await _reply_embed(message, f"ICSR Narrative Draft — {drug}", result.narrative, color=0x3498db)

        elif route == "LIT_MONITOR":
            await _log_status(message.guild, query, route, DRAFT_MODEL)
            from modules.lit_monitor import search_pubmed, score_relevance, generate_digest
            results = await asyncio.to_thread(search_pubmed, drug, days_back=30, max_results=3)
            if results:
                scored = await asyncio.to_thread(score_relevance, results, drug)
                digest = await asyncio.to_thread(generate_digest, drug, scored)
                await _reply_embed(
                    message,
                    f"Literature Digest — {drug}",
                    digest.digest_text or "No relevant papers found for summary.",
                    color=0x9b59b6,
                )
            else:
                await message.reply(f"No recent PubMed results for {drug}.")

        elif route == "PIPELINE_TRIGGER":
            # Parse drug and comparator from the message; fall back to active drug
            import re as _re
            vs_match = _re.search(
                r'\b([\w-]+)\s+(?:vs\.?|versus|compared?\s+to|against)\s+([\w-]+)',
                query, _re.IGNORECASE
            )
            if vs_match:
                target_drug = vs_match.group(1).lower()
                comparator_drug = vs_match.group(2).lower()
            else:
                target_drug = drug
                comparator_drug = "meropenem"

            await _log_status(message.guild, query, route, "Signal Detection")
            await message.reply(
                f"🚀 Running FAERS signal detection for **{target_drug}** vs **{comparator_drug}**... "
                f"This takes a few minutes — check #workbench-status for updates."
            )
            shared_state.set_pipeline_status("Signal Detection", "Running")

            async def _run_detection():
                try:
                    from modules.signal_detection import run_signal_detection, interpret_signals
                    logger.info("_run_detection: fetching FAERS data")
                    raw = await asyncio.to_thread(run_signal_detection, target_drug, comparator_drug)
                    logger.info(f"_run_detection: raw signals={len(raw)}, starting interpretation")
                    results = None
                    for attempt in range(3):
                        try:
                            results = await asyncio.to_thread(interpret_signals, raw, target_drug)
                            logger.info(f"_run_detection: interpretation complete, results={len(results)}")
                            break
                        except Exception as llm_err:
                            logger.warning(f"_run_detection: interpretation attempt {attempt+1} failed: {llm_err}")
                            if attempt < 2:
                                await asyncio.sleep(10)
                            else:
                                raise llm_err

                    shared_state.set_pipeline_status("Signal Detection", "Complete")
                    logger.info("_run_detection: generating clinical discussion")
                    discussion = None
                    try:
                        from shared.pdf_report import save_signal_detection_report, generate_signal_discussion
                        discussion = await asyncio.to_thread(generate_signal_discussion, target_drug, comparator_drug, results)
                        logger.info("_run_detection: discussion generated")
                    except Exception as disc_err:
                        logger.warning(f"Discussion generation failed (continuing without): {disc_err}")
                        from shared.pdf_report import save_signal_detection_report

                    logger.info("_run_detection: saving PDF")
                    try:
                        pdf_path = save_signal_detection_report(target_drug, comparator_drug, results, raw_signals=raw, discussion=discussion)
                        logger.info(f"_run_detection: PDF saved to {pdf_path}")
                        # Try Discord file attachment — DM via author + server channel
                        _discord_sent = False
                        try:
                            with open(pdf_path, "rb") as fp:
                                await message.author.send(
                                    "📄 Signal detection report ready:",
                                    file=discord.File(fp, filename=pdf_path.name),
                                )
                            _discord_sent = True
                            logger.info("_run_detection: PDF sent via Discord DM")
                        except Exception as disc_file_err:
                            logger.warning(f"Discord DM file send failed: {disc_file_err}")
                        # Also post to #signal-detection server channel
                        try:
                            sig_ch = discord.utils.get(message.guild.text_channels, name="signal-detection") if message.guild else None
                            if sig_ch:
                                with open(pdf_path, "rb") as fp2:
                                    await sig_ch.send(
                                        f"📄 **{target_drug.capitalize()} vs {comparator_drug.capitalize()}** report ready:",
                                        file=discord.File(fp2, filename=pdf_path.name),
                                    )
                                _discord_sent = True
                                logger.info("_run_detection: PDF posted to #signal-detection")
                        except Exception as ch_err:
                            logger.warning(f"Channel file send failed: {ch_err}")
                        if not _discord_sent:
                            await message.channel.send(f"📄 Report saved: `{pdf_path.name}` — check email for PDF")
                        # Always send email copy
                        positives_count = sum(1 for r in results if r.signal)
                        emailed = _send_pdf_email(
                            pdf_path,
                            subject=f"FAERS Signal Detection Report — {target_drug.capitalize()} vs {comparator_drug.capitalize()}",
                            body=(
                                f"Signal detection complete.\n\n"
                                f"Drug: {target_drug.capitalize()}\n"
                                f"Comparator: {comparator_drug.capitalize()}\n"
                                f"Evans-positive signals: {positives_count}\n\n"
                                f"Report: {pdf_path.name}\n\n"
                                f"— Argus PV Workbench"
                            ),
                        )
                        if emailed:
                            logger.info("_run_detection: PDF emailed")
                    except Exception as pdf_err:
                        logger.warning(f"PDF save failed: {pdf_err}", exc_info=True)
                    logger.info("_run_detection: sending Discord results")
                    positives = [r for r in results if r.signal]
                    if positives:
                        lines = [f"**FAERS Signal Detection: {target_drug.capitalize()} vs {comparator_drug.capitalize()}**\n"]
                        for r in positives:
                            lines.append(
                                f"**{r.reaction_pt}** — PRR {r.prr:.2f}, χ² {r.chi2:.2f}, N={r.drug_cases}\n"
                                f"{r.clinical_assessment}\n"
                                f"Confounding: {'Yes' if r.confounding_likely else 'No'} | Action: {r.regulatory_action}\n"
                            )
                        await _send_long(message.channel, "\n".join(lines), reference=message)
                    else:
                        await message.reply(
                            f"✅ Signal detection complete for **{target_drug}** vs **{comparator_drug}** — "
                            f"no signals meeting Evans criteria (PRR≥2, N≥3, χ²≥4)."
                        )
                except Exception as e:
                    shared_state.set_pipeline_status("Signal Detection", "Error")
                    await message.reply(f"❌ Signal detection failed: `{type(e).__name__}: {str(e)[:200]}`")

            asyncio.create_task(_run_detection())

        elif route == "GENERAL":
            await _log_status(message.guild, query, route, CHAT_MODEL)
            from langchain_ollama import ChatOllama
            from langchain_core.messages import HumanMessage, SystemMessage

            qv = _load_query_vault()
            hits = await asyncio.to_thread(qv, query, 3, "Guidelines")
            context_text = ""
            if hits:
                context_text = "\n\nRelevant Vault Context:\n" + "\n".join([f"- {h['text']}" for h in hits])

            workbench_ctx = _build_workbench_context()
            user_context = f"\n\n## Who You Are Talking To\n{_MICHAEL_CONTEXT}" if _MICHAEL_CONTEXT else ""
            llm = ChatOllama(model=CHAT_MODEL, base_url=OLLAMA_BASE_URL)
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
            await _send_long(message.channel, response.content, reference=message)

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
            citations = "\n".join(f"• {c}" for c in result.citations[:5]) if result.citations else None
            extra = [("Sources", citations, False)] if citations else None
            pages = _make_embed_pages(
                f"Regulatory Q&A{jur_label} — {result.confidence}",
                result.answer,
                color=0x2ecc71,
            )
            for i, embed in enumerate(pages):
                if extra and i == len(pages) - 1:
                    for name, value, inline in extra:
                        embed.add_field(name=name, value=str(value)[:1024], inline=inline)
                if i == 0:
                    await ctx.reply(embed=embed)
                else:
                    await ctx.send(embed=embed)
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
`!report`           — summary of latest completed analysis
`!email`            — email the most recent PDF report
`!help`             — this message

**Queries**
`!ask <question>`         — RAG query (all sources)
`!ask fda <question>`     — FDA sources only (21 CFR, FAERS)
`!ask ema <question>`     — EMA sources only (GVP, EudraVigilance)

**Portfolio**
`!portfolio status`       — full project portfolio overview
`!portfolio update`       — post update to #portfolio-dev

**Channel Routing** (no prefix needed in dedicated channels)
`#regulatory-qa`    → Module 1 (Regulatory Q&A)
`#meddra-coding`    → Module 2 (MedDRA Coder)
`#signal-detection` → Module 3 (Signal context)
`#icsr-generator`   → Module 4 (ICSR drafts)
`#lit-monitor`      → Module 5 (Literature)
`#portfolio-dev`    → General workbench context

**Voice**
`!voice join`           — join your voice channel
`!voice leave`          — leave voice channel
`!voice speak <text>`   — TTS output in voice channel
`!transcribe`           — transcribe audio file attachment

*All outputs are DRAFTS — senior reviewer sign-off required before regulatory use.*
"""
    await ctx.reply(embed=_make_embed("Argus Commands", text))


@bot.command(name="email")
async def cmd_email(ctx: commands.Context):
    """Email the most recent PDF report from the output directory."""
    from config import OUTPUT_DIR
    pdfs = sorted(OUTPUT_DIR.glob("*.pdf"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not pdfs:
        await ctx.send("No PDF reports found in output directory.")
        return
    latest = pdfs[0]
    await ctx.send(f"Sending `{latest.name}` to email...")
    ok = _send_pdf_email(
        latest,
        subject=f"PV Workbench Report — {latest.stem}",
        body=f"Report: {latest.name}\nSize: {latest.stat().st_size // 1024} KB\n\n— Argus PV Workbench",
    )
    if ok:
        await ctx.send(f"✅ Sent to {os.environ.get('REPORT_EMAIL_TO', 'configured address')}")
    else:
        await ctx.send("❌ Email failed — check SMTP_APP_PASSWORD in .env")


@bot.command(name="report")
async def cmd_report(ctx: commands.Context):
    """Post a summary of the latest completed analysis to the current channel."""
    text = (
        "**Vancomycin Nephrotoxicity Signal Analysis — Summary**\n\n"
        "**Study 1: Pre/Post 2020 AUC/MIC Guideline (FAERS 2015-2025)**\n"
        "Drug: Vancomycin | Comparator: Linezolid | Evans criteria (PRR>=2, N>=3, chi2>=4)\n\n"
        "PRE-2020 (trough era, 22,200 reports):\n"
        "- AKI: PRR=2.16 **SIGNAL**\n"
        "- Oliguria: PRR=11.97 **SIGNAL**\n"
        "- Renal tubular necrosis: PRR=18.10 **SIGNAL**\n\n"
        "POST-2020 (AUC/MIC era, 31,793 reports):\n"
        "- AKI: PRR=1.95 (below threshold — resolved)\n"
        "- Oliguria: PRR=1.12 (fully resolved)\n"
        "- Renal tubular necrosis: PRR=10.51 (attenuating — **still Evans-positive, regulatory priority**)\n\n"
        "**Study 2: Single-Level vs Two-Level Bayesian AUC Estimation**\n"
        "Single-level (one trough): Adequate for stable patients, AUC accuracy ~15-25%.\n"
        "Two-level required in: AKI/rapidly changing CrCl, CRRT/ECMO, BMI>40, ARC (CrCl>130), pediatrics.\n"
        "PV implication: Residual RTN signal consistent with single-level use in high-complexity ICU\n"
        "patients where two-level is pharmacologically warranted.\n\n"
        "**Output**: 13-page PDF report — ~/Desktop/vancomycin_pv_analysis/vancomycin_full_report_*.pdf\n"
        "Status: DRAFT — Requires senior reviewer sign-off before regulatory use."
    )
    await _reply_embed(ctx.message, "Vancomycin PV Analysis — Completed", text, color=0x1a6b6b)


@bot.group(name="portfolio", invoke_without_command=True)
async def portfolio_group(ctx: commands.Context):
    """Portfolio management. Subcommands: status, update"""
    await ctx.reply(
        "Portfolio commands:\n"
        "`!portfolio status` — show current project portfolio state\n"
        "`!portfolio update` — post a project update to #portfolio-dev"
    )


@portfolio_group.command(name="status")
async def portfolio_status(ctx: commands.Context):
    """Show current portfolio state across all projects."""
    text = (
        "**PV Signal Intelligence Workbench — Portfolio Status**\n"
        "GitHub: https://github.com/molszewskiPV/PV-Signal-Intelligence-Workbench\n\n"
        "**Projects under surveillance**:\n"
        "- Vancomycin (comparator: linezolid) — ANALYSES COMPLETE\n"
        "- Cefiderocol (comparator: meropenem) — Signal analysis complete\n"
        "- Colistin (comparator: meropenem) — Under surveillance\n\n"
        "**Platform modules (all operational)**:\n"
        "1. Regulatory Q&A — RAG over ICH/EMA/FDA guidelines\n"
        "2. MedDRA Coder — PT deliberation with Evans-qualified reviewer flags\n"
        "3. Signal Detection — FAERS PRR/chi2 + temporal cohort analysis\n"
        "4. ICSR Generator — E2B(R3)-aligned narrative drafts\n"
        "5. Lit Monitor — PubMed surveillance + Discord delivery\n\n"
        "**Completed deliverables**:\n"
        "- Vancomycin nephrotoxicity FAERS study (pre/post 2020 guideline) — PDF report\n"
        "- Bayesian dosing methodology analysis (single vs two-level) — included in PDF\n"
        "- Vault: 14 notes, 200 chunks, 100% P@5 retrieval benchmark\n\n"
        "**Current phase**: Phase 3 complete (integration testing). Phase 4 next: scheduling automation."
    )
    await _reply_embed(ctx.message, "Portfolio Status", text, color=0x0f2a48)


@portfolio_group.command(name="update")
async def portfolio_update(ctx: commands.Context):
    """Post a project update summary to #portfolio-dev."""
    guild = ctx.guild
    if not guild:
        await ctx.reply("This command must be run in a server channel, not a DM.")
        return

    portfolio_channel = discord.utils.get(guild.text_channels, name="portfolio-dev")
    if not portfolio_channel:
        await ctx.reply("Cannot find #portfolio-dev channel. Check server configuration.")
        return

    update_text = (
        "**Project Update — PV Signal Intelligence Workbench**\n\n"
        "**Vancomycin Project — All Analyses Complete**\n\n"
        "**Study 1: Nephrotoxicity Signal Analysis (FAERS 2015-2025)**\n"
        "The pre/post 2020 AUC/MIC guideline temporal analysis is complete. "
        "Key finding: the 2020 ASHP/IDSA/SIDP guideline change is associated with "
        "meaningful nephrotoxicity signal attenuation across the FAERS reporting population.\n"
        "- Oliguria signal fully resolved (PRR 11.97 -> 1.12)\n"
        "- AKI dropped below Evans detection threshold (PRR 2.16 -> 1.95)\n"
        "- Renal tubular necrosis attenuating but Evans-positive (18.10 -> 10.51) — regulatory priority\n\n"
        "**Study 2: Bayesian Dosing Methodology Analysis**\n"
        "Clinical review of single-level vs two-level AUC estimation methods. "
        "Conclusion: single-level adequate for stable patients; two-level mandatory in "
        "AKI, CRRT/ECMO, morbid obesity, and augmented renal clearance. "
        "Residual RTN signal mechanistically linked to suboptimal sampling strategy in complex ICU patients.\n\n"
        "**Deliverable**: Full 13-page clinical pharmacovigilance PDF report generated "
        "(statistical analysis + clinical interpretation + Bayesian methodology review).\n\n"
        "**Platform**: All 5 workbench modules operational. Discord + Streamlit dashboard active. "
        "Vault: 14 notes, 200 chunks, 100% P@5 retrieval accuracy.\n\n"
        "GitHub: https://github.com/molszewskiPV/PV-Signal-Intelligence-Workbench"
    )

    await portfolio_channel.send(embed=_make_embed(
        "Vancomycin Analysis — Project Update",
        update_text,
        color=0x1a6b6b,
    ))
    if portfolio_channel != ctx.channel:
        await ctx.reply(f"Update posted to {portfolio_channel.mention}.")


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
