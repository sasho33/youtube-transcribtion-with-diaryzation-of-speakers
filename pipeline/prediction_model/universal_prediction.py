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
    TEMPORARY_PREDICTION_FOLDER,
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
)

HERE = Path(__file__).resolve().parent
MODEL_PATH = HERE / "best_xgboost_model.pkl"
ATHLETE_DATA_PATH = UNIQUE_ATHLETES_WITH_DATA_FILE
TEMP_FOLDER = TEMPORARY_PREDICTION_FOLDER
EVENTS = load_events()
ATHLETE_MATCHES, _ = build_athlete_match_history(EVENTS)

# Model feature columns (same as before)
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

def generate_feature_explanations(features, athlete1_name, athlete2_name):
    """Generate human-readable explanations for key features"""
    explanations = []
    
    # Physical advantages
    if features["weight_advantage"] > 5:
        explanations.append({
            "category": "Physical",
            "title": "Weight Advantage",
            "description": f"{athlete1_name} has a {features['weight_advantage']:.1f}kg weight advantage over {athlete2_name}",
            "impact": "positive" if features["weight_advantage"] > 0 else "negative",
            "value": features["weight_advantage"]
        })
    elif features["weight_advantage"] < -5:
        explanations.append({
            "category": "Physical",
            "title": "Weight Disadvantage", 
            "description": f"{athlete2_name} has a {abs(features['weight_advantage']):.1f}kg weight advantage over {athlete1_name}",
            "impact": "negative",
            "value": features["weight_advantage"]
        })
    
    if features["height_advantage"] > 3:
        explanations.append({
            "category": "Physical",
            "title": "Height Advantage",
            "description": f"{athlete1_name} has a {features['height_advantage']:.1f}cm height advantage",
            "impact": "positive",
            "value": features["height_advantage"]
        })
    elif features["height_advantage"] < -3:
        explanations.append({
            "category": "Physical", 
            "title": "Height Disadvantage",
            "description": f"{athlete2_name} has a {abs(features['height_advantage']):.1f}cm height advantage",
            "impact": "negative",
            "value": features["height_advantage"]
        })
    
    # Age factor
    age_diff = features["f1_age"] - features["f2_age"]
    if abs(age_diff) > 5:
        if age_diff > 0:
            explanations.append({
                "category": "Experience",
                "title": "Age Factor",
                "description": f"{athlete1_name} is {age_diff} years older than {athlete2_name}",
                "impact": "neutral",
                "value": age_diff
            })
        else:
            explanations.append({
                "category": "Experience", 
                "title": "Age Factor",
                "description": f"{athlete2_name} is {abs(age_diff)} years older than {athlete1_name}",
                "impact": "neutral",
                "value": age_diff
            })
    
    # Travel advantage
    if features["domestic_advantage"] > 0:
        explanations.append({
            "category": "Travel",
            "title": "Home Advantage", 
            "description": f"{athlete1_name} has home advantage - competing closer to home territory",
            "impact": "positive",
            "value": features["domestic_advantage"]
        })
    elif features["domestic_advantage"] < 0:
        explanations.append({
            "category": "Travel",
            "title": "Away Disadvantage",
            "description": f"{athlete2_name} has home advantage - {athlete1_name} is traveling further",
            "impact": "negative", 
            "value": features["domestic_advantage"]
        })
    
    # Win rates
    if features["f1_domestic_win_rate"] > features["f2_domestic_win_rate"] + 0.1:
        explanations.append({
            "category": "Performance",
            "title": "Domestic Win Rate",
            "description": f"{athlete1_name} has a higher domestic win rate ({features['f1_domestic_win_rate']:.1%} vs {features['f2_domestic_win_rate']:.1%})",
            "impact": "positive",
            "value": features["f1_domestic_win_rate"] - features["f2_domestic_win_rate"]
        })
    elif features["f2_domestic_win_rate"] > features["f1_domestic_win_rate"] + 0.1:
        explanations.append({
            "category": "Performance",
            "title": "Domestic Win Rate",
            "description": f"{athlete2_name} has a higher domestic win rate ({features['f2_domestic_win_rate']:.1%} vs {features['f1_domestic_win_rate']:.1%})",
            "impact": "negative",
            "value": features["f1_domestic_win_rate"] - features["f2_domestic_win_rate"]
        })
    
    # Style advantage
    style_rate = features["athlete1_style_advantage_rate"]
    if style_rate > 55:
        explanations.append({
            "category": "Style",
            "title": "Style Matchup Advantage",
            "description": f"{athlete1_name}'s style is historically effective against {athlete2_name}'s style ({style_rate:.1f}% success rate)",
            "impact": "positive",
            "value": style_rate
        })
    elif style_rate < 45:
        explanations.append({
            "category": "Style",
            "title": "Style Matchup Disadvantage", 
            "description": f"{athlete2_name}'s style is historically effective against {athlete1_name}'s style ({100-style_rate:.1f}% success rate)",
            "impact": "negative",
            "value": style_rate
        })
    
    # Winning streaks
    if features["f1_winning_streak"] > features["f2_winning_streak"] + 2:
        explanations.append({
            "category": "Form",
            "title": "Winning Streak",
            "description": f"{athlete1_name} is on a {features['f1_winning_streak']}-match winning streak vs {athlete2_name}'s {features['f2_winning_streak']} wins",
            "impact": "positive",
            "value": features["f1_winning_streak"] - features["f2_winning_streak"]
        })
    elif features["f2_winning_streak"] > features["f1_winning_streak"] + 2:
        explanations.append({
            "category": "Form",
            "title": "Winning Streak Disadvantage",
            "description": f"{athlete2_name} is on a {features['f2_winning_streak']}-match winning streak vs {athlete1_name}'s {features['f1_winning_streak']} wins", 
            "impact": "negative",
            "value": features["f1_winning_streak"] - features["f2_winning_streak"]
        })
    
    # Title holder status
    if features["f1_is_current_title_holder"] and not features["f2_is_current_title_holder"]:
        explanations.append({
            "category": "Status",
            "title": "Title Holder",
            "description": f"{athlete1_name} is currently a title holder",
            "impact": "positive",
            "value": 1
        })
    elif features["f2_is_current_title_holder"] and not features["f1_is_current_title_holder"]:
        explanations.append({
            "category": "Status", 
            "title": "Title Holder Disadvantage",
            "description": f"{athlete2_name} is currently a title holder",
            "impact": "negative",
            "value": -1
        })
    
    # Head to head
    if features["has_head_to_head"]:
        if features["head_to_head_result"] > 0:
            explanations.append({
                "category": "History",
                "title": "Head-to-Head Advantage", 
                "description": f"{athlete1_name} has won their previous encounters",
                "impact": "positive",
                "value": features["head_to_head_result"]
            })
        elif features["head_to_head_result"] < 0:
            explanations.append({
                "category": "History",
                "title": "Head-to-Head Disadvantage",
                "description": f"{athlete2_name} has won their previous encounters", 
                "impact": "negative",
                "value": features["head_to_head_result"]
            })
    
    # MMA Math
    if features["mma_math_positive"] > features["mma_math_negative"]:
        explanations.append({
            "category": "Comparison",
            "title": "Common Opponents Advantage",
            "description": f"{athlete1_name} has better results against {features['mma_math_positive']} shared opponents",
            "impact": "positive", 
            "value": features["num_shared_opponents_value"]
        })
    elif features["mma_math_negative"] > features["mma_math_positive"]:
        explanations.append({
            "category": "Comparison",
            "title": "Common Opponents Disadvantage",
            "description": f"{athlete2_name} has better results against {features['mma_math_negative']} shared opponents",
            "impact": "negative",
            "value": features["num_shared_opponents_value"]
        })
    
    return explanations

