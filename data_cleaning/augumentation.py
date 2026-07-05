import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import warnings
warnings.filterwarnings("ignore")

df = pd.read_csv("merged_features.csv")
df["is_synthetic"] = False
print(f" Loaded {len(df)} TikTok rows\n")

SPARSE_THRESHOLD = 15
TARGET_MIN       = 20
NEIGHBOR_WINDOW  = 2
NOISE_PCT        = 0.10

bucket_counts = (
    df.groupby(["hour", "day_number"])
    .size()
    .reset_index(name="count")
)

sparse_buckets = bucket_counts[bucket_counts["count"] < SPARSE_THRESHOLD].copy()
day_names = {0:"Mon",1:"Tue",2:"Wed",3:"Thu",4:"Fri",5:"Sat",6:"Sun"}
sparse_buckets["day_name"] = sparse_buckets["day_number"].map(day_names)
sparse_buckets = sparse_buckets.sort_values(["hour","day_number"]).reset_index(drop=True)

print(f" 6.1  Sparse hourxday buckets (TikTok, count < {SPARSE_THRESHOLD}):")
print(f"   Total sparse buckets : {len(sparse_buckets)}")
print(f"   Hours affected       : {sorted(sparse_buckets['hour'].unique())}")
print(f"   Worst buckets (<= 3 posts):")
worst = sparse_buckets[sparse_buckets["count"] <= 3][["hour","day_name","count"]]
print(worst.to_string(index=False) if len(worst) > 0 else "   None")
print()

tt_hourly = df.groupby("hour").size()
print("   TikTok hourly totals (all days combined):")
print("   " + tt_hourly.to_string().replace("\n","\n   "))
print()

numeric_cols = [
    "hour_sin","hour_cos","dow_sin","dow_cos",
    "like_rate_views","save_rate_views","comment_rate_views","share_rate_views",
    "is_weekend","is_festival","is_lunch_hour","is_evening",
    "caption_length","hashtag_count","video_duration_sec","ct_Video",
    "followers_log","engagement_score"
]
numeric_cols = [c for c in numeric_cols if c in df.columns]

BINARY_COLS = {"ct_Video","is_weekend","is_festival","is_lunch_hour","is_evening"}

rng = np.random.default_rng(seed=42)
synthetic_rows = []

for _, row in sparse_buckets.iterrows():
    h      = row["hour"]
    d      = int(row["day_number"])
    cnt    = int(row["count"])
    needed = max(0, TARGET_MIN - cnt)
    if needed == 0:
        continue

    hour_range = range(max(0, h - NEIGHBOR_WINDOW), min(24, h + NEIGHBOR_WINDOW + 1))
    neighbors  = df[df["hour"].isin(hour_range) & (df["day_number"] == d)]

    if len(neighbors) < 5:
        neighbors = df[df["hour"].isin(hour_range)]

    if len(neighbors) < 3:
        continue

    eng_mean = neighbors["engagement_score"].mean()
    eng_std  = neighbors["engagement_score"].std()
    if np.isnan(eng_std) or eng_std == 0:
        eng_std = eng_mean * 0.1

    for _ in range(needed):
        base    = neighbors.sample(1, random_state=int(rng.integers(1e6))).iloc[0].copy()
        new_eng = max(0, rng.normal(eng_mean, eng_std))
        new_row = base.copy()

        for col in numeric_cols:
            if col == "engagement_score":
                new_row[col] = new_eng
            elif col in BINARY_COLS:
                pass
            else:
                noise = rng.normal(0, abs(float(new_row[col])) * NOISE_PCT)
                new_row[col] = float(new_row[col]) + noise

        new_row["hour"]         = h
        new_row["day_number"]   = d
        new_row["is_synthetic"] = True
        new_row["platform"]     = "TikTok"
        synthetic_rows.append(new_row)

synth_df     = pd.DataFrame(synthetic_rows).reset_index(drop=True)
df_augmented = pd.concat([df, synth_df], ignore_index=True)

print(f" 6.2  Synthetic data generation done")
print(f"   Real rows      : {len(df)}")
print(f"   Synthetic rows : {len(synth_df)}")
print(f"   Total rows     : {len(df_augmented)}")

if len(synth_df) > 0 and "engagement_score" in synth_df.columns:
    print(f"   Synthetic engagement_score stats:")
    print("   " + synth_df["engagement_score"].describe().round(5).to_string().replace("\n","\n   "))
