import requests
from bs4 import BeautifulSoup
import json
import re
from unidecode import unidecode
from pathlib import Path
import sys

# Append project root to sys.path
sys.path.append(str(Path(__file__).resolve().parents[1]))
from pipeline.config import GOLDSARM_DIR, UNIQUE_ATHLETES_FILE

def sanitize_name(name):
    # Normalize name
    name = unidecode(name.lower().strip()).replace(" ", "-")
    # Remove invalid filename characters
    name = re.sub(r'[<>:"/\\|?*]', '', name)
    return name

def extract_number(text, unit):
    """Extract a float number followed by a specific unit."""
    match = re.search(rf"([\d.]+)\s*{unit}", text)
    return float(match.group(1)) if match else None

def parse_athlete_data(raw_data):
    """Convert scraped text fields into structured data."""
    def clean(value):
        return None if value == "---" else value

    result = {
        "name": raw_data.get("name"),
        "country": clean(raw_data.get("country")),
        "nickname": clean(raw_data.get("nickname")),
        "age": int(raw_data["age"]) if raw_data.get("age") and raw_data["age"].isdigit() else None,
        "weight_kg": extract_number(raw_data.get("weight", ""), "kg"),
        "height_cm": extract_number(raw_data.get("height", ""), "cm"),
        "occupation": clean(raw_data.get("occupation")),
        "bicep_cm": extract_number(raw_data.get("biceps", ""), "cm"),
        "forearm_cm": extract_number(raw_data.get("forearm", ""), "cm"),
        "wrist_cm": extract_number(raw_data.get("wrist", ""), "cm"),
    }

    return result


def scrape_athlete_data(athlete_name):
    slug = sanitize_name(athlete_name)
    filename = f"{slug}.json"
    log_path = GOLDSARM_DIR / filename

    if log_path.exists():
        print(f"⏭️  Skipping {athlete_name} — data already exists.")
        return

    url = f"https://www.goldsarm.com/armwrestlers/{slug}"
    response = requests.get(url)
    if response.status_code != 200:
        print(f"❌ Failed to fetch page for {athlete_name} (HTTP {response.status_code})")
        return

    soup = BeautifulSoup(response.text, 'html.parser')

    # ✅ Extract image URL
        # ✅ Extract image from profile section
    image_tag = soup.select_one("div.lg\\:flex img")  # CSS escapes `:` in class
    image_url = image_tag["src"] if image_tag else None

    if image_url:
        image_ext = image_url.split(".")[-1].split("?")[0]  # handle ? queries
        image_path = GOLDSARM_DIR / f"{slug}.{image_ext}"
        img_data = requests.get(image_url).content
        with image_path.open("wb") as img_file:
            img_file.write(img_data)
        print(f"🖼️  Saved image to {image_path.name}")
    else:
        print(f"⚠️  No image found for {athlete_name}")


    # ✅ Parse profile table
    table = soup.find("table", class_="details-table")
    if not table:
        print(f"❌ No details table found for {athlete_name}")
        return

    raw_data = {"name": athlete_name}
    for row in table.find_all("tr"):
        cells = row.find_all("td")
        if len(cells) == 2:
            key = cells[0].text.strip().lower()
            value = cells[1].text.strip()
            raw_data[key] = value

    parsed = parse_athlete_data(raw_data)
    # ✅ Fetch match info and attach
   
    # ✅ Ensure folder exists
    GOLDSARM_DIR.mkdir(parents=True, exist_ok=True)

    with log_path.open("w", encoding="utf-8") as f:
        json.dump(parsed, f, indent=2, ensure_ascii=False)

    print(f"✅ Saved data for {athlete_name} to {filename}")


def fetch_athlete_list():
    print("Fetching unique athletes from file...")
    with UNIQUE_ATHLETES_FILE.open("r", encoding="utf-8") as f:
        athletes = json.load(f)
    for athelete in athletes:
        scrape_athlete_data(athelete)
    print("All athletes processed.")
        
# Test it
# scrape_athlete_data("Alex Kurdecha")
if __name__ == "__main__":
    # fetch_athlete_list()
    names = [  "Rob Vigeant Jr",]
    for name in names:
        scrape_athlete_data(name)
