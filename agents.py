"""
DebateMoi — Agent Definitions & State Schema
=============================================
Defines the DebateState, Pro/Con/Judge node functions, budget guard, and router.

Models:
  - Pro & Con agents: DeepSeek V4 (cost-efficient, strong reasoning)
  - Judge: GPT-4o-mini (excellent structured JSON output)

You can swap models by changing the model name below. For stronger reasoning,
try "claude-3-7-sonnet" (Anthropic) or "gpt-4o" (OpenAI).
"""

import json
import os
from typing import Annotated, TypedDict, List, Optional

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph.message import add_messages

load_dotenv()

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
DEBATER_MODEL = "deepseek-chat"
JUDGE_MODEL = "gpt-4o-mini"
DEBATER_MAX_TOKENS = 600    # Hard API cap per debater turn (~400 words)
JUDGE_MAX_TOKENS = 1500     # Enough for detailed JSON verdict
TOTAL_TOKEN_BUDGET = 8000   # 3 rounds safely within budget


# ---------------------------------------------------------------------------
# State Schema
# ---------------------------------------------------------------------------
class DebateState(TypedDict):
    """Single source of truth passed between all nodes in the debate graph."""
    topic: str
    current_round: int
    max_rounds: int
    arguments_for: List[dict]       # [{round, content, tokens}]
    arguments_against: List[dict]   # [{round, content, tokens}]
    verdict: str                    # Judge's full JSON verdict
    winner: str                     # "Pro" or "Con"
    reasoning: str                  # Judge's reasoning
    judge_scores: str               # JSON string with detailed scores
    total_tokens: int               # Running token counter
    budget_exceeded: bool           # Flag if budget guard triggered
    messages: Annotated[list, add_messages]  # LangGraph message trace


# ---------------------------------------------------------------------------
# LLM Factory
# ---------------------------------------------------------------------------
def _get_debater_llm():
    """Returns the debater LLM instance (DeepSeek by default)."""
    from langchain_openai import ChatOpenAI
    return ChatOpenAI(
        model=DEBATER_MODEL,
        max_tokens=DEBATER_MAX_TOKENS,
        temperature=0.8,
        api_key=os.getenv("DEEPSEEK_API_KEY"),
        base_url="https://api.deepseek.com",
    )


def _get_judge_llm():
    """Returns the judge LLM instance (GPT-4o-mini by default)."""
    from langchain_openai import ChatOpenAI
    return ChatOpenAI(
        model=JUDGE_MODEL,
        max_tokens=JUDGE_MAX_TOKENS,
        temperature=0.3,
        api_key=os.getenv("OPENAI_API_KEY"),
    )


# ---------------------------------------------------------------------------
# Prompt Personas
# ---------------------------------------------------------------------------
PRO_SYSTEM_PROMPT = """You argue IN FAVOR of the topic. You are a razor-sharp debater — evidence-driven, direct, lethal.

⚠️ HARD LIMIT: 350 words MAXIMUM. Stop writing when you hit 350 words. No exceptions.
DO NOT greet or introduce yourself. Start with your first argument immediately.

FORMAT (use exactly):

**1. [Argument Title]**
Claim: One declarative sentence.
Evidence: Cite a named study, statistic, or historical precedent.
Impact: Why this matters in practice.

**2. [Argument Title]**
Claim / Evidence / Impact (same structure)

**3. [Argument Title]**
Claim / Evidence / Impact (same structure)

**Rebuttal** (Rounds 2–3 only): Name the opponent's weakest claim. Demolish it with one counter-fact or exposed logical flaw. Then pivot to a new offensive point they haven't addressed.

**Bottom Line**: One sentence. Make it land.

RULES:
- Real data only. Named studies, named people, specific numbers.
- No filler. Every sentence advances your position.
- Use steel-manning, reductio ad absurdum, or false-dichotomy exposure where lethal."""

CON_SYSTEM_PROMPT = """You argue AGAINST the topic. You are a precision instrument of logic — calm, devastating, surgical.

⚠️ HARD LIMIT: 350 words MAXIMUM. Stop writing when you hit 350 words. No exceptions.
DO NOT greet or introduce yourself. Start with substance immediately.

FORMAT (use exactly):

**Logical Flaw**: Name the specific fallacy in the Pro's opening. Explain in 2 sentences why it collapses.

**1. [Counter-Argument Title]**
Claim: One declarative sentence — YOUR independent case.
Evidence: Named data, counterexample, or philosophical framework.
Consequence: What breaks if the Pro's position is adopted.

**2. [Counter-Argument Title]**
Claim / Evidence / Consequence (same structure)

**3. [Counter-Argument Title]**
Claim / Evidence / Consequence (same structure)

**Knockout**: Take the Pro's single strongest point. Demolish it with a specific counterexample or suppressed premise. Introduce one angle they haven't touched.

**Bottom Line**: One sentence. Make it sting.

RULES:
- 60%+ of your response must be YOUR arguments, not just attacks.
- Expose hidden costs, unintended consequences, implementation failures.
- No filler. Every sentence does work."""

