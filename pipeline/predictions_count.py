import json
from pathlib import Path
import sys
from rapidfuzz import fuzz

sys.path.append(str(Path(__file__).resolve().parents[1]))
from pipeline.config import PREDICTION_SUMMARY_FILE


with open(PREDICTION_SUMMARY_FILE, 'r', encoding='utf-8') as f:
    predictor_summary = json.load(f)

low_ranked = {name for name, data in predictor_summary.items() if 58 <= data["success_rate"] < 70}
high_ranked = {name for name, data in predictor_summary.items() if data["success_rate"] >= 70}

FUZZ_THRESHOLD = 85

def _fuzzy_match(name1: str, name2: str) -> bool:
    return fuzz.ratio(name1.lower(), name2.lower()) >= FUZZ_THRESHOLD


def count_predictions(athlete_name: str, event_name: str, predictor_group: set) -> int:
    """
    Count predictions from predictor_summary.json favoring an athlete
    from a specific predictor group. Uses fuzzy matching (80 threshold) for names.
    Each predictor is counted only once. Only considers predictions matching the event name.
    """
    total_count = 0

    for predictor_name, predictor_data in predictor_summary.items():
        if predictor_name not in predictor_group:
            continue

        counted = False
        for prediction in predictor_data.get("results", []):
            # Strict match for event name
            if prediction.get("event", "") != event_name:
                continue

            participants = prediction.get("match", [])
            athlete_in_participants = any(_fuzzy_match(athlete_name, p) for p in participants)
            winner_matches = _fuzzy_match(prediction.get("predicted_winner", ""), athlete_name)
            predictor_in_participants = any(_fuzzy_match(predictor_name, p) for p in participants)

            if (
                athlete_in_participants and
                winner_matches and
                not predictor_in_participants
            ):
                # print(f"Predictor: {predictor_name}")
                total_count += 1
                counted = True
                break  # Only count this predictor once

    return total_count

def count_low_rank_predictions(athlete_name: str, event_name: str) -> int:
    """Count predictions for athlete from low-ranked predictors using predictor_summary.json."""
    return count_predictions(athlete_name, event_name, low_ranked)

def count_high_rank_predictions(athlete_name: str, event_name: str) -> int:
    """Count predictions for athlete from high-ranked predictors using predictor_summary.json."""
    return count_predictions(athlete_name, event_name, high_ranked)
def count_all_predictions(athlete_name: str, event_name: str) -> int:
    """
    Count predictions from all predictors in predictor_summary.json favoring an athlete.
    Uses fuzzy matching for names.
    Each predictor is counted only once. Only considers predictions matching the event name.
    """
    total_count = 0

    for predictor_name, predictor_data in predictor_summary.items():
        counted = False
        for prediction in predictor_data.get("results", []):
            # Strict match for event name
            if prediction.get("event", "") != event_name:
                continue

            participants = prediction.get("match", [])
            athlete_in_participants = any(_fuzzy_match(athlete_name, p) for p in participants)
            winner_matches = _fuzzy_match(prediction.get("predicted_winner", ""), athlete_name)
            predictor_in_participants = any(_fuzzy_match(predictor_name, p) for p in participants)

            if (
                athlete_in_participants and
                winner_matches and
                not predictor_in_participants
            ):
                total_count += 1
                counted = True
                break  # Only count this predictor once

    return total_count

def count_all_prediction_vote_diff(athlete1: str, athlete2: str, event_name: str) -> int:
    """
    Returns the difference: (all predictor votes for athlete1) - (all predictor votes for athlete2)
    """
    return count_all_predictions(athlete1, event_name) - count_all_predictions(athlete2, event_name)

# Example usage:
# print(count_low_rank_predictions("Betkili Oniani", "East vs West 16"))
# print(count_high_rank_predictions("Betkili Oniani", "East vs West 16"))
if __name__ == "__main__":
    print(count_low_rank_predictions("Irakli Zirakashvili", "East vs West 11"))
    print(count_high_rank_predictions("Irakli Zirakashvili", "East vs West 11"))