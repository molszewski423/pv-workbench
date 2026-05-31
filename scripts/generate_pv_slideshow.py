"""
PV AI Workbench — PowerPoint Slideshow Generator
Produces a professional presentation for LinkedIn / portfolio use.
Run: python3 scripts/generate_pv_slideshow.py
Output: ~/Desktop/PV_Workbench_Presentation.pptx
"""

from pathlib import Path
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN

# ── Color palette ─────────────────────────────────────────────────────────────
BLUE      = RGBColor(0x0D, 0x47, 0xA1)
BLUE_LT   = RGBColor(0xBB, 0xDE, 0xFB)
BLUE_DARK = RGBColor(0x01, 0x2E, 0x6B)
TEAL      = RGBColor(0x00, 0x69, 0x5C)
AMBER     = RGBColor(0xE6, 0x51, 0x00)
WHITE     = RGBColor(0xFF, 0xFF, 0xFF)
BLACK     = RGBColor(0x21, 0x21, 0x21)
GREY      = RGBColor(0x75, 0x75, 0x75)
SLATE     = RGBColor(0x37, 0x47, 0x4F)

W = Inches(13.33)
H = Inches(7.5)

OUT = Path.home() / "Desktop" / "PV_Workbench_Presentation.pptx"


def rgb(r, g, b):
    return RGBColor(r, g, b)


def new_prs() -> Presentation:
    prs = Presentation()
    prs.slide_width  = W
    prs.slide_height = H
    return prs


def blank_slide(prs):
    return prs.slides.add_slide(prs.slide_layouts[6])


def fill_bg(slide, color):
    bg   = slide.background
    fill = bg.fill
    fill.solid()
    fill.fore_color.rgb = color


def add_rect(slide, x, y, w, h, fill, line=None):
    shape = slide.shapes.add_shape(1, Inches(x), Inches(y), Inches(w), Inches(h))
    shape.fill.solid()
    shape.fill.fore_color.rgb = fill
    if line:
        shape.line.color.rgb = line
        shape.line.width = Pt(1)
    else:
        shape.line.fill.background()
    return shape


def add_text(slide, text, x, y, w, h,
             size=18, bold=False, color=BLACK, align=PP_ALIGN.LEFT, italic=False):
    txb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf  = txb.text_frame
    tf.word_wrap = True
    p   = tf.paragraphs[0]
    p.alignment = align
    run = p.add_run()
    run.text       = text
    run.font.size  = Pt(size)
    run.font.bold  = bold
    run.font.italic = italic
    run.font.color.rgb = color
    return txb


# ── Slide 1: Title ────────────────────────────────────────────────────────────
def slide_title(prs):
    sl = blank_slide(prs)
    fill_bg(sl, BLUE_DARK)
    add_rect(sl, 0, 0, 13.33, 0.08, BLUE)

    add_text(sl, "PV AI Workbench", 0.8, 1.1, 11, 1.6,
             size=54, bold=True, color=WHITE)
    add_text(sl, "Pharmacovigilance Signal Intelligence Platform",
             0.8, 2.8, 11, 0.7, size=24, color=BLUE_LT)
    add_rect(sl, 0.8, 3.68, 4.5, 0.04, BLUE)
    add_text(sl,
             "Local-LLM-powered platform for adverse event signal detection, regulatory Q&A,\n"
             "ICSR generation, literature monitoring, and MedDRA coding — fully on-device.",
             0.8, 3.82, 11.5, 1.0, size=16, color=BLUE_LT)
    add_text(sl,
             "Michael Olszewski, PharmD, BCPS, BCCCP\n"
             "Critical Care & Infectious Disease Pharmacist",
             7.5, 6.3, 5.5, 0.9, size=13, color=BLUE_LT, align=PP_ALIGN.RIGHT)
    add_rect(sl, 0, 7.35, 13.33, 0.15, BLUE)


