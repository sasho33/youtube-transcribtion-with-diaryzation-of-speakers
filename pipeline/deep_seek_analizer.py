import os
import json
import requests
import re
from pathlib import Path
import sys

# Append the project root to path and import config
sys.path.append(str(Path(__file__).resolve().parents[1]))
from pipeline.config import SHALLOWSEEK_APIK, TRANSCRIPT_DIR, EVW_EVENTS_FILE

# Configuration
DEEPSEEK_API_KEY = SHALLOWSEEK_APIK
API_URL = "https://api.deepseek.com/v1/chat/completions"
MODEL = "deepseek-reasoner"

def extract_predictions_as_json(event_title: str, filename: str):
    """
    Process a normalized transcript to identify speakers and extract match predictions.
    Saves result as JSON in Identified/ folder under the same event.
    """
    normalized_path = TRANSCRIPT_DIR / event_title / "normalized" / filename
    output_path = TRANSCRIPT_DIR / event_title / "Identified"
    output_path.mkdir(parents=True, exist_ok=True)
    output_json_path = output_path / filename.replace(".txt", ".json")

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
        [
            f"- {m['participants'][0]} vs {m['participants'][1]} (arm: {m['arm']}, weight: {m['weight_category']})"
            for m in matches
        ]
    )

    # Escape nested braces for f-string compatibility
    example_json = """{
  \"SPEAKER_00\": \"Devon Larratt\",
  \"SPEAKER_01\": \"Engin Terzi\",
  \"Devon Larratt\": [
    {
      \"event\": \"%s\",
      \"participants\": [\"Devon Larratt\", \"Corey West\"],
      \"predicted_winner\": \"Devon Larratt\",
      \"prediction_summary\": \"I believe I can stop him and control center table.\",
      \"confidence_level\": \"high\",
      \"opinion_about_opponent\": \"Corey is strong but has a weak pronation.\"
    }
  ]
}""" % event_title

    # Prompt for structured JSON response
    system_prompt = f"""
You are an expert assistant in analyzing armwrestling podcasts.

You will receive a transcript and metadata. Your task is to:
1. Identify each speaker using filename and content.
2. Return structured JSON with:
   - A speaker mapping like \"SPEAKER_00\": \"Devon Larratt\"
   - For each speaker who is a known athlete, extract their match predictions about {event_title}
   - Use the list of matches below for valid match-ups
   - For each prediction include:
     * event name (always '{event_title}')
     * participants (exact two names from the match)
     * predicted_winner (exact name from participants)
     * prediction_summary (1-2 sentences max summarizing reasoning)
     * confidence_level (optional, if speaker expresses it clearly)
     * opinion_about_opponent (optional: speaker's brief opinion of opponent)

Return only a JSON object like this:
{example_json}

List of matches:
{match_summaries}

Filename: {filename}
"""

    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": transcript}
        ],
        "temperature": 0.3,
        "max_tokens": 8192
    }

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }

    print(f"📤 Requesting speaker prediction data for: {filename}")
    response = requests.post(API_URL, headers=headers, json=payload)
    response_data = response.json()

    if 'choices' in response_data and response_data['choices']:
        try:
            raw = response_data['choices'][0]['message']['content']
            cleaned = re.sub(r'^```(?:json)?|```$', '', raw.strip(), flags=re.MULTILINE).strip()
            structured_json = json.loads(cleaned)
            with output_json_path.open("w", encoding="utf-8") as f:
                json.dump(structured_json, f, indent=2, ensure_ascii=False)
            print(f"✅ Saved structured predictions to: {output_json_path}")
            return output_json_path
        except Exception as e:
            print("❌ Failed to parse AI response as JSON")
            print(response_data['choices'][0]['message']['content'])
            raise e

    raise Exception("❌ DeepSeek API call failed:\n" + json.dumps(response_data, indent=2))

# Example usage
if __name__ == "__main__":
    try:
        event = "East vs West 17"
        file = "Corey West _amp_ Devon Larratt EvW17 Podcast.txt"
        extract_predictions_as_json(event, file)
    except Exception as e:
        print(f"Error: {str(e)}")
