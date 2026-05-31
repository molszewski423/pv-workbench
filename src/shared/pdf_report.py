"""
PV AI Workbench — PDF Report Generator

Auto-saves timestamped PDF reports to OUTPUT_DIR for every module result.
Color scheme: PV navy (#1A3A5C) / amber (#E67E22).
All reports are DRAFTS requiring senior reviewer sign-off.
"""

from __future__ import annotations
import io
from collections import Counter
from datetime import datetime
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from fpdf import FPDF

from config import OUTPUT_DIR, REASON_MODEL, OLLAMA_BASE_URL

# ── Palette ───────────────────────────────────────────────────────────────────
NAVY     = (26, 58, 92)
NAVY_LT  = (232, 240, 248)
AMBER    = (230, 119, 0)
AMBER_LT = (255, 243, 224)
RED      = (198, 40, 40)
RED_LT   = (255, 235, 238)
GREEN    = (46, 125, 50)
GREEN_LT = (232, 245, 233)
GREY_LT  = (245, 245, 245)
WHITE    = (255, 255, 255)
BLACK    = (33, 33, 33)
GREY_MID = (117, 117, 117)

AUTHOR = "Michael Olszewski, PharmD, BCPS, BCCCP"
DRAFT_NOTE = "DRAFT — AI-generated. Requires senior reviewer sign-off before regulatory use."


def _s(text) -> str:
    return (
        str(text)
        .replace("—", "-").replace("–", "-")
        .replace("‘", "'").replace("’", "'")
        .replace("“", '"').replace("”", '"')
        .replace("•", "-").replace("·", "-")
        .replace("≥", ">=").replace("²", "2")
        .replace("χ", "chi")
        .encode("latin-1", errors="replace").decode("latin-1")
    )


def _wrap(pdf: "PVReport", text: str, width: float, size: float) -> list[str]:
    pdf.set_font_size(size)
    words, lines, cur = _s(text).split(), [], ""
    for w in words:
        test = (cur + " " + w).strip()
        if pdf.get_string_width(test) <= width:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines or [""]


class PVReport(FPDF):
    def __init__(self, title: str):
        super().__init__()
        self._title = _s(title)
        self.set_margins(10, 22, 10)
        self.set_auto_page_break(auto=True, margin=20)
        self.t_margin = 22

    def cell(self, w=0, h=0, txt="", border=0, ln=0, align="", fill=False, link=""):
        return super().cell(w, h, _s(txt), border, ln, align, fill, link)

    def header(self):
        self.set_fill_color(*NAVY)
        self.rect(0, 0, 210, 13, "F")
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(*WHITE)
        self.set_xy(10, 3)
        self.cell(130, 7, _s(self._title), ln=False)
        self.set_font("Helvetica", "", 8)
        self.set_xy(140, 3)
        self.cell(60, 7, AUTHOR, ln=False, align="R")
        self.set_text_color(*BLACK)
        self.set_y(16)

    def footer(self):
        self.set_y(-14)
        self.set_font("Helvetica", "I", 7)
        self.set_text_color(*GREY_MID)
        self.cell(0, 5, _s(DRAFT_NOTE), align="C")
        self.set_y(-9)
        self.cell(0, 5, f"Page {self.page_no()}", align="C")
        self.set_text_color(*BLACK)

    def cover(self, subtitle: str, drug: str = "", generated: str = ""):
        self.add_page()
        self.set_fill_color(*NAVY)
        self.rect(0, 0, 210, 55, "F")
        self.set_font("Helvetica", "B", 20)
        self.set_text_color(*WHITE)
        self.set_xy(10, 14)
        self.cell(190, 10, _s(self._title), align="C")
        self.set_font("Helvetica", "", 12)
        self.set_xy(10, 27)
        self.cell(190, 8, _s(subtitle), align="C")
        if drug:
            self.set_font("Helvetica", "B", 11)
            self.set_xy(10, 37)
            self.cell(190, 7, _s(drug), align="C")
        self.set_text_color(*BLACK)
        self.set_y(62)
        self.set_font("Helvetica", "", 9)
        self.set_text_color(*GREY_MID)
        self.cell(0, 6, f"Generated: {generated or datetime.now().strftime('%Y-%m-%d %H:%M')}", align="C")
        self.set_text_color(*BLACK)
        self.ln(8)
        self.set_fill_color(*AMBER)
        self.rect(10, self.get_y(), 190, 0.5, "F")
        self.ln(4)

    def section(self, title: str):
        self.ln(3)
        self.set_fill_color(*NAVY_LT)
        self.set_draw_color(*NAVY)
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(*NAVY)
        self.set_fill_color(*NAVY_LT)
        self.cell(0, 7, _s(f"  {title}"), border="L", fill=True, ln=True)
        self.set_text_color(*BLACK)
        self.ln(1)

    def body(self, text: str, size: float = 9):
        self.set_font("Helvetica", "", size)
        lines = _wrap(self, text, 190, size)
        for line in lines:
            self.cell(0, 5, _s(line), ln=True)

    def label_value(self, label: str, value: str, size: float = 9):
        self.set_font("Helvetica", "B", size)
        self.cell(40, 5, _s(label + ":"), ln=False)
        self.set_font("Helvetica", "", size)
        lines = _wrap(self, value, 148, size)
        self.cell(148, 5, _s(lines[0]), ln=True)
        for line in lines[1:]:
            self.set_x(50)
            self.cell(148, 5, _s(line), ln=True)

    def callout(self, text: str, color: tuple, bg: tuple):
        self.set_fill_color(*bg)
        self.set_draw_color(*color)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(*color)
        y0 = self.get_y()
        lines = _wrap(self, text, 180, 8)
        h = len(lines) * 5 + 4
        self.rect(10, y0, 190, h, "FD")
        self.set_xy(14, y0 + 2)
        for i, line in enumerate(lines):
            self.set_x(14)
            self.cell(182, 5, _s(line), ln=True)
        self.set_y(y0 + h + 2)
        self.set_text_color(*BLACK)


