import json
import re
from pathlib import Path
from unidecode import unidecode
import sys

# Setup project path and import config
sys.path.append(str(Path(__file__).resolve().parents[2]))
from pipeline.config import ATHLETES_DIR, UNIQUE_ATHLETES_FILE, EVW_EVENTS_FILE, KOTT_EVENTS_FILE, TRANSCRIPT_DIR, DATA_DIR

athletes_country_file = DATA_DIR / "athletes_country_map.json"

def convert_to_utf8(file_path: Path):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        source_encoding = "utf-8"
    except UnicodeDecodeError:
        with open(file_path, "r", encoding="latin-1") as f:
            data = json.load(f)
        source_encoding = "latin-1"
    except json.JSONDecodeError as e:
        print(f"[🚫] JSON decode error in {file_path.name}: {e}")
        return

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    try:
        relative_path = file_path.relative_to(Path.cwd())
    except ValueError:
        relative_path = file_path

    print(f"✅ Converted {relative_path} from {source_encoding} to UTF-8")

# === PROCESS EVERYTHING ===
if __name__ == "__main__":
    print("🔁 Converting all relevant JSON files to UTF-8...\n")

    # 1. Convert athlete JSON files
    for file in ATHLETES_DIR.glob("*.json"):
        convert_to_utf8(file)

    # 2. Convert main global files
    for file in [UNIQUE_ATHLETES_FILE, EVW_EVENTS_FILE, KOTT_EVENTS_FILE, athletes_country_file]:
        convert_to_utf8(file)

    # 3. Convert transcript identified JSONs: TRANSCRIPT_DIR/*/identified/*.json
    for subdir in TRANSCRIPT_DIR.glob("*"):
        identified_dir = subdir / "identified"
        if identified_dir.exists() and identified_dir.is_dir():
            for file in identified_dir.glob("*.json"):
                convert_to_utf8(file)
