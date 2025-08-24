import pandas as pd
from xgboost import XGBClassifier, plot_importance
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix, mean_squared_error, roc_auc_score, average_precision_score, log_loss
from sklearn.calibration import calibration_curve
import matplotlib.pyplot as plt
import sys
from pathlib import Path
import numpy as np
import shap
from sklearn.metrics import roc_curve, auc
import joblib
import json

sys.path.append(str(Path(__file__).resolve().parents[2]))
from pipeline.config import TRAINING_MODEL_DATASET

OUT = Path("reports"); OUT.mkdir(exist_ok=True)

# 1. Load dataset
df = pd.read_csv(TRAINING_MODEL_DATASET)

# 2. Encode categorical columns for XGBoost
# Gender: male=0, female=1
df['f1_gender'] = df['f1_gender'].map({'male': 0, 'female': 1})
df['f2_gender'] = df['f2_gender'].map({'male': 0, 'female': 1})

# Title Holder: FALSE=0, TRUE=1
df['f1_is_current_title_holder'] = df['f1_is_current_title_holder'].map({'FALSE': 0, 'TRUE': 1}).fillna(0)
df['f2_is_current_title_holder'] = df['f2_is_current_title_holder'].map({'FALSE': 0, 'TRUE': 1}).fillna(0)

# Dynamically select the relevant streak columns for both fighters according to their match arm (left/right)
df['f1_winning_streak'] = np.where(
    df['match_arm'] == 'Right',
    df['f1_right_winning_streak'],
    df['f1_left_winning_streak']
)
df['f2_winning_streak'] = np.where(
    df['match_arm'] == 'Right',
    df['f2_right_winning_streak'],
    df['f2_left_winning_streak']
)

# 3. Choose features (all meaningful numerics, as above)
feature_cols = [
    "f1_age", "f2_age",
    "f1_weight", "f2_weight", "weight_advantage",
    "f1_height", "f2_height", "height_advantage",
    "f1_travel_penalty", "f2_travel_penalty", "domestic_advantage",
    "f1_domestic_win_rate", "f2_domestic_win_rate",
    "f1_transatlantic_win_rate", "f2_transatlantic_win_rate",
    "f1_low_rank_predictions", "f2_low_rank_predictions",
    "f1_high_rank_predictions", "f2_high_rank_predictions",
    "f1_style_combo_success_percent", "f2_style_combo_success_percent",
    "athlete1_style_advantage_rate",
    "num_shared_opponents_value",
    "mma_math_positive", "mma_math_negative",
    "has_head_to_head", "head_to_head_result",
    "second_order_mma_math_difference", "second_order_mma_math_positive", "second_order_mma_math_negative",
    "f1_gender", "f2_gender", "f1_is_current_title_holder", "f2_is_current_title_holder", "f1_winning_streak", "f2_winning_streak",  
]


# 4. Drop rows with missing features (or you can use fillna for some columns if you wish)
# X = df[feature_cols].fillna(0)

X = df[feature_cols]       
y = df.loc[X.index, "label"]



# 5. Train/test split
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.15, random_state=42
)

# 6. Train the model
model = XGBClassifier(
    n_estimators=100,
    max_depth=4,
    learning_rate=0.1,
    random_state=42,
    use_label_encoder=False,
    eval_metric="logloss"
)
model.fit(X_train, y_train)

# 6.1 Save the model
joblib.dump(model, "best_xgboost_model.pkl")
print("Model saved to best_xgboost_model.pkl")

# 7. Predict win probabilities
probs = model.predict_proba(X_test)[:, 1]  # Probability fighter_1 wins
y_pred = (probs >= 0.5).astype(int)

# === Extra metrics for Chapter 6 ===
brier = mean_squared_error(y_test, probs)
ll = log_loss(y_test, probs)
auc_roc = roc_auc_score(y_test, probs)
ap = average_precision_score(y_test, probs)

print("\n[📏 Metrics — test split]")
print(f"Samples: train={len(X_train):,}, test={len(X_test):,}")
print(f"Positives in test (label=1): {int(y_test.sum())}/{len(y_test)} "
      f"({y_test.mean():.1%})")
print(f"AUC-ROC: {auc_roc:.3f} | PR-AUC (AP): {ap:.3f}")
print(f"Brier score (MSE of probs): {brier:.4f} | Log loss: {ll:.4f}")

# Persist metrics for the dissertation

