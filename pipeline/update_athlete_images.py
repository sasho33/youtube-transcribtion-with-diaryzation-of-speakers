import json
import sys
from pathlib import Path
from rapidfuzz import process, fuzz

# Import config using sys.path trick
sys.path.append(str(Path(__file__).resolve().parents[1]))
from pipeline.config import UNIQUE_ATHLETES_WITH_DATA_FILE, GOLDSARM_DIR

def load_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading JSON file '{path}': {e}")
        sys.exit(1)

def save_json(data, path):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error saving JSON file '{path}': {e}")
        sys.exit(1)

def normalize(s):
    return s.lower().replace('-', ' ').replace('_', ' ').replace('.', ' ').strip()

def main():
    # Check athlete data file exists
    if not Path(UNIQUE_ATHLETES_WITH_DATA_FILE).exists():
        print(f"File not found: {UNIQUE_ATHLETES_WITH_DATA_FILE}")
        sys.exit(1)
    # Check photos directory exists
    if not Path(GOLDSARM_DIR).exists():
        print(f"Directory not found: {GOLDSARM_DIR}")
        sys.exit(1)

    athletes = load_json(UNIQUE_ATHLETES_WITH_DATA_FILE)
    athlete_names = list(athletes.keys())
    norm_names = [normalize(name) for name in athlete_names]

    # List all .jpg/.png files in GOLDSARM_DIR
    photo_files = []
    for ext in ('*.jpg', '*.png'):
        photo_files.extend(Path(GOLDSARM_DIR).glob(ext))
    if not photo_files:
        print(f"No image files found in directory: {GOLDSARM_DIR}")
    photo_names = [f.stem for f in photo_files]
    norm_photos = [normalize(stem) for stem in photo_names]

    # Fuzzy match athlete name to image file
    for idx, (athlete, athlete_data) in enumerate(athletes.items()):
        try:
            match, score, file_idx = process.extractOne(
                normalize(athlete),
                norm_photos,
                scorer=fuzz.token_sort_ratio
            )
            if score >= 85 and file_idx is not None:
                img_file = photo_files[file_idx]
                rel_path = f"goldsarm/{img_file.name}"
                athlete_data["img"] = rel_path
            else:
                athlete_data["img"] = None
                print(f"No image found for athlete: {athlete}")
        except Exception as e:
            print(f"Error processing athlete '{athlete}': {e}")
            athlete_data["img"] = None
            print(f"No image found for athlete: {athlete}")

    save_json(athletes, UNIQUE_ATHLETES_WITH_DATA_FILE)
    print("Updated athlete images with fuzzy matching.")

if __name__ == "__main__":
    main()