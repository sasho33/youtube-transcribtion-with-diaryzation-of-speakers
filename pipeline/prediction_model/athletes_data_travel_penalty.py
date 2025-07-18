import json
import re
from pathlib import Path
from unidecode import unidecode
import sys

# Setup project path and import config
sys.path.append(str(Path(__file__).resolve().parents[2]))
from pipeline.config import ATHLETES_DIR, UNIQUE_ATHLETES_FILE, EVW_EVENTS_FILE, KOTT_EVENTS_FILE, TRANSCRIPT_DIR, DATA_DIR