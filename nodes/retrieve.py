"""
Node B: retrieve_venues

Calls the Places API using only the hard filters from merged_constraints
(location, radius, price range, category). Soft signals like rating and
vibe are NOT used here — they get applied later in rank_and_explain.
"""

from state import DateState
from utils.places_api import search_places


def retrieve_venues(state: DateState) -> dict:
    c = state["merged_constraints"]

    results = search_places(
        location=c["location"],
        radius_meters=c["radius_km"] * 1000,
        place_type=c["category"],
        min_price=c["price_level_min"],
        max_price=c["price_level_max"],
        open_now=c.get("time_sensitive", False),
    )

    return {"candidate_venues": results}


def check_results(state: DateState) -> str:
    """
    Conditional edge function — decides what happens after retrieve_venues.
    Returns a string naming the next node.
    """
    if len(state["candidate_venues"]) > 0:
        return "rank_and_explain"
    if state["retry_attempts"] < 2:
        return "loosen_constraints"
    return "rank_and_explain"  # give up gracefully — rank_and_explain must handle an empty list


def loosen_constraints(state: DateState) -> dict:
    """
    Loosens exactly one hard filter per retry, weakest constraint first,
    so we can tell the user specifically what we changed if we ask them later.
    """
    c = dict(state["merged_constraints"])  # copy, don't mutate the original dict in place
    attempts = state["retry_attempts"]

    if attempts == 0:
        c["radius_km"] = c.get("radius_km", 2) + 3
    elif attempts == 1:
        c["price_level_max"] = min(c.get("price_level_max", 2) + 1, 4)

    return {"merged_constraints": c, "retry_attempts": attempts + 1}
