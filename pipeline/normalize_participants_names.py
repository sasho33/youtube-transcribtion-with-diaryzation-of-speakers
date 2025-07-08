import json
import re
from pathlib import Path
from rapidfuzz import process, fuzz
import sys

# Setup project path and import config
sys.path.append(str(Path(__file__).resolve().parents[1]))
from pipeline.config import EVW_EVENTS_FILE, TRANSCRIPT_DIR

def normalize_string(s):
    return re.sub(r"[^\w\s]", "", s.lower()).strip()

# Load event data
with EVW_EVENTS_FILE.open(encoding="utf-8") as f:
    evw_events = json.load(f)

change_logs = {}

for event in evw_events:
    print(f"\n🔍 Processing event: {event['event_title']}")
    event_title = event["event_title"]
    event_dir = TRANSCRIPT_DIR / event_title

    if not event_dir.exists():
        print(f"⚠️ Skipping: folder {event_dir} not found.")
        continue

    # Collect participant names
    participants = set()
    for match in event.get("matches", []):
        participants.update(match.get("participants", []))
    participant_list = sorted(participants)

    # Build normalization tables
    first_names = {}
    last_names = {}
    full_names = {}

    for full_name in participant_list:
        parts = full_name.strip().split()
        if len(parts) >= 2:
            first = parts[0]
            last = parts[-1]
            norm_first = normalize_string(first)
            norm_last = normalize_string(last)
            norm_full = normalize_string(full_name)
            first_names[norm_first] = first
            last_names[norm_last] = last
            full_names[norm_full] = full_name

    # Output folder
    normalized_dir = event_dir / "normalized"
    normalized_dir.mkdir(parents=True, exist_ok=True)

    event_changes = {}

    for txt_file in event_dir.glob("*.txt"):
        with txt_file.open("r", encoding="utf-8") as f:
            original_text = f.read()

        candidate_words = set(re.findall(r"\b[A-Z][a-z]{2,}\b", original_text))

        replacements = {}

        for word in candidate_words:
            norm_word = normalize_string(word)

            # Match full name
            best_full, score_full, _ = process.extractOne(norm_word, full_names.keys(), scorer=fuzz.ratio)
            if score_full >= 80:
                replacements[word] = full_names[best_full]
                continue

            # Match first name
            best_first, score_first, _ = process.extractOne(norm_word, first_names.keys(), scorer=fuzz.ratio)
            if score_first >= 75:
                replacements[word] = first_names[best_first]
                continue

            # Match last name
            best_last, score_last, _ = process.extractOne(norm_word, last_names.keys(), scorer=fuzz.ratio)
            if score_last >= 75:
                replacements[word] = last_names[best_last]
                continue

        print(f"📄 {txt_file.name}: {len(replacements)} replacements")

        new_text = original_text
        file_changes = {}

        for old, new in replacements.items():
            pattern = rf'\b{re.escape(old)}\b'
            count = len(re.findall(pattern, new_text))
            if count > 0:
                new_text = re.sub(pattern, new, new_text)
                file_changes[old] = {"replacement": new, "count": count}

        # Save cleaned transcript
        normalized_path = normalized_dir / txt_file.name
        with normalized_path.open("w", encoding="utf-8") as f:
            f.write(new_text)

        if file_changes:
            event_changes[txt_file.name] = file_changes

    if event_changes:
        change_logs[event_title] = event_changes

# Save full log
if change_logs:
    log_path = TRANSCRIPT_DIR / "list_of_changes.json"
    with log_path.open("w", encoding="utf-8") as f:
        json.dump(change_logs, f, indent=2, ensure_ascii=False)

print("\n✅ Transcript normalization complete. Changes saved.")