# ── Signal Detection helpers ───────────────────────────────────────────────────

def _embed_figure(pdf: "PVReport", fig, max_width: float = 190, padding: float = 4) -> None:
    fig_w, fig_h = fig.get_size_inches()
    img_h = max_width * (fig_h / fig_w)
    if pdf.get_y() + img_h > pdf.h - 22:
        pdf.add_page()
        pdf.set_y(28)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight", facecolor="white")
    buf.seek(0)
    pdf.image(buf, x=10, y=pdf.get_y(), w=max_width, h=img_h)
    pdf.set_y(pdf.get_y() + img_h + padding)
    plt.close(fig)


def _prr_forest_plot(positives: list, drug: str) -> plt.Figure:
    """Horizontal bar chart of PRR for all positive signals, sorted descending."""
    top = sorted(positives, key=lambda r: r.prr, reverse=True)[:20]
    labels = [_s(r.reaction_pt) for r in reversed(top)]
    prrs   = [r.prr for r in reversed(top)]
    n_vals = [r.drug_cases for r in reversed(top)]

    action_map = {"expedited": "#C62828", "routine": "#E67E22", "monitor": "#1A3A5C", "none": "#2E7D32"}
    colors = [action_map.get(getattr(r, "regulatory_action", "monitor").lower(), "#1A3A5C") for r in reversed(top)]

    fig, ax = plt.subplots(figsize=(10, max(4, len(top) * 0.45)))
    bars = ax.barh(labels, prrs, color=colors, edgecolor="white", height=0.65)
    ax.axvline(x=2.0, color="#E67E22", linestyle="--", linewidth=1.2, label="Evans threshold (PRR=2)")
    ax.axvline(x=1.0, color="#888", linestyle=":", linewidth=0.8)

    for bar, n in zip(bars, n_vals):
        ax.text(bar.get_width() + 0.05, bar.get_y() + bar.get_height() / 2,
                f"N={n}", va="center", fontsize=7, color="#333")

    ax.set_xlabel("Proportional Reporting Ratio (PRR)", fontsize=9)
    ax.set_title(f"PRR Forest Plot — {drug.capitalize()} vs Comparator\n(Top {len(top)} Evans-positive signals)", fontsize=10, fontweight="bold")
    ax.spines[["top", "right"]].set_visible(False)

    legend_patches = [
        mpatches.Patch(color="#C62828", label="Expedited"),
        mpatches.Patch(color="#E67E22", label="Routine"),
        mpatches.Patch(color="#1A3A5C", label="Monitor"),
        mpatches.Patch(color="#2E7D32", label="None"),
    ]
    ax.legend(handles=legend_patches, fontsize=7, loc="lower right")
    fig.tight_layout()
    return fig


def _action_pie(positives: list) -> plt.Figure:
    counts = Counter(getattr(r, "regulatory_action", "monitor").lower() for r in positives)
    order  = ["expedited", "routine", "monitor", "none"]
    colors_map = {"expedited": "#C62828", "routine": "#E67E22", "monitor": "#1A3A5C", "none": "#2E7D32"}
    labels, sizes, colors = [], [], []
    for k in order:
        if counts.get(k, 0):
            labels.append(k.capitalize())
            sizes.append(counts[k])
            colors.append(colors_map[k])

    fig, ax = plt.subplots(figsize=(4.5, 3.5))
    wedges, texts, autotexts = ax.pie(
        sizes, labels=labels, colors=colors, autopct="%1.0f%%",
        startangle=140, pctdistance=0.75,
        wedgeprops=dict(edgecolor="white", linewidth=1.5),
    )
    for t in autotexts:
        t.set_fontsize(9)
        t.set_color("white")
        t.set_fontweight("bold")
    ax.set_title("Signals by Regulatory Action", fontsize=9, fontweight="bold")
    fig.tight_layout()
    return fig


