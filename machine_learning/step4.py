import pandas as pd
import numpy as np
import json
import joblib
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import warnings
warnings.filterwarnings("ignore")

try:
    import shap
except ImportError:
    print("❌ SHAP not installed. Run: pip install shap")
    exit(1)

# ── Load data and best model ──────────────────────────────────────────────────
train_df = pd.read_csv("train_set.csv")
test_df  = pd.read_csv("test_set.csv")

with open("feature_cols.json") as f:
    FEATURE_COLS = json.load(f)

with open("best_model_name.txt") as f:
    best_name = f.read().strip()

TARGET_COL     = "engagement_score"
model          = joblib.load("model_best.joblib")
scaler         = joblib.load("scaler.joblib")

X_train = train_df[FEATURE_COLS].fillna(0).values
X_test  = test_df[FEATURE_COLS].fillna(0).values
X_train_scaled = scaler.transform(X_train)
X_test_scaled  = scaler.transform(X_test)

print(f"📥 Best model: {best_name}")

# ══════════════════════════════════════════════════════════════════════════════
# STEP 7.4a - Built-in feature importance
# ══════════════════════════════════════════════════════════════════════════════

importances = model.feature_importances_
feat_imp_df = pd.DataFrame({
    "feature"   : FEATURE_COLS,
    "importance": importances
}).sort_values("importance", ascending=False).reset_index(drop=True)

print("\n✅ Feature importances (top 15):")
print(feat_imp_df.head(15).to_string(index=False))

# Color-code by feature group
def get_color(feat):
    if feat in ["hour_sin","hour_cos","dow_sin","dow_cos"]:
        return "#1A73E8"   # blue  - time
    elif feat in ["is_weekend","is_festival","is_lunch_hour","is_evening"]:
        return "#34A853"   # green - calendar
    elif feat.startswith("ct_"):
        return "#FBBC04"   # yellow - content type
    elif feat in ["like_rate_followers","comment_rate_followers","share_rate_followers",
                  "like_rate_views","save_rate_views"]:
        return "#EA4335"   # red - engagement rates
    elif feat == "followers_log":
        return "#9334E6"   # purple - account size
    else:
        return "#888888"   # grey - other

colors = [get_color(f) for f in feat_imp_df["feature"]]

fig, ax = plt.subplots(figsize=(10, 7))
bars = ax.barh(feat_imp_df["feature"], feat_imp_df["importance"],
               color=colors, edgecolor="white", height=0.7)
ax.invert_yaxis()
ax.set_xlabel("Feature Importance", fontsize=11)
ax.set_title(f"Feature Importance - {best_name}", fontsize=13, pad=12)
ax.grid(axis="x", alpha=0.3)
ax.spines[["top","right"]].set_visible(False)

# Legend
legend_items = [
    mpatches.Patch(color="#1A73E8", label="Cyclical time (hour/day)"),
    mpatches.Patch(color="#34A853", label="Nepal calendar flags"),
    mpatches.Patch(color="#FBBC04", label="Content type"),
    mpatches.Patch(color="#EA4335", label="Engagement rates"),
    mpatches.Patch(color="#9334E6", label="Account size (followers_log)"),
]
ax.legend(handles=legend_items, loc="lower right", fontsize=8)
plt.tight_layout()
plt.savefig("step7_feature_importance.png", dpi=150, bbox_inches="tight")
plt.close()
print("\n📊 Saved → step7_feature_importance.png")

# ══════════════════════════════════════════════════════════════════════════════
# STEP 7.4b - SHAP values
# SHAP explains each prediction individually - more trustworthy than built-in
# importances which can be biased toward high-cardinality features.
# ══════════════════════════════════════════════════════════════════════════════

print("\n🔍 Computing SHAP values (this may take ~1 min)...")

# Use a sample of 500 test rows for speed
sample_size  = min(500, len(X_test_scaled))
X_shap       = X_test_scaled[:sample_size]
feature_names = FEATURE_COLS

explainer   = shap.TreeExplainer(model)
shap_values = explainer.shap_values(X_shap)

# ── SHAP summary plot (beeswarm) ──────────────────────────────────────────────
plt.figure(figsize=(10, 7))
shap.summary_plot(
    shap_values,
    X_shap,
    feature_names=feature_names,
    show=False,
    plot_size=(10, 7)
)
plt.title(f"SHAP Summary - {best_name}", fontsize=13, pad=10)
plt.tight_layout()
plt.savefig("step7_shap_summary.png", dpi=150, bbox_inches="tight")
plt.close()
print("📊 Saved → step7_shap_summary.png")

# ── SHAP bar plot (mean |SHAP|) ───────────────────────────────────────────────
plt.figure(figsize=(10, 7))
shap.summary_plot(
    shap_values,
    X_shap,
    feature_names=feature_names,
    plot_type="bar",
    show=False,
    plot_size=(10, 7)
)
plt.title(f"Mean |SHAP| - {best_name}", fontsize=13, pad=10)
plt.tight_layout()
plt.savefig("step7_shap_bar.png", dpi=150, bbox_inches="tight")
plt.close()
print("📊 Saved → step7_shap_bar.png")

# ── Key insight printout ──────────────────────────────────────────────────────
mean_shap = np.abs(shap_values).mean(axis=0)
shap_df   = pd.DataFrame({"feature": feature_names, "mean_abs_shap": mean_shap})
shap_df   = shap_df.sort_values("mean_abs_shap", ascending=False).reset_index(drop=True)

print("\n📋 Top 10 features by mean |SHAP|:")
print(shap_df.head(10).to_string(index=False))

# Thesis insight: does account size or timing matter more?
timing_shap  = shap_df[shap_df["feature"].isin(["hour_sin","hour_cos","dow_sin","dow_cos"])]["mean_abs_shap"].sum()
follower_shap = shap_df[shap_df["feature"] == "followers_log"]["mean_abs_shap"].values
follower_shap = follower_shap[0] if len(follower_shap) > 0 else 0

print(f"\n💡 Thesis insight:")
print(f"   Timing features (hour+day) total SHAP : {timing_shap:.6f}")
print(f"   followers_log SHAP                    : {follower_shap:.6f}")
if timing_shap > follower_shap:
    print("   → TIMING matters more than account size ✓ (validates your research question)")
else:
    print("   → Account size matters more than timing → discuss as a nuanced finding")

print("\n💾 All SHAP plots saved.")