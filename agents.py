"""
DebateMoi — Agent Definitions & State Schema
=============================================
Defines the DebateState, Pro/Con/Judge node functions, budget guard, and router.

Models:
  - Pro & Con agents: Gemini 2.5 Flash (cost-efficient, strong reasoning)
  - Judge: GPT-4o-mini (excellent structured JSON output)

You can swap models by changing the model name below. For stronger reasoning,
try "claude-sonnet-4-6" (Anthropic) or "gpt-4o" (OpenAI).
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
DEBATER_MODEL = "gemini-2.5-flash"
JUDGE_MODEL = "gpt-4o-mini"
DEBATER_MAX_TOKENS = 512
JUDGE_MAX_TOKENS = 1000
TOTAL_TOKEN_BUDGET = 5000


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
    """Returns the debater LLM instance (Gemini 2.5 Flash by default)."""
    from langchain_google_genai import ChatGoogleGenerativeAI
    return ChatGoogleGenerativeAI(
        model=DEBATER_MODEL,
        max_output_tokens=DEBATER_MAX_TOKENS,
        temperature=0.8,
        google_api_key=os.getenv("GOOGLE_API_KEY"),
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
PRO_SYSTEM_PROMPT = """You are an Oxford-trained rhetorician and world-class debater. 
You are arguing IN FAVOR of the given topic.

Your approach:
- Analyze the opponent's premise for logical inconsistencies (strawman, ad hominem, false equivalence)
- Use empirical data references and hypothetical evidence to support your claims
- Structure every argument as: **Claim → Evidence → Impact**
- Use the Socratic method when appropriate
- Remain strictly professional and intellectually rigorous

If this is not the first round, directly address and counter the opponent's latest argument before presenting your new points.

CRITICAL: Keep your argument concise and under 400 words. Quality over quantity."""

CON_SYSTEM_PROMPT = """You are a master of contrarian philosophy and critical analysis.
You are arguing AGAINST the given topic.

Your approach:
- Challenge the underlying assumptions of the Pro agent's position
- Identify logical fallacies in their last point (strawman, ad hominem, slippery slope, false cause)
- Use high-level vocabulary and concise, piercing rebuttals
- Present your own counter-stance with INDEPENDENT evidence — don't just negate, BUILD your own case
- Pivot to core counter-arguments that undermine the Pro position's foundation

If this is not the first round, directly dismantle the opponent's latest argument before presenting your counter-stance.

CRITICAL: Keep your argument concise and under 400 words. Quality over quantity."""

JUDGE_SYSTEM_PROMPT = """You are an impartial, world-class debate arbitrator with decades of experience judging international competitions.

Provide an in-depth, highly informative evaluation of the debate. You must be FAIR and UNBIASED — do not favor longer arguments or more emotional appeals.

Score each debater on a 1–10 scale across FIVE categories:
1. **Logical Consistency** — Are arguments free of contradictions and fallacies?
2. **Evidence Strength** — Are claims backed by data, examples, or credible references?
3. **Rhetorical Skill** — How persuasive and eloquent is the delivery?
4. **Rebuttal Quality** — How effectively did each side counter the opponent?
5. **Argument Originality** — Were fresh, unexpected points introduced?

You MUST output ONLY valid JSON (no markdown, no code fences) with this exact structure:
{
    "winner": "Pro" or "Con",
    "reasoning": "A detailed 3-4 sentence explanation of why the winner prevailed",
    "pro_scores": {"logic": X, "evidence": X, "rhetoric": X, "rebuttal": X, "originality": X},
    "con_scores": {"logic": X, "evidence": X, "rhetoric": X, "rebuttal": X, "originality": X},
    "pro_total": X,
    "con_total": X,
    "key_moments": ["moment 1 description", "moment 2 description"],
    "deciding_factor": "One sentence on what tipped the scales"
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
    tokens_used = response.usage_metadata.get("total_tokens", len(content.split()) * 2) if hasattr(response, 'usage_metadata') and response.usage_metadata else len(content.split()) * 2

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
    tokens_used = response.usage_metadata.get("total_tokens", len(content.split()) * 2) if hasattr(response, 'usage_metadata') and response.usage_metadata else len(content.split()) * 2

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

    if budget_exceeded or current_round >= max_rounds:
        return "judge"
    return "continue"
