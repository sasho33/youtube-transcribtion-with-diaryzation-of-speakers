import os
import json
import requests
import re
from pathlib import Path
import sys

# Append project root to sys.path
sys.path.append(str(Path(__file__).resolve().parents[1]))
from pipeline.config import OPENAI_API_KEY, TRANSCRIPT_DIR, EVW_EVENTS_FILE

API_URL = "https://api.openai.com/v1/chat/completions"
MODEL = "gpt-4o"

def extract_predictions_with_openai(event_title: str, filename: str):
    normalized_path = TRANSCRIPT_DIR / event_title / "normalized" / filename
    output_path = TRANSCRIPT_DIR / event_title / "chatgpt_identified"
    output_path.mkdir(parents=True, exist_ok=True)
    output_json_path = output_path / filename.replace(".txt", ".json")

    if output_json_path.exists():
        print(f"⏭️ Skipping {filename} — JSON already exists.")
        return output_json_path

    if not normalized_path.exists():
        raise FileNotFoundError(f"Transcript file not found: {normalized_path}")

    with normalized_path.open("r", encoding="utf-8") as f:
        transcript = f.read()

    with open(EVW_EVENTS_FILE, "r", encoding="utf-8") as f:
        all_events = json.load(f)

    event_record = next((e for e in all_events if e["event_title"] == event_title), None)
    if not event_record:
        raise ValueError(f"Event '{event_title}' not found in EVW_EVENTS_FILE.")

    matches = event_record.get("matches", [])
    match_summaries = "\n".join(
        [f"- {m['participants'][0]} vs {m['participants'][1]} (arm: {m['arm']}, weight: {m['weight_category']})"
         for m in matches]
    )

    system_prompt = f"""
You are an expert assistant in analyzing armwrestling podcasts.

You will receive a transcript and metadata. Your task is to:
1. Identify each speaker using filename and content. Speaker diarization might be noisy. Normalize speaker names.
2. Focus only on predictions and discussion related to the matches listed below from the event '{event_title}'.
3. Return structured JSON with:
   - speaker_mapping: e.g., "SPEAKER_00": "Devon Larratt"
   - date: null
   - For each speaker:
     - self_predictions: list of predictions about their own match
     - third_party_predictions: list of predictions about others, using:
         * match: [participant1, participant2]
         * arm: "Left" or "Right"
         * event
         * predicted_winner
         * predicted_score
         * prediction_summary
         * predicted_duration
         * style_conflict
         * opinion_about_athletes: dictionary of:
             - strength
             - health
             - previous_match_summary

Return only a JSON object.

List of matches for this event ({event_title}):
{match_summaries}

Filename: {filename}
"""

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": transcript}
        ],
        "temperature": 0.3,
        "max_tokens": 8192
    }

    print(f"📤 Requesting GPT-4o analysis for: {filename}")
    response = requests.post(API_URL, headers=headers, json=payload)
    response_data = response.json()

    if 'choices' in response_data and response_data['choices']:
        try:
            raw = response_data['choices'][0]['message']['content']
            cleaned = re.sub(r'^```(?:json)?|```$', '', raw.strip(), flags=re.MULTILINE).strip()
            cleaned = re.sub(r'\"{2,}', '\"', cleaned)
            cleaned = re.sub(r',\s*}', '}', cleaned)
            structured_json = json.loads(cleaned)

            with output_json_path.open("w", encoding="utf-8") as f:
                json.dump(structured_json, f, indent=2, ensure_ascii=False)
            print(f"✅ Saved structured predictions to: {output_json_path}")
            return output_json_path
        except json.JSONDecodeError:
            print("❌ Failed to parse GPT-4o response as JSON")
            raise
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            raise

    raise Exception("❌ GPT-4o API call failed:\n" + json.dumps(response_data, indent=2))


# Example usage
if __name__ == "__main__":
    try:
        event = "East vs West 17"
        file = "Georgi Tsvetkov EvW17 Podcast.txt"
        extract_predictions_with_openai(event, file)
    except Exception as e:
        print(f"Error: {str(e)}")
