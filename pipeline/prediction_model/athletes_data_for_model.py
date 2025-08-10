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
    UNIQUE_ATHLETES_WITH_DATA_FILE,
    UPDATED_TRAINING_FEATURES_WITH_TRAVEL_STATS,
    VALUEABLE_MATCHES_FILE,
    STYLES_COMBO_RATES_FILE
)
from pipeline.prediction_model.title_holder import is_current_title_holder
from pipeline.predictions_count import count_low_rank_predictions, count_high_rank_predictions, count_all_predictions

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
    style_combo_success_dict[(entry["style_1"], entry["style_2"])] = entry.get("success_pct")



# Normalized American countries (Zone A)
ZONE_A_COUNTRIES = {
    "United States", "USA", "Canada", "Mexico", "Brazil", "Argentina", "Colombia", "Chile",
    "Peru", "Venezuela", "Ecuador", "Uruguay", "Paraguay", "Panama", "Cuba",
    "El Salvador", "Guatemala", "Honduras", "Nicaragua", "Bolivia", "Costa Rica",
    "Dominican Republic", "Haiti", "Jamaica", "Trinidad and Tobago", "Japan"
}

def normalize_country(name):
    name = name.strip().lower()
    if name in {"usa", "united states", "united states of america"}:
        return "USA"
    if name == "uk":
        return "United Kingdom"
    if name == "turkey" or name == "türkiye":
        return "Turkey"
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
    # Compare ALL countries as upper-case (or lower-case)
    AMERICAS = {c.strip().lower() for c in ZONE_A_COUNTRIES}
    return "America" if normalize_country(country).lower() in AMERICAS else "RestOfWorld"

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
    key = ((style1 or "Unknown").strip(), (style2 or "").strip())
    if key not in style_combo_success_dict:
        print(f"[Combo Rate] No entry for {key}")
    return style_combo_success_dict.get(key, None)

def get_athlete1_style_advantage_rate(style1, style2):
    # This is the specific rate of athlete1 dominant vs athlete2 dominant (directional)
    return style_vs_style_dict.get((style1 or "Unknown", style2 or "Unknown"), None)



# get gender of an athlete
def get_gender(athlete):
    return athlete.get("gender", "")



def parse_date(date_str):
    """
    Robust date parser for YYYY-MM-DD, YYYY/MM/DD, YYYY, and other variants.
    """
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%B %d, %Y", "%b %d, %Y", "%Y-%m", "%Y"):
        try:
            return datetime.strptime(date_str, fmt)
        except Exception:
            continue
    return None

def get_athlete_match_history(athlete_profile, up_to_date):
    """
    Returns list of matches (as dict) before up_to_date, sorted by date (oldest first).
    """
    matches = []
    for opponent, matches_list in athlete_profile.get("matches", {}).items():
        for match in matches_list:
            match_date = parse_date(match.get("date", ""))
            if not match_date or match_date >= up_to_date:
                continue
            matches.append({
                "date": match_date,
                "arm": match.get("arm", "Unknown"),
                "result": match.get("result", ""),  # "Win" or "Lost"
            })
    matches.sort(key=lambda x: x["date"])
    return matches

def calc_streaks_and_winrate(matches):
    """
    matches: List of matches sorted oldest to newest.
    Returns: (left_winning_streak, right_winning_streak, winrate_last_5)
    """
    # For streaks, count most recent (last) consecutive W/L for each arm
    left_streak, right_streak = 0, 0

    # We'll process in reverse for streaks (most recent first)
    last_left, last_right = None, None
    for m in reversed(matches):
        if m["arm"] == "Left":
            if last_left is None:
                last_left = m["result"]
                left_streak = 1 if m["result"] == "Win" else -1 if m["result"] == "Lost" else 0
            elif m["result"] == last_left:
                left_streak += 1 if last_left == "Win" else -1 if last_left == "Lost" else 0
            else:
                break
    for m in reversed(matches):
        if m["arm"] == "Right":
            if last_right is None:
                last_right = m["result"]
                right_streak = 1 if m["result"] == "Win" else -1 if m["result"] == "Lost" else 0
            elif m["result"] == last_right:
                right_streak += 1 if last_right == "Win" else -1 if last_right == "Lost" else 0
            else:
                break

    # Winrate last 5 (any arm)
    recent = matches[-5:]
    wins = sum(1 for m in recent if m["result"] == "Win")
    winrate_last_5 = wins / len(recent) if len(recent) else 0.5

    return left_streak, right_streak, winrate_last_5

