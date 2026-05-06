# DebateMoi 🎭

🚀 **Live Demo:** [debatemoi.streamlit.app](https://debatemoi.streamlit.app)

I built **DebateMoi** because I wanted to see what happens when you pit two AI agents against each other in a structured, high-stakes debate — and have a third AI judge declare the winner with detailed scoring.

It's a multi-agent system where a **Pro agent** and **Con agent** go head-to-head for 3 rounds on any topic you throw at them. After the final round, an impartial **Judge agent** evaluates the entire transcript across 5 categories and delivers a dramatic verdict with detailed scores.

The whole thing runs on a cinematic dark-mode UI that streams the debate in real-time. It's not just a chatbot — it's an arena.

## What It Does

- **3-Round Structured Debates**: Two AI agents argue for and against any topic you provide
- **Impartial AI Judge**: Scores both sides on Logic, Evidence, Rhetoric, Rebuttal Quality, and Originality (1–10 each)
- **Persistent Sessions**: Refresh the page? Your debate state is saved. Resume anytime with your Session ID
- **Real-Time Streaming**: Watch arguments appear live as the agents think
- **PDF Export**: Download a beautifully styled, color-coded PDF transcript of the full debate
- **Cost-Protected**: IP-based rate limiting (3 debates/day), token budget guards, and input sanitization

## Tech Stack

| Component | Technology | Why |
|---|---|---|
| **Orchestration** | LangGraph + LangChain | Best-in-class for stateful, cyclic multi-agent flows |
| **Pro/Con Agents** | DeepSeek Chat | Ultra cost-efficient, fast, strong reasoning |
| **Judge Agent** | GPT-4o-mini | Excellent at structured JSON output and impartial evaluation |
| **UI** | Streamlit | Rapid development of interactive LLM dashboards |
| **Persistence** | SQLite (SqliteSaver) | Reliable local checkpoints — survives restarts |
| **PDF Export** | fpdf2 | Lightweight, colorful PDF generation with cover page |
| **Rate Limiting** | Custom SQLite-backed | IP-based, 3 debates/day, persistent across restarts |

## How to Run Locally

### Prerequisites
- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip
- API keys for DeepSeek and OpenAI

### Setup

```bash
git clone https://github.com/kpkanth7/DebateMoi.git
cd DebateMoi

# Install dependencies
uv sync
# or: pip install -r requirements.txt

# Set up API keys
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# Edit .streamlit/secrets.toml with your actual keys
```

### Run

```bash
uv run streamlit run app.py
# or: streamlit run app.py
```

Open [http://localhost:8501](http://localhost:8501) and start debating.

## Deploy to Streamlit Community Cloud (Free)

1. Fork this repo to your GitHub account
2. Go to [share.streamlit.io](https://share.streamlit.io) and sign in with GitHub
3. Click **New app** → select your fork → set main file to `app.py`
4. Under **Advanced settings → Secrets**, add:
   ```toml
   DEEPSEEK_API_KEY = "sk-..."
   OPENAI_API_KEY = "sk-..."
   ```
5. Click **Deploy** — your app will be live at `your-app-name.streamlit.app`

> **Note**: Streamlit Community Cloud has a free tier with unlimited public apps. The SQLite databases are ephemeral (reset on restart) — this is fine since rate limiting resets are acceptable for a demo.

## Architecture

```
START → Pro Agent → Con Agent → Increment Round → Budget Guard → Router
                                                                   ↓
                                                      continue → Pro Agent (loop)
                                                      judge → Judge Agent → END
```

- **Pro Agent**: Argues IN FAVOR — Claim → Evidence → Impact structure, hard 350-word cap
- **Con Agent**: Argues AGAINST — dismantles opponent's logic, builds independent counter-stance, hard 350-word cap
- **Budget Guard**: Monitors total token usage (8,000 cap) — forces early verdict if exceeded
- **Judge Agent**: Evaluates across 5 categories, outputs structured JSON with round-by-round analysis

## Cost Control

- **Cheap models**: DeepSeek Chat for debaters (fraction of GPT-4o cost)
- **Hard token caps**: 600 tokens/turn API limit for debaters, 1500 for judge
- **Session budget**: 8,000 total tokens per debate
- **Rate limiting**: 3 debates/day per IP address
- **Input sanitization**: Topics capped at 200 characters, HTML-escaped before rendering

## Project Structure

```
├── app.py                        # Streamlit UI — entry point
├── graph.py                      # LangGraph workflow definition
├── agents.py                     # LLM node functions & prompts
├── pdf_export.py                 # PDF transcript generation (cover + rounds + verdict)
├── rate_limiter.py               # IP-based daily rate limiter
├── .streamlit/
│   ├── config.toml               # Streamlit server config
│   └── secrets.toml.example      # API key template
├── pyproject.toml                # uv project config
└── requirements.txt              # pip dependencies
```

## License

MIT
