import json
from pathlib import Path
import sys
import pandas as pd
from collections import defaultdict
from fuzzywuzzy import process
from datetime import datetime


# Setup project path and import config
sys.path.append(str(Path(__file__).resolve().parents[2]))
from pipeline.config import (
    EVW_EVENTS_FILE,
    KOTT_EVENTS_FILE,
    TRAVEL_EFFECT_FILE,
    UNIQUE_ATHLETES_WITH_DATA_FILE,
    UPDATED_TRAINING_FEATURES_WITH_TRAVEL_STATS,
    VALUEABLE_MATCHES_FILE,
    STYLES_COMBO_RATES_FILE
)
from pipeline.prediction_model.title_holder import is_current_title_holder
from pipeline.predictions_count import count_low_rank_predictions, count_high_rank_predictions

# Load the combo rates JSON in modern explicit dict style
with open(STYLES_COMBO_RATES_FILE, encoding="utf-8") as f:
    combo_json = json.load(f)

style_vs_style_dict = {}
style_combo_success_dict = {}

# The new structure: keys "style_vs_style" and "style_combos" mapping to lists of dicts
for entry in combo_json["style_vs_style"]:
    # For each style-vs-style record, add both (A, B) and (B, A) with explicit fields
    k1 = (entry["style_1"], entry["style_2"])
    k2 = (entry["style_2"], entry["style_1"])
    style_vs_style_dict[k1] = entry.get("style_1_success_pct")
    style_vs_style_dict[k2] = entry.get("style_2_success_pct")

for entry in combo_json["style_combos"]:
    style_combo_success_dict[entry["style_combo"]] = entry.get("success_pct")


# Normalized American countries (Zone A)
ZONE_A_COUNTRIES = {
    "United States", "USA", "Canada", "Mexico", "Brazil", "Argentina", "Colombia", "Chile",
    "Peru", "Venezuela", "Ecuador", "Uruguay", "Paraguay", "Panama", "Cuba",
    "El Salvador", "Guatemala", "Honduras", "Nicaragua", "Bolivia", "Costa Rica",
    "Dominican Republic", "Haiti", "Jamaica", "Trinidad and Tobago"
}

def normalize_country(name):
    name = name.strip().lower()
    if name in {"usa", "united states", "united states of america"}:
        return "USA"
    if name == "uk":
        return "United Kingdom"
    return name.title()

# Load data
east_west_events = json.load(open(EVW_EVENTS_FILE, encoding="utf-8"))
kott_events = json.load(open(KOTT_EVENTS_FILE, encoding="utf-8"))
athlete_data = json.load(open(UNIQUE_ATHLETES_WITH_DATA_FILE, encoding="utf-8"))
with open(VALUEABLE_MATCHES_FILE, encoding="utf-8") as f:
    valuable_data = json.load(f)

def make_val_key(entry):
    match = entry["match"]
    # Ensure the participant order matches your CSV: fighter_1, fighter_2
    p1, p2 = match["participants"]
    return (
        match["event"],
        match["date"],
        match["arm"],
        p1,
        p2
    )

# Build the lookup dictionary
valuable_lookup = {make_val_key(entry): entry["analysis"] for entry in valuable_data}

def get_age(athlete, event_date):
    age = athlete.get("age")
    if age:
        return age
    dob = athlete.get("date_of_birth")
    if not dob:
        return ""
    # Try all formats from most to least precise
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y-%m", "%Y"):
        try:
            dob_date = datetime.strptime(dob, fmt)
            # If only year is provided, use July 1 as birthday for estimation
            if fmt == "%Y":
                dob_date = dob_date.replace(month=7, day=1)
            elif fmt == "%Y-%m":
                dob_date = dob_date.replace(day=15)  # Middle of month
            break
        except ValueError:
            continue
    else:
        # None matched
        return ""
    try:
        event_dt = datetime.strptime(event_date, "%Y-%m-%d")
    except Exception:
        return ""
    # Calculate age
    age = event_dt.year - dob_date.year - ((event_dt.month, event_dt.day) < (dob_date.month, dob_date.day))
    return age


# Fuzzy matching for athlete names
athlete_names = list(athlete_data.keys())
def fuzzy_get_athlete(name, threshold=80):
    if name in athlete_data:
        return athlete_data[name]
    match, score = process.extractOne(name, athlete_names)
    if score >= threshold:
        print(f"[Fuzzy matched] '{name}' → '{match}' (score: {score})")
        return athlete_data[match]
    print(f"[❌ Missing athlete data] '{name}' (closest: '{match}', score={score})")
    return {"country": "Unknown", "pulling_style": ["Unknown"], "weight_kg": "Unknown"}