JUDGE_SYSTEM_PROMPT = """You are a ruthlessly impartial debate arbitrator — world-class, experienced, impossible to manipulate.

EVALUATION PRINCIPLES:
- Score substance, not style. A concise, precise argument beats a long flowery one.
- Penalize logical fallacies, unsupported assertions, and circular reasoning.
- Reward specific data (named studies, statistics, historical events) over vague claims.
- Track how arguments evolve round-to-round. Does each side build, adapt, and counter?
- A debater who successfully steel-mans the opponent then dismantles them scores higher than one who attacks a strawman.
- Tiebreaker: whichever side introduced more original, non-obvious arguments that the other side could not adequately answer.

SCORING (1–10 per category, be ruthless — 7+ must be earned):
1. Logical Consistency — free of fallacies, contradictions, and non-sequiturs
2. Evidence Strength — named sources, statistics, or verifiable precedents (not vague appeals)
3. Rhetorical Skill — persuasive structure, clarity, precision of language
4. Rebuttal Quality — did they directly engage the opponent's best points or dodge them?
5. Argument Originality — fresh angles, suppressed premises exposed, unexpected evidence

REASONING REQUIREMENT: Write 6–8 sentences. Reference specific rounds and specific claims made by each side. Explain exactly what tipped the scales — do not write generic praise.

Output ONLY valid JSON. No markdown, no code fences, no preamble:
{
    "winner": "Pro" or "Con",
    "reasoning": "6-8 sentences referencing specific rounds and specific arguments",
    "pro_scores": {"logic": X, "evidence": X, "rhetoric": X, "rebuttal": X, "originality": X},
    "con_scores": {"logic": X, "evidence": X, "rhetoric": X, "rebuttal": X, "originality": X},
    "pro_total": X,
    "con_total": X,
    "key_moments": ["Round N: specific pivotal exchange description", "Round N: ..."],
    "deciding_factor": "One precise sentence naming the exact argument or moment that decided the outcome"
}"""


# ---------------------------------------------------------------------------
# Node Functions
# ---------------------------------------------------------------------------
def pro_agent_node(state: DebateState) -> dict:
    """Pro agent generates an argument IN FAVOR of the topic."""
    llm = _get_debater_llm()
    current_round = state.get("current_round", 1)
    topic = state["topic"]

    # Build context from previous arguments
    context = f"DEBATE TOPIC: {topic}\n\n"
    context += f"CURRENT ROUND: {current_round} of {state.get('max_rounds', 3)}\n\n"

    # Include previous exchange history
    args_for = state.get("arguments_for", [])
    args_against = state.get("arguments_against", [])

    if args_for or args_against:
        context += "PREVIOUS EXCHANGES:\n"
        max_prev = max(len(args_for), len(args_against))
        for i in range(max_prev):
            if i < len(args_for):
                context += f"\n--- PRO (Round {args_for[i]['round']}) ---\n{args_for[i]['content']}\n"
            if i < len(args_against):
                context += f"\n--- CON (Round {args_against[i]['round']}) ---\n{args_against[i]['content']}\n"

    if args_against:
        context += f"\nYour opponent's LATEST argument to counter:\n{args_against[-1]['content']}\n"

    context += f"\nNow present your Round {current_round} argument IN FAVOR of the topic."

    messages = [
        SystemMessage(content=PRO_SYSTEM_PROMPT),
        HumanMessage(content=context),
    ]

    response = llm.invoke(messages)
    content = response.content
    usage = getattr(response, "usage_metadata", {}) or {}
    meta_usage = getattr(response, "response_metadata", {}).get("token_usage", {})
    tokens_used = usage.get("output_tokens") or meta_usage.get("completion_tokens") or (len(content.split()) * 2)

    new_argument = {
        "round": current_round,
        "content": content,
        "tokens": tokens_used,
    }

    return {
        "arguments_for": state.get("arguments_for", []) + [new_argument],
        "total_tokens": state.get("total_tokens", 0) + tokens_used,
        "messages": [HumanMessage(content=f"[PRO Round {current_round}] {content}")],
    }


