import json
from pathlib import Path
from difflib import get_close_matches
import sys

# Setup project path and import config
sys.path.append(str(Path(__file__).resolve().parents[1]))
from pipeline.config import UNIQUE_ATHLETES_FILE, DATA_DIR, ATHLETES_DIR

UNIQUE_ATHLETES_WITH_DATA = DATA_DIR / "unique_athletes_with_data.json"

# === STEP 1: Load Unique Athlete Names ===
with open(UNIQUE_ATHLETES_FILE, "r", encoding="utf-8") as f:
    unique_names = json.load(f)

# === STEP 2: Load all JSON files from ATHLETES_DIR ===
athlete_files = list(ATHLETES_DIR.glob("*.json"))
name_to_file = {f.stem.replace("_", " ").title(): f for f in athlete_files}

# Build reverse index (lowercase names for fuzzy match)
reverse_index = {name.lower(): path for name, path in name_to_file.items()}

# === STEP 3: Match and Load Athlete Data ===
enriched_data = {}

for unique_name in unique_names:
    matched_name = None

    # Try exact lowercase match
    if unique_name.lower() in reverse_index:
        matched_name = unique_name

    # Try fuzzy match
    if not matched_name:
        possible_matches = get_close_matches(unique_name.lower(), reverse_index.keys(), n=3, cutoff=0.7)
        if possible_matches:
            matched_name = possible_matches[0]
        else:
            matched_name = None

    # Load JSON if match found
    if matched_name:
        file_path = reverse_index.get(matched_name.lower())
        if file_path and file_path.exists():
            try:
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read().strip()
                except UnicodeDecodeError:
                    print(f"[⚠️] UTF-8 decode failed for {file_path.name}, trying latin-1")
                    with open(file_path, "r", encoding="latin-1") as f:
                        content = f.read().strip()

                if not content:
                    print(f"[⚠️] File for '{unique_name}' is empty: {file_path.name}")
                    enriched_data[unique_name] = None
                else:
                    enriched_data[unique_name] = json.loads(content)
            except json.JSONDecodeError as e:
                print(f"[🚫] Failed to parse JSON for '{unique_name}' in file: {file_path.name}")
                print(f"     Reason: {e}")
                enriched_data[unique_name] = None

        else:
            print(f"[❗] Match found for '{unique_name}' as '{matched_name}', but file does not exist.")
            enriched_data[unique_name] = None
    else:
        print(f"[❌] No match found for: '{unique_name}'")
        suggestions = get_close_matches(unique_name.lower(), reverse_index.keys(), n=3, cutoff=0.5)
        if suggestions:
            print(f"     🔍 Suggestions: {suggestions}")
        enriched_data[unique_name] = None

# === STEP 4: Save the enriched dataset ===
with open(UNIQUE_ATHLETES_WITH_DATA, "w", encoding="utf-8") as f:
    json.dump(enriched_data, f, indent=2, ensure_ascii=False)

print(f"\n✅ Saved enriched athlete data to: {UNIQUE_ATHLETES_WITH_DATA}")