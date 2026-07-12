"""
classification_metrics.py - High/Low Engagement Classifier
A supplementary script that converts the regression target into a binary
classification problem so you get real ROC-AUC and accuracy percentages.

This does NOT replace your regression model - it's an additional validation
metric for your thesis report. Your main pipeline (API, dashboard) is unaffected.

Run from machine_learning/ folder, after step 5 (features) and step 7.1 (split) exist.

Outputs:
  classif_1_roc_curve.png
  classif_2_confusion_matrix.png
  classif_metrics.csv
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (roc_auc_score, roc_curve, accuracy_score,
                              precision_score, recall_score, f1_score, confusion_matrix)
import json, os, warnings
warnings.filterwarnings("ignore")

try:
    import xgboost as xgb
    HAS_XGB = True
except ImportError:
    HAS_XGB = False

# Soft rose editorial theme (frontend/src/theme.js)
BG="#FFF9F6"; INK="#45372E"; TEXT="#5C4B43"; MUTED="#A18E84"; GRID="#5C4B4314"; BORDER="#EBE0DA"
plt.rcParams.update({
    "font.family":"sans-serif",
    "figure.facecolor":BG,"savefig.facecolor":BG,"axes.facecolor":BG,
    "axes.edgecolor":BORDER,"axes.labelcolor":TEXT,"text.color":INK,
    "xtick.color":MUTED,"ytick.color":MUTED,
    "axes.spines.top":False,"axes.spines.right":False,
    "figure.dpi":130,"savefig.dpi":300,
})
GOOD, BAD, ACCENT = "#3AA876", "#E5484D", "#FF7EA5"  # rose theme

# ── Load train/test splits from step 7.1 ──────────────────────────────────────
if not (os.path.exists("train_set.csv") and os.path.exists("test_set.csv")):
    raise FileNotFoundError("train_set.csv / test_set.csv not found. Run step 7.1 (split) first.")

train_df = pd.read_csv("train_set.csv")
test_df  = pd.read_csv("test_set.csv")

with open("feature_cols.json") as f:
    FEATURE_COLS = json.load(f)

eng_col = "engagement_score" if "engagement_score" in train_df.columns else "eng_score"
print(f"📥 Train: {len(train_df)} rows, Test: {len(test_df)} rows")
print(f"   Using target column: {eng_col}\n")

# ── LEAKAGE CHECK ──────────────────────────────────────────────────────────────
# engagement_score = (likes + 3*comments + 2*shares) / followers  (or /views for TikTok)
# Features like like_rate_followers = likes/followers are near-identical to the target
# itself - training on them gives artificially perfect accuracy (data leakage), not a
# real model. Remove any feature that's a direct component of the target formula.
LEAKY_FEATURES = [
    "like_rate_followers", "comment_rate_followers", "share_rate_followers",
    "like_rate_views", "save_rate_views",
]
removed = [c for c in LEAKY_FEATURES if c in FEATURE_COLS]
if removed:
    print(f"⚠️  Removing leaky features (near-identical to target): {removed}")
    FEATURE_COLS = [c for c in FEATURE_COLS if c not in LEAKY_FEATURES]
print(f"   Clean feature set ({len(FEATURE_COLS)} cols): {FEATURE_COLS}\n")

# ══════════════════════════════════════════════════════════════════════════════
# STEP 1 - Convert continuous engagement_score into binary label
# High engagement = above the TRAIN median (so test set isn't used to set the threshold)
# ══════════════════════════════════════════════════════════════════════════════
threshold = train_df[eng_col].median()
train_df["is_high_engagement"] = (train_df[eng_col] > threshold).astype(int)
test_df["is_high_engagement"]  = (test_df[eng_col]  > threshold).astype(int)

print(f"✅ Threshold (train median): {threshold:.6f}")
print(f"   Train class balance: {train_df['is_high_engagement'].value_counts().to_dict()}")
print(f"   Test class balance:  {test_df['is_high_engagement'].value_counts().to_dict()}\n")

X_train = train_df[FEATURE_COLS].fillna(0).values
y_train = train_df["is_high_engagement"].values
X_test  = test_df[FEATURE_COLS].fillna(0).values
y_test  = test_df["is_high_engagement"].values

scaler = StandardScaler()
X_train_s = scaler.fit_transform(X_train)
X_test_s  = scaler.transform(X_test)

# ══════════════════════════════════════════════════════════════════════════════
# STEP 2 - Train classifiers (Logistic Regression baseline + XGBoost if available)
# ══════════════════════════════════════════════════════════════════════════════
results = {}

print("🔍 Training Logistic Regression...")
log_reg = LogisticRegression(max_iter=1000, random_state=42)
log_reg.fit(X_train_s, y_train)
y_pred_lr  = log_reg.predict(X_test_s)
y_proba_lr = log_reg.predict_proba(X_test_s)[:, 1]

results["Logistic Regression"] = {
    "accuracy" : accuracy_score(y_test, y_pred_lr),
    "roc_auc"  : roc_auc_score(y_test, y_proba_lr),
    "precision": precision_score(y_test, y_pred_lr),
    "recall"   : recall_score(y_test, y_pred_lr),
    "f1"       : f1_score(y_test, y_pred_lr),
    "y_proba"  : y_proba_lr,
}

if HAS_XGB:
    print("🔍 Training XGBoost Classifier...")
    xgb_clf = xgb.XGBClassifier(n_estimators=200, max_depth=5, learning_rate=0.1,
                                  random_state=42, eval_metric="logloss")
    xgb_clf.fit(X_train_s, y_train)
    y_pred_xgb  = xgb_clf.predict(X_test_s)
    y_proba_xgb = xgb_clf.predict_proba(X_test_s)[:, 1]

    results["XGBoost Classifier"] = {
        "accuracy" : accuracy_score(y_test, y_pred_xgb),
        "roc_auc"  : roc_auc_score(y_test, y_proba_xgb),
        "precision": precision_score(y_test, y_pred_xgb),
        "recall"   : recall_score(y_test, y_pred_xgb),
        "f1"       : f1_score(y_test, y_pred_xgb),
        "y_proba"  : y_proba_xgb,
    }

# ── Print results clearly ─────────────────────────────────────────────────────
print("\n" + "="*60)
print("CLASSIFICATION METRICS (supplementary to regression model)")
print("="*60)
for name, r in results.items():
    print(f"\n{name}:")
    print(f"   Accuracy : {r['accuracy']*100:.2f}%")
    print(f"   ROC-AUC  : {r['roc_auc']*100:.2f}%")
    print(f"   Precision: {r['precision']*100:.2f}%")
    print(f"   Recall   : {r['recall']*100:.2f}%")
    print(f"   F1-score : {r['f1']*100:.2f}%")

best_name = max(results, key=lambda k: results[k]["roc_auc"])
print(f"\n🏆 Best model: {best_name} (ROC-AUC = {results[best_name]['roc_auc']*100:.2f}%)")

# ══════════════════════════════════════════════════════════════════════════════
# STEP 3 - ROC curve plot
# ══════════════════════════════════════════════════════════════════════════════
from matplotlib.colors import LinearSegmentedColormap
DEEP = "#B33E5D"
ROSE_CMAP = LinearSegmentedColormap.from_list(
    "rose", ["#FFF5F7", "#FFD9E6", "#FF9DBB", "#FF7EA5", "#B33E5D"])

def style_ax(ax):
    ax.set_facecolor(BG)
    for s in ["top", "right"]:
        ax.spines[s].set_visible(False)
    ax.tick_params(colors=MUTED)

fig, ax = plt.subplots(figsize=(6, 6))
style_ax(ax)
colors = [ACCENT, GOOD]
for (name, r), color in zip(results.items(), colors):
    fpr, tpr, _ = roc_curve(y_test, r["y_proba"])
    ax.plot(fpr, tpr, label=f"{name} (AUC={r['roc_auc']*100:.1f}%)", color=color, linewidth=2)
ax.plot([0,1], [0,1], "--", linewidth=1, label="Random guess (AUC=50%)", alpha=0.6, color=MUTED)
ax.set_xlabel("False Positive Rate")
ax.set_ylabel("True Positive Rate")
ax.set_title("ROC Curve - High vs Low Engagement Classifier", fontsize=12, pad=10)
ax.legend(loc="lower right", fontsize=9, framealpha=0.9, edgecolor=BORDER)
plt.tight_layout()
plt.savefig("classif_1_roc_curve.png", bbox_inches="tight")
plt.close()
print("\n✅ classif_1_roc_curve.png")

# ══════════════════════════════════════════════════════════════════════════════
# STEP 4 - Confusion matrix for best model (rose ramp, no default purple)
# ══════════════════════════════════════════════════════════════════════════════
best_pred = (results[best_name]["y_proba"] > 0.5).astype(int)
cm = confusion_matrix(y_test, best_pred)

fig, ax = plt.subplots(figsize=(5, 4.5))
style_ax(ax)
im = ax.imshow(cm, cmap=ROSE_CMAP, vmin=0, vmax=cm.max())
ax.set_xticks([0,1]); ax.set_yticks([0,1])
ax.set_xticklabels(["Low", "High"]); ax.set_yticklabels(["Low", "High"])
ax.set_xlabel("Predicted")
ax.set_ylabel("Actual")
ax.set_title(f"Confusion Matrix - {best_name}", fontsize=12, pad=10)
for i in range(2):
    for j in range(2):
        dark = cm[i,j] > cm.max()/2
        ax.text(j, i, cm[i,j], ha="center", va="center",
                color="#FFFFFF" if dark else TEXT, fontsize=14, fontweight="bold")
plt.tight_layout()
plt.savefig("classif_2_confusion_matrix.png", bbox_inches="tight")
plt.close()
print("✅ classif_2_confusion_matrix.png")

# ══════════════════════════════════════════════════════════════════════════════
# STEP 5 - Combined ROC + Confusion Matrix (single figure, side by side)
# ══════════════════════════════════════════════════════════════════════════════
fig, axes = plt.subplots(1, 2, figsize=(12, 5.5))
for ax in axes:
    style_ax(ax)

ax = axes[0]
for (name, r), color in zip(results.items(), colors):
    fpr, tpr, _ = roc_curve(y_test, r["y_proba"])
    ax.plot(fpr, tpr, label=f"{name} (AUC={r['roc_auc']*100:.1f}%)", color=color, linewidth=2)
ax.plot([0,1], [0,1], "--", linewidth=1, label="Random guess (AUC=50%)", alpha=0.6, color=MUTED)
ax.set_xlabel("False Positive Rate")
ax.set_ylabel("True Positive Rate")
ax.set_title("ROC Curve - High vs Low Engagement Classifier", fontsize=12, pad=10)
ax.legend(loc="lower right", fontsize=8, framealpha=0.9, edgecolor=BORDER)

ax = axes[1]
im = ax.imshow(cm, cmap=ROSE_CMAP, vmin=0, vmax=cm.max())
ax.set_xticks([0,1]); ax.set_yticks([0,1])
ax.set_xticklabels(["Low", "High"]); ax.set_yticklabels(["Low", "High"])
ax.set_xlabel("Predicted")
ax.set_ylabel("Actual")
ax.set_title(f"Confusion Matrix - {best_name}", fontsize=12, pad=10)
for i in range(2):
    for j in range(2):
        dark = cm[i,j] > cm.max()/2
        ax.text(j, i, cm[i,j], ha="center", va="center",
                color="#FFFFFF" if dark else TEXT, fontsize=14, fontweight="bold")

plt.tight_layout()
plt.savefig("classif_3_roc_confusion_combined.png", bbox_inches="tight")
plt.close()
print("✅ classif_3_roc_confusion_combined.png")

# ── Save metrics table ────────────────────────────────────────────────────────
metrics_df = pd.DataFrame([
    {"model": name, **{k: v for k, v in r.items() if k != "y_proba"}}
    for name, r in results.items()
])
metrics_df.to_csv("classif_metrics.csv", index=False)
print("✅ classif_metrics.csv")

print("\n" + "="*60)
print(f"📌 FOR YOUR THESIS: {best_name} ROC-AUC = {results[best_name]['roc_auc']*100:.1f}%")
print(f"   Accuracy = {results[best_name]['accuracy']*100:.1f}%")
print("="*60)