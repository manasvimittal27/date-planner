# Date Planner — LangGraph project (work in progress)

## What's built so far
- `state.py` — the shared DateState schema
- `nodes/reconcile.py` — Node A: merges both partners' quiz answers
- `nodes/retrieve.py` — Node B: calls the Places API, includes the retry/loosen-constraints loop
- `utils/places_api.py` — Foursquare Places API wrapper (free tier, no card required)

## Setup

1. Install Python 3.10+ if you don't have it.
2. Create a virtual environment (recommended, keeps this project's packages separate from
   everything else on your machine):
   ```
   python3 -m venv venv
   source venv/bin/activate      # on Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
4. Set your Foursquare API key as an environment variable:
   ```
   export FOURSQUARE_API_KEY="your-key-here"     # on Windows PowerShell: $env:FOURSQUARE_API_KEY="..."
   ```
   Do this every time you open a new terminal, or add it to your shell config
   (~/.zshrc or ~/.bashrc) to make it permanent.

## Running the tests

```
python3 test_reconcile.py              # tests Node A with fake data, no API calls
python3 test_retrieve.py               # tests Node B's logic with a FAKE Places API (no real key needed)
python3 test_real_foursquare_call.py   # makes a REAL call to Foursquare — needs your API key set
```

## What's next
- Node C: rank_and_explain (ranks venues, picks the best one, explains why)
- Node D: outfit_suggestion
- graph.py: wires all four nodes together into the actual LangGraph graph
- main.py: runs the whole thing end to end

## A note on rating data
Foursquare's free tier doesn't include ratings/review counts — those are a paid feature.
Our ranking logic (once we build Node C) will lean on distance and category/vibe match
instead. Worth knowing if you ever compare this project's venue picks against what you'd
expect from Google Maps ratings — they're not using the same signals.

## Deploying to Render (free hosting)

This deploys two separate services: the FastAPI backend and the static frontend.

### Step 1: Push this project to GitHub
Render deploys from a GitHub repo, not a direct file upload.
1. Create a new repository on GitHub (github.com → New repository)
2. In your terminal, inside the date-planner folder:
   ```
   git init
   git add .
   git commit -m "Initial commit"
   git branch -M main
   git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
   git push -u origin main
   ```

### Step 2: Deploy on Render
1. Go to https://render.com and sign up (no card required for the free tier)
2. Click "New" → "Blueprint"
3. Connect your GitHub account and select this repository
4. Render will detect `render.yaml` and show both services (API + frontend) —
   click "Apply" to create them
5. For the API service, go to its "Environment" tab and add your real
   `FOURSQUARE_API_KEY` and `GEMINI_API_KEY` values (these were marked
   `sync: false` in render.yaml specifically so you set them here, not in
   version-controlled code)
6. Wait for both services to finish deploying (a few minutes)

### Step 3: Connect the frontend to the real backend URL
1. Once the API service is live, copy its URL from the Render dashboard
   (looks like `https://date-planner-api-XXXX.onrender.com`)
2. Edit `frontend/index.html`, find the line `const API_URL = ...` and change
   it to `https://date-planner-api-XXXX.onrender.com/plan-date`
3. Commit and push this change — Render will auto-redeploy the frontend

### Step 4: Tighten CORS (see the TODO comment in api.py)
Once you know your frontend's real Render URL, update `allow_origins` in
`api.py` from `["*"]` to your actual frontend URL, then commit and push.

### A real limitation to know about
Render's free tier spins the backend down after 15 minutes of no traffic.
The next request after that will take 30-50 seconds to respond while it wakes
back up — normal and expected on the free tier, not a bug. Fine for a
portfolio demo; if this ever needs to feel instant for real users, that's a
paid-tier upgrade, not a code change.
