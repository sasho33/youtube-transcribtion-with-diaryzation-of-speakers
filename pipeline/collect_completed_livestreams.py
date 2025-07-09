import os
import json
from googleapiclient.discovery import build
from pathlib import Path
import sys
# Replace with your own API key or import from .env/config
sys.path.append(str(Path(__file__).resolve().parents[1]))
from pipeline.config import YOUTUBE_API_KEY2

OUTPUT_FILE = Path("youtube_completed_lives.json")

channels = [
    {
        "label": "East vs West Main",
        "channel_id": "UC3Dw8OYsWmZqrM1qBBZUMhQ"
    },
    {
        "label": "Engin Terzi Enigma of rage",
        "channel_id": "UCMzpyrvO3yUeGDclgjixSoA"
    }
]

def get_all_completed_livestreams(youtube, channel_id):
    all_videos = []
    page_token = None

    while True:
        request = youtube.search().list(
            part="snippet",
            channelId=channel_id,
            type="video",
            eventType="completed",
            order="date",
            maxResults=50,
            pageToken=page_token
        )
        response = request.execute()

        for item in response.get("items", []):
            all_videos.append({
                "title": item["snippet"]["title"],
                "videoId": item["id"]["videoId"],
                "publishedAt": item["snippet"]["publishedAt"]
            })

        page_token = response.get("nextPageToken")
        if not page_token:
            break

    return all_videos

def main():
    youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY2)

    results = {}
    for channel in channels:
        label = channel["label"]
        channel_id = channel["channel_id"]
        print(f"📺 Fetching completed livestreams from: {label}")
        try:
            videos = get_all_completed_livestreams(youtube, channel_id)
            results[label] = videos
            print(f"✅ Found {len(videos)} videos.")
        except Exception as e:
            print(f"❌ Error fetching from {label}: {e}")

    with OUTPUT_FILE.open("w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"📁 Saved all results to: {OUTPUT_FILE.resolve()}")

if __name__ == "__main__":
    main()
