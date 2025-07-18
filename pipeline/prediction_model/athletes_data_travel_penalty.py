import json
from pathlib import Path
import sys
import pandas as pd
from collections import defaultdict
from fuzzywuzzy import process

# Setup project path and import config
sys.path.append(str(Path(__file__).resolve().parents[2]))
from pipeline.config import (
    EVW_EVENTS_FILE,
    KOTT_EVENTS_FILE,
    TRAVEL_EFFECT_FILE,
    UNIQUE_ATHLETES_WITH_DATA_FILE,
    UPDATED_TRAINING_FEATURES_WITH_TRAVEL_STATS
)

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
                "f1_style": ", ".join(a1["pulling_style"]) if isinstance(a1.get("pulling_style"), list) else "Unknown",
                "f2_style": ", ".join(a2["pulling_style"]) if isinstance(a2.get("pulling_style"), list) else "Unknown",
                "f1_weight": a1.get("weight_kg", "Unknown"),
                "f2_weight": a2.get("weight_kg", "Unknown"),
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
                "label": 1 if f1 == winner else 0
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

df.to_csv(UPDATED_TRAINING_FEATURES_WITH_TRAVEL_STATS, index=False)
print(f"[✅] Recreated dataset with travel stats saved to: {UPDATED_TRAINING_FEATURES_WITH_TRAVEL_STATS}")
