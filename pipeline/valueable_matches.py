import json
from collections import defaultdict
from pathlib import Path
import sys
from difflib import get_close_matches
from datetime import datetime

sys.path.append(str(Path(__file__).resolve().parents[1]))
from pipeline.config import EVW_EVENTS_FILE, KOTT_EVENTS_FILE, DATA_DIR

def load_events():
    with open(EVW_EVENTS_FILE, 'r', encoding='utf-8') as f:
        east_vs_west_events = json.load(f)
    with open(KOTT_EVENTS_FILE, 'r', encoding='utf-8') as f:
        kott_events = json.load(f)
    return east_vs_west_events + kott_events

def build_athlete_match_history(events):
    athlete_matches = defaultdict(list)
    all_future_matches = []
    for event in events:
        event_title = event.get('event_title')
        event_date = event.get('event_date')
        event_dt = datetime.strptime(event_date, "%B %d, %Y")
        for match in event.get('matches', []):
            participants = match['participants']
            match_info = {
                'event': event_title,
                'date': event_date,
                'date_dt': event_dt,
                'winner': match['winner'],
                'loser': match['loser'],
                'score': match['score'],
                'arm': match['arm'],
                'participants': participants
            }
            # Collect matches for future comparison loop
            all_future_matches.append(match_info)
            # Build each athlete's match history
            for athlete in participants:
                opponent = [p for p in participants if p != athlete][0]
                result = 'win' if match['winner'] == athlete else 'loss'
                athlete_matches[athlete].append({
                    'event': event_title,
                    'date': event_date,
                    'date_dt': event_dt,
                    'opponent': opponent,
                    'result': result,
                    'score': match['score'],
                    'arm': match['arm']
                })
    return athlete_matches, all_future_matches

