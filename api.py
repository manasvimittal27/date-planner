"""
api.py — exposes our LangGraph date planner as an HTTP API.

This is the layer a frontend will actually call. It takes both partners'
quiz answers plus a real location (lat/lng from the browser), runs the graph,
and returns the result as JSON.

Run with: uvicorn api:app --reload
Then visit http://127.0.0.1:8000/docs for an interactive test page —
FastAPI generates this automatically, no extra work needed.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from graph import build_graph

app = FastAPI(title="Date Planner API")

# CORS: allows a frontend running on a different origin (e.g. a local dev
# server on a different port, or a deployed frontend on a different domain)
# to actually call this API from the browser. Without this, browsers block
# the request by default as a security measure.
#
# TODO after deploying: replace "*" with your actual frontend's Render URL,
# e.g. ["https://date-planner-frontend-XXXX.onrender.com"]. Leaving this as
# "*" means ANY website can call your API and consume your Foursquare/Gemini
# quota — fine while testing, a real risk once this is live and discoverable.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

compiled_graph = build_graph()


class PartnerAnswers(BaseModel):
    budget: int
    vibe: str
    cuisine: str
    indoor_outdoor: str
    occasion: str


class PlanDateRequest(BaseModel):
    partner_a_answers: PartnerAnswers
    partner_b_answers: PartnerAnswers
    latitude: float
    longitude: float


@app.post("/plan-date")
def plan_date(request: PlanDateRequest):
    """
    Runs the full graph with real quiz answers and a real location,
    and returns the venue, reasoning, and outfit suggestion.
    """
    initial_state = {
        "partner_a_answers": request.partner_a_answers.model_dump(),
        "partner_b_answers": request.partner_b_answers.model_dump(),
        "merged_constraints": {},
        "candidate_venues": [],
        "retry_attempts": 0,
        "chosen_venue": None,
        "reasoning": "",
        "outfit_suggestion": "",
        "user_location": {"lat": request.latitude, "lng": request.longitude},
    }

    result = compiled_graph.invoke(initial_state)

    return {
        "venue": result["chosen_venue"],
        "reasoning": result["reasoning"],
        "outfit_suggestion": result["outfit_suggestion"],
    }


@app.get("/health")
def health():
    """Simple endpoint to confirm the API is up — useful once this is deployed."""
    return {"status": "ok"}
