"""
Tests for Node D (outfit_suggestion) using fake weather and LLM responses —
verifies the node's logic without needing real network calls.
"""

import sys
sys.path.insert(0, "..")

import nodes.outfit as outfit_module
from nodes.outfit import outfit_suggestion


def test_outfit_with_weather_and_llm_success():
    print("--- Test 1: weather + LLM both succeed ---")

    def fake_weather(location):
        return {"temperature_c": 32.0, "precipitation_mm": 0, "weather_code": 0, "is_rainy": False}

    def fake_llm(prompt):
        assert "32.0" in prompt, "prompt should include the actual temperature value"
        assert "romantic" in prompt, "prompt should mention the vibe"
        return "Go with soft pastels and light linen — perfect for a warm, romantic evening."

    outfit_module.get_current_weather = fake_weather
    outfit_module.generate_text = fake_llm

    fake_state = {
        "merged_constraints": {
            "location": {"lat": 28.6139, "lng": 77.2090},
            "occasion": "anniversary",
            "vibe": "romantic",
        }
    }
    result = outfit_suggestion(fake_state)
    print(f"  suggestion: {result['outfit_suggestion']}")
    assert "pastels" in result["outfit_suggestion"], "should use the LLM's real output"
    print("  PASSED\n")


def test_outfit_when_weather_fails():
    print("--- Test 2: weather API fails, should still produce a suggestion ---")

    def fake_weather_failure(location):
        raise RuntimeError("simulated weather API outage")

    def fake_llm(prompt):
        assert "isn't available" in prompt, "prompt should acknowledge missing weather gracefully"
        return "Since we don't have weather info, stick with versatile neutrals like grey and navy."

    outfit_module.get_current_weather = fake_weather_failure
    outfit_module.generate_text = fake_llm

    fake_state = {
        "merged_constraints": {
            "location": {"lat": 28.6139, "lng": 77.2090},
            "occasion": "casual",
            "vibe": "chill",
        }
    }
    result = outfit_suggestion(fake_state)
    print(f"  suggestion: {result['outfit_suggestion']}")
    assert "neutrals" in result["outfit_suggestion"], "should still get a usable suggestion despite weather failure"
    print("  PASSED\n")


def test_outfit_when_both_weather_and_llm_fail():
    print("--- Test 3: both weather AND LLM fail — should still not crash ---")

    def fake_weather_failure(location):
        raise RuntimeError("simulated weather API outage")

    def fake_llm_failure(prompt):
        raise RuntimeError("simulated LLM API outage")

    outfit_module.get_current_weather = fake_weather_failure
    outfit_module.generate_text = fake_llm_failure

    fake_state = {
        "merged_constraints": {
            "location": {"lat": 28.6139, "lng": 77.2090},
            "occasion": "casual",
            "vibe": "chill",
        }
    }
    result = outfit_suggestion(fake_state)
    print(f"  suggestion: {result['outfit_suggestion']}")
    assert "neutral tones" in result["outfit_suggestion"], "should fall back to the hardcoded safe suggestion"
    print("  PASSED\n")


if __name__ == "__main__":
    test_outfit_with_weather_and_llm_success()
    test_outfit_when_weather_fails()
    test_outfit_when_both_weather_and_llm_fail()
    print("All Node D tests passed.")
