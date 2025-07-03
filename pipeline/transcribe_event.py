from pytubefix import Channel, Playlist
from datetime import datetime, timedelta
import json
import sys
from pathlib import Path
import traceback

sys.path.append(str(Path(__file__).resolve().parents[1]))
from pipeline.config import EVW_EVENTS_FILE, TRANSCRIPT_DIR
from pipeline.transcribe_video import transcribe_youtube_video

def parse_date_flexible(date_str):
    for fmt in ("%Y-%m-%d", "%B %d, %Y"):
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    raise ValueError(f"Unsupported date format: {date_str}")

def process_single_event(target_title, channels=None):
    # Use EVW_EVENTS_FILE instead of EVENTS_FILE
    with open(EVW_EVENTS_FILE, "r", encoding="utf-8") as f:
        events = json.load(f)

    events_sorted = sorted(events, key=lambda e: parse_date_flexible(e["event_date"] or "9999-12-31"))

    target_index = next((i for i, e in enumerate(events_sorted) if e["event_title"].lower() == target_title.lower()), None)
    if target_index is None:
        print(f"❌ Event '{target_title}' not found.")
        return

    event = events_sorted[target_index]
    event_title = event["event_title"]
    event_date = parse_date_flexible(event["event_date"])

    if target_index > 0:
        prev_event_date = parse_date_flexible(events_sorted[target_index - 1]["event_date"])
        start_date = prev_event_date + timedelta(days=7)
    else:
        start_date = event_date - timedelta(days=30)

    end_date = event_date

    print(f"\n📦 Processing event: {event_title}")
    print(f"   🔍 Date range: {start_date.date()} to {end_date.date()}")

    for ch_cfg in channels:
        label = ch_cfg["label"]
        source_type = ch_cfg["source_type"]
        print(f"\n🔍 Scanning source: {label} ({source_type})")

        try:
            if source_type == "live":
                ch = Channel(ch_cfg["channel_url"])
                # Add error checking for videos
                try:
                    videos = list(ch.live)  # Convert to list to check length
                except Exception as e:
                    print(f"❌ Error fetching live videos: {e}")
                    videos = []

            elif source_type == "videos":
                ch = Channel(ch_cfg["channel_url"])
                try:
                    videos = list(ch.videos)  # Convert to list to check length
                except Exception as e:
                    print(f"❌ Error fetching channel videos: {e}")
                    videos = []

            elif source_type == "playlist":
                pl = Playlist(ch_cfg["playlist_url"])
                try:
                    videos = list(pl.videos)  # Convert to list to check length
                except Exception as e:
                    print(f"❌ Error fetching playlist videos: {e}")
                    videos = []

            else:
                print(f"⚠️  Unsupported source_type: {source_type}")
                continue

            # Debugging: Print total number of videos
            print(f"Total videos found: {len(videos)}")

            count = 0
            for video in videos:
                try:
                    if not video.publish_date:
                        continue

                    naive_date = video.publish_date.replace(tzinfo=None)
                    if not (start_date <= naive_date <= end_date):
                        continue

                    # Additional filtering
                    if ch_cfg["label"] == "East vs West Main" and "podcast" not in video.title.lower():
                        continue

                    count += 1
                    print(f"\n🎞️  [{count}] {video.title}")
                    print(f"    🗓 Published: {naive_date}")
                    print(f"    🔗 {video.watch_url}")

                    url = video.watch_url
                    title = video.title
                    
                    # Optional: Modify title based on specific conditions
                    if ch_cfg.get("label") == "East vs West Main":
                        title = f'{video.title} with Engin Terzi (interviewer)'
                        print("Terzi detected")

                    print(f"Processing video: {title}, date: {naive_date}")
                    # transcribe_youtube_video(url, title, target_title)
                    if transcribe_youtube_video(url, title, target_title) is None:
                        continue

                except Exception as video_error:
                    print(f"❌ Error processing individual video: {video_error}")
                    traceback.print_exc()

        except Exception as e:
            print(f"❌ Error processing {label}: {e}")
            traceback.print_exc()

    print(f"\n📁 Saved all transcripts for '{event_title}' to {TRANSCRIPT_DIR}")

# --- RUN ---
if __name__ == "__main__":
    channels = [
        {
            "label": "East vs West Main",
            "channel_url": "https://www.youtube.com/channel/UC3Dw8OYsWmZqrM1qBBZUMhQ",
            "source_type": "live"
        },
    ]
    process_single_event("East vs West 17", channels=channels)