# ── Slide 2: The PV Problem ───────────────────────────────────────────────────
def slide_problem(prs):
    sl = blank_slide(prs)
    fill_bg(sl, WHITE)
    add_rect(sl, 0, 0, 13.33, 1.0, BLUE)
    add_text(sl, "The Pharmacovigilance Challenge", 0.4, 0.15, 12.5, 0.7,
             size=28, bold=True, color=WHITE)

    add_rect(sl, 0.4, 1.2, 3.7, 5.9, rgb(0xE3, 0xF2, 0xFD))
    add_text(sl, "FAERS at a Glance", 0.6, 1.35, 3.3, 0.5, size=15, bold=True, color=BLUE)
    stats = [
        ("18M+", "FAERS reports\ncurrently in database"),
        ("2M+", "New reports added\nannually"),
        ("~50%", "Reports with\nincomplete causality data"),
        ("17 days", "Average signal review\ntime (manual workflow)"),
    ]
    y = 1.95
    for val, lbl in stats:
        add_text(sl, val, 0.6, y, 3.3, 0.55, size=22, bold=True, color=AMBER)
        add_text(sl, lbl, 0.6, y + 0.52, 3.3, 0.55, size=11, color=SLATE)
        y += 1.28

    add_rect(sl, 4.4, 1.2, 8.5, 5.9, rgb(0xF5, 0xF5, 0xF5))
    add_text(sl, "Why Manual PV Workflows Fall Short", 4.6, 1.35, 8.1, 0.5,
             size=15, bold=True, color=BLUE)
    challenges = [
        ("Data volume", "18M+ FAERS records with new quarterly drops — impossible to manually scan for emerging signals across all reactions."),
        ("Statistical complexity", "PRR, ROR, and BCPNN each require correct 2×2 contingency table construction; errors in manual calculation are common."),
        ("Multi-source burden", "VigiBase, EMA Yellow Card, FAERS, and literature signals exist in separate systems with no unified signal view."),
        ("Guideline currency", "ICH E2A, E2B(R3), GVP Module VI, and WHO-UMC criteria update regularly — hard to track at point of signal review."),
        ("Causality subjectivity", "WHO-UMC and Naranjo assessments require structured clinical reasoning that benefits from decision-support frameworks."),
    ]
    y = 1.95
    for title, body in challenges:
        add_rect(sl, 4.5, y, 8.2, 0.08, BLUE)
        add_text(sl, title, 4.6, y + 0.12, 8.0, 0.35, size=13, bold=True, color=BLUE)
        add_text(sl, body, 4.6, y + 0.45, 8.0, 0.6, size=10.5, color=BLACK)
        y += 1.1

    add_rect(sl, 0, 7.35, 13.33, 0.15, BLUE)


# ── Slide 3: Platform Overview ────────────────────────────────────────────────
def slide_overview(prs):
    sl = blank_slide(prs)
    fill_bg(sl, WHITE)
    add_rect(sl, 0, 0, 13.33, 1.0, BLUE)
    add_text(sl, "Platform Overview", 0.4, 0.15, 12.5, 0.7,
             size=28, bold=True, color=WHITE)

    add_text(sl,
             "PV AI Workbench applies a two-tier AI oversight model: local LLMs identify signals, draft narratives, "
             "and retrieve guidelines — all requiring explicit senior pharmacist sign-off before any regulatory use.",
             0.5, 1.15, 12.3, 0.75, size=14, color=SLATE)

    modules = [
        ("Module 1", "Regulatory Q&A", BLUE,
         "Semantic search over ICH E2A, E2B(R3), E2E, GVP Module VI, Evans Criteria, MedDRA guidelines.\ngemma4:26b answers with source citations."),
        ("Module 2", "Signal Detection", rgb(0x15, 0x65, 0xC0),
         "FAERS PRR, ROR, and BCPNN disproportionality with Evans criteria filtering.\nTemporal signal trending and strength classification."),
        ("Module 3", "MedDRA Coding", TEAL,
         "gemma4:26b suggests Preferred Term codes from free-text narratives.\nHierarchy-aware with reviewer_flag logic for ambiguous cases."),
        ("Module 4", "ICSR Generator", rgb(0x6A, 0x1B, 0x9A),
         "E2B(R3)-compliant ICSR narrative drafting via gemma4:e4b.\nRule-based seriousness assessment before LLM generation."),
        ("Module 5", "Lit Monitor", rgb(0x33, 0x69, 0x1E),
         "PubMed semantic monitoring with relevance scoring.\nDiscord digest delivery with configurable alert thresholds."),
    ]

    x = 0.35
    for i, (num, name, color, desc) in enumerate(modules):
        add_rect(sl, x, 2.2, 2.45, 4.9, rgb(0xF5, 0xF8, 0xFF))
        add_rect(sl, x, 2.2, 2.45, 0.55, color)
        add_text(sl, num, x + 0.1, 2.25, 2.25, 0.28, size=9, bold=True, color=WHITE)
        add_text(sl, name, x + 0.1, 2.5, 2.25, 0.42, size=12, bold=True, color=WHITE)
        add_text(sl, desc, x + 0.1, 2.9, 2.25, 3.8, size=9.5, color=SLATE)
        x += 2.6

    add_rect(sl, 0, 7.35, 13.33, 0.15, BLUE)


