from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
MEDIA_DIR = BASE_DIR / "media"
AUDIO_DIR = MEDIA_DIR / "audio"
TRANSCRIPT_DIR = DATA_DIR / "transcripts"
EVW_EVENTS_FILE = DATA_DIR / "events" / "east_vs_west_events.json"
KOTT_EVENTS_FILE = DATA_DIR / "events" / "kott_events.json"
HF_TOKEN = "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"
SHALLOWSEEK_APIK="sk-0cc54fb71e7c4b4381d5fafad5e7d1f5"
YOUTUBE_API_KEY="AIzaSyBkSNYJxSMBlqLkZXTDNZ1dAFyABuSKUwE"
API_URL="https://api.deepseek.com/v1/chat/completions"
