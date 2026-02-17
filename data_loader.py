# ファイル名: data_loader.py

import json
from pathlib import Path

def load_cards_json(path: str = "cards.json"):
    """
    cards.json を読み込んで Python のリストとして返す
    """
    file_path = Path(path)

    if not file_path.exists():
        raise FileNotFoundError(f"{path} が見つかりません。")

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return data