def _chi2_scatter(positives: list) -> plt.Figure:
    """PRR vs chi2 scatter — size = N, color = action."""
    action_map = {"expedited": "#C62828", "routine": "#E67E22", "monitor": "#1A3A5C", "none": "#2E7D32"}
    fig, ax = plt.subplots(figsize=(8, 4))
    for r in positives:
        c = action_map.get(getattr(r, "regulatory_action", "monitor").lower(), "#1A3A5C")
        size = min(max(r.drug_cases / 5, 20), 300)
        ax.scatter(r.prr, r.chi2, s=size, c=c, alpha=0.75, edgecolors="white", linewidths=0.5)
        if r.prr > 3 or r.chi2 > 15:
            ax.annotate(_s(r.reaction_pt), (r.prr, r.chi2), fontsize=6,
                        xytext=(4, 4), textcoords="offset points", color="#333")

    ax.axvline(x=2.0, color="#E67E22", linestyle="--", linewidth=1, label="PRR=2")
    ax.axhline(y=4.0, color="#888",    linestyle=":",  linewidth=0.8, label="chi2=4")
    ax.set_xlabel("PRR", fontsize=9)
    ax.set_ylabel("chi-squared", fontsize=9)
    ax.set_title("PRR vs chi-squared (bubble size = N cases)", fontsize=9, fontweight="bold")
    ax.spines[["top", "right"]].set_visible(False)
    legend_patches = [
        mpatches.Patch(color="#C62828", label="Expedited"),
        mpatches.Patch(color="#E67E22", label="Routine"),
        mpatches.Patch(color="#1A3A5C", label="Monitor"),
        mpatches.Patch(color="#2E7D32", label="None"),
    ]
    ax.legend(handles=legend_patches, fontsize=7)
    fig.tight_layout()
    return fig


def _confounding_bar(positives: list) -> plt.Figure:
    """Bar chart of signals with/without confounding by SOC grouping."""
    conf = [r for r in positives if r.confounding_likely]
    no_conf = [r for r in positives if not r.confounding_likely]
    fig, ax = plt.subplots(figsize=(6, 3))
    categories = ["Confounding likely", "No confounding"]
    values = [len(conf), len(no_conf)]
    bar_colors = ["#E67E22", "#1A3A5C"]
    bars = ax.bar(categories, values, color=bar_colors, edgecolor="white", width=0.4)
    for bar, v in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.1,
                str(v), ha="center", va="bottom", fontsize=10, fontweight="bold")
    ax.set_ylabel("Number of signals", fontsize=9)
    ax.set_title("Confounding Assessment", fontsize=9, fontweight="bold")
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_ylim(0, max(values) * 1.25 + 1)
    fig.tight_layout()
    return fig


# ── Signal Detection discussion generator ────────────────────────────────────

