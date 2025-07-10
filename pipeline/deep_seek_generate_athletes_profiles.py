from concurrent.futures import ThreadPoolExecutor, as_completed

import os
import json
import requests
import re
import difflib
from pathlib import Path
from unidecode import unidecode
import sys
from deep_seek_analizer import DEEPSEEK_API_KEY, API_URL

# Append the project root to path and import config
sys.path.append(str(Path(__file__).resolve().parents[1]))
from pipeline.config import EVW_EVENTS_FILE, KOTT_EVENTS_FILE, UNIQUE_ATHLETES_FILE, ATHLETE_EXAMPLE_FILE, ATHLETES_DIR

MODEL = "deepseek-reasoner"

HEADERS = {
    "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
    "Content-Type": "application/json"
}

# === Helper Functions ===
def normalize_name(name):
    return unidecode(name).lower()

def fuzzy_match(name, candidates, cutoff=0.8):
    matches = difflib.get_close_matches(normalize_name(name), [normalize_name(c) for c in candidates], n=1, cutoff=cutoff)
    if matches:
        idx = [normalize_name(c) for c in candidates].index(matches[0])
        return candidates[idx]
    return None

def extract_matches_for_athlete(name, events):
    matches = {}
    record = {"right": {"wins": 0, "losses": 0}, "left": {"wins": 0, "losses": 0}}
    norm_name = normalize_name(name)

    for event in events:
        for match in event.get("matches", []):
            p1, p2 = match["participants"]
            if norm_name in [normalize_name(p1), normalize_name(p2)]:
                opponent = p2 if normalize_name(p1) == norm_name else p1
                result = "Win" if normalize_name(match["winner"]) == norm_name else "Lost"
                record[match["arm"].lower()]["wins" if result == "Win" else "losses"] += 1

                matches[opponent] = {
                    "arm": match["arm"],
                    "date": event["event_date"],
                    "result": result,
                    "score": match["score"]
                }
    return record, matches

def request_athlete_profile_from_deepseek(name):
    system_prompt = f"""
You are an AI assistant specialized in armwrestling data analysis.

Return detailed structured JSON about the athlete "{name}" including:
- name
- country
- age or date_of_birth
- professional_expirience_years
- height_cm, weight_kg, bicep_cm, forearm_cm, hand_size_cm, wingspan_cm, grip_strength_kg
- dominant_arm
- pulling_style (list of strings)
- titles (list of titles won)
- recent_opponents (last 2-3)
- notable_victories (biggest names beaten)
- injuries (list of objects with `type`, `arm`, `date`, `status`)
- training_location
- coach
- preferred_start_position
- strength_metrics:
  - bench_press_kg
  - curl_kg
  - wrist_curl_kg
  - backpressure_kg
  - sidepressure_kg
- career_highlights (list of strings)
Respond with JSON only.

Only return valid JSON (no text, no markdown).
Use publicly available sources such as:
- https://eastvswestarmwrestling.com/athlete/devon-larratt (name of athlete in the end of URL)
- https://www.goldsarm.com/armwrestlers/
- search for YouTube interviews, Wikipedia pages, or social posts
- historical records from "East vs West" and "King of the Table"

Respond in the following JSON structure. Use null for missing fields.

{{
  "name": "Devon Larratt",
  "country": "Canada",
  "age": 48,
  "date_of_birth": "1975-04-24",
  "professional_expirience_years": 30,
  "height_cm": 196,
  "weight_kg": 124.7,
  "bicep_cm": 48.2,
  "forearm_cm": 40.6,
  "dominant_arm": "Right",
  "pulling_style": ["Toproll", "Kings Move"],
  "matches": {{}},
  "win_loss_record": {{}},
  "titles": ["WAL Heavyweight Champion", "World Armwrestling League Champion"],
  "recent_opponents": ["Genadi Kvikvinia", "Vitalii Laletin"],
  "notable_victories": ["John Brzenk", "Jerry Cadorette"],
  "injuries": [
    {{
      "type": "Elbow Tendonitis",
      "arm": "Right",
      "date": "2023-04-10",
      "status": "Recovered"
    }}
  ],
  "training_location": "Ottawa, Canada",
  "coach": "Self-trained",
  "preferred_start_position": "Strap",
  "strength_metrics": {{
    "bench_press_kg": 160,
    "curl_kg": 70,
    "wrist_curl_kg": 80,
    "backpressure_kg": 72,
    "sidepressure_kg": 130
  }},
  "hand_size_cm": 24.5,
  "wingspan_cm": 210,
  "grip_strength_kg": 75,
  "career_highlights": [
    "Beat John Brzenk 6-0 in 2008",
    "First WAL heavyweight world champion"
  ]
}}
"""

    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": name}
        ],
        "temperature": 0.3,
        "max_tokens": 8192
    }

    print(f"🔍 Querying DeepSeek for: {name}")
    res = requests.post(API_URL, headers=HEADERS, json=payload)
    raw = res.json().get("choices", [{}])[0].get("message", {}).get("content", "")
    if res.status_code != 200:
        raise ValueError(f"DeepSeek API failed ({res.status_code}): {res.text}")
    cleaned = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    if not raw.strip():
        print("⚠️ Empty response from DeepSeek.")
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        print("❌ JSON decoding failed:", e)
        print("Response:", cleaned)
        return {}

