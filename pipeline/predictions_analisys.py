import json
from pathlib import Path
from difflib import SequenceMatcher
import sys

# Adjust import path for config
sys.path.append(str(Path(__file__).resolve().parents[1]))
from pipeline.config import TRANSCRIPT_DIR, EVW_EVENTS_FILE, PREDICTIONS_DIR

def similar(a, b):
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

def load_event_data():
    print(f"📂 Loading event data from {EVW_EVENTS_FILE}")
    with open(EVW_EVENTS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def load_transcripts():
    all_transcripts = list(Path(TRANSCRIPT_DIR).rglob("Identified/*.json"))
    return all_transcripts

def find_actual_match(event_data, event_name, match_names, arm):
    for ev in event_data:
        if ev.get("event") != event_name:
            continue
        for match in ev.get("matches", []):
            m_names = match.get("match", [])
            if (
                sorted(name.lower() for name in m_names) == sorted(name.lower() for name in match_names)
                and match.get("arm", "").lower() == arm.lower()
            ):
                return match
    return None

def flatten_predictions(transcript):
    results = {}
    # Format 1: full 'predictions' list
    if isinstance(transcript.get("predictions"), list):
        for block in transcript["predictions"]:
            speaker = block.get("speaker")
            results.setdefault(speaker, [])
            results[speaker].extend(block.get("self_predictions", []))
            results[speaker].extend(block.get("third_party_predictions", []))

    # Format 2: self_predictions and third_party_predictions dictionaries
    for pred_type in ["self_predictions", "third_party_predictions"]:
        block = transcript.get(pred_type)
        if isinstance(block, dict):
            for speaker, preds in block.items():
                results.setdefault(speaker, [])
                results[speaker].extend(preds)
    return results

def analyze_predictions(transcript_path, event_name, event_data):
    print(f"📄 Loading transcript: {transcript_path}")
    with open(transcript_path, "r", encoding="utf-8") as f:
        transcript = json.load(f)

    speaker_predictions = flatten_predictions(transcript)
    all_results = {}

    for speaker, predictions in speaker_predictions.items():
        all_results.setdefault(speaker, [])
        for pred in predictions:
            match_names = pred.get("match", [])
            arm = pred.get("arm", "")
            if not match_names or not arm:
                continue

            actual = find_actual_match(event_data, event_name, match_names, arm)
            if not actual:
                print(f"⚠️ Match not found in event data: {match_names} for {event_name}")
                continue

            predicted_winner = pred.get("predicted_winner")
            predicted_score = pred.get("predicted_score")
            actual_winner = actual.get("winner")
            actual_score = actual.get("score")

            result = {
                "event": event_name,
                "match": match_names,
                "arm": arm,
                "predicted_winner": predicted_winner,
                "predicted_score": predicted_score,
                "actual_winner": actual_winner,
                "actual_score": actual_score,
                "result": (
                    "Correct" if predicted_winner and predicted_winner.lower() == actual_winner.lower() else "Incorrect"
                ),
            }

            # Score comparison
            if predicted_score and actual_score:
                result["score_match"] = "Correct" if predicted_score == actual_score else "Incorrect"

            all_results[speaker].append(result)

    return all_results

def main():
    event_data = load_event_data()
    transcripts = load_transcripts()

    for transcript_path in transcripts:
        event_name = transcript_path.parts[-3]  # e.g., "East vs West 11"
        predictions_result = analyze_predictions(transcript_path, event_name, event_data)

        if predictions_result:
            for speaker, results in predictions_result.items():
                safe_speaker = speaker if speaker else f"unknown_{hash(event_name)}"
                filename = f"{safe_speaker.replace(' ', '_').lower()}_{event_name.replace(' ', '_').lower()}_predictions.json"

                output_path = Path(PREDICTIONS_DIR) / filename
                output_path.parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump({speaker: results}, f, indent=2, ensure_ascii=False)
                print(f"✅ Saved predictions for {speaker} to {output_path}")
        else:
            print("❌ No predictions found.")

if __name__ == "__main__":
    main()