def generate_signal_discussion(drug: str, comparator: str, results: list) -> dict:
    """
    Call gemma4:26b to generate a structured clinical discussion for the full
    signal detection report. Returns a dict with keys:
        drug_profile, overall_discussion, regulatory_context, limitations, conclusion
    """
    from langchain_ollama import ChatOllama
    from langchain_core.messages import HumanMessage, SystemMessage

    positives = sorted(
        [r for r in results if r.signal], key=lambda r: r.prr, reverse=True
    )
    top_signals = positives[:25]
    signal_summary = "\n".join(
        f"- {r.reaction_pt}: PRR={r.prr:.2f}, N={r.drug_cases}, chi2={r.chi2:.1f}, "
        f"Action={r.regulatory_action}, Confounding={'Yes' if r.confounding_likely else 'No'}"
        + (f", Assessment: {r.clinical_assessment[:120]}" if r.clinical_assessment else "")
        for r in top_signals
    )

    prompt = f"""You are a senior clinical pharmacovigilance analyst writing a formal signal detection report.

Drug under analysis: {drug.capitalize()}
Background comparator: {comparator.capitalize()}
Total Evans-positive signals: {len(positives)} (top {len(top_signals)} shown by PRR)

Signal findings:
{signal_summary}

Write the following sections for the formal PDF report. Be specific, clinical, and concise.
Use plain ASCII characters only (no em-dashes, no curly quotes).

DRUG_PROFILE:
[2-3 sentences: mechanism of action, therapeutic class, primary clinical indications, known CNS/neurotoxicity risk profile]

OVERALL_DISCUSSION:
[3-4 sentences: synthesize the signal findings as a whole. What patterns emerge? Are the signals expected given the drug's mechanism? How do they compare to the known safety profile? Any notable clusters?]

REGULATORY_CONTEXT:
[2-3 sentences: what do these findings mean under ICH E2A and ICH E2E? Which signals, if any, approach SUSAR criteria? What is the recommended regulatory pathway?]

LIMITATIONS:
[2-3 sentences: FAERS-specific limitations - spontaneous reporting bias, Weber effect, confounding by indication, underreporting, inability to establish causality]

CONCLUSION:
[2 sentences: overall conclusion and next steps for the Senior Reviewer]"""

    llm = ChatOllama(model=REASON_MODEL, base_url=OLLAMA_BASE_URL)
    sys_msg = SystemMessage(content=(
        "You are a clinical pharmacovigilance expert writing formal regulatory reports. "
        "Be precise and clinically grounded. Use only ASCII characters."
    ))
    response = llm.invoke([sys_msg, HumanMessage(content=prompt)])
    text = response.content

    def extract(tag: str) -> str:
        import re
        m = re.search(rf"{tag}:\s*\n?(.*?)(?=\n[A-Z_]+:|$)", text, re.S)
        if m:
            return m.group(1).strip()
        return ""

    return {
        "drug_profile":       extract("DRUG_PROFILE"),
        "overall_discussion": extract("OVERALL_DISCUSSION"),
        "regulatory_context": extract("REGULATORY_CONTEXT"),
        "limitations":        extract("LIMITATIONS"),
        "conclusion":         extract("CONCLUSION"),
    }


# ── Signal Detection ──────────────────────────────────────────────────────────