def generate_athlete_json(name, evw_data, kott_data):
    safe_filename = re.sub(r'[<>:"/\\|?*\'“”]', '', normalize_name(name).replace(' ', '_'))
    output_path = ATHLETES_DIR / f"{safe_filename}.json"
    if output_path.exists():
        print(f"⏭️ Skipping {name} — already generated.")
        return
    
    try:
        info = request_athlete_profile_from_deepseek(name)
    except Exception as e:
        print(f"❌ DeepSeek failed for {name}: {e}")
        return

    record_evw, matches_evw = extract_matches_for_athlete(name, evw_data)
    record_kott, matches_kott = extract_matches_for_athlete(name, kott_data)

    combined_record = {
        "right": {
            "wins": record_evw["right"]["wins"] + record_kott["right"]["wins"],
            "losses": record_evw["right"]["losses"] + record_kott["right"]["losses"]
        },
        "left": {
            "wins": record_evw["left"]["wins"] + record_kott["left"]["wins"],
            "losses": record_evw["left"]["losses"] + record_kott["left"]["losses"]
        }
    }

    combined_matches = matches_evw.copy()
    combined_matches.update(matches_kott)

    # ✅ Append match info without overwriting
    info["win_loss_record"] = combined_record
    info["matches"] = combined_matches

    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(info, f, indent=2, ensure_ascii=False)
    print(f"✅ Saved profile: {output_path}")

# === Main Runner ===
def main():
    with open(UNIQUE_ATHLETES_FILE, "r", encoding="utf-8") as f:
        athlete_names = json.load(f)
    with open(EVW_EVENTS_FILE, "r", encoding="utf-8") as f:
        evw_data = json.load(f)
    with open(KOTT_EVENTS_FILE, "r", encoding="utf-8") as f:
        kott_data = json.load(f)

    max_threads = 6  # adjust between 4 and 6 based on your connection and API allowance

    def task(name):
        try:
            generate_athlete_json(name, evw_data, kott_data)
        except Exception as e:
            print(f"❌ Error processing {name}: {e}")

    with ThreadPoolExecutor(max_workers=max_threads) as executor:
        futures = [executor.submit(task, name) for name in athlete_names]
        for future in as_completed(futures):
            future.result()  # will raise exception if one occurred

# === Test Function ===
def test_single_athlete():
    test_name = "Artem Taynov"
    with open(EVW_EVENTS_FILE, "r", encoding="utf-8") as f:
        evw_data = json.load(f)
    with open(KOTT_EVENTS_FILE, "r", encoding="utf-8") as f:
        kott_data = json.load(f)

    generate_athlete_json(test_name, evw_data, kott_data)

if __name__ == "__main__":
    # Uncomment to run all
    main()

    # Run single test
    # test_single_athlete()
