# DebateMoi 🎭

🚀 **Live Demo:** [DebateMoi.onrender.com](https://Debatemoi.onrender.com)

I built **DebateMoi** because I wanted to see what happens when you pit two AI agents against each other in a structured, high-stakes debate — and have a third AI judge declare the winner with detailed scoring.

It's a multi-agent system where a **Pro agent** and **Con agent** go head-to-head for 3 rounds on any topic you throw at them. Each agent has a distinct persona — one's an Oxford-trained rhetorician, the other's a master of contrarian philosophy. After the final round, an impartial **Judge agent** evaluates the entire transcript across 5 categories and delivers a dramatic verdict.

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
| **Pro/Con Agents** | DeepSeek V4 | Ultra cost-efficient, fast, strong reasoning |
| **Judge Agent** | GPT-4o-mini | Excellent at structured JSON output and impartial evaluation |
| **UI** | Streamlit | Rapid development of interactive LLM dashboards |
| **Persistence** | SQLite (SqliteSaver) | Reliable local checkpoints — survives restarts |
| **PDF Export** | fpdf2 | Lightweight, colorful PDF generation |
| **Rate Limiting** | Custom SQLite-backed | IP-based, 3 debates/day, persistent across restarts |

> **Note on Models**: I've used DeepSeek V4 to keep costs minimal. If you want even stronger reasoning, you can easily swap in Anthropic's Claude, OpenAI's GPT-4o, or any other model — just update the model name in `agents.py`. The architecture is completely provider-agnostic.

## How to Run

### Prerequisites
- Python 3.10+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip
- API keys for DeepSeek and OpenAI

### Setup

```bash
# Clone the repo
git clone https://github.com/kpkanth7/DebateMoi.git
cd DebateMoi

# Install dependencies with uv
uv sync

# Or with pip
pip install -r requirements.txt

# Set up your API keys
cp .env .env.backup
# Edit .env with your actual keys
```

### Run

```bash
# With uv
uv run streamlit run app.py

# Or directly
streamlit run app.py
```

Then open [http://localhost:8501](http://localhost:8501) and start debating!

## Architecture

```
START → Pro Agent → Con Agent → Increment Round → Budget Guard → Router
                                                                   ↓
                                                      continue → Pro Agent (loop)
                                                      judge → Judge Agent → END
```

- **Pro Agent**: Argues IN FAVOR — uses Claim → Evidence → Impact structure
- **Con Agent**: Argues AGAINST — dismantles opponent's logic, builds independent counter-stance
- **Budget Guard**: Monitors total token usage (8,000 cap) — forces early verdict if exceeded
- **Judge Agent**: Evaluates across 5 categories, outputs structured JSON with scores and key moments

## Cost Control

This project is built to be deployment-friendly without burning through your wallet:

- **Cheap models by default**: DeepSeek V4 for debaters
- **Token caps**: 1024 tokens/turn for debaters, 1024 for the judge
- **Session budget**: 8,000 total tokens per debate
- **Rate limiting**: 3 debates/day per IP address
- **Input sanitization**: Topics capped at 200 characters

## Project Structure

```
├── app.py             # Streamlit UI — entry point
├── graph.py           # LangGraph workflow definition
├── agents.py          # LLM node functions & prompts
├── pdf_export.py      # PDF transcript generation
├── rate_limiter.py    # IP-based daily rate limiter
├── .env               # API keys (not tracked)
├── .gitignore         # Git ignore rules
├── pyproject.toml     # uv project config
└── requirements.txt   # pip dependencies
```

## License

MIT