def get_athlete_form_features(athlete_name, athlete_data, match_date):
    """
    Returns dict with 'left_winning_streak', 'right_winning_streak', 'winrate_last_5'.
    Streaks only set if abs(streak) > 1, winrate set only if at least 2 recent matches.
    """
    athlete = athlete_data.get(athlete_name)
    if not athlete:
        return {
            "left_winning_streak": 0,
            "right_winning_streak": 0,
            "winrate_last_5": 0.5
        }
    matches = get_athlete_match_history(athlete, match_date)
    left_streak, right_streak, winrate_last_5 = calc_streaks_and_winrate(matches)
    # Only keep streaks if >1 in absolute value
    left_streak = left_streak if abs(left_streak) > 1 else 0
    right_streak = right_streak if abs(right_streak) > 1 else 0

    # Only set winrate if at least 2 matches
    recent = matches[-5:]
    winrate = round(winrate_last_5, 2) if len(recent) >= 1 else 0.5

    return {
        "left_winning_streak": left_streak,
        "right_winning_streak": right_streak,
        "winrate_last_5": winrate
    }

def get_days_from_last_match(athlete_profile, event_date):
    """
    Returns days since last match (before event_date).
    If no previous match, returns 0.
    """
    from datetime import datetime
    def parse_date(date_str):
        for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%B %d, %Y", "%b %d, %Y", "%Y-%m", "%Y"):
            try:
                return datetime.strptime(date_str, fmt)
            except Exception:
                continue
        return None

    event_dt = parse_date(event_date)
    if not event_dt:
        return 0

    last_match_date = None
    for matches_list in athlete_profile.get("matches", {}).values():
        for match in matches_list:
            match_date = parse_date(match.get("date", ""))
            if match_date and match_date < event_dt:
                if not last_match_date or match_date > last_match_date:
                    last_match_date = match_date
    if last_match_date:
        return (event_dt - last_match_date).days
    return 0

def extract_country_from_location(location):
    """
    Extracts the country from an event_location string.
    Assumes last comma-separated part is country.
    """
    if not location or not isinstance(location, str):
        return "Unknown"
    return location.split(",")[-1].strip()


def compute_domestic_transatlantic_winrates_single(athlete_profile, athlete_country, up_to_date=None):
    home_zone = get_zone(athlete_country)
    domestic_wins = domestic_total = trans_wins = trans_total = 0

    for opponent, matches_list in athlete_profile.get("matches", {}).items():
        for match in matches_list:
            match_date = parse_date(match.get("date", ""))
            if up_to_date and (not match_date or match_date >= up_to_date):
                continue
            # Fix: extract the country from event_location
            event_location = match.get("event_location")
            event_country = extract_country_from_location(event_location)
            event_country = normalize_country(event_country)
            event_zone = get_zone(event_country)
            mtype = "domestic" if event_zone == home_zone else "transatlantic"
            result = match.get("result", "")
            if mtype == "domestic":
                domestic_total += 1
                if result == "Win":
                    domestic_wins += 1
            else:
                trans_total += 1
                if result == "Win":
                    trans_wins += 1

    return {
        "domestic_win_rate": round(domestic_wins / domestic_total, 3) if domestic_total > 0 else 0.5,
        "transatlantic_win_rate": round(trans_wins / trans_total, 3) if trans_total > 0 else 0.5,
        "domestic_wins": domestic_wins,
        "domestic_total": domestic_total,
        "transatlantic_wins": trans_wins,
        "transatlantic_total": trans_total
    }
