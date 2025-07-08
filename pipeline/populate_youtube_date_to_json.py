import re
import json
from datetime import datetime
from pathlib import Path
from googleapiclient.discovery import build
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))
from pipeline.config import YOUTUBE_API_KEY, TRANSCRIPT_DIR

channels = [
    {
        "label": "East vs West Main",
        "channel_id": "UC3Dw8OYsWmZqrM1qBBZUMhQ"
    },
    {
        "label": "Engin Terzi Enigma of rage",
        "channel_id": "UCMzpyrvO3yUeGDclgjixSoA"
    },
]

def get_video_publish_date(youtube, video_title):
    for ch in channels:
        request = youtube.search().list(
            part="snippet",
            channelId=ch["channel_id"],
            maxResults=50,
            q=video_title.replace("_amp_", "&"),
            type="video"
        )
        response = request.execute()
        for item in response.get("items", []):
            title = item["snippet"]["title"].lower()
            if all(word in title for word in video_title.replace("_amp_", "&").lower().split()):
                return item["snippet"]["publishedAt"]
    return None

def update_json_with_date(event_name: str, video_title: str):
    youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)

    published_at = get_video_publish_date(youtube, video_title)
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
    # update_json_with_date("East vs West 17", "Artyom Morozov - East vs West Podcast")
    # populate_event("East vs West 17")
    populate_all()