# ── Slide 4: Architecture ─────────────────────────────────────────────────────
def slide_architecture(prs):
    sl = blank_slide(prs)
    fill_bg(sl, WHITE)
    add_rect(sl, 0, 0, 13.33, 1.0, BLUE)
    add_text(sl, "System Architecture", 0.4, 0.15, 12.5, 0.7,
             size=28, bold=True, color=WHITE)

    layers = [
        ("Knowledge Layer",    "Vault: 184 chunks across 6 ICH/GVP/Evans guidelines · ChromaDB · nomic-embed-text embeddings (768-dim)", rgb(0xE3, 0xF2, 0xFD), BLUE),
        ("Data Layer",         "FAERS OpenFDA API (live) · PubMed Entrez (live) · VigiBase / EMA / Yellow Card integration · ICSR input forms", rgb(0xE8, 0xF5, 0xE9), TEAL),
        ("AI Layer",           "gemma4:26b (256K context) — signal analysis, regulatory Q&A, MedDRA coding · gemma4:e4b — narrative drafting, literature digests", rgb(0xFF, 0xF3, 0xE0), AMBER),
        ("Application Layer",  "Streamlit multi-page dashboard (port 8501) · Argus Discord bot (intelligent router) · Discord delivery · bcrypt session auth", rgb(0xF3, 0xE5, 0xF5), rgb(0x6A, 0x1B, 0x9A)),
    ]

    y = 1.2
    for name, detail, bg, accent in layers:
        add_rect(sl, 0.4, y, 12.5, 1.28, bg)
        add_rect(sl, 0.4, y, 0.22, 1.28, accent)
        add_text(sl, name, 0.75, y + 0.12, 3.2, 0.45, size=13, bold=True, color=accent)
        add_text(sl, detail, 0.75, y + 0.58, 12.0, 0.6, size=11, color=SLATE)
        y += 1.45

    add_rect(sl, 0.4, 6.9, 12.5, 0.4, rgb(0xF5, 0xF5, 0xF5))
    add_text(sl,
             "Hardware: RTX 5060 Ti 16 GB VRAM  ·  32 GB RAM  ·  Ollama @ localhost:11434  ·  Benchmark: 100% P@5 (30-question retrieval evaluation)",
             0.6, 6.95, 12.1, 0.3, size=10, color=SLATE)

    add_rect(sl, 0, 7.35, 13.33, 0.15, BLUE)


