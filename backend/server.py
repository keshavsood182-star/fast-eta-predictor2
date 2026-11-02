"""Inference API + static host. Loads the trained pipeline as-is (no retraining)."""
import json, math, logging
from pathlib import Path
import joblib, pandas as pd
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route, Mount
from starlette.staticfiles import StaticFiles

ROOT = Path(__file__).resolve().parent.parent
META = json.loads((ROOT / "zomato_fast_eta_metadata.json").read_text())
MODEL = joblib.load(ROOT / "zomato_fast_eta_model.joblib")
FEATURES = META["features"]
assert list(MODEL.feature_names_in_) == FEATURES
CATS = {"Weather_conditions": ["Cloudy","Fog","Sandstorms","Stormy","Sunny","Windy"],
        "Road_traffic_density": ["Low","Medium","High","Jam"],
        "Type_of_order": ["Buffet","Drinks","Meal","Snack"],
        "Type_of_vehicle": ["bicycle","electric_scooter","motorcycle","scooter"],
        "Festival": ["No","Yes"], "City": ["Metropolitian","Semi-Urban","Urban"]}
NAN = float("nan")

def haversine(a, b, c, d):
    p1, p2 = math.radians(a), math.radians(c)
    h = math.sin((p2-p1)/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(math.radians(d-b)/2)**2
    return 2*6371.0*math.asin(math.sqrt(min(1.0, h)))

def row(s):
    age, rating = float(s["Delivery_person_Age"]), float(s["Delivery_person_Ratings"])
    if not 15 <= age <= 50: raise ValueError("Age must be 15-50.")
    if not 1 <= rating <= 5: raise ValueError("Rating must be 1-5.")
    for k, v in CATS.items():
        if s[k] not in v: raise ValueError(f"Invalid {k}.")
    co = [float(s[k]) for k in ("Restaurant_latitude","Restaurant_longitude","Delivery_location_latitude","Delivery_location_longitude")]
    gv, dv, dist = 0, 0, NAN
    if s.get("gps_available") and not any(abs(c) < 0.1 for c in co):
        gv = 1
        d = haversine(*co)
        if d <= 100: dist, dv = d, 1
    if not gv: co = [NAN]*4
    hk = s.get("hour_known") and s.get("order_hour") is not None
    r = dict(Delivery_person_Age=age, Delivery_person_Ratings=rating,
             Vehicle_condition=float(s["Vehicle_condition"]), multiple_deliveries=float(s["multiple_deliveries"]),
             Restaurant_latitude=co[0], Restaurant_longitude=co[1], Delivery_location_latitude=co[2],
             Delivery_location_longitude=co[3], distance_km=dist,
             order_hour=float(s["order_hour"]) if hk else NAN, order_day_of_week=float(s["order_day_of_week"]),
             GPS_valid=float(gv), distance_valid=float(dv), order_time_missing=0.0 if hk else 1.0,
             **{k: s[k] for k in CATS})
    return r, (None if math.isnan(dist) else round(dist, 2))

async def predict(request):
    try:
        body = await request.json()
        built = [row(s) for s in body["scenarios"][:4]]
        df = pd.DataFrame([b[0] for b in built])[FEATURES]
        preds = MODEL.predict(df)
        return JSONResponse({"results": [{"eta": round(float(p), 1), "distance_km": b[1]} for p, b in zip(preds, built)]})
    except (ValueError, KeyError, TypeError) as e:
        return JSONResponse({"error": f"Invalid input: {e}"}, status_code=400)
    except Exception:
        logging.exception("prediction failed")
        return JSONResponse({"error": "Prediction failed."}, status_code=500)

async def health(request): return JSONResponse({"ok": True, "features": len(FEATURES)})

routes = [Route(p, predict, methods=["POST"]) for p in ("/api/predict", "/predict")] + \
         [Route(p, health) for p in ("/api/health", "/health")]
if (ROOT / "frontend").is_dir():  # locally/Docker the same process serves the page; on Vercel the CDN does
    routes.append(Mount("/", StaticFiles(directory=ROOT / "frontend", html=True)))
app = Starlette(routes=routes)
