# ==========================================
# レースフォルダ内のスクショからスキルをOCRで抽出し、skills.json に保存する
# 使い方: python race/extract_race_skills.py 202602_LOH
# ==========================================

import json
import os
import re
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

try:
    import cv2
    import numpy as np
    import pytesseract
    import difflib
except ImportError as e:
    print(f"⚠️ 依存: pip install opencv-python pytesseract numpy を実行してください: {e}")
    sys.exit(1)


def load_known_skills_from_cards(path: str = None) -> set:
    """cards.json から全ユニークなスキル名を取得"""
    p = path or ROOT / "cards.json"
    if not p.exists():
        return set()
    with open(p, "r", encoding="utf-8") as f:
        cards = json.load(f)
    known = set()
    for c in cards:
        for s in c.get("skills") or []:
            if s and str(s).strip():
                known.add(str(s).strip())
    return known


def imread_japanese(filename: str):
    try:
        n = np.fromfile(filename, np.uint8)
        return cv2.imdecode(n, cv2.IMREAD_COLOR)
    except Exception:
        return None


def process_folder(folder_path: Path, known_skills: set) -> list[str]:
    """フォルダ内の画像をOCRし、known_skills と照合してスキル名リストを返す"""
    if not folder_path.is_dir():
        return []
    exts = (".png", ".jpg", ".jpeg", ".bmp")
    images = [f for f in folder_path.iterdir() if f.suffix.lower() in exts]
    if not images:
        return []

    folder_text = ""
    for img_path in sorted(images):
        try:
            img = imread_japanese(str(img_path))
            if img is None:
                continue
            img = cv2.resize(img, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            _, binary = cv2.threshold(gray, 140, 255, cv2.THRESH_BINARY)
            text = pytesseract.image_to_string(binary, lang="jpn", config="--psm 6")
            folder_text += text + "\n"
        except Exception as e:
            print(f"  警告: {img_path.name} - {e}")

    ignore = ["獲得", "Pt", "Lv", "詳細", "スキル", "失敗", "成功", "ヒント", "サポート", "イベント", "OK", "キャンセル", "おすすめ"]
    final_skills = []
    for line in folder_text.split("\n"):
        line = line.strip()
        if len(line) < 2:
            continue
        for part in re.split(r"[\s　]+", line):
            part = part.strip()
            if len(part) < 2 or any(w in part for w in ignore) or re.match(r"^[0-9\W]+$", part):
                continue
            if part in known_skills:
                final_skills.append(part)
            else:
                matches = difflib.get_close_matches(part, known_skills, n=1, cutoff=0.55)
                if matches:
                    final_skills.append(matches[0])

    return sorted(list(set(final_skills)))


def main():
    if len(sys.argv) < 2:
        print("使い方: python race/extract_race_skills.py 202602_LOH")
        sys.exit(1)
    race_id = sys.argv[1].strip()
    race_dir = ROOT / "race" / race_id
    if not race_dir.is_dir():
        print(f"エラー: フォルダが見つかりません: {race_dir}")
        sys.exit(1)

    tesseract_path = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    if os.path.exists(tesseract_path):
        pytesseract.pytesseract.tesseract_cmd = tesseract_path

    known = load_known_skills_from_cards()
    print(f"辞書: {len(known)} スキル (cards.json)")
    skills = process_folder(race_dir, known)
    out_path = race_dir / "skills.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(skills, f, ensure_ascii=False, indent=2)
    print(f"保存: {out_path} ({len(skills)} 件)")


if __name__ == "__main__":
    main()
