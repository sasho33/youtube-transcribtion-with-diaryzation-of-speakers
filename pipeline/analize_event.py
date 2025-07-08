import os
from pathlib import Path
import sys

# Append the project root to path and import config
sys.path.append(str(Path(__file__).resolve().parents[1]))
from pipeline.deep_seek_analizer import extract_predictions_as_json
from pipeline.config import TRANSCRIPT_DIR

def analyze_event(event_title: str):
    """
    Loop through all normalized transcripts in the event folder
    and apply the DeepSeek-based prediction extraction.
    """
    normalized_folder = TRANSCRIPT_DIR / event_title / "normalized"

    if not normalized_folder.exists():
        raise FileNotFoundError(f"No normalized folder found for event: {normalized_folder}")

    files = [f for f in normalized_folder.glob("*.txt") if f.is_file()]

    if not files:
        print(f"⚠️ No .txt files found in: {normalized_folder}")
        return

    for file_path in files:
        try:
            print(f"\n🔄 Processing {file_path.name}...")
            extract_predictions_as_json(event_title, file_path.name)
        except Exception as e:
            print(f"❌ Failed to process {file_path.name}: {e}")

def analyze_all():
    """
    Loop through all event folders in TRANSCRIPT_DIR and call analyze_event on each.
    """
    for event_folder in TRANSCRIPT_DIR.iterdir():
        if event_folder.is_dir() and (event_folder / "normalized").exists():
            event_title = event_folder.name
            print(f"\n📁 Analyzing event: {event_title}")
            try:
                analyze_event(event_title)
            except Exception as e:
                print(f"❌ Failed to analyze event '{event_title}': {e}")

# Example usage:
if __name__ == "__main__":
    analyze_event("East vs West 17")
    # analyze_all()