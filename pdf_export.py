"""
DebateMoi — PDF Export
=======================
Clean, professional white-paper layout.
Typography-first design: strong hierarchy, consistent grid, restrained color.
"""

import json
import re
from datetime import datetime, timezone
from fpdf import FPDF

# ---------------------------------------------------------------------------
# Design tokens
# ---------------------------------------------------------------------------
# All colors are (R, G, B) tuples

# Neutrals
INK        = (20,  22,  38)   # headings, labels
BODY       = (50,  52,  70)   # body text
MUTED      = (120, 122, 140)  # captions, metadata
RULE       = (210, 212, 220)  # horizontal rules
ROW_ALT    = (248, 249, 252)  # alternating table row
WHITE      = (255, 255, 255)
NEAR_WHITE = (252, 253, 255)

# Accents (print-safe: saturated enough on white to read, not harsh)
PRO   = (0,   130, 170)  # teal-blue
CON   = (180,  0,  70)   # deep red-magenta
GOLD  = (150, 110,   0)  # amber-gold

# Header band
BAND_BG    = (18,  20,  36)
BAND_PRO   = (0,  140, 180)
BAND_CON   = (190,  0,  75)

# Margin & grid
L = 18   # left margin
R = 18   # right margin
TW = 210 - L - R  # text width = 174 mm


# ---------------------------------------------------------------------------
# Unicode sanitiser
# ---------------------------------------------------------------------------
_SUBS = {
    "‘": "'", "’": "'", "“": '"', "”": '"',
    "–": "-", "—": "-", "…": "...", "•": "*",
    "®": "(R)", "©": "(c)", "™": "(TM)",
    "é": "e", "è": "e", "ê": "e", "à": "a",
    "â": "a", "ô": "o", "û": "u", "ü": "u",
    "ç": "c", "°": "deg",
}
_EMOJI = re.compile(
    "[\U00002600-\U000027BF\U0001F300-\U0001F9FF\U0000FE0F]+"
)

def _s(text: str) -> str:
    """Sanitise text for latin-1 PDF rendering."""
    if not text:
        return ""
    for src, dst in _SUBS.items():
        text = text.replace(src, dst)
    text = _EMOJI.sub("", text)
    return "".join(ch if ord(ch) < 256 else "-" for ch in text)


def _strip_md(text: str) -> str:
    return re.sub(r"\*+", "", text)


