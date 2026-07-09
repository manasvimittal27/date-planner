"""
DateState is the shared "notebook" that flows through every node in the graph.
Each node reads whatever fields it needs and returns only the fields it changes —
LangGraph merges those changes into the full state automatically.
"""

from typing_extensions import TypedDict
from typing import Optional, List, Dict, Any


class PartnerAnswers(TypedDict):
    """The 5 questions, answered by one partner."""
    budget: int              # in rupees, per person
    vibe: str                # "chill" | "adventurous" | "romantic" | "fun_loud"
    cuisine: str              # e.g. "italian", "cafe", "street_food"
    indoor_outdoor: str       # "indoor" | "outdoor" | "either"
    occasion: str             # "casual" | "anniversary" | "first_date"


class MergedConstraints(TypedDict, total=False):
    """What Node A produces after reconciling both partners' answers.
    total=False means not every key has to be present — useful since
    loosen_constraints will add/modify keys over retries."""
    location: Dict[str, float]   # {"lat": ..., "lng": ...}
    radius_km: float
    price_level_min: int          # Places API price levels: 0-4
    price_level_max: int
    category: str                  # "cafe" | "restaurant" | "activity"
    indoor_outdoor: str             # "indoor" | "outdoor"
    vibe: str
    time_sensitive: bool
    occasion: str


class DateState(TypedDict, total=False):
    # --- inputs ---
    partner_a_answers: PartnerAnswers
    partner_b_answers: PartnerAnswers
    user_location: Optional[Dict[str, float]]  # real lat/lng from the API layer, if provided

    # --- Node A output ---
    merged_constraints: MergedConstraints

    # --- Node B output (+ retry loop) ---
    candidate_venues: List[Dict[str, Any]]
    retry_attempts: int

    # --- Node C output ---
    chosen_venue: Optional[Dict[str, Any]]
    reasoning: str

    # --- Node D output ---
    outfit_suggestion: str
