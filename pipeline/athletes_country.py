import json
from pathlib import Path
from difflib import get_close_matches
import sys

# Append project root for imports
sys.path.append(str(Path(__file__).resolve().parents[1]))
from pipeline.config import GOLDSARM_DIR, DATA_DIR

output_path = DATA_DIR / "athletes_country_map.json"
unique_athletes_file = DATA_DIR / "unique_athletes.json"

# Manual corrections for unmatched names
manual_name_map = {
    "Aitbek Beket": "Beket Aitbek",
    "Aleksandr Beziazykov": "Aleksandr “Schoolboy” Beziazykov",
    "Andrew Cobra Rhodes": "Cobra Rhodes",
    "Denis Ivanovich Tsyplenkov": "Denis Cyplenkov",
    "Dustin Alan Hyatt": "Dustin Hyatt",
    "Malin Kleinsmith": "Malin Bergström",
    "Rosa Maria Acosta": "Rosa Acosta (Boltadano)",
    "Ryan Bull Belanger": "Ryan Belanger",
    "Sedrakyan Vrezh": "Vrezh Sedrakyan",
    "Vladyslav Dzisiak": "Vlad Dzisiak",
    "Yusuf Ziya Yildizoglu": "Yusuf Yıldızoğlu"
}

# Dictionary to store athlete name → country
athlete_country = {}


print(f"📂 Scanning directory: {GOLDSARM_DIR}")

# Step 1: Build initial athlete → country map
for file in sorted(GOLDSARM_DIR.glob("*.json")):
    try:
        with open(file, "r", encoding="utf-8") as f:
            data = json.load(f)
        name = data.get("name")
        country = data.get("country")
        if name and country:
            athlete_country[name] = country
            print(f"✅ Loaded: {file.name} → {name}: {country}")
        else:
            print(f"⚠️ Skipped (missing name/country): {file.name}")
    except Exception as e:
        print(f"❌ Error reading {file.name}: {e}")

# Step 2: Load unique athlete names
with open(unique_athletes_file, "r", encoding="utf-8") as f:
    unique_athletes = json.load(f)

# Step 3: Match and correct names using fuzzy matching + manual override
corrected_athlete_country = {}
for original_name, country in athlete_country.items():
    if original_name in manual_name_map:
        corrected_name = manual_name_map[original_name]
        print(f"✍️ Manually corrected: '{original_name}' → '{corrected_name}'")
    else:
        match = get_close_matches(original_name, unique_athletes, n=1, cutoff=0.85)
        if match:
            corrected_name = match[0]
            if corrected_name != original_name:
                print(f"🔄 Auto-corrected: '{original_name}' → '{corrected_name}'")
        else:
            print(f"❓ No close match for: {original_name}")
            corrected_name = original_name  # fallback

    corrected_athlete_country[corrected_name] = country

# Step 4: Save the corrected result
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(corrected_athlete_country, f, ensure_ascii=False, indent=2)

print(f"\n💾 Saved corrected athlete-country map to: {output_path}")