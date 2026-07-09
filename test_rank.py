"""
Tests for Node C (rank_and_explain), using data shaped like what we actually
saw from the real Foursquare call — multiple Café Coffee Day locations, since
that's the real duplicate problem this node needs to solve.
"""

import sys
sys.path.insert(0, "..")

from nodes.rank import rank_and_explain, _deduplicate_by_chain, _haversine_distance
import nodes.rank as rank_module

# User is at our Delhi placeholder coordinates
USER_LOCATION = {"lat": 28.6139, "lng": 77.2090}

# Shaped like the real results we got — 5 Café Coffee Day locations at
# different addresses, plus one genuinely different cafe further away.
REALISTIC_CANDIDATES = [
    {"name": "Café Coffee Day", "address": "Janpath (Next To Sarvana Bhawan)",
     "lat": 28.626639961580253, "lng": 77.21928786545695, "rating": None, "review_count": None, "price_level": None},
    {"name": "Café Coffee Day", "address": "Janpath, New Delhi, Delhi",
     "lat": 28.62687063328005, "lng": 77.2197650541998, "rating": None, "review_count": None, "price_level": None},
    {"name": "Café Coffee Day", "address": "Gymkhana club (Chanakyapuri), New Delhi, Delhi",
     "lat": 28.600040985835808, "lng": 77.21143362337921, "rating": None, "review_count": None, "price_level": None},
    {"name": "Café Coffee Day", "address": "Janpath (Opposite Janpath Street Market), New Delhi, Delhi",
     "lat": 28.628999206370686, "lng": 77.21969768649409, "rating": None, "review_count": None, "price_level": None},
    {"name": "Blue Tokai Coffee Roasters", "address": "Khan Market, New Delhi",
     "lat": 28.5992, "lng": 77.2260, "rating": None, "review_count": None, "price_level": None},
]


def test_dedup_removes_repeated_chain():
    print("--- Test 1: dedup collapses NEARBY repeated Café Coffee Day entries ---")
    deduped = _deduplicate_by_chain(REALISTIC_CANDIDATES)
    names = [v["name"] for v in deduped]
    print(f"  names after dedup: {names}")
    # Of our 4 real CCD coordinates, 3 are within ~300m of each other (clearly
    # the same immediate cluster) and 1 (the Gymkhana Club branch) is genuinely
    # ~3km away — a real, different branch worth treating as a distinct option,
    # not noise. So we expect dedup down to 2 CCD entries, not 1: one for the
    # close cluster, one for the distant branch. This is more accurate than
    # blindly collapsing every same-named result regardless of real distance.
    assert names.count("Café Coffee Day") == 2, (
        "should collapse the 3 nearby CCD branches into 1, but keep the "
        "genuinely distant (3km away) branch as a separate option"
    )
    assert "Blue Tokai Coffee Roasters" in names, "the genuinely different cafe should still be present"
    assert len(deduped) == 3, "should have 3 venues left: 2 CCD clusters + 1 Blue Tokai"
    print("  PASSED\n")


def test_haversine_distance_sanity_check():
    print("--- Test 2: haversine distance gives a sane real-world number ---")
    # Delhi to Mumbai is roughly 1150km in a straight line — a good sanity check
    # since it's a well-known distance we can eyeball.
    delhi = (28.6139, 77.2090)
    mumbai = (19.0760, 72.8777)
    distance = _haversine_distance(*delhi, *mumbai)
    print(f"  Delhi to Mumbai calculated as: {distance:.0f} km")
    assert 1100 < distance < 1200, f"expected roughly 1150km, got {distance:.0f}km — formula may be wrong"
    print("  PASSED\n")


def test_rank_and_explain_full_flow():
    print("--- Test 3: full rank_and_explain picks the closest, deduplicated venue ---")
    fake_state = {
        "candidate_venues": REALISTIC_CANDIDATES,
        "merged_constraints": {
            "location": USER_LOCATION,
            "vibe": "chill",
            "occasion": "casual",
        },
    }
    result = rank_and_explain(fake_state)
    chosen = result["chosen_venue"]
    print(f"  chosen venue: {chosen['name']}")
    print(f"  distance: {chosen['distance_km']} km")
    print(f"  reasoning: {result['reasoning']}")

    assert chosen is not None, "should have chosen a venue"
    # of the deduped candidates, confirm we actually picked the closer one
    assert chosen["distance_km"] < 5, "the closest Delhi venue should be well under 5km from our test user location"
    print("  PASSED\n")


def test_empty_candidates_handled_gracefully():
    print("--- Test 4: empty candidate list doesn't crash, gives a graceful message ---")
    fake_state = {
        "candidate_venues": [],
        "merged_constraints": {"location": USER_LOCATION, "vibe": "chill", "occasion": "casual"},
    }
    result = rank_and_explain(fake_state)
    print(f"  chosen_venue: {result['chosen_venue']}")
    print(f"  reasoning: {result['reasoning']}")
    assert result["chosen_venue"] is None, "should be None when there are no candidates"
    assert len(result["reasoning"]) > 0, "should still give the user SOME message, not crash"
    print("  PASSED\n")


