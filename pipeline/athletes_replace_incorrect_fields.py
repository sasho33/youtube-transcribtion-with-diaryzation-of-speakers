import json
from pathlib import Path
from fuzzywuzzy import fuzz
from tqdm import tqdm
import sys
import re

# Set up paths
sys.path.append(str(Path(__file__).resolve().parents[1]))
from pipeline.config import ATHLETES_DIR, GOLDSARM_DIR

FUZZY_THRESHOLD = 85

# Load Goldsarm data once
goldsarm_data_list = []
for file in GOLDSARM_DIR.glob("*.json"):
    try:
        data = json.loads(file.read_text(encoding="utf-8"))
        name = data.get("name", "")
        goldsarm_data_list.append({
            "file": file.name,
            "name": name,
            "data": data
        })
    except Exception as e:
        print(f"⚠️ Failed to read {file.name}: {e}")


def get_best_goldsarm_match(name: str, threshold: int = 85):
    """Find the best fuzzy match for a name in the Goldsarm dataset."""
    best_score = 0
    best_match = None
    for entry in goldsarm_data_list:
        score = fuzz.token_sort_ratio(name.lower(), entry["name"].lower())
        if score > best_score:
            best_score = score
            best_match = entry
    return best_match if best_score >= threshold else None


def replace_single_athlete_data(filename: str):
    """Replace or fill in fields for one athlete file based on the closest Goldsarm match."""
    athlete_file = ATHLETES_DIR / filename
    if not athlete_file.exists():
        print(f"❌ File not found: {filename}")
        return

    name_from_filename = filename.replace(".json", "").replace("_", " ")
    best_match = get_best_goldsarm_match(name_from_filename)
    if not best_match:
        print(f"❌ No good match found for: {name_from_filename}")
        return

    try:
        athlete_data = json.loads(athlete_file.read_text(encoding="utf-8"))
        goldsarm_data = best_match["data"]

        updated_data = athlete_data.copy()
        for key, value in goldsarm_data.items():
            if key not in updated_data or not updated_data[key]:
                updated_data[key] = value
            elif updated_data[key] != value:
                updated_data[key] = value

        athlete_file.write_text(json.dumps(updated_data, indent=2, ensure_ascii=False))
        print(f"✅ Updated '{filename}' using '{best_match['file']}'")
    except Exception as e:
        print(f"⚠️ Error processing {filename}: {e}")


def replace_all_athletes_data():
    """Process all JSON files in the ATHLETES_DIR and attempt to correct them."""
    files = list(ATHLETES_DIR.glob("*.json"))
    for file in tqdm(files, desc="Replacing athlete data"):
        replace_single_athlete_data(file.name)


# Example usage
if __name__ == "__main__":
    # Run for all files
    replace_all_athletes_data()

    # OR test a single case:
    # replace_single_athlete_data("alex_kurdecha.json")