# ── Slide 5: Signal Detection ─────────────────────────────────────────────────
def slide_signal(prs):
    sl = blank_slide(prs)
    fill_bg(sl, WHITE)
    add_rect(sl, 0, 0, 13.33, 1.0, BLUE)
    add_text(sl, "Module 2: Signal Detection", 0.4, 0.15, 12.5, 0.7,
             size=28, bold=True, color=WHITE)

    add_rect(sl, 0.4, 1.2, 6.0, 5.9, rgb(0xE3, 0xF2, 0xFD))
    add_text(sl, "Statistical Methods", 0.6, 1.35, 5.6, 0.45, size=15, bold=True, color=BLUE)
    methods = [
        ("PRR — Proportional Reporting Ratio",
         "(a/(a+c)) / (b/(b+d)) — the foundational FAERS disproportionality measure with 95% CI."),
        ("ROR — Reporting Odds Ratio",
         "(a/c) / (b/d) — logistic regression analog; preferred for sparse cells and rare reactions."),
        ("BCPNN — Bayesian Confidence Propagation",
         "Information component (IC) with credibility interval — VigiBase standard method."),
        ("Evans Criteria (signal threshold)",
         "PRR ≥ 2 AND N ≥ 3 AND chi² ≥ 4 — all three required simultaneously for signal qualification."),
        ("Temporal trending",
         "Pre/post year-of-interest PRR comparison to detect emerging or resolving safety signals."),
        ("Signal strength classification",
         "Strong (PRR ≥ 5), Moderate (3–5), Threshold (2–3) — drives alert color coding in reports."),
    ]
    y = 1.95
    for title, body in methods:
        add_text(sl, title, 0.6, y, 5.6, 0.35, size=11.5, bold=True, color=BLUE_DARK)
        add_text(sl, body, 0.6, y + 0.33, 5.6, 0.52, size=10, color=SLATE)
        y += 0.93

    add_rect(sl, 6.6, 1.2, 6.3, 5.9, rgb(0xF5, 0xF5, 0xF5))
    add_text(sl, "Report Outputs", 6.8, 1.35, 5.9, 0.45, size=15, bold=True, color=BLUE)
    outputs = [
        "Disproportionality signal table (PRR / ROR / chi² / strength)",
        "PRR bar chart with 95% CI — Evans-positive reactions highlighted",
        "Temporal comparison: ΔPRR pre/post cutoff with direction flag",
        "AMS-relevant category breakdown (resistance, organ injury, etc.)",
        "Top signal narrative (LLM-generated clinical context)",
        "Regulatory recommendation: class labeling review, PSUR flag, further evaluation",
        "Draft disclaimer with senior pharmacist sign-off field",
    ]
    y = 1.95
    for out in outputs:
        add_rect(sl, 6.65, y + 0.12, 0.08, 0.08, BLUE)
        add_text(sl, out, 6.85, y, 5.9, 0.52, size=10.5, color=SLATE)
        y += 0.78

    add_rect(sl, 0.4, 7.0, 12.5, 0.3, rgb(0xE3, 0xF2, 0xFD))
    add_text(sl, "Case study: Vancomycin nephrotoxicity — PRR 3.8 pre-2020 vs 5.1 post-2020; 14-page full analysis report generated on-device.",
             0.55, 7.04, 12.2, 0.25, size=9.5, color=BLUE_DARK)

    add_rect(sl, 0, 7.35, 13.33, 0.15, BLUE)


# ── Slide 6: Regulatory Q&A & Knowledge Vault ────────────────────────────────
def slide_regulatory(prs):
    sl = blank_slide(prs)
    fill_bg(sl, WHITE)
    add_rect(sl, 0, 0, 13.33, 1.0, BLUE)
    add_text(sl, "Module 1: Regulatory Q&A & Knowledge Vault", 0.4, 0.15, 12.5, 0.7,
             size=26, bold=True, color=WHITE)

    add_rect(sl, 0.4, 1.2, 5.9, 5.9, rgb(0xE3, 0xF2, 0xFD))
    add_text(sl, "Knowledge Vault Contents", 0.6, 1.35, 5.5, 0.45, size=15, bold=True, color=BLUE)
    docs = [
        ("ICH E2A", "Clinical Safety Data Management — ICSR criteria, seriousness definitions, expedited timelines (7/15-day)"),
        ("ICH E2B(R3)", "Electronic ICSR Transmission — HL7 ICSR v3 XML data elements and narrative requirements"),
        ("ICH E2E", "Pharmacovigilance Planning — signal management, PSUR structure, Risk Management Plans"),
        ("EMA GVP Module VI", "EU Signal Management Process — PRAC workflow, EudraVigilance, signal detection obligations"),
        ("Evans Criteria", "PRR signal detection thresholds, formula derivation, known biases and corrections"),
        ("MedDRA Coding", "Hierarchy (SOC→PT), PT selection rules, common coding decisions, ambiguous case guidance"),
    ]
    y = 1.95
    for name, desc in docs:
        add_text(sl, name, 0.6, y, 5.5, 0.35, size=11.5, bold=True, color=BLUE_DARK)
        add_text(sl, desc, 0.6, y + 0.33, 5.5, 0.52, size=10, color=SLATE)
        y += 0.93

    add_rect(sl, 6.6, 1.2, 6.3, 5.9, rgb(0xF5, 0xF5, 0xF5))
    add_text(sl, "RAG Pipeline", 6.8, 1.35, 5.9, 0.45, size=15, bold=True, color=BLUE)
    steps = [
        ("Ingestion", "Obsidian vault markdown → header-aware chunker → nomic-embed-text embeddings → ChromaDB (184 chunks)"),
        ("Retrieval", "Query embedding → cosine similarity search → top-k chunks with source metadata and distance scores"),
        ("Generation", "Chunks + system prompt → gemma4:26b (256K context) → answer with inline source citations"),
        ("Evaluation", "30-question gold standard benchmark — Precision@5 and MRR — currently 100% P@5"),
        ("Jurisdiction filter", "Optional FDA / EMA / ICH filter for region-specific regulatory guidance retrieval"),
    ]
    y = 1.95
    for title, body in steps:
        add_text(sl, title, 6.8, y, 5.9, 0.35, size=11.5, bold=True, color=BLUE_DARK)
        add_text(sl, body, 6.8, y + 0.33, 5.9, 0.55, size=10, color=SLATE)
        y += 1.05

    add_rect(sl, 0, 7.35, 13.33, 0.15, BLUE)


