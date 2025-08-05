import json
import joblib
import numpy as np
import pandas as pd
from datetime import datetime
import os
import sys
from pathlib import Path


sys.path.append(str(Path(__file__).resolve().parents[2]))
from pipeline.config import (
    UNIQUE_ATHLETES_WITH_DATA_FILE,
    TEMPORARY_PREDICTION_FOLDER
)

# === CONFIGURATION ===
MODEL_PATH = "best_xgboost_model.pkl"
ATHLETE_DATA_PATH = UNIQUE_ATHLETES_WITH_DATA_FILE   # <-- Update to your path           # <-- Update as needed

FEATURE_COLS = [
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

def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)

def encode_gender(gender):
    if isinstance(gender, str):
        return {"male": 0, "female": 1}.get(gender.lower(), 0)
    return 0

def encode_bool(val):
    if isinstance(val, bool):
        return int(val)
    if isinstance(val, str):
        return 1 if val.strip().lower() in ("true", "yes", "1") else 0
    return 0

def compute_age(dob, as_of=None):
    if not dob: return 0
    if not as_of:
        as_of = datetime.now()
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y-%m", "%Y"):
        try:
            dob_date = datetime.strptime(dob, fmt)
            if fmt == "%Y":
                dob_date = dob_date.replace(month=7, day=1)
            elif fmt == "%Y-%m":
                dob_date = dob_date.replace(day=15)
            break
        except Exception:
            continue
    else:
        return 0
    return as_of.year - dob_date.year - ((as_of.month, as_of.day) < (dob_date.month, dob_date.day))

def safe_float(val):
    try:
        return float(val)
    except Exception:
        return 0.0

def universal_predict_and_save(athlete1_name, athlete2_name, match_arm="Right", verbose=False):
    # -- Load model and data
    model = joblib.load(MODEL_PATH)
    athletes = load_json(ATHLETE_DATA_PATH)

    # Get today as the match date
    match_date = datetime.now().strftime("%Y-%m-%d")

    # Helper for missing athletes
    def get_athlete(name):
        if name in athletes:
            return athletes[name]
        # Fallback: fuzzy search (could use fuzzywuzzy here if available)
        return {"country": "Unknown", "pulling_style": ["Unknown"], "weight_kg": 0, "height_cm": 0, "gender": "male"}

    a1 = get_athlete(athlete1_name)
    a2 = get_athlete(athlete2_name)

    # Age, Weight, Height
    f1_age = compute_age(a1.get("date_of_birth", ""), as_of=datetime.now())
    f2_age = compute_age(a2.get("date_of_birth", ""), as_of=datetime.now())
    f1_weight = safe_float(a1.get("weight_kg", 0))
    f2_weight = safe_float(a2.get("weight_kg", 0))
    weight_adv = f1_weight - f2_weight
    f1_height = safe_float(a1.get("height_cm", 0))
    f2_height = safe_float(a2.get("height_cm", 0))
    height_adv = f1_height - f2_height

    # Travel features (for demo, always 0/domestic; you can update with your travel logic)
    f1_travel_penalty = 0
    f2_travel_penalty = 0
    domestic_adv = 0

    # Winrate & streaks – fake logic for now, insert your real function!
    f1_left_win = 0
    f1_right_win = 0
    f1_winrate = 0
    f2_left_win = 0
    f2_right_win = 0
    f2_winrate = 0

    # Style combo (set as 0 for now, add logic if you want)
    f1_style_combo = 0
    f2_style_combo = 0
    style_advantage = 0

    # Winrates (travel)
    f1_dom_win = 0.5
    f1_trans_win = 0.5
    f2_dom_win = 0.5
    f2_trans_win = 0.5

    # Gender, Title holder (assume male, not champion; update as needed)
    f1_gender = encode_gender(a1.get("gender", "male"))
    f2_gender = encode_gender(a2.get("gender", "male"))
    f1_title = 0
    f2_title = 0

    # Winning streaks: pick right/left depending on arm
    f1_winning_streak = f1_right_win if match_arm == "Right" else f1_left_win
    f2_winning_streak = f2_right_win if match_arm == "Right" else f2_left_win

    # Features not computable: set to 0/neutral
    default_fill = 0
    features = dict(
        f1_age=f1_age,
        f2_age=f2_age,
        f1_weight=f1_weight,
        f2_weight=f2_weight,
        weight_advantage=weight_adv,
        f1_height=f1_height,
        f2_height=f2_height,
        height_advantage=height_adv,
        f1_travel_penalty=f1_travel_penalty,
        f2_travel_penalty=f2_travel_penalty,
        domestic_advantage=domestic_adv,
        f1_domestic_win_rate=f1_dom_win,
        f2_domestic_win_rate=f2_dom_win,
        f1_transatlantic_win_rate=f1_trans_win,
        f2_transatlantic_win_rate=f2_trans_win,
        f1_low_rank_predictions=default_fill,
        f2_low_rank_predictions=default_fill,
        f1_high_rank_predictions=default_fill,
        f2_high_rank_predictions=default_fill,
        f1_style_combo_success_percent=f1_style_combo,
        f2_style_combo_success_percent=f2_style_combo,
        athlete1_style_advantage_rate=style_advantage,
        num_shared_opponents_value=default_fill,
        mma_math_positive=default_fill,
        mma_math_negative=default_fill,
        has_head_to_head=default_fill,
        head_to_head_result=default_fill,
        num_second_order_valuable=default_fill,
        second_order_mma_math_positive=default_fill,
        second_order_mma_math_negative=default_fill,
        f1_gender=f1_gender,
        f2_gender=f2_gender,
        f1_is_current_title_holder=f1_title,
        f2_is_current_title_holder=f2_title,
        f1_winning_streak=f1_winning_streak,
        f2_winning_streak=f2_winning_streak,
    )

    # Build DataFrame and fill missing
    X = pd.DataFrame([features], columns=FEATURE_COLS).fillna(0)

    # Predict
    prob = model.predict_proba(X)[0, 1]

    # ---- SAVE FEATURE DATAFRAME ----
    if not os.path.exists(TEMPORARY_PREDICTION_FOLDER):
        os.makedirs(TEMPORARY_PREDICTION_FOLDER)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    fname = f"{athlete1_name.replace(' ', '_')}_vs_{athlete2_name.replace(' ', '_')}_prediction_{timestamp}.csv"
    save_path = os.path.join(TEMPORARY_PREDICTION_FOLDER, fname)
    X.to_csv(save_path, index=False)

    if verbose:
        print(f"Prediction for {athlete1_name} vs {athlete2_name}: {prob:.3f}")
        print(f"Feature row saved at: {save_path}")
    return prob, save_path

# ---- Example usage ----
if __name__ == "__main__":
    universal_predict_and_save("Devon Larratt", "John Brzenk", match_arm="Right", verbose=True)
