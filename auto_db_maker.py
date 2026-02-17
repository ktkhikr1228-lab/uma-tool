import pandas as pd
from bs4 import BeautifulSoup
import re
import os

# ==========================================
# Wiki解析用 DB作成ツール (フリースタイル検索版)
# ・「列番号」に頼らず、行内のデータをスキャンして項目を自動特定
# ・列ズレ、画像混入、ゴミデータを完全に回避
# ==========================================

target_file = "Wiki.html"
output_file = "cards.csv"

print(f"📂 '{target_file}' を解析します...")

if not os.path.exists(target_file):
    if os.path.exists("wiki.html"):
        target_file = "wiki.html"
        print(f"  ℹ️ '{target_file}' を発見。こちらを使用します。")
    else:
        print(f"❌ エラー: '{target_file}' が見つかりません！")
        exit()

# ---------------------------------------------------------
# 1. HTML読み込み
# ---------------------------------------------------------
soup = None
encodings = ['utf-8', 'cp932', 'shift_jis', 'euc-jp']

for enc in encodings:
    try:
        with open(target_file, "r", encoding=enc) as f:
            soup = BeautifulSoup(f, "html.parser")
        print(f"  ✅ 文字コード '{enc}' で読み込み成功")
        break
    except Exception:
        continue

if soup is None:
    print("❌ 読み込み失敗。")
    exit()

# ---------------------------------------------------------
# 2. テーブル特定
# ---------------------------------------------------------
print("🔍 データを探しています...")

target_table = None
max_rows = 0
tables = soup.find_all("table")

# 最も行数が多いテーブルを探す
for table in tables:
    rows = table.find_all("tr")
    if len(rows) > max_rows:
        max_rows = len(rows)
        target_table = table

if not target_table or max_rows < 10:
    print("❌ データテーブルが見つかりませんでした。")
    exit()

print(f"  ✅ {max_rows} 行のテーブルを発見。解析を開始します...")

# ---------------------------------------------------------
# 3. データ抽出 (フリースタイル検索)
# ---------------------------------------------------------
data_rows = []
rows = target_table.find_all("tr")

valid_types = ["スピード", "スタミナ", "パワー", "根性", "賢さ", "友人", "グループ"]

for row in rows:
    cells = row.find_all(["td", "th"])
    if not cells: continue

    # --- 行内の全セルをテキスト化してリストにする ---
    row_texts = []
    for cell in cells:
        # 画像(alt)処理
        imgs = cell.find_all("img")
        for img in imgs:
            val = img.get("alt", "") or img.get("title", "")
            if val:
                # 拡張子や _icon などを強力に削除
                val = re.sub(r'(\.png|\.jpg|\.gif|_icon|アイコン)', '', val).strip()
                img.replace_with(f" {val} ")
        
        # 改行処理
        for br in cell.find_all("br"):
            br.replace_with(", ")
            
        text = cell.get_text(separator=" ", strip=True)
        row_texts.append(text)

    # ヘッダー行やデータ不足行をスキップ
    full_text = "".join(row_texts)
    if "名前" in full_text and "レアリティ" in full_text: continue
    if len(row_texts) < 3: continue

    # ==================================================
    # 自動判別ロジック
    # ==================================================
    
    rarity = "R"
    ctype = "不明"
    raw_name = ""
    skill_parts = []
    
    rarity_idx = -1
    type_idx = -1
    name_idx = -1

    # 1. レアリティを探す (SSR, SR, R)
    for i, text in enumerate(row_texts):
        if text in ["SSR", "SR", "R"]:
            rarity = text
            rarity_idx = i
            break
            
    # 2. タイプを探す (スピード, スタミナ...)
    for i, text in enumerate(row_texts):
        # 既にレアリティとして使った列は避ける
        if i == rarity_idx: continue
        
        for t in valid_types:
            if t in text:
                ctype = t
                type_idx = i
                break
        if ctype != "不明": break
        
    # 3. 名前を探す ( [ ] を含む、あるいはレアリティより左にある )
    for i, text in enumerate(row_texts):
        if i == rarity_idx or i == type_idx: continue
        
        # [] を含んでいれば名前の可能性が高い
        if "[" in text or "［" in text:
            raw_name = text
            name_idx = i
            break
            
    # 名前が見つからない場合、レアリティより左にある最初の文字入りセルを採用
    if not raw_name and rarity_idx > 0:
        for i in range(rarity_idx):
            if row_texts[i].strip():
                raw_name = row_texts[i]
                name_idx = i
                break

    # 4. スキルを探す (レアリティ・タイプ・名前以外の列をすべて結合)
    start_idx = max(rarity_idx, type_idx, name_idx)
    # もし特定に失敗していたら、後ろの方の列をスキルとみなす
    if start_idx == -1: start_idx = 2 
    
    for i in range(len(row_texts)):
        if i in [rarity_idx, type_idx, name_idx]: continue
        # 名前より左にある列（画像列など）はスキルではないので無視
        if name_idx != -1 and i < name_idx: continue
        
        if row_texts[i].strip():
            skill_parts.append(row_texts[i])

    # ==================================================
    # データ整形
    # ==================================================

    # --- 名前整形 ---
    card_name = "トレセン学園"
    char_name = raw_name
    match = re.search(r'[\[［](.+?)[\]］](.+)', raw_name)
    if match:
        card_name = match.group(1).strip()
        char_name = match.group(2).strip()
    else:
        match_simple = re.search(r'[\[［](.+?)[\]］]', raw_name)
        if match_simple:
            card_name = match_simple.group(1).strip()
            char_name = raw_name.replace(match_simple.group(0), "").strip()
            
    # 名前が空っぽならスキップ（ゴミ行）
    if not char_name: continue

    # --- スキル整形 ---
    combined_skill = ",".join(skill_parts)
    
    # < > ( ) 削除
    clean_skill = re.sub(r'[<＜].*?[>＞]', '', combined_skill) 
    clean_skill = re.sub(r'[\(（].*?[\)）]', '', clean_skill)
    
    # 記号削除
    clean_skill = clean_skill.replace("※", "").replace("◯", "").replace("◎", "").replace("→", ",")
    clean_skill = re.sub(r'[,，\s　]+', ',', clean_skill)
    
    # 強力ゴミ掃除フィルター
    skill_list = []
    blacklist = ["Lv", "Pt", "ヒント", "None", "nan", "速度", "加速", "回復", "スキル", "編集", "実装日", "画像"]
    
    for s in clean_skill.split(','):
        s = s.strip()
        if len(s) <= 1: continue
        if s in blacklist: continue
        if s == char_name or s == card_name: continue
        if s == f"［{card_name}］{char_name}": continue
        # 画像ファイル名っぽいものは絶対除外
        if "_icon" in s or ".jpg" in s or ".png" in s: continue
        if "トレセン学園" in s: continue

        skill_list.append(s)
    
    final_skills = ",".join(list(dict.fromkeys(skill_list)))

    data_rows.append({
        "レアリティ": rarity,
        "キャラクター名": char_name,
        "カード名": card_name,
        "タイプ": ctype,
        "所持スキル": final_skills
    })

# 保存
df = pd.DataFrame(data_rows)
df = df[["レアリティ", "キャラクター名", "カード名", "タイプ", "所持スキル"]]
df.to_csv(output_file, index=False, encoding='utf-8-sig')

print("-" * 30)
print(f"🎉 成功！ 列ズレに左右されない最強の検索ロジックでCSVを作成しました。")
print(f"抽出件数: {len(df)} 件")