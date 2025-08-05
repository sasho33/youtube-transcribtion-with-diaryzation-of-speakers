import pandas as pd
from xgboost import XGBClassifier, plot_importance
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix, mean_squared_error
import matplotlib.pyplot as plt
import sys
from pathlib import Path
import numpy as np
import shap
from sklearn.metrics import roc_curve, auc
import joblib

sys.path.append(str(Path(__file__).resolve().parents[2]))
from pipeline.config import TRAINING_MODEL_DATASET

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
    "num_second_order_valuable", "second_order_mma_math_positive", "second_order_mma_math_negative",
    "f1_gender", "f2_gender", "f1_is_current_title_holder", "f2_is_current_title_holder", "f1_winning_streak", "f2_winning_streak",
    
    
]


# 4. Drop rows with missing features (or you can use fillna for some columns if you wish)
X = df[feature_cols].fillna(0)
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

# 8. Evaluation
print("\n[✅] Mean Squared Error:", mean_squared_error(y_test, probs))
print("\n[📊] Classification Report:")
print(classification_report(y_test, y_pred))
print("\n[📉] Confusion Matrix:")
print(confusion_matrix(y_test, y_pred))

# 9. Feature Importances Plot
# 1. Feature Importance Plot
# Bar chart of top features (by importance, gain, or cover).

# Shows which features (e.g., physical stats, prediction counts, streaks) matter most in the model’s decisions.


fig, ax = plt.subplots(figsize=(10, 6))  # Make the plot wider (change width as you like)
plot_importance(
    model,
    max_num_features=25,
    importance_type='gain',
    height=0.5,
    ax=ax
)
plt.title("Top 25 Feature Importances")
plt.tight_layout()

# Format x-axis ticks to 2 decimals
ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{x:.2f}'))
# Format numbers at end of bars
for patch, label in zip(ax.patches, ax.texts):
    # label contains the value
    try:
        value = float(label.get_text())
        label.set_text(f"{value:.2f}")
    except Exception:
        pass  # skip if not a number (just in case)
plt.show()

# 9.2 SHAP Summary Plot
# SHAP (“SHapley Additive exPlanations”) plots explain how much each feature impacts model output.

# Bar plot: Mean absolute SHAP value per feature (importance).

# Beeswarm plot: For each feature, shows how each value increases/decreases the predicted win probability.

explainer = shap.Explainer(model, X_train)
shap_values = explainer(X_test)
shap.plots.bar(shap_values, max_display=15)
shap.plots.beeswarm(shap_values, max_display=15)
plt.show()


# 9.3 
# Receiver Operating Characteristic (ROC) curve.

# Shows tradeoff between True Positive Rate and False Positive Rate.



y_pred_proba = model.predict_proba(X_test)[:,1]
fpr, tpr, _ = roc_curve(y_test, y_pred_proba)
plt.plot(fpr, tpr, label=f"AUC = {auc(fpr, tpr):.2f}")
plt.plot([0, 1], [0, 1], 'k--')
plt.xlabel("False Positive Rate")
plt.ylabel("True Positive Rate")
plt.title("ROC Curve")
plt.legend()
plt.show()


# 9. 5. Probability Distribution Histogram
# Histogram/bar chart of the predicted probabilities (win percent) for test matches.

# Shows how “confident”  model is.
plt.hist(y_pred_proba, bins=20)
plt.xlabel("Predicted Win Probability")
plt.ylabel("Frequency")
plt.title("Distribution of Predicted Probabilities")
plt.show()

# 9. 6. Predicted vs. True Outcome Scatter
# This plot shows the predicted win probability (X-axis) versus the true label (Y-axis) for each match.
# It helps visualize calibration—do high probabilities correspond to more actual wins?
plt.figure(figsize=(8, 4))
plt.scatter(y_pred_proba, y_test, alpha=0.5)
plt.xlabel("Predicted Win Probability")
plt.ylabel("True Outcome (0=loss, 1=win)")
plt.title("Predicted Probability vs. True Outcome")
plt.yticks([0, 1], ["Loss", "Win"])
plt.grid(True, axis='y', linestyle='--', alpha=0.6)
plt.tight_layout()
plt.show()

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
