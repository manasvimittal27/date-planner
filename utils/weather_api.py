"""
Thin wrapper around Open-Meteo (https://open-meteo.com) — genuinely free,
no API key, no signup, no card. Same adapter pattern as our other utils files.
"""

import requests

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"


def get_current_weather(location: dict) -> dict:
    """
    Returns simplified current weather for the given lat/lng.
    No API key required at all — this call works with zero setup.
    """
    params = {
        "latitude": location["lat"],
        "longitude": location["lng"],
        "current": "temperature_2m,precipitation,weather_code",
    }

    response = requests.get(OPEN_METEO_URL, params=params, timeout=10)
    response.raise_for_status()
    data = response.json()

    current = data.get("current", {})
    return {
        "temperature_c": current.get("temperature_2m"),
        "precipitation_mm": current.get("precipitation"),
        "weather_code": current.get("weather_code"),
        "is_rainy": (current.get("precipitation") or 0) > 0,
    }
