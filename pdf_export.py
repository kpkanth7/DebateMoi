"""
DebateMoi — PDF Export
=======================
Generates a polished, color-coded PDF transcript using fpdf2.
Layout: cover page → debate rounds (Pro/Con) → verdict & scores.
"""

import io
import json
import re
import textwrap
from datetime import datetime, timezone
from fpdf import FPDF

# ---------------------------------------------------------------------------
# Unicode sanitiser
# ---------------------------------------------------------------------------
_UNICODE_MAP = {
    "‘": "'", "’": "'", "“": '"', "”": '"',
    "–": "-", "—": "-", "…": "...", "•": "*",
    "·": "*", "°": "deg", "®": "(R)", "©": "(c)",
    "™": "(TM)", "é": "e", "è": "e", "ê": "e",
    "à": "a", "â": "a", "ô": "o", "û": "u",
    "ü": "u", "ç": "c",
    # Emoji / symbols
    "⚔️": ">>", "\U0001F6E1️": "<<", "⚖️": "=",
    "⚠️": "!", "✅": "[OK]", "❌": "[X]",
    "\U0001F3C6": "[WIN]", "\U0001F4DD": "[NOTE]", "\U0001F511": "[KEY]",
    "\U0001F3AD": "[*]",
}

def _sanitise(text: str) -> str:
    """Replace known Unicode chars; strip remaining non-latin1."""
    if not text:
        return ""
    for src, dst in _UNICODE_MAP.items():
        text = text.replace(src, dst)
    return text.encode("latin-1", "ignore").decode("latin-1")


def _strip_md_bold(text: str) -> str:
    """Strip **bold** markers for plain-text contexts."""
    return re.sub(r"\*{1,2}(.+?)\*{1,2}", r"\1", text)


# ---------------------------------------------------------------------------
# PDF class
# ---------------------------------------------------------------------------
class DebatePDF(FPDF):

    def __init__(self):
        super().__init__()
        self.set_margins(left=15, top=15, right=15)
        self.set_auto_page_break(auto=True, margin=20)

    def header(self):
        if self.page_no() == 1:
            return  # Cover page handles its own header
        # Running header
        self.set_fill_color(10, 10, 15)
        self.rect(0, 0, 210, 12, "F")
        self.set_font("Helvetica", "B", 7)
        self.set_text_color(0, 180, 220)
        self.set_xy(0, 3)
        self.cell(0, 6, "D E B A T E M O I  //  MULTI-AGENT DEBATE TRANSCRIPT", align="C")
        self.ln(12)

    def footer(self):
        if self.page_no() == 1:
            return
        self.set_y(-14)
        self.set_font("Helvetica", "I", 7)
        self.set_text_color(80, 80, 90)
        self.cell(0, 8, f"debatemoi.streamlit.app  |  Page {self.page_no()}", align="C")

    def cover_page(self, topic: str, session_id: str, rounds: int):
        """Full cover page with branding."""
        self.add_page()

        # Dark background
        self.set_fill_color(8, 8, 12)
        self.rect(0, 0, 210, 297, "F")

        # Top accent bar — cyan
        self.set_fill_color(0, 212, 255)
        self.rect(0, 0, 105, 3, "F")
        # Top accent bar — magenta
        self.set_fill_color(255, 0, 110)
        self.rect(105, 0, 105, 3, "F")

        # Brand name
        self.set_y(55)
        self.set_font("Helvetica", "B", 36)
        self.set_text_color(0, 212, 255)
        self.cell(0, 16, "DEBATEMOI", align="C", new_x="LMARGIN", new_y="NEXT")

        # Tagline
        self.set_font("Helvetica", "", 9)
        self.set_text_color(80, 80, 95)
        self.cell(0, 8, "MULTI-AGENT DEBATE TRANSCRIPT", align="C", new_x="LMARGIN", new_y="NEXT")

        # Divider
        self.ln(10)
        self.set_draw_color(0, 212, 255)
        self.set_line_width(0.3)
        self.line(50, self.get_y(), 160, self.get_y())
        self.ln(14)

        # Topic box
        self.set_fill_color(18, 18, 28)
        self.set_draw_color(0, 212, 255)
        self.set_line_width(0.5)
        topic_clean = _sanitise(topic)
        # Wrap topic text
        wrapped = textwrap.fill(topic_clean, width=55)
        lines = wrapped.split("\n")
        box_h = max(24, len(lines) * 9 + 18)
        bx, by = 25, self.get_y()
        self.rect(bx, by, 160, box_h, "DF")

        self.set_font("Helvetica", "", 7)
        self.set_text_color(0, 150, 180)
        self.set_xy(bx, by + 5)
        self.cell(160, 6, "DEBATE TOPIC", align="C", new_x="LMARGIN", new_y="NEXT")

        self.set_font("Helvetica", "B", 12)
        self.set_text_color(230, 230, 240)
        self.set_x(bx + 8)
        self.multi_cell(144, 7, topic_clean, align="C", new_x="LMARGIN", new_y="NEXT")

        self.ln(20)

        # Stats row
        stats = [
            ("ROUNDS", str(rounds)),
            ("SESSION", session_id[:8] if session_id else "—"),
            ("MODELS", "DeepSeek + GPT-4o"),
        ]
        col_w = 56
        start_x = 21
        for i, (label, val) in enumerate(stats):
            cx = start_x + i * (col_w + 4)
            self.set_fill_color(20, 20, 30)
            self.set_draw_color(40, 40, 55)
            self.set_line_width(0.3)
            self.rect(cx, self.get_y(), col_w, 22, "DF")
            self.set_font("Helvetica", "", 7)
            self.set_text_color(80, 80, 95)
            self.set_xy(cx, self.get_y() + 4)
            self.cell(col_w, 5, label, align="C", new_x="LMARGIN", new_y="NEXT")
            self.set_font("Helvetica", "B", 11)
            self.set_text_color(200, 200, 215)
            self.set_x(cx)
            self.cell(col_w, 7, _sanitise(val), align="C")

        self.ln(32)

        # Timestamp
        ts = datetime.now(timezone.utc).strftime("%d %b %Y  %H:%M UTC")
        self.set_font("Helvetica", "", 8)
        self.set_text_color(50, 50, 60)
        self.cell(0, 6, ts, align="C", new_x="LMARGIN", new_y="NEXT")

        # Bottom accent bar
        self.set_fill_color(255, 0, 110)
        self.rect(0, 293, 105, 4, "F")
        self.set_fill_color(0, 212, 255)
        self.rect(105, 293, 105, 4, "F")


