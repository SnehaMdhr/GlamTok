import pandas as pd
import numpy as np
import json
from sklearn.model_selection import RandomizedSearchCV, KFold
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import joblib
import warnings
warnings.filterwarnings("ignore")

try:
    import xgboost as xgb
    print(f"✅ XGBoost version: {xgb.__version__}")
except ImportError:
    print("❌ XGBoost not installed. Run: pip install xgboost")
    exit(1)

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

# Load the same scaler from RF step
scaler         = joblib.load("scaler.joblib")
X_train_scaled = scaler.transform(X_train)
X_test_scaled  = scaler.transform(X_test)

print(f"📥 Train: {X_train.shape}, Test: {X_test.shape}\n")

# ══════════════════════════════════════════════════════════════════════════════
# STEP 7.3 - XGBoost with RandomizedSearchCV
# XGBoost typically wins on skewed tabular data like engagement metrics.
# ══════════════════════════════════════════════════════════════════════════════

param_dist_xgb = {
    "n_estimators"       : [100, 200, 300, 500],
    "max_depth"          : [3, 4, 5, 6, 8],
    "learning_rate"      : [0.01, 0.05, 0.1, 0.2],
    "subsample"          : [0.6, 0.8, 1.0],
    "colsample_bytree"   : [0.6, 0.8, 1.0],
    "min_child_weight"   : [1, 3, 5],
    "gamma"              : [0, 0.1, 0.2, 0.5],
    "reg_alpha"          : [0, 0.01, 0.1],    # L1
    "reg_lambda"         : [1, 1.5, 2],       # L2
}

cv = KFold(n_splits=5, shuffle=False)

xgb_base = xgb.XGBRegressor(
    objective="reg:squarederror",
    random_state=42,
    n_jobs=-1,
    verbosity=0
)

print("🔍 Running RandomizedSearchCV for XGBoost (50 iterations, 5-fold CV)...")
xgb_search = RandomizedSearchCV(
    xgb_base,
    param_distributions=param_dist_xgb,
    n_iter=50,
    cv=cv,
    scoring="neg_root_mean_squared_error",
    random_state=42,
    n_jobs=-1,
    verbose=1
)
xgb_search.fit(X_train_scaled, y_train)

best_xgb = xgb_search.best_estimator_
print(f"\n✅ Best XGB params: {xgb_search.best_params_}")

# ── Evaluate both models ──────────────────────────────────────────────────────
def evaluate(name, model, X_tr, y_tr, X_te, y_te):
    y_pred_train = model.predict(X_tr)
    y_pred_test  = model.predict(X_te)
    return {
        "model"     : name,
        "train_rmse": np.sqrt(mean_squared_error(y_tr, y_pred_train)),
        "test_rmse" : np.sqrt(mean_squared_error(y_te, y_pred_test)),
        "test_mae"  : mean_absolute_error(y_te, y_pred_test),
        "test_r2"   : r2_score(y_te, y_pred_test),
    }

xgb_results = evaluate("XGBoost", best_xgb,
                        X_train_scaled, y_train,
                        X_test_scaled,  y_test)

# Load RF results for comparison
rf_results_df = pd.read_csv("model_results.csv")
rf_results    = rf_results_df.iloc[0].to_dict()

# ── Side-by-side comparison ───────────────────────────────────────────────────
print("\n" + "="*55)
print(f"{'Metric':<15} {'RandomForest':>18} {'XGBoost':>18}")
print("="*55)
for metric in ["train_rmse", "test_rmse", "test_mae", "test_r2"]:
    rf_val  = rf_results[metric]
    xgb_val = xgb_results[metric]
    winner  = "← RF" if rf_val < xgb_val else "← XGB"
    if metric == "test_r2":
        winner = "← RF" if rf_val > xgb_val else "← XGB"
    print(f"{metric:<15} {rf_val:>18.6f} {xgb_val:>18.6f}  {winner}")
print("="*55)

# Pick the winner
if xgb_results["test_rmse"] <= rf_results["test_rmse"]:
    best_model = best_xgb
    best_name  = "XGBoost"
    print("\n🏆 Winner: XGBoost → will use for feature importance and API export")
else:
    best_model = joblib.load("model_rf.joblib")
    best_name  = "RandomForest"
    print("\n🏆 Winner: RandomForest → will use for feature importance and API export")

# ── Save ──────────────────────────────────────────────────────────────────────
joblib.dump(best_xgb, "model_xgb.joblib")
joblib.dump(best_model, "model_best.joblib")

# Append XGB results to comparison CSV
all_results = pd.concat([
    rf_results_df,
    pd.DataFrame([xgb_results])
], ignore_index=True)
all_results.to_csv("model_results.csv", index=False)

# Save winner name
with open("best_model_name.txt", "w") as f:
    f.write(best_name)

print(f"\n💾 Saved → model_xgb.joblib, model_best.joblib")
print(f"💾 Updated → model_results.csv")