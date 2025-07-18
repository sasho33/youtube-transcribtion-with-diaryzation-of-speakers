import json
from collections import defaultdict
from pathlib import Path
import sys
from difflib import get_close_matches

# Make sure root project dir is on path for config import
sys.path.append(str(Path(__file__).resolve().parents[1]))
from pipeline.config import EVW_EVENTS_FILE, KOTT_EVENTS_FILE, DATA_DIR

def normalize_country(raw_location: str) -> str:
    location = raw_location.lower()

    if "usa" in location or "united states" in location:
        return "United States Of America"
    elif "georgia" in location:
        return "Georgia"
    elif "turkey" in location or "türkiye" in location or "istanbul" in location:
        return "Turkey"
    elif "canada" in location:
        return "Canada"
    elif "brazil" in location:
        return "Brazil"
    elif "costa rica" in location:
        return "Costa Rica"

    return raw_location.strip().title()


# Load athlete → country mapping
athlete_country_path = DATA_DIR / "athletes_country_map.json"
with open(athlete_country_path, "r", encoding="utf-8") as f:
    athlete_country_map = json.load(f)
print(f"📌 Loaded {len(athlete_country_map)} athlete-country mappings.")

# Define geographic zones
america_keywords = {"United States Of America", "Canada", "Brazil", "Costa Rica"}
zone_map = {country: "americas" for country in america_keywords}
for country in set(athlete_country_map.values()):
    if country not in zone_map:
        zone_map[country] = "rest"

# Load event data
all_events = []
for file_path in [EVW_EVENTS_FILE, KOTT_EVENTS_FILE]:
    if not file_path.exists():
        print(f"❌ File not found: {file_path}")
        continue
    with open(file_path, "r", encoding="utf-8") as f:
        events = json.load(f)
        print(f"📦 Loaded {len(events)} events from {file_path.name}")
        all_events.extend(events)

# Stats structure
athlete_stats = defaultdict(lambda: {
    "domestic_matches": 0,
    "domestic_matches_win": 0,
    "transatlantic_matches": 0,
    "transatlantic_matches_win": 0
})

# Analyze each match
event_count = 0
match_count = 0
valid_match_count = 0

for event in all_events:
    event_count += 1
    event_country_raw = event.get("event_location", "")
    event_country = normalize_country(event_country_raw)
    matches = event.get("matches", [])

    for match in matches:
        match_count += 1
        participants = match.get("participants", [])
        winner = match.get("winner")

        if len(participants) != 2 or not winner:
            continue

        valid_match_count += 1

        for athlete_name in participants:
            athlete_country = athlete_country_map.get(athlete_name)

            # Try fuzzy match if no exact match
            if not athlete_country:
                close = get_close_matches(athlete_name, athlete_country_map.keys(), n=1, cutoff=0.80)
                if close:
                    matched_name = close[0]
                    athlete_country = athlete_country_map[matched_name]
                    print(f"🔄 Fuzzy matched '{athlete_name}' → '{matched_name}'")
                    athlete_name = matched_name
                else:
                    print(f"⚠️ No country info for: {athlete_name}")
                    continue

            athlete_zone = zone_map.get(athlete_country)
            event_zone = zone_map.get(event_country)

            is_domestic = athlete_zone == event_zone
            won = (winner == athlete_name)

            stats = athlete_stats[athlete_name]
            if is_domestic:
                stats["domestic_matches"] += 1
                if won:
                    stats["domestic_matches_win"] += 1
            else:
                stats["transatlantic_matches"] += 1
                if won:
                    stats["transatlantic_matches_win"] += 1

print(f"\n✅ Processed {event_count} events, {match_count} matches, {valid_match_count} valid matches.")
print(f"📟 Athletes with stats: {len(athlete_stats)}")

# Format for output
output = {}
for athlete, stats in athlete_stats.items():
    output[athlete] = {
        "domestic_matches": stats["domestic_matches"],
        "domestic_matches_win_rate": round(stats["domestic_matches_win"] / stats["domestic_matches"], 2) if stats["domestic_matches"] else None,
        "transatlantic_matches": stats["transatlantic_matches"],
        "transatlantic_matches_win_rate": round(stats["transatlantic_matches_win"] / stats["transatlantic_matches"], 2) if stats["transatlantic_matches"] else None,
    }

# Save results
output_file = DATA_DIR / "travel_effect_analysis.json"
with open(output_file, "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f"\n📂 Saved travel effect analysis to: {output_file}")