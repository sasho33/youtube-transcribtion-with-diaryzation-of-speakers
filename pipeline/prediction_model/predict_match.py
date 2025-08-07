# predict_match.py

import sys
from pathlib import Path
import pandas as pd
import xgboost as xgb
import joblib
import numpy as np

sys.path.append(str(Path(__file__).resolve().parents[2]))
from pipeline.config import TRAINING_MODEL_DATASET

model = joblib.load("best_xgboost_model.pkl")  

# 2. Load the dataset
df = pd.read_csv(TRAINING_MODEL_DATASET)  # Or however you load it

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


# 3. Define your prediction function
def predict_for_match(event_title, athlete1, athlete2):
    # Find the relevant row (you may need fuzzy matching for names)
    row = df[
        (df['event'] == event_title) &
        (df['fighter_1'] == athlete1) &
        (df['fighter_2'] == athlete2)
    ]
    if row.empty:
        print(f"No data found for match: {event_title}, {athlete1} vs {athlete2}")
        return None

    # Drop label and non-feature columns as needed
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
        
    ]  # List of feature column names used in training
    X = row[feature_cols]
    pred_prob = model.predict_proba(X)[0, 1]  # Probability of "win" class
    
    return pred_prob

def predict_and_get_odds(event_title, athlete1, athlete2, margin=0.85, print_console=True, min_odds=1.1, max_odds=10):
    """
    Returns a dict with raw and normalized probabilities and odds for both athletes.
    Prints a nice summary if print_console is True.
    """
    # 1. Predict win probabilities for both orders
    prob1 = predict_for_match(event_title, athlete1, athlete2)
    prob2 = predict_for_match(event_title, athlete2, athlete1)
    if (prob1 is None) or (prob2 is None):
        print(f"Prediction not available for this matchup: {athlete1} vs {athlete2}")
        return None
    
    # 2. Normalize probabilities
    total = prob1 + prob2
    norm_p1 = prob1 / total if total > 0 else 0.5
    norm_p2 = prob2 / total if total > 0 else 0.5
    
    # 3. Apply margin
    adj_p1 = norm_p1 * margin
    adj_p2 = norm_p2 * margin
    odds1 = 1 / adj_p1 if adj_p1 > 0 else float('inf')
    odds2 = 1 / adj_p2 if adj_p2 > 0 else float('inf')

    # 4. Clip the odds to min and max
    odds1 = min(max(odds1, min_odds), max_odds)
    odds2 = min(max(odds2, min_odds), max_odds)

    # 5. Print results
    if print_console:
        print(f"\n{event_title}: {athlete1} vs {athlete2}")
        print(f"Raw model probabilities: {athlete1}: {prob1:.3f}, {athlete2}: {prob2:.3f}")
        print(f"Normalized probabilities: {athlete1}: {norm_p1:.2%}, {athlete2}: {norm_p2:.2%}")
        print(f"Decimal odds (with {int((1-margin)*100)}% margin, min={min_odds}, max={max_odds}):")
        print(f"  {athlete1}: {odds1:.2f}")
        print(f"  {athlete2}: {odds2:.2f}")
    
    return {
        'athlete1': athlete1,
        'athlete2': athlete2,
        'prob1_raw': prob1,
        'prob2_raw': prob2,
        'prob1_normalized': norm_p1,
        'prob2_normalized': norm_p2,
        'odds1': round(odds1, 2),
        'odds2': round(odds2, 2)
    }


# Example usage
if __name__ == "__main__":
    matches = [
    ("East vs West 18", "Riekerd Bornman", "Wallace Dilley"),
    ("East vs West 18", "Wallace Dilley", "Riekerd Bornman"),
    ("East vs West 18", "Ryan Belanger", "Allen Ford"),
    ("East vs West 18", "Allen Ford", "Ryan Belanger"),
    ("East vs West 18", "Joseph Meranto", "Ivan Portela"),
    ("East vs West 18", "Ivan Portela", "Joseph Meranto"),
    ("East vs West 18", "Pavlo Derbedyenyev", "Wagner Bortalato"),
    ("East vs West 18", "Wagner Bortalato", "Pavlo Derbedyenyev"),
    ("East vs West 18", "Devon Larratt", "Alex Kurdecha"),
    ("East vs West 18", "Alex Kurdecha", "Devon Larratt"),
    ("East vs West 18", "Paul Linn", "Arsen Khachatryan"),
    ("East vs West 18", "Arsen Khachatryan", "Paul Linn"),
    ("East vs West 18", "Matt Mask", "Irakli Zirakashvili"),
    ("East vs West 18", "Irakli Zirakashvili", "Matt Mask"),
    ("East vs West 18", "Michael Todd", "Georgii Dzeranov"),
    ("East vs West 18", "Georgii Dzeranov", "Michael Todd"),
    ("East vs West 18", "Fia Reisek", "Elin Janeheim"),
    ("East vs West 18", "Elin Janeheim", "Fia Reisek"),
]
    
    for event, athlete1, athlete2 in matches:
        predict_and_get_odds(event, athlete1, athlete2)