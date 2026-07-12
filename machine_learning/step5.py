import pandas as pd
import numpy as np
import json
import joblib
import warnings
warnings.filterwarnings("ignore")

# ══════════════════════════════════════════════════════════════════════════════
# STEP 7.5 - Export model and predict_best_time() function
# Saves the model + scaler, then defines a reusable prediction function
# that returns the top 3 recommended hour × day combinations.
# ══════════════════════════════════════════════════════════════════════════════

# ── Load model artifacts ──────────────────────────────────────────────────────
model  = joblib.load("model_best.joblib")
scaler = joblib.load("scaler.joblib")

with open("feature_cols.json") as f:
    FEATURE_COLS = json.load(f)

with open("best_model_name.txt") as f:
    best_name = f.read().strip()

print(f"📥 Loaded model: {best_name}")
print(f"   Features: {FEATURE_COLS}\n")

# ── Helper: build a feature row for a given hour × day ───────────────────────
FESTIVAL_MONTHS = [3, 10, 11]   # March (Holi), October (Dashain), November (Tihar)
DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

def build_feature_row(
    hour: int,
    day_number: int,      # 0=Mon … 6=Sun
    platform: str,        # "Instagram" or "TikTok"
    followers: int,
    content_type: str,    # "Reel" | "Image" | "Carousel" | "Video"
    month: int = 5,       # default: May (no festival)
    caption_length: int   = 100,
    hashtag_count: int    = 10,
    video_duration_sec: float = 0.0,
    avg_like_rate: float  = 0.03,
    avg_comment_rate: float = 0.005,
    avg_share_rate: float = 0.002,
    avg_like_rate_views: float = 0.04,
    avg_save_rate_views: float = 0.01,
) -> dict:
    row = {}

    # Cyclical time
    row["hour_sin"] = np.sin(hour        * (2 * np.pi / 24))
    row["hour_cos"] = np.cos(hour        * (2 * np.pi / 24))
    row["dow_sin"]  = np.sin(day_number  * (2 * np.pi / 7))
    row["dow_cos"]  = np.cos(day_number  * (2 * np.pi / 7))

    # Calendar flags
    row["is_weekend"]    = int(day_number in [5, 6])
    row["is_festival"]   = int(month in FESTIVAL_MONTHS)
    row["is_lunch_hour"] = int(12 <= hour <= 13)
    row["is_evening"]    = int(18 <= hour <= 20)

    # Content type one-hot
    row["ct_Carousel"] = int(content_type == "Carousel")
    row["ct_Image"]    = int(content_type == "Image")
    row["ct_Reel"]     = int(content_type == "Reel")
    row["ct_Video"]    = int(content_type == "Video")

    # TikTok numeric
    row["caption_length"]    = caption_length
    row["hashtag_count"]     = hashtag_count
    row["video_duration_sec"]= video_duration_sec

    # Engagement rates (use account averages passed in, or typical defaults)
    row["like_rate_followers"]    = avg_like_rate
    row["comment_rate_followers"] = avg_comment_rate
    row["share_rate_followers"]   = avg_share_rate

    if "like_rate_views" in FEATURE_COLS:
        row["like_rate_views"] = avg_like_rate_views if platform == "TikTok" else 0.0
    if "save_rate_views" in FEATURE_COLS:
        row["save_rate_views"] = avg_save_rate_views if platform == "TikTok" else 0.0

    # Account size (log-transformed)
    row["followers_log"] = np.log1p(followers)

    return row


