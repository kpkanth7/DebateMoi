"""
DebateMoi — LangGraph Workflow Definition
==========================================
Builds the StateGraph with cyclic debate loop:
  START → pro_agent → con_agent → increment_round → budget_guard → router
                                                                    ↓
                                                          continue → pro_agent
                                                          judge → judge_agent → END

Compiled with SqliteSaver for persistent session recovery.
"""

import sqlite3
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.sqlite import SqliteSaver

from agents import (
    DebateState,
    pro_agent_node,
    con_agent_node,
    increment_round_node,
    budget_guard_node,
    judge_agent_node,
    should_continue,
)


def create_graph(db_path: str = "database.db"):
    """
    Creates and compiles the debate graph with SQLite checkpointing.
    
    Args:
        db_path: Path to the SQLite database for state persistence.
    
    Returns:
        Tuple of (compiled_graph, sqlite_connection).
        Caller is responsible for closing the connection when done.
    """
    # Build the graph
    builder = StateGraph(DebateState)

    # Add nodes
    builder.add_node("pro_agent", pro_agent_node)
    builder.add_node("con_agent", con_agent_node)
    builder.add_node("increment_round", increment_round_node)
    builder.add_node("budget_guard", budget_guard_node)
    builder.add_node("judge", judge_agent_node)

    # Add edges: linear flow through the debate round
    builder.add_edge(START, "pro_agent")
    builder.add_edge("pro_agent", "con_agent")
    builder.add_edge("con_agent", "increment_round")
    builder.add_edge("increment_round", "budget_guard")

    # Conditional routing: continue debating or go to judge
    builder.add_conditional_edges(
        "budget_guard",
        should_continue,
        {
            "continue": "pro_agent",
            "judge": "judge",
        },
    )

    builder.add_edge("judge", END)

    # Set up SQLite persistence
    conn = sqlite3.connect(db_path, check_same_thread=False)
    memory = SqliteSaver(conn)

    # Compile with checkpointer
    graph = builder.compile(checkpointer=memory)

    return graph, conn


def get_initial_state(topic: str, max_rounds: int = 3) -> dict:
    """
    Creates the initial state for a new debate.
    
    Args:
        topic: The debate topic from the user.
        max_rounds: Number of debate rounds (fixed at 3).
    
    Returns:
        Initial DebateState dictionary.
    """
    return {
        "topic": topic,
        "current_round": 1,
        "max_rounds": max_rounds,
        "arguments_for": [],
        "arguments_against": [],
        "verdict": "",
        "winner": "",
        "reasoning": "",
        "judge_scores": "",
        "total_tokens": 0,
        "budget_exceeded": False,
        "messages": [],
    }
