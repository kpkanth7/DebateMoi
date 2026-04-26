"""
DebateMoi — Streamlit UI
=========================
Cinematic dark-mode debate interface with streaming, session recovery,
rate limiting, and dramatic verdict reveal.
"""

import json
import uuid
import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv

load_dotenv()

from graph import create_graph, get_initial_state
from rate_limiter import RateLimiter
from pdf_export import generate_debate_pdf

# ---------------------------------------------------------------------------
# Page Configuration
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="DebateMoi — AI Debate Arena",
    page_icon="🎭",
    layout="wide",
    initial_sidebar_state="expanded",
)
# ---------------------------------------------------------------------------
# Theme State
# ---------------------------------------------------------------------------
if "theme" not in st.session_state:
    st.session_state.theme = "Dark"

# ---------------------------------------------------------------------------
# Custom CSS — Dynamic Theme
# ---------------------------------------------------------------------------
_t = st.session_state.theme
if _t == "Light":
    _bg1, _bg2, _bgc = "#f4f4f8", "#ffffff", "rgba(255,255,255,0.9)"
    _txt1, _txt2, _txtm = "#1a1a2e", "#3a3a5a", "#7a7a9a"
    _border = "rgba(0,0,0,0.08)"
    _sidebar_bg = "linear-gradient(180deg, #eeeef4 0%, #f8f8fc 100%)"
    _card_shadow_pro = "rgba(0, 212, 255, 0.12)"
    _card_shadow_con = "rgba(255, 0, 110, 0.12)"
    _dot_color = "rgba(0,0,0,0.04)"
else:
    _bg1, _bg2, _bgc = "#0a0a0f", "#0f0f18", "rgba(15, 15, 24, 0.85)"
    _txt1, _txt2, _txtm = "#e8e8f0", "#8888a0", "#555570"
    _border = "rgba(255, 255, 255, 0.06)"
    _sidebar_bg = "linear-gradient(180deg, #08080d 0%, #0d0d16 100%)"
    _card_shadow_pro = "rgba(0, 212, 255, 0.08)"
    _card_shadow_con = "rgba(255, 0, 110, 0.08)"
    _dot_color = "rgba(255,255,255,0.03)"
