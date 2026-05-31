"""
PV AI Workbench — Streamlit Dashboard

Run from project root:
    PYTHONPATH=src streamlit run src/dashboard/app.py
"""

import json
import subprocess
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))
import shared_state
from auth import require_auth, auth_sidebar
from config import CHROMA_PATH, COLLECTION_NAME, OLLAMA_BASE_URL, REASON_MODEL, DRAFT_MODEL
from projects import list_projects, load_project

st.set_page_config(
    page_title="PV AI Workbench",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)

require_auth()


# ── Data helpers (cached) ────────────────────────────────────────────────────

@st.cache_data(ttl=20)
def _ollama_tags() -> dict:
    """Available models: {name: {size_mb, modified}}"""
    try:
        req = urllib.request.Request(
            f"{OLLAMA_BASE_URL}/api/tags", headers={"User-Agent": "pv-workbench"}
        )
        with urllib.request.urlopen(req, timeout=3) as r:
            data = json.loads(r.read())
        return {
            m["name"]: {
                "size_mb": m["size"] // 1024 // 1024,
                "modified": m.get("modified_at", "")[:10],
            }
            for m in data.get("models", [])
        }
    except Exception:
        return {}


@st.cache_data(ttl=10)
def _ollama_running() -> list[str]:
    """Model names currently loaded into VRAM."""
    try:
        req = urllib.request.Request(
            f"{OLLAMA_BASE_URL}/api/ps", headers={"User-Agent": "pv-workbench"}
        )
        with urllib.request.urlopen(req, timeout=3) as r:
            data = json.loads(r.read())
        return [m["name"] for m in data.get("models", [])]
    except Exception:
        return []


@st.cache_data(ttl=60)
def _argus_status() -> tuple[str, str]:
    """(active_state, started_timestamp) — checks heartbeat file written by argus pod."""
    import time
    hb = OUTPUT_DIR / ".argus_heartbeat"
    try:
        mtime = hb.stat().st_mtime
        age = time.time() - mtime
        if age < 120:  # heartbeat within last 2 minutes = alive
            started = __import__("datetime").datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
            return "active/running", started
        return "inactive/dead", ""
    except FileNotFoundError:
        return "inactive/dead", ""
    except Exception:
        return "unknown", ""


@st.cache_data(ttl=60)
def _vault_chunks() -> int:
    try:
        import chromadb
        client = chromadb.PersistentClient(path=str(CHROMA_PATH))
        col = client.get_collection(COLLECTION_NAME)
        return col.count()
    except Exception:
        return -1


@st.cache_data(ttl=5)
def _gpu_info() -> str | None:
    try:
        out = subprocess.check_output(
            ["nvidia-smi",
             "--query-gpu=memory.used,memory.total,utilization.gpu",
             "--format=csv,noheader,nounits"],
            text=True, timeout=5,
        ).strip()
        used, total, util = [x.strip() for x in out.split(",")]
        used_gb = int(used) / 1024
        total_gb = int(total) / 1024
        return f"{used_gb:.1f} / {total_gb:.1f} GB used · {util}% GPU util"
    except Exception:
        return None


# ── Sidebar ──────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## 🔬 PV AI Workbench")
    st.caption("Clinical Pharmacovigilance · Local LLM")

    st.markdown("---")
    st.markdown("**Active Project**")
    projects = list_projects()
    if projects:
        current_drug = shared_state.get_active_drug()
        drug_names = [p.drug_name for p in projects]
        try:
            idx = drug_names.index(current_drug)
        except ValueError:
            idx = 0
        selected_name = st.selectbox(
            "Drug", drug_names, index=idx, label_visibility="collapsed"
        )
        if selected_name != current_drug:
            shared_state.set_active_drug(selected_name)
            st.rerun()
        active_project = load_project(selected_name)
        st.session_state["active_project"] = active_project
        proj = active_project
        st.markdown(f"**{proj.drug_name.capitalize()}**")
        if hasattr(proj, "comparator") and proj.comparator:
            st.caption(f"Comparator: {proj.comparator}")
    else:
        st.warning("No projects configured.")

    st.markdown("---")
    st.markdown("**Navigation**")
    st.page_link("app.py", label="Home", icon="🏠")
    st.page_link("pages/1_Regulatory_QA.py", label="Regulatory Q&A", icon="📋")
    st.page_link("pages/2_MedDRA_Coder.py", label="MedDRA Coder", icon="🏷️")
    st.page_link("pages/3_Signal_Detection.py", label="Signal Detection", icon="📊")
    st.page_link("pages/4_ICSR_Generator.py", label="ICSR Generator", icon="📝")
    st.page_link("pages/5_Lit_Monitor.py", label="Lit Monitor", icon="📚")

    auth_sidebar()
    st.markdown("---")
    st.caption("All AI outputs require senior clinical reviewer sign-off before regulatory use.")


