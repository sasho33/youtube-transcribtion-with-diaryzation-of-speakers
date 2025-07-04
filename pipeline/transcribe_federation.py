import json
import sys
from pathlib import Path

# Dynamically add project root to sys.path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from pipeline.config import EVW_EVENTS_FILE
from pipeline.transcribe_event_video_list import process_single_event

def transcribe_federation(events_file, channels=None):
    """
    Transcribe videos for all events in the given events file
    
    Args:
        events_file (str or Path): Path to the JSON file containing event details
        channels (list, optional): List of channel configurations to search for videos
    """
    # Default channels if not provided
    if channels is None:
        channels = [
            {
                "label": "East vs West Main",
                "channel_url": "https://www.youtube.com/channel/UC3Dw8OYsWmZqrM1qBBZUMhQ",
                "source_type": "live"
            },
        ]
    
    # Read events from file
    try:
        with open(events_file, "r", encoding="utf-8") as f:
            events = json.load(f)
    except FileNotFoundError:
        print(f"❌ Events file not found: {events_file}")
        return
    except json.JSONDecodeError:
        print(f"❌ Invalid JSON in events file: {events_file}")
        return
    
    # Sort events by date (assuming events have 'event_date')
    try:
        events_sorted = sorted(
            events, 
            key=lambda e: parse_date_flexible(e.get("event_date", "9999-12-31")), 
            reverse=True  # Most recent events first
        )
    except Exception as e:
        print(f"❌ Error sorting events: {e}")
        events_sorted = events
    
    # Process events
    print("\n🏆 Starting Federation Video Transcription 🏆")
    print("="*50)
    
    for event in events_sorted:
        event_title = event.get("event_title", "Unknown Event")
        event_date = event.get("event_date", "No Date")
        
        print(f"\n📅 Processing Event: {event_title}")
        print(f"   Date: {event_date}")
        
        try:
            # Call the process_single_event function
            process_single_event(event_title, channels=channels)
        except Exception as e:
            print(f"❌ Error processing {event_title}: {e}")
            continue
    
    print("\n✅ Federation Video Transcription Complete!")

def parse_date_flexible(date_str):
    """
    Flexibly parse dates from different formats
    
    Args:
        date_str (str): Date string to parse
    
    Returns:
        datetime: Parsed date
    """
    from datetime import datetime
    
    date_formats = [
        "%B %d, %Y",  # June 21, 2025
        "%Y-%m-%d",   # 2025-06-21
        "%d %B %Y",   # 21 June 2025
    ]
    
    for fmt in date_formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    
    raise ValueError(f"Unable to parse date: {date_str}")

def main():
    """
    Main entry point for the script
    """
    transcribe_federation(EVW_EVENTS_FILE)

if __name__ == "__main__":
    main()