(json.dumps({
    "n_train": int(len(X_train)),
    "n_test": int(len(X_test)),
    "test_pos_rate": float(y_test.mean()),
    "auc_roc": float(auc_roc),
    "pr_auc": float(ap),
    "brier": float(brier),
    "log_loss": float(ll)
}, indent=2))
with open(OUT/"metrics.json", "w") as f:
    json.dump({
        "n_train": int(len(X_train)),
        "n_test": int(len(X_test)),
        "test_pos_rate": float(y_test.mean()),
        "auc_roc": float(auc_roc),
        "pr_auc": float(ap),
        "brier": float(brier),
        "log_loss": float(ll)
    }, f, indent=2)



# 8. Evaluation
print("\n[✅] Mean Squared Error:", mean_squared_error(y_test, probs))
print("\n[📊] Classification Report:")
print(classification_report(y_test, y_pred))
print("\n[📉] Confusion Matrix:")
print(confusion_matrix(y_test, y_pred))

# Predicted probabilities 
y_pred_proba = model.predict_proba(X_test)[:,1]


# === Feature importance (Figure 6.3) ===
# Bar chart of top features (by importance, gain, or cover).

# Shows which features (e.g., physical stats, prediction counts, streaks) matter most in the model’s decisions.

fig, ax = plt.subplots(figsize=(10, 6))
plot_importance(model, max_num_features=25, importance_type='gain', height=0.5, ax=ax)
plt.title("Top 25 Feature Importances")
plt.tight_layout()
plt.savefig(OUT/"fig6_3_feature_importance.png", dpi=300)
plt.show()

# === SHAP (Figures 6.4 & 6.5) ===
# SHAP (“SHapley Additive exPlanations”) plots explain how much each feature impacts model output.

# Bar plot: Mean absolute SHAP value per feature (importance).

# Beeswarm plot: For each feature, shows how each value increases/decreases the predicted win probability.
explainer = shap.TreeExplainer(model)
shap_vals = explainer(X_test)
shap.plots.bar(shap_vals, max_display=15, show=False)
plt.tight_layout(); plt.savefig(OUT/"fig6_4_shap_bar.png", dpi=300); plt.show()
shap.plots.beeswarm(shap_vals, max_display=15, show=False)
plt.tight_layout(); plt.savefig(OUT/"fig6_5_shap_beeswarm.png", dpi=300); plt.show()

# === ROC (Figure 6.1) ===
plt.figure()
fpr, tpr, _ = roc_curve(y_test, y_pred_proba)
plt.plot(fpr, tpr, label=f"AUC = {auc(fpr, tpr):.2f}")
plt.plot([0, 1], [0, 1], 'k--')
plt.xlabel("False Positive Rate"); plt.ylabel("True Positive Rate")
plt.title("ROC Curve (Test)"); plt.legend(); plt.tight_layout()
plt.savefig(OUT/"fig6_1_roc.png", dpi=300); plt.show()

# === Probability histogram (Supplement) ===
# Histogram/bar chart of the predicted probabilities (win percent) for test matches.

# Shows how “confident”  model is.

plt.figure()
plt.hist(y_pred_proba, bins=20)
plt.xlabel("Predicted Win Probability"); plt.ylabel("Frequency")
plt.title("Distribution of Predicted Probabilities (Test)")
plt.tight_layout(); plt.savefig(OUT/"figS_1_pred_hist.png", dpi=300); plt.show()


# === Reliability / Calibration curve (Figure 6.2) ===
prob_true, prob_pred = calibration_curve(y_test, y_pred_proba, n_bins=10, strategy="quantile")
plt.figure(figsize=(5.6, 5))
plt.plot([0, 1], [0, 1], 'k--', label="Perfect")
plt.plot(prob_pred, prob_true, marker='o', label="Model")
plt.xlabel("Predicted probability (bin mean)")
plt.ylabel("Empirical win rate in bin")
plt.title("Reliability Curve (Test)")
plt.legend()
plt.tight_layout()
plt.savefig(OUT/"fig6_2_reliability_curve.png", dpi=300)
plt.show()

# Predicted vs. True Outcome Scatter
# This plot shows the predicted win probability (X-axis) versus the true label (Y-axis) for each match.
# It helps visualize calibration—do high probabilities correspond to more actual wins?
plt.figure(figsize=(6.2, 3.6))
plt.scatter(y_pred_proba, y_test, alpha=0.5)
plt.xlabel("Predicted Win Probability"); plt.ylabel("True Outcome (0/1)")
plt.title("Predicted Probability vs. True Outcome (Test)")
plt.yticks([0, 1], ["Loss", "Win"]); plt.grid(True, axis='y', linestyle='--', alpha=0.6)
plt.tight_layout(); plt.savefig(OUT/"figS_2_pred_vs_true.png", dpi=300); plt.show()

