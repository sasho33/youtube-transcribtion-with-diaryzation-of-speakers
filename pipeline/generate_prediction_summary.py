import json
from pathlib import Path
from collections import defaultdict
import sys
from rapidfuzz import process, fuzz
import unicodedata

# Append project root for imports
sys.path.append(str(Path(__file__).resolve().parents[1]))
from pipeline.config import TRANSCRIPT_DIR, EVW_EVENTS_FILE, DATA_DIR, KOTT_EVENTS_FILE

SUMMARY_PATH = DATA_DIR / "predictor_summary.json"

# Mapping for known name normalizations
NAME_CORRECTIONS = {
    "coach ray": "Raimonds Liepins",
    "ray": "Raimonds Liepins",
    "raimonds liepiņš": "Raimonds Liepins",
    "unknown host": "Raimonds Liepins",
    "janis": "Janis Amolins",
    "yanis": "Janis Amolins",
    "jānis amolins": "Janis Amolins",
    "paulo": "Pavlo Derbedyenyev",
    "pavlo": "Pavlo Derbedyenyev",
    "paolo": "Pavlo Derbedyenyev",
    "pablo": "Pavlo Derbedyenyev",
    "paolo derbedyenyev": "Pavlo Derbedyenyev",
    "sergey kalinichenko": "Serhii Kalinichenko",
    "artem taranov": "Artem Taranenko",
    "ted": "Paul Linn",
    "paul": "Paul Linn",
    "rino mašić": "Rino Masic",
    "nugo chikadze": "Nugzari Chikadze",
    "nugo (nugzari chikadze)": "Nugzari Chikadze",
    "roman tsindeliani": "Betkili Oniani",
    "fia": "Fia Reisek",
    "paul lynn": "Paul Linn",
    "frank lamparell": "Frank Lamparelli",
    "sarah bäckman": "Sarah Backman",
    "mindaugas": "Mindaugas Tarasaitis",
    "ivan matushenko": "Ivan Matyushenko",
    "hermes gasparini": "Ermes Gasparini",
    "sultan": "Kydirgali Ongarbaev",
    "lars": "Lars Robbaken"
}
ALL_KNOWN_PARTICIPANTS = set()



def normalize_ascii(name: str) -> str:
    import unicodedata
    return unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")

def fuzzy_correct_name(name: str) -> str:
    if not ALL_KNOWN_PARTICIPANTS:
        return name
    name_ascii = normalize_ascii(name)
    all_ascii_names = {
        normalize_ascii(candidate): candidate for candidate in ALL_KNOWN_PARTICIPANTS
    }
    match, score, _ = process.extractOne(name_ascii, list(all_ascii_names.keys()), scorer=fuzz.token_sort_ratio)
    return all_ascii_names[match] if score > 80 else name

def normalize_name(name: str):
    name = name.strip().lower()
    return NAME_CORRECTIONS.get(name, name.title())

def load_event_results():
    def load(file):
        with open(file, "r", encoding="utf-8") as f:
            events = json.load(f)
        event_map = {}
        participant_map = defaultdict(list)
        for event in events:
            title = event["event_title"]
            for match in event["matches"]:
                normalized = tuple(sorted(normalize_name(p) for p in match["participants"]))
                event_map[(title, normalized)] = normalize_name(match.get("winner") or "")
                participant_map[normalized].append((title, normalize_name(match.get("winner") or "")))
        return event_map, participant_map

    evw, evw_part = load(EVW_EVENTS_FILE)
    kott, kott_part = load(KOTT_EVENTS_FILE)
    print(f"✅ Loaded {len(evw)} EVW matches and {len(kott)} KOTT matches")
    global ALL_KNOWN_PARTICIPANTS
    for (title, participants), winner in list(evw.items()) + list(kott.items()):
        ALL_KNOWN_PARTICIPANTS.update(participants)
    return evw, kott, {**evw_part, **kott_part}, evw_part

def fuzzy_merge(stats, threshold=90):
    merged = {}
    used = set()

    for name in stats:
        if name in used:
            continue
        group = [name]
        matches = process.extract(name, stats.keys(), scorer=fuzz.token_sort_ratio, score_cutoff=threshold)
        for match_name, score, _ in matches:
            if match_name != name and match_name not in used:
                group.append(match_name)

        canonical = group[0]

        total = sum(stats[n]["total_predictions"] for n in group)
        correct = sum(stats[n]["correct_predictions"] for n in group)
        unsure = sum(stats[n].get("unsure_predictions", 0) for n in group)
        potential = sum(stats[n].get("potential_matches_predictions", 0) for n in group)
        results_combined = []
        for n in group:
            results_combined.extend(stats[n].get("results", []))

        merged[canonical] = {
            "total_predictions": total,
            "correct_predictions": correct,
            "unsure_predictions": unsure,
            "potential_matches_predictions": potential,
            "results": results_combined,
            "success_rate": round((correct / total) * 100, 2) if (total) > 0 else 0.0
        }

        used.update(group)

    return merged


