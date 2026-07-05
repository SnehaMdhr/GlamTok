import pandas as pd

df = pd.read_csv("merged_with_datetime.csv")
original_count = len(df)
print(f" Loaded {original_count} rows")

ghost_mask = (df["likes"] == 0) & (df["comments"] == 0) & (df["shares"] == 0)
ghost_count = ghost_mask.sum()
df = df[~ghost_mask].copy()
print(f"  Removed {ghost_count} ghost posts (0 likes & 0 comments & 0 shares)")

engagement_cols = ["likes", "comments", "shares", "views", "saves"]
engagement_cols = [c for c in engagement_cols if c in df.columns]

def cap_outliers(series, multiplier=3):
    """Return upper cap value using IQR method."""
    Q1 = series.quantile(0.25)
    Q3 = series.quantile(0.75)
    IQR = Q3 - Q1
    upper = Q3 + multiplier * IQR
    return upper

outlier_summary = {}
for col in engagement_cols:
    df[col] = df[col].astype(float)

for col in engagement_cols:
    before = len(df)
    for platform in df["platform"].unique():
        mask = df["platform"] == platform
        cap = cap_outliers(df.loc[mask, col].fillna(0))
        clipped = (df.loc[mask, col] > cap).sum()
        df.loc[mask, col] = df.loc[mask, col].clip(upper=cap)
        outlier_summary[f"{platform}_{col}_cap"] = round(cap, 0)
        if clipped > 0:
            print(f"   {platform}: clipped {clipped} rows in '{col}' (cap={cap:,.0f})")

print(f"\n Rows remaining: {len(df)} (removed {original_count - len(df)} total)")
print("\n Engagement stats after cleaning:")
print(df[engagement_cols].describe().round(1).to_string())

df.to_csv("merged_cleaned.csv", index=False)
print("\n Saved -> merged_cleaned.csv")