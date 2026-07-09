"""
Run this on YOUR machine (not in Claude's sandbox) to test the real Foursquare API call.

Before running:
1. Make sure FOURSQUARE_API_KEY is set in your terminal (export FOURSQUARE_API_KEY="...")
2. Install the requests library if you haven't: pip install requests

Run with: python3 test_real_foursquare_call.py
"""

import sys
sys.path.insert(0, "..")

from utils.places_api import search_places

# Delhi coordinates, same as our DEFAULT_LOCATION placeholder in reconcile.py
delhi = {"lat": 28.6139, "lng": 77.2090}

print("Calling the real Foursquare API...")
results = search_places(
    location=delhi,
    radius_meters=2000,
    place_type="cafe",
)

print(f"\nGot {len(results)} venues back:\n")
for venue in results[:5]:  # just show the first 5
    print(f"  {venue['name']}")
    print(f"    address: {venue['address']}")
    print(f"    lat/lng: {venue['lat']}, {venue['lng']}")
    print(f"    rating: {venue['rating']} (expected None — free tier doesn't include this)")
    print()