# Sample predictions table (Table 6.S1)
sample_df = pd.DataFrame({
    "true": y_test,
    "pred": (y_pred_proba >= 0.5).astype(int),
    "prob_win": np.round(y_pred_proba, 3),
    "f1_streak": X_test["f1_winning_streak"].values,
    "f2_streak": X_test["f2_winning_streak"].values,
    "f1_high_rank_preds": X_test["f1_high_rank_predictions"].values,
    "f2_high_rank_preds": X_test["f2_high_rank_predictions"].values,
})
sample_df.head(25).to_csv(OUT/"table6S1_sample_predictions.csv", index=False)

# Confusion matrix heatmap (Supplement)
from sklearn.metrics import ConfusionMatrixDisplay
disp = ConfusionMatrixDisplay(confusion_matrix(y_test, (y_pred_proba>=0.5)))
disp.plot(values_format='d', cmap="Blues")
plt.title("Confusion Matrix (Test)")
plt.tight_layout(); plt.savefig(OUT/"figS_3_confusion.png", dpi=300); plt.show()


# 9. 7. Sample Predictions Table
# A simple, human-readable table showing a few test matches with:
#
# True label
#
# Predicted label

# Predicted win probability
y_pred_class = (y_pred_proba >= 0.5).astype(int)
sample_df = pd.DataFrame({
    "True Label": y_test,
    "Predicted Label": y_pred_class,
    "Predicted Win %": np.round(y_pred_proba * 100, 1),
    # Optional: add more columns from X_test for context
    "f1_winning_streak": X_test["f1_winning_streak"].values,
    "f2_winning_streak": X_test["f2_winning_streak"].values,
    "f1_high_rank_predictions": X_test["f1_high_rank_predictions"].values,
    "f2_high_rank_predictions": X_test["f2_high_rank_predictions"].values,
})

print(sample_df.head(10).to_string(index=False))

# 10. Show the first 10 test predictions as example (with win percent)
test_results = X_test.copy()
test_results['true_label'] = y_test
test_results['predicted_label'] = y_pred
test_results['predicted_win_percent'] = (probs * 100).round(1)
print("\n[Sample predictions]")
print(test_results[['true_label', 'predicted_label', 'predicted_win_percent']].head(10))

# --------------------------------------------------------------------------------
# === Ablation study (Table 6.2 + Figures 6.6–6.7) ===
# This block retrains the model once per "feature family", dropping that family,
# then logs metrics and saves a compact report table + bar plots.
from sklearn.metrics import brier_score_loss

def _compute_metrics(y_true, proba):
    """Return dict of evaluation metrics for binary classification."""
    proba = np.clip(proba, 1e-12, 1-1e-12)
    y_pred = (proba >= 0.5).astype(int)
    return {
        "auc": roc_auc_score(y_true, proba),
        "pr_auc": average_precision_score(y_true, proba),
        "brier": brier_score_loss(y_true, proba),
        "logloss": log_loss(y_true, proba),
        "accuracy": (y_pred == y_true).mean(),
    }

# Define feature families (drop all columns in each group together)
FEATURE_FAMILIES = {
    "Expert priors": [
        "f1_high_rank_predictions", "f2_high_rank_predictions",
        "f1_low_rank_predictions", "f2_low_rank_predictions",
    ],
    "Physical advantage": [
        "f1_weight", "f2_weight", "weight_advantage",
        "f1_height", "f2_height", "height_advantage",
        # Optionally include: "f1_age", "f2_age",
    ],
    "Travel & home": [
        "f1_travel_penalty", "f2_travel_penalty", "domestic_advantage",
        "f1_domestic_win_rate", "f2_domestic_win_rate",
        "f1_transatlantic_win_rate", "f2_transatlantic_win_rate",
    ],
    "Streak / momentum": [
        "f1_winning_streak", "f2_winning_streak",
    ],
    "MMA-math & shared opponents": [
        "num_shared_opponents_value",
        "mma_math_positive", "mma_math_negative",
        "second_order_mma_math_difference",
        "second_order_mma_math_positive", "second_order_mma_math_negative",
    ],
    "Head-to-head": [
        "has_head_to_head", "head_to_head_result",
    ],
    "Style features": [
        "f1_style_combo_success_percent", "f2_style_combo_success_percent",
        "athlete1_style_advantage_rate",
    ],
    "Profile flags": [
        "f1_is_current_title_holder", "f2_is_current_title_holder",
        "f1_gender", "f2_gender",
    ],
}