def save_signal_detection_report(
    drug: str,
    comparator: str,
    results: list,
    raw_signals: list | None = None,
    discussion: dict | None = None,
    generated: str = "",
) -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = OUTPUT_DIR / f"signal_{drug.lower()}_{ts}.pdf"

    positives = [r for r in results if r.signal]
    action_color_map = {
        "expedited": (RED, RED_LT),
        "routine":   (AMBER, AMBER_LT),
        "monitor":   (NAVY, NAVY_LT),
        "none":      (GREEN, GREEN_LT),
    }
    generated_str = generated or datetime.now().strftime("%Y-%m-%d %H:%M")
    total_evaluated = len(raw_signals) if raw_signals else len(results)
    drug_total = sum(r.drug_cases for r in results) if results else 0
    expedited_ct = sum(1 for r in positives if getattr(r, "regulatory_action", "") == "expedited")
    routine_ct   = sum(1 for r in positives if getattr(r, "regulatory_action", "") == "routine")
    monitor_ct   = sum(1 for r in positives if getattr(r, "regulatory_action", "") == "monitor")

    pdf = PVReport(f"FAERS Signal Detection — {drug.capitalize()}")

    # ── Cover ──────────────────────────────────────────────────────────────────
    pdf.cover(
        subtitle="Disproportionality Analysis (PRR/chi2 - Evans Criteria)",
        drug=f"{drug.capitalize()}  vs  {comparator.capitalize()} (background comparator)",
        generated=generated_str,
    )

    # ── Executive Summary ──────────────────────────────────────────────────────
    pdf.section("Executive Summary")
    pdf.label_value("Target drug", drug.capitalize())
    pdf.label_value("Comparator (background)", comparator.capitalize())
    pdf.label_value("FAERS reports — drug", f"{drug_total:,}" if drug_total else "N/A")
    pdf.label_value("Reaction PTs evaluated", str(total_evaluated))
    pdf.label_value("Evans-positive signals", str(len(positives)))
    pdf.label_value("Evans criteria", "PRR >= 2.0  AND  N >= 3  AND  chi2 >= 4.0 (Yates correction applied)")
    pdf.ln(2)

    # Action breakdown inline
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(*NAVY)
    pdf.cell(0, 5, "Regulatory Action Breakdown:", ln=True)
    pdf.set_text_color(*BLACK)
    pdf.set_font("Helvetica", "", 9)
    for label, count, c in [
        ("Expedited review", expedited_ct, RED),
        ("Routine monitoring", routine_ct, AMBER),
        ("Monitor (low confidence)", monitor_ct, NAVY),
        ("No action", len(positives) - expedited_ct - routine_ct - monitor_ct, GREEN),
    ]:
        pdf.set_text_color(*c)
        pdf.cell(60, 5, f"  {label}:", ln=False)
        pdf.set_text_color(*BLACK)
        pdf.cell(0, 5, str(count), ln=True)
    pdf.ln(2)
    pdf.callout(DRAFT_NOTE, AMBER, AMBER_LT)

    if not positives:
        pdf.ln(3)
        pdf.section("Result")
        pdf.body("No signals meeting Evans criteria (PRR>=2, N>=3, chi2>=4) were detected for this drug-comparator pair.")
        pdf.output(str(out))
        return out

    # ── Visualizations ─────────────────────────────────────────────────────────
    pdf.add_page()
    pdf.section("Signal Visualizations")

    # Forest plot (full width)
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(0, 5, _s("Figure 1 - PRR Forest Plot (top 20 signals, Evans-positive only)"), ln=True)
    pdf.ln(1)
    _embed_figure(pdf, _prr_forest_plot(positives, drug), max_width=190)
    pdf.ln(2)

    # Pie + confounding side by side
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(0, 5, _s("Figure 2 - Regulatory Action Distribution"), ln=True)
    pdf.ln(1)
    pie_fig = _action_pie(positives)
    _embed_figure(pdf, pie_fig, max_width=90)

    # Chi2 scatter (new page to give space)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(0, 5, _s("Figure 3 - PRR vs chi-squared Scatter (bubble = N cases)"), ln=True)
    pdf.ln(1)
    _embed_figure(pdf, _chi2_scatter(positives), max_width=190)
    pdf.ln(3)

    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(0, 5, _s("Figure 4 - Confounding Assessment"), ln=True)
    pdf.ln(1)
    _embed_figure(pdf, _confounding_bar(positives), max_width=110)

    # ── Positive Signals Table ─────────────────────────────────────────────────
    pdf.add_page()
    pdf.section("Positive Signals — Full Table (Evans Criteria Met)")
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_fill_color(*NAVY)
    pdf.set_text_color(*WHITE)
    for col, w in [("MedDRA PT", 72), ("N", 14), ("PRR", 20), ("chi2", 20), ("CC", 10), ("Action", 28), ("Confounding", 26)]:
        pdf.cell(w, 6, col, fill=True)
    pdf.ln()
    pdf.set_text_color(*BLACK)
    for i, r in enumerate(positives):
        if pdf.get_y() > 270:
            pdf.add_page()
            pdf.set_font("Helvetica", "B", 8)
            pdf.set_fill_color(*NAVY)
            pdf.set_text_color(*WHITE)
            for col, w in [("MedDRA PT", 72), ("N", 14), ("PRR", 20), ("chi2", 20), ("CC", 10), ("Action", 28), ("Confounding", 26)]:
                pdf.cell(w, 6, col, fill=True)
            pdf.ln()
            pdf.set_text_color(*BLACK)
        fill = i % 2 == 0
        pdf.set_fill_color(*GREY_LT)
        pdf.set_font("Helvetica", "", 8)
        cc = getattr(r, "continuity_corrected", False) if hasattr(r, "continuity_corrected") else ""
        for val, w in [
            (r.reaction_pt, 72),
            (str(r.drug_cases), 14),
            (f"{r.prr:.2f}", 20),
            (f"{r.chi2:.1f}", 20),
            ("Y" if cc else "N", 10),
            (r.regulatory_action.upper(), 28),
            ("Yes" if r.confounding_likely else "No", 26),
        ]:
            pdf.cell(w, 6, _s(val), fill=fill)
        pdf.ln()
    pdf.ln(2)
    pdf.set_font("Helvetica", "I", 7)
    pdf.set_text_color(*GREY_MID)
    pdf.cell(0, 4, "CC = Continuity corrected (b=0 in background; 0.5 substituted). PRR/chi2 computed on 2x2 FAERS contingency table.", ln=True)
    pdf.set_text_color(*BLACK)

    # ── Sub-threshold signals ──────────────────────────────────────────────────
    subthreshold = [r for r in results if not r.signal][:30]
    if subthreshold:
        pdf.ln(3)
        pdf.section("Sub-Threshold Signals (PRR >= 1.5, not meeting full Evans criteria)")
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_fill_color(*GREY_LT)
        pdf.set_text_color(*GREY_MID)
        for col, w in [("MedDRA PT", 100), ("N", 20), ("PRR", 30), ("chi2", 40)]:
            pdf.cell(w, 5, col, fill=True)
        pdf.ln()
        pdf.set_text_color(*BLACK)
        sub_show = [r for r in subthreshold if r.prr >= 1.5][:20]
        for i, r in enumerate(sub_show):
            if pdf.get_y() > 270:
                break
            fill = i % 2 == 0
            pdf.set_fill_color(*GREY_LT)
            pdf.set_font("Helvetica", "", 7)
            pdf.set_text_color(*GREY_MID)
            for val, w in [
                (r.reaction_pt, 100),
                (str(r.drug_cases), 20),
                (f"{r.prr:.2f}", 30),
                (f"{r.chi2:.1f}", 40),
            ]:
                pdf.cell(w, 5, _s(val), fill=fill)
            pdf.ln()
            pdf.set_text_color(*BLACK)
        pdf.ln(2)

    # ── Clinical Interpretations ───────────────────────────────────────────────
    pdf.add_page()
    pdf.section("Clinical Interpretations — Signal-by-Signal Analysis")
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(*GREY_MID)
    pdf.cell(0, 5, f"gemma4:26b interpretation - {len(positives)} Evans-positive signals - {generated_str}", ln=True)
    pdf.set_text_color(*BLACK)
    pdf.ln(2)

    for r in positives:
        if pdf.get_y() > 245:
            pdf.add_page()
        action = getattr(r, "regulatory_action", "monitor").lower()
        c, bg = action_color_map.get(action, (NAVY, NAVY_LT))

        # Signal header bar
        pdf.set_fill_color(*c)
        pdf.set_text_color(*WHITE)
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(0, 7, _s(f"  {r.reaction_pt}"), fill=True, ln=True)
        pdf.set_text_color(*BLACK)

        # Stats strip
        pdf.set_fill_color(*bg)
        pdf.set_font("Helvetica", "", 8)
        pdf.cell(0, 5,
            _s(f"  PRR {r.prr:.2f}  |  chi2 {r.chi2:.1f}  |  N={r.drug_cases}  |  Action: {r.regulatory_action.upper()}  |  Confounding: {'Yes' if r.confounding_likely else 'No'}"),
            fill=True, ln=True)

        pdf.ln(1)

        if r.clinical_assessment:
            pdf.set_font("Helvetica", "B", 8)
            pdf.cell(0, 5, "Clinical Assessment:", ln=True)
            pdf.set_font("Helvetica", "", 8)
            for line in _wrap(pdf, r.clinical_assessment, 190, 8):
                pdf.set_x(14)
                pdf.cell(176, 4.5, _s(line), ln=True)
            pdf.ln(1)

        if r.confounding_likely:
            pdf.callout(
                "Confounding by indication likely — this signal may reflect disease severity or prescribing patterns rather than a true drug effect. Apply causality assessment per ICH E2A before regulatory action.",
                AMBER, AMBER_LT,
            )
            pdf.ln(1)

        if r.reviewer_notes:
            pdf.set_font("Helvetica", "B", 8)
            pdf.cell(0, 5, "Reviewer Notes:", ln=True)
            pdf.set_font("Helvetica", "I", 8)
            for line in _wrap(pdf, r.reviewer_notes, 190, 8):
                pdf.set_x(14)
                pdf.cell(176, 4.5, _s(line), ln=True)
            pdf.ln(1)

        pdf.ln(3)

    # ── Clinical Discussion (LLM-generated) ───────────────────────────────────
    if discussion:
        pdf.add_page()
        pdf.section("Drug Profile")
        for line in _wrap(pdf, discussion.get("drug_profile", ""), 190, 9):
            pdf.set_x(10)
            pdf.cell(190, 5, _s(line), ln=True)
        pdf.ln(3)

        pdf.section("Overall Discussion")
        for line in _wrap(pdf, discussion.get("overall_discussion", ""), 190, 9):
            pdf.set_x(10)
            pdf.cell(190, 5, _s(line), ln=True)
        pdf.ln(3)

        pdf.section("Regulatory Context")
        for line in _wrap(pdf, discussion.get("regulatory_context", ""), 190, 9):
            pdf.set_x(10)
            pdf.cell(190, 5, _s(line), ln=True)
        pdf.ln(3)

        pdf.section("Limitations")
        for line in _wrap(pdf, discussion.get("limitations", ""), 190, 9):
            pdf.set_x(10)
            pdf.cell(190, 5, _s(line), ln=True)
        pdf.ln(3)

        pdf.section("Conclusion")
        for line in _wrap(pdf, discussion.get("conclusion", ""), 190, 9):
            pdf.set_x(10)
            pdf.cell(190, 5, _s(line), ln=True)
        pdf.ln(3)

    # ── Recommendations ────────────────────────────────────────────────────────
    pdf.add_page()
    pdf.section("Recommendations Summary")

    if expedited_ct:
        pdf.callout(
            f"EXPEDITED ACTION REQUIRED: {expedited_ct} signal(s) flagged for expedited review. "
            "These meet Evans criteria and are assessed as unexpected or serious. "
            "Evaluate for SUSAR reporting obligations under ICH E2A.",
            RED, RED_LT,
        )
        pdf.ln(2)

    pdf.set_font("Helvetica", "", 9)
    recs = [
        ("Expedited review", [r for r in positives if r.regulatory_action == "expedited"]),
        ("Routine monitoring", [r for r in positives if r.regulatory_action == "routine"]),
        ("Monitor — watch", [r for r in positives if r.regulatory_action == "monitor"]),
    ]
    for label, group in recs:
        if not group:
            continue
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(0, 6, f"{label} ({len(group)} signal{'s' if len(group) != 1 else ''}):", ln=True)
        pdf.set_font("Helvetica", "", 8)
        for r in group:
            pdf.set_x(12)
            pdf.cell(0, 5, _s(f"- {r.reaction_pt}  (PRR {r.prr:.2f}, N={r.drug_cases})"), ln=True)
        pdf.ln(2)

    # Reviewer sign-off block
    pdf.ln(4)
    pdf.set_draw_color(*NAVY)
    pdf.set_fill_color(*NAVY_LT)
    pdf.rect(10, pdf.get_y(), 190, 30, "FD")
    pdf.set_xy(14, pdf.get_y() + 3)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(*NAVY)
    pdf.cell(0, 6, "Senior Reviewer Sign-Off", ln=True)
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(*BLACK)
    pdf.set_x(14)
    pdf.cell(0, 5, f"Reviewer: {AUTHOR}", ln=True)
    pdf.set_x(14)
    pdf.cell(80, 5, "Date: ____________________", ln=False)
    pdf.cell(0, 5, "Signature: ____________________", ln=True)
    pdf.set_x(14)
    pdf.cell(0, 5, "[ ] Reviewed and approved for regulatory use    [ ] Requires further investigation", ln=True)

    pdf.output(str(out))
    return out


