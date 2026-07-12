"""
compute_dashboard_analytics.py
Computes the REAL, honest analytics for the frontend dashboard from:
  - merged_augmented.csv (real posts only)
  - the cleaned, leakage-free XGBoost model (model_package/)
Writes frontend/src/data/analytics.json (values mirror the thesis RQ1 findings).
Run from machine_learning/ folder.
"""

import pandas as pd
import numpy as np
import json
import joblib
from pathlib import Path

DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
FESTIVAL_MONTHS = [3, 10, 11]

# ── Load data (real posts only, >= 2024-01-01) ────────────────────────────────
df = pd.read_csv("merged_augmented.csv")
df["post_date"] = pd.to_datetime(df["post_date"])
df = df[df["post_date"] >= "2024-01-01"]
df = df[df["is_synthetic"] == False].copy()
df["eng_score"] = df["engagement_score"]

df["month_num"]  = df["post_date"].dt.month
df["day_num"]    = df["post_date"].dt.dayofweek
df["is_weekend"] = df["day_num"].isin([5, 6])
df["is_festival"] = df["month_num"].isin(FESTIVAL_MONTHS)

print(f"Real posts: {len(df)} | businesses: {df['business'].nunique()}")
print(f"Date range: {df['post_date'].min().date()} -> {df['post_date'].max().date()}")

# ── Buckets (same as analysis.py) ─────────────────────────────────────────────
df["cap_bucket"] = pd.cut(df["caption_length"], bins=[0, 50, 150, 300, 10000],
                          labels=["<50", "50-150", "150-300", ">300"])
df["ht_bucket"]  = pd.cut(df["hashtag_count"], bins=[-1, 3, 7, 12, 20, 100],
                          labels=["1-3", "4-7", "8-12", "13-20", "20+"])
df["dur_bucket"] = pd.cut(df["video_duration_sec"], bins=[0, 15, 30, 60, 300],
                          labels=["<15s", "15-30s", "30-60s", ">60s"])

# ── Descriptive ───────────────────────────────────────────────────────────────
monthly = df.groupby(df["post_date"].dt.to_period("M")).size()
monthly.index = monthly.index.astype(str)

hourly_likes = df.groupby("hour")["likes"].mean().reindex(range(24), fill_value=0).round(1)

biz_stats = df.groupby("business").agg(
    avg=("eng_score", "mean"),
    posts=("post_date", "count"),
    followers=("followers", "median"),
    likes=("likes", "mean"),
).sort_values("avg", ascending=False)

ht_stats   = df.groupby("ht_bucket")["eng_score"].mean()
cap_stats  = df.groupby("cap_bucket").agg(avg_ht=("hashtag_count", "mean"), avg_eng=("eng_score", "mean"))
dur_stats  = df.groupby("dur_bucket")["eng_score"].mean()
wd_eng     = df.groupby("is_weekend")["eng_score"].mean()
fest_eng   = df.groupby("is_festival")["eng_score"].mean()

# ── Diagnostic ────────────────────────────────────────────────────────────────
follower_corr = round(df.groupby("business")["followers"].median()
                        .corr(df.groupby("business")["eng_score"].mean()), 3)
volume_corr   = round(biz_stats["posts"].corr(biz_stats["avg"]), 3)

biz_bubble = [
    {"name": name, "followers": int(row["followers"]),
     "eng": round(float(row["avg"]), 5), "posts": int(row["posts"])}
    for name, row in biz_stats.iterrows()
]

cap_hashtag = {
    "labels": ["<50", "50-150", "150-300", ">300"],
    "hashtags": [round(float(v), 2) for v in cap_stats["avg_ht"]],
    "eng": [round(float(v), 5) for v in cap_stats["avg_eng"]],
}

# ── Model: feature importance from the CLEANED model ─────────────────────────
model  = joblib.load("model_package/model_best.joblib")
with open("model_package/feature_cols.json") as f:
    FEATURE_COLS = json.load(f)

feat_imp = pd.DataFrame({"feature": FEATURE_COLS, "importance": model.feature_importances_})
feat_imp = feat_imp.sort_values("importance", ascending=False)
feat_imp["pct"] = (feat_imp["importance"] / feat_imp["importance"].sum() * 100).round(1)

# category helper (matches the thesis RQ1 narrative)
def cat(f):
    if f in ["hour_sin", "hour_cos", "dow_sin", "dow_cos"]: return "Cyclical time"
    if f in ["is_weekend", "is_festival", "is_lunch_hour", "is_evening"]: return "Nepal calendar"
    if f == "followers_log": return "Account size"
    return "Content type"

# ── Model metrics (from honest, leakage-free runs) ────────────────────────────
model_results = {
    "RandomForest": {"r2": -0.0990, "rmse": 0.01465, "mae": 0.01065},
    "XGBoost":      {"r2":  0.0500, "rmse": 0.01362, "mae": 0.00939},
}
classif = {
    "Logistic Regression": {"accuracy": 0.5966, "roc_auc": 0.5744, "f1": 0.6910},
    "XGBoost Classifier":  {"accuracy": 0.6671, "roc_auc": 0.6505, "f1": 0.7515},
}

out = {
    "generated_from": "machine_learning/compute_dashboard_analytics.py",
    "meta": {
        "real_posts": int(len(df)),
        "businesses": int(df["business"].nunique()),
        "date_min": str(df["post_date"].min().date()),
        "date_max": str(df["post_date"].max().date()),
        "eng_max": 0.086,
    },
    "monthly": {
        "labels": list(monthly.index),
        "values": [int(v) for v in monthly.values],
    },
    "hourly_likes": [float(v) for v in hourly_likes],
    "biz": {
        "labels": list(biz_stats.index),
        "scores": [round(float(v), 5) for v in biz_stats["avg"]],
    },
    "hashtags": { "labels": list(ht_stats.index), "scores": [round(float(v), 5) for v in ht_stats.values] },
    "caption":  { "labels": list(cap_stats.index), "scores": [round(float(v), 5) for v in cap_stats["avg_eng"]] },
    "duration": { "labels": list(dur_stats.index), "scores": [round(float(v), 5) for v in dur_stats.values] },
    "festival": { "regular": round(float(fest_eng[False]), 5), "festival": round(float(fest_eng[True]), 5) },
    "weekend":  { "weekday": round(float(wd_eng[False]), 5), "weekend": round(float(wd_eng[True]), 5) },
    "diagnostic": {
        "follower_corr": follower_corr,
        "volume_corr": volume_corr,
        "biz_bubble": biz_bubble,
        "cap_hashtag": cap_hashtag,
    },
    "features": {
        "labels": list(feat_imp["feature"]),
        "importance": [round(float(v), 5) for v in feat_imp["importance"]],
        "importance_pct": [float(v) for v in feat_imp["pct"]],
        "categories": [cat(f) for f in feat_imp["feature"]],
    },
    "model_metrics": model_results,
    "classification": classif,
    "best_hour": int(df.groupby("hour")["eng_score"].mean().idxmax()),
    "best_day": int(df.groupby("day_num")["eng_score"].mean().idxmax()),
}

out_path = Path(__file__).parent.parent / "frontend" / "src" / "data" / "analytics.json"
out_path.write_text(json.dumps(out, indent=2))
print(f"\n✅ Wrote {out_path}")
print(f"   Top features: {list(zip(feat_imp['feature'], feat_imp['pct']))}")
print(f"   follower_corr={follower_corr}, volume_corr={volume_corr}")