# ---------------------------------------------------------------------------
# PDF class
# ---------------------------------------------------------------------------
class DebatePDF(FPDF):

    def __init__(self):
        super().__init__()
        self.set_margins(L, 20, R)
        self.set_auto_page_break(auto=True, margin=22)
        self._in_cover = False

    def header(self):
        if self._in_cover:
            return
        # Thin top rule + running header
        self.set_draw_color(*RULE)
        self.set_line_width(0.3)
        self.line(L, 14, 210 - R, 14)
        self.set_font("Helvetica", "", 7)
        self.set_text_color(*MUTED)
        self.set_xy(L, 7)
        self.cell(0, 6, "DEBATEMOI  |  DEBATE TRANSCRIPT", align="L")
        self.set_xy(L, 7)
        self.cell(0, 6, f"Page {self.page_no()}", align="R")
        self.set_y(20)

    def footer(self):
        if self._in_cover:
            return
        self.set_y(-13)
        self.set_draw_color(*RULE)
        self.set_line_width(0.3)
        self.line(L, self.get_y(), 210 - R, self.get_y())
        self.set_font("Helvetica", "", 7)
        self.set_text_color(*MUTED)
        self.cell(0, 8, "debatemoi.streamlit.app", align="C")

    # ------------------------------------------------------------------ utils
    def _rule(self, color=RULE, width=0.3):
        self.set_draw_color(*color)
        self.set_line_width(width)
        self.line(L, self.get_y(), 210 - R, self.get_y())
        self.ln(4)

    def _section_label(self, text: str):
        """Small all-caps muted label above a section."""
        self.set_font("Helvetica", "B", 7)
        self.set_text_color(*MUTED)
        self.cell(0, 5, _s(text), new_x="LMARGIN", new_y="NEXT")
        self.ln(1)

    def _body(self, text: str, indent: int = 0):
        self.set_x(L + indent)
        self.set_font("Helvetica", "", 9.5)
        self.set_text_color(*BODY)
        self.multi_cell(TW - indent, 5.5, _s(text), new_x="LMARGIN", new_y="NEXT")

    # ------------------------------------------------------------------ cover
    def cover_page(self, topic: str, session_id: str, rounds: int, winner: str = ""):
        self._in_cover = True
        self.add_page()

        # ── Dark header band ──────────────────────────────────────────────
        self.set_fill_color(*BAND_BG)
        self.rect(0, 0, 210, 60, "F")

        # Side stripes (4 mm wide)
        self.set_fill_color(*BAND_PRO)
        self.rect(0, 0, 4, 60, "F")
        self.set_fill_color(*BAND_CON)
        self.rect(206, 0, 4, 60, "F")

        # Brand name
        self.set_font("Helvetica", "B", 30)
        self.set_text_color(255, 255, 255)
        self.set_xy(0, 14)
        self.cell(210, 14, "DEBATEMOI", align="C", new_x="LMARGIN", new_y="NEXT")

        # Tagline
        self.set_font("Helvetica", "", 8)
        self.set_text_color(160, 162, 180)
        self.cell(210, 7, "MULTI-AGENT  AI  DEBATE  TRANSCRIPT", align="C",
                  new_x="LMARGIN", new_y="NEXT")

        # ── White body ────────────────────────────────────────────────────
        self.set_fill_color(*WHITE)
        self.rect(0, 60, 210, 237, "F")

        # ── Topic ────────────────────────────────────────────────────────
        self.set_y(72)
        self._section_label("DEBATE TOPIC")

        # Box: left-border only (clean, no background fill)
        topic_clean = _s(topic)
        y0 = self.get_y()
        self.set_x(L + 6)
        self.set_font("Helvetica", "B", 13)
        self.set_text_color(*INK)
        self.multi_cell(TW - 6, 7.5, topic_clean, new_x="LMARGIN", new_y="NEXT")
        y1 = self.get_y()

        # Left accent bar
        self.set_draw_color(*PRO)
        self.set_line_width(3)
        self.line(L, y0, L, y1)
        self.set_line_width(0.2)
        self.ln(10)

        # ── Metadata row ─────────────────────────────────────────────────
        self._rule()
        meta_y = self.get_y()

        cols = [
            ("ROUNDS",    str(rounds)),
            ("SESSION",   (session_id or "—")[:8]),
            ("DATE",      datetime.now(timezone.utc).strftime("%d %b %Y")),
            ("TIME (UTC)",datetime.now(timezone.utc).strftime("%H:%M")),
        ]
        col_w = TW / len(cols)
        for i, (label, val) in enumerate(cols):
            cx = L + i * col_w
            self.set_font("Helvetica", "", 7)
            self.set_text_color(*MUTED)
            self.set_xy(cx, meta_y)
            self.cell(col_w, 5, label, align="C")
            self.set_font("Helvetica", "B", 12)
            self.set_text_color(*INK)
            self.set_xy(cx, meta_y + 5)
            self.cell(col_w, 8, _s(val), align="C")

        self.set_y(meta_y + 16)
        self._rule()
        self.ln(6)

        # ── Winner ribbon (if available) ──────────────────────────────────
        if winner and winner not in ("", "Unknown"):
            w_color = PRO if winner == "Pro" else CON
            self._section_label("RESULT")
            wy = self.get_y()
            self.set_x(L)
            self.set_font("Helvetica", "B", 14)
            self.set_text_color(*w_color)
            arrow = ">>" if winner == "Pro" else "<<"
            self.cell(TW, 10,
                      f"{arrow}  {winner.upper()} AGENT WINS  {arrow}",
                      align="C", new_x="LMARGIN", new_y="NEXT")

            # Underline in accent color
            self.set_draw_color(*w_color)
            self.set_line_width(1.5)
            self.line(L + 30, self.get_y(), 210 - R - 30, self.get_y())
            self.set_line_width(0.2)
            self.ln(14)

        # ── Bottom accent bar ─────────────────────────────────────────────
        self.set_fill_color(*BAND_PRO)
        self.rect(0, 285, 105, 12, "F")
        self.set_fill_color(*BAND_CON)
        self.rect(105, 285, 105, 12, "F")

        self._in_cover = False


