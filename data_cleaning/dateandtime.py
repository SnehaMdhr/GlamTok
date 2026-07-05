import pandas as pd
from datetime import timedelta

df = pd.read_csv("merged_social_data.csv")

df["post_datetime"] = pd.to_datetime(
    df["post_date"].astype(str) + " " + df["post_time"].astype(str),
    format="%Y-%m-%d %H:%M",
    errors="coerce"
)

NPT_OFFSET = timedelta(hours=5, minutes=45)
NPT = pd.DateOffset(hours=5, minutes=45)

df["post_datetime_npt"] = df["post_datetime"].dt.tz_localize(
    "Asia/Kathmandu",
    ambiguous="NaT",
    nonexistent="NaT"
)

bad_hours = df[df["hour"] > 23]
print(f"  Rows with impossible hour values (>23): {len(bad_hours)}")
if len(bad_hours) > 0:
    print(bad_hours[["platform", "business", "post_date", "post_time", "hour"]])

bad_parse = df[df["post_datetime"].isna()]
print(f"  Rows where datetime parsing failed: {len(bad_parse)}")

print("\n Sample output:")
print(df[["platform", "business", "post_date", "post_time", "post_datetime_npt"]].head(5).to_string())

print(f"\n Date range: {df['post_datetime'].min()} -> {df['post_datetime'].max()}")
print(f" Hour distribution:\n{df['hour'].value_counts().sort_index()}")

df.to_csv("merged_with_datetime.csv", index=False)
print("\n Saved -> merged_with_datetime.csv")