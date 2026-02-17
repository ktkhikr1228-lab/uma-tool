
import json
from pathlib import Path

# Load cards.json
with open("cards.json", "r", encoding="utf-8") as f:
    cards = json.load(f)
    existing_names = {c["name"] for c in cards}

# Parse raw_data.txt
# Format seems to be tab separated? Or just lines?
# Line 2: 画像	名前	レアリティ	タイプ...
# Let's inspect raw_data.txt again.
# It seems to have lines with `\t` separator?

missing_cards = []
raw_path = Path("raw_data.txt")
if raw_path.exists():
    with open(raw_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
        for line in lines:
            parts = line.strip().split("\t")
            if len(parts) >= 2:
                # Part 1 is usually Name or "Image Name"
                # Looking at valid lines:
                # ［飛び出せ、キラメケ］アイネスフウジン_icon.jpg	［飛び出せ、キラメケ］アイネスフウジン	SSR	根性
                if len(parts) > 2 and parts[1].startswith("［"):
                     name = parts[1]
                     if name not in existing_names:
                         missing_cards.append(name)

print(f"Missing cards count: {len(missing_cards)}")
for m in missing_cards:
    print(f"- {m}")
