# ==========================================
# 月別レース定義とスキル読み込み
# race/races.json と race/{id}/skills.json を参照
# ==========================================

import json
from pathlib import Path

RACE_DIR = Path(__file__).resolve().parent / "race"


def load_races() -> list[dict]:
    """race/races.json からレース一覧を返す"""
    p = RACE_DIR / "races.json"
    if not p.exists():
        return []
    with open(p, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("races", [])


def load_race_skills(race_id: str) -> list[dict]:
    """
    レースIDに対応する有効スキルを返す。
    race/{race_id}/skills.json がリストなら [{"name": s, "tier": "おすすめ"}] に変換。
    なければ []。
    """
    race_folder = RACE_DIR / race_id
    skills_file = race_folder / "skills.json"
    if not skills_file.exists():
        return []
    with open(skills_file, "r", encoding="utf-8") as f:
        raw = json.load(f)
    if isinstance(raw, list):
        return [{"name": s, "tier": "おすすめ"} if isinstance(s, str) else s for s in raw]
    return []


def get_race_by_id(race_id: str) -> dict | None:
    """レースIDからメタ情報を返す"""
    for r in load_races():
        if r.get("id") == race_id:
            return r
    return None
