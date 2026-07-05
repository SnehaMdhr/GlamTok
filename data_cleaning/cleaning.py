import pandas as pd
import numpy as np

df = pd.read_csv("finaltiktokdata.csv")
df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_").str.replace("%", "pct")
df["platform"] = "TikTok"

print(f" Loaded {len(df)} TikTok rows")
print(f"   Columns    : {df.columns.tolist()}")
print(f"   Date range : {pd.to_datetime(df['post_date']).min().date()} -> {pd.to_datetime(df['post_date']).max().date()}")
print(f"   Businesses : {sorted(df['business'].unique().tolist())}")

unique_biz = sorted(df["business"].dropna().unique())
business_map = {name: f"Business{i+1}" for i, name in enumerate(unique_biz)}
df["business"] = df["business"].map(business_map)

mapping_df = pd.DataFrame(list(business_map.items()), columns=["original_name","anonymized_name"])
mapping_df.to_csv("business_name_mapping.csv", index=False)
print("\n Business name mapping:")
print(mapping_df.to_string(index=False))

fill_zero_cols = ["views","saves","video_duration_sec","likes","comments","shares",
                  "caption_length","hashtag_count"]
for col in fill_zero_cols:
    if col in df.columns:
        df[col] = df[col].fillna(0)

print(f"\n Shape       : {df.shape}")
print(f"   Columns    : {df.columns.tolist()}")
print(f"   Businesses : {df['business'].value_counts().to_dict()}")
print(f"   Nulls      :\n{df.isnull().sum()}")

df.to_csv("merged_social_data.csv", index=False)
print("\n Saved -> merged_social_data.csv")