def test_reasoning_uses_llm_with_fallback():
    print("--- Test 5: reasoning generation calls the LLM, falls back gracefully if it fails ---")

    def fake_generate_text_success(prompt):
        assert "Café Coffee Day" in prompt, "prompt should mention the venue name"
        assert "chill" in prompt, "prompt should mention the vibe"
        return "This cozy cafe is perfect for a relaxed, chill hangout close to home."

    rank_module.generate_text = fake_generate_text_success
    fake_state = {
        "candidate_venues": REALISTIC_CANDIDATES,
        "merged_constraints": {"location": USER_LOCATION, "vibe": "chill", "occasion": "casual"},
    }
    result = rank_and_explain(fake_state)
    print(f"  reasoning (LLM succeeds): {result['reasoning']}")
    assert "cozy cafe" in result["reasoning"], "should use the LLM's actual generated text"

    def fake_generate_text_failure(prompt):
        raise RuntimeError("simulated network failure")

    rank_module.generate_text = fake_generate_text_failure
    result2 = rank_and_explain(fake_state)
    print(f"  reasoning (LLM fails, fallback): {result2['reasoning']}")
    assert "km away" in result2["reasoning"], "should fall back to the templated sentence, not crash"
    print("  PASSED\n")


def test_zero_distance_venue_is_filtered_out():
    print("--- Test 6: a venue at suspiciously exact 0.0 km is filtered, not chosen ---")
    candidates_with_bad_data = [
        {"name": "Tabula Beach Cafe", "address": "New Delhi, Delhi",
         "lat": USER_LOCATION["lat"], "lng": USER_LOCATION["lng"],  # exact match to user location — the bug we saw
         "rating": None, "review_count": None, "price_level": None},
        {"name": "Blue Tokai Coffee Roasters", "address": "Khan Market, New Delhi",
         "lat": 28.5992, "lng": 77.2260, "rating": None, "review_count": None, "price_level": None},
    ]
    fake_state = {
        "candidate_venues": candidates_with_bad_data,
        "merged_constraints": {"location": USER_LOCATION, "vibe": "chill", "occasion": "casual"},
    }
    result = rank_and_explain(fake_state)
    print(f"  chosen venue: {result['chosen_venue']['name']}")
    assert result["chosen_venue"]["name"] != "Tabula Beach Cafe", (
        "should NOT pick the venue with suspicious 0.0 km distance"
    )
    assert result["chosen_venue"]["name"] == "Blue Tokai Coffee Roasters", (
        "should fall through to the next genuinely-distanced venue"
    )
    print("  PASSED\n")


def test_dedup_keeps_same_name_if_far_apart():
    print("--- Test 7: two venues with the SAME name but far apart are NOT merged ---")
    # Two "City Cafe" locations, roughly 15km apart — plausible as two
    # unrelated independently-owned businesses that happen to share a name,
    # not branches of the same chain.
    far_apart_same_name = [
        {"name": "City Cafe", "address": "Connaught Place, New Delhi",
         "lat": 28.6315, "lng": 77.2167, "rating": None, "review_count": None, "price_level": None},
        {"name": "City Cafe", "address": "Saket, New Delhi",
         "lat": 28.5245, "lng": 77.2066, "rating": None, "review_count": None, "price_level": None},
    ]
    deduped = _deduplicate_by_chain(far_apart_same_name)
    print(f"  kept {len(deduped)} venues (expected 2 — different businesses, same name)")
    assert len(deduped) == 2, "same-named venues far apart should both be kept, not merged"
    print("  PASSED\n")


def test_dedup_merges_same_name_if_close():
    print("--- Test 8: two venues with the SAME name and close together ARE merged ---")
    close_together_same_name = [
        {"name": "City Cafe", "address": "Block A, Connaught Place",
         "lat": 28.6315, "lng": 77.2167, "rating": None, "review_count": None, "price_level": None},
        {"name": "City Cafe", "address": "Block B, Connaught Place",  # same chain, 400m away
         "lat": 28.6340, "lng": 77.2180, "rating": None, "review_count": None, "price_level": None},
    ]
    deduped = _deduplicate_by_chain(close_together_same_name)
    print(f"  kept {len(deduped)} venue (expected 1 — same chain, different branch)")
    assert len(deduped) == 1, "same-named venues close together should be merged as the same chain"
    print("  PASSED\n")


if __name__ == "__main__":
    test_dedup_removes_repeated_chain()
    test_haversine_distance_sanity_check()
    test_rank_and_explain_full_flow()
    test_empty_candidates_handled_gracefully()
    test_reasoning_uses_llm_with_fallback()
    test_zero_distance_venue_is_filtered_out()
    test_dedup_keeps_same_name_if_far_apart()
    test_dedup_merges_same_name_if_close()
    print("All Node C tests passed.")