def con_agent_node(state: DebateState) -> dict:
    """Con agent generates an argument AGAINST the topic."""
    llm = _get_debater_llm()
    current_round = state.get("current_round", 1)
    topic = state["topic"]

    # Build context from previous arguments
    context = f"DEBATE TOPIC: {topic}\n\n"
    context += f"CURRENT ROUND: {current_round} of {state.get('max_rounds', 3)}\n\n"

    args_for = state.get("arguments_for", [])
    args_against = state.get("arguments_against", [])

    if args_for or args_against:
        context += "PREVIOUS EXCHANGES:\n"
        max_prev = max(len(args_for), len(args_against))
        for i in range(max_prev):
            if i < len(args_for):
                context += f"\n--- PRO (Round {args_for[i]['round']}) ---\n{args_for[i]['content']}\n"
            if i < len(args_against):
                context += f"\n--- CON (Round {args_against[i]['round']}) ---\n{args_against[i]['content']}\n"

    # Always include the Pro's latest argument to counter
    if args_for:
        context += f"\nYour opponent's LATEST argument to counter:\n{args_for[-1]['content']}\n"

    context += f"\nNow present your Round {current_round} argument AGAINST the topic. First dismantle the Pro's latest point, then build your own counter-stance."

    messages = [
        SystemMessage(content=CON_SYSTEM_PROMPT),
        HumanMessage(content=context),
    ]

    response = llm.invoke(messages)
    content = response.content
    usage = getattr(response, "usage_metadata", {}) or {}
    meta_usage = getattr(response, "response_metadata", {}).get("token_usage", {})
    tokens_used = usage.get("output_tokens") or meta_usage.get("completion_tokens") or (len(content.split()) * 2)

    new_argument = {
        "round": current_round,
        "content": content,
        "tokens": tokens_used,
    }

    return {
        "arguments_against": state.get("arguments_against", []) + [new_argument],
        "total_tokens": state.get("total_tokens", 0) + tokens_used,
        "messages": [HumanMessage(content=f"[CON Round {current_round}] {content}")],
    }


def increment_round_node(state: DebateState) -> dict:
    """Increments the current round counter."""
    return {
        "current_round": state.get("current_round", 1) + 1,
    }


def budget_guard_node(state: DebateState) -> dict:
    """Checks if total token usage has exceeded the budget cap."""
    total = state.get("total_tokens", 0)
    if total >= TOTAL_TOKEN_BUDGET:
        return {
            "budget_exceeded": True,
            "current_round": state.get("max_rounds", 3),  # Force judge
            "messages": [HumanMessage(content=f"[SYSTEM] Budget guard triggered at {total} tokens. Proceeding to verdict.")],
        }
    return {"budget_exceeded": False}


def judge_agent_node(state: DebateState) -> dict:
    """Judge evaluates the full debate and renders a detailed verdict."""
    llm = _get_judge_llm()
    topic = state["topic"]

    # Build the full transcript for the judge
    transcript = f"DEBATE TOPIC: {topic}\n\n"
    args_for = state.get("arguments_for", [])
    args_against = state.get("arguments_against", [])
    rounds_played = max(len(args_for), len(args_against))

    for i in range(rounds_played):
        transcript += f"═══════════════ ROUND {i + 1} ═══════════════\n\n"
        if i < len(args_for):
            transcript += f"⚔️ PRO ARGUMENT:\n{args_for[i]['content']}\n\n"
        if i < len(args_against):
            transcript += f"🛡️ CON ARGUMENT:\n{args_against[i]['content']}\n\n"

    transcript += "═══════════════════════════════════════\n"
    transcript += f"\nTotal rounds completed: {rounds_played}"
    if state.get("budget_exceeded"):
        transcript += "\n⚠️ NOTE: This debate was ended early due to token budget limits."

    messages = [
        SystemMessage(content=JUDGE_SYSTEM_PROMPT),
        HumanMessage(content=f"Please evaluate the following debate and render your verdict:\n\n{transcript}"),
    ]

    response = llm.invoke(messages)
    verdict_text = response.content.strip()

    # Parse the JSON verdict
    try:
        # Clean up potential markdown code fences
        clean = verdict_text
        if clean.startswith("```"):
            clean = clean.split("\n", 1)[1] if "\n" in clean else clean[3:]
        if clean.endswith("```"):
            clean = clean[:-3]
        clean = clean.strip()

        verdict_data = json.loads(clean)
        winner = verdict_data.get("winner", "Unknown")
        reasoning = verdict_data.get("reasoning", "No reasoning provided.")
        judge_scores = json.dumps(verdict_data)
    except (json.JSONDecodeError, ValueError):
        winner = "Unknown"
        reasoning = verdict_text
        judge_scores = json.dumps({"raw_response": verdict_text, "parse_error": True})

    return {
        "verdict": verdict_text,
        "winner": winner,
        "reasoning": reasoning,
        "judge_scores": judge_scores,
        "messages": [HumanMessage(content=f"[JUDGE] Winner: {winner}. {reasoning}")],
    }


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------
def should_continue(state: DebateState) -> str:
    """Routes to 'continue' (next round) or 'judge' (final verdict)."""
    current_round = state.get("current_round", 1)
    max_rounds = state.get("max_rounds", 3)
    budget_exceeded = state.get("budget_exceeded", False)

    if budget_exceeded or current_round > max_rounds:
        return "judge"
    return "continue"