# ── Regulatory Q&A ────────────────────────────────────────────────────────────

def save_regulatory_qa_report(question: str, result, generated: str = "") -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    slug = question[:30].strip().replace(" ", "_").replace("/", "-")
    out = OUTPUT_DIR / f"regulatory_qa_{slug}_{ts}.pdf"

    pdf = PVReport("Regulatory Q&A")
    pdf.cover(
        subtitle="RAG-assisted Regulatory Guidance",
        drug=question[:80] + ("..." if len(question) > 80 else ""),
        generated=generated or datetime.now().strftime("%Y-%m-%d %H:%M"),
    )

    pdf.section("Question")
    pdf.body(question)
    pdf.ln(3)

    pdf.section(f"Answer  —  Confidence: {getattr(result, 'confidence', '')}")
    pdf.body(getattr(result, "answer", ""))
    pdf.ln(3)

    citations = getattr(result, "citations", [])
    if citations:
        pdf.section("Citations")
        for cit in citations:
            pdf.set_font("Helvetica", "", 8)
            pdf.cell(5, 5, "-")
            lines = _wrap(pdf, cit, 183, 8)
            pdf.set_x(15)
            for i, line in enumerate(lines):
                if i:
                    pdf.set_x(15)
                pdf.cell(183, 5, _s(line), ln=True)
        pdf.ln(2)

    pdf.callout(DRAFT_NOTE, AMBER, AMBER_LT)
    pdf.output(str(out))
    return out


