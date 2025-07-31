import json
from datetime import datetime
from pathlib import Path
import sys

import matplotlib.pyplot as plt

sys.path.append(str(Path(__file__).resolve().parents[2]))
from pipeline.config import EVW_EVENTS_FILE, KOTT_EVENTS_FILE

def normalize_key(arm, weight_category):
    """Normalize the title key to ensure consistency (case and whitespace)."""
    return (str(arm).strip().lower(), str(weight_category).strip().lower())

def parse_event_date(date_str):
    # Try multiple date formats if needed
    for fmt in ("%B %d, %Y", "%b %d, %Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    raise ValueError(f"Unrecognized date format: {date_str}")

def is_current_title_holder(event_title, athlete_name,
                            evw_file=EVW_EVENTS_FILE,
                            kott_file=KOTT_EVENTS_FILE):
    # Load events
    with open(evw_file, 'r') as f:
        evw_events = json.load(f)
    with open(kott_file, 'r') as f:
        kott_events = json.load(f)
    all_events = []
    for event in evw_events + kott_events:
        try:
            event_date = parse_event_date(event['event_date'])
        except Exception as e:
            print(f"Error parsing date for event {event['event_title']}: {e}")
            continue
        all_events.append({
            'event_title': event['event_title'],
            'event_date': event_date,
            'matches': event['matches']
        })
    # Sort all events by date ascending
    all_events.sort(key=lambda x: x['event_date'])

    # Find the event and date for this query
    target_event = next((e for e in all_events if e['event_title'].lower() == event_title.lower()), None)
    if not target_event:
        raise ValueError("Event title not found.")
    target_date = target_event['event_date']

    # Prepare a map: key = (arm, weight), value = current champion as of each match
    title_holder = {}

    # Step 1: Build champion history up to (but not including) the target event
    for event in all_events:
        if event['event_date'] >= target_date:
            break
        for match in event['matches']:
            if match.get('is_title', False):
                key = normalize_key(match.get('arm', ''), match.get('weight_category', ''))
                winner = match['winner'].strip()
                title_holder[key] = winner

    # Step 2: In the target event, check for title matches where this athlete could be the champion
    is_holder = False
    for match in target_event['matches']:
        if match.get('is_title', False):
            key = normalize_key(match.get('arm', ''), match.get('weight_category', ''))
            # Check if the athlete is the current champ for this match's title
            if title_holder.get(key, None) and title_holder[key].strip().lower() == athlete_name.strip().lower():
                is_holder = True
    return is_holder

# Example usage:
# result = is_current_title_holder("East vs West 18", "Levan Saginashvili")
# print("Is current title holder:", result)


def count_title_defenses(evw_file=EVW_EVENTS_FILE, kott_file=KOTT_EVENTS_FILE):
    # Load and combine events as before
    with open(evw_file, 'r') as f:
        evw_events = json.load(f)
    with open(kott_file, 'r') as f:
        kott_events = json.load(f)
    all_events = []
    for event in evw_events + kott_events:
        try:
            event_date = parse_event_date(event['event_date'])
        except Exception as e:
            print(f"Error parsing date for event {event['event_title']}: {e}")
            continue
        all_events.append({
            'event_title': event['event_title'],
            'event_date': event_date,
            'matches': event['matches']
        })
    # Sort all events by date ascending
    all_events.sort(key=lambda x: x['event_date'])

    title_holder = {}  # {normalized_key: champion}
    defended = 0
    lost = 0
    title_matches = 0
    match_list = []

    for event in all_events:
        for match in event['matches']:
            if match.get('is_title', False):
                key = normalize_key(match.get('arm', ''), match.get('weight_category', ''))
                prev_holder = title_holder.get(key)
                participants = [p.strip() for p in match.get('participants', [])]
                winner = match['winner'].strip()
                loser = match['loser'].strip()
                # Only count if the prev_holder is among the participants
                if prev_holder and prev_holder.strip() in participants:
                    match_info = {
                        "event_title": event['event_title'],
                        "event_date": event['event_date'].strftime('%Y-%m-%d'),
                        "arm": match.get('arm', ''),
                        "weight_category": match.get('weight_category', ''),
                        "previous_champion": prev_holder,
                        "winner": winner,
                        "loser": loser,
                        "result": ""
                    }
                    if winner == prev_holder.strip():
                        defended += 1
                        match_info["result"] = "Defense"
                    else:
                        lost += 1
                        match_info["result"] = "Title Change"
                    title_matches += 1
                    match_list.append(match_info)
                # Always update the title holder (even for skipped matches)
                title_holder[key] = winner

    print(f"Defended: {defended}  |  Lost: {lost}  |  Total matches with champion present: {title_matches}")
    print("\nList of title matches (with champion present):")
    for match in match_list:
        print(
            f"{match['event_date']} | {match['event_title']} | {match['arm']} | {match['weight_category']} | "
            f"Champion: {match['previous_champion']} | Winner: {match['winner']} | Loser: {match['loser']} | {match['result']}"
        )

    # Pie chart
    labels = ['Title Defense (Champion Won)', 'Title Change (Champion Lost)']
    sizes = [defended, lost]
    plt.figure(figsize=(6, 6))
    plt.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=140)
    plt.title("Title Matches: Defense vs Change (Champion Present)")
    plt.axis('equal')
    plt.show()

    return match_list

if __name__ == "__main__":
    # Example usage:
    result = is_current_title_holder("East vs West 18", "Ermes Gasparini")
    print("Is current title holder:", result)
    
    # Count title defenses
    count_title_defenses()