print()

before_counts = df.groupby("hour").size().reindex(range(24), fill_value=0)
after_counts  = df_augmented.groupby("hour").size().reindex(range(24), fill_value=0)
synth_counts  = synth_df.groupby("hour").size().reindex(range(24), fill_value=0) if len(synth_df) > 0 else pd.Series(0, index=range(24))

fig, axes = plt.subplots(1, 2, figsize=(16, 5))

axes[0].bar(before_counts.index, before_counts.values, color="#1DA1F2", alpha=0.85)
axes[0].axhline(SPARSE_THRESHOLD, color="black", linestyle="--", linewidth=1.2,
                label=f"Sparse threshold ({SPARSE_THRESHOLD})")
axes[0].axhline(TARGET_MIN, color="navy", linestyle=":", linewidth=1.2,
                label=f"Target minimum ({TARGET_MIN})")
axes[0].set_title("Before Augmentation\n(TikTok post count by hour)", fontsize=11)
axes[0].set_xlabel("Hour (NPT)")
axes[0].set_ylabel("Post count")
axes[0].set_xticks(range(0, 24, 2))
axes[0].legend(fontsize=8)
axes[0].grid(axis="y", alpha=0.3)
axes[0].spines[["top","right"]].set_visible(False)

axes[1].bar(before_counts.index, before_counts.values, color="#1DA1F2", alpha=0.85, label="Real")
axes[1].bar(synth_counts.index,  synth_counts.values,  color="#90CAF9", alpha=0.85,
            bottom=before_counts.values, label="Synthetic")
axes[1].axhline(TARGET_MIN, color="navy", linestyle=":", linewidth=1.2,
                label=f"Target minimum ({TARGET_MIN})")
axes[1].set_title("After Augmentation\n(TikTok post count by hour)", fontsize=11)
axes[1].set_xlabel("Hour (NPT)")
axes[1].set_ylabel("Post count")
axes[1].set_xticks(range(0, 24, 2))
axes[1].legend(fontsize=8)
axes[1].grid(axis="y", alpha=0.3)
axes[1].spines[["top","right"]].set_visible(False)

plt.tight_layout()
plt.savefig("step6_hourly_counts.png", dpi=150, bbox_inches="tight")
plt.close()
print(" Saved -> step6_hourly_counts.png")

fig, axes = plt.subplots(1, 2, figsize=(14, 5))

sns.histplot(df["engagement_score"].dropna(), bins=40, kde=True, color="#1DA1F2", ax=axes[0])
axes[0].set_title("Engagement Score - Before Augmentation", fontsize=11)
axes[0].set_xlabel("engagement_score")
axes[0].spines[["top","right"]].set_visible(False)

real_mask  = df_augmented["is_synthetic"] == False
synth_mask = df_augmented["is_synthetic"] == True
sns.histplot(df_augmented.loc[real_mask,"engagement_score"].dropna(),
             bins=40, kde=True, color="#1DA1F2", label="Real", ax=axes[1], alpha=0.6)
if synth_mask.sum() > 0:
    sns.histplot(df_augmented.loc[synth_mask,"engagement_score"].dropna(),
                 bins=40, kde=True, color="#90CAF9", label="Synthetic", ax=axes[1], alpha=0.6)
axes[1].set_title("Engagement Score - After Augmentation", fontsize=11)
axes[1].set_xlabel("engagement_score")
axes[1].legend(fontsize=9)
axes[1].spines[["top","right"]].set_visible(False)

plt.tight_layout()
plt.savefig("step6_engagement_distribution.png", dpi=150, bbox_inches="tight")
plt.close()
print(" Saved -> step6_engagement_distribution.png")

validation = pd.DataFrame({
    "before"         : before_counts,
    "after"          : after_counts,
    "synthetic_added": after_counts - before_counts,
    "meets_target"   : after_counts >= TARGET_MIN
})
print(f"\n 6.3  Validation - TikTok samples per hour after augmentation:")
print(validation.to_string())
fails = validation[~validation["meets_target"]]
if len(fails) == 0:
    print(f"\n   All hours now have >= {TARGET_MIN} samples.")
else:
    print(f"\n   {len(fails)} hours still below {TARGET_MIN} (insufficient neighbors):")
    print(fails[["before","after"]].to_string())

df_augmented.to_csv("merged_augmented.csv", index=False)
print(f"\n Saved -> merged_augmented.csv  ({len(df_augmented)} rows)")