# ── MedDRA Coder ──────────────────────────────────────────────────────────────

def save_meddra_report(narrative: str, result, generated: str = "") -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    pt = getattr(result, "primary_pt", "unknown").replace(" ", "_")[:30]
    out = OUTPUT_DIR / f"meddra_{pt}_{ts}.pdf"

    pdf = PVReport("MedDRA Coding Suggestion")
    pdf.cover(
        subtitle="Thinking Mode PT Deliberation",
        drug=f"Primary PT: {getattr(result, 'primary_pt', '')}",
        generated=generated or datetime.now().strftime("%Y-%m-%d %H:%M"),
    )

    if getattr(result, "reviewer_flag", False):
        pdf.callout("REVIEWER FLAG: Low confidence or ambiguous PT — manual coding required.", RED, RED_LT)
        pdf.ln(2)

    pdf.section("Clinical Narrative")
    pdf.body(narrative)
    pdf.ln(3)

    pdf.section("Coding Result")
    pdf.label_value("Primary PT", getattr(result, "primary_pt", ""))
    pdf.label_value("SOC", getattr(result, "soc", ""))
    pdf.label_value("Confidence", getattr(result, "confidence", ""))
    pdf.ln(2)

    notes = getattr(result, "coding_notes", "")
    if notes:
        pdf.section("Coding Notes")
        pdf.body(notes)
        pdf.ln(2)

    alts = getattr(result, "alternative_pts", [])
    if alts:
        pdf.section("Alternative PTs Considered")
        for alt in alts:
            pdf.set_font("Helvetica", "", 9)
            pdf.cell(0, 5, _s(f"  - {alt}"), ln=True)
        pdf.ln(2)

    pdf.callout(DRAFT_NOTE, AMBER, AMBER_LT)
    pdf.output(str(out))
    return out


