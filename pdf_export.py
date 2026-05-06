"""
DebateMoi — PDF Export (Light Theme)
======================================
White-paper document with strong contrast and colored accents.
Layout: cover → debate rounds (Pro / Con) → verdict & score table.
"""

import json
import re
import textwrap
from datetime import datetime, timezone
from fpdf import FPDF

# ---------------------------------------------------------------------------
# Palette (print-safe, high-contrast on white paper)
# ---------------------------------------------------------------------------
WHITE       = (255, 255, 255)
OFF_WHITE   = (248, 249, 252)
LIGHT_GRAY  = (240, 242, 247)
MID_GRAY    = (180, 182, 192)
DARK        = (22,  24,  38)
BODY        = (55,  57,  75)
MUTED       = (110, 112, 130)

PRO_DARK    = (0,   130, 170)   # readable cyan on white
PRO_LIGHT   = (230, 247, 252)
CON_DARK    = (185, 0,   75)    # readable magenta on white
CON_LIGHT   = (253, 230, 242)
GOLD_DARK   = (160, 120, 0)
GOLD_LIGHT  = (255, 249, 220)

# ---------------------------------------------------------------------------
# Unicode sanitiser
# ---------------------------------------------------------------------------
_UNICODE_MAP = {
    "‘": "'", "’": "'", "“": '"', "”": '"',
    "–": "-", "—": "-", "…": "...", "•": "*",
    "°": "deg", "®": "(R)", "©": "(c)", "™": "(TM)",
    "é": "e", "è": "e", "ê": "e", "à": "a",
    "â": "a", "ô": "o", "û": "u", "ü": "u",
    "ç": "c",
    # emoji
    "⚔️": ">>", "\U0001f6e1️": "<<", "⚖️": "=",
    "⚠️": "!", "✅": "[OK]", "❌": "[X]",
}

def _s(text: str) -> str:
    """Sanitise unicode for latin-1 PDF rendering."""
    if not text:
        return ""
    for src, dst in _UNICODE_MAP.items():
        text = text.replace(src, dst)
    return text.encode("latin-1", "ignore").decode("latin-1")


