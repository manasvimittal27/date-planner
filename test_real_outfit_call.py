"""
Run this on YOUR machine to test Node D end-to-end with REAL weather + Gemini calls.

No weather API key needed at all (Open-Meteo is fully free, no signup).
Make sure GEMINI_API_KEY is still set from before.

Run with: python3 test_real_outfit_call.py
"""

import sys
sys.path.insert(0, "..")

from nodes.outfit import outfit_suggestion

fake_state = {
    "merged_constraints": {
        "location": {"lat": 28.6139, "lng": 77.2090},  # Delhi
        "occasion": "casual",
        "vibe": "chill",
    }
}

print("Calling outfit_suggestion with REAL weather + Gemini...\n")
result = outfit_suggestion(fake_state)
print(f"Outfit suggestion:\n  {result['outfit_suggestion']}")
