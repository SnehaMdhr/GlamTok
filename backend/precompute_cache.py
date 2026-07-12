"""
precompute_cache.py
Run this ONCE after training the model (or whenever new data is added).
Precomputes all heatmaps and business stats and saves them to precomputed_cache.json.
Express.js loads this file on startup - no ML calls needed for common requests.

Run with:
    python precompute_cache.py
"""

import pandas as pd
import numpy as np
import joblib
import json
from pathlib import Path

# ── Load model artifacts ───────────────────────────────────────────────────────
# precompute_cache.py runs from backend/, model_package is in machine_learning/
ML_DIR   = Path(__file__).parent.parent / "machine_learning"
BASE_DIR = ML_DIR / "model_package"
model        = joblib.load(BASE_DIR / "model_best.joblib")
scaler       = joblib.load(BASE_DIR / "scaler.joblib")
FEATURE_COLS = json.loads((BASE_DIR / "feature_cols.json").read_text())
MODEL_NAME   = (BASE_DIR / "best_model_name.txt").read_text().strip()

print(f"✅ Loaded model: {MODEL_NAME}\n")

# ── Load cleaned real data for business stats ─────────────────────────────────
df = pd.read_csv(ML_DIR / "merged_augmented.csv")
df = df[df["is_synthetic"] == False].copy()   # only real posts for stats
df["post_date"] = pd.to_datetime(df["post_date"])
df = df[df["post_date"] >= "2025-11-01"]       # drop stray 2023 rows

DAY_NAMES       = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
FESTIVAL_MONTHS = [3, 10, 11]

VALID_COMBOS = [
    ("tiktok", "Video"),
]

# ── Feature builder (same as ml_service.py) ───────────────────────────────────
def build_feature_row(hour, day_number, platform, followers,
                      content_type, month, caption_length=100,
                      hashtag_count=10, video_duration_sec=30.0):
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
    row["like_rate_views"]    = 0.04
    row["save_rate_views"]    = 0.01
    row["comment_rate_views"] = 0.005
    row["share_rate_views"]   = 0.002
    row["followers_log"] = np.log1p(followers)
    return [row.get(c, 0) for c in FEATURE_COLS]


def compute_heatmap(platform, content_type, followers=5000, month=5):
    rows, labels = [], []
    for day in range(7):
        for hour in range(24):
            rows.append(build_feature_row(
                hour, day, platform, followers, content_type, month))
            labels.append((hour, day))
    X     = scaler.transform(np.array(rows))
    preds = model.predict(X)
    matrix = np.zeros((7, 24))
    for i, (hour, day) in enumerate(labels):
        matrix[day][hour] = float(preds[i])
    return {
        "platform"  : platform,
        "content_type": content_type,
        "day_labels": DAY_NAMES,
        "hours"     : list(range(24)),
        "matrix"    : matrix.tolist(),
        "max_score" : float(matrix.max()),
        "min_score" : float(matrix.min()),
    }


# ══════════════════════════════════════════════════════════════════════════════
# 1. Precompute heatmaps for all platform × content_type × month combos
# ══════════════════════════════════════════════════════════════════════════════
cache = {}

print("📊 Precomputing heatmaps...")
MONTHS    = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
FOLLOWERS = 5000   # representative middle-ground account

for platform, content_type in VALID_COMBOS:
    for month in MONTHS:
        key  = f"heatmap:{platform}:{content_type}:{month}"
        data = compute_heatmap(platform, content_type, FOLLOWERS, month)
        cache[key] = data
        print(f"   ✅ {key}")

# ══════════════════════════════════════════════════════════════════════════════
# 2. Precompute business stats from real data
# ══════════════════════════════════════════════════════════════════════════════
print("\n📋 Computing business stats...")

businesses_list = []
for (platform, business), grp in df.groupby(["platform", "business"]):
    followers   = int(grp["followers"].median())
    post_count  = len(grp)
    avg_likes   = round(float(grp["likes"].mean()), 1)
    avg_comments= round(float(grp["comments"].mean()), 1)
    avg_shares  = round(float(grp["shares"].mean()), 1)

    # Peak posting hour
    peak_hour = int(grp["hour"].value_counts().idxmax()) if post_count > 0 else 0

    # Avg engagement score if column exists
    avg_eng = None
    if "engagement_score" in grp.columns:
        avg_eng = round(float(grp["engagement_score"].mean()), 6)

    # Content type breakdown
    ct_counts = grp["content_type"].value_counts().to_dict()

    businesses_list.append({
        "business"       : business,
        "platform"       : platform.lower(),
        "followers"      : followers,
        "post_count"     : post_count,
        "avg_likes"      : avg_likes,
        "avg_comments"   : avg_comments,
        "avg_shares"     : avg_shares,
        "peak_hour"      : peak_hour,
        "peak_hour_label": f"{peak_hour:02d}:00 NPT",
        "avg_engagement_score": avg_eng,
        "content_types"  : ct_counts,
    })

# Sort by follower count descending
businesses_list.sort(key=lambda x: x["followers"], reverse=True)
cache["businesses:all"] = businesses_list
print(f"   ✅ {len(businesses_list)} businesses processed")

# ══════════════════════════════════════════════════════════════════════════════
# 3. Precompute top recommendations for standard follower tiers
# ══════════════════════════════════════════════════════════════════════════════
print("\n🎯 Precomputing recommendations for standard follower tiers...")

FOLLOWER_TIERS = [500, 1000, 5000, 10000, 50000, 100000]

for platform, content_type in VALID_COMBOS:
    for followers in FOLLOWER_TIERS:
        for month in [5, 10]:   # regular month + festival month
            rows, labels = [], []
            for day in range(7):
                for hour in range(24):
                    rows.append(build_feature_row(
                        hour, day, platform, followers, content_type, month))
                    labels.append((hour, day))
            X     = scaler.transform(np.array(rows))
            preds = model.predict(X)

            grid = sorted(
                [{"hour": labels[i][0], "day_number": labels[i][1],
                  "day_name": DAY_NAMES[labels[i][1]], "predicted_score": float(preds[i])}
                 for i in range(len(labels))],
                key=lambda x: x["predicted_score"], reverse=True
            )
            top3 = [
                {
                    "rank"           : i + 1,
                    "day"            : r["day_name"],
                    "hour"           : r["hour"],
                    "time_label"     : f"{r['hour']:02d}:00 NPT",
                    "label"          : f"Post on {r['day_name']} at {r['hour']:02d}:00 NPT",
                    "predicted_score": round(r["predicted_score"], 6),
                }
                for i, r in enumerate(grid[:3])
            ]
            key = f"rec:{platform}:{followers}:{content_type}:{month}"
            cache[key] = {
                "platform": platform, "followers": followers,
                "content_type": content_type, "model_used": MODEL_NAME,
                "recommendations": top3
            }

print(f"   ✅ {len(FOLLOWER_TIERS) * len(VALID_COMBOS) * 2} recommendation combos cached")

# ══════════════════════════════════════════════════════════════════════════════
# 4. Save to disk
# ══════════════════════════════════════════════════════════════════════════════
with open("precomputed_cache.json", "w") as f:
    json.dump(cache, f)

total = len(cache)
print(f"\n💾 Saved {total} entries → precomputed_cache.json")
print(f"   File size: {Path('precomputed_cache.json').stat().st_size / 1024:.1f} KB")
print("\n✅ Done! Start Express with: node server.js")