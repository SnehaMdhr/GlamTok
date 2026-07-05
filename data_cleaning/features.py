import pandas as pd
import numpy as np

df = pd.read_csv("merged_cleaned.csv")
print(f" Loaded {len(df)} rows\n")

df["hour_sin"] = np.sin(df["hour"] * (2 * np.pi / 24))
df["hour_cos"] = np.cos(df["hour"] * (2 * np.pi / 24))
df["dow_sin"]  = np.sin(df["day_number"] * (2 * np.pi / 7))
df["dow_cos"]  = np.cos(df["day_number"] * (2 * np.pi / 7))

def sample_hour(hour):
    s = np.sin(hour * (2 * np.pi / 24))
    c = np.cos(hour * (2 * np.pi / 24))
    return f"sin={s:.3f}, cos={c:.3f}"

print(" 5.1 Cyclical encoding done")
print(f"   Sample hour=0  -> {sample_hour(0)}")
print(f"   Sample hour=23 -> {sample_hour(23)}")
print("   (hour 0 and 23 are now close)\n")

safe_views = df["views"].replace(0, np.nan)
df["like_rate_views"]    = df["likes"]    / safe_views
df["save_rate_views"]    = df["saves"]    / safe_views
df["comment_rate_views"] = df["comments"] / safe_views
df["share_rate_views"]   = df["shares"]   / safe_views

print(" 5.2 Engagement rates done")
print(f"   TikTok -> like_rate_views, save_rate_views, comment_rate_views, share_rate_views")
print(f"   like_rate_views stats:\n{df['like_rate_views'].describe().round(4)}\n")

dt = pd.to_datetime(df["post_date"])
df["month_num"] = dt.dt.month
df["is_weekend"]    = df["day_number"].isin([5, 6]).astype(int)
df["is_festival"]   = df["month_num"].isin([3, 10, 11]).astype(int)

def time_bucket(hour):
    if 5 <= hour < 12:  return "Morning"
    elif 12 <= hour < 14: return "Lunch"
    elif 14 <= hour < 18: return "Afternoon"
    elif 18 <= hour < 21: return "Evening"
    else: return "Night"

df["time_of_day"]   = df["hour"].apply(time_bucket)
df["is_lunch_hour"] = df["hour"].between(12, 13).astype(int)
df["is_evening"]    = df["hour"].between(18, 20).astype(int)

print(" 5.3 Nepal calendar features done")
print(f"   Weekend posts : {df['is_weekend'].sum()}")
print(f"   Festival month: {df['is_festival'].sum()}")
print(f"   time_of_day   :\n{df['time_of_day'].value_counts()}\n")

df["ct_Video"] = 1
for col in ["video_duration_sec", "caption_length", "hashtag_count"]:
    if col in df.columns:
        df[col] = df[col].fillna(0)

print(" 5.4 Content type done (all TikTok = Video)")
print(f"   Numeric features kept: video_duration_sec, caption_length, hashtag_count\n")

safe_views = df["views"].replace(0, np.nan)
df["engagement_score"] = (
    df["likes"] + 3 * df["comments"] + 2 * df["shares"] + df["saves"]
) / safe_views

cap = df["engagement_score"].quantile(0.99)
df["engagement_score"] = df["engagement_score"].clip(upper=cap)

print(" 5.5 Engagement score (target) done")
print(f"   Formula: (likes + 3xcomments + 2xshares + saves) / views")
print(f"   Stats:\n{df['engagement_score'].describe().round(5)}")

new_cols = ["hour_sin","hour_cos","dow_sin","dow_cos",
            "like_rate_views","save_rate_views","comment_rate_views","share_rate_views",
            "is_weekend","is_festival","time_of_day","is_lunch_hour","is_evening",
            "ct_Video","engagement_score"]
print(f"\n New features added: {len(new_cols)}")
print(f" Final shape: {df.shape}")

df.to_csv("merged_features.csv", index=False)
print("\n Saved -> merged_features.csv")