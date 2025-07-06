import json
import re
from pathlib import Path
import spacy
from rapidfuzz import process, fuzz
from pipeline.config import EVW_EVENTS_FILE, TRANSCRIPT_DIR

# Load SpaCy model
nlp = spacy.load("en_core_web_sm")

# Load event data
with EVW_EVENTS_FILE.open(encoding="utf-8") as f:
    evw_events = json.load(f)

# Normalize for comparison
def normalize_string(s):
    return re.sub(r"[^\w\s]", "", s).lower().strip()

# Main logging dict
change_logs = {}

for event in evw_events:
    event_title = event["event_title"]
    event_dir = TRANSCRIPT_DIR / event_title

    if not event_dir.exists():
        continue

    # Build participant normalization table
    participants = set()
    for match in event.get("matches", []):
        participants.update(match.get("participants", []))
    participant_list = sorted(participants)

    # Pre-normalize participant names
    norm_participants = {normalize_string(p): p for p in participant_list}

    # Create normalized folder
    normalized_dir = event_dir / "normalized"
    normalized_dir.mkdir(parents=True, exist_ok=True)

    event_changes = {}

    for txt_file in event_dir.glob("*.txt"):
        with txt_file.open(encoding="utf-8") as f:
            original_text = f.read()

        doc = nlp(original_text)
        person_names = set(ent.text.strip() for ent in doc.ents if ent.label_ == "PERSON")

        replacements = {}

        for name in person_names:
            norm_name = normalize_string(name)
            best_match, score, _ = process.extractOne(
                norm_name,
                norm_participants.keys(),
                scorer=fuzz.ratio
            )
            if score >= 80:
                correct_name = norm_participants[best_match]
                if name != correct_name:
                    replacements[name] = correct_name

        # Apply replacements in text
        new_text = original_text
        for old, new in replacements.items():
            new_text = re.sub(rf'\b{re.escape(old)}\b', new, new_text)

        # Save normalized version
        normalized_path = normalized_dir / txt_file.name
        with normalized_path.open("w", encoding="utf-8") as f:
            f.write(new_text)

        if replacements:
            event_changes[txt_file.name] = replacements

    if event_changes:
        change_logs[event_title] = event_changes

# Save all changes to log file
if change_logs:
    log_path = TRANSCRIPT_DIR / "list_of_changes.json"
    with log_path.open("w", encoding="utf-8") as f:
        json.dump(change_logs, f, indent=2, ensure_ascii=False)

print("✅ Transcript normalization complete. Changes saved.")
