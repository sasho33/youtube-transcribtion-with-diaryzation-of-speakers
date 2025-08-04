import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix, mean_squared_error
from xgboost import XGBClassifier, plot_importance
import sys
from pathlib import Path
import matplotlib.pyplot as plt
import shap


sys.path.append(str(Path(__file__).resolve().parents[2]))
from pipeline.config import UPDATED_TRAINING_FEATURES_WITH_TRAVEL_STATS
def balance_dataset_by_swapping(df):
    swapped_rows = []

    for _, row in df.iterrows():
        swapped = row.copy()

        # Swap fighter info
        swapped["fighter_1"], swapped["fighter_2"] = row["fighter_2"], row["fighter_1"]
        swapped["f1_style"], swapped["f2_style"] = row["f2_style"], row["f1_style"]
        swapped["f1_weight"], swapped["f2_weight"] = row["f2_weight"], row["f1_weight"]
        swapped["f1_country"], swapped["f2_country"] = row["f2_country"], row["f1_country"]
        swapped["f1_travel_penalty"], swapped["f2_travel_penalty"] = row["f2_travel_penalty"], row["f1_travel_penalty"]
        swapped["f1_domestic_win_rate"], swapped["f2_domestic_win_rate"] = row["f2_domestic_win_rate"], row["f1_domestic_win_rate"]
        swapped["f1_transatlantic_win_rate"], swapped["f2_transatlantic_win_rate"] = row["f2_transatlantic_win_rate"], row["f1_transatlantic_win_rate"]

        # Reverse calculated advantages
        if "height_advantage" in row:
            swapped["height_advantage"] = -row["height_advantage"] if pd.notnull(row["height_advantage"]) else None

        if "weight_advantage" in row:
            swapped["weight_advantage"] = -row["weight_advantage"] if pd.notnull(row["weight_advantage"]) else None

        if "domestic_advantage" in row:
            swapped["domestic_advantage"] = -row["domestic_advantage"] if pd.notnull(row["domestic_advantage"]) else None

        # Flip the label
        swapped["label"] = 0 if row["label"] == 1 else 1

        swapped_rows.append(swapped)

    df_swapped = pd.DataFrame(swapped_rows)
    balanced_df = pd.concat([df, df_swapped], ignore_index=True)
    return balanced_df

# Load dataset
df = pd.read_csv(UPDATED_TRAINING_FEATURES_WITH_TRAVEL_STATS)
df = balance_dataset_by_swapping(df)


# Basic info
print(f"[🔍] Dataset size: {len(df)}")
print("[🔍] Label distribution:", df["label"].value_counts())

# Drop rows with missing data
df.dropna(inplace=True)

# Features to use for training
feature_cols = [
    "height_advantage",
    "weight_advantage",
    "f1_domestic_win_rate",
    "f2_domestic_win_rate",
    "f1_transatlantic_win_rate",
    "f2_transatlantic_win_rate",
    "f1_travel_penalty",
    "f2_travel_penalty",
    "domestic_advantage"
]

X = df[feature_cols]
y = df["label"]

# Split data
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

# Train XGBRegressor
model = XGBClassifier(
    n_estimators=100,
    max_depth=4,
    learning_rate=0.1,
    use_label_encoder=False,
    eval_metric="logloss"
)
model.fit(X_train, y_train)

# Plot the top 15 features by importance
plot_importance(model, max_num_features=15, importance_type='weight', height=0.5)

# Explain the model predictions using SHAP
explainer = shap.Explainer(model, X_train)  # Use your training set here
shap_values = explainer(X_test)  # Apply to your test set

# Predict
y_pred = model.predict(X_test)

# Evaluate as classification for interpretability
y_pred_class = (y_pred >= 0.5).astype(int)

print("\n[✅] MSE:", mean_squared_error(y_test, y_pred))
print("\n[📊] Classification Report:")
print(classification_report(y_test, y_pred_class))

print("\n[📉] Confusion Matrix:")
print(confusion_matrix(y_test, y_pred_class))

# Optional: Make it easier to read
plt.title("Top 15 Feature Importances")
plt.tight_layout()
plt.show()

# SHAP summary plot (bar chart of feature impact)
shap.plots.bar(shap_values, max_display=15)

# SHAP beeswarm plot (more detailed)
shap.plots.beeswarm(shap_values, max_display=15)
