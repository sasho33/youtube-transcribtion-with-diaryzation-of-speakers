import json
import joblib
import numpy as np
import pandas as pd
from datetime import datetime
import os
import sys
from pathlib import Path
from fuzzywuzzy import process

sys.path.append(str(Path(__file__).resolve().parents[2]))
from pipeline.config import (
    UNIQUE_ATHLETES_WITH_DATA_FILE,
    TEMPORARY_PREDICTION_FOLDER
)
from pipeline.prediction_model.title_holder import is_current_title_holder_on_date
from pipeline.predictions_count import count_low_rank_predictions, count_high_rank_predictions, count_all_predictions
from pipeline.valueable_matches import (
    load_events,
    build_athlete_match_history,
    get_valuable_info,
)
from pipeline.prediction_model.athletes_data_for_model import (
    get_athlete_form_features,
    get_combo_success_pct,
    get_athlete1_style_advantage_rate,
    compute_domestic_transatlantic_winrates_single,
    get_travel_penalty    
           # dict from athletes_data_for_model.py
)

MODEL_PATH = "best_xgboost_model.pkl"
ATHLETE_DATA_PATH = UNIQUE_ATHLETES_WITH_DATA_FILE  # JSON file
TEMP_FOLDER = TEMPORARY_PREDICTION_FOLDER
EVENTS = load_events()
ATHLETE_MATCHES, _ = build_athlete_match_history(EVENTS)

# Numeric/categorical features your model expects, in order
MODEL_FEATURE_COLS = [
    "f1_age","f2_age","f1_weight","f2_weight","weight_advantage",
    "f1_height","f2_height","height_advantage",
    "f1_travel_penalty","f2_travel_penalty","domestic_advantage",
    "f1_domestic_win_rate","f2_domestic_win_rate",
    "f1_transatlantic_win_rate","f2_transatlantic_win_rate",
    "f1_low_rank_predictions","f2_low_rank_predictions",
    "f1_high_rank_predictions","f2_high_rank_predictions",
    "f1_style_combo_success_percent","f2_style_combo_success_percent",
    "athlete1_style_advantage_rate",
    "num_shared_opponents_value","mma_math_positive","mma_math_negative",
    "has_head_to_head","head_to_head_result",
    "second_order_mma_math_difference","second_order_mma_math_positive","second_order_mma_math_negative",
    "f1_gender","f2_gender","f1_is_current_title_holder","f2_is_current_title_holder",
    "f1_winning_streak","f2_winning_streak"
]

# All fields to save to CSV for logging/debugging/tracing
FEATURE_COLS = [
    "event_title", "event_date", "match_arm", "event_country",
    "f1_name", "f2_name"
] + MODEL_FEATURE_COLS

def encode_gender(gender):
    if isinstance(gender, str):
        return {"male": 0, "female": 1}.get(gender.lower(), 0)
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

def get_dominant_style(athlete):
    return athlete.get("pulling_style", ["Unknown"])[0] if athlete.get("pulling_style") else "Unknown"

def get_additional_style(athlete):
    ps = athlete.get("pulling_style", [])
    return ps[1] if len(ps) > 1 else ""

def get_date_now():
    return datetime.now().strftime("%Y-%m-%d")

