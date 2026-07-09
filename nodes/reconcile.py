"""
Node A: reconcile_preferences

Takes both partners' answers and merges them into one set of constraints
the rest of the graph can act on. This is a node function — it takes the
current state, does its one job, and returns a dict of only the fields it changed.
"""

from state import DateState


# Rough city-center coordinates as a placeholder.
# In the real version this would come from the user's location or a geocoding call.
DEFAULT_LOCATION = {"lat": 28.6139, "lng": 77.2090}  # Delhi, since that's your location


def reconcile_preferences(state: DateState) -> dict:
    a = state["partner_a_answers"]
    b = state["partner_b_answers"]

    # Use a real location if the API layer provided one (from the browser's
    # geolocation), otherwise fall back to our Delhi placeholder — this keeps
    # main.py and our existing tests working unchanged, since they never set
    # user_location in their initial state.
    location = state.get("user_location") or DEFAULT_LOCATION

    # Budget: take the lower of the two so neither partner is priced out.
    # Convert rupee amount into a rough Places API price_level (0-4 scale).
    lower_budget = min(a["budget"], b["budget"])
    price_level_max = _budget_to_price_level(lower_budget)

    # Vibe: if they match, use it directly. If they don't, we don't guess —
    # we mark it "flexible" and let rank_and_explain lean on ratings/reviews instead.
    vibe = a["vibe"] if a["vibe"] == b["vibe"] else "flexible"

    # Cuisine: if they match, use it. If they don't, don't silently pick one partner's
    # answer — mark it "mixed" so rank_and_explain knows to search more broadly
    # (e.g. category="restaurant" is broad enough to include both italian and cafe-style venues).
    # A v2 improvement would use an LLM to find a cuisine both partners would enjoy.
    cuisines_match = a["cuisine"] == b["cuisine"]
    cuisine = a["cuisine"] if cuisines_match else "mixed"

    # Indoor/outdoor: if either partner wants outdoor and the other is flexible-ish,
    # lean outdoor; if they directly conflict, default to indoor (safer fallback).
    indoor_outdoor = a["indoor_outdoor"] if a["indoor_outdoor"] == b["indoor_outdoor"] else "indoor"

    merged = {
        "location": location,
        "radius_km": 2.0,
        "price_level_min": 0,
        "price_level_max": price_level_max,
        "category": _cuisine_to_category(cuisine),
        "vibe": vibe,
        "indoor_outdoor": indoor_outdoor,
        "time_sensitive": False,
        "occasion": a["occasion"],
    }

    return {"merged_constraints": merged, "retry_attempts": 0}


def _budget_to_price_level(budget_rupees: int) -> int:
    """Rough mapping — tune these thresholds once you see real Places API data."""
    if budget_rupees < 500:
        return 1
    elif budget_rupees < 1000:
        return 2
    elif budget_rupees < 2000:
        return 3
    return 4


def _cuisine_to_category(cuisine: str) -> str:
    """Maps our quiz's cuisine answer to a Places API-friendly place type.
    "mixed" (from a partner cuisine conflict) and any unrecognized value both
    fall back to "restaurant" since it's the broadest category to search."""
    mapping = {
        "cafe": "cafe",
        "italian": "restaurant",
        "street_food": "restaurant",
        "fine_dining": "restaurant",
    }
    return mapping.get(cuisine, "restaurant")
