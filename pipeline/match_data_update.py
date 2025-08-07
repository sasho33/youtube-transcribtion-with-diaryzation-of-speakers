import json
import sys
from pathlib import Path
from collections import defaultdict
from rapidfuzz import process, fuzz

# Import config with sys.path trick
sys.path.append(str(Path(__file__).resolve().parents[1]))
from pipeline.config import EVW_EVENTS_FILE, KOTT_EVENTS_FILE, UNIQUE_ATHLETES_WITH_DATA_FILE

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(data, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def normalize_name(name):
    return name.strip().lower()

def extract_matches_from_events(events_data):
    matches_by_athlete = defaultdict(list)
    for event in events_data:
        event_title = event.get("event_title", "")
        event_date = event.get("event_date", "")
        for match in event.get("matches", []):
            participants = match["participants"]
            for i, athlete in enumerate(participants):
                opponent = participants[1-i]
                result = "Win" if match.get("winner") == athlete else "Lost"
                matches_by_athlete[normalize_name(athlete)].append({
                    "athlete": athlete,
                    "opponent": opponent,
                    "arm": match.get("arm", ""),
                    "date": event_date,
                    "result": result,
                    "score": match.get("score", ""),
                    "event": event_title,
                    "event_location": event.get("event_location", ""),
                })
    return matches_by_athlete

def compute_win_loss(matches):
    record = {"right": {"wins": 0, "losses": 0}, "left": {"wins": 0, "losses": 0}}
    for match in matches:
        arm = match["arm"].strip().lower()
        if "right" in arm:
            arm_key = "right"
        elif "left" in arm:
            arm_key = "left"
        else:
            continue
        if match["result"] == "Win":
            record[arm_key]["wins"] += 1
        elif match["result"] == "Lost":
            record[arm_key]["losses"] += 1
    return record

def main():
    athletes = load_json(UNIQUE_ATHLETES_WITH_DATA_FILE)
    evw_events = load_json(EVW_EVENTS_FILE)
    kott_events = load_json(KOTT_EVENTS_FILE)

    # All names in the main athlete file
    athlete_keys = list(athletes.keys())
    normalized_athlete_keys = [normalize_name(name) for name in athlete_keys]

    # Build matches from both event files
    all_matches = extract_matches_from_events(evw_events)
    kott_matches = extract_matches_from_events(kott_events)
    for k, v in kott_matches.items():
        all_matches[k].extend(v)

    # Fuzzy mapping: only for athlete name between events and main athlete file
    fuzzy_map = {}
    for event_name in all_matches:
        match, score, idx = process.extractOne(
            event_name,
            normalized_athlete_keys,
            scorer=fuzz.token_sort_ratio,
        )
        if score >= 90:
            fuzzy_map[event_name] = athlete_keys[idx]

    # For each athlete, replace matches/win_loss_record using only fuzzy-matched athlete name
    for athlete_name, athlete_data in athletes.items():
        matches = []
        # Find all event keys mapped to this athlete_name
        for event_norm_name, real_name in fuzzy_map.items():
            if real_name == athlete_name:
                matches.extend(all_matches[event_norm_name])
        # Build the matches dict: key = opponent, value = match info
        matches_dict = defaultdict(list)
        for match in matches:
            print(match)
            matches_dict[match["opponent"]].append({
                "arm": match["arm"],
                "date": match["date"],
                "event": match["event"],
                "result": match["result"],
                "score": match["score"],
                "event_title": match["event"],
                "event_location": match["event_location"]
            })
        athlete_data["matches"] = matches_dict
        athlete_data["win_loss_record"] = compute_win_loss(matches)

    save_json(athletes, UNIQUE_ATHLETES_WITH_DATA_FILE)
    print("Athlete matches and win/loss records updated using fuzzy matching on athlete names only.")

if __name__ == "__main__":
    main()
