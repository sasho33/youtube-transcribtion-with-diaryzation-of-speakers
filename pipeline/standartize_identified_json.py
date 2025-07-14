import os
import json
import requests
import re
from pathlib import Path
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.append(str(Path(__file__).resolve().parents[1]))
from pipeline.config import SHALLOWSEEK_APIK, TRANSCRIPT_DIR

API_URL = "https://api.deepseek.com/v1/chat/completions"
MODEL = "deepseek-chat"
DEEPSEEK_API_KEY = SHALLOWSEEK_APIK
MAX_WORKERS = 6  # Adjust based on your rate limits & connection capacity

def call_deepseek_standardizer(content: str, filename: str):
    system_prompt = f"""
You are a JSON formatting expert. Your job is to convert armwrestling podcast prediction data into a **unified structure**.

Instructions:
- Clean any invalid or partial JSON.
- Output should contain:
  - "speaker_mapping": dict of e.g., "SPEAKER_00": "Devon Larratt"
  - "date": null or actual date string
  - "predictions": dict keyed by speaker name, each with:
    - "self_predictions": list
    - "third_party_predictions": list
- All predictions must use:
  - match: [name1, name2]
  - arm, event, predicted_winner, predicted_score, prediction_summary, predicted_duration, style_conflict
  - opinion_about_athletes: dict per athlete with keys "strength", "health", "previous_match_summary"

Filename: {filename}
Return only JSON.
"""

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": content}
        ],
        "temperature": 0,
        "max_tokens": 8192
    }

    response = requests.post(API_URL, headers=headers, json=payload)
    response_data = response.json()

    if "choices" in response_data and response_data["choices"]:
        raw = response_data["choices"][0]["message"]["content"]
        cleaned = re.sub(r'^```(?:json)?|```$', '', raw.strip(), flags=re.MULTILINE).strip()
        cleaned = re.sub(r',\s*}', '}', cleaned)
        cleaned = re.sub(r',\s*]', ']', cleaned)
        return json.loads(cleaned)

    raise Exception("❌ DeepSeek failed:\n" + json.dumps(response_data, indent=2))


def process_file(event_dir: Path, json_file: Path, output_file: Path):
    try:
        with open(json_file, "r", encoding="utf-8") as f:
            content = f.read()

        print(f"📤 Sending {json_file.name} to DeepSeek...")
        result = call_deepseek_standardizer(content, json_file.name)

        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"✅ Saved: {output_file}")
        return json_file.name

    except Exception as e:
        print(f"❌ Error with {json_file.name}: {e}")
        return None


def standardize_event_with_deepseek(event_title: str):
    event_dir = TRANSCRIPT_DIR / event_title
    identified_dir = event_dir / "Identified"
    output_dir = event_dir / "Identified2"
    output_dir.mkdir(parents=True, exist_ok=True)

    jobs = []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        for json_file in identified_dir.glob("*.json"):
            output_file = output_dir / json_file.name

            # ✅ Skip if already exists
            if output_file.exists() and output_file.stat().st_size > 0:
                print(f"⏭️ Skipping {json_file.name} — already standardized.")
                continue

            jobs.append(executor.submit(process_file, event_dir, json_file, output_file))

        completed = 0
        for future in as_completed(jobs):
            result = future.result()
            if result:
                completed += 1

    print(f"🎯 Event '{event_title}': {completed} files processed.")


def standardize_all_with_deepseek():
    for event_dir in TRANSCRIPT_DIR.iterdir():
        if event_dir.is_dir():
            standardize_event_with_deepseek(event_dir.name)


if __name__ == "__main__":
    # Option A: Single event (edit name)
    # standardize_event_with_deepseek("East vs West 13")

    # Option B: All events
    standardize_all_with_deepseek()
