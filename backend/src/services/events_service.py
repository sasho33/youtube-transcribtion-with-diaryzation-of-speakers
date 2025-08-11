# backend/src/services/events_service.py
import json
from pathlib import Path
import sys
from functools import lru_cache
from typing import Optional  # <-- added

# Make project root importable
sys.path.append(str(Path(__file__).resolve().parents[2]))
from config import EVW_EVENTS_FILE, KOTT_EVENTS_FILE

@lru_cache(maxsize=2)
def _load_events(source: str):
    if source == "evw":
        with open(EVW_EVENTS_FILE, encoding="utf-8") as f:
            return json.load(f)
    if source == "kott":
        with open(KOTT_EVENTS_FILE, encoding="utf-8") as f:
            return json.load(f)
    raise ValueError("Unknown source; expected 'evw' or 'kott'.")

def list_events(source: Optional[str] = None):  # <-- fixed for Python 3.9
    """Return events for one source or both combined."""
    if source in ("evw", "kott"):
        return _load_events(source)

    evw = _load_events("evw")
    kott = _load_events("kott")
    return evw + kott

def get_event_by_title(source: str, title: str):
    """Find an event by exact title within a source."""
    events = _load_events(source)
    for e in events:
        if e.get("event_title", "").strip().lower() == title.strip().lower():
            return e
    return None

def get_event_by_title_any(title: str):
    """Find an event by title in both EvW and KOTT."""
    for src in ("evw", "kott"):
        event = get_event_by_title(src, title)
        if event:
            event["source"] = src  # optional, so frontend knows where it came from
            return event
    return None