# ---------------------------------------------------------------------------
# PDF class
# ---------------------------------------------------------------------------
class DebatePDF(FPDF):

    def __init__(self):
        super().__init__()
        self.set_margins(left=18, top=18, right=18)
        self.set_auto_page_break(auto=True, margin=22)

    def header(self):
        if self.page_no() == 1:
            return
        # Thin top rule
        self.set_draw_color(*MID_GRAY)
        self.set_line_width(0.3)
        self.line(18, 12, 192, 12)
        self.set_font("Helvetica", "B", 7)
        self.set_text_color(*MUTED)
        self.set_xy(18, 6)
        self.cell(0, 6, "DEBATEMOI  //  DEBATE TRANSCRIPT", align="L")
        self.set_xy(18, 6)
        self.cell(0, 6, f"Page {self.page_no()}", align="R")
        self.ln(10)

    def footer(self):
        if self.page_no() == 1:
            return
        self.set_y(-14)
        self.set_draw_color(*LIGHT_GRAY)
        self.set_line_width(0.3)
        self.line(18, self.get_y(), 192, self.get_y())
        self.set_font("Helvetica", "", 7)
        self.set_text_color(*MUTED)
        self.cell(0, 8, "debatemoi.streamlit.app", align="C")

    # ------------------------------------------------------------------ cover
    def cover_page(self, topic: str, session_id: str, rounds: int, winner: str = ""):
        self.add_page()

        # Dark header band
        self.set_fill_color(18, 20, 35)
        self.rect(0, 0, 210, 65, "F")

        # Cyan left stripe + magenta right stripe
        self.set_fill_color(*PRO_DARK)
        self.rect(0, 0, 4, 65, "F")
        self.set_fill_color(*CON_DARK)
        self.rect(206, 0, 4, 65, "F")

        # Brand name
        self.set_font("Helvetica", "B", 32)
        self.set_text_color(255, 255, 255)
        self.set_xy(0, 16)
        self.cell(210, 14, "DEBATEMOI", align="C", new_x="LMARGIN", new_y="NEXT")

        # Tagline
        self.set_font("Helvetica", "", 8)
        self.set_text_color(*MID_GRAY)
        self.cell(210, 6, "MULTI-AGENT  AI  DEBATE  TRANSCRIPT", align="C",
                  new_x="LMARGIN", new_y="NEXT")

        # White body
        self.set_fill_color(*WHITE)
        self.rect(0, 65, 210, 232, "F")

        # Topic box
        self.set_y(78)
        topic_clean = _s(topic)
        wrapped = textwrap.fill(topic_clean, width=60)
        lines = wrapped.count("\n") + 1
        box_h = max(28, lines * 8 + 20)

        self.set_fill_color(*OFF_WHITE)
        self.set_draw_color(*PRO_DARK)
        self.set_line_width(1.5)
        self.rect(18, self.get_y(), 174, box_h, "DF")
        self.set_line_width(0.2)

        self.set_font("Helvetica", "B", 7)
        self.set_text_color(*PRO_DARK)
        self.set_x(18)
        self.cell(174, 8, "DEBATE TOPIC", align="C", new_x="LMARGIN", new_y="NEXT")

        self.set_font("Helvetica", "B", 13)
        self.set_text_color(*DARK)
        self.set_x(22)
        self.multi_cell(170, 8, topic_clean, align="C", new_x="LMARGIN", new_y="NEXT")

        self.ln(12)

        # Stats row — 3 equal boxes
        stats = [
            ("ROUNDS", str(rounds)),
            ("SESSION", session_id[:8] if session_id else "—"),
            ("GENERATED", datetime.now(timezone.utc).strftime("%d %b %Y")),
        ]
        col_w, gap = 54, 3
        start_x = 18
        y_stats = self.get_y()

        for i, (label, val) in enumerate(stats):
            cx = start_x + i * (col_w + gap)
            self.set_fill_color(*LIGHT_GRAY)
            self.set_draw_color(*MID_GRAY)
            self.set_line_width(0.2)
            self.rect(cx, y_stats, col_w, 24, "DF")

            self.set_font("Helvetica", "", 7)
            self.set_text_color(*MUTED)
            self.set_xy(cx, y_stats + 5)
            self.cell(col_w, 5, label, align="C", new_x="LMARGIN", new_y="NEXT")

            self.set_font("Helvetica", "B", 12)
            self.set_text_color(*DARK)
            self.set_x(cx)
            self.cell(col_w, 8, _s(val), align="C")

        self.ln(30)

        # Winner ribbon (if available)
        if winner and winner != "Unknown":
            w_fill = PRO_LIGHT if winner == "Pro" else CON_LIGHT
            w_text = PRO_DARK if winner == "Pro" else CON_DARK
            self.set_fill_color(*w_fill)
            self.set_draw_color(*w_text)
            self.set_line_width(0.8)
            y_rib = self.get_y()
            self.rect(18, y_rib, 174, 18, "DF")
            self.set_line_width(0.2)
            self.set_font("Helvetica", "B", 10)
            self.set_text_color(*w_text)
            self.set_xy(18, y_rib + 4)
            icon = ">>" if winner == "Pro" else "<<"
            self.cell(174, 10,
                      f"{icon}  {winner.upper()} AGENT WINS  {icon}",
                      align="C")
            self.ln(26)

        # Bottom accent bar
        self.set_fill_color(18, 20, 35)
        self.rect(0, 285, 210, 12, "F")
        self.set_fill_color(*PRO_DARK)
        self.rect(0, 285, 105, 12, "F")
        self.set_fill_color(*CON_DARK)
        self.rect(105, 285, 105, 12, "F")


