import pandas as pd
import numpy as np
import json
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import RandomizedSearchCV, KFold
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import joblib
import warnings
warnings.filterwarnings("ignore")

# ── Load splits ───────────────────────────────────────────────────────────────
train_df = pd.read_csv("train_set.csv")
test_df  = pd.read_csv("test_set.csv")

with open("feature_cols.json") as f:
    FEATURE_COLS = json.load(f)

TARGET_COL = "engagement_score"

X_train = train_df[FEATURE_COLS].fillna(0).values
y_train = train_df[TARGET_COL].values
X_test  = test_df[FEATURE_COLS].fillna(0).values
y_test  = test_df[TARGET_COL].values

print(f"📥 Train: {X_train.shape}, Test: {X_test.shape}")

# ── Scale features ────────────────────────────────────────────────────────────
scaler  = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled  = scaler.transform(X_test)

# ══════════════════════════════════════════════════════════════════════════════
# STEP 7.2 - Random Forest baseline with RandomizedSearchCV
# Use time-aware CV: KFold with shuffle=False preserves order within train set.
# ══════════════════════════════════════════════════════════════════════════════

param_dist = {
    "n_estimators"     : [100, 200, 300, 500],
    "max_depth"        : [None, 5, 10, 15, 20],
    "min_samples_split": [2, 5, 10],
    "min_samples_leaf" : [1, 2, 4],
    "max_features"     : ["sqrt", "log2", 0.5],
    "bootstrap"        : [True, False],
}

# KFold with shuffle=False - respects temporal ordering within train
cv = KFold(n_splits=5, shuffle=False)

rf_base = RandomForestRegressor(random_state=42, n_jobs=-1)

print("\n🔍 Running RandomizedSearchCV (50 iterations, 5-fold CV)...")
rf_search = RandomizedSearchCV(
    rf_base,
    param_distributions=param_dist,
    n_iter=50,
    cv=cv,
    scoring="neg_root_mean_squared_error",
    random_state=42,
    n_jobs=-1,
    verbose=1
)
rf_search.fit(X_train_scaled, y_train)

best_rf = rf_search.best_estimator_
print(f"\n✅ Best RF params: {rf_search.best_params_}")

# ── Evaluate ──────────────────────────────────────────────────────────────────
def evaluate(name, model, X_tr, y_tr, X_te, y_te):
    y_pred_train = model.predict(X_tr)
    y_pred_test  = model.predict(X_te)
    results = {
        "model"     : name,
        "train_rmse": np.sqrt(mean_squared_error(y_tr, y_pred_train)),
        "test_rmse" : np.sqrt(mean_squared_error(y_te, y_pred_test)),
        "test_mae"  : mean_absolute_error(y_te, y_pred_test),
        "test_r2"   : r2_score(y_te, y_pred_test),
    }
    print(f"\n📊 {name}")
    for k, v in results.items():
        if k != "model":
            print(f"   {k:12s}: {v:.6f}")
    return results

rf_results = evaluate("RandomForest", best_rf,
                       X_train_scaled, y_train,
                       X_test_scaled,  y_test)

# ── Save ──────────────────────────────────────────────────────────────────────
joblib.dump(best_rf, "model_rf.joblib")
joblib.dump(scaler,  "scaler.joblib")
print("\n💾 Saved → model_rf.joblib, scaler.joblib")

# Save results for comparison in step 7.4
pd.DataFrame([rf_results]).to_csv("model_results.csv", index=False)
print("💾 Saved → model_results.csv")