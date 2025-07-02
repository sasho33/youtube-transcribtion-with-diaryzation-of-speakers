# File: pipeline/parse_kott_events.py
import sys
from pathlib import Path
import json
import re
import requests
from bs4 import BeautifulSoup

# Dynamically add project root to sys.path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from pipeline.config import KOTT_EVENTS_FILE

def parse_match_line(line):
    """Parse a match line to extract match details with arm and other info."""
    pattern = r'^(.+?)\s+(\d+-\d+)\s+over\s+(.+?)(?:\s+\(([^)]+)\))?.*$'
    match = re.search(pattern, line)
    if not match:
        return None

    winner = match.group(1).strip()
    score = match.group(2)
    loser = match.group(3).strip()
    arm_info = match.group(4) if match.group(4) else "Right"

    arm = "Right"
    if arm_info and "left" in arm_info.lower():
        arm = "Left"

    return {
        'winner': winner,
        'loser': loser,
        'score': score,
        'participants': [winner, loser],
        'arm': arm,
        'weight_category': "Supermatch",
        'is_title': False
    }

def scrape_and_parse_king_of_the_table():
    url = "https://www.thearmwrestlingarchives.com/king-of-the-table-results-2021-present.html"
    headers = {'User-Agent': 'Mozilla/5.0'}

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        print(f"✓ Successfully fetched King of the Table page (status: {response.status_code})")
    except Exception as e:
        print(f"✗ Error fetching King of the Table page: {e}")
        return None

    soup = BeautifulSoup(response.content, 'html.parser')
    content_div = soup.find('div', class_='paragraph')
    if not content_div:
        print(f"✗ Could not find div with class 'paragraph'")
        return None

    content = content_div.get_text()
    event_pattern = r'(King of the Table\s*\d*)'
    event_matches = list(re.finditer(event_pattern, content, re.IGNORECASE))
    events = []

    for i, event_match in enumerate(event_matches):
        event_title = event_match.group().strip()
        start_pos = event_match.end()
        end_pos = event_matches[i + 1].start() if i + 1 < len(event_matches) else len(content)
        event_content = content[start_pos:end_pos].strip()

        event_date = "Unknown"
        event_location = "Unknown"
        matches = []

        date_match = re.search(r'([A-Za-z]+ \d+, \d+)\s*[–—-]\s*([^S]+?)(?=SUPERMATCHES|$)', event_content)
        if date_match:
            event_date = date_match.group(1).strip()
            event_location = date_match.group(2).strip()

        clean_content = event_content
        if date_match:
            supermatches_pos = clean_content.find('SUPERMATCHES')
            if supermatches_pos != -1:
                clean_content = clean_content[supermatches_pos + len('SUPERMATCHES'):].strip()

        match_pattern = r'([A-Za-z][^0-9]*?)\s+(\d+-\d+)\s+over\s+([^(]+?)\s*\(([^)]+)\)'
        match_results = re.findall(match_pattern, clean_content)

        for match_result in match_results:
            winner = re.sub(r'^.*(SUPERMATCHES|UAE|Dubai|Turkey|USA|America)', '', match_result[0], flags=re.IGNORECASE).strip()
            winner = re.sub(r'^\W+', '', winner).strip()
            winner = re.sub(r'(.*?)(\s+\([^)]*\).*|wins.*|did not.*|Last.*)', r'\1', winner, flags=re.IGNORECASE).strip()

            loser = re.sub(r'(.*?)(\s+\([^)]*\).*|Last.*|did not.*)', r'\1', match_result[2], flags=re.IGNORECASE).strip()

            if not winner or len(winner) < 2:
                continue

            arm = "Left" if "left" in match_result[3].lower() else "Right"

            scores = match_result[1].split('-')
            max_score = max(int(scores[0]), int(scores[1]))
            is_title = max_score >= 4

            match_data = {
                'winner': winner,
                'loser': loser,
                'score': match_result[1],
                'participants': [winner, loser],
                'arm': arm,
                'weight_category': "Unknown",
                'is_title': is_title
            }
            matches.append(match_data)

        if matches:
            event = {
                'event_title': event_title,
                'event_date': event_date,
                'event_location': event_location,
                'matches': matches
            }
            events.append(event)
            print(f"✓ Parsed event: {event_title} with {len(matches)} matches")

    return events

def save_results_to_file(events, filename=KOTT_EVENTS_FILE):
    try:
        filename.parent.mkdir(parents=True, exist_ok=True)
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(events, f, indent=2, ensure_ascii=False)
        print(f"Results saved to {filename}")
        return True
    except Exception as e:
        print(f"Error saving file: {e}")
        return False

def display_sample_results(events, max_events=3, max_matches_per_event=5):
    print("Sample of King of the Table results:")
    print("=" * 60)
    for event in events[:max_events]:
        print(f"\nEvent: {event['event_title']}")
        print(f"Date: {event['event_date']}")
        print(f"Location: {event['event_location']}")
        print(f"Matches: {len(event['matches'])}")
        print("-" * 40)
        for i, match in enumerate(event['matches'][:max_matches_per_event]):
            print(f"{i+1}. {match['winner']} def. {match['loser']} ({match['score']}) - {match['arm']} Arm")
        if len(event['matches']) > max_matches_per_event:
            print(f"   ... and {len(event['matches']) - max_matches_per_event} more matches")

if __name__ == "__main__":
    print("Scraping King of the Table results from archive website...")
    print("=" * 70)
    events = scrape_and_parse_king_of_the_table()
    if events:
        display_sample_results(events)
        save_results_to_file(events)
        print(f"\n✓ Total King of the Table events parsed: {len(events)}")
        print(f"✓ Total matches parsed: {sum(len(e['matches']) for e in events)}")
    else:
        print("✗ Failed to parse King of the Table results.")