# ---------------------------------------------------------------------------
# Argument renderer
# ---------------------------------------------------------------------------
def _render_argument(pdf: DebatePDF, label: str, content: str,
                     accent: tuple, label_color: tuple):
    """Render one argument block with colored left border and heading."""
    y_start = pdf.get_y()

    # Agent label bar
    pdf.set_fill_color(15, 15, 22)
    pdf.set_x(15)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(*label_color)
    icon = ">>" if label == "PRO" else "<<"
    pdf.cell(180, 8, f"  {icon}  {label} AGENT", fill=True,
             new_x="LMARGIN", new_y="NEXT")

    # Content
    pdf.set_font("Helvetica", "", 9.5)
    for raw_line in _sanitise(content).split("\n"):
        line = raw_line.strip()
        if not line:
            pdf.ln(2.5)
            continue

        # Full-line heading (**text**)
        if re.match(r"^\*\*(.+)\*\*$", line):
            heading = re.sub(r"\*+", "", line).strip()
            pdf.ln(2)
            pdf.set_x(18)
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_text_color(*accent)
            pdf.multi_cell(177, 5.5, heading,
                           new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", "", 9.5)
            pdf.set_text_color(70, 70, 80)
            continue

        # Inline bold label (**Key**: rest)
        m = re.match(r"^\*\*(.+?)\*\*[:\s]+(.*)", line)
        if m:
            key_text = m.group(1).strip()
            rest = m.group(2).strip()
            pdf.set_x(18)
            pdf.set_font("Helvetica", "B", 9.5)
            pdf.set_text_color(160, 160, 175)
            pdf.cell(0, 5, key_text + ":", new_x="LMARGIN", new_y="NEXT")
            if rest:
                pdf.set_x(22)
                pdf.set_font("Helvetica", "", 9.5)
                pdf.set_text_color(70, 70, 80)
                pdf.multi_cell(173, 5, rest,
                               new_x="LMARGIN", new_y="NEXT")
            continue

        # Normal text
        clean = re.sub(r"\*+", "", line)
        pdf.set_x(18)
        pdf.set_font("Helvetica", "", 9.5)
        pdf.set_text_color(70, 70, 80)
        pdf.multi_cell(177, 5, clean,
                       new_x="LMARGIN", new_y="NEXT")

    y_end = pdf.get_y()

    # Left border accent
    pdf.set_draw_color(*accent)
    pdf.set_line_width(2)
    pdf.line(13, y_start, 13, y_end)
    pdf.set_line_width(0.2)
    pdf.ln(5)


# ---------------------------------------------------------------------------
# Verdict renderer
# ---------------------------------------------------------------------------
def _render_verdict(pdf: DebatePDF, state: dict):
    """Render verdict page with gold styling and score table."""
    pdf.add_page()

    winner = state.get("winner", "Unknown")
    reasoning = state.get("reasoning", "No reasoning available.")

    # Gold header bar
    pdf.set_fill_color(40, 35, 8)
    pdf.set_draw_color(200, 165, 0)
    pdf.set_line_width(0.5)
    y0 = pdf.get_y()
    pdf.rect(15, y0, 180, 18, "DF")
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(255, 215, 0)
    pdf.set_xy(15, y0 + 2)
    pdf.cell(180, 14, "  JUDGE'S VERDICT", align="L")
    pdf.ln(24)

    # Winner announcement
    w_color = (0, 212, 255) if winner == "Pro" else (255, 0, 110)
    pdf.set_font("Helvetica", "B", 22)
    pdf.set_text_color(*w_color)
    pdf.cell(0, 12, f"{winner.upper()} AGENT WINS",
             align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(8)

    # Divider
    pdf.set_draw_color(*w_color)
    pdf.set_line_width(0.4)
    pdf.line(40, pdf.get_y(), 170, pdf.get_y())
    pdf.ln(8)

    # Reasoning
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(200, 165, 0)
    pdf.cell(0, 6, "REASONING", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    pdf.set_fill_color(18, 18, 25)
    pdf.set_draw_color(50, 45, 15)
    pdf.set_line_width(0.2)
    reasoning_clean = _sanitise(reasoning)
    wrapped = textwrap.fill(reasoning_clean, width=90)
    lines = wrapped.count("\n") + 1
    box_h = max(20, lines * 5.5 + 12)
    pdf.rect(15, pdf.get_y(), 180, box_h, "DF")
    pdf.set_x(18)
    pdf.set_font("Helvetica", "", 9.5)
    pdf.set_text_color(75, 75, 85)
    pdf.multi_cell(174, 5.5, reasoning_clean,
                   new_x="LMARGIN", new_y="NEXT")
    pdf.ln(10)

    # Scores
    judge_scores_str = state.get("judge_scores", "")
    if judge_scores_str:
        try:
            scores = json.loads(judge_scores_str)
            if not scores.get("parse_error"):
                _render_scores(pdf, scores)
        except (json.JSONDecodeError, ValueError):
            pass


def _render_scores(pdf: DebatePDF, scores: dict):
    """Score table + key moments + deciding factor."""
    pro_scores = scores.get("pro_scores", {})
    con_scores = scores.get("con_scores", {})

    # Section heading
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(180, 180, 195)
    pdf.cell(0, 8, "DETAILED SCORES", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)

    # Table header
    row_h = 7
    c1, c2, c3 = 90, 45, 45
    pdf.set_fill_color(22, 22, 32)
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_x(15)
    pdf.set_text_color(140, 140, 155)
    pdf.cell(c1, row_h, "  CATEGORY", fill=True)
    pdf.set_text_color(0, 180, 220)
    pdf.cell(c2, row_h, "PRO", align="C", fill=True)
    pdf.set_text_color(200, 0, 90)
    pdf.cell(c3, row_h, "CON", align="C", fill=True,
             new_x="LMARGIN", new_y="NEXT")

    categories = [
        ("logic", "Logical Consistency"),
        ("evidence", "Evidence Strength"),
        ("rhetoric", "Rhetorical Skill"),
        ("rebuttal", "Rebuttal Quality"),
        ("originality", "Argument Originality"),
    ]

    alt = False
    for key, label in categories:
        fill_c = (20, 20, 30) if alt else (16, 16, 24)
        pdf.set_fill_color(*fill_c)
        pdf.set_x(15)
        pdf.set_font("Helvetica", "", 8.5)
        pdf.set_text_color(80, 80, 92)
        pdf.cell(c1, row_h, f"  {label}", fill=True)

        pro_v = pro_scores.get(key, 0)
        con_v = con_scores.get(key, 0)

        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(0, 170, 210)
        pdf.cell(c2, row_h, str(pro_v), align="C", fill=True)
        pdf.set_text_color(200, 0, 90)
        pdf.cell(c3, row_h, str(con_v), align="C", fill=True,
                 new_x="LMARGIN", new_y="NEXT")
        alt = not alt

    # Totals row
    pdf.set_fill_color(28, 28, 40)
    pdf.set_x(15)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(160, 160, 175)
    pdf.cell(c1, row_h + 1, "  TOTAL", fill=True)
    pdf.set_text_color(0, 212, 255)
    pdf.cell(c2, row_h + 1, str(scores.get("pro_total", "—")), align="C", fill=True)
    pdf.set_text_color(255, 0, 110)
    pdf.cell(c3, row_h + 1, str(scores.get("con_total", "—")), align="C", fill=True,
             new_x="LMARGIN", new_y="NEXT")
    pdf.ln(10)

    # Key moments
    key_moments = scores.get("key_moments", [])
    if key_moments:
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(200, 165, 0)
        pdf.cell(0, 6, "KEY MOMENTS", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)
        for i, moment in enumerate(key_moments, 1):
            pdf.set_x(18)
            pdf.set_font("Helvetica", "B", 8.5)
            pdf.set_text_color(120, 100, 0)
            pdf.cell(8, 5.5, f"{i}.")
            pdf.set_font("Helvetica", "", 8.5)
            pdf.set_text_color(75, 75, 85)
            pdf.multi_cell(167, 5.5, _sanitise(moment),
                           new_x="LMARGIN", new_y="NEXT")
        pdf.ln(6)

    # Deciding factor
    deciding = scores.get("deciding_factor", "")
    if deciding:
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(200, 165, 0)
        pdf.cell(0, 6, "DECIDING FACTOR", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)
        pdf.set_fill_color(30, 25, 8)
        pdf.set_draw_color(100, 80, 0)
        pdf.set_line_width(0.2)
        deciding_clean = _sanitise(deciding)
        pdf.set_x(15)
        box_h = max(12, len(deciding_clean) // 80 * 5.5 + 10)
        pdf.rect(15, pdf.get_y(), 180, box_h, "DF")
        pdf.set_x(18)
        pdf.set_font("Helvetica", "I", 9)
        pdf.set_text_color(175, 140, 0)
        pdf.multi_cell(174, 5.5, deciding_clean,
                       new_x="LMARGIN", new_y="NEXT")


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------
def generate_debate_pdf(state: dict, session_id: str = "") -> bytes:
    """Generate a polished PDF from debate state. Returns raw bytes."""
    args_for = state.get("arguments_for", [])
    args_against = state.get("arguments_against", [])
    rounds_played = max(len(args_for), len(args_against))

    pdf = DebatePDF()

    # Cover page
    pdf.cover_page(
        topic=state.get("topic", "Unknown Topic"),
        session_id=session_id,
        rounds=rounds_played,
    )

    # Debate rounds
    pdf.add_page()
    for i in range(rounds_played):
        # Round header
        pdf.set_fill_color(22, 22, 34)
        pdf.set_draw_color(40, 40, 58)
        pdf.set_line_width(0.2)
        pdf.set_x(15)
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(140, 140, 165)
        pdf.cell(180, 10, f"  ROUND {i + 1}", fill=True,
                 new_x="LMARGIN", new_y="NEXT")
        pdf.ln(4)

        if i < len(args_for):
            _render_argument(
                pdf, "PRO", args_for[i]["content"],
                accent=(0, 180, 220), label_color=(0, 212, 255),
            )

        if i < len(args_against):
            _render_argument(
                pdf, "CON", args_against[i]["content"],
                accent=(200, 0, 90), label_color=(255, 0, 110),
            )

        pdf.ln(4)

    # Verdict
    _render_verdict(pdf, state)

    return bytes(pdf.output())
