# FAST ETA — an interactive ML case study

A scrollytelling site that walks through a food-delivery ETA project (messy data → cleaning → leakage prevention → modeling → test evaluation → engineering experiment) and ends with a live predictor running the **supplied, unmodified** `zomato_fast_eta_model.joblib`. Nothing is retrained, tuned or replaced.

## Project facts
- **Business problem:** predict total delivery time (`Time_taken (min)`) when an order is placed, using only information available then.
- **Dataset:** 45,584 records, 20 original columns, 44 unique dates, 2022-02-11 → 2022-04-06.
- **Data quality:** 53 ratings outside 1–5 → set to missing. 3,640 records with a GPS coordinate of |value| < 0.1 → kept, `GPS_valid=0`, coordinates NaN (41,944 valid). Haversine (R = 6371 km); > 100 km invalid. 41,513 valid distances: mean 9.7198, median 9.1930, 75th pct 13.6809, max 20.9695 km.
- **Time parsing:** handles HH:MM, HH:MM:SS, day fractions and ≥ 24:00. `order_minute` excluded (weak signal, 11 distinct values).
- **Leakage:** `Time_Order_picked` occurs after the order is placed and is excluded; IDs are not features.
- **Split (chronological):** train 2022-02-11 → 03-25, validation 03-26 → 03-31, test 04-01 → 04-06.
- **20 features:** exactly those in `zomato_fast_eta_metadata.json`.
- **Validation RMSE:** mean baseline 9.474 · Linear 6.063 · Decision Tree 4.268 · initial RF 4.184 · tuned RF 4.058 (3.01% better than initial RF).
- **Tuned RF:** n_estimators 150, max_depth 15, min_samples_leaf 1, min_samples_split 2, max_features 0.5, random_state 42 (lightweight 3-fold CV search).
- **Final test:** RMSE 4.032 min · MAE 3.214 min · R² 0.811 · **80.38% of predictions within ±5 minutes** (not "accuracy").
- **Road-distance experiment (not in the model):** 100 pairs, 99 routed. Mean Haversine 8.8145 km vs road 12.6308 km; ratio mean 1.504×, median 1.421×. No road-distance model was trained or evaluated on the test set, so nothing is claimed about predictive value.
- **Feature importances:** read from the saved forest (`feature_importances_`, one-hot columns summed per original feature) and embedded in the page. They are impurity-based, descriptive and not causal.

## Architecture
```
frontend/index.html ──POST /api/predict──▶ backend/server.py (Starlette) ──▶ zomato_fast_eta_model.joblib
(static story + UI)                        builds the 20 raw features,        (sklearn Pipeline)
                                           validates inputs, model.predict
```
The page is dependency-free (vanilla JS, SVG/CSS, `IntersectionObserver`, `prefers-reduced-motion` respected, readable without JS). The same server hosts the page, so one process serves everything. The what-if simulator sends two scenarios to the same endpoint; it is a model-based counterfactual, not a causal estimate. Its distance option scales the delivery coordinates toward/away from the restaurant.

## Run locally
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn backend.server:app --port 8000      # open http://localhost:8000
```
Keep the pinned versions (scikit-learn 1.6.1, pandas 2.2.3, numpy 2.1.3, joblib 1.6.0); the model was serialized with them (Python 3.13.16).

## Deploy
- **Simplest:** any container host (Render, Fly.io, Railway, Cloud Run) using the included `Dockerfile`; it serves site and API together.
- **Vercel:** host `frontend/` as a static site and set `window.API_BASE="https://your-api-host"` before the main script in `index.html`; add CORS to the API (Starlette `CORSMiddleware`). A Python serverless function with scikit-learn + a ~98 MB model may exceed Vercel's size limit; this was not tested.

## Limitations
One 44-date period; performance may shift under other conditions. Haversine is not route distance. Weather/traffic are historical categorical labels. No causal claims. Predictions are expected times, not guarantees, and no prediction intervals are provided. Missing GPS/time are imputed by the pipeline, so those estimates are less specific.