# ── Main ─────────────────────────────────────────────────────────────────────

st.title("PV AI Workbench")
st.caption("Pharmacovigilance Signal Intelligence · Local-First · Privacy-Preserving")
st.markdown("**Michael Olszewski, PharmD, BCPS, BCCCP** · Creator & Senior Clinical Reviewer")


# ═══════════════════════════════════════════════════════════════════════════════
# SYSTEM STATUS
# ═══════════════════════════════════════════════════════════════════════════════

st.markdown("### System Status")

tags      = _ollama_tags()
running   = _ollama_running()
argus_state, argus_started = _argus_status()
chunks    = _vault_chunks()
gpu       = _gpu_info()

CORE_MODELS = [
    ("gemma4:26b",             "Reasoning",  "Signal analysis · Regulatory Q&A · MedDRA"),
    ("gemma4:e4b",             "Drafting",   "ICSR narratives · Literature digests"),
    ("nomic-embed-text:latest","Embeddings", "Vault RAG retrieval"),
]

status_cols = st.columns(len(CORE_MODELS) + 2)

for col, (mname, role, desc) in zip(status_cols, CORE_MODELS):
    base = mname.split(":")[0]
    info = tags.get(mname) or next(
        (v for k, v in tags.items() if k.startswith(base)), {}
    )
    in_vram  = any(base in r for r in running)
    available = bool(info)

    if in_vram:
        badge, bcolor = "● In VRAM", "green"
    elif available:
        badge, bcolor = "● Available", "blue"
    else:
        badge, bcolor = "● Not found", "red"

    size_str = f"{info['size_mb']:,} MB" if info else "—"

    with col:
        with st.container(border=True):
            st.markdown(f"**{role}**")
            st.caption(f"`{mname}`")
            st.caption(size_str)
            if bcolor == "green":
                st.success(badge)
            elif bcolor == "blue":
                st.info(badge)
            else:
                st.error(badge)

