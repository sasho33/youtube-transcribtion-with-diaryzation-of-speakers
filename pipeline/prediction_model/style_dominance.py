import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from itertools import combinations
from pathlib import Path
import sys
import json


sys.path.append(str(Path(__file__).resolve().parents[2]))
from pipeline.config import UPDATED_TRAINING_FEATURES_WITH_TRAVEL_STATS, STYLES_COMBO_RATES_FILE

df = pd.read_csv(UPDATED_TRAINING_FEATURES_WITH_TRAVEL_STATS)

def style_vs_style_table(df):
    styles = set(df['f1_style_dominant'].dropna()) | set(df['f2_style_dominant'].dropna())
    styles = {s for s in styles if s and s != 'Unknown'}

    results = []
    checked = set()
    for s1, s2 in combinations(styles, 2):
        mask = (
            ((df['f1_style_dominant'] == s1) & (df['f2_style_dominant'] == s2)) |
            ((df['f1_style_dominant'] == s2) & (df['f2_style_dominant'] == s1))
        )
        matches = df[mask]
        if len(matches) == 0:
            continue

        s1_wins = (
            ((matches['f1_style_dominant'] == s1) & (matches['winner'] == matches['fighter_1'])).sum() +
            ((matches['f2_style_dominant'] == s1) & (matches['winner'] == matches['fighter_2'])).sum()
        )
        s2_wins = (
            ((matches['f1_style_dominant'] == s2) & (matches['winner'] == matches['fighter_1'])).sum() +
            ((matches['f2_style_dominant'] == s2) & (matches['winner'] == matches['fighter_2'])).sum()
        )
        total = len(matches)
        s1_pct = 100 * s1_wins / total if total > 0 else 0.0
        s2_pct = 100 * s2_wins / total if total > 0 else 0.0

        pair = tuple(sorted([s1, s2]))
        if pair not in checked:
            checked.add(pair)
            results.append({
                'Style 1': s1,
                'Style 2': s2,
                'Style 1 Wins': s1_wins,
                'Style 2 Wins': s2_wins,
                'Total Matches': total,
                'Style 1 Success %': round(s1_pct, 1),
                'Style 2 Success %': round(s2_pct, 1)
            })
    return pd.DataFrame(results).sort_values(by='Total Matches', ascending=False)

style_vs_style_df = style_vs_style_table(df)

print("=== Style vs Style Success Table (Top 20 by Matches) ===")
print(style_vs_style_df.head(20).to_string(index=False))

print("Additional function test:")
def style_vs_style_success(df, style1, style2):
    if style1 == style2:
        print(f"Styles must be different. ({style1} vs {style2})")
        return (0, 0, 0.0)
    mask = (
        ((df['f1_style_dominant'] == style1) & (df['f2_style_dominant'] == style2)) |
        ((df['f1_style_dominant'] == style2) & (df['f2_style_dominant'] == style1))
    )
    matches = df[mask]
    if len(matches) == 0:
        print(f"No matches between {style1} and {style2}")
        return (0, 0, 0.0)
    s1_wins = (
        ((matches['f1_style_dominant'] == style1) & (matches['winner'] == matches['fighter_1'])).sum() +
        ((matches['f2_style_dominant'] == style1) & (matches['winner'] == matches['fighter_2'])).sum()
    )
    total = len(matches)
    pct = (s1_wins / total * 100) if total > 0 else 0.0
    print(f"{style1} vs {style2}: {s1_wins}/{total} wins ({pct:.1f}%) for {style1}")
    return s1_wins, total, pct

print(style_vs_style_success(df, 'Toproll', 'Hook'))

# --- PLOT STYLE vs STYLE ---
top_n = 12
plot_df = style_vs_style_df.head(top_n)[::-1]

bar_labels = [f"{s1} vs {s2}" for s1, s2 in zip(plot_df['Style 1'], plot_df['Style 2'])]
style1_wins = plot_df['Style 1 Wins']
style2_wins = plot_df['Style 2 Wins']
success_pct = plot_df['Style 1 Success %']
y_pos = np.arange(len(bar_labels))

bar_width = 0.4
fig, ax = plt.subplots(figsize=(16, 7))
bars1 = ax.barh(y_pos - bar_width/2, style1_wins, height=bar_width, color='royalblue', label='Style 1')
bars2 = ax.barh(y_pos + bar_width/2, style2_wins, height=bar_width, color='gold', label='Style 2')

for bar, wins in zip(bars1, style1_wins):
    ax.text(bar.get_width()/2, bar.get_y() + bar.get_height()/2, f"{wins}", ha='center', va='center', color='white', fontweight='bold', fontsize=12)
for bar, wins in zip(bars2, style2_wins):
    ax.text(bar.get_width()/2, bar.get_y() + bar.get_height()/2, f"{wins}", ha='center', va='center', color='black', fontweight='bold', fontsize=12)
for i, (w1, w2, pct,s2) in enumerate(zip(style1_wins, style2_wins, success_pct, plot_df['Style 2'])):
    max_width = max(w1, w2)
    ax.text(max_width + 2, y_pos[i], f"{(100-pct):.1f}% success for {s2} ", va='center', ha='left', color='green', fontweight='bold', fontsize=12)
