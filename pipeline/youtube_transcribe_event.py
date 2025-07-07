


from googleapiclient.discovery import build
from datetime import datetime, timedelta
import json
import sys
from pathlib import Path
import traceback

sys.path.append(str(Path(__file__).resolve().parents[1]))
from pipeline.config import EVW_EVENTS_FILE, TRANSCRIPT_DIR, YOUTUBE_API_KEY
from pipeline.transcribe_video_clean import transcribe_youtube_video

# Replace with your actual API key


def parse_date_flexible(date_str):
    for fmt in ("%Y-%m-%d", "%B %d, %Y"):
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    raise ValueError(f"Unsupported date format: {date_str}")

def fetch_channel_videos(youtube, channel_id, start_date, end_date):
    """
    Fetch live videos from a YouTube channel using YouTube Data API
    
    Args:
        youtube (Resource): YouTube API resource
        channel_id (str): YouTube channel ID
        start_date (datetime): Start date for filtering videos
        end_date (datetime): End date for filtering videos
    
    Returns:
        list: List of dictionaries containing video information
    """
    videos = []
    
    # Convert dates to RFC 3339 format
    start_date_str = start_date.isoformat() + 'Z'
    end_date_str = end_date.isoformat() + 'Z'
    
    # Expanded podcast and interview keywords
    podcast_keywords = [
        'podcast', 
        'interview', 
        'evw podcast', 
        'east vs west podcast',
        'Morozov',
        'Nisa Camadan',
        'Ermes',
        'Mindaugas',
        'Ivan',
        'Alex',
        'Chance',
        'John',
        'Ron',
        'Cobra',
        'School',
        'Arsen',
        'Sarah','Reisek', 'Zoloev', 'Todd', 'Mask', 'Davit', 'Zurab', 'Revaz'
        
        
        
    ]
    
    try:
        # Request live videos
        request = youtube.search().list(
            part="snippet",
            channelId=channel_id,
            type="video",
            eventType="completed",  # Completed live streams
            order="date",
            maxResults=250,  # Increased to capture more videos
            publishedAfter=start_date_str,
            publishedBefore=end_date_str
        )
        response = request.execute()
        
        print(f"Total live video results: {len(response.get('items', []))}")
        
        # Filter and process videos
        for item in response.get('items', []):
            title = item['snippet']['title']
            video_id = item['id']['videoId']
            published_at = datetime.strptime(
                item['snippet']['publishedAt'], 
                "%Y-%m-%dT%H:%M:%SZ"
            )
            
            # Detailed logging for each video
            print(f"Checking live video: {title}")
            print(f"Published at: {published_at}")
            
            # More flexible keyword matching
            is_podcast = any(
                keyword.lower() in title.lower() 
                for keyword in podcast_keywords
            )
            
            if is_podcast:
                print(f"✅ Matched Live Podcast/Interview: {title}")
                videos.append({
                    'title': title,
                    'url': f"https://www.youtube.com/watch?v={video_id}",
                    'date': published_at
                })
            else:
                print(f"❌ Skipped live video: {title}")
        
        print(f"Filtered live podcast/interview videos: {len(videos)}")
        return videos
    
    except Exception as e:
        print(f"❌ Error fetching live videos: {e}")
        traceback.print_exc()
        return []

# The rest of the script remains the same as in the previous implementation
def process_single_event(target_title, channels=None, api_key=YOUTUBE_API_KEY):
    # Create YouTube API client
    youtube = build('youtube', 'v3', developerKey=api_key)
    
    # Use EVW_EVENTS_FILE
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
        channel_url = ch_cfg["channel_url"]
        
        # Extract channel ID from URL
        channel_id = channel_url.split("/")[-1]
        
        print(f"\n🔍 Scanning source: {label}")

        try:
            # Fetch videos for this channel
            channel_videos = fetch_channel_videos(
                youtube, 
                channel_id, 
                start_date, 
                end_date
            )

            # Extend videos to process
            videos_to_process.extend(channel_videos)

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
        print(f"   Channel: {label}")
        print(f"   Date: {video['date']}")
        print(f"   URL: {video['url']}\n")

    # Process videos
    for video in videos_to_process:
        try:
            title = video['title']
            url = video['url']
            
            # Optional: Modify title based on specific conditions
            if label == "East vs West Main":
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
        },
         {
            "label": "Engin Terzi Enigma of rage",
            "channel_url": "https://www.youtube.com/channel/UCMzpyrvO3yUeGDclgjixSoA",
        },
    ]
    process_single_event("East vs West 17", channels=channels)