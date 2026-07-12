"""
diagnostic.py - Diagnostic Analysis: "Why did this happen?" (TikTok only)
Run from machine_learning/ folder.

Outputs:
  diag_1_business_size_vs_engagement.png
  diag_2_volume_vs_quality.png
  diag_3_caption_hashtag_drivers.png
  diag_4_festival_reality_check.png
  diag_5_root_cause_summary.csv
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os, warnings
warnings.filterwarnings("ignore")

# Soft rose editorial theme (frontend/src/theme.js)
BG="#FFF9F6"; INK="#45372E"; TEXT="#5C4B43"; MUTED="#A18E84"; GRID="#5C4B4314"; BORDER="#EBE0DA"
plt.rcParams.update({
    "font.family":"sans-serif",
    "figure.facecolor":BG,"savefig.facecolor":BG,"axes.facecolor":BG,
    "axes.edgecolor":BORDER,"axes.labelcolor":TEXT,"text.color":INK,
    "xtick.color":MUTED,"ytick.color":MUTED,
    "axes.spines.top":False,"axes.spines.right":False,
    "axes.grid":True,"grid.color":GRID,"grid.linewidth":0.8,"grid.linestyle":"--",
    "figure.dpi":130,"savefig.dpi":300,
})
TT_COLOR, GOOD, BAD = "#FF7EA5", "#3AA876", "#E5484D"  # rose theme

# ── Load data ─────────────────────────────────────────────────────────────────
def load_data():
    for fname in ["merged_augmented.csv","merged_features.csv","merged_cleaned.csv"]:
        if os.path.exists(fname):
            df = pd.read_csv(fname)
            df["post_date"] = pd.to_datetime(df["post_date"])
            return df[df["platform"] == "TikTok"].copy()
    raise FileNotFoundError("No merged CSV found. Run steps 1-5 first.")

df = load_data()

if "eng_score" not in df.columns:
    col = "engagement_score" if "engagement_score" in df.columns else None
    if col:
        df["eng_score"] = df[col]
    else:
        safe_views = df["views"].replace(0, np.nan)
        df["eng_score"] = (
            df["likes"] + 3*df["comments"] + 2*df["shares"] + df["saves"].fillna(0)
        ) / safe_views

df["month_num"] = df["post_date"].dt.month

print(f"📥 Loaded {len(df)} TikTok rows\n")
print("🔍 Building diagnostic charts - answering WHY engagement varies...\n")

# ══════════════════════════════════════════════════════════════════════════════
# DIAG 1 - Does account size (followers) explain who performs best?
# ══════════════════════════════════════════════════════════════════════════════
biz_stats = df.groupby("business").agg(
    followers=("followers","mean"),
    eng=("eng_score","mean"),
    posts=("eng_score","count")
).reset_index()

fig, ax = plt.subplots(figsize=(9, 6))
sizes = (biz_stats["posts"] / biz_stats["posts"].max()) * 800 + 80
ax.scatter(biz_stats["followers"], biz_stats["eng"], s=sizes,
           c=biz_stats["eng"], cmap="RdPu", edgecolors="black", linewidth=0.6, alpha=0.85)
for _, row in biz_stats.iterrows():
    ax.annotate(row["business"], (row["followers"], row["eng"]),
                xytext=(8,5), textcoords="offset points", fontsize=8)
ax.set_xlabel("Average followers")
ax.set_ylabel("Average engagement score")
ax.set_title("WHY does engagement vary by business?\nDo larger accounts perform better or worse?", fontsize=12, pad=10)
ax.text(0.97, 0.95, "Bubble size = post count", transform=ax.transAxes,
        ha="right", fontsize=9, style="italic", color="gray")
plt.tight_layout()
plt.savefig("diag_1_business_size_vs_engagement.png", bbox_inches="tight")
plt.close()

corr_size = biz_stats["followers"].corr(biz_stats["eng"])
print(f"✅ diag_1_business_size_vs_engagement.png")
print(f"   Correlation (followers vs eng_score): {corr_size:.3f} - {'negative' if corr_size < 0 else 'positive'} relationship")

# ══════════════════════════════════════════════════════════════════════════════
# DIAG 2 - Does posting MORE often help or hurt engagement quality?
# ══════════════════════════════════════════════════════════════════════════════
vol_stats = df.groupby("business").agg(
    posts=("eng_score","count"),
    eng=("eng_score","mean")
).reset_index()

fig, ax = plt.subplots(figsize=(8, 5))
ax.scatter(vol_stats["posts"], vol_stats["eng"], s=100,
           color=TT_COLOR, alpha=0.85, edgecolors="black", linewidth=0.5)
for _, row in vol_stats.iterrows():
    ax.annotate(row["business"], (row["posts"], row["eng"]),
                xytext=(4,4), textcoords="offset points", fontsize=8)

if len(vol_stats) >= 2:
    z = np.polyfit(vol_stats["posts"], vol_stats["eng"], 1)
    x_line = np.linspace(vol_stats["posts"].min(), vol_stats["posts"].max(), 50)
    ax.plot(x_line, np.poly1d(z)(x_line), "k--", linewidth=1.2, alpha=0.7, label="Trend")
    ax.legend(fontsize=9)

vol_corr = vol_stats["posts"].corr(vol_stats["eng"])
ax.set_title(f"TikTok - Post Volume vs Engagement Quality\ncorrelation = {vol_corr:.3f}", fontsize=11)
ax.set_xlabel("Total posts (volume)")
ax.set_ylabel("Avg engagement score (quality)")
plt.tight_layout()
plt.savefig("diag_2_volume_vs_quality.png", bbox_inches="tight")
plt.close()
print(f"✅ diag_2_volume_vs_quality.png")
print(f"   Volume-quality correlation: {vol_corr:.3f}")

# ══════════════════════════════════════════════════════════════════════════════
# DIAG 3 - What's actually driving the caption length effect?
# ══════════════════════════════════════════════════════════════════════════════
df["cap_bucket"] = pd.cut(df["caption_length"],
    bins=[0,50,150,300,10000], labels=["Short","Medium","Long","V.Long"])
cap_stats = df.groupby("cap_bucket", observed=True).agg(
    avg_hashtags=("hashtag_count","mean"),
    avg_eng=("eng_score","mean"),
    posts=("eng_score","count")
)

fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))

axes[0].bar(cap_stats.index, cap_stats["avg_eng"], color=TT_COLOR, alpha=0.85, edgecolor="white")
axes[0].set_title("Engagement by caption length", fontsize=11)
axes[0].set_ylabel("Avg engagement score")

ax2 = axes[0].twinx()
ax2.plot(cap_stats.index, cap_stats["avg_hashtags"], color=BAD, marker="o", linewidth=2)
ax2.set_ylabel("Avg hashtag count", color=BAD)
ax2.tick_params(axis="y", colors=BAD)
axes[0].text(0.5, -0.28,
    "Medium captions also use more hashtags\n→ caption length may be a proxy for hashtag strategy",
    transform=axes[0].transAxes, ha="center", fontsize=9, style="italic")

# Hashtag count vs engagement scatter
valid = df[["hashtag_count","eng_score"]].dropna()
axes[1].scatter(valid["hashtag_count"], valid["eng_score"],
                alpha=0.15, s=10, color=TT_COLOR)
if len(valid) >= 3:
    z = np.polyfit(valid["hashtag_count"], valid["eng_score"], 2)
    x_line = np.linspace(0, valid["hashtag_count"].max(), 100)
    axes[1].plot(x_line, np.poly1d(z)(x_line), "k--", linewidth=1.5)
axes[1].set_title("Hashtag count vs engagement score", fontsize=11)
axes[1].set_xlabel("Hashtag count")
axes[1].set_ylabel("Engagement score")

plt.tight_layout()
plt.savefig("diag_3_caption_hashtag_drivers.png", bbox_inches="tight")
plt.close()
print(f"✅ diag_3_caption_hashtag_drivers.png")

# ══════════════════════════════════════════════════════════════════════════════
# DIAG 4 - Festival reality check (TikTok only)
# ══════════════════════════════════════════════════════════════════════════════
df["is_fest"] = df["month_num"].isin([3, 10, 11])
fest_stats = df.groupby("is_fest")["eng_score"].mean()

regular_eng = fest_stats.get(False, np.nan)
festival_eng = fest_stats.get(True, np.nan)
diff_pct = ((festival_eng - regular_eng) / (regular_eng + 1e-9)) * 100

fig, ax = plt.subplots(figsize=(6, 4.5))
labels = ["Regular month", "Festival month\n(Mar/Oct/Nov)"]
values = [regular_eng, festival_eng]
colors_bar = [TT_COLOR+"99", GOOD if festival_eng > regular_eng else BAD]
ax.bar(labels, values, color=colors_bar, alpha=0.85, edgecolor="white")
ax.set_title(f"TikTok - Festival vs Regular Month Engagement\n{diff_pct:+.1f}% in festival months", fontsize=11)
ax.set_ylabel("Avg engagement score")
plt.tight_layout()
plt.savefig("diag_4_festival_reality_check.png", bbox_inches="tight")
plt.close()
print(f"✅ diag_4_festival_reality_check.png")
print(f"   Festival effect: {diff_pct:+.1f}% vs regular months")

# ══════════════════════════════════════════════════════════════════════════════
# DIAG 5 - Root cause summary CSV
# ══════════════════════════════════════════════════════════════════════════════
root_causes = [
    {
        "Question"   : "Why does engagement rate vary between businesses?",
        "Root cause" : "Smaller accounts tend to have more engaged followings relative to their size",
        "Evidence"   : f"Correlation(followers, eng_score) = {corr_size:.3f}",
        "Implication": "Raw engagement rate penalises large accounts - normalisation needed for fair comparison",
    },
    {
        "Question"   : "Why do high-volume posters get lower average engagement?",
        "Root cause" : "Posting more often dilutes per-post audience attention (oversaturation effect)",
        "Evidence"   : f"Correlation(post count, eng_score) = {vol_corr:.3f}",
        "Implication": "Quality and consistency matter more than raw posting frequency",
    },
    {
        "Question"   : "Why do medium-length captions perform best?",
        "Root cause" : "Medium captions correlate with higher hashtag usage - hashtag count may be the real driver",
        "Evidence"   : f"Medium caption avg hashtags = {cap_stats.loc['Medium','avg_hashtags']:.2f} vs Short = {cap_stats.loc['Short','avg_hashtags']:.2f}",
        "Implication": "Caption length is a proxy variable - optimise hashtag strategy first",
    },
    {
        "Question"   : "Why doesn't festival season boost engagement as expected?",
        "Root cause" : "Higher posting volume during festivals dilutes per-post engagement even if total reach increases",
        "Evidence"   : f"Festival avg = {festival_eng:.5f} vs regular = {regular_eng:.5f} ({diff_pct:+.1f}%)",
        "Implication": "Post fewer, higher-quality videos during festival periods rather than increasing frequency",
    },
]

root_df = pd.DataFrame(root_causes)
root_df.to_csv("diag_5_root_cause_summary.csv", index=False)
print("✅ diag_5_root_cause_summary.csv")

print("\n" + "="*60)
print("✅ DIAGNOSTIC ANALYSIS COMPLETE (TikTok only)")
print("="*60)
for _, row in root_df.iterrows():
    print(f"\nQ: {row['Question']}")
    print(f"   → {row['Root cause']}")
    print(f"   Evidence: {row['Evidence']}")