# ── ICSR Generator ────────────────────────────────────────────────────────────

def save_icsr_report(case: dict, result, generated: str = "") -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    drug = str(case.get("drug_name", "unknown")).replace(" ", "_")[:20]
    out = OUTPUT_DIR / f"icsr_{drug}_{ts}.pdf"

    pdf = PVReport("ICSR Narrative Draft")
    pdf.cover(
        subtitle="E2B(R3)-Aligned Narrative — Senior Reviewer Sign-Off Required",
        drug=f"Drug: {case.get('drug_name', '')}  |  AE: {case.get('adverse_event', '')}",
        generated=generated or datetime.now().strftime("%Y-%m-%d %H:%M"),
    )

    pdf.callout(DRAFT_NOTE, AMBER, AMBER_LT)
    pdf.ln(3)

    pdf.section("Case Details")
    for label, key in [
        ("Patient", "patient_description"),
        ("Drug", "drug_name"),
        ("Dose/Route", "dose_route"),
        ("Adverse Event", "adverse_event"),
        ("Outcome", "outcome"),
    ]:
        val = case.get(key, "")
        if val:
            pdf.label_value(label, str(val))
    pdf.ln(3)

    seriousness = getattr(result, "seriousness_criteria", [])
    pdf.section("Seriousness Assessment")
    if seriousness:
        for crit in seriousness:
            pdf.set_font("Helvetica", "", 9)
            pdf.cell(0, 5, _s(f"  - {crit}"), ln=True)
    else:
        pdf.body("No seriousness criteria met — reviewer adjudication required.")
    pdf.ln(3)

    pdf.section("E2B(R3) Narrative")
    narrative = getattr(result, "narrative", "")
    pdf.set_font("Helvetica", "", 9)
    for para in narrative.split("\n"):
        if para.strip():
            pdf.body(para.strip())
            pdf.ln(1)

    pdf.output(str(out))
    return out


# ── Literature Monitor ────────────────────────────────────────────────────────

def save_lit_monitor_report(drug: str, papers: list, digest, generated: str = "") -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = OUTPUT_DIR / f"lit_monitor_{drug.lower()}_{ts}.pdf"

    pdf = PVReport(f"Literature Monitor — {drug.capitalize()}")
    pdf.cover(
        subtitle="PubMed PV Relevance Scan",
        drug=f"{drug.capitalize()}  |  {len(papers)} papers retrieved",
        generated=generated or datetime.now().strftime("%Y-%m-%d %H:%M"),
    )

    digest_text = getattr(digest, "digest_text", "") if digest else ""
    if digest_text:
        pdf.section("Pharmacovigilance Digest")
        for para in digest_text.split("\n"):
            if para.strip():
                pdf.body(para.strip())
                pdf.ln(1)
        pdf.ln(2)

    escalations = getattr(digest, "escalations", []) if digest else []
    if escalations:
        pdf.section("Safety Escalations")
        for esc in escalations:
            pdf.callout(
                f"ESCALATE: {getattr(esc, 'title', '')} — {getattr(esc, 'summary', '')}",
                RED, RED_LT,
            )
            pdf.ln(1)
        pdf.ln(2)

    if papers:
        pdf.section(f"Retrieved Papers ({len(papers)})")
        for p in papers[:50]:
            if pdf.get_y() > 260:
                pdf.add_page()
            title = getattr(p, "title", "") or p.get("title", "") if isinstance(p, dict) else getattr(p, "title", "")
            pmid  = getattr(p, "pmid",  "") or p.get("pmid",  "") if isinstance(p, dict) else getattr(p, "pmid",  "")
            score = getattr(p, "pv_score", None)
            score_str = f"  [PV score: {score:.2f}]" if score is not None else ""
            pdf.set_font("Helvetica", "B", 8)
            pdf.cell(0, 5, _s(f"{title}{score_str}"), ln=True)
            if pmid:
                pdf.set_font("Helvetica", "", 7)
                pdf.set_text_color(*GREY_MID)
                pdf.cell(0, 4, _s(f"PMID: {pmid}"), ln=True)
                pdf.set_text_color(*BLACK)
            pdf.ln(1)

    pdf.callout(DRAFT_NOTE, AMBER, AMBER_LT)
    pdf.output(str(out))
    return out