# Extract matches from events
def extract_matches(events, event_type):
    rows = []
    for event in events:
        date = event.get("event_date")
        title = event.get("event_title")
        event_location_country_raw = event.get("event_location", "Unknown").split(",")[-1].strip()
        event_location_country = normalize_country(event_location_country_raw)
        match_date = parse_date(date)  # match_date_string from your row

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
            a1_country = normalize_country(a1.get("country", "Unknown"))
            a2_country = normalize_country(a2.get("country", "Unknown"))

            travels_1 = get_travel_penalty(a1_country, event_location_country)
            travels_2 = get_travel_penalty(a2_country, event_location_country)
            travel_type = get_travel_type(a1_country, a2_country)

            f1_form = get_athlete_form_features(f1, athlete_data, match_date)
            f2_form = get_athlete_form_features(f2, athlete_data, match_date)
            match_arm = m.get("arm", "Unknown")

            row = {
                "event": title,
                "league": event_type,
                "date": date,
                "event_location_country": event_location_country,
                "fighter_1": f1,
                "fighter_2": f2,
                "winner": winner,
                "match_arm": match_arm,
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
                    a1["pulling_style"][1] if a1.get("pulling_style") and len(a1["pulling_style"]) > 1 else ""
                ),
                "f2_style_combo_success_percent": get_combo_success_pct(
                    a2["pulling_style"][0] if a2.get("pulling_style") else "Unknown",
                    a2["pulling_style"][1] if a2.get("pulling_style") and len(a2["pulling_style"]) > 1 else ""
                ),
                "athlete1_style_advantage_rate":
                    50 if (
                        a1.get("pulling_style") and a2.get("pulling_style") and
                        len(a1["pulling_style"]) > 0 and len(a2["pulling_style"]) > 0 and
                        a1["pulling_style"][0] == a2["pulling_style"][0]
                    )
                    else get_athlete1_style_advantage_rate(
                        a1["pulling_style"][0] if a1.get("pulling_style") else "Unknown",
                        a2["pulling_style"][0] if a2.get("pulling_style") else "Unknown"
                    ),
                "f1_gender": get_gender(a1),
                "f2_gender": get_gender(a2),
                "f1_is_current_title_holder": is_current_title_holder(title, f1),
                "f2_is_current_title_holder": is_current_title_holder(title, f2),
                "f1_days_from_last_match": get_days_from_last_match(a1, date),
                "f2_days_from_last_match": get_days_from_last_match(a2, date),
                "f1_low_rank_predictions": count_low_rank_predictions(f1, title),
                "f1_high_rank_predictions": count_high_rank_predictions(f1, title),
                "f2_low_rank_predictions": count_low_rank_predictions(f2, title),
                "f2_high_rank_predictions": count_high_rank_predictions(f2, title),
                "f1_all_rank_predictions": count_all_predictions(f1, title),
                "f2_all_rank_predictions": count_all_predictions(f2, title),
                "f1_left_winning_streak": f1_form["left_winning_streak"],
                "f1_right_winning_streak": f1_form["right_winning_streak"],
                "f1_winrate_last_5": f1_form["winrate_last_5"],
                "f2_left_winning_streak": f2_form["left_winning_streak"],
                "f2_right_winning_streak": f2_form["right_winning_streak"],
                "f2_winrate_last_5": f2_form["winrate_last_5"],
                }
            rows.append(row)
    return rows

# Build dataset
df = pd.DataFrame(
    extract_matches(east_west_events, "EvW") +
    extract_matches(kott_events, "KOTT")
)

event_name = "East vs West 18"
# First, build the athlete stats (using the same method as in the function, but store counts not just rates)
from collections import defaultdict

zone_a = {normalize_country(c) for c in ZONE_A_COUNTRIES}

def get_zone(country):
    return "America" if normalize_country(country) in zone_a else "RestOfWorld"

# Collect win/loss by type for each athlete
win_stats = defaultdict(lambda: {"domestic": [0,0], "transatlantic": [0,0]})

for _, row in df.iterrows():
    f1 = row["fighter_1"].strip().lower()
    f2 = row["fighter_2"].strip().lower()
    winner = row["winner"].strip().lower()
    event_country = normalize_country(row["event_location_country"])
    f1_country = normalize_country(row["f1_country"])
    f2_country = normalize_country(row["f2_country"])
    event_zone = get_zone(event_country)
    f1_zone = get_zone(f1_country)
    f2_zone = get_zone(f2_country)

    # FIGHTER 1
    mtype1 = "domestic" if event_zone == f1_zone else "transatlantic"
    if winner == f1:
        win_stats[f1][mtype1][0] += 1
    win_stats[f1][mtype1][1] += 1

    # FIGHTER 2
    mtype2 = "domestic" if event_zone == f2_zone else "transatlantic"
    if winner == f2:
        win_stats[f2][mtype2][0] += 1
    win_stats[f2][mtype2][1] += 1

