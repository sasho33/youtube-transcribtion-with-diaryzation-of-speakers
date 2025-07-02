# File: pipeline/parse_events.py
import sys
from pathlib import Path
import json
import re
import requests
from bs4 import BeautifulSoup

# Dynamically add project root to sys.path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from pipeline.config import EVW_EVENTS_FILE


def parse_match_line(line):
    line = line.replace('&nbsp;', ' ').strip()
    score_pattern = r'\s+(\d+-\d+)\s+'
    match = re.search(score_pattern, line)
    if not match:
        return None
    score = match.group(1)
    parts = re.split(score_pattern, line)
    if len(parts) < 3:
        return None
    winner = parts[0].strip()
    loser = parts[2].strip()
    return {
        'winner': winner,
        'loser': loser,
        'score': score,
        'participants': [winner, loser]
    }

def parse_category_line(line):
    line = line.strip().lower()
    arm = "Right"
    if "left arm" in line:
        arm = "Left"
    elif "right arm" in line or "righ arm" in line:
        arm = "Right"
    weight_category = "Unknown"
    categories = [
        ("light heavyweight", "Light Heavyweight"),
        ("super heavyweight", "Super Heavyweight"),
        ("featherweight", "Featherweight"),
        ("lightweight", "Lightweight"),
        ("welterweight", "Welterweight"),
        ("middleweight", "Middleweight"),
        ("heavyweight", "Heavyweight"),
        ("openweight", "Openweight")
    ]
    for search_term, display_name in categories:
        if search_term in line:
            weight_category = display_name
            break
    is_title = "world title" in line
    return {
        'arm': arm,
        'weight_category': weight_category,
        'is_title': is_title
    }

def parse_event_header(header_element):
    if not header_element:
        return None
    title_elem = header_element.find('h3')
    event_title = title_elem.get_text().strip() if title_elem else "Unknown Event"
    subheading = header_element.find('div', class_='av-subheading')
    event_date = event_location = "Unknown"
    if subheading:
        match = re.search(r'([A-Za-z]+ \d+, \d+)\s*[–—-]\s*(.+)', subheading.get_text().strip())
        if match:
            event_date = match.group(1).strip()
            event_location = match.group(2).strip()
    return {'title': event_title, 'date': event_date, 'location': event_location}

def scrape_and_parse_east_vs_west():
    url = "https://eastvswestarmwrestling.com/results/"
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        page = requests.get(url, headers=headers)
        page.raise_for_status()
        print(f"✓ Successfully fetched East vs West page (status: {page.status_code})")
    except requests.RequestException as e:
        print(f"✗ Error fetching the page: {e}")
        return None
    soup = BeautifulSoup(page.content, "html.parser")
    armsections = soup.find_all("section", class_="av_textblock_section")
    print(f"✓ Found {len(armsections)} result sections")
    events = []
    for section in armsections:
        matches = []
        header_element = None
        current = section.find_previous_sibling()
        while current:
            if current.name == 'div' and 'av-special-heading' in current.get('class', []):
                header_element = current
                break
            current = current.find_previous_sibling()
        if not header_element:
            parent = section.parent
            if parent:
                current = parent.find_previous_sibling()
                while current:
                    header_div = current.find('div', class_=lambda x: x and 'av-special-heading' in x)
                    if header_div:
                        header_element = header_div
                        break
                    current = current.find_previous_sibling()
        event_info = parse_event_header(header_element) or {
            'title': "East vs West Event",
            'date': "Unknown",
            'location': "Unknown"
        }
        lines = [line.strip() for line in section.get_text().split('\n') if line.strip()]
        current_match = None
        for line in lines:
            if re.search(r'\d+-\d+', line):
                match_data = parse_match_line(line)
                if match_data:
                    current_match = match_data
                    print(f"    Found match: {match_data['winner']} vs {match_data['loser']} ({match_data['score']})")
            elif current_match and line.lower().startswith(('left arm', 'right arm', 'righ arm')):
                category_data = parse_category_line(line)
                current_match.update(category_data)
                print(f"      Category: {category_data['arm']} Arm {category_data['weight_category']}")
                matches.append(current_match)
                current_match = None
        if matches:
            event = {
                "event_title": event_info['title'],
                "event_date": event_info['date'],
                "event_location": event_info['location'],
                "matches": matches
            }
            events.append(event)
            print(f"✓ Parsed event: {event_info['title']} with {len(matches)} matches")
    return events

def save_results_to_file(events, filename=EVW_EVENTS_FILE):
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
    print("Sample of East vs West results:")
    print("=" * 60)
    for event in events[:max_events]:
        print(f"\nEvent: {event['event_title']}")
        print(f"Date: {event['event_date']}")
        print(f"Location: {event['event_location']}")
        print(f"Matches: {len(event['matches'])}")
        print("-" * 40)
        for i, match in enumerate(event['matches'][:max_matches_per_event]):
            title_flag = " (Title)" if match.get('is_title', False) else ""
            print(f"{i+1}. {match['winner']} def. {match['loser']} ({match['score']})")
            print(f"   {match['arm']} Arm {match['weight_category']}{title_flag}")
        if len(event['matches']) > max_matches_per_event:
            print(f"   ... and {len(event['matches']) - max_matches_per_event} more matches")

if __name__ == "__main__":
    print("Scraping East vs West results from official website...")
    print("=" * 15)
    events = scrape_and_parse_east_vs_west()
    if events:
        display_sample_results(events)
        save_results_to_file(events)
        print(f"\n✓ Total East vs West events parsed: {len(events)}")
        print(f"✓ Total matches parsed: {sum(len(e['matches']) for e in events)}")
    else:
        print("✗ Failed to parse East vs West results.")
