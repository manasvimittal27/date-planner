"""
Test for Node B (retrieve_venues) and its conditional edge (check_results).

We don't have a real Google Places API key set up yet, so we "monkeypatch" —
temporarily swap out — the real search_places function with a fake one that
returns made-up data. This lets us test the NODE's logic (does it call the
API with the right arguments? does the retry loop work?) completely separately
from whether the real API integration works.
"""

import sys
sys.path.insert(0, "..")

from state import DateState
import nodes.retrieve as retrieve_module


def fake_search_places_with_results(location, radius_meters, place_type, min_price, max_price, open_now):
    """Pretends the API found 2 venues."""
    return [
        {"name": "Cafe Delight", "address": "123 MG Road", "lat": 28.61, "lng": 77.20,
         "rating": 4.3, "review_count": 210, "price_level": 2},
        {"name": "Spice Corner", "address": "45 CP", "lat": 28.62, "lng": 77.21,
         "rating": 4.0, "review_count": 85, "price_level": 2},
    ]


def fake_search_places_empty(location, radius_meters, place_type, min_price, max_price, open_now):
    """Pretends the API found nothing — to test the retry path."""
    return []


base_state: DateState = {
    "partner_a_answers": {"budget": 800, "vibe": "chill", "cuisine": "chinese", "indoor_outdoor": "indoor", "occasion": "casual"},
    "partner_b_answers": {"budget": 1200, "vibe": "romantic", "cuisine": "indian", "indoor_outdoor": "indoor", "occasion": "casual"},
    "merged_constraints": {
        "location": {"lat": 28.6139, "lng": 77.2090},
        "radius_km": 2.0,
        "price_level_min": 0,
        "price_level_max": 2,
        "category": "restaurant",
        "vibe": "flexible",
        "indoor_outdoor": "indoor",
        "time_sensitive": False,
        "occasion": "casual",
    },
    "candidate_venues": [],
    "retry_attempts": 0,
    "chosen_venue": None,
    "reasoning": "",
    "outfit_suggestion": "",
}


def test_retrieve_with_results():
    print("--- Test 1: API returns results ---")
    retrieve_module.search_places = fake_search_places_with_results

    result = retrieve_module.retrieve_venues(base_state)
    print(f"  Got {len(result['candidate_venues'])} venues")
    assert len(result["candidate_venues"]) == 2, "should get 2 fake venues back"

    # feed this result into check_results to confirm it routes correctly
    state_after = {**base_state, **result}
    next_node = retrieve_module.check_results(state_after)
    print(f"  check_results routes to: {next_node}")
    assert next_node == "rank_and_explain", "results exist, should move forward, not retry"
    print("  PASSED\n")


def test_retrieve_empty_triggers_retry():
    print("--- Test 2: API returns zero results, should trigger retry ---")
    retrieve_module.search_places = fake_search_places_empty

    result = retrieve_module.retrieve_venues(base_state)
    assert len(result["candidate_venues"]) == 0, "fake API should return nothing"

    state_after = {**base_state, **result}
    next_node = retrieve_module.check_results(state_after)
    print(f"  check_results routes to: {next_node}")
    assert next_node == "loosen_constraints", "zero results with attempts=0 should retry, not give up"

    loosened = retrieve_module.loosen_constraints(state_after)
    print(f"  after loosening: radius_km = {loosened['merged_constraints']['radius_km']}, "
          f"retry_attempts = {loosened['retry_attempts']}")
    assert loosened["merged_constraints"]["radius_km"] == 5.0, "first retry should widen radius by 3km"
    assert loosened["retry_attempts"] == 1, "retry counter should increment"
    print("  PASSED\n")


def test_max_retries_gives_up_gracefully():
    print("--- Test 3: after max retries, should give up instead of looping forever ---")
    state_maxed = {**base_state, "retry_attempts": 2, "candidate_venues": []}
    next_node = retrieve_module.check_results(state_maxed)
    print(f"  check_results routes to: {next_node}")
    assert next_node == "rank_and_explain", "should give up after 2 attempts, not loop forever"
    print("  PASSED\n")


if __name__ == "__main__":
    test_retrieve_with_results()
    test_retrieve_empty_triggers_retry()
    test_max_retries_gives_up_gracefully()
    print("All Node B tests passed.")