ax.set_yticks(y_pos)
ax.set_yticklabels(bar_labels)
ax.set_xlabel('Number of Wins')
ax.set_title('Top 10 Dominant Style-vs-Style Matchups\n(Wins for Both Styles, Success % for Style 1)')
ax.legend(["Style 1", "Style 2"], loc="lower right")
plt.tight_layout()
plt.show()

# === NEW: STYLE COMBINATION ANALYSIS (for f1 and f2 separately, then aggregate) ===
def get_style_combo(dominant, additional):
    if pd.isna(dominant) or dominant == "Unknown":
        return None
    if pd.isna(additional) or additional == "Unknown":
        return dominant
    return f"{dominant} + {additional}"

def aggregate_style_combos_pairs(df):
    """
    Aggregate win stats for all (dominant, additional) style pairs as separate columns.
    Skips rows where additional is missing/unknown.
    """
    combo_records = []
    for idx, row in df.iterrows():
        dom1, add1 = row['f1_style_dominant'], row['f1_style_additional']
        dom2, add2 = row['f2_style_dominant'], row['f2_style_additional']

        # Fighter 1: Only if both styles are present
        if pd.notna(dom1) and pd.notna(add1) and add1 != "Unknown" and dom1 != "Unknown":
            win = 1 if row['winner'] == row['fighter_1'] else 0
            combo_records.append({'style_1': dom1, 'style_2': add1, 'win': win})

        # Fighter 2: Only if both styles are present
        if pd.notna(dom2) and pd.notna(add2) and add2 != "Unknown" and dom2 != "Unknown":
            win = 1 if row['winner'] == row['fighter_2'] else 0
            combo_records.append({'style_1': dom2, 'style_2': add2, 'win': win})

    return pd.DataFrame(combo_records)

combo_df = aggregate_style_combos_pairs(df)
combo_summary = combo_df.groupby(['style_1', 'style_2']).agg({'win': ['sum', 'count']})
combo_summary.columns = ['wins', 'matches']
combo_summary['success_pct'] = (combo_summary['wins'] / combo_summary['matches'] * 100).round(1)
combo_summary = combo_summary.reset_index().sort_values('matches', ascending=False)

# --- SAVE TO JSON --- #
def tolist(df):
    """Convert DataFrame to list of dicts (for JSON serializing)"""
    return [row._asdict() if hasattr(row, "_asdict") else dict(row) for _, row in df.iterrows()]

# 1. Style vs Style rates
style_vs_style_json = []
for _, row in style_vs_style_df.iterrows():
    style_vs_style_json.append({
        "style_1": row['Style 1'],
        "style_2": row['Style 2'],
        "style_1_wins": int(row['Style 1 Wins']),
        "style_2_wins": int(row['Style 2 Wins']),
        "total_matches": int(row['Total Matches']),
        "style_1_success_pct": float(row['Style 1 Success %']),
        "style_2_success_pct": float(row['Style 2 Success %']),
    })

# 2. Style Combo rates
style_combo_json = []
for _, row in combo_summary.iterrows():
    style_combo_json.append({
        "style_1": row['style_1'],
        "style_2": row['style_2'],
        "wins": int(row['wins']),
        "matches": int(row['matches']),
        "success_pct": float(row['success_pct'])
    })

# Now style_combo_json will look like you want!
json_out = {
    "style_vs_style": style_vs_style_json,  # unchanged, from earlier in your code
    "style_combos": style_combo_json
}
with open(STYLES_COMBO_RATES_FILE, "w", encoding="utf-8") as f:
    json.dump(json_out, f, indent=2, ensure_ascii=False)
print(f"[✅] Saved new style statistics to {STYLES_COMBO_RATES_FILE.resolve()}")

# --- PLOT STYLE COMBO ---
plot_combo = combo_summary.head(15)[::-1].reset_index(drop=True)
y_pos = np.arange(len(plot_combo))
bar_labels = [f"{row['style_1']} + {row['style_2']}" for _, row in plot_combo.iterrows()]

fig, ax = plt.subplots(figsize=(16, 7))
bars = ax.barh(y_pos, plot_combo['wins'], color='darkcyan', height=0.5)

# Win number inside bar
for bar, wins in zip(bars, plot_combo['wins']):
    ax.text(bar.get_width()/2, bar.get_y() + bar.get_height()/2, f"{int(wins)}",
            ha='center', va='center', color='white', fontweight='bold', fontsize=12)

# Success percentage outside bar
for idx, (wins, pct) in enumerate(zip(plot_combo['wins'], plot_combo['success_pct'])):
    ax.text(wins + plot_combo['wins'].max()*0.05, idx, f"{pct:.1f}% success overall",
            va='center', ha='left', color='green', fontweight='bold', fontsize=12)

ax.set_yticks(y_pos)
ax.set_yticklabels(bar_labels)
ax.set_xlabel('Number of Wins')
ax.set_title('Top 15 Most Frequent Style Combinations\n(Wins and Success %)')
ax.set_xlim(0, plot_combo['wins'].max() * 1.25)
plt.tight_layout()
plt.show()