# ---------------------------------------------------------------------------
# Argument block
# ---------------------------------------------------------------------------
def _render_argument(pdf: DebatePDF, label: str, content: str,
                     accent_dark: tuple, accent_light: tuple):
    """One argument card: tinted background, left border, readable text."""

    # Agent header bar
    pdf.set_fill_color(*accent_light)
    pdf.set_x(18)
    icon = ">>" if label == "PRO" else "<<"
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(*accent_dark)
    pdf.cell(174, 9, f"  {icon}  {label} AGENT", fill=True,
             new_x="LMARGIN", new_y="NEXT")

    # Content area: white fill, left colored border
    y_start = pdf.get_y()
    pdf.set_fill_color(*WHITE)
    pdf.set_x(18)

    for raw_line in _s(content).split("\n"):
        line = raw_line.strip()
        if not line:
            pdf.ln(3)
            continue

        # Full-line heading: **text** alone on line
        if re.match(r"^\*\*[^*]+\*\*$", line):
            heading = re.sub(r"\*+", "", line).strip()
            pdf.ln(2)
            pdf.set_x(22)
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_text_color(*accent_dark)
            pdf.multi_cell(166, 5.5, heading, new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", "", 9.5)
            pdf.set_text_color(*BODY)
            continue

        # Inline bold label: **Key**: rest
        m = re.match(r"^\*\*(.+?)\*\*[:\s]+(.*)", line)
        if m:
            key_text = m.group(1).strip()
            rest = _s(m.group(2).strip())
            pdf.set_x(22)
            pdf.set_font("Helvetica", "B", 9.5)
            pdf.set_text_color(*DARK)
            pdf.cell(0, 5.5, key_text + ":", new_x="LMARGIN", new_y="NEXT")
            if rest:
                pdf.set_x(26)
                pdf.set_font("Helvetica", "", 9.5)
                pdf.set_text_color(*BODY)
                pdf.multi_cell(162, 5.5, rest, new_x="LMARGIN", new_y="NEXT")
            continue

        # Normal text
        clean = re.sub(r"\*+", "", line)
        pdf.set_x(22)
        pdf.set_font("Helvetica", "", 9.5)
        pdf.set_text_color(*BODY)
        pdf.multi_cell(166, 5.5, clean, new_x="LMARGIN", new_y="NEXT")

    y_end = pdf.get_y()
    pdf.ln(3)

    # Left accent border
    pdf.set_draw_color(*accent_dark)
    pdf.set_line_width(2.5)
    pdf.line(18, y_start, 18, y_end)
    pdf.set_line_width(0.2)

    # Bottom separator
    pdf.set_draw_color(*LIGHT_GRAY)
    pdf.set_line_width(0.3)
    pdf.line(18, pdf.get_y(), 192, pdf.get_y())
    pdf.ln(6)


# ---------------------------------------------------------------------------
# Verdict page
# ---------------------------------------------------------------------------
def _render_verdict(pdf: DebatePDF, state: dict):
    pdf.add_page()

    winner = state.get("winner", "Unknown")
    reasoning = _s(state.get("reasoning", "No reasoning provided."))

    # Section heading
    pdf.set_fill_color(*DARK)
    pdf.set_x(18)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(*WHITE)
    pdf.cell(174, 12, "  JUDGE'S VERDICT", fill=True,
             new_x="LMARGIN", new_y="NEXT")
    pdf.ln(8)

    # Winner banner
    if winner and winner != "Unknown":
        w_fill = PRO_LIGHT if winner == "Pro" else CON_LIGHT
        w_dark = PRO_DARK if winner == "Pro" else CON_DARK
        pdf.set_fill_color(*w_fill)
        pdf.set_draw_color(*w_dark)
        pdf.set_line_width(1.5)
        y_b = pdf.get_y()
        pdf.rect(18, y_b, 174, 20, "DF")
        pdf.set_line_width(0.2)
        pdf.set_font("Helvetica", "B", 16)
        pdf.set_text_color(*w_dark)
        pdf.set_xy(18, y_b + 3)
        icon = ">>" if winner == "Pro" else "<<"
        pdf.cell(174, 14, f"{icon}  {winner.upper()} AGENT WINS  {icon}", align="C")
        pdf.ln(26)

    # Reasoning box
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(*MUTED)
    pdf.set_x(18)
    pdf.cell(0, 6, "REASONING", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    wrapped = textwrap.fill(reasoning, width=88)
    n_lines = wrapped.count("\n") + 1
    box_h = max(18, n_lines * 5.5 + 12)

    pdf.set_fill_color(*OFF_WHITE)
    pdf.set_draw_color(*LIGHT_GRAY)
    pdf.set_line_width(0.3)
    pdf.rect(18, pdf.get_y(), 174, box_h, "DF")

    # Gold left accent
    pdf.set_draw_color(*GOLD_DARK)
    pdf.set_line_width(2.5)
    y0 = pdf.get_y()
    pdf.set_x(22)
    pdf.set_font("Helvetica", "", 9.5)
    pdf.set_text_color(*BODY)
    pdf.multi_cell(166, 5.5, reasoning, new_x="LMARGIN", new_y="NEXT")
    pdf.line(18, y0, 18, pdf.get_y())
    pdf.set_line_width(0.2)
    pdf.ln(10)

    # Score table
    judge_scores_str = state.get("judge_scores", "")
    if judge_scores_str:
        try:
            scores = json.loads(judge_scores_str)
            if not scores.get("parse_error"):
                _render_scores(pdf, scores)
        except (json.JSONDecodeError, ValueError):
            pass


def _render_scores(pdf: DebatePDF, scores: dict):
    pro_s = scores.get("pro_scores", {})
    con_s = scores.get("con_scores", {})

    # Section heading
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(*MUTED)
    pdf.set_x(18)
    pdf.cell(0, 6, "DETAILED SCORES", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    # Table header
    c_cat, c_pro, c_con = 100, 37, 37
    pdf.set_fill_color(*DARK)
    pdf.set_x(18)
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(*WHITE)
    pdf.cell(c_cat, 8, "  CATEGORY", fill=True)
    pdf.set_text_color(160, 230, 245)
    pdf.cell(c_pro, 8, "PRO", align="C", fill=True)
    pdf.set_text_color(255, 180, 210)
    pdf.cell(c_con, 8, "CON", align="C", fill=True,
             new_x="LMARGIN", new_y="NEXT")

    categories = [
        ("logic",       "Logical Consistency"),
        ("evidence",    "Evidence Strength"),
        ("rhetoric",    "Rhetorical Skill"),
        ("rebuttal",    "Rebuttal Quality"),
        ("originality", "Argument Originality"),
    ]

    for i, (key, label) in enumerate(categories):
        row_fill = OFF_WHITE if i % 2 == 0 else WHITE
        pdf.set_fill_color(*row_fill)
        pdf.set_draw_color(*LIGHT_GRAY)
        pdf.set_line_width(0.2)
        pdf.set_x(18)

        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(*BODY)
        pdf.cell(c_cat, 8, f"  {label}", fill=True, border="B")

        pv = pro_s.get(key, 0)
        cv = con_s.get(key, 0)

        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(*PRO_DARK)
        pdf.cell(c_pro, 8, str(pv), align="C", fill=True, border="B")
        pdf.set_text_color(*CON_DARK)
        pdf.cell(c_con, 8, str(cv), align="C", fill=True, border="B",
                 new_x="LMARGIN", new_y="NEXT")

    # Totals row
    pdf.set_fill_color(*DARK)
    pdf.set_x(18)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(*WHITE)
    pdf.cell(c_cat, 9, "  TOTAL", fill=True)
    pdf.set_text_color(160, 230, 245)
    pdf.cell(c_pro, 9, str(scores.get("pro_total", "—")), align="C", fill=True)
    pdf.set_text_color(255, 180, 210)
    pdf.cell(c_con, 9, str(scores.get("con_total", "—")), align="C", fill=True,
             new_x="LMARGIN", new_y="NEXT")
    pdf.ln(10)

    # Key moments
    key_moments = scores.get("key_moments", [])
    if key_moments:
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_text_color(*MUTED)
        pdf.set_x(18)
        pdf.cell(0, 6, "KEY MOMENTS", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)
        for i, moment in enumerate(key_moments, 1):
            pdf.set_x(18)
            pdf.set_font("Helvetica", "B", 9)
            pdf.set_text_color(*GOLD_DARK)
            pdf.cell(8, 5.5, f"{i}.")
            pdf.set_font("Helvetica", "", 9)
            pdf.set_text_color(*BODY)
            pdf.multi_cell(160, 5.5, _s(moment), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(6)

    # Deciding factor
    deciding = scores.get("deciding_factor", "")
    if deciding:
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_text_color(*MUTED)
        pdf.set_x(18)
        pdf.cell(0, 6, "DECIDING FACTOR", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)
        pdf.set_fill_color(*GOLD_LIGHT)
        pdf.set_draw_color(*GOLD_DARK)
        pdf.set_line_width(0.8)
        y0 = pdf.get_y()
        deciding_clean = _s(deciding)
        n = max(12, len(deciding_clean) // 85 * 5.5 + 12)
        pdf.rect(18, y0, 174, n, "DF")
        pdf.set_line_width(0.2)
        pdf.set_x(22)
        pdf.set_font("Helvetica", "I", 9.5)
        pdf.set_text_color(*GOLD_DARK)
        pdf.multi_cell(166, 5.5, deciding_clean, new_x="LMARGIN", new_y="NEXT")


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------
def generate_debate_pdf(state: dict, session_id: str = "") -> bytes:
    args_for    = state.get("arguments_for", [])
    args_against = state.get("arguments_against", [])
    rounds_played = max(len(args_for), len(args_against), 1)

    pdf = DebatePDF()

    # Cover
    pdf.cover_page(
        topic=state.get("topic", "Unknown Topic"),
        session_id=session_id,
        rounds=rounds_played,
        winner=state.get("winner", ""),
    )

    # Debate rounds
    pdf.add_page()
    for i in range(rounds_played):
        # Round header
        pdf.set_fill_color(*LIGHT_GRAY)
        pdf.set_draw_color(*MID_GRAY)
        pdf.set_line_width(0.2)
        pdf.set_x(18)
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(*MUTED)
        pdf.cell(174, 9, f"  ROUND {i + 1}", fill=True,
                 new_x="LMARGIN", new_y="NEXT")
        pdf.ln(5)

        if i < len(args_for):
            _render_argument(pdf, "PRO", args_for[i]["content"],
                             PRO_DARK, PRO_LIGHT)
        if i < len(args_against):
            _render_argument(pdf, "CON", args_against[i]["content"],
                             CON_DARK, CON_LIGHT)
        pdf.ln(4)

    # Verdict
    _render_verdict(pdf, state)

    return bytes(pdf.output())
