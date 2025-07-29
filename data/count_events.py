import json

with open('valuable_comparisons.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Count using all three types of valuable info:
# - Direct shared opponent (num_shared_opponents_value > 0)
# - Head to head (has_head_to_head == 1)
# - Second-order (num_second_order_valuable > 0)

valuable_count = sum(
    1 for entry in data
    if entry['analysis'].get('num_shared_opponents_value', 0) > 0
    or entry['analysis'].get('has_head_to_head', 0) == 1
    or entry['analysis'].get('num_second_order_valuable', 0) > 0
)

# For breakdown (optional, for analysis):
direct_count = sum(
    1 for entry in data if entry['analysis'].get('num_shared_opponents_value', 0) > 0
)
head_to_head_count = sum(
    1 for entry in data if entry['analysis'].get('has_head_to_head', 0) == 1
)
second_order_count = sum(
    1 for entry in data if entry['analysis'].get('num_second_order_valuable', 0) > 0
)

total = len(data)
print(f"Valuable matches (any kind): {valuable_count} / {total}")
print(f"  - With direct shared opponent: {direct_count}")
print(f"  - With head to head: {head_to_head_count}")
print(f"  - With second-order MMA math: {second_order_count}")
