"""
graph.py — wires our four separately-tested nodes into one real LangGraph agent.

The shape, as we designed it:

    START -> reconcile -+-> retrieve_venues -> [check_results conditional edge]
                         |         ^                    |
                         |         |                    v
                         |  loosen_constraints    rank_and_explain -> END
                         |
                         +-> outfit_suggestion -> END

Correction from our original design: outfit_suggestion only needs
merged_constraints (from reconcile) and weather — it never actually reads
candidate_venues or chosen_venue. Making it wait on retrieve_venues would be
an unnecessary dependency, so it branches directly off reconcile instead.
This means outfit_suggestion can start running WHILE retrieve_venues (and its
retry loop) is still working — genuinely parallel from the earliest possible point.

retrieve_venues loops back through loosen_constraints on zero results,
capped by retry_attempts (see check_results in nodes/retrieve.py).
"""

from langgraph.graph import StateGraph, START, END

from state import DateState
from nodes.reconcile import reconcile_preferences
from nodes.retrieve import retrieve_venues, check_results, loosen_constraints
from nodes.rank import rank_and_explain
from nodes.outfit import outfit_suggestion


def build_graph():
    graph = StateGraph(DateState)

    graph.add_node("reconcile", reconcile_preferences)
    graph.add_node("retrieve_venues", retrieve_venues)
    graph.add_node("loosen_constraints", loosen_constraints)
    graph.add_node("rank_and_explain", rank_and_explain)
    graph.add_node("outfit_suggestion", outfit_suggestion)

    graph.add_edge(START, "reconcile")

    # fan out directly from reconcile: retrieve_venues and outfit_suggestion
    # don't depend on each other, so both branches start as soon as reconcile finishes
    graph.add_edge("reconcile", "retrieve_venues")
    graph.add_edge("reconcile", "outfit_suggestion")

    # conditional edge: after retrieve_venues, check_results decides whether
    # to loop back (loosen_constraints) or move forward (rank_and_explain)
    graph.add_conditional_edges(
        "retrieve_venues",
        check_results,
        {
            "loosen_constraints": "loosen_constraints",
            "rank_and_explain": "rank_and_explain",
        },
    )
    # after loosening constraints, go back and retry the venue search
    graph.add_edge("loosen_constraints", "retrieve_venues")

    # fan in: END waits for both branches to finish
    graph.add_edge("rank_and_explain", END)
    graph.add_edge("outfit_suggestion", END)

    return graph.compile()
