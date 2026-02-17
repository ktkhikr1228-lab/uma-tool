import pandas as pd # type: ignore
import re
import os
import io
import json

# ==========================================
# 【最終完全版】全サポカDB作成ツール
# スキルの取りこぼしを許さない「全列スキャン」モード
# ==========================================

input_file = 'raw_data.txt'
output_file = 'cards.json'

print(f"Reading '{input_file}'...")

if not os.path.exists(input_file):
    print(f"Error: '{input_file}' not found.")
    exit()

try:
    # 1. 改行結合処理（バラバラになった行をくっつける）
    with open(input_file, 'r', encoding='utf-8') as f:
        raw_lines = f.readlines()

    merged_lines = []
    current_line = ""

    for index, line in enumerate(raw_lines):
        line = line.strip('\n')
        if not line: continue

        # タブの数で新しい行か判断
        # Wikiの行は [画像] [名前] [レア] [タイプ] ... と最低3つはタブがある
        # または、行頭に [ ] がある場合は新しい行とみなす
        tab_count = line.count('\t')
        has_bracket = "[" in line or "［" in line
        
        is_new_row = False
        if tab_count >= 3:
            is_new_row = True
        elif tab_count >= 1 and has_bracket:
            is_new_row = True

        if is_new_row:
            if current_line:
                merged_lines.append(current_line)
            current_line = line
        else:
            current_line += "," + line # 改行をカンマに変換して結合

    if current_line:
        merged_lines.append(current_line)

    # Filter out lines that don't look like table rows (headers or data)
    # This removes the "フィルタ機能を有効にする" line which confuses pd.read_csv
    merged_lines = [line for line in merged_lines if line.count('\t') >= 3]

    # 2. DataFrame化
    csv_io = io.StringIO("\n".join(merged_lines))
    df = pd.read_csv(csv_io, sep='\t', header=None, on_bad_lines='skip')

    # 3. 列の特定

    col_name_idx = -1
    col_type_idx = -1
    
    # 全列スキャン用の開始位置
    skill_start_idx = -1

    if len(df) > 0:
        first_row = df.iloc[0]
        for i, val in enumerate(first_row):
            val_str = str(val)
            if ("[" in val_str or "［" in val_str) and len(val_str) > 2:
                col_name_idx = i
            elif val_str in ["スピード", "スタミナ", "パワー", "根性", "賢さ", "友人", "グループ"]:
                col_type_idx = i
    
    # 強制指定
    if col_name_idx == -1: col_name_idx = 1
    if col_type_idx == -1: col_type_idx = 3
    
    # 名前とタイプより後ろの列は、すべて「スキル候補」として扱います
    skill_start_idx = max(col_name_idx, col_type_idx) + 1

    # 4. データ抽出
    new_data = []
    
    for index, row in df.iterrows():
        if col_name_idx >= len(row): continue
        raw_name = str(row[col_name_idx]).strip()
        
        # ゴミ行スキップ
        if raw_name in ["名前", "nan", "", "None"] or re.match(r'^\d{4}\.', raw_name): continue
        if "<" in raw_name and ">" in raw_name: continue 

        # タイプ
        ctype = "不明"
        if col_type_idx < len(row):
            val = str(row[col_type_idx])
            if val != "nan": ctype = val.strip()

        # ★ここが強化ポイント：すべての列からスキルをかき集める
        skill_text = ""
        for i in range(skill_start_idx, len(row)):
            val = str(row[i])
            # 日付、編集、nan 以外はすべて結合！
            if val != "nan" and not re.match(r'20\d\d\.', val) and "編集" not in val:
                skill_text += val + ","

        # クリーニング
        text = re.sub(r'<[^>]+>', '', skill_text) # タグ削除
        text = text.replace("→", ",").replace("nan", "").replace("　", ",")
        text = re.sub(r'[\s\n]+', ',', text) # 改行削除
        
        s_list = [s.strip() for s in text.split(',') if len(s.strip()) > 1]
        
        ignore_words = ["SSR", "SR", "R", "配布", "報酬", "評価", "能力", "イベント", "取得", "条件", "編集"]
        clean_list = []
        for s in s_list:
            if (s not in ignore_words and 
                not s.isdigit() and 
                not re.match(r'20\d\d\.', s) and
                s != raw_name):
                clean_list.append(s)

        final_skills = list(set(clean_list))

        new_data.append({
            "name": raw_name,
            "type": ctype,
            "skills": final_skills
        })

    # 保存
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(new_data, f, ensure_ascii=False, indent=4)
        
    print(f"Done! Updated dictionary ({output_file}).")
    print(f"登録枚数: {len(new_data)} 枚")

except Exception as e:
    print(f"Error: {e}")