def predict_best_time(
    platform: str,
    followers: int,
    content_type: str,
    month: int = 5,
    top_n: int = 3,
    caption_length: int = 100,
    hashtag_count: int = 10,
    video_duration_sec: float = 30.0,
) -> pd.DataFrame:
    """
    Returns the top_n recommended (hour, day) combinations for a post,
    ranked by predicted engagement_score.

    Parameters
    ----------
    platform        : "Instagram" or "TikTok"
    followers       : account follower count
    content_type    : "Reel" | "Image" | "Carousel" | "Video"
    month           : month of posting (1–12), affects festival flag
    top_n           : number of recommendations to return (default 3)
    caption_length  : estimated caption length in characters
    hashtag_count   : number of hashtags planned
    video_duration_sec : for TikTok videos
    """
    # Validate inputs
    valid_platforms = ["Instagram", "TikTok"]
    valid_content   = {"Instagram": ["Reel","Image","Carousel"],
                       "TikTok": ["Video"]}
    assert platform in valid_platforms, f"platform must be one of {valid_platforms}"
    assert content_type in valid_content[platform], \
        f"For {platform}, content_type must be one of {valid_content[platform]}"

    # Build grid: all 24 hours × 7 days = 168 combinations
    rows = []
    labels = []
    for day in range(7):
        for hour in range(24):
            row = build_feature_row(
                hour=hour, day_number=day, platform=platform,
                followers=followers, content_type=content_type,
                month=month, caption_length=caption_length,
                hashtag_count=hashtag_count,
                video_duration_sec=video_duration_sec,
            )
            rows.append([row.get(c, 0) for c in FEATURE_COLS])
            labels.append((hour, day))

    X_grid   = np.array(rows)
    X_scaled = scaler.transform(X_grid)
    preds    = model.predict(X_scaled)

    results = pd.DataFrame({
        "hour"            : [l[0] for l in labels],
        "day_number"      : [l[1] for l in labels],
        "day_name"        : [DAY_NAMES[l[1]] for l in labels],
        "predicted_score" : preds,
    })

    top = (results
           .sort_values("predicted_score", ascending=False)
           .head(top_n)
           .reset_index(drop=True))

    top.index = top.index + 1   # rank from 1
    top["time_label"] = top["hour"].apply(lambda h: f"{h:02d}:00")
    top["recommendation"] = top.apply(
        lambda r: f"Post on {r['day_name']} at {r['time_label']} NPT", axis=1
    )
    return top[["recommendation", "day_name", "hour", "predicted_score"]]


# ══════════════════════════════════════════════════════════════════════════════
# Demo: run predictions for each platform
# ══════════════════════════════════════════════════════════════════════════════

print("=" * 60)
print("INSTAGRAM - Reel, 5000 followers, posted in May")
print("=" * 60)
ig_recs = predict_best_time(
    platform="Instagram",
    followers=5000,
    content_type="Reel",
    month=5,
    top_n=3
)
print(ig_recs.to_string())

print("\n" + "=" * 60)
print("INSTAGRAM - Image, 50000 followers, posted in October (Dashain)")
print("=" * 60)
ig_recs_festival = predict_best_time(
    platform="Instagram",
    followers=50000,
    content_type="Image",
    month=10,
    top_n=3
)
print(ig_recs_festival.to_string())

print("\n" + "=" * 60)
print("TIKTOK - Video, 15000 followers, 30s video, posted in May")
print("=" * 60)
tt_recs = predict_best_time(
    platform="TikTok",
    followers=15000,
    content_type="Video",
    month=5,
    video_duration_sec=30,
    top_n=3
)
print(tt_recs.to_string())

# ── Save model package ────────────────────────────────────────────────────────
# Everything needed for the API backend
import shutil, os

os.makedirs("model_package", exist_ok=True)
for f in ["model_best.joblib", "scaler.joblib", "feature_cols.json",
          "best_model_name.txt"]:
    if os.path.exists(f):
        shutil.copy(f, f"model_package/{f}")

# Save this predict function as a standalone module
shutil.copy(__file__, "model_package/predictor.py")

print("\n💾 Model package saved → model_package/")
print("   Files: model_best.joblib, scaler.joblib, feature_cols.json, predictor.py")
print("\n✅ To use in your API backend:")
print("   from predictor import predict_best_time")
print("   recs = predict_best_time('Instagram', followers=5000, content_type='Reel')")