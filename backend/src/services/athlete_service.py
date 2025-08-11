import json
from pathlib import Path
from urllib.parse import unquote
import sys
from pathlib import Path


from config import UNIQUE_ATHLETES_WITH_DATA_FILE

# Load data once
_data_path = Path(UNIQUE_ATHLETES_WITH_DATA_FILE)
with open(_data_path, "r", encoding="utf-8") as f:
    _athletes_by_name = json.load(f)

_lower_index = {name.lower(): name for name in _athletes_by_name}

def get_all_athletes(q=None, country=None):
    results = []
    for name, obj in _athletes_by_name.items():
        if q and q.lower() not in name.lower():
            continue
        if country and (obj.get("country") or "").lower() != country.lower():
            continue
        results.append(obj)
    return results

def get_athlete_by_name(name):
    decoded = unquote(name)
    key = _lower_index.get(decoded.lower())
    if not key:
        return None
    return _athletes_by_name[key]


