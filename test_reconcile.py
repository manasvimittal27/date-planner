"""
Quick manual test for Node A (reconcile_preferences).
Not a formal unit test yet — just a way to see the node work with real-looking input
before we wire it into the full graph.
"""

import sys
sys.path.insert(0, "..")  # so we can import state.py from the parent folder

from state import DateState
from nodes.reconcile import reconcile_preferences

# Two example partners answering the 5 questions
example_state: DateState = {
    "partner_a_answers": {
        "budget": 800,
        "vibe": "chill",
        "cuisine": "chinese",
        "indoor_outdoor": "indoor",
        "occasion": "casual",
    },
    "partner_b_answers": {
        "budget": 1200,
        "vibe": "romantic",   # deliberately different from A, to test the "flexible" fallback
        "cuisine": "indian",  # deliberately different from A, to test conflict handling
        "indoor_outdoor": "indoor",
        "occasion": "casual",
    },
    # the rest of these fields don't matter yet since Node A doesn't touch them
    "merged_constraints": {},
    "candidate_venues": [],
    "retry_attempts": 0,
    "chosen_venue": None,
    "reasoning": "",
    "outfit_suggestion": "",
}

if __name__ == "__main__":
    result = reconcile_preferences(example_state)

    print("Node A output:")
    for key, value in result.items():
        print(f"  {key}: {value}")

    # A couple of sanity checks so we're not just eyeballing the output
    assert result["merged_constraints"]["price_level_max"] == 2, "800 rupees should map to price level 2"
    assert result["merged_constraints"]["vibe"] == "flexible", "mismatched vibes should fall back to flexible"
    assert result["retry_attempts"] == 0, "retry_attempts should start at 0"
    assert result["merged_constraints"]["category"] == "restaurant", (
        "mismatched cuisine (chinese vs indian) should fall back to the broad 'restaurant' category, "
        "not silently pick partner A's answer"
    )
    assert "indoor_outdoor" in result["merged_constraints"], (
        "indoor_outdoor was computed but must actually be written into merged_constraints"
    )
    assert result["merged_constraints"]["indoor_outdoor"] == "indoor", "both partners chose indoor, should match"

    print("\nAll checks passed.")


def test_real_location_overrides_default():
    """A separate, explicit test: when user_location IS provided in state,
    it should be used instead of the hardcoded Delhi default."""
    print("\n--- Testing real location override ---")
    mumbai_location = {"lat": 19.0760, "lng": 72.8777}
    state_with_real_location = {**example_state, "user_location": mumbai_location}

    result = reconcile_preferences(state_with_real_location)
    print(f"  location used: {result['merged_constraints']['location']}")
    assert result["merged_constraints"]["location"] == mumbai_location, (
        "should use the real provided location, not fall back to the Delhi default"
    )
    print("  PASSED — real location correctly overrides the default")


test_real_location_overrides_default()