# ── Slide 7: ICSR & MedDRA ────────────────────────────────────────────────────
def slide_icsr_meddra(prs):
    sl = blank_slide(prs)
    fill_bg(sl, WHITE)
    add_rect(sl, 0, 0, 13.33, 1.0, BLUE)
    add_text(sl, "Modules 3 & 4: MedDRA Coding & ICSR Generation", 0.4, 0.15, 12.5, 0.7,
             size=26, bold=True, color=WHITE)

    # MedDRA
    add_rect(sl, 0.4, 1.2, 6.0, 5.9, rgb(0xE0, 0xF2, 0xF1))
    add_text(sl, "MedDRA Coding (Module 3)", 0.6, 1.35, 5.6, 0.45, size=15, bold=True, color=TEAL)
    add_text(sl, "gemma4:26b Thinking Mode", 0.6, 1.88, 5.6, 0.35, size=11, italic=True, color=SLATE)
    meddra = [
        ("Free-text input", "Clinician enters adverse event narrative in natural language — no coding knowledge required."),
        ("Hierarchy reasoning", "Model reasons through SOC → HLGT → HLT → PT → LLT hierarchy to select the most specific appropriate term."),
        ("Ambiguity handling", "When multiple PTs qualify, `reviewer_flag=True` triggers mandatory human review before submission."),
        ("Coding confidence", "Structured output includes suggested PT, confidence level, rationale, and alternative terms."),
        ("Validated", "Three clinical scenarios validated: nephrotoxicity, hepatotoxicity, anaphylaxis — all PTs correct."),
    ]
    y = 2.3
    for title, body in meddra:
        add_text(sl, title, 0.6, y, 5.6, 0.35, size=11.5, bold=True, color=TEAL)
        add_text(sl, body, 0.6, y + 0.33, 5.6, 0.52, size=10, color=SLATE)
        y += 0.95

    # ICSR
    add_rect(sl, 6.6, 1.2, 6.3, 5.9, rgb(0xF3, 0xE5, 0xF5))
    add_text(sl, "ICSR Generator (Module 4)", 6.8, 1.35, 5.9, 0.45, size=15, bold=True, color=rgb(0x6A, 0x1B, 0x9A))
    add_text(sl, "gemma4:e4b — E2B(R3) compliant", 6.8, 1.88, 5.9, 0.35, size=11, italic=True, color=SLATE)
    icsr_items = [
        ("Seriousness assessment", "Rule-based logic evaluates life-threatening, hospitalization, disability, and death criteria before LLM invocation."),
        ("Narrative structure", "E2B(R3) Section H.1 format: patient history, event onset, time course, intervention, outcome, causality assessment."),
        ("WHO-UMC causality", "Structured assessment across Certain / Probable / Possible / Unlikely / Unclassified / Unassessable scale."),
        ("Naranjo algorithm", "Automated scoring across 10 questions with reviewer verification flag for borderline scores."),
        ("Draft status", "All ICSRs generated as DRAFT — explicit senior pharmacist sign-off required before regulatory submission."),
    ]
    y = 2.3
    for title, body in icsr_items:
        add_text(sl, title, 6.8, y, 5.9, 0.35, size=11.5, bold=True, color=rgb(0x6A, 0x1B, 0x9A))
        add_text(sl, body, 6.8, y + 0.33, 5.9, 0.52, size=10, color=SLATE)
        y += 0.95

    add_rect(sl, 0, 7.35, 13.33, 0.15, BLUE)


