# File: pipeline/collect_and_transcribe.py

import sys
from pathlib import Path
from datetime import datetime
import json

sys.path.append(str(Path(__file__).resolve().parents[1]))

from pipeline.config import EVW_EVENTS_FILE, TRANSCRIPT_DIR, AUDIO_DIR
from pipeline.youtube_utils import get_videos_between_dates, get_first_video_date
from pipeline.transcribe import transcribe_with_diarization

import re
import os

def safe_filename(name):
    """Sanitize the filename."""
    return re.sub(r'[^\w\-_\. ]', '_', name)

def load_event_dates(events_path):
    with open(events_path, 'r', encoding='utf-8') as f:
        events = json.load(f)
    return [(e['event_title'], datetime.strptime(e['event_date'], "%B %d, %Y")) for e in events]

def main():
    CHANNEL_ID = "UC3Dw8OYsWmZqrM1qBBZUMhQ"
    LABEL = "East vs West Main"

    first_video_date = get_first_video_date(CHANNEL_ID, title_filter="podcast")
    if not first_video_date:
        print("✗ No matching videos found on the channel.")
        return

    event_dates = load_event_dates(EVW_EVENTS_FILE)
    event_dates.sort(key=lambda x: x[1])

    # Only process events after first video date
    for i in range(1, len(event_dates)):
        prev_event, start_date = event_dates[i - 1]
        curr_event, end_date = event_dates[i]

        if end_date < first_video_date:
            continue  # Skip old events

        print(f"Fetching videos between {start_date.date()} and {end_date.date()} for event: {curr_event}")

        videos = get_videos_between_dates(
            channel_id=CHANNEL_ID,
            start_date=start_date,
            end_date=end_date,
            title_filter="podcast"
        )

        for video in videos:
            video_title = video['title']
            video_url = video['url']
            video_id = video['id']

            event_folder = TRANSCRIPT_DIR / curr_event
            event_folder.mkdir(parents=True, exist_ok=True)

            filename_stem = safe_filename(video_title)
            transcript_path = event_folder / f"{filename_stem}.txt"

            if transcript_path.exists():
                print(f"✓ Skipping already transcribed: {video_title}")
                continue

            print(f"▶ Transcribing: {video_title}")
            try:
                transcribe_with_diarization(
                    video_url=video_url,
                    output_dir=event_folder,
                    audio_dir=AUDIO_DIR,
                    filename_stem=filename_stem
                )
            except Exception as e:
                print(f"✗ Error processing {video_title}: {e}")

if __name__ == "__main__":
    main()