def universal_predict_and_save(
    athlete1_name, athlete2_name, match_arm="Right", event_country="United States",
    event_title="(Virtual)", event_date=None, verbose=False
):
    if event_date is None:
        event_date = get_date_now()

    # Load model and athlete data
    with open(ATHLETE_DATA_PATH, encoding="utf-8") as f:
        athletes = json.load(f)
    model = joblib.load(MODEL_PATH)

    # Use event_date as match_date
    match_date = event_date
    match_dt = datetime.strptime(match_date, "%Y-%m-%d")

    def get_athlete(name):
        if name in athletes:
            return athletes[name]
        # Fuzzy fallback
        match, score = process.extractOne(name, list(athletes.keys()))
        if score >= 85:
            return athletes[match]
        return {"country": "Unknown", "pulling_style": ["Unknown"], "weight_kg": 0, "height_cm": 0, "gender": "male"}

    a1 = get_athlete(athlete1_name)
    a2 = get_athlete(athlete2_name)
    match_date_dt = datetime.strptime(event_date, "%Y-%m-%d")
    # def get_opponents(match_list, athlete_name):
    #     opponents = set()
    #     for match in match_list:
    #         if match.get('opponent') and match.get('opponent') != athlete_name:
    #             opponents.add(match['opponent'])
    #         # Or use the correct key depending on your match dict structure
    #     return opponents

    # devon_matches = ATHLETE_MATCHES['Devon Larratt']
    # levan_matches = ATHLETE_MATCHES['Vitaly Laletin']

    # devon_opponents = get_opponents(devon_matches, 'Devon Larratt')
    # levan_opponents = get_opponents(levan_matches, 'Vitaly Laletin')

    # print("Devon opponents:", devon_opponents)
    # print("Vitaly opponents:", levan_opponents)
    # print("Shared:", devon_opponents & levan_opponents)
    valuable_info = get_valuable_info(athlete1_name, athlete2_name, match_date_dt, ATHLETE_MATCHES)

    # --- Basic features ---
    f1_name = a1.get("name", athlete1_name)
    f2_name = a2.get("name", athlete2_name)
    f1_age = compute_age(a1.get("date_of_birth", ""), as_of=match_dt)
    f2_age = compute_age(a2.get("date_of_birth", ""), as_of=match_dt)
    f1_weight = safe_float(a1.get("weight_kg", 0))
    f2_weight = safe_float(a2.get("weight_kg", 0))
    weight_adv = f1_weight - f2_weight
    f1_height = safe_float(a1.get("height_cm", 0))
    f2_height = safe_float(a2.get("height_cm", 0))
    height_adv = f1_height - f2_height

    # --- Form/streaks/winrate ---
    f1_form = get_athlete_form_features(athlete1_name, athletes, match_dt)
    f2_form = get_athlete_form_features(athlete2_name, athletes, match_dt)
    f1_left_win = f1_form["left_winning_streak"]
    f1_right_win = f1_form["right_winning_streak"]
    f1_winrate = f1_form["winrate_last_5"]
    f2_left_win = f2_form["left_winning_streak"]
    f2_right_win = f2_form["right_winning_streak"]
    f2_winrate = f2_form["winrate_last_5"]
    f1_winning_streak = f1_right_win if match_arm == "Right" else f1_left_win
    f2_winning_streak = f2_right_win if match_arm == "Right" else f2_left_win

    # --- Travel ---
    f1_country = a1.get("country", "Unknown")
    f2_country = a2.get("country", "Unknown")
   

    f1_travel_penalty = get_travel_penalty(f1_country, event_country)
    f2_travel_penalty = get_travel_penalty(f2_country, event_country)
    domestic_adv = f2_travel_penalty - f1_travel_penalty


    # --- Winrates (domestic/transatlantic) ---
    a1_profile = a1
    a2_profile = a2
    a1_country = a1_profile.get("country", "Unknown")
    a2_country = a2_profile.get("country", "Unknown")
    a1_winrate_stats = compute_domestic_transatlantic_winrates_single(a1_profile, a1_country, up_to_date=match_dt)
    a2_winrate_stats = compute_domestic_transatlantic_winrates_single(a2_profile, a2_country, up_to_date=match_dt)

    f1_dom_win = a1_winrate_stats["domestic_win_rate"]
    f1_trans_win = a1_winrate_stats["transatlantic_win_rate"]
    f2_dom_win = a2_winrate_stats["domestic_win_rate"]
    f2_trans_win = a2_winrate_stats["transatlantic_win_rate"]


    # --- Styles ---
    f1_style_dominant = get_dominant_style(a1)
    f1_style_additional = get_additional_style(a1)
    f2_style_dominant = get_dominant_style(a2)
    f2_style_additional = get_additional_style(a2)
    f1_style_combo = get_combo_success_pct(f1_style_dominant, f1_style_additional)
    f2_style_combo = get_combo_success_pct(f2_style_dominant, f2_style_additional)
    style_advantage = get_athlete1_style_advantage_rate(f1_style_dominant, f2_style_dominant)

    # --- Gender ---
    f1_gender = encode_gender(a1.get("gender", "male"))
    f2_gender = encode_gender(a2.get("gender", "male"))

    # --- Title holder (no event context for virtual) ---
    f1_title = int(is_current_title_holder_on_date(athlete1_name, as_of_date=event_date))
    f2_title = int(is_current_title_holder_on_date(athlete2_name, as_of_date=event_date))

    # --- "Uncomputable" features ---
    default_fill = 0

    # --- All predictions ---
    features = dict(
        event_title=event_title,
        event_date=event_date,
        match_arm=match_arm,
        event_country=event_country,
        f1_name=f1_name,
        f2_name=f2_name,
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
        f1_style_combo_success_percent=f1_style_combo if f1_style_combo is not None else 0,
        f2_style_combo_success_percent=f2_style_combo if f2_style_combo is not None else 0,
        athlete1_style_advantage_rate=style_advantage if style_advantage is not None else 50,
        num_shared_opponents_value=valuable_info.get('num_shared_opponents_value', default_fill),
        mma_math_positive=valuable_info.get('mma_math_positive', default_fill),
        mma_math_negative=valuable_info.get('mma_math_negative', default_fill),
        has_head_to_head=valuable_info.get('has_head_to_head', default_fill),
        head_to_head_result=valuable_info.get('head_to_head_result', default_fill),
        second_order_mma_math_difference=valuable_info.get('second_order_mma_math_difference', default_fill),
        second_order_mma_math_positive=valuable_info.get('second_order_mma_math_positive', default_fill),
        second_order_mma_math_negative=valuable_info.get('second_order_mma_math_negative', default_fill),
        f1_gender=f1_gender,
        f2_gender=f2_gender,
        f1_is_current_title_holder=f1_title,
        f2_is_current_title_holder=f2_title,
        f1_winning_streak=f1_winning_streak,
        f2_winning_streak=f2_winning_streak,
    )

    # --- Save ALL info to CSV for debugging ---
    X_all = pd.DataFrame([features], columns=FEATURE_COLS)
    if not os.path.exists(TEMP_FOLDER):
        os.makedirs(TEMP_FOLDER)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    fname = f"{athlete1_name.replace(' ', '_')}_vs_{athlete2_name.replace(' ', '_')}_prediction_{timestamp}.csv"
    save_path = os.path.join(TEMP_FOLDER, fname)
    X_all.to_csv(save_path, index=False)

    # --- Model input: only numeric/categorical columns ---
    X_model = X_all[MODEL_FEATURE_COLS].fillna(0)
    prob = model.predict_proba(X_model)[0, 1]

    if verbose:
        print(f"Prediction for {athlete1_name} vs {athlete2_name}: {prob:.3f}")
        print(f"Feature row saved at: {save_path}")
        # print("Valuable info about shared matches:", valuable_info)
    return prob, save_path

# Example usage:
if __name__ == "__main__":
    universal_predict_and_save("Devon Larratt", "Kamil Jablonski", match_arm="Right", verbose=True)
    universal_predict_and_save("Kamil Jablonski", "Devon Larratt", match_arm="Right", verbose=True)