def evaluate_predictions(evw_results, kott_results, all_participants_map, evw_participants):
    stats = defaultdict(lambda: {
        "total_predictions": 0,
        "correct_predictions": 0,
        "unsure_predictions": 0,
        "potential_matches_predictions": 0,
        "results": [],
        "success_rate": 0.0
    })

    for event_dir in TRANSCRIPT_DIR.iterdir():
        identified_dir = event_dir / "Identified"
        if not identified_dir.exists():
            continue

        for json_file in identified_dir.glob("*.json"):
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                print(f"❌ Skipping invalid JSON: {json_file}")
                continue

            predictions = data.get("predictions", {})
            for speaker, blocks in predictions.items():
                for section in ["self_predictions", "third_party_predictions"]:
                    for pred in blocks.get(section, []):
                        event = pred.get("event")
                        participants = pred.get("match")
                        predicted = pred.get("predicted_winner")

                        if not event or not participants or not predicted:
                            continue

                        corrected_participants = [fuzzy_correct_name(normalize_name(p)) for p in participants]
                        norm_participants = tuple(sorted(corrected_participants))
                        pred_norm = fuzzy_correct_name(normalize_name(predicted))
                        key = (event, norm_participants)

                        actual = evw_results.get(key)
                        source = "EVW"

                        if actual is None:
                            actual = kott_results.get(key)
                            if actual:
                                print(f"ℹ️ Match not found in EVW, found in KOTT: {key}")
                                source = "KOTT"

                        if actual is None and norm_participants in evw_participants:
                            fallback = evw_participants[norm_participants]
                            if fallback:
                                event, actual = fallback[0]
                                print(f"✅ Match found by participants only in other EVW event: {event}")
                                source = "EVW (fallback)"

                        if actual is None and norm_participants in all_participants_map:
                            fallback = all_participants_map[norm_participants]
                            if fallback:
                                event, actual = fallback[0]
                                print(f"✅ Match found by participants only in: {event}")
                                source = "KOTT (fallback)"

                        match_info = {
                            "match": sorted(participants),
                            "event": event,
                            "predicted_winner": predicted,
                            "actual_winner": actual if actual else None,
                            "source": source if actual else "UNKNOWN"
                        }

                        if pred_norm not in norm_participants:
                            stats[speaker]["unsure_predictions"] += 1
                        elif not actual:
                            stats[speaker]["potential_matches_predictions"] += 1
                        else:
                            stats[speaker]["total_predictions"] += 1
                            if pred_norm == actual:
                                stats[speaker]["correct_predictions"] += 1

                        stats[speaker]["results"].append(match_info)

    for speaker, data in stats.items():
        total = data["total_predictions"]
        unsure = data["unsure_predictions"]
        potential = data["potential_matches_predictions"]
        correct = data["correct_predictions"]
        base = total if unsure + potential >= total else total - unsure - potential
        data["success_rate"] = round((correct / base) * 100, 2) if base > 0 else 0.0

        # Apply canonical name correction before fuzzy merge
    corrected_stats = defaultdict(lambda: {
        "total_predictions": 0,
        "correct_predictions": 0,
        "unsure_predictions": 0,
        "potential_matches_predictions": 0,
        "results": [],
        "success_rate": 0.0
    })

    for name, values in stats.items():
        canonical = normalize_name(name)
        corrected_stats[canonical]["total_predictions"] += values["total_predictions"]
        corrected_stats[canonical]["correct_predictions"] += values["correct_predictions"]
        corrected_stats[canonical]["unsure_predictions"] += values["unsure_predictions"]
        corrected_stats[canonical]["potential_matches_predictions"] += values["potential_matches_predictions"]
        corrected_stats[canonical]["results"].extend(values["results"])

    for speaker, data in corrected_stats.items():
        total = data["total_predictions"]
        unsure = data["unsure_predictions"]
        potential = data["potential_matches_predictions"]
        correct = data["correct_predictions"]
        base = total if unsure + potential >= total else total - unsure - potential
        data["success_rate"] = round((correct / base) * 100, 2) if base > 0 else 0.0

    merged = fuzzy_merge(corrected_stats, threshold=90)
    filter_and_save_summary(merged)
    return merged


def filter_and_save_summary(merged_stats):
    filtered = {
        name: {
            k: v for k, v in stats.items() if k != "results"
        }
        for name, stats in merged_stats.items()
        if stats["success_rate"] > 60 and stats["total_predictions"] > 5
    }
    sorted_filtered = dict(sorted(filtered.items(), key=lambda x: x[1]["success_rate"], reverse=True))
    output_path = DATA_DIR / "predictor_summary_filtered.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(sorted_filtered, f, indent=2, ensure_ascii=False)
    print(f"📄 Saved filtered summary to: {output_path}")

def save_json(data, path: Path):
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"✅ Saved: {path}")

if __name__ == "__main__":
    print("📥 Loading match results...")
    evw_results, kott_results, all_participants_map, evw_participants = load_event_results()

    print("🔍 Evaluating and merging all predictions...")
    merged_stats = evaluate_predictions(evw_results, kott_results, all_participants_map, evw_participants)

    save_json(merged_stats, SUMMARY_PATH)

    print("🎉 All done!")
