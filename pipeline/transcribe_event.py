import subprocess
import json
import re
from datetime import datetime, timedelta
import sys
from pathlib import Path
import traceback

sys.path.append(str(Path(__file__).resolve().parents[1]))
from pipeline.config import EVW_EVENTS_FILE, TRANSCRIPT_DIR
from pipeline.transcribe_video import transcribe_youtube_video

def fetch_channel_videos(channel_url, start_date, end_date):
    """
    Fetch videos from a YouTube channel using yt-dlp
    
    Args:
        channel_url (str): YouTube channel URL
        start_date (datetime): Start date for filtering videos
        end_date (datetime): End date for filtering videos
    
    Returns:
        list: List of dictionaries containing video information
    """
    try:
        # Construct yt-dlp command with more flexible filtering
        command = [
            'yt-dlp',
            '--dateafter', (start_date - timedelta(days=60)).strftime('%Y%m%d'),  # Wider date range
            '--datebefore', (end_date + timedelta(days=30)).strftime('%Y%m%d'),   # Extended range
            '--print', 'filename:%(title)s\nurl:%(webpage_url)s\ndate:%(upload_date)s',
            channel_url
        ]

        # Run the command and capture output
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        
        # Parse the output
        videos = []
        lines = result.stdout.strip().split('\n')

        print(f"🔍 Found {len(lines) // 3} videos in channel '{channel_url}' within date range {start_date.date()} to {end_date.date()}")
        
        for i in range(0, len(lines), 3):
            if i + 2 < len(lines):
                title = lines[i].replace('filename:', '').strip()
                url = lines[i+1].replace('url:', '').strip()
                date_str = lines[i+2].replace('date:', '').strip()
                
                try:
                    # Convert date string to datetime
                    video_date = datetime.strptime(date_str, '%Y%m%d')
                    
                    # Additional title and date filtering
                    if (start_date <= video_date <= end_date and 
                        any(keyword in title.lower() for keyword in ['podcast', 'interview'])):
                        videos.append({
                            'title': title,
                            'url': url,
                            'date': video_date
                        })
                
                except ValueError:
                    print(f"Could not parse date for video: {title}")
        
        return videos

    except subprocess.CalledProcessError as e:
        print(f"Error fetching channel videos: {e}")
        print(f"Command output: {e.stdout}")
        print(f"Command error: {e.stderr}")
        return []
    except Exception as e:
        print(f"Unexpected error fetching channel videos: {e}")
        return []


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

    # List to store videos to be processed
    videos_to_process = []

    for ch_cfg in channels:
        label = ch_cfg["label"]
        source_type = ch_cfg["source_type"]
        print(f"\n🔍 Scanning source: {label} ({source_type})")

        try:
            # Fetch videos using yt-dlp
            videos = fetch_channel_videos(
                ch_cfg["channel_url"], 
                start_date, 
                end_date
            )

            # Filter videos with podcast or interview in title
            filtered_videos = []
            for video in videos:
                print(f"✅ Found video: {video['title']} ({video['date']}) - {video['url']}")
                filtered_videos.append({
                    'title': video['title'],
                    'url': video['url'],
                    'date': video['date'],
                    'channel': label
                })

            videos_to_process.extend(filtered_videos)

        except Exception as e:
            print(f"❌ Error processing {label}: {e}")
            traceback.print_exc()

    # Preview videos to be processed
    print("\n📋 Videos to be Processed:")
    if not videos_to_process:
        print("   No videos found matching the criteria.")
        return

    for i, video in enumerate(videos_to_process, 1):
        print(f"{i}. {video['title']}")
        print(f"   Channel: {video['channel']}")
        print(f"   Date: {video['date']}")
        print(f"   URL: {video['url']}\n")

    # Process videos
    for video in videos_to_process:
        try:
            title = video['title']
            url = video['url']
            
            # Optional: Modify title based on specific conditions
            if video['channel'] == "East vs West Main":
                title = f'{title} with Engin Terzi (interviewer)'

            print(f"\nProcessing video: {title}, date: {video['date']}")
            if transcribe_youtube_video(url, title, target_title) is None:
                continue

        except Exception as video_error:
            print(f"❌ Error processing individual video: {video_error}")
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