def get_zone(country):
    return "America" if normalize_country(country) in {c.title() for c in ZONE_A_COUNTRIES} else "RestOfWorld"

def get_travel_penalty(origin_country, event_country):
    if origin_country == "Unknown" or event_country == "Unknown":
        return 0
    return 1 if get_zone(origin_country) != get_zone(event_country) else 0

def get_travel_type(c1, c2):
    return "domestic" if get_zone(c1) == get_zone(c2) else "transatlantic"

def try_get_numeric(data, key):
    try:
        return int(data[key])
    except (ValueError, TypeError):
        return 0
# get styles success rates

def get_combo_success_pct(style1, style2):
    key = " + ".join(sorted([style1 or "Unknown", style2 or "Unknown"]))
    return style_combo_success_dict.get(key, None)

def get_athlete1_style_advantage_rate(style1, style2):
    # This is the specific rate of athlete1 dominant vs athlete2 dominant (directional)
    return style_vs_style_dict.get((style1 or "Unknown", style2 or "Unknown"), None)



# get gender of an athlete
def get_gender(athlete):
    return athlete.get("gender", "")

# Extract matches from events
def extract_matches(events, event_type):
    rows = []
    for event in events:
        date = event.get("event_date")
        title = event.get("event_title")
        event_location_country = event.get("event_location", "Unknown").split(",")[-1].strip()

        for m in event.get("matches", []):
            participants = m.get("participants", [])
            if len(participants) != 2:
                continue
            f1, f2 = participants
            winner = m.get("winner")
            if not winner:
                continue
            
            
            a1 = fuzzy_get_athlete(f1)
            a2 = fuzzy_get_athlete(f2)
            a1_country = a1.get("country", "Unknown")
            a2_country = a2.get("country", "Unknown")

            travels_1 = get_travel_penalty(a1_country, event_location_country)
            travels_2 = get_travel_penalty(a2_country, event_location_country)
            travel_type = get_travel_type(a1_country, a2_country)

            row = {
                "event": title,
                "league": event_type,
                "date": date,
                "fighter_1": f1,
                "fighter_2": f2,
                "winner": winner,
                "f1_age": get_age(a1, date),
                "f2_age": get_age(a2, date),
                "f1_style_dominant": a1["pulling_style"][0] if a1.get("pulling_style") and len(a1["pulling_style"]) > 0 else "Unknown",
                "f1_style_additional": a1["pulling_style"][1] if a1.get("pulling_style") and len(a1["pulling_style"]) > 1 else "",
                "f2_style_dominant": a2["pulling_style"][0] if a2.get("pulling_style") and len(a2["pulling_style"]) > 0 else "Unknown",
                "f2_style_additional": a2["pulling_style"][1] if a2.get("pulling_style") and len(a2["pulling_style"]) > 1 else "",
                "f1_weight": a1.get("weight_kg", "Unknown"),
                "f2_weight": a2.get("weight_kg", "Unknown"),
                "weight_advantage": (a1.get("weight_kg") - a2.get("weight_kg")) if isinstance(a1.get("weight_kg"), (int, float)) and isinstance(a2.get("weight_kg"), (int, float)) else None,
                "f1_height": a1.get("height_cm", None),
                "f2_height": a2.get("height_cm", None),
                "height_advantage": (
                    (a1.get("height_cm") - a2.get("height_cm"))
                    if a1.get("height_cm") is not None and a2.get("height_cm") is not None
                    else None
                ),
                "f1_country": a1_country,
                "f2_country": a2_country,
                "f1_travel_penalty": travels_1,
                "f2_travel_penalty": travels_2,
                "domestic_advantage": travels_2 - travels_1,
                "travel_type": travel_type,
                "label": 1 if winner == f1 else 0,
                "f1_style_combo_success_percent": get_combo_success_pct(
                    a1["pulling_style"][0] if a1.get("pulling_style") else "Unknown",
                    a2["pulling_style"][0] if a2.get("pulling_style") else "Unknown"
                ),
                "f2_style_combo_success_percent": get_combo_success_pct(
                    a2["pulling_style"][0] if a2.get("pulling_style") else "Unknown",
                    a1["pulling_style"][0] if a1.get("pulling_style") else "Unknown"
                ),
                "athlete1_style_advantage_rate": get_athlete1_style_advantage_rate(
                    a1["pulling_style"][0] if a1.get("pulling_style") else "Unknown",
                    a2["pulling_style"][0] if a2.get("pulling_style") else "Unknown"
                ),
                "f1_gender": get_gender(a1),
                "f2_gender": get_gender(a2),
                "f1_is_current_title_holder": is_current_title_holder(title, f1),
                "f2_is_current_title_holder": is_current_title_holder(title, f2),
                "f1_low_rank_predictions": count_low_rank_predictions(f1, title),
                "f1_high_rank_predictions": count_high_rank_predictions(f1, title),
                "f2_low_rank_predictions": count_low_rank_predictions(f2, title),
                "f2_high_rank_predictions": count_high_rank_predictions(f2, title)
                }
            rows.append(row)
    return rows

