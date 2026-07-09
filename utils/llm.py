"""
Thin wrapper around the Google Gemini API (free tier, no card required).
Same adapter pattern as utils/places_api.py — isolating the LLM call here
means rank_and_explain's node logic doesn't care which LLM provider we use.
If we ever swap to Claude or GPT later, only this file changes.
"""

import os
import requests

GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-2.5-flash:generateContent"
)


def generate_text(prompt: str) -> str:
    """
    Sends a prompt to Gemini and returns the generated text.
    Raises a clear error if the API key isn't set, and a clear error if the
    response doesn't have the shape we expect (rather than a confusing KeyError).
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not set. Get a free key from https://aistudio.google.com/apikey "
            "and set it as an environment variable before calling generate_text."
        )

    headers = {"Content-Type": "application/json"}
    params = {"key": api_key}
    body = {
        "contents": [
            {"parts": [{"text": prompt}]}
        ]
    }

    response = requests.post(GEMINI_URL, headers=headers, params=params, json=body, timeout=15)
    response.raise_for_status()
    data = response.json()

    try:
        return data["candidates"][0]["content"]["parts"][0]["text"].strip()
    except (KeyError, IndexError) as e:
        raise RuntimeError(
            f"Unexpected response shape from Gemini API: {data}"
        ) from e