def run_ablation_suite(
    model_params: dict = None,
    families: dict = None,
    out_dir: Path = OUT,
):
    """
    Saves:
      - reports/table6_2_ablation.csv
      - reports/table6_2_ablation.md
      - reports/fig6_6_ablation_auc.png
      - reports/fig6_7_ablation_brier.png
      - reports/appendix_feature_families.csv
    """
    families = families or FEATURE_FAMILIES

    # 1) Baseline on the current full model (already fitted above as `model`)
    try:
        full_proba_test = model.predict_proba(X_test)[:, 1]
    except Exception:
        params = model_params or dict(
            n_estimators=100, max_depth=4, learning_rate=0.1,
            random_state=42, use_label_encoder=False, eval_metric="logloss",
        )
        base_model = XGBClassifier(**params)
        base_model.fit(X_train[feature_cols], y_train)
        full_proba_test = base_model.predict_proba(X_test[feature_cols])[:, 1]
    full_metrics = _compute_metrics(y_test, full_proba_test)

    rows, dropped_registry = [], []

    # 2) Loop over families
    for fam, cols in (families or {}).items():
        cols_to_drop = [c for c in cols if c in feature_cols]
        dropped_registry.append((fam, cols_to_drop))
        if not cols_to_drop:
            # Nothing to drop; record a no-op row
            rows.append({
                "family": fam,
                "auc_full": full_metrics["auc"], "auc_ablated": full_metrics["auc"],
                "delta_auc": full_metrics["auc"] - full_metrics["auc"],
                "pr_auc_full": full_metrics["pr_auc"], "pr_auc_ablated": full_metrics["pr_auc"],
                "delta_pr_auc": full_metrics["pr_auc"] - full_metrics["pr_auc"],
                "brier_full": full_metrics["brier"], "brier_ablated": full_metrics["brier"],
                "delta_brier": full_metrics["brier"] - full_metrics["brier"],
                "logloss_full": full_metrics["logloss"], "logloss_ablated": full_metrics["logloss"],
                "delta_logloss": full_metrics["logloss"] - full_metrics["logloss"],
            })
            continue

        ablated_cols = [c for c in feature_cols if c not in cols_to_drop]
        params = model_params or dict(
            n_estimators=100, max_depth=4, learning_rate=0.1,
            random_state=42, use_label_encoder=False, eval_metric="logloss",
        )
        m = XGBClassifier(**params)
        m.fit(X_train[ablated_cols], y_train)
        proba_test = m.predict_proba(X_test[ablated_cols])[:, 1]
        met = _compute_metrics(y_test, proba_test)

        rows.append({
            "family": fam,
            "auc_full": full_metrics["auc"], "auc_ablated": met["auc"],
            "delta_auc": full_metrics["auc"] - met["auc"],              # + means removal hurt
            "pr_auc_full": full_metrics["pr_auc"], "pr_auc_ablated": met["pr_auc"],
            "delta_pr_auc": full_metrics["pr_auc"] - met["pr_auc"],      # + means removal hurt
            "brier_full": full_metrics["brier"], "brier_ablated": met["brier"],
            "delta_brier": met["brier"] - full_metrics["brier"],         # + means removal hurt
            "logloss_full": full_metrics["logloss"], "logloss_ablated": met["logloss"],
            "delta_logloss": met["logloss"] - full_metrics["logloss"],   # + means removal hurt
        })

    # 3) Save tables
    df_ablate = pd.DataFrame(rows).sort_values("delta_auc", ascending=False)
    df_ablate.to_csv(out_dir / "table6_2_ablation.csv", index=False)
    (out_dir / "table6_2_ablation.md").write_text(
        df_ablate.to_markdown(index=False, floatfmt=".4f"), encoding="utf-8"
    )
    pd.DataFrame(
        [{"family": fam, "dropped_cols": ", ".join(cols)} for fam, cols in dropped_registry]
    ).to_csv(out_dir / "appendix_feature_families.csv", index=False)

    # 4) Save bar charts
    plt.figure(figsize=(8, 5))
    plt.bar(df_ablate["family"], df_ablate["delta_auc"])
    plt.ylabel("ΔAUC = AUC(full) − AUC(ablated)")
    plt.title("Ablation: drop in AUC (higher = more important)")
    plt.xticks(rotation=30, ha="right")
    plt.tight_layout()
    plt.savefig(out_dir / "fig6_6_ablation_auc.png", dpi=300)
    plt.close()

    plt.figure(figsize=(8, 5))
    plt.bar(df_ablate["family"], df_ablate["delta_brier"])
    plt.ylabel("ΔBrier = Brier(ablated) − Brier(full)")
    plt.title("Ablation: increase in Brier (higher = worse)")
    plt.xticks(rotation=30, ha="right")
    plt.tight_layout()
    plt.savefig(out_dir / "fig6_7_ablation_brier.png", dpi=300)
    plt.close()

    print("[Ablation] Saved:",
          out_dir / "table6_2_ablation.csv",
          out_dir / "table6_2_ablation.md",
          out_dir / "appendix_feature_families.csv",
          out_dir / "fig6_6_ablation_auc.png",
          out_dir / "fig6_7_ablation_brier.png", sep="\n - ")