def universal_predict_and_save(
    athlete1_name, athlete2_name, match_arm="Right", event_country="United States",
    event_title="(Virtual)", event_date=None, verbose=False
):
    """Enhanced prediction with detailed analysis and explanations"""
    
    if event_date is None:
        event_date = get_date_now()

    # Load model and athlete data
    with open(ATHLETE_DATA_PATH, encoding="utf-8") as f:
        athletes = json.load(f)
    model = joblib.load(MODEL_PATH)

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

    # Get valuable match information
    valuable_info = get_valuable_info(athlete1_name, athlete2_name, match_date_dt, ATHLETE_MATCHES)

    # --- Calculate all features (same as original) ---
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

    # Form/streaks/winrate
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

    # Travel
    f1_country = a1.get("country", "Unknown")
    f2_country = a2.get("country", "Unknown")
    f1_travel_penalty = get_travel_penalty(f1_country, event_country)
    f2_travel_penalty = get_travel_penalty(f2_country, event_country)
    domestic_adv = f2_travel_penalty - f1_travel_penalty

    # Winrates (domestic/transatlantic)
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

    # Styles
    f1_style_dominant = get_dominant_style(a1)
    f1_style_additional = get_additional_style(a1)
    f2_style_dominant = get_dominant_style(a2)
    f2_style_additional = get_additional_style(a2)
    f1_style_combo = get_combo_success_pct(f1_style_dominant, f1_style_additional)
    f2_style_combo = get_combo_success_pct(f2_style_dominant, f2_style_additional)
    style_advantage = get_athlete1_style_advantage_rate(f1_style_dominant, f2_style_dominant)

    # Gender
    f1_gender = encode_gender(a1.get("gender", "male"))
    f2_gender = encode_gender(a2.get("gender", "male"))

    # Title holder
    f1_title = int(is_current_title_holder_on_date(athlete1_name, as_of_date=event_date))
    f2_title = int(is_current_title_holder_on_date(athlete2_name, as_of_date=event_date))

    # Default values for features not computed
    default_fill = 0

    # Create features dictionary
    features = {
        "event_title": event_title,
        "event_date": event_date,
        "match_arm": match_arm,
        "event_country": event_country,
        "f1_name": f1_name,
        "f2_name": f2_name,
        "f1_age": f1_age,
        "f2_age": f2_age,
        "f1_weight": f1_weight,
        "f2_weight": f2_weight,
        "weight_advantage": weight_adv,
        "f1_height": f1_height,
        "f2_height": f2_height,
        "height_advantage": height_adv,
        "f1_travel_penalty": f1_travel_penalty,
        "f2_travel_penalty": f2_travel_penalty,
        "domestic_advantage": domestic_adv,
        "f1_domestic_win_rate": f1_dom_win,
        "f2_domestic_win_rate": f2_dom_win,
        "f1_transatlantic_win_rate": f1_trans_win,
        "f2_transatlantic_win_rate": f2_trans_win,
        "f1_low_rank_predictions": default_fill,
        "f2_low_rank_predictions": default_fill,
        "f1_high_rank_predictions": default_fill,
        "f2_high_rank_predictions": default_fill,
        "f1_style_combo_success_percent": f1_style_combo if f1_style_combo is not None else 0,
        "f2_style_combo_success_percent": f2_style_combo if f2_style_combo is not None else 0,
        "athlete1_style_advantage_rate": style_advantage if style_advantage is not None else 50,
        "num_shared_opponents_value": valuable_info.get('num_shared_opponents_value', default_fill),
        "mma_math_positive": valuable_info.get('mma_math_positive', default_fill),
        "mma_math_negative": valuable_info.get('mma_math_negative', default_fill),
        "has_head_to_head": valuable_info.get('has_head_to_head', default_fill),
        "head_to_head_result": valuable_info.get('head_to_head_result', default_fill),
        "second_order_mma_math_difference": valuable_info.get('second_order_mma_math_difference', default_fill),
        "second_order_mma_math_positive": valuable_info.get('second_order_mma_math_positive', default_fill),
        "second_order_mma_math_negative": valuable_info.get('second_order_mma_math_negative', default_fill),
        "f1_gender": f1_gender,
        "f2_gender": f2_gender,
        "f1_is_current_title_holder": f1_title,
        "f2_is_current_title_holder": f2_title,
        "f1_winning_streak": f1_winning_streak,
        "f2_winning_streak": f2_winning_streak,
    }

    # Model prediction
    X_model = pd.DataFrame([features])[MODEL_FEATURE_COLS].fillna(0)
    prob = model.predict_proba(X_model)[0, 1]

    # Generate explanations
    explanations = generate_feature_explanations(features, athlete1_name, athlete2_name)

    # Extract valuable matches data
    shared_opponents = valuable_info.get('all_shared_results', [])
    head_to_head_matches = valuable_info.get('head_to_head', [])
    second_order_matches = valuable_info.get('second_order_valuable_shared_results', [])

    # Build comprehensive response
    result = {
        "prediction": {
            "athlete1_name": athlete1_name,
            "athlete2_name": athlete2_name,
            "athlete1_win_probability": round(float(prob), 4),
            "athlete2_win_probability": round(float(1 - prob), 4),
            "confidence": "High" if abs(prob - 0.5) > 0.2 else "Medium" if abs(prob - 0.5) > 0.1 else "Low"
        },
        "match_details": {
            "event_title": event_title,
            "event_date": event_date,
            "match_arm": match_arm,
            "event_country": event_country
        },
        "athlete_profiles": {
            "athlete1": {
                "name": athlete1_name,
                "age": f1_age,
                "weight_kg": f1_weight,
                "height_cm": f1_height,
                "country": f1_country,
                "dominant_style": f1_style_dominant,
                "additional_style": f1_style_additional,
                "is_title_holder": bool(f1_title),
                "current_winning_streak": f1_winning_streak,
                "domestic_win_rate": f1_dom_win,
                "transatlantic_win_rate": f1_trans_win
            },
            "athlete2": {
                "name": athlete2_name,
                "age": f2_age,
                "weight_kg": f2_weight,
                "height_cm": f2_height,
                "country": f2_country,
                "dominant_style": f2_style_dominant,
                "additional_style": f2_style_additional,
                "is_title_holder": bool(f2_title),
                "current_winning_streak": f2_winning_streak,
                "domestic_win_rate": f2_dom_win,
                "transatlantic_win_rate": f2_trans_win
            }
        },
        "analysis": {
            "explanations": explanations,
            "key_factors": {
                "weight_advantage_kg": weight_adv,
                "height_advantage_cm": height_adv,
                "age_difference": f1_age - f2_age,
                "travel_advantage": domestic_adv,
                "style_advantage_rate": style_advantage,
                "has_head_to_head_history": bool(valuable_info.get('has_head_to_head', 0)),
                "shared_opponents_count": len(shared_opponents),
                "mma_math_advantage": valuable_info.get('num_shared_opponents_value', 0)
            }
        },
        "valuable_matches": {
            "head_to_head": head_to_head_matches,
            "shared_opponents": shared_opponents,
            "second_order_connections": second_order_matches
        },
        "raw_features": {k: v for k, v in features.items() if k in MODEL_FEATURE_COLS},
        "metadata": {
            "prediction_date": datetime.now().isoformat(),
            "model_features_count": len(MODEL_FEATURE_COLS),
            "data_quality": "Complete" if f1_weight > 0 and f2_weight > 0 else "Partial"
        }
    }

    if verbose:
        print(f"Enhanced prediction for {athlete1_name} vs {athlete2_name}")
        print(f"Win probability: {prob:.1%}")
        print(f"Key factors identified: {len(explanations)}")
        print(f"Shared opponents: {len(shared_opponents)}")

    return result

# Example usage
if __name__ == "__main__":
    result = universal_predict_and_save("Devon Larratt", "Kamil Jablonski", match_arm="Right", verbose=True)
    print(json.dumps(result, indent=2, ensure_ascii=False))