# ── Slide 8: Literature Monitor & Argus Bot ───────────────────────────────────
def slide_lit_argus(prs):
    sl = blank_slide(prs)
    fill_bg(sl, WHITE)
    add_rect(sl, 0, 0, 13.33, 1.0, BLUE)
    add_text(sl, "Module 5: Literature Monitor & Argus Bot", 0.4, 0.15, 12.5, 0.7,
             size=26, bold=True, color=WHITE)

    add_rect(sl, 0.4, 1.2, 6.0, 5.9, rgb(0xE8, 0xF5, 0xE9))
    add_text(sl, "Literature Monitor (Module 5)", 0.6, 1.35, 5.6, 0.45, size=15, bold=True, color=rgb(0x33, 0x69, 0x1E))
    lit_items = [
        ("PubMed integration", "Live Entrez API queries — configurable search terms, date range, and journal filters."),
        ("Semantic scoring", "nomic-embed-text embeds each abstract; cosine similarity against a safety signal reference vector filters noise."),
        ("gemma4:e4b digest", "Top-ranked abstracts summarized into a clinical digest with key findings, implications, and action items."),
        ("Discord delivery", "Digest posted to #lit-monitor channel with signal relevance scores and PubMed links."),
        ("Alert thresholds", "Configurable relevance cutoff — high-scoring signals escalate to #signal-detection for immediate review."),
        ("Scheduled monitoring", "Runs on APScheduler — weekly automated pulls with Discord notification on new high-priority literature."),
    ]
    y = 1.95
    for title, body in lit_items:
        add_text(sl, title, 0.6, y, 5.6, 0.35, size=11.5, bold=True, color=rgb(0x33, 0x69, 0x1E))
        add_text(sl, body, 0.6, y + 0.33, 5.6, 0.52, size=10, color=SLATE)
        y += 0.93

    add_rect(sl, 6.6, 1.2, 6.3, 5.9, rgb(0x26, 0x32, 0x38))
    add_text(sl, "Argus Discord Bot", 6.8, 1.35, 5.9, 0.45, size=15, bold=True, color=BLUE_LT)
    add_text(sl, "Intelligent intent router — auto-routes messages to modules",
             6.8, 1.88, 5.9, 0.35, size=10, italic=True, color=GREY)
    argus_items = [
        ("Intent detection", "gemma4:26b classifies each Discord message → routes to REGULATORY_QA, SIGNAL_DETECTION, MEDDRA_CODING, ICSR, or LIT_MONITOR."),
        ("Route logging", "Every request creates a #workbench-status embed: input, detected intent, model assigned, processing time."),
        ("Shared state", "JSON-backed sync between Discord and Streamlit dashboard — `!drug <name>` updates sidebar in real time."),
        ("Portfolio commands", "`!report` — current project status with full clinical details. `!portfolio status/update` for project tracking."),
        ("Channel routing", "#signal-detection, #regulatory-qa, #meddra-coding, #lit-monitor, #portfolio-dev all handled contextually."),
    ]
    y = 2.3
    for title, body in argus_items:
        add_text(sl, title, 6.8, y, 5.9, 0.35, size=11.5, bold=True, color=BLUE_LT)
        add_text(sl, body, 6.8, y + 0.33, 5.9, 0.55, size=10, color=WHITE)
        y += 1.0

    add_rect(sl, 0, 7.35, 13.33, 0.15, BLUE)