def get_valuable_info(a1, a2, match_date_dt, athlete_matches):
    matches_a1 = [m for m in athlete_matches.get(a1, []) if m['date_dt'] < match_date_dt]
    matches_a2 = [m for m in athlete_matches.get(a2, []) if m['date_dt'] < match_date_dt]
    opponents_a1 = set(m['opponent'] for m in matches_a1)
    opponents_a2 = set(m['opponent'] for m in matches_a2)
    shared = opponents_a1 & opponents_a2

    # Direct shared opponents logic
    head_to_head = [m for m in matches_a1 if m['opponent'] == a2]
    head_to_head += [m for m in matches_a2 if m['opponent'] == a1]
    valuable_shared_results = []
    mma_math_positive = 0
    mma_math_negative = 0
    for opp in shared:
        if opp == a2 or opp == a1:
            continue  # Skip each other
        a1_matches = [m for m in matches_a1 if m['opponent'] == opp]
        a2_matches = [m for m in matches_a2 if m['opponent'] == opp]
        a1_best = next((m for m in a1_matches if m['result'] == 'win'), None)
        a2_best = next((m for m in a2_matches if m['result'] == 'win'), None)
        if (a1_best and not a2_best) or (a2_best and not a1_best):
            result = {
                'shared_opponent': opp,
                a1 + '_vs_' + opp: 'win ' + a1_best['score'] if a1_best else 'no win',
                a2 + '_vs_' + opp: 'win ' + a2_best['score'] if a2_best else 'no win'
            }
            if a1_best and not a2_best:
                mma_math_positive += 1
            if a2_best and not a1_best:
                mma_math_negative += 1
            valuable_shared_results.append(result)

    num_shared_opponents_value = mma_math_positive - mma_math_negative
    has_head_to_head = 1 if head_to_head else 0
    head_to_head_result = 0
    if head_to_head:
        for m in head_to_head:
            if m['opponent'] == a2 and m['result'] == 'win':
                head_to_head_result = 1
            elif m['opponent'] == a2 and m['result'] == 'loss':
                head_to_head_result = -1

    # --- Second-order MMA math (opponent-of-opponent) logic ---
    second_order_valuable = []
    second_order_mma_math_positive = 0
    second_order_mma_math_negative = 0
    second_order_mma_math_difference = 0

    # For each of A's opponents and each of B's opponents (excluding each other)
    for o_a in opponents_a1 - {a2, a1}:
        for o_b in opponents_a2 - {a1, a2}:
            # All matches before date for o_a and o_b
            o_a_matches = [m for m in athlete_matches.get(o_a, []) if m['date_dt'] < match_date_dt]
            o_b_matches = [m for m in athlete_matches.get(o_b, []) if m['date_dt'] < match_date_dt]
            o_a_opps = set(m['opponent'] for m in o_a_matches)
            o_b_opps = set(m['opponent'] for m in o_b_matches)
            shared_second = o_a_opps & o_b_opps - {a1, a2, o_a, o_b}
            for shared_o in shared_second:
                # Get best win for o_a and o_b vs shared_o
                o_a_best = next((m for m in o_a_matches if m['opponent'] == shared_o and m['result'] == 'win'), None)
                o_b_best = next((m for m in o_b_matches if m['opponent'] == shared_o and m['result'] == 'win'), None)
                if (o_a_best and not o_b_best) or (o_b_best and not o_a_best):
                    entry = {
                        'a1_opponent': o_a,
                        'a2_opponent': o_b,
                        'shared_second_order': shared_o,
                        o_a + '_vs_' + shared_o: 'win ' + o_a_best['score'] if o_a_best else 'no win',
                        o_b + '_vs_' + shared_o: 'win ' + o_b_best['score'] if o_b_best else 'no win'
                    }
                    if o_a_best and not o_b_best:
                        second_order_mma_math_positive += 1
                    if o_b_best and not o_a_best:
                        second_order_mma_math_negative += 1
                    second_order_valuable.append(entry)

    num_second_order_valuable = len(second_order_valuable)
    second_order_mma_math_difference = second_order_mma_math_positive - second_order_mma_math_negative

    # --- Output ---
    output = {}
    if head_to_head:
        output['head_to_head'] = [
            {k: v for k, v in m.items() if k in ['event', 'date', 'opponent', 'result', 'score', 'arm']}
            for m in head_to_head
        ]
    if valuable_shared_results:
        output['valuable_shared_results'] = valuable_shared_results
    if second_order_valuable:
        output['second_order_valuable_shared_results'] = second_order_valuable

    output['num_shared_opponents_value'] = num_shared_opponents_value
    output['mma_math_positive'] = mma_math_positive
    output['mma_math_negative'] = mma_math_negative
    output['has_head_to_head'] = has_head_to_head
    output['head_to_head_result'] = head_to_head_result
    output['num_second_order_valuable'] = num_second_order_valuable
    output['second_order_mma_math_positive'] = second_order_mma_math_positive
    output['second_order_mma_math_negative'] = second_order_mma_math_negative
    output['second_order_mma_math_difference'] = second_order_mma_math_difference
    
    return output

def analyze_all_matches(athlete_matches, all_future_matches, save_path):
    # Use set to avoid duplicate pairs (A,B) vs (B,A)
    done_pairs = set()
    results = []
    for match in all_future_matches:
        a1, a2 = match['participants']
        date_dt = match['date_dt']
        pair_key = tuple(sorted([a1, a2])) + (date_dt,)
        if pair_key in done_pairs:
            continue
        done_pairs.add(pair_key)
        info = get_valuable_info(a1, a2, date_dt, athlete_matches)
        # Only save matches with valuable info
        if info:
            result_entry = {
                'match': {
                    'event': match['event'],
                    'date': match['date'],
                    'arm': match['arm'],
                    'participants': match['participants'],
                    'score': match['score']
                },
                'analysis': info
            }
            results.append(result_entry)
    # Save to json
    with open(save_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"Saved results to {save_path}")

if __name__ == '__main__':
    events = load_events()
    athlete_matches, all_future_matches = build_athlete_match_history(events)
    save_path = Path(DATA_DIR) / 'valuable_comparisons.json'
    analyze_all_matches(athlete_matches, all_future_matches, save_path)
