"""
Node C: rank_and_explain

Takes the candidate venues from Node B and:
1. Deduplicates by chain name (we saw this need firsthand — a Foursquare
   keyword search for "cafe" in Delhi returned 5 Café Coffee Day locations
   in a row, which would make for a very repetitive date suggestion)
2. Scores what's left by distance (our free Foursquare tier doesn't include
   rating/review_count, so distance + category match are our real signals for v1)
3. Picks the top venue and calls an LLM to explain the choice in plain language

This node deliberately separates "which venue wins" (pure Python, deterministic,
easy to test) from "how do we explain it" (an LLM call, since generating natural
language reasoning is a judgment task, not arithmetic).
"""

import math
from state import DateState
from utils.llm import generate_text


def rank_and_explain(state: DateState) -> dict:
    candidates = state["candidate_venues"]

    if not candidates:
        return {
            "chosen_venue": None,
            "reasoning": (
                "We couldn't find a venue matching your preferences, even after "
                "widening the search. Try adjusting your budget or location."
            ),
        }

    deduped = _deduplicate_by_chain(candidates)
    user_location = state["merged_constraints"]["location"]
    scored = _score_by_distance(deduped, user_location)

    top_venue = scored[0][1]
    reasoning = _generate_reasoning(top_venue, state["merged_constraints"])

    return {"chosen_venue": top_venue, "reasoning": reasoning}


def _deduplicate_by_chain(venues: list[dict]) -> list[dict]:
    """
    Keeps only one venue per (name, rough location) combination.

    Same name AND close together (within ~1km) is treated as the same chain,
    different branch — this is the Café Coffee Day problem we actually saw:
    5 branches within a couple km of each other, same name every time.

    Same name but FAR apart is treated as two unrelated venues that happen to
    share a name — a real, if less common, case (e.g. two independently-owned
    "Cafe Coffee House" spots in different neighborhoods). These are kept
    separate rather than incorrectly merged.

    A true v2 fix would use a chain/business ID from the API if one becomes
    available — string-matching names is inherently a heuristic, not a
    guarantee, but this is a meaningful improvement over name-only matching.
    """
    SAME_CHAIN_RADIUS_KM = 1.0

    kept = []
    for venue in venues:
        is_duplicate = False
        if venue["lat"] is not None and venue["lng"] is not None:
            for existing in kept:
                if existing["name"] != venue["name"]:
                    continue
                if existing["lat"] is None or existing["lng"] is None:
                    continue
                distance = _haversine_distance(
                    existing["lat"], existing["lng"], venue["lat"], venue["lng"]
                )
                if distance < SAME_CHAIN_RADIUS_KM:
                    is_duplicate = True
                    break
        else:
            # no coordinates to compare — fall back to exact name match only,
            # since we can't verify proximity
            is_duplicate = any(existing["name"] == venue["name"] for existing in kept)

        if not is_duplicate:
            kept.append(venue)

    return kept


def _score_by_distance(venues: list[dict], user_location: dict) -> list[tuple[float, dict]]:
    """
    Scores each venue by distance from the user (closer = higher score).
    Returns a list of (score, venue) tuples, sorted best-first.

    Note: we treat distance < 10 meters as suspicious rather than a genuine
    "right next door" match. We saw this in practice — a venue came back at
    exactly 0.0 km, which is far more likely to mean Foursquare's data lacks
    precise coordinates for that place (and defaulted to the search center)
    than an actual coincidence of the user standing inside the venue.
    """
    scored = []
    for venue in venues:
        if venue["lat"] is None or venue["lng"] is None:
            continue  # can't score a venue with no coordinates — skip it

        distance_km = _haversine_distance(
            user_location["lat"], user_location["lng"],
            venue["lat"], venue["lng"],
        )
        if distance_km < 0.01:  # under 10 meters — treat as unreliable data, not a real match
            continue

        # simple inverse scoring: closer venues get a higher score
        score = 1 / (distance_km + 0.1)  # +0.1 avoids divide-by-zero for very close venues
        venue_with_distance = {**venue, "distance_km": round(distance_km, 2)}
        scored.append((score, venue_with_distance))

    scored.sort(key=lambda pair: pair[0], reverse=True)
    return scored


def _haversine_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """
    Calculates the straight-line distance between two lat/lng points, in km.
    This is the standard formula for distance on a sphere — worth knowing by name
    since it comes up constantly in location-based apps.
    """
    R = 6371  # Earth's radius in km
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lng2 - lng1)

    a = (math.sin(delta_phi / 2) ** 2
         + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def _generate_reasoning(venue: dict, constraints: dict) -> str:
    """
    Calls Gemini to generate natural-language reasoning for why this venue
    was chosen. We give the LLM the concrete facts (distance, vibe, occasion)
    rather than asking it to invent anything — it's explaining a decision
    that already happened in _score_by_distance, not making the decision itself.
    """
    prompt = f"""Explain why this venue is a good pick for a couple's date. Ground the
explanation only in the facts below — don't invent anything.

Venue: {venue['name']}
Address: {venue['address']}
Distance from them: {venue['distance_km']} km
Their stated vibe preference: {constraints.get('vibe', 'not specified')}
Occasion: {constraints.get('occasion', 'not specified')}

Write exactly 1-2 sentences. Rules:
- No greeting, no opener like "Hey there" or "How about"
- No rhetorical questions
- No exclamation marks
- No filler enthusiasm ("perfect!", "great choice!", "you'll love it")
- Don't mention rating or reviews — we don't have that data
- State it plainly, like a person giving a quick, matter-of-fact recommendation
  to a friend — not like a salesperson or an assistant

Example of the tone we want: "Café Coffee Day is close by and fits the low-key
vibe you're after — good option if you don't want to travel far for a casual hang."

Example of what to avoid: "Hey! How about Café Coffee Day? It's super close and
perfect for a chill vibe — you'll love it!" """

    try:
        return generate_text(prompt)
    except Exception as e:
        # If the LLM call fails for any reason (network, quota, bad response),
        # fall back to the simple templated version rather than crashing the
        # whole graph over a reasoning-text failure — the venue pick itself
        # is still valid and useful even without a nicely worded explanation.
        return (
            f"{venue['name']} is about {venue['distance_km']} km away — "
            f"the closest match to your preferences. "
            f"(Note: couldn't generate a detailed explanation right now: {e})"
        )