# ---------------------------------------------------------------------------
# Argument block
# ---------------------------------------------------------------------------
def _render_argument(pdf: DebatePDF, label: str, content: str, accent: tuple):
    """
    Render one agent argument.
    Structure:
      [LABEL BAR]    — 8pt, accent-colored text on NEAR_WHITE strip
      [text block]   — body text, 2pt left accent border drawn after
    """
    # Label strip
    pdf.set_fill_color(*NEAR_WHITE)
    pdf.set_x(L)
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(*accent)
    arrow = ">>" if label == "PRO" else "<<"
    pdf.cell(TW, 8, f"  {arrow}  {label} AGENT", fill=True,
             new_x="LMARGIN", new_y="NEXT")

    # Thin rule below label
    pdf.set_draw_color(*accent)
    pdf.set_line_width(0.5)
    pdf.line(L, pdf.get_y(), L + TW, pdf.get_y())
    pdf.set_line_width(0.2)
    pdf.ln(4)

    # Content — render line by line, track start Y for left border
    y_start = pdf.get_y()

    for raw in _s(content).split("\n"):
        line = raw.strip()
        if not line:
            pdf.ln(2.5)
            continue

        # Full-line heading **text**
        if re.match(r"^\*\*[^*]+\*\*$", line):
            heading = re.sub(r"\*+", "", line)
            pdf.ln(2)
            pdf.set_x(L + 4)
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_text_color(*accent)
            pdf.multi_cell(TW - 4, 5.5, heading, new_x="LMARGIN", new_y="NEXT")
            continue

        # Inline label **Key**: rest
        m = re.match(r"^\*\*(.+?)\*\*[:\s]+(.*)", line)
        if m:
            key  = _strip_md(m.group(1))
            rest = _s(m.group(2))
            pdf.set_x(L + 4)
            pdf.set_font("Helvetica", "B", 9)
            pdf.set_text_color(*INK)
            pdf.cell(0, 5.5, key + ":", new_x="LMARGIN", new_y="NEXT")
            if rest:
                pdf.set_x(L + 8)
                pdf.set_font("Helvetica", "", 9.5)
                pdf.set_text_color(*BODY)
                pdf.multi_cell(TW - 8, 5.5, rest, new_x="LMARGIN", new_y="NEXT")
            continue

        # Normal text
        pdf.set_x(L + 4)
        pdf.set_font("Helvetica", "", 9.5)
        pdf.set_text_color(*BODY)
        pdf.multi_cell(TW - 4, 5.5, _strip_md(line), new_x="LMARGIN", new_y="NEXT")

    y_end = pdf.get_y()

    # Left accent border (drawn after so height is exact)
    pdf.set_draw_color(*accent)
    pdf.set_line_width(2)
    pdf.line(L, y_start, L, y_end)
    pdf.set_line_width(0.2)

    # Bottom separator
    pdf.ln(2)
    pdf.set_draw_color(*RULE)
    pdf.set_line_width(0.3)
    pdf.line(L, pdf.get_y(), L + TW, pdf.get_y())
    pdf.ln(6)


