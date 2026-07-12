"""
get_all_metrics.py
Run from machine_learning/ folder.
Gives you: RF baseline, XGBoost, and binary classification metrics.
Paste the full terminal output to your module leader.
"""

import pandas as pd
import numpy as np
import json
import joblib
import os
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    mean_squared_error, mean_absolute_error, r2_score,
    roc_auc_score, accuracy_score, precision_score,
    recall_score, f1_score, confusion_matrix
)
import warnings
warnings.filterwarnings("ignore")

# ── Load data ─────────────────────────────────────────────────────────────────
train_df = pd.read_csv("train_set.csv")
test_df  = pd.read_csv("test_set.csv")

with open("model_package/feature_cols.json") as f:
    FEATURES = json.load(f)

eng_col = "engagement_score" if "engagement_score" in train_df.columns else "eng_score"

X_train = train_df[FEATURES].fillna(0).values
y_train = train_df[eng_col].values
X_test  = test_df[FEATURES].fillna(0).values
y_test  = test_df[eng_col].values

print(f"Train: {len(train_df)} rows | Test: {len(test_df)} rows")
print(f"Features ({len(FEATURES)}): {FEATURES}")
print(f"Target: {eng_col}")
print(f"Train mean: {y_train.mean():.5f} | Test mean: {y_test.mean():.5f}")
print()

scaler = StandardScaler()
Xtr = scaler.fit_transform(X_train)
Xte = scaler.transform(X_test)

null_rmse = np.sqrt(((y_test - y_train.mean())**2).mean())
print(f"Null baseline RMSE (always predict train mean): {null_rmse:.5f}")
print()

# ── 1. Random Forest baseline ─────────────────────────────────────────────────
print("=" * 55)
print("1. RANDOM FOREST (baseline)")
print("=" * 55)
rf = RandomForestRegressor(
    n_estimators=300, max_depth=10,
    min_samples_split=5, min_samples_leaf=2,
    random_state=42, n_jobs=-1
)
rf.fit(Xtr, y_train)
rf_pred = rf.predict(Xte)

rf_rmse = np.sqrt(mean_squared_error(y_test, rf_pred))
rf_mae  = mean_absolute_error(y_test, rf_pred)
rf_r2   = r2_score(y_test, rf_pred)

print(f"R²  : {rf_r2:.4f}  ({rf_r2*100:.2f}%)")
print(f"RMSE: {rf_rmse:.5f}")
print(f"MAE : {rf_mae:.5f}")
print()
rf_fi = sorted(zip(FEATURES, rf.feature_importances_), key=lambda x:-x[1])
print("Feature importance (RF):")
for i,(f,v) in enumerate(rf_fi):
    print(f"  #{i+1:<2} {f:<25} {v*100:.1f}%")

# ── 2. XGBoost (best model) ───────────────────────────────────────────────────
print()
print("=" * 55)
print("2. XGBOOST (best model from model_package)")
print("=" * 55)
model   = joblib.load("model_package/model_best.joblib")
xgb_pred = model.predict(Xte)

xgb_rmse = np.sqrt(mean_squared_error(y_test, xgb_pred))
xgb_mae  = mean_absolute_error(y_test, xgb_pred)
xgb_r2   = r2_score(y_test, xgb_pred)

print(f"R²  : {xgb_r2:.4f}  ({xgb_r2*100:.2f}%)")
print(f"RMSE: {xgb_rmse:.5f}")
print(f"MAE : {xgb_mae:.5f}")
print()
xgb_fi = sorted(zip(FEATURES, model.feature_importances_), key=lambda x:-x[1])
print("Feature importance (XGBoost):")
for i,(f,v) in enumerate(xgb_fi):
    print(f"  #{i+1:<2} {f:<25} {v*100:.1f}%")

# ── 3. Comparison table ───────────────────────────────────────────────────────
print()
print("=" * 55)
print("3. COMPARISON TABLE")
print("=" * 55)
print(f"{'Metric':<8} {'Null baseline':>15} {'Random Forest':>15} {'XGBoost':>12}")
print("-" * 55)
print(f"{'R²':<8} {'0.0000':>15} {rf_r2:>15.4f} {xgb_r2:>12.4f}")
print(f"{'RMSE':<8} {null_rmse:>15.5f} {rf_rmse:>15.5f} {xgb_rmse:>12.5f}")
print(f"{'MAE':<8} {'-':>15} {rf_mae:>15.5f} {xgb_mae:>12.5f}")
winner = "XGBoost" if xgb_r2 >= rf_r2 else "Random Forest"
print(f"\nWinner: {winner}")

# ── 4. Binary classification (high vs low engagement) ────────────────────────
print()
print("=" * 55)
print("4. BINARY CLASSIFICATION (supplementary)")
print("   High engagement = above train median")
print("=" * 55)

threshold   = np.median(y_train)
y_train_cls = (y_train > threshold).astype(int)
y_test_cls  = (y_test  > threshold).astype(int)

print(f"Threshold (train median): {threshold:.6f}")
print(f"Train: {y_train_cls.sum()} high / {(1-y_train_cls).sum()} low")
print(f"Test:  {y_test_cls.sum()} high / {(1-y_test_cls).sum()} low")
print()

# Logistic Regression
lr = LogisticRegression(max_iter=1000, random_state=42)
lr.fit(Xtr, y_train_cls)
lr_pred  = lr.predict(Xte)
lr_proba = lr.predict_proba(Xte)[:,1]

print("Logistic Regression:")
print(f"  Accuracy : {accuracy_score(y_test_cls, lr_pred)*100:.2f}%")
print(f"  ROC-AUC  : {roc_auc_score(y_test_cls, lr_proba)*100:.2f}%")
print(f"  Precision: {precision_score(y_test_cls, lr_pred)*100:.2f}%")
print(f"  Recall   : {recall_score(y_test_cls, lr_pred)*100:.2f}%")
print(f"  F1       : {f1_score(y_test_cls, lr_pred)*100:.2f}%")

# XGBoost classifier
try:
    import xgboost as xgb
    xgb_cls = xgb.XGBClassifier(
        n_estimators=200, max_depth=4, learning_rate=0.05,
        random_state=42, verbosity=0, eval_metric="logloss"
    )
    xgb_cls.fit(Xtr, y_train_cls)
    xgb_cls_pred  = xgb_cls.predict(Xte)
    xgb_cls_proba = xgb_cls.predict_proba(Xte)[:,1]

    print()
    print("XGBoost Classifier:")
    print(f"  Accuracy : {accuracy_score(y_test_cls, xgb_cls_pred)*100:.2f}%")
    print(f"  ROC-AUC  : {roc_auc_score(y_test_cls, xgb_cls_proba)*100:.2f}%")
    print(f"  Precision: {precision_score(y_test_cls, xgb_cls_pred)*100:.2f}%")
    print(f"  Recall   : {recall_score(y_test_cls, xgb_cls_pred)*100:.2f}%")
    print(f"  F1       : {f1_score(y_test_cls, xgb_cls_pred)*100:.2f}%")

    cm = confusion_matrix(y_test_cls, xgb_cls_pred)
    print(f"  Confusion matrix:")
    print(f"    TN={cm[0,0]}  FP={cm[0,1]}")
    print(f"    FN={cm[1,0]}  TP={cm[1,1]}")
except ImportError:
    print("XGBoost not installed - skipping classifier")

print()
print("=" * 55)
print("NOTE: Classification uses leakage-free features only.")
print("These numbers are supplementary - primary metric is R².")
print("=" * 55)