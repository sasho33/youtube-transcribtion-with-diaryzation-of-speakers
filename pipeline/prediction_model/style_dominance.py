import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from itertools import combinations
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).resolve().parents[2]))
from pipeline.config import UPDATED_TRAINING_FEATURES_WITH_TRAVEL_STATS

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

# --- PLOT ---
top_n = 10
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

# Add win numbers inside each bar
for bar, wins in zip(bars1, style1_wins):
    ax.text(bar.get_width()/2, bar.get_y() + bar.get_height()/2, f"{wins}", ha='center', va='center', color='white', fontweight='bold', fontsize=12)
for bar, wins in zip(bars2, style2_wins):
    ax.text(bar.get_width()/2, bar.get_y() + bar.get_height()/2, f"{wins}", ha='center', va='center', color='black', fontweight='bold', fontsize=12)

# Add success % for Style 1 at end of both bars
for i, (w1, w2, pct) in enumerate(zip(style1_wins, style2_wins, success_pct)):
    max_width = max(w1, w2)
    ax.text(max_width + 2, y_pos[i], f"{pct:.1f}% success", va='center', ha='left', color='green', fontweight='bold', fontsize=12)

ax.set_yticks(y_pos)
ax.set_yticklabels(bar_labels)
ax.set_xlabel('Number of Wins')
ax.set_title('Top 10 Dominant Style-vs-Style Matchups\n(Wins for Both Styles, Success % for Style 1)')
ax.legend(["Style 1", "Style 2"], loc="lower right")
plt.tight_layout()
plt.show()
