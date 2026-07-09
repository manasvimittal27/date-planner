"""
Thin wrapper around the Foursquare Places API (v3, Pro tier — free, no card required).
Keeping this isolated in its own file means retrieve_venues (the node) never
talks to the API directly — it only calls this function. That's the "adapter
pattern": if we ever swap providers again, only this file changes, not the node.

Important limitation, by design: Foursquare's free Pro tier does NOT include
rating or review_count — those are Premium-only fields, billed from the first
call. So this wrapper returns None for both, and rank_and_explain (Node C)
must not treat rating as a required signal — rank by distance/category match
instead, and treat rating as a bonus if we ever add the paid tier later.
"""

import os
import requests

FOURSQUARE_SEARCH_URL = "https://places-api.foursquare.com/places/search"

# Rather than guess Foursquare's internal category IDs (a real bug we hit — our
# first attempt used made-up IDs and got government buildings back instead of
# cafes), we use the plain-text "query" parameter instead. It searches on
# name/category keywords directly, which is more reliable without needing to
# look up Foursquare's full category taxonomy.
QUERY_KEYWORDS = {
    "cafe": "cafe coffee",
    "restaurant": "restaurant",
    "activity": "activity entertainment",
}


def search_places(
    location: dict,
    radius_meters: float,
    place_type: str,
    min_price: int = 0,
    max_price: int = 4,
    open_now: bool = False,
) -> list[dict]:
    """
    Calls the Foursquare Places API and returns a simplified list of venue dicts.
    Raises no exceptions on empty results — an empty list just means zero matches,
    which the graph's retry loop knows how to handle.
    """
    api_key = os.environ.get("FOURSQUARE_API_KEY")
    if not api_key:
        raise RuntimeError(
            "FOURSQUARE_API_KEY is not set. Set it as an environment variable "
            "before calling search_places — see your shell config or .env file."
        )

    headers = {
        "Authorization": f"Bearer {api_key}",
        "X-Places-Api-Version": "2025-06-17",
        "Accept": "application/json",
    }

    params = {
        "ll": f"{location['lat']},{location['lng']}",
        "radius": int(radius_meters),
        "query": QUERY_KEYWORDS.get(place_type, QUERY_KEYWORDS["restaurant"]),
        "limit": 20,
    }
    if open_now:
        params["open_now"] = "true"

    response = requests.get(FOURSQUARE_SEARCH_URL, headers=headers, params=params, timeout=10)
    response.raise_for_status()
    data = response.json()

    raw_places = data.get("results", [])
    # Note: no price filtering here yet — Foursquare's free tier price data is
    # inconsistent/sparse, so we don't hard-filter on it. rank_and_explain can
    # still use price_level if a venue happens to have it.
    return [_simplify_place(p) for p in raw_places]


def _simplify_place(place: dict) -> dict:
    """Converts Foursquare's response shape into just what our nodes need."""
    location = place.get("location", {})

    return {
        "name": place.get("name", "Unknown"),
        "address": location.get("formatted_address", ""),
        "lat": place.get("latitude"),
        "lng": place.get("longitude"),
        "rating": None,        # not available on the free tier — see module docstring
        "review_count": None,  # not available on the free tier
        "price_level": place.get("price"),  # sometimes present, often null — don't rely on it
    }
