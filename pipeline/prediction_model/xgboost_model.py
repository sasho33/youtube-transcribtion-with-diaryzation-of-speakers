import pandas as pd
from xgboost import XGBClassifier, plot_importance
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix, mean_squared_error
import matplotlib.pyplot as plt
import sys
from pathlib import Path

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
    "f1_gender", "f2_gender", "f1_is_current_title_holder", "f2_is_current_title_holder"
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
plot_importance(model, max_num_features=20, importance_type='gain', height=0.5)
plt.title("Top 20 Feature Importances")
plt.tight_layout()
plt.show()

# 10. Show the first 10 test predictions as example (with win percent)
test_results = X_test.copy()
test_results['true_label'] = y_test
test_results['predicted_label'] = y_pred
test_results['predicted_win_percent'] = (probs * 100).round(1)
print("\n[Sample predictions]")
print(test_results[['true_label', 'predicted_label', 'predicted_win_percent']].head(10))
