import json
from pathlib import Path
from collections import defaultdict
import sys

# Append project root for imports
sys.path.append(str(Path(__file__).resolve().parents[1]))
from pipeline.config import TRANSCRIPT_DIR, EVW_EVENTS_FILE

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

def load_event_results():
    with open(EVW_EVENTS_FILE, "r", encoding="utf-8") as f:
        all_events = json.load(f)

    results = {}  # (event, [name1, name2]) → winner
    for event in all_events:
        event_title = event["event_title"]
        for match in event["matches"]:
            key = (event_title, tuple(sorted(match["participants"])))
            results[key] = match.get("winner")
    return results

def normalize_name(name: str):
    return name.strip().lower()

def evaluate_predictions(results):
    predictor_stats = defaultdict(lambda: {"total": 0, "correct": 0})

    for event_dir in TRANSCRIPT_DIR.iterdir():
        identified_dir = event_dir / "Identified"
        if not identified_dir.exists():
            continue

        for json_file in identified_dir.glob("*.json"):
            with open(json_file, "r", encoding="utf-8") as f:
                try:
                    data = json.load(f)
                except Exception as e:
                    print(f"❌ Skipping invalid JSON file: {json_file}")
                    continue

            predictions = data.get("predictions", {})
            for speaker, blocks in predictions.items():
                for section in ["self_predictions", "third_party_predictions"]:
                    for pred in blocks.get(section, []):
                        event = pred.get("event")
                        participants = pred.get("match")
                        predicted = pred.get("predicted_winner")

                        if not event or not participants or not predicted:
                            continue

                        key = (event, tuple(sorted(participants)))
                        actual = results.get(key)

                        if actual:
                            predictor_stats[speaker]["total"] += 1
                            if normalize_name(predicted) == normalize_name(actual):
                                predictor_stats[speaker]["correct"] += 1

    return predictor_stats

def save_predictor_stats(stats):
    for speaker, counts in stats.items():
        out_path = DATA_DIR / f"{speaker.replace(' ', '_')}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump({
                "predictor": speaker,
                "total_predictions": counts["total"],
                "correct_predictions": counts["correct"]
            }, f, indent=2, ensure_ascii=False)
        print(f"✅ Saved summary for {speaker} → {out_path.name}")

if __name__ == "__main__":
    print("📥 Loading event results...")
    result_map = load_event_results()
    print("🔍 Evaluating predictions...")
    stats = evaluate_predictions(result_map)
    print("📤 Saving summaries...")
    save_predictor_stats(stats)
    print("✅ All predictor summaries saved.")
