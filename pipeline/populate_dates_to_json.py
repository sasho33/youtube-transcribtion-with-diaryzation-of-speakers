import re
import json
from datetime import datetime
from pathlib import Path
import sys

# Set up paths
sys.path.append(str(Path(__file__).resolve().parents[1]))
from pipeline.config import TRANSCRIPT_DIR, YOUTUBE_DATA



# Load local YouTube data
with open(YOUTUBE_DATA, "r", encoding="utf-8") as f:
    youtube_db = json.load(f)

def match_video_date(video_title: str):
    cleaned_title = video_title.replace("_amp_", "&").lower()
    for channel_videos in youtube_db.values():
        for entry in channel_videos:
            yt_title = entry["title"].replace("&amp;", "&").lower()
            if all(word in yt_title for word in cleaned_title.split()):
                return entry["publishedAt"]
    return None

def update_json_with_date(event_name: str, video_title: str):
    published_at = match_video_date(video_title)
    if not published_at:
        print(f"❌ Could not find publish date for video: {video_title}")
        return

    formatted_date = datetime.strptime(published_at, "%Y-%m-%dT%H:%M:%SZ").strftime("%B %d, %Y")

    safe_title = re.sub(r'[\\/:*?"<>|]', '_', video_title).strip()
    json_path = TRANSCRIPT_DIR / event_name / "Identified" / f"{safe_title}.json"
    if not json_path.exists():
        print(f"❌ JSON file not found: {json_path}")
        return

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    data["date"] = formatted_date

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"✅ Updated date in JSON: {json_path}")

def populate_event(event_name: str):
    event_path = TRANSCRIPT_DIR / event_name / "Identified"
    if not event_path.exists():
        print(f"❌ No Identified folder for event: {event_name}")
        return

    for json_file in event_path.glob("*.json"):
        title = json_file.stem
        update_json_with_date(event_name, title)

def populate_all():
    for event_folder in TRANSCRIPT_DIR.iterdir():
        if (event_folder / "Identified").exists():
            print(f"\n📅 Populating dates for event: {event_folder.name}")
            populate_event(event_folder.name)

# Example usage
if __name__ == "__main__":
    # populate_event("East vs West 17")
    populate_all()
    # update_json_with_date("East vs West 17", "Cody Wood _amp_ Joseph Meranto EvW17 Podcast")
