from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
MEDIA_DIR = BASE_DIR / "media"
AUDIO_DIR = MEDIA_DIR / "audio"
TRANSCRIPT_DIR = DATA_DIR / "transcripts"
EVW_EVENTS_FILE = DATA_DIR / "events" / "east_vs_west_events.json"
KOTT_EVENTS_FILE = DATA_DIR / "events" / "kott_events.json"