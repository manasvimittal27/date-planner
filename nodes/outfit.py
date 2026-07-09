"""
Node D: outfit_suggestion

Runs in parallel with Node C (rank_and_explain) — it doesn't need the chosen
venue, only the merged_constraints (occasion, vibe) and current weather.
This is why it's a separate branch in the graph rather than chained after C:
there's no data dependency between them, so they can execute independently.

Same pattern as Node C's reasoning: get real facts first (weather), then use
an LLM only to phrase the suggestion naturally — never to invent the weather.
"""

from state import DateState
from utils.weather_api import get_current_weather
from utils.llm import generate_text


def outfit_suggestion(state: DateState) -> dict:
    constraints = state["merged_constraints"]
    location = constraints["location"]

    try:
        weather = get_current_weather(location)
    except Exception as e:
        # Weather is a nice-to-have for this suggestion, not a hard requirement —
        # fall back to a weather-agnostic suggestion rather than failing the node.
        weather = None

    suggestion = _generate_outfit_suggestion(constraints, weather)
    return {"outfit_suggestion": suggestion}


def _generate_outfit_suggestion(constraints: dict, weather: dict | None) -> str:
    occasion = constraints.get("occasion", "casual")
    vibe = constraints.get("vibe", "flexible")

    if weather is not None:
        weather_line = (
            f"Current weather: {weather['temperature_c']}°C, "
            f"{'rainy' if weather['is_rainy'] else 'no rain expected'}."
        )
    else:
        weather_line = "Weather data isn't available right now — suggest something weather-neutral."

    prompt = f"""Suggest an outfit color palette for a couple's date. Ground it only
in the facts below — don't invent anything.

Occasion: {occasion}
Vibe: {vibe}
{weather_line}

Give a 2-3 color palette and one practical style note. Don't refer to "person
one" and "person two" or use numbered labels — just give general guidance that
works for both of them, or phrase it as "one of you... the other...' if you
genuinely need to differentiate. Rules:
- No greeting, no opener like "Hey there" or "How about"
- No rhetorical questions
- No exclamation marks
- No filler enthusiasm ("perfect!", "you'll love it", "stay stylish!")
- No brand names or exact clothing items — just colors and general style
  (e.g. "light, breathable fabrics")
- 2-3 sentences total, stated plainly like a friend giving quick practical advice

Example of the tone we want: "Stick to light neutrals — off-white, sand, pale
blue — given the heat. Breathable cotton over anything heavy."

Example of what to avoid: "Hey! For your date, how about a fresh palette of
soft blues and off-whites? You'll both look amazing and stay cool!" """

    try:
        return generate_text(prompt)
    except Exception as e:
        return (
            f"For a {vibe} {occasion} date, soft neutral tones (beige, white, "
            f"muted blue) are a safe, flattering choice for both of you. "
            f"(Note: couldn't generate a detailed suggestion right now: {e})"
        )
