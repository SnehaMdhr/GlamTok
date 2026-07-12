"""
ml_service.py - FastAPI microservice
Loads the trained model and serves ML predictions.
Express.js calls this internally; it is NOT exposed to the frontend directly.

Run with:
    pip install fastapi uvicorn
    uvicorn ml_service:app --port 8001 --reload
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pandas as pd
import numpy as np
import joblib
import json
import os
from typing import Optional
from pathlib import Path

# ── Load model artifacts ───────────────────────────────────────────────────────
# ml_service.py is in backend/, model_package is in machine_learning/
BASE_DIR    = Path(__file__).parent.parent / "machine_learning" / "model_package"
model       = joblib.load(BASE_DIR / "model_best.joblib")
scaler      = joblib.load(BASE_DIR / "scaler.joblib")
FEATURE_COLS = json.loads((BASE_DIR / "feature_cols.json").read_text())
MODEL_NAME  = (BASE_DIR / "best_model_name.txt").read_text().strip()

print(f"✅ Loaded model: {MODEL_NAME}")
print(f"   Features: {len(FEATURE_COLS)} columns")

app = FastAPI(title="Engagement Predictor ML Service", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5000"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# ── Constants ─────────────────────────────────────────────────────────────────
DAY_NAMES       = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
FESTIVAL_MONTHS = [3, 10, 11]    # March (Holi), October (Dashain), November (Tihar)
VALID_CONTENT   = {
    "instagram": ["Reel", "Image", "Carousel"],
    "tiktok"   : ["Video"],
}

# ── Feature builder ───────────────────────────────────────────────────────────
def build_feature_row(
    hour: int, day_number: int, platform: str,
    followers: int, content_type: str, month: int,
    caption_length: int = 100, hashtag_count: int = 10,
    video_duration_sec: float = 30.0,
) -> list:
    row = {}
    row["hour_sin"]  = np.sin(hour       * (2 * np.pi / 24))
    row["hour_cos"]  = np.cos(hour       * (2 * np.pi / 24))
    row["dow_sin"]   = np.sin(day_number * (2 * np.pi / 7))
    row["dow_cos"]   = np.cos(day_number * (2 * np.pi / 7))
    row["is_weekend"]    = int(day_number in [5, 6])
    row["is_festival"]   = int(month in FESTIVAL_MONTHS)
    row["is_lunch_hour"] = int(12 <= hour <= 13)
    row["is_evening"]    = int(18 <= hour <= 20)
    row["ct_Carousel"]   = int(content_type == "Carousel")
    row["ct_Image"]      = int(content_type == "Image")
    row["ct_Reel"]       = int(content_type == "Reel")
    row["ct_Video"]      = int(content_type == "Video")
    row["caption_length"]     = caption_length
    row["hashtag_count"]      = hashtag_count
    row["video_duration_sec"] = video_duration_sec if platform == "tiktok" else 0.0
    # Use typical engagement rates as defaults (will be real if passed in)
    row["like_rate_views"]    = 0.04
    row["save_rate_views"]    = 0.01
    row["comment_rate_views"] = 0.005
    row["share_rate_views"]   = 0.002
    row["followers_log"] = np.log1p(followers)
    return [row.get(c, 0) for c in FEATURE_COLS]


def predict_grid(platform: str, followers: int, content_type: str,
                 month: int, caption_length: int, hashtag_count: int,
                 video_duration_sec: float) -> pd.DataFrame:
    """Score all 168 hour×day combinations and return sorted results."""
    rows, labels = [], []
    for day in range(7):
        for hour in range(24):
            rows.append(build_feature_row(
                hour, day, platform, followers, content_type,
                month, caption_length, hashtag_count, video_duration_sec
            ))
            labels.append((hour, day))
    X = scaler.transform(np.array(rows))
    preds = model.predict(X)
    return pd.DataFrame({
        "hour"           : [l[0] for l in labels],
        "day_number"     : [l[1] for l in labels],
        "day_name"       : [DAY_NAMES[l[1]] for l in labels],
        "predicted_score": preds.tolist(),
    })


# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINT 1 - GET /predict/recommendations
# Returns top N posting times for given inputs
# ═══════════════════════════════════════════════════════════════════════════════
@app.get("/predict/recommendations")
def get_recommendations(
    platform     : str = Query(..., description="instagram or tiktok"),
    followers    : int = Query(..., description="Account follower count"),
    content_type : str = Query(..., description="Reel | Image | Carousel | Video"),
    month        : int = Query(default=5, ge=1, le=12),
    top_n        : int = Query(default=3, ge=1, le=10),
    caption_length    : int   = Query(default=100),
    hashtag_count     : int   = Query(default=10),
    video_duration_sec: float = Query(default=30.0),
):
    platform = platform.lower()
    if platform not in VALID_CONTENT:
        raise HTTPException(400, f"platform must be 'tiktok'")
    if content_type not in VALID_CONTENT[platform]:
        raise HTTPException(400,
            f"For {platform}, content_type must be one of {VALID_CONTENT[platform]}")

    grid = predict_grid(platform, followers, content_type, month,
                        caption_length, hashtag_count, video_duration_sec)
    top  = grid.sort_values("predicted_score", ascending=False).head(top_n)

    return {
        "platform"   : platform,
        "followers"  : followers,
        "content_type": content_type,
        "model_used" : MODEL_NAME,
        "recommendations": [
            {
                "rank"           : int(i + 1),
                "day"            : row["day_name"],
                "hour"           : int(row["hour"]),
                "time_label"     : f"{int(row['hour']):02d}:00 NPT",
                "label"          : f"Post on {row['day_name']} at {int(row['hour']):02d}:00 NPT",
                "predicted_score": round(float(row["predicted_score"]), 6),
            }
            for i, (_, row) in enumerate(top.iterrows())
        ]
    }


# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINT 2 - GET /predict/heatmap
# Returns full 24×7 engagement matrix for a platform
# ═══════════════════════════════════════════════════════════════════════════════
@app.get("/predict/heatmap")
def get_heatmap(
    platform     : str = Query(...),
    followers    : int = Query(default=5000),
    content_type : str = Query(default="Reel"),
    month        : int = Query(default=5, ge=1, le=12),
):
    platform = platform.lower()
    if platform not in VALID_CONTENT:
        raise HTTPException(400, f"platform must be 'tiktok'")
    # Auto-correct content_type for TikTok
    if platform == "tiktok":
        content_type = "Video"

    grid = predict_grid(platform, followers, content_type, month,
                        caption_length=100, hashtag_count=10,
                        video_duration_sec=30.0)

    # Pivot to 7×24 matrix (day × hour)
    matrix = grid.pivot(index="day_number", columns="hour", values="predicted_score")
    matrix = matrix.reindex(index=range(7), columns=range(24)).fillna(0)

    return {
        "platform"  : platform,
        "day_labels": DAY_NAMES,
        "hours"     : list(range(24)),
        "matrix"    : matrix.values.tolist(),   # shape: [7][24]
        "max_score" : float(matrix.values.max()),
        "min_score" : float(matrix.values.min()),
    }


@app.get("/health")
def health():
    return {"status": "ok", "model": MODEL_NAME, "features": len(FEATURE_COLS)}