# Argus card
with status_cols[-2]:
    with st.container(border=True):
        st.markdown("**Argus Bot**")
        st.caption("`argus-bot.service`")
        argus_ok = "active" in argus_state
        if argus_ok and argus_started:
            try:
                # systemctl format: "Thu 2026-05-07 08:49:48 EDT"
                ts_clean = " ".join(argus_started.split()[1:3])
                started_dt = datetime.strptime(ts_clean, "%Y-%m-%d %H:%M:%S")
                delta = datetime.now() - started_dt
                hours = int(delta.total_seconds() // 3600)
                mins  = int((delta.total_seconds() % 3600) // 60)
                uptime = f"{hours}h {mins}m" if hours else f"{mins}m"
            except Exception:
                uptime = ""
            st.caption(f"Up {uptime}" if uptime else "Running")
            st.success("● Running")
        else:
            st.caption("—")
            st.error("● Stopped")

# Vault card
with status_cols[-1]:
    with st.container(border=True):
        st.markdown("**Knowledge Vault**")
        st.caption("ChromaDB · nomic-embed-text")
        if chunks > 0:
            st.caption(f"{chunks} chunks")
            st.success("● Indexed")
        else:
            st.caption("Not indexed")
            st.error("● Offline")

# GPU row
if gpu:
    st.caption(f"🖥️  RTX 5060 Ti · {gpu}")

col_ref, col_btn_refresh = st.columns([6, 1])
with col_btn_refresh:
    if st.button("↻ Refresh", key="refresh_status"):
        st.cache_data.clear()
        st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# COMMAND CENTER
# ═══════════════════════════════════════════════════════════════════════════════

st.markdown("---")
st.markdown("### Command Center")
st.caption(
    "**Commands:** `status` · `models` · `run signal <drug>` · "
    "`ask <regulatory question>` · `project <drug>` · `lit <drug>` · "
    "or type anything for LLM routing"
)

if "cmd_history" not in st.session_state:
    st.session_state.cmd_history = []

col_input, col_run = st.columns([6, 1])
with col_input:
    cmd_input = st.text_input(
        "command",
        placeholder="run signal vancomycin  |  ask what are Evans criteria  |  status",
        label_visibility="collapsed",
        key="cmd_text",
    )
with col_run:
    run_pressed = st.button("Run", type="primary", use_container_width=True)


def _execute_cmd(raw: str) -> str:
    cmd = raw.strip()
    lower = cmd.lower()

    # ── status / models ──────────────────────────────────────────────────────
    if lower in ("status", "models", "health", "model status"):
        lines = ["**Model Status**\n"]
        for mname, role, _ in CORE_MODELS:
            base = mname.split(":")[0]
            info = tags.get(mname) or next((v for k, v in tags.items() if k.startswith(base)), {})
            ok   = "✓" if info else "✗"
            size = f"{info['size_mb']:,} MB" if info else "not found"
            vram = " · in VRAM" if any(base in r for r in running) else ""
            lines.append(f"- {ok} **{role}** `{mname}` — {size}{vram}")
        argus_line = "✓ running" if "active" in argus_state else "✗ stopped"
        lines.append(f"\n**Argus Bot**: {argus_line}")
        lines.append(f"**Vault**: {chunks} chunks")
        if gpu:
            lines.append(f"**GPU**: {gpu}")
        return "\n".join(lines)

    # ── project info ─────────────────────────────────────────────────────────
    if lower.startswith("project"):
        parts = cmd.split()
        drug = parts[1] if len(parts) > 1 else shared_state.get_active_drug()
        try:
            p = load_project(drug)
            lines = [f"**Project: {p.drug_name.capitalize()}**"]
            if hasattr(p, "comparator") and p.comparator:
                lines.append(f"- Comparator: {p.comparator}")
            if hasattr(p, "indication") and p.indication:
                lines.append(f"- Indication: {p.indication}")
            return "\n".join(lines)
        except Exception:
            configured = [p.drug_name for p in list_projects()]
            return f"Project `{drug}` not found. Configured: {configured}"

    # ── signal analysis ──────────────────────────────────────────────────────
    if lower.startswith(("run signal", "signal ")):
        parts = cmd.split()
        offset = 2 if lower.startswith("run signal") else 1
        drug = parts[offset] if len(parts) > offset else shared_state.get_active_drug()
        shared_state.set_active_drug(drug)
        return (
            f"**Signal Detection → {drug.capitalize()}**\n\n"
            f"Active project set to `{drug}`. "
            f"Open **Signal Detection** from the sidebar to run PRR/chi² analysis. "
            f"The drug will be pre-selected from shared state."
        )

    # ── lit monitor ──────────────────────────────────────────────────────────
    if lower.startswith("lit "):
        drug = cmd[4:].strip()
        shared_state.set_active_drug(drug)
        return (
            f"**Lit Monitor → {drug.capitalize()}**\n\n"
            f"Active project set to `{drug}`. "
            f"Open **Lit Monitor** from the sidebar to run PubMed search. "
            f"Results will be delivered to #lit-monitor on Discord."
        )

    # ── regulatory Q&A (runs inline) ─────────────────────────────────────────
    if lower.startswith("ask "):
        question = cmd[4:].strip()
        if not question:
            return "Usage: `ask <question>`  e.g. `ask what are Evans criteria`"
        with st.spinner(f"Querying {REASON_MODEL} via RAG..."):
            try:
                from modules.regulatory_qa import answer_regulatory_question
                result = answer_regulatory_question(question)
                lines = [f"**Q:** {question}\n", f"**A:** {result.answer}"]
                if result.sources:
                    lines.append(f"\n*Sources: {', '.join(result.sources[:3])}*")
                if result.confidence:
                    lines.append(f"*Confidence: {result.confidence}*")
                return "\n".join(lines)
            except Exception as e:
                return f"Q&A error: {e}\n\nNavigate to **Regulatory Q&A** page for the full interface."

    # ── help ─────────────────────────────────────────────────────────────────
    if lower in ("help", "?", "commands"):
        return (
            "**Available commands**\n\n"
            "| Command | Description |\n"
            "|---|---|\n"
            "| `status` / `models` | Show model and system status |\n"
            "| `run signal <drug>` | Set active drug for Signal Detection |\n"
            "| `ask <question>` | Run regulatory Q&A inline via RAG |\n"
            "| `project <drug>` | Show project configuration |\n"
            "| `lit <drug>` | Set active drug for Lit Monitor |\n"
            "| Any other text | Routed to LLM for interpretation |\n"
        )

    # ── LLM fallback ─────────────────────────────────────────────────────────
    with st.spinner(f"Routing via {DRAFT_MODEL}..."):
        try:
            payload = json.dumps({
                "model": DRAFT_MODEL,
                "prompt": (
                    f"You are a pharmacovigilance AI assistant embedded in a signal intelligence workbench. "
                    f"The user entered: '{cmd}'\n\n"
                    f"Available commands: status, run signal <drug>, ask <question>, project <drug>, lit <drug>.\n"
                    f"If the input looks like a command, explain what it does and suggest the correct syntax. "
                    f"If it's a question, answer it directly and concisely (3-5 sentences max). "
                    f"Focus on pharmacovigilance, FAERS, regulatory science, or drug safety topics."
                ),
                "stream": False,
            }).encode()
            req = urllib.request.Request(
                f"{OLLAMA_BASE_URL}/api/generate",
                data=payload,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=90) as r:
                resp = json.loads(r.read())
            return resp.get("response", "No response.").strip()
        except Exception as e:
            return (
                f"Unrecognized command. Type `help` for available commands.\n\nError: {e}"
            )


if run_pressed and cmd_input:
    result = _execute_cmd(cmd_input)
    st.session_state.cmd_history.insert(0, {
        "cmd": cmd_input,
        "result": result,
        "ts": datetime.now().strftime("%H:%M:%S"),
    })

# Render history (most recent first, first one open)
if st.session_state.cmd_history:
    for i, entry in enumerate(st.session_state.cmd_history[:8]):
        with st.expander(f"`{entry['cmd']}`  —  {entry['ts']}", expanded=(i == 0)):
            st.markdown(entry["result"])
    col_clr, _ = st.columns([1, 5])
    with col_clr:
        if st.button("Clear history", key="clear_hist"):
            st.session_state.cmd_history = []
            st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# MODULE CARDS
# ═══════════════════════════════════════════════════════════════════════════════

st.markdown("---")
st.markdown("### Modules")

MODULES = [
    ("📋", "Regulatory Q&A",  "gemma4:26b",         "RAG over ICH/EMA/FDA guidelines. Cited answers with confidence."),
    ("🏷️", "MedDRA Coder",    "gemma4:26b",         "Thinking-mode PT deliberation. Reviewer-flag enforced."),
    ("📊", "Signal Detection", "gemma4:26b + PRR",   "FAERS PRR/chi² · Evans criteria · Temporal cohort analysis."),
    ("📝", "ICSR Generator",  "gemma4:e4b",          "E2B(R3)-aligned narrative drafts. Seriousness auto-assessed."),
    ("📚", "Lit Monitor",     "gemma4:e4b + PubMed", "PubMed search · Relevance scoring · Discord digest delivery."),
]

mod_cols = st.columns(len(MODULES))
for col, (icon, name, model, desc) in zip(mod_cols, MODULES):
    with col:
        with st.container(border=True):
            st.markdown(f"### {icon} {name}")
            st.caption(f"`{model}`")
            st.markdown(desc)
            st.success("✓ Active")


# ═══════════════════════════════════════════════════════════════════════════════
# WORKFLOW GUIDE
# ═══════════════════════════════════════════════════════════════════════════════

st.markdown("---")
col_a, col_b = st.columns(2)

with col_a:
    st.markdown("### Recommended Workflows")
    with st.expander("**New Signal Investigation**", expanded=False):
        st.markdown("""
1. **Signal Detection** → run PRR for drug of interest
2. **MedDRA Coder** → validate reaction terms against FAERS PTs
3. **Regulatory Q&A** → check reporting obligations (ICH E2A timelines)
4. **ICSR Generator** → draft initial case narrative
5. **Lit Monitor** → search for supporting literature
        """)
    with st.expander("**Pre/Post Guideline Change Analysis**", expanded=False):
        st.markdown("""
Use **Signal Detection** with temporal filter:
- Set *Start year* / *End year* to define cohort windows
- Compare PRR and case counts across time periods
- Example: Vancomycin nephrotoxicity, Pre-2020 vs Post-2020 (AUC/MIC)
        """)
    with st.expander("**Literature-Driven Signal Validation**", expanded=False):
        st.markdown("""
1. **Lit Monitor** → run search with custom date range
2. Review escalation flags
3. Cross-reference with **Signal Detection** PRR data
4. Generate ICSR narrative if a reportable case is identified
        """)

with col_b:
    st.markdown("### Quick Reference")
    with st.expander("**Evans Criteria (Signal Threshold)**"):
        st.markdown("""
All three must be met simultaneously:
- **PRR ≥ 2.0** — at least 2× overrepresented vs. background
- **N ≥ 3** — minimum 3 drug-reaction co-reports
- **chi² ≥ 4.0** — statistical significance threshold

*Yates' correction applied when any expected cell < 5.*
*Continuity correction (b=0.5) applied for background zeros.*
        """)
    with st.expander("**Reporting Timelines (ICH E2A)**"):
        st.markdown("""
| Case Type | Timeline |
|---|---|
| Fatal/life-threatening SUSAR | 7 days (expedited) |
| Other serious unexpected SAR | 15 days (expedited) |
| Non-serious / expected | Periodic (PSUR/PADER) |
        """)
    with st.expander("**Seriousness Criteria (ICH E2A)**"):
        st.markdown("""
An adverse event is **serious** if it:
- Results in **death**
- Is **life-threatening**
- Requires **inpatient hospitalization** or prolongation
- Results in **persistent/significant disability**
- Is a **congenital anomaly**
- Is an **important medical event** per regulatory judgment
        """)

st.markdown("---")
st.caption(
    f"PV AI Workbench · Local LLM Stack · "
    f"gemma4:26b reasoning · gemma4:e4b drafting · "
    f"Built by Michael Olszewski, PharmD BCPS BCCCP"
)
