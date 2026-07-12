import pandas as pd
import numpy as np
import json

# ── Load augmented feature file ───────────────────────────────────────────────
df = pd.read_csv("merged_augmented.csv")
df["post_date"] = pd.to_datetime(df["post_date"])

# Drop stray rows - keep everything from Jan 2024 onward (3 clean years)
stray = df[df["post_date"] < "2024-01-01"]
if len(stray) > 0:
    print(f"⚠️  Dropping {len(stray)} rows before Jan 2024 (sparse early data)")
df = df[df["post_date"] >= "2024-01-01"].copy()

print(f"📥 Loaded {len(df)} TikTok rows")
print(f"   Date range : Jan 2024 → Jul 2026 (~2.5 years)")
print(f"   Businesses : {df['business'].nunique()}")
print(f"\n   Monthly distribution:")
print("   " + df.groupby(df["post_date"].dt.to_period("M")).size().to_string().replace("\n","\n   "))

# ── Time-based split: train Jan 2024–Mar 2026, test Apr–Jul 2026 ──────────────
SPLIT_DATE = pd.Timestamp("2026-04-01")
train_df = df[df["post_date"] <  SPLIT_DATE].copy()
test_df  = df[df["post_date"] >= SPLIT_DATE].copy()

print(f"\n✅ Split at {SPLIT_DATE.date()}")
print(f"   Train : {len(train_df)} rows  ({len(train_df)/len(df)*100:.1f}%)")
print(f"   Test  : {len(test_df)}  rows  ({len(test_df)/len(df)*100:.1f}%)")

# ── Stratification check ──────────────────────────────────────────────────────
train_biz = set(train_df["business"].unique())
test_biz  = set(test_df["business"].unique())
missing   = train_biz - test_biz
if missing:
    print(f"\n⚠️  Fixing missing businesses in test: {missing}")
    for biz in missing:
        move_idx = train_df[train_df["business"]==biz].sort_values("post_date").tail(max(1,int(len(train_df[train_df["business"]==biz])*0.2))).index
        test_df  = pd.concat([test_df, train_df.loc[move_idx]], ignore_index=True)
        train_df = train_df.drop(index=move_idx)
    print(f"   Fixed. Train: {len(train_df)}, Test: {len(test_df)}")
else:
    print(f"   ✅ All {len(train_biz)} businesses in both sets")

# ── Feature matrix ────────────────────────────────────────────────────────────
FEATURE_COLS = [
    "hour_sin","hour_cos","dow_sin","dow_cos",
    "is_weekend","is_festival","is_lunch_hour","is_evening",
    "ct_Video","caption_length","hashtag_count","video_duration_sec",
    "like_rate_views","save_rate_views","comment_rate_views","share_rate_views",
]
FEATURE_COLS = [c for c in FEATURE_COLS if c in train_df.columns]

# Log-transform followers
train_df["followers_log"] = np.log1p(train_df["followers"])
test_df["followers_log"]  = np.log1p(test_df["followers"])
FEATURE_COLS.append("followers_log")

TARGET_COL = "engagement_score"
train_df = train_df.dropna(subset=[TARGET_COL])
test_df  = test_df.dropna(subset=[TARGET_COL])
train_df[FEATURE_COLS] = train_df[FEATURE_COLS].fillna(0)
test_df[FEATURE_COLS]  = test_df[FEATURE_COLS].fillna(0)

print(f"\n   Features : {len(FEATURE_COLS)} columns")
print(f"   {FEATURE_COLS}")
print(f"\n   Target stats - Train: mean={train_df[TARGET_COL].mean():.5f}, std={train_df[TARGET_COL].std():.5f}")
print(f"   Target stats - Test : mean={test_df[TARGET_COL].mean():.5f}, std={test_df[TARGET_COL].std():.5f}")

train_df.to_csv("train_set.csv", index=False)
test_df.to_csv("test_set.csv",   index=False)
with open("feature_cols.json","w") as f:
    json.dump(FEATURE_COLS, f)

print("\n💾 Saved → train_set.csv, test_set.csv, feature_cols.json")