import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

df = pd.read_csv("merged_cleaned.csv")

post_counts = df.groupby(["platform", "business"]).size().reset_index(name="post_count")
post_counts["pct"] = (post_counts["post_count"] / len(df) * 100).round(1)
print(" Post count by business:")
print(post_counts.sort_values("post_count", ascending=False).to_string(index=False))

businesses = df["business"].unique()
n = len(businesses)
cols = 3
rows = (n + cols - 1) // cols

fig, axes = plt.subplots(rows, cols, figsize=(18, rows * 4), sharey=False)
axes = axes.flatten()

for i, biz in enumerate(sorted(businesses)):
    ax = axes[i]
    biz_df = df[df["business"] == biz]

    hourly = biz_df.groupby("hour").size()
    all_hours = pd.Series(0, index=range(24))
    all_hours.update(hourly)

    ax.bar(all_hours.index, all_hours.values, color="#1DA1F2", alpha=0.85, width=0.8)
    ax.set_title(f"{biz}\n(TikTok, n={len(biz_df)})", fontsize=9, pad=6)
    ax.set_xlabel("Hour (NPT)", fontsize=8)
    ax.set_ylabel("# Posts", fontsize=8)
    ax.set_xticks(range(0, 24, 3))
    ax.set_xticklabels([f"{h:02d}:00" for h in range(0, 24, 3)], fontsize=7, rotation=30)
    ax.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))
    ax.grid(axis="y", alpha=0.3)
    ax.spines[["top", "right"]].set_visible(False)

for j in range(i + 1, len(axes)):
    axes[j].set_visible(False)

plt.suptitle("Post Count by Hour of Day (NPT) - Per Business (TikTok)", fontsize=13, y=1.01)
plt.tight_layout()
plt.savefig("posting_hours_by_business.png", dpi=150, bbox_inches="tight")
plt.close()
print("\n Chart saved -> posting_hours_by_business.png")

tt_counts = df.groupby("business").size()
dominant_biz   = tt_counts.idxmax()
dominant_count = tt_counts.max()
pct = dominant_count / len(df) * 100
print(f"\n Dominant business: {dominant_biz} = {dominant_count} / {len(df)} posts ({pct:.1f}%)")
if pct > 20:
    print("   One business dominates - consider this when interpreting results.")
else:
    print("   Data is reasonably balanced across businesses.")

summary = df.groupby(["platform", "business"]).agg(
    posts        = ("likes", "count"),
    avg_likes    = ("likes", "mean"),
    avg_comments = ("comments", "mean"),
    avg_shares   = ("shares", "mean"),
    avg_views    = ("views", "mean"),
    avg_saves    = ("saves", "mean"),
    peak_hour    = ("hour", lambda x: x.value_counts().idxmax()),
).round(1).reset_index()

print("\n Per-business summary:")
print(summary.to_string(index=False))

summary.to_csv("business_summary.csv", index=False)
print("\n Saved -> business_summary.csv")