# Build dataset
df = pd.DataFrame(
    extract_matches(east_west_events, "EvW") +
    extract_matches(kott_events, "KOTT")
)

# Build win/loss travel stats
records = defaultdict(lambda: {"domestic": {"wins": 0, "losses": 0},
                               "transatlantic": {"wins": 0, "losses": 0}})

for _, row in df.iterrows():
    f1, f2, winner, tt = row["fighter_1"], row["fighter_2"], row["winner"], row["travel_type"]
    if winner == f1:
        records[f1][tt]["wins"] += 1
        records[f2][tt]["losses"] += 1
    else:
        records[f2][tt]["wins"] += 1
        records[f1][tt]["losses"] += 1

def safe_rate(w, l):
    return round(w / (w + l), 3) if w + l > 0 else 0.5

travel_stats = {
    name: {
        "domestic_win_rate": safe_rate(d["domestic"]["wins"], d["domestic"]["losses"]),
        "transatlantic_win_rate": safe_rate(d["transatlantic"]["wins"], d["transatlantic"]["losses"])
    }
    for name, d in records.items()
}

def get_stat_safe(name, stat):
    if name in travel_stats:
        return travel_stats[name].get(stat, 0.5)
    match, score = process.extractOne(name, list(travel_stats.keys()))
    if score >= 90:
        print(f"[TRAVEL RATE Fuzzy] '{name}' → '{match}' (score={score})")
        return travel_stats[match].get(stat, 0.5)
    print(f"[❌ Travel stat missing] '{name}' (closest: '{match}', score={score})")
    return 0.5

df["f1_domestic_win_rate"] = df["fighter_1"].apply(lambda x: get_stat_safe(x, "domestic_win_rate"))
df["f1_transatlantic_win_rate"] = df["fighter_1"].apply(lambda x: get_stat_safe(x, "transatlantic_win_rate"))
df["f2_domestic_win_rate"] = df["fighter_2"].apply(lambda x: get_stat_safe(x, "domestic_win_rate"))
df["f2_transatlantic_win_rate"] = df["fighter_2"].apply(lambda x: get_stat_safe(x, "transatlantic_win_rate"))

def get_valuable_features(row):
    key = (
        row["event"],
        row["date"],
        row.get("arm", "Right"),  # Or "Left" if that's more common for your data, or handle as needed
        row["fighter_1"],
        row["fighter_2"],
    )
    analysis = valuable_lookup.get(key, {})
    # Safely extract all numeric features, defaulting to 0 if missing
    return pd.Series({
        "num_shared_opponents_value": analysis.get("num_shared_opponents_value", 0),
        "mma_math_positive": analysis.get("mma_math_positive", 0),
        "mma_math_negative": analysis.get("mma_math_negative", 0),
        "has_head_to_head": analysis.get("has_head_to_head", 0),
        "head_to_head_result": analysis.get("head_to_head_result", 0),
        "num_second_order_valuable": analysis.get("num_second_order_valuable", 0),
        "second_order_mma_math_positive": analysis.get("second_order_mma_math_positive", 0),
        "second_order_mma_math_negative": analysis.get("second_order_mma_math_negative", 0),
    })
valuable_features = df.apply(get_valuable_features, axis=1)
df = pd.concat([df, valuable_features], axis=1)

df.to_csv(UPDATED_TRAINING_FEATURES_WITH_TRAVEL_STATS, index=False)



print(f"[✅] Recreated dataset with travel stats saved to: {UPDATED_TRAINING_FEATURES_WITH_TRAVEL_STATS}")
