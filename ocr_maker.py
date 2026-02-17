import pytesseract
import cv2
import os
import re
import numpy as np
import pandas as pd
import difflib # 似ている文字を探すライブラリ

# ==========================================
# スクショ解析ツール（自動補正・最強版）
# 画像拡大 & 既存DBとの照合で精度を爆上げします
# ==========================================

tesseract_path = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

if os.path.exists(tesseract_path):
    pytesseract.pytesseract.tesseract_cmd = tesseract_path
else:
    print(f"⚠️ エラー: Tesseractが見つかりません: {tesseract_path}")

# ------------------------------------------
# 1. 正しいスキル辞書を作る
# ------------------------------------------
known_skills = set()
csv_path = 'cards.csv'

if os.path.exists(csv_path):
    print("📚 cards.csv から正しいスキル名を学習中...")
    try:
        df = pd.read_csv(csv_path)
        # 全カードのスキル列を結合してリスト化
        for skills_str in df['所持スキル'].fillna("").astype(str):
            for s in skills_str.split(','):
                s = s.strip()
                if s: known_skills.add(s)
    except Exception as e:
        print(f"⚠️ CSV読み込みエラー: {e}")
else:
    print("⚠️ cards.csv がないため、補正機能は弱くなります。")

print(f"✅ {len(known_skills)} 個の正しいスキル名を辞書に登録しました。\n")


def imread_japanese(filename):
    try:
        n = np.fromfile(filename, np.uint8)
        img = cv2.imdecode(n, cv2.IMREAD_COLOR)
        return img
    except Exception:
        return None

def process_folder(folder_path):
    if not os.path.exists(folder_path) or not os.path.isdir(folder_path):
        print(f"  ℹ️ フォルダが見つかりません (スキップ): {folder_path}")
        return []

    files = os.listdir(folder_path)
    extensions = ('.png', '.jpg', '.jpeg', '.bmp')
    image_files = [f for f in files if f.lower().endswith(extensions)]

    if not image_files:
        print(f"  ℹ️ 画像がありません: {folder_path}")
        return []

    print(f"  📸 {len(image_files)} 枚の画像を解析中...")
    
    folder_text = ""
    for img_file in image_files:
        full_path = os.path.join(folder_path, img_file)
        try:
            img = imread_japanese(full_path)
            if img is None: continue

            # ★工夫1: 画像を2倍に拡大する（これで小さい文字も読める！）
            img = cv2.resize(img, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)

            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            # 二値化（くっきりさせる）
            _, binary = cv2.threshold(gray, 140, 255, cv2.THRESH_BINARY)
            
            text = pytesseract.image_to_string(binary, lang='jpn', config='--psm 6')
            folder_text += text + "\n"
        except Exception as e:
            print(f"    エラー: {img_file} - {e}")

    # --- クリーニング & 自動補正 ---
    lines = folder_text.split('\n')
    final_skills = []
    
    ignore_words = ["獲得", "Pt", "Lv", "詳細", "スキル", "失敗", "成功", "ヒント", "サポート", "イベント", "OK", "キャンセル", "おすすめ"]

    for line in lines:
        line = line.strip()
        if len(line) < 2: continue
        
        # スペース分割
        parts = re.split(r'[\s　]+', line)
        
        for part in parts:
            part = part.strip()
            if len(part) < 2: continue
            if any(w in part for w in ignore_words): continue
            if re.match(r'^[0-9\W]+$', part): continue

            # ★工夫2: 自動補正ロジック
            # 辞書(cards.csv)の中に、この読み取った文字と「そっくりなスキル」があるか探す
            
            # 完全一致ならそのまま採用
            if part in known_skills:
                final_skills.append(part)
            else:
                # 似ているものを探す (一致率 0.6以上)
                matches = difflib.get_close_matches(part, known_skills, n=1, cutoff=0.6)
                if matches:
                    corrected = matches[0]
                    # print(f"    🔧 補正: '{part}' → '{corrected}'") # ログが見たい場合はコメント解除
                    final_skills.append(corrected)
                else:
                    # 辞書になくても、とりあえず読み取ったまま追加しておく
                    final_skills.append(part)

    return list(set(final_skills))

def main():
    targets = {
        "nige": "逃げ",
        "senko": "先行",
        "sashi": "差し",
        "oikomi": "追込"
    }
    
    base_dir = "images"
    final_output = "# 自動生成されたスキルリスト\n\n"

    print("🚀 解析と自動補正を開始します...\n")

    for folder_name, jp_name in targets.items():
        print(f"📂 脚質【{jp_name}】({folder_name}) の処理中...")
        target_path = os.path.join(base_dir, folder_name)
        skills = process_folder(target_path)
        skills.sort()

        var_name = f"skill_list_{folder_name}"
        final_output += f"# --- {jp_name}用スキル ---\n"
        final_output += f"{var_name} = [\n"
        for s in skills:
            final_output += f'    "{s}",\n'
        final_output += "]\n\n"
        
        print(f"  ✅ {len(skills)} 個のスキルを抽出しました。\n")

    with open("result_code.txt", "w", encoding="utf-8") as f:
        f.write(final_output)

    print("="*40)
    print("🎉 完了！ 'result_code.txt' を確認してください。")
    print("誤字がかなり減っているはずです！")

if __name__ == "__main__":
    main()