# ── Slide 9: Technical Stack ──────────────────────────────────────────────────
def slide_tech(prs):
    sl = blank_slide(prs)
    fill_bg(sl, WHITE)
    add_rect(sl, 0, 0, 13.33, 1.0, BLUE)
    add_text(sl, "Technical Stack", 0.4, 0.15, 12.5, 0.7,
             size=28, bold=True, color=WHITE)

    categories = [
        ("AI / LLM", BLUE, [
            "gemma4:26b — signal analysis, regulatory Q&A, MedDRA (256K ctx)",
            "gemma4:e4b — ICSR narrative drafting, literature digests",
            "nomic-embed-text — 768-dim semantic embeddings",
            "Ollama — local GPU serving (RTX 5060 Ti 16 GB VRAM)",
            "LangChain LCEL — prompt chains, ChatOllama",
            "think=False — prevents token exhaustion on thinking models",
        ]),
        ("Data & Analytics", TEAL, [
            "FDA OpenFDA API — live FAERS adverse event pulls",
            "NCBI Bio.Entrez — PubMed structured XML retrieval",
            "pandas / scipy — PRR/ROR math, chi-squared, signal tables",
            "ChromaDB — persistent vector store (184 PV guideline chunks)",
            "python-frontmatter — Obsidian vault frontmatter parsing",
            "Benchmark: 30-question gold standard, 100% Precision@5",
        ]),
        ("Application", rgb(0x6A, 0x1B, 0x9A), [
            "Streamlit — multi-page dashboard (port 8501)",
            "streamlit-authenticator — bcrypt sessions",
            "fpdf2 — full-length regulatory PDF reports",
            "discord.py — Argus bot + alert delivery",
            "APScheduler — weekly automated literature scans",
            "Gateway (port 8500) — Clinical Intelligence Portal",
        ]),
    ]

    x = 0.35
    for cat, color, items in categories:
        add_rect(sl, x, 1.2, 4.15, 6.0, rgb(0xF5, 0xF8, 0xFF))
        add_rect(sl, x, 1.2, 4.15, 0.6, color)
        add_text(sl, cat, x + 0.15, 1.28, 3.85, 0.45, size=14, bold=True, color=WHITE)
        y = 2.0
        for item in items:
            add_rect(sl, x + 0.12, y + 0.14, 0.07, 0.07, color)
            add_text(sl, item, x + 0.28, y, 3.75, 0.55, size=10.5, color=SLATE)
            y += 0.84
        x += 4.35

    add_rect(sl, 0, 7.35, 13.33, 0.15, BLUE)


# ── Slide 10: Clinical Impact ─────────────────────────────────────────────────
def slide_impact(prs):
    sl = blank_slide(prs)
    fill_bg(sl, BLUE_DARK)
    add_rect(sl, 0, 0, 13.33, 0.08, BLUE)

    add_text(sl, "Clinical Impact", 0.6, 0.5, 12.0, 0.9,
             size=38, bold=True, color=WHITE)
    add_text(sl, "Built by an ICU pharmacist who has reviewed real adverse event cases — not a demo, a working tool.",
             0.6, 1.42, 12.0, 0.5, size=16, color=BLUE_LT)

    impacts = [
        ("100% P@5 retrieval", "30-question pharmacovigilance benchmark — all top-5 retrieved chunks include the correct regulatory source."),
        ("Multi-standard coverage", "PRR, ROR, and BCPNN all computed simultaneously — no need to switch between databases for signal confirmation."),
        ("Full oversight model", "Every AI output carries explicit DRAFT status. Senior reviewer sign-off enforced by design across all five modules."),
        ("Regulatory-grade output", "ICSR narratives formatted to E2B(R3) Section H.1 spec. MedDRA PTs include hierarchy context and confidence scores."),
        ("Zero data egress", "FAERS uses public de-identified data. Vault RAG is fully on-device. No patient data sent to any external service."),
    ]

    y = 2.15
    for title, body in impacts:
        add_rect(sl, 0.6, y, 11.8, 0.08, BLUE)
        add_text(sl, title, 0.6, y + 0.15, 3.8, 0.45, size=13, bold=True, color=BLUE_LT)
        add_text(sl, body, 4.55, y + 0.12, 7.8, 0.72, size=11.5, color=WHITE)
        y += 0.98

    add_rect(sl, 0.6, 7.0, 12.1, 0.28, BLUE)
    add_text(sl,
             "Michael Olszewski, PharmD, BCPS, BCCCP  ·  Critical Care & Infectious Disease Pharmacist  ·  molszewski423@gmail.com",
             0.75, 7.03, 11.8, 0.24, size=10, color=WHITE, align=PP_ALIGN.CENTER)

    add_rect(sl, 0, 7.35, 13.33, 0.15, BLUE)


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    prs = new_prs()
    slide_title(prs)
    slide_problem(prs)
    slide_overview(prs)
    slide_architecture(prs)
    slide_signal(prs)
    slide_regulatory(prs)
    slide_icsr_meddra(prs)
    slide_lit_argus(prs)
    slide_tech(prs)
    slide_impact(prs)
    prs.save(str(OUT))
    print(f"Saved: {OUT}  ({len(prs.slides)} slides)")


if __name__ == "__main__":
    main()
