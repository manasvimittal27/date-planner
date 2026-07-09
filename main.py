"""
main.py — runs the full date planner graph end to end.

This makes REAL calls to Foursquare, Gemini (twice — once for reasoning, once
for the outfit suggestion), and Open-Meteo. Make sure FOURSQUARE_API_KEY and
GEMINI_API_KEY are both set as environment variables before running this.

Run with: python3 main.py
"""

from graph import build_graph

app = build_graph()

initial_state = {
    "partner_a_answers": {
        "budget": 800,
        "vibe": "chill",
        "cuisine": "cafe",
        "indoor_outdoor": "indoor",
        "occasion": "casual",
    },
    "partner_b_answers": {
        "budget": 1200,
        "vibe": "chill",
        "cuisine": "cafe",
        "indoor_outdoor": "indoor",
        "occasion": "casual",
    },
    "merged_constraints": {},
    "candidate_venues": [],
    "retry_attempts": 0,
    "chosen_venue": None,
    "reasoning": "",
    "outfit_suggestion": "",
}

print("Running the full date planner graph...\n")
result = app.invoke(initial_state)

print("=" * 50)
print("DATE PLAN")
print("=" * 50)

if result["chosen_venue"]:
    print(f"\nVenue: {result['chosen_venue']['name']}")
    print(f"Address: {result['chosen_venue']['address']}")
    print(f"Distance: {result['chosen_venue']['distance_km']} km")
else:
    print("\nNo venue found.")

print(f"\nWhy this pick:\n  {result['reasoning']}")
print(f"\nWhat to wear:\n  {result['outfit_suggestion']}")
