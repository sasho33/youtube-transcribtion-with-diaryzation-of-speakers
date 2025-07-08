import re
import json
from datetime import datetime
from pathlib import Path
from googleapiclient.discovery import build
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))
from pipeline.config import YOUTUBE_API_KEY, TRANSCRIPT_DIR

def get_video_publish_date(youtube, video_title, channel_id):
    request = youtube.search().list(
        part="snippet",
        channelId=channel_id,
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

def update_json_with_date(event_name: str, video_title: str, channel_id: str):
    youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)

    published_at = get_video_publish_date(youtube, video_title, channel_id)
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

# Example usage
if __name__ == "__main__":
    event = "East vs West 17"
    title = "Corey West _amp_ Devon Larratt EvW17 Podcast"
    channel_id = "UC3Dw8OYsWmZqrM1qBBZUMhQ"  # Replace with correct channel if needed
    update_json_with_date(event, title, channel_id)
