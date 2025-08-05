import pandas as pd
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))
from pipeline.config import (
    UPDATED_TRAINING_FEATURES_WITH_TRAVEL_STATS,
    TRAINING_MODEL_DATASET
)

# Load your data
df = pd.read_csv(UPDATED_TRAINING_FEATURES_WITH_TRAVEL_STATS)

for col in ['f1_winrate_last_5', 'f2_winrate_last_5']:
    if col in df.columns:
        df[col] = df[col].round(2)

# Identify all f1_ and f2_ columns
f1_cols = [col for col in df.columns if col.startswith('f1_')]
f2_cols = [col for col in df.columns if col.startswith('f2_')]

# MMA Math and related columns
mma_pos_col = 'mma_math_positive'
mma_neg_col = 'mma_math_negative'
second_order_pos = 'second_order_mma_math_positive'
second_order_neg = 'second_order_mma_math_negative'

# Style and advantage
style_combo_1 = 'f1_style_combo_success_percent'
style_combo_2 = 'f2_style_combo_success_percent'
style_advantage = 'athlete1_style_advantage_rate'

# Advantage columns to invert
advantage_cols = ['weight_advantage', 'height_advantage', 'domestic_advantage', 'head_to_head_result']

# Prepare the output list
new_rows = []
for idx, row in df.iterrows():
    # Append the original row (winner as fighter_1, label=1)
    new_rows.append(row.copy())
    
    # Create a swapped row (loser as fighter_1, label=0)
    swapped = row.copy()
    swapped['fighter_1'], swapped['fighter_2'] = row['fighter_2'], row['fighter_1']
    swapped['label'] = 0
    # Swap all f1_ and f2_ columns
    for c1, c2 in zip(f1_cols, f2_cols):
        swapped[c1], swapped[c2] = row[c2], row[c1]
    # Invert advantages
    for adv in advantage_cols:
        if adv in swapped:
            swapped[adv] = -row[adv] if pd.notnull(row[adv]) else row[adv]
    # Swap style combo success rates
    if style_combo_1 in swapped and style_combo_2 in swapped:
        swapped[style_combo_1], swapped[style_combo_2] = row[style_combo_2], row[style_combo_1]
    # Swap MMA math pos/neg and second order pos/neg
    if mma_pos_col in swapped and mma_neg_col in swapped:
        swapped[mma_pos_col], swapped[mma_neg_col] = row[mma_neg_col], row[mma_pos_col]
    if second_order_pos in swapped and second_order_neg in swapped:
        swapped[second_order_pos], swapped[second_order_neg] = row[second_order_neg], row[second_order_pos]
    # Invert head_to_head_result
    if 'head_to_head_result' in swapped:
        swapped['head_to_head_result'] = -row['head_to_head_result'] if pd.notnull(row['head_to_head_result']) else row['head_to_head_result']
    # Invert athlete1_style_advantage_rate if it's a difference (typically is)
    if pd.notnull(row['athlete1_style_advantage_rate']):
        swapped['athlete1_style_advantage_rate'] = round(100 - float(row['athlete1_style_advantage_rate']), 1)
    else:
        swapped['athlete1_style_advantage_rate'] = row['athlete1_style_advantage_rate']
    # Swap any other symmetric prediction columns (like f1_low_rank_predictions, etc.)
    pred_cols = ['f1_low_rank_predictions', 'f1_high_rank_predictions', 'f2_low_rank_predictions', 'f2_high_rank_predictions']
    if all(c in swapped for c in pred_cols):
        swapped['f1_low_rank_predictions'], swapped['f2_low_rank_predictions'] = row['f2_low_rank_predictions'], row['f1_low_rank_predictions']
        swapped['f1_high_rank_predictions'], swapped['f2_high_rank_predictions'] = row['f2_high_rank_predictions'], row['f1_high_rank_predictions']
        swapped['f1_all_rank_predictions'], swapped['f2_all_rank_predictions'] = row['f2_all_rank_predictions'], row['f1_all_rank_predictions']
    # Append swapped row
    new_rows.append(swapped)

# Build and save the new DataFrame
df_new = pd.DataFrame(new_rows)
df_new.to_csv(TRAINING_MODEL_DATASET, index=False)
print("[✅] Duplicated and swapped dataset saved.")