st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@300;400;500;600;700&display=swap');

    :root {{
        --bg-primary: {_bg1};
        --bg-secondary: {_bg2};
        --bg-card: {_bgc};
        --pro-color: #00d4ff;
        --pro-glow: rgba(0, 212, 255, 0.3);
        --con-color: #ff006e;
        --con-glow: rgba(255, 0, 110, 0.3);
        --judge-color: #ffd700;
        --judge-glow: rgba(255, 215, 0, 0.3);
        --text-primary: {_txt1};
        --text-secondary: {_txt2};
        --text-muted: {_txtm};
        --border-subtle: {_border};
    }}

    .stApp, [data-testid="stAppViewContainer"] {{
        background: var(--bg-primary) !important;
        color: var(--text-primary) !important;
        font-family: 'Inter', sans-serif !important;
    }}

    .stApp::before {{
        content: '';
        position: fixed;
        top: 0; left: 0; right: 0; bottom: 0;
        background-image: radial-gradient({_dot_color} 1px, transparent 1px);
        background-size: 30px 30px;
        pointer-events: none;
        z-index: 0;
    }}

    [data-testid="stSidebar"] {{
        background: {_sidebar_bg} !important;
        border-right: 1px solid var(--border-subtle) !important;
    }}

    [data-testid="stSidebar"] * {{
        color: var(--text-primary) !important;
    }}

    [data-testid="stHeader"] {{
        background: var(--bg-primary) !important;
    }}

    header[data-testid="stHeader"] {{
        background: var(--bg-primary) !important;
    }}

    h1, h2, h3 {{
        font-family: 'Inter', sans-serif !important;
        font-weight: 800 !important;
    }}

    .stTextInput input, .stTextArea textarea {{
        background: var(--bg-secondary) !important;
        border: 1px solid var(--border-subtle) !important;
        color: var(--text-primary) !important;
        font-family: 'JetBrains Mono', monospace !important;
        border-radius: 8px !important;
        transition: border-color 0.3s ease, box-shadow 0.3s ease !important;
    }}

    .stTextInput input:focus, .stTextArea textarea:focus {{
        border-color: var(--pro-color) !important;
        box-shadow: 0 0 15px var(--pro-glow) !important;
    }}

    [data-testid="stSidebar"] .stButton > button {{
        background: linear-gradient(135deg, #00d4ff 0%, #a855f7 50%, #ff006e 100%) !important;
        color: #fff !important;
        font-family: 'Inter', sans-serif !important;
        font-weight: 700 !important;
        font-size: 1rem !important;
        letter-spacing: 0.5px !important;
        border: none !important;
        border-radius: 10px !important;
        padding: 0.7rem 2rem !important;
        width: 100% !important;
        cursor: pointer !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 4px 20px rgba(0, 212, 255, 0.25) !important;
    }}

    [data-testid="stSidebar"] .stButton > button:hover {{
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 30px rgba(0, 212, 255, 0.4), 0 0 40px rgba(168, 85, 247, 0.2) !important;
    }}

    [data-testid="stSidebar"] .stButton > button:active {{
        transform: scale(0.97) !important;
    }}

    .debate-card {{
        background: var(--bg-card);
        backdrop-filter: blur(12px);
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        border: 1px solid var(--border-subtle);
        animation: fadeSlideIn 0.6s ease-out;
        font-family: 'JetBrains Mono', monospace;
        line-height: 1.7;
    }}

    .debate-card.pro {{
        border-left: 3px solid var(--pro-color);
        box-shadow: 0 4px 20px {_card_shadow_pro};
    }}

    .debate-card.con {{
        border-left: 3px solid var(--con-color);
        box-shadow: 0 4px 20px {_card_shadow_con};
    }}

    .debate-card.judge {{
        border: 2px solid var(--judge-color);
        box-shadow: 0 4px 30px var(--judge-glow);
        background: rgba(40, 35, 10, 0.5);
    }}

    .card-header {{
        display: flex;
        align-items: center;
        gap: 0.5rem;
        margin-bottom: 0.8rem;
        font-family: 'Inter', sans-serif;
    }}

    .card-header .agent-name {{
        font-weight: 700;
        font-size: 0.95rem;
        text-transform: uppercase;
        letter-spacing: 1px;
    }}

    .card-header .agent-name.pro {{ color: var(--pro-color); }}
    .card-header .agent-name.con {{ color: var(--con-color); }}
    .card-header .agent-name.judge {{ color: var(--judge-color); }}

    .round-badge {{
        display: inline-block;
        background: rgba(255,255,255,0.06);
        padding: 0.15rem 0.6rem;
        border-radius: 20px;
        font-size: 0.7rem;
        color: var(--text-muted);
        font-weight: 600;
        letter-spacing: 0.5px;
        text-transform: uppercase;
    }}

    .card-content {{
        color: var(--text-secondary);
        font-size: 0.88rem;
        white-space: pre-wrap;
    }}

    .verdict-winner {{
        text-align: center;
        font-family: 'Inter', sans-serif;
        font-weight: 900;
        font-size: 2.2rem;
        margin: 1rem 0;
        text-shadow: 0 0 30px var(--judge-glow);
        animation: glowPulse 2s ease-in-out infinite;
    }}

    .verdict-winner.pro {{ color: var(--pro-color); text-shadow: 0 0 30px var(--pro-glow); }}
    .verdict-winner.con {{ color: var(--con-color); text-shadow: 0 0 30px var(--con-glow); }}

    .score-bar {{
        flex: 1;
        height: 8px;
        background: rgba(255,255,255,0.05);
        border-radius: 4px;
        overflow: hidden;
    }}

    .score-fill {{
        height: 100%;
        border-radius: 4px;
        transition: width 1s ease;
    }}

    .score-fill.pro {{ background: linear-gradient(90deg, var(--pro-color), #00a8cc); }}
    .score-fill.con {{ background: linear-gradient(90deg, var(--con-color), #cc005a); }}

    .score-value {{
        width: 30px;
        text-align: right;
        font-weight: 600;
    }}

    .score-value.pro {{ color: var(--pro-color); }}
    .score-value.con {{ color: var(--con-color); }}

    .main-title {{
        text-align: center;
        font-family: 'Inter', sans-serif;
        font-weight: 900;
        font-size: 3rem;
        background: linear-gradient(135deg, #00d4ff, #a855f7, #ff006e);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin-bottom: 0.2rem;
        animation: fadeSlideIn 0.8s ease-out;
    }}

    .main-subtitle {{
        text-align: center;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.85rem;
        color: var(--text-muted);
        letter-spacing: 2px;
        text-transform: uppercase;
        margin-bottom: 2rem;
    }}

    .rate-limit-banner {{
        background: linear-gradient(135deg, rgba(255,0,110,0.15), rgba(255,0,110,0.05));
        border: 1px solid rgba(255,0,110,0.3);
        border-radius: 12px;
        padding: 2rem;
        text-align: center;
        margin: 2rem 0;
    }}

    .rate-limit-banner h3 {{ color: var(--con-color); }}
    .rate-limit-banner p {{ color: var(--text-secondary); }}

    @keyframes fadeSlideIn {{
        from {{ opacity: 0; transform: translateY(15px); }}
        to {{ opacity: 1; transform: translateY(0); }}
    }}

    @keyframes glowPulse {{
        0%, 100% {{ opacity: 1; }}
        50% {{ opacity: 0.85; }}
    }}

    .stMarkdown, .stMarkdown p {{ color: var(--text-primary) !important; }}
    [data-testid="stExpander"] {{
        background: var(--bg-card) !important;
        border: 1px solid var(--border-subtle) !important;
        border-radius: 10px !important;
    }}
    .stDownloadButton > button {{
        background: linear-gradient(135deg, #ffd700, #ff8c00) !important;
        color: #000 !important;
        font-weight: 700 !important;
        border: none !important;
        border-radius: 8px !important;
    }}
    div[data-testid="stStatusWidget"] {{ visibility: hidden; }}
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Session State Initialization
# ---------------------------------------------------------------------------
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())[:8]
if "debate_running" not in st.session_state:
    st.session_state.debate_running = False
if "debate_complete" not in st.session_state:
    st.session_state.debate_complete = False
if "debate_state" not in st.session_state:
    st.session_state.debate_state = None
if "debate_events" not in st.session_state:
    st.session_state.debate_events = []
if "recovered" not in st.session_state:
    st.session_state.recovered = False


# ---------------------------------------------------------------------------
# Helper: Recover Session from SQLite Checkpoint
# ---------------------------------------------------------------------------
def try_recover_session(sid: str):
    """Attempt to load a previous debate state from the SQLite checkpoint."""
    if st.session_state.recovered and st.session_state.debate_events:
        return  # Already recovered for this session
    try:
        graph, conn = create_graph()
        config = {"configurable": {"thread_id": sid}}
        saved = graph.get_state(config)
        if saved and saved.values and saved.values.get("arguments_for"):
            state = dict(saved.values)
            # Rebuild debate_events from the saved state
            events = []
            args_for = state.get("arguments_for", [])
            args_against = state.get("arguments_against", [])
            rounds_played = max(len(args_for), len(args_against))
            for i in range(rounds_played):
                if i < len(args_for):
                    events.append({
                        "type": "pro",
                        "round": args_for[i].get("round", i + 1),
                        "content": args_for[i].get("content", ""),
                    })
                if i < len(args_against):
                    events.append({
                        "type": "con",
                        "round": args_against[i].get("round", i + 1),
                        "content": args_against[i].get("content", ""),
                    })
            st.session_state.debate_events = events
            st.session_state.debate_state = state
            st.session_state.debate_complete = bool(state.get("winner"))
            st.session_state.recovered = True
        conn.close()
    except Exception:
        pass  # No saved state or DB doesn't exist yet


# ---------------------------------------------------------------------------
# Helper: Get User IP
# ---------------------------------------------------------------------------
def get_user_ip() -> str:
    """Extract user IP from Streamlit headers or fallback."""
    try:
        headers = st.context.headers
        # Check common proxy headers
        for header in ["X-Forwarded-For", "X-Real-Ip", "CF-Connecting-IP"]:
            ip = headers.get(header)
            if ip:
                return ip.split(",")[0].strip()
        return headers.get("Host", "127.0.0.1")
    except Exception:
        return "127.0.0.1"


# ---------------------------------------------------------------------------
# Helper: Render Debate Card (inline HTML)
# ---------------------------------------------------------------------------
import re

def _md_to_html(text: str) -> str:
    """Convert basic markdown to HTML for card display."""
    # Bold: **text** → <strong>text</strong>
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    # Italic: *text* → <em>text</em>
    text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
    # Convert newlines to <br> for proper spacing
    text = text.replace('\n\n', '<br><br>').replace('\n', '<br>')
    return text

def render_card_html(agent_type: str, round_num: int, content: str) -> str:
    """Return styled debate argument card HTML."""
    icon = "⚔️" if agent_type == "pro" else "🛡️" if agent_type == "con" else "⚖️"
    label = "PRO AGENT" if agent_type == "pro" else "CON AGENT" if agent_type == "con" else "JUDGE"
    formatted = _md_to_html(content)
    return f"""
    <div class="debate-card {agent_type}">
        <div class="card-header">
            <span style="font-size: 1.2rem;">{icon}</span>
            <span class="agent-name {agent_type}">{label}</span>
            <span class="round-badge">Round {round_num}</span>
        </div>
        <div class="card-content">{formatted}</div>
    </div>
    """

def render_card(agent_type: str, round_num: int, content: str):
    """Render a styled debate argument card."""
    st.markdown(render_card_html(agent_type, round_num, content), unsafe_allow_html=True)


def render_score_bar(label: str, pro_val: int, con_val: int):
    """Render a comparison score bar for a category."""
    html = f"""
    <div style="display: flex; gap: 10px; align-items: center; margin: 6px 0; font-family: 'JetBrains Mono', monospace; font-size: 0.82rem;">
        <div style="width: 160px; color: #555570;">{label}</div>
        <div class="score-value pro">{pro_val}</div>
        <div class="score-bar"><div class="score-fill pro" style="width: {pro_val * 10}%;"></div></div>
        <div style="width: 20px;"></div>
        <div class="score-bar"><div class="score-fill con" style="width: {con_val * 10}%;"></div></div>
        <div class="score-value con">{con_val}</div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Helper: Show Verdict
# ---------------------------------------------------------------------------
def show_verdict(state):
    """Display the dramatic verdict section."""
    winner = state.get("winner", "Unknown")
    reasoning = state.get("reasoning", "")
    judge_scores_str = state.get("judge_scores", "")

    st.markdown("---")
    st.markdown('<div id="verdict-section"></div>', unsafe_allow_html=True)

    winner_class = "pro" if winner == "Pro" else "con"
    winner_icon = "⚔️" if winner == "Pro" else "🛡️"

    verdict_html = f"""
    <div class="debate-card judge">
        <div style="text-align: center; margin-bottom: 0.5rem;">
            <span style="font-size: 2rem;">⚖️</span>
        </div>
        <div class="verdict-winner {winner_class}">
            {winner_icon} {winner.upper()} AGENT WINS {winner_icon}
        </div>
    </div>
    """
    st.markdown(verdict_html, unsafe_allow_html=True)

    try:
        scores = json.loads(judge_scores_str) if judge_scores_str else {}
        if scores and not scores.get("parse_error"):
            pro_scores = scores.get("pro_scores", {})
            con_scores = scores.get("con_scores", {})

            categories = [
                ("Logical Consistency", "logic"),
                ("Evidence Strength", "evidence"),
                ("Rhetorical Skill", "rhetoric"),
                ("Rebuttal Quality", "rebuttal"),
                ("Argument Originality", "originality"),
            ]

            st.markdown(f"""
            <div style="display: flex; gap: 10px; align-items: center; margin: 12px 0 4px 0; font-family: 'JetBrains Mono', monospace; font-size: 0.75rem;">
                <div style="width: 160px;"></div>
                <div style="width: 30px; text-align: right; color: #00d4ff; font-weight: 700;">PRO</div>
                <div style="flex: 1;"></div>
                <div style="width: 20px;"></div>
                <div style="flex: 1;"></div>
                <div style="width: 30px; text-align: left; color: #ff006e; font-weight: 700;">CON</div>
            </div>
            """, unsafe_allow_html=True)

            for label, key in categories:
                render_score_bar(label, pro_scores.get(key, 0), con_scores.get(key, 0))

            st.markdown(f"""
            <div style="display: flex; justify-content: center; gap: 3rem; margin: 1.5rem 0; font-family: 'Inter', sans-serif;">
                <div style="text-align: center;">
                    <div style="font-size: 2rem; font-weight: 800; color: #00d4ff;">{scores.get('pro_total', '-')}</div>
                    <div style="font-size: 0.7rem; color: #555570; text-transform: uppercase; letter-spacing: 1px;">Pro Total</div>
                </div>
                <div style="text-align: center;">
                    <div style="font-size: 2rem; font-weight: 800; color: #ff006e;">{scores.get('con_total', '-')}</div>
                    <div style="font-size: 0.7rem; color: #555570; text-transform: uppercase; letter-spacing: 1px;">Con Total</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            deciding = scores.get("deciding_factor", "")
            if deciding:
                st.markdown(f"""
                <div style="text-align: center; padding: 1rem; background: rgba(255, 215, 0, 0.05); border: 1px solid rgba(255, 215, 0, 0.2); border-radius: 10px; margin: 1rem 0;">
                    <div style="font-size: 0.7rem; color: #ffd700; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 0.3rem;">Deciding Factor</div>
                    <div style="font-size: 0.9rem; color: #8888a0; font-style: italic;">{deciding}</div>
                </div>
                """, unsafe_allow_html=True)
    except (json.JSONDecodeError, ValueError):
        pass

    st.markdown('<div style="font-family: \'Inter\', sans-serif; font-weight: 800; font-size: 1.1rem; color: var(--text-primary); margin: 2rem 0 1rem 0;">📝 Full Judge\'s Reasoning</div>', unsafe_allow_html=True)
    st.markdown(f'<div style="background: var(--bg-card); border: 1px solid var(--border-subtle); border-radius: 10px; padding: 1.5rem; color: var(--text-secondary); font-family: \'JetBrains Mono\', monospace; font-size: 0.9rem; line-height: 1.7; box-shadow: 0 4px 20px rgba(0,0,0,0.05); margin-bottom: 2rem;">{reasoning}</div>', unsafe_allow_html=True)

    try:
        scores = json.loads(judge_scores_str) if judge_scores_str else {}
        key_moments = scores.get("key_moments", [])
        if key_moments:
            st.markdown('<div style="font-family: \'Inter\', sans-serif; font-weight: 800; font-size: 1.1rem; color: var(--text-primary); margin: 1rem 0;">🔑 Key Moments</div>', unsafe_allow_html=True)
            moments_html = ""
            for i, moment in enumerate(key_moments, 1):
                moments_html += f'<div style="margin-bottom: 0.8rem; display: flex; gap: 0.8rem;"><strong style="color: var(--judge-color);">{i}.</strong> <span>{moment}</span></div>'
            st.markdown(f'<div style="background: var(--bg-card); border: 1px solid var(--border-subtle); border-radius: 10px; padding: 1.5rem; color: var(--text-secondary); font-size: 0.9rem; line-height: 1.6; box-shadow: 0 4px 20px rgba(0,0,0,0.05);">{moments_html}</div>', unsafe_allow_html=True)
    except (json.JSONDecodeError, ValueError):
        pass

    # Auto-scroll to verdict
    components.html(
        """
        <script>
            var element = window.parent.document.getElementById("verdict-section");
            if (element) {
                element.scrollIntoView({behavior: "smooth", block: "start"});
            }
        </script>
        """,
        height=0
    )

# ---------------------------------------------------------------------------
# Main Title
# ---------------------------------------------------------------------------
st.markdown('<div class="main-title">DebateMoi</div>', unsafe_allow_html=True)
st.markdown('<div class="main-subtitle">AI-Powered Debate Arena</div>', unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    # Theme selector
    theme_choice = st.radio(
        "Theme",
        ["Dark", "Light"],
        index=0 if st.session_state.theme == "Dark" else 1,
        horizontal=True,
        key="theme_radio",
    )
    if theme_choice != st.session_state.theme:
        st.session_state.theme = theme_choice
        st.rerun()

    st.markdown("### ⚙️ Debate Configuration")
    st.markdown("---")

    # Session ID
    session_id = st.text_input(
        "Session ID",
        value=st.session_state.session_id,
        help="Your unique debate save code. Copy it to resume this debate later, or paste an old one to reload a previous session.",
    )
    if session_id != st.session_state.session_id:
        st.session_state.session_id = session_id
        st.session_state.recovered = False  # Reset recovery flag for new ID
        st.session_state.debate_events = []
        st.session_state.debate_state = None
        st.session_state.debate_complete = False
    st.session_state.session_id = session_id

    st.markdown("""
    <div style="font-size: 0.72rem; color: #555570; line-height: 1.5; margin: -0.5rem 0 0.8rem 0; padding: 0.5rem 0.6rem; background: rgba(255,255,255,0.02); border-radius: 6px; border-left: 2px solid rgba(0, 212, 255, 0.3);">
        💾 <strong style="color: #8888a0;">Save & Resume</strong> — This ID links to your debate's saved state.
        If you refresh or close the tab, just paste this ID back to reload your full debate transcript.
    </div>
    """, unsafe_allow_html=True)

    # Topic
    topic = st.text_area(
        "Debate Topic",
        placeholder="Enter your debate topic here...\n\ne.g. 'AI will replace most white-collar jobs within 10 years' or 'Space exploration is a waste of taxpayer money'",
        max_chars=200,
        height=150,
        help="Enter the topic to debate (max 200 characters)",
    )

    # Character counter
    if topic:
        remaining = 200 - len(topic)
        color = "#00d4ff" if remaining > 50 else "#ffd700" if remaining > 20 else "#ff006e"
        st.markdown(f'<p style="text-align: right; font-size: 0.75rem; color: {color}; font-family: JetBrains Mono, monospace;">{len(topic)}/200</p>', unsafe_allow_html=True)

    st.markdown("---")

    # Rate limiting info
    rate_limiter = RateLimiter()
    user_ip = get_user_ip()
    remaining_debates = rate_limiter.get_remaining(user_ip)

    st.markdown(f"""
    <div style="text-align: center; padding: 0.5rem; background: rgba(255,255,255,0.03); border-radius: 8px; margin-bottom: 1rem;">
        <div style="font-size: 0.75rem; color: #555570; text-transform: uppercase; letter-spacing: 1px;">Debates Remaining Today</div>
        <div style="font-size: 1.8rem; font-weight: 800; color: {'#00d4ff' if remaining_debates > 1 else '#ffd700' if remaining_debates == 1 else '#ff006e'};">{remaining_debates}/3</div>
    </div>
    """, unsafe_allow_html=True)

    # Start button
    start_clicked = st.button("Start Debate", use_container_width=True, disabled=st.session_state.debate_running)

    st.markdown("---")

    # Token usage display
    if st.session_state.debate_state:
        tokens = st.session_state.debate_state.get("total_tokens", 0)
        pct = min(100, (tokens / 15000) * 100)
        bar_color = "#00d4ff" if pct < 60 else "#ffd700" if pct < 85 else "#ff006e"
        st.markdown(f"""
        <div style="margin-top: 0.5rem;">
            <div style="font-size: 0.75rem; color: #555570; margin-bottom: 4px;">Token Budget</div>
            <div style="background: rgba(255,255,255,0.05); border-radius: 4px; overflow: hidden; height: 6px;">
                <div style="width: {pct}%; height: 100%; background: {bar_color}; border-radius: 4px; transition: width 0.5s;"></div>
            </div>
            <div style="font-size: 0.7rem; color: #555570; margin-top: 2px; text-align: right;">{tokens:,} / 15,000</div>
        </div>
        """, unsafe_allow_html=True)

    # PDF Export button (only after debate is complete)
    if st.session_state.debate_complete and st.session_state.debate_state:
        st.markdown("---")
        pdf_bytes = generate_debate_pdf(st.session_state.debate_state, session_id)
        st.download_button(
            "📄 Download PDF Transcript",
            data=pdf_bytes,
            file_name=f"debatemoi_{session_id}.pdf",
            mime="application/pdf",
            use_container_width=True,
        )


# ---------------------------------------------------------------------------
# Rate Limit Block
# ---------------------------------------------------------------------------
if remaining_debates <= 0 and not st.session_state.debate_running and not st.session_state.debate_complete:
    st.markdown("""
    <div class="rate-limit-banner">
        <h3>⏳ Daily Limit Reached</h3>
        <p>You've used all 3 debates for today. Come back tomorrow for fresh rounds!</p>
        <p style="font-size: 0.8rem; color: #555570; margin-top: 1rem;">Limits reset at midnight UTC</p>
    </div>
    """, unsafe_allow_html=True)
    st.stop()


# ---------------------------------------------------------------------------
# Helper: Render side-by-side rounds
# ---------------------------------------------------------------------------
def render_rounds_side_by_side(events):
    """Display debate events in side-by-side Pro (left) vs Con (right) layout."""
    # Group events by round
    rounds = {}
    for e in events:
        r = e["round"]
        if r not in rounds:
            rounds[r] = {}
        rounds[r][e["type"]] = e["content"]

    for r in sorted(rounds.keys()):
        st.markdown(f'<div style="text-align:center;margin:1.2rem 0 0.6rem;font-family:Inter,sans-serif;font-weight:700;font-size:0.8rem;letter-spacing:2px;color:#555570;text-transform:uppercase;">— Round {r} —</div>', unsafe_allow_html=True)
        col_pro, col_con = st.columns(2)
        with col_pro:
            if "pro" in rounds[r]:
                st.markdown(render_card_html("pro", r, rounds[r]["pro"]), unsafe_allow_html=True)
        with col_con:
            if "con" in rounds[r]:
                st.markdown(render_card_html("con", r, rounds[r]["con"]), unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Auto-recover session from checkpoint (on page load / refresh)
# ---------------------------------------------------------------------------
try_recover_session(session_id)

# ---------------------------------------------------------------------------
# Display Previous Debate (from session state)
# ---------------------------------------------------------------------------
if st.session_state.debate_events and not st.session_state.debate_running:
    if st.session_state.recovered:
        st.markdown(f"""
        <div style="text-align: center; padding: 0.6rem 1rem; background: rgba(0, 212, 255, 0.06); border: 1px solid rgba(0, 212, 255, 0.15); border-radius: 10px; margin-bottom: 1.5rem; font-family: 'JetBrains Mono', monospace; font-size: 0.8rem; color: #8888a0;">
            🔄 Session <strong style="color: #00d4ff;">{session_id}</strong> restored from saved state
        </div>
        """, unsafe_allow_html=True)

    render_rounds_side_by_side(st.session_state.debate_events)

    if st.session_state.debate_complete and st.session_state.debate_state:
        show_verdict(st.session_state.debate_state)


# ---------------------------------------------------------------------------
# Run Debate
# ---------------------------------------------------------------------------

if start_clicked:
    # Validation
    if not topic or not topic.strip():
        st.error("Please enter a debate topic.")
        st.stop()

    if len(topic.strip()) > 200:
        st.error("Topic must be 200 characters or fewer.")
        st.stop()

    if not rate_limiter.check_rate_limit(user_ip):
        st.error("Daily debate limit reached. Come back tomorrow!")
        st.stop()

    # Reset state for new debate
    st.session_state.debate_running = True
    st.session_state.debate_complete = False
    st.session_state.debate_events = []
    st.session_state.debate_state = None

    # Increment rate limit
    rate_limiter.increment(user_ip)

    # Create graph
    graph, conn = create_graph()

    try:
        initial_state = get_initial_state(topic.strip())
        config = {"configurable": {"thread_id": session_id}}

        # Stream the debate
        current_pro = None  # Buffer for side-by-side rendering
        with st.status("🎭 Debate in progress...", expanded=True) as status:
            for event in graph.stream(initial_state, config=config, stream_mode="updates"):
                for node_name, node_output in event.items():
                    if node_name == "pro_agent":
                        args = node_output.get("arguments_for", [])
                        if args:
                            latest = args[-1]
                            current_pro = latest
                            st.session_state.debate_events.append({
                                "type": "pro", "round": latest["round"], "content": latest["content"]
                            })

                    elif node_name == "con_agent":
                        args = node_output.get("arguments_against", [])
                        if args:
                            latest = args[-1]
                            st.session_state.debate_events.append({
                                "type": "con", "round": latest["round"], "content": latest["content"]
                            })
                            # Render side-by-side now that we have both
                            rnd = latest["round"]
                            st.markdown(f'<div style="text-align:center;margin:1.2rem 0 0.6rem;font-family:Inter,sans-serif;font-weight:700;font-size:0.8rem;letter-spacing:2px;color:#555570;text-transform:uppercase;">— Round {rnd} —</div>', unsafe_allow_html=True)
                            c1, c2 = st.columns(2)
                            with c1:
                                if current_pro:
                                    st.markdown(render_card_html("pro", current_pro["round"], current_pro["content"]), unsafe_allow_html=True)
                            with c2:
                                st.markdown(render_card_html("con", rnd, latest["content"]), unsafe_allow_html=True)
                            current_pro = None

                    elif node_name == "judge":
                        # Save the full state after judge runs
                        st.session_state.debate_state = {
                            **initial_state,
                            **node_output,
                            "arguments_for": [e for e in st.session_state.debate_events if e["type"] == "pro"],
                            "arguments_against": [e for e in st.session_state.debate_events if e["type"] == "con"],
                        }

                    elif node_name == "budget_guard":
                        if node_output.get("budget_exceeded"):
                            st.warning("⚠️ Token budget exceeded — proceeding to judge's verdict early.")

                    # Update token count in state
                    if "total_tokens" in node_output:
                        if st.session_state.debate_state is None:
                            st.session_state.debate_state = {**initial_state}
                        st.session_state.debate_state["total_tokens"] = node_output["total_tokens"]

            status.update(label="⚖️ The Judge is deliberating...", state="running")

        # Get final state from the graph
        final_state = graph.get_state(config)
        if final_state and final_state.values:
            st.session_state.debate_state = dict(final_state.values)

        # Mark complete
        st.session_state.debate_complete = True
        st.session_state.debate_running = False

        # Show verdict
        if st.session_state.debate_state:
            show_verdict(st.session_state.debate_state)
            st.balloons()

    except Exception as e:
        st.error(f"An error occurred during the debate: {str(e)}")
        st.session_state.debate_running = False
    finally:
        conn.close()
