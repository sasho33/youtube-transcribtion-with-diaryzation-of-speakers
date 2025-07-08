import os
import json
import requests
import re
from pathlib import Path
import sys

# Append the project root to path and import config
sys.path.append(str(Path(__file__).resolve().parents[1]))
from pipeline.config import TRANSCRIPT_DIR

# Configuration


def replace_speakers_with_names(event_title: str):
    normalized_dir = TRANSCRIPT_DIR / event_title / "normalized"
    identified_dir = TRANSCRIPT_DIR / event_title / "Identified"
    diarized_dir = TRANSCRIPT_DIR / event_title / "diarized"
    diarized_dir.mkdir(parents=True, exist_ok=True)

    for transcript_file in normalized_dir.glob("*.txt"):
        identified_file = identified_dir / transcript_file.name.replace(".txt", ".json")
        if not identified_file.exists():
            print(f"❌ Skipping {transcript_file.name}: no identified JSON found.")
            continue

        with open(transcript_file, "r", encoding="utf-8") as tf:
            transcript = tf.read()

        with open(identified_file, "r", encoding="utf-8") as jf:
            try:
                data = json.load(jf)
                speaker_mapping = data.get("speaker_mapping", {})
            except Exception as e:
                print(f"❌ Error reading JSON {identified_file.name}: {e}")
                continue

        # Replace speaker tags in transcript
        for speaker_tag, real_name in speaker_mapping.items():
            pattern = rf"^{speaker_tag}:"
            replacement = f"{real_name}:"
            transcript = re.sub(pattern, replacement, transcript, flags=re.MULTILINE)

        diarized_path = diarized_dir / transcript_file.name
        with open(diarized_path, "w", encoding="utf-8") as df:
            df.write(transcript)

        print(f"✅ Diarized transcript saved: {diarized_path}")

def rename_all_speakers():
    for event_folder in TRANSCRIPT_DIR.iterdir():
        if (event_folder / "normalized").exists() and (event_folder / "Identified").exists():
            print(f"\n🔄 Renaming speakers for event: {event_folder.name}")
            replace_speakers_with_names(event_folder.name)

# Example usage
if __name__ == "__main__":
    # replace_speakers_with_names("East vs West 5")
    rename_all_speakers()