# ---------------------------------------------------------------------------
# Verdict page
# ---------------------------------------------------------------------------
def _render_verdict(pdf: DebatePDF, state: dict):
    pdf.add_page()

    winner   = state.get("winner", "Unknown")
    reasoning = _s(state.get("reasoning", "No reasoning provided."))

    # Section heading bar
    pdf.set_fill_color(*BAND_BG)
    pdf.set_x(L)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(*WHITE)
    pdf.cell(TW, 11, "  JUDGE'S VERDICT", fill=True, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(8)

    # Winner line
    if winner and winner != "Unknown":
        w_color = PRO if winner == "Pro" else CON
        pdf.set_font("Helvetica", "B", 18)
        pdf.set_text_color(*w_color)
        arrow = ">>" if winner == "Pro" else "<<"
        pdf.cell(TW, 10, f"{arrow}  {winner.upper()} AGENT WINS  {arrow}",
                 align="C", new_x="LMARGIN", new_y="NEXT")

        pdf.set_draw_color(*w_color)
        pdf.set_line_width(1.5)
        pdf.line(L + 20, pdf.get_y() + 1, L + TW - 20, pdf.get_y() + 1)
        pdf.set_line_width(0.2)
        pdf.ln(10)

    # Reasoning
    pdf._section_label("REASONING")
    y0 = pdf.get_y()
    pdf.set_x(L + 4)
    pdf.set_font("Helvetica", "", 9.5)
    pdf.set_text_color(*BODY)
    pdf.multi_cell(TW - 4, 5.5, reasoning, new_x="LMARGIN", new_y="NEXT")
    y1 = pdf.get_y()

    # Gold left border on reasoning
    pdf.set_draw_color(*GOLD)
    pdf.set_line_width(2)
    pdf.line(L, y0, L, y1)
    pdf.set_line_width(0.2)
    pdf.ln(10)

    # Scores
    try:
        scores = json.loads(state.get("judge_scores", "{}"))
        if scores and not scores.get("parse_error"):
            _render_scores(pdf, scores)
    except (json.JSONDecodeError, ValueError):
        pass


def _render_scores(pdf: DebatePDF, scores: dict):
    pro_s = scores.get("pro_scores", {})
    con_s = scores.get("con_scores", {})

    # ── Score table ──────────────────────────────────────────────────────
    pdf._section_label("SCORES")

    # Column widths (must sum to TW = 174)
    c0, c1, c2 = 110, 32, 32

    # Header row
    pdf.set_fill_color(*BAND_BG)
    pdf.set_x(L)
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(*WHITE)
    pdf.cell(c0, 8, "  CATEGORY", fill=True)
    pdf.set_text_color(180, 230, 245)
    pdf.cell(c1, 8, "PRO", align="C", fill=True)
    pdf.set_text_color(255, 180, 200)
    pdf.cell(c2, 8, "CON", align="C", fill=True, new_x="LMARGIN", new_y="NEXT")

    categories = [
        ("logic",       "Logical Consistency"),
        ("evidence",    "Evidence Strength"),
        ("rhetoric",    "Rhetorical Skill"),
        ("rebuttal",    "Rebuttal Quality"),
        ("originality", "Argument Originality"),
    ]

    for i, (key, label) in enumerate(categories):
        fill = ROW_ALT if i % 2 == 0 else WHITE
        pdf.set_fill_color(*fill)
        pdf.set_draw_color(*RULE)
        pdf.set_line_width(0.2)
        pdf.set_x(L)

        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(*BODY)
        pdf.cell(c0, 7.5, f"  {label}", fill=True, border="B")

        pv, cv = pro_s.get(key, "—"), con_s.get(key, "—")
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(*PRO)
        pdf.cell(c1, 7.5, str(pv), align="C", fill=True, border="B")
        pdf.set_text_color(*CON)
        pdf.cell(c2, 7.5, str(cv), align="C", fill=True, border="B",
                 new_x="LMARGIN", new_y="NEXT")

    # Totals row
    pdf.set_fill_color(*INK)
    pdf.set_x(L)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(*WHITE)
    pdf.cell(c0, 8.5, "  TOTAL", fill=True)
    pdf.set_text_color(180, 230, 245)
    pdf.cell(c1, 8.5, str(scores.get("pro_total", "-")), align="C", fill=True)
    pdf.set_text_color(255, 180, 200)
    pdf.cell(c2, 8.5, str(scores.get("con_total", "-")), align="C", fill=True,
             new_x="LMARGIN", new_y="NEXT")
    pdf.ln(10)

    # ── Key moments ──────────────────────────────────────────────────────
    moments = scores.get("key_moments", [])
    if moments:
        pdf._section_label("KEY MOMENTS")
        for i, moment in enumerate(moments, 1):
            pdf.set_x(L)
            pdf.set_font("Helvetica", "B", 9)
            pdf.set_text_color(*GOLD)
            pdf.cell(7, 5.5, f"{i}.")
            pdf.set_font("Helvetica", "", 9.5)
            pdf.set_text_color(*BODY)
            pdf.multi_cell(TW - 7, 5.5, _s(moment), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(6)

    # ── Deciding factor ──────────────────────────────────────────────────
    deciding = scores.get("deciding_factor", "")
    if deciding:
        pdf._rule(GOLD, 0.5)
        pdf._section_label("DECIDING FACTOR")
        y0 = pdf.get_y()
        pdf.set_x(L + 4)
        pdf.set_font("Helvetica", "I", 9.5)
        pdf.set_text_color(*GOLD)
        pdf.multi_cell(TW - 4, 5.5, _s(deciding), new_x="LMARGIN", new_y="NEXT")
        y1 = pdf.get_y()
        pdf.set_draw_color(*GOLD)
        pdf.set_line_width(2)
        pdf.line(L, y0, L, y1)
        pdf.set_line_width(0.2)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def generate_debate_pdf(state: dict, session_id: str = "") -> bytes:
    args_for     = state.get("arguments_for", [])
    args_against = state.get("arguments_against", [])
    rounds       = max(len(args_for), len(args_against), 1)

    pdf = DebatePDF()

    # Cover
    pdf.cover_page(
        topic=state.get("topic", "Unknown Topic"),
        session_id=session_id,
        rounds=rounds,
        winner=state.get("winner", ""),
    )

    # Rounds
    pdf.add_page()
    for i in range(rounds):
        # Round header
        pdf.set_fill_color(*NEAR_WHITE)
        pdf.set_draw_color(*RULE)
        pdf.set_line_width(0.2)
        pdf.set_x(L)
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_text_color(*MUTED)
        pdf.cell(TW, 8, f"  ROUND {i + 1}", fill=True, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(5)

        if i < len(args_for):
            _render_argument(pdf, "PRO", args_for[i]["content"], PRO)
        if i < len(args_against):
            _render_argument(pdf, "CON", args_against[i]["content"], CON)
        pdf.ln(3)

    # Verdict
    _render_verdict(pdf, state)

    return bytes(pdf.output())