# === Calibration (Figure 6.8 + Table 6.3) — CV-based & method comparison ===
from sklearn.calibration import calibration_curve, CalibratedClassifierCV
from sklearn.model_selection import StratifiedKFold
from sklearn.base import clone
from sklearn.metrics import log_loss, roc_auc_score, average_precision_score, brier_score_loss

def _compute_metrics(y_true, proba):
    proba = np.clip(np.asarray(proba), 1e-12, 1-1e-12)
    y_pred = (proba >= 0.5).astype(int)
    return {
        "auc": roc_auc_score(y_true, proba),
        "pr_auc": average_precision_score(y_true, proba),
        "brier": brier_score_loss(y_true, proba),
        "logloss": log_loss(y_true, proba),
        "accuracy": (y_pred == y_true).mean(),
    }

def _ece(y_true, proba, n_bins=10, strategy="quantile"):
    y_true = np.asarray(y_true).astype(float)
    proba = np.asarray(proba).astype(float)
    edges = (np.quantile(proba, np.linspace(0,1,n_bins+1)) if strategy=="quantile"
             else np.linspace(0,1,n_bins+1))
    edges[0], edges[-1] = 0.0, 1.0
    ece = 0.0
    for i in range(n_bins):
        mask = (proba >= edges[i]) & (proba <= edges[i+1] if i==n_bins-1 else proba < edges[i+1])
        if not np.any(mask): continue
        conf, acc = proba[mask].mean(), y_true[mask].mean()
        ece += mask.mean() * abs(acc - conf)
    return float(ece)

def run_calibration_compare(out_dir: Path = OUT, n_bins: int = 10, cv_splits: int = 5, seed: int = 42):
    # 1) Uncalibrated baseline on test
    base = clone(model)  # same params as trained model
    base.fit(X_train[feature_cols], y_train)
    proba_before = base.predict_proba(X_test[feature_cols])[:, 1]
    met_before = _compute_metrics(y_test, proba_before)
    met_before["ece"] = _ece(y_test, proba_before, n_bins=n_bins)

    # 2) Calibrate with CV on the training set — compare isotonic vs sigmoid
    results = []
    for method in ("isotonic", "sigmoid"):
        est = clone(model)
        cal = CalibratedClassifierCV(estimator=est, method=method,
                                     cv=StratifiedKFold(n_splits=cv_splits, shuffle=True, random_state=seed))
        cal.fit(X_train[feature_cols], y_train)
        proba_after = cal.predict_proba(X_test[feature_cols])[:, 1]
        met_after = _compute_metrics(y_test, proba_after)
        met_after["ece"] = _ece(y_test, proba_after, n_bins=n_bins)
        results.append((method, proba_after, met_after))

    # 3) Pick best calibrated variant by Brier, then ECE
    best = sorted(results, key=lambda x: (x[2]["brier"], x[2]["ece"]))[0]
    best_method, proba_after, met_after = best

    # 4) Reliability diagram (before vs best)
    prob_b, frac_b = calibration_curve(y_test, proba_before, n_bins=n_bins, strategy="quantile")
    prob_a, frac_a = calibration_curve(y_test, proba_after,  n_bins=n_bins, strategy="quantile")

    plt.figure(figsize=(6.6, 6.2))
    plt.plot([0,1],[0,1], "--", linewidth=1)
    plt.plot(prob_b, frac_b, marker="o", label="Before (uncalibrated)")
    plt.plot(prob_a, frac_a, marker="o", label=f"After ({best_method})")
    plt.xlabel("Predicted probability"); plt.ylabel("Observed frequency")
    plt.title("Reliability diagram — before vs. after calibration")
    plt.legend(); plt.tight_layout()
    plt.savefig(out_dir / "fig6_8_calibration_before_after.png", dpi=300)
    plt.close()

    # 5) Save table (before + both methods)
    rows = [{"variant": "Before (uncalibrated)", **met_before}]
    for method, _, met in results:
        rows.append({"variant": f"After ({method})", **met})
    pd.DataFrame(rows).to_csv(out_dir / "table6_3_calibration.csv", index=False)

    print("[Calibration] Best method:", best_method)
    print(pd.DataFrame(rows).round(6).to_string(index=False))
    return best_method

if __name__ == "__main__":
    run_calibration_compare()