# Now, get all athletes in East vs West 18
participants = set(df.loc[df["event"] == event_name, "fighter_1"].str.lower()) | set(df.loc[df["event"] == event_name, "fighter_2"].str.lower())



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
        # "num_second_order_valuable": analysis.get("num_second_order_valuable", 0),
        "second_order_mma_math_difference": analysis.get("second_order_mma_math_difference", 0),
        "second_order_mma_math_positive": analysis.get("second_order_mma_math_positive", 0),
        "second_order_mma_math_negative": analysis.get("second_order_mma_math_negative", 0),
    })
valuable_features = df.apply(get_valuable_features, axis=1)
df = pd.concat([df, valuable_features], axis=1)


def compute_athlete_domestic_transatlantic_winrates(df):
    """
    Calculates, for each athlete:
    - domestic win rate: matches held in their home zone
    - transatlantic win rate: matches held outside their home zone
    and attaches these as new columns to the DataFrame (for both f1 and f2).
    """
    # Helper: determine zone (America vs RestOfWorld)
    zone_a = {c.strip().lower() for c in ZONE_A_COUNTRIES}

    def get_zone(country):
        return "America" if country.lower() in zone_a else "RestOfWorld"

    win_stats = {}

    for _, row in df.iterrows():
        # normalize names and countries
        f1 = row["fighter_1"].strip().lower()
        f2 = row["fighter_2"].strip().lower()
        winner = row["winner"].strip().lower()
        event_country = normalize_country(row["event_location_country"])
        f1_country = normalize_country(row["f1_country"])
        f2_country = normalize_country(row["f2_country"])
        # zones
        event_zone = get_zone(event_country)
        f1_zone = get_zone(f1_country)
        f2_zone = get_zone(f2_country)

        # FIGHTER 1
        if f1 not in win_stats:
            win_stats[f1] = {"domestic": [0,0], "transatlantic": [0,0]}
        mtype = "domestic" if event_zone == f1_zone else "transatlantic"
        if winner == f1:
            win_stats[f1][mtype][0] += 1
        win_stats[f1][mtype][1] += 1

        # FIGHTER 2
        if f2 not in win_stats:
            win_stats[f2] = {"domestic": [0,0], "transatlantic": [0,0]}
        mtype = "domestic" if event_zone == f2_zone else "transatlantic"
        if winner == f2:
            win_stats[f2][mtype][0] += 1
        win_stats[f2][mtype][1] += 1

    # Now convert to win rates
    win_rates = {}
    for name, stats in win_stats.items():
        dw, dtot = stats["domestic"]
        tw, ttot = stats["transatlantic"]
        win_rates[name] = {
            "domestic": round(dw / dtot, 3) if dtot > 0 else 0.5,
            "transatlantic": round(tw / ttot, 3) if ttot > 0 else 0.5
        }

    def get_rate(name, typ):
        return win_rates.get(name.strip().lower(), {}).get(typ, 0.5)

    # Add new columns
    df["f1_domestic_win_rate"] = df.apply(lambda r: get_rate(r["fighter_1"], "domestic"), axis=1)
    df["f1_transatlantic_win_rate"] = df.apply(lambda r: get_rate(r["fighter_1"], "transatlantic"), axis=1)
    df["f2_domestic_win_rate"] = df.apply(lambda r: get_rate(r["fighter_2"], "domestic"), axis=1)
    df["f2_transatlantic_win_rate"] = df.apply(lambda r: get_rate(r["fighter_2"], "transatlantic"), axis=1)

    return df

df = compute_athlete_domestic_transatlantic_winrates(df)

df.to_csv(UPDATED_TRAINING_FEATURES_WITH_TRAVEL_STATS, index=False)



print(f"[✅] Recreated dataset with travel stats saved to: {UPDATED_TRAINING_FEATURES_WITH_TRAVEL_STATS}")

