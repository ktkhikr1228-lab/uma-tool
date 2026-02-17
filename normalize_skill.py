import csv
import json
import re

def normalize_skill(s):
    if s is None: return ""
    s = s.strip()
    # 全角スペース→半角、全角英数→半角などを簡易的に正規化
    s = s.replace('\u3000', ' ')
    s = re.sub(r'\s+', ' ', s)
    return s

out = []
with open('cards.csv', newline='', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        skills_raw = row.get('所持スキル','')
        # カンマ区切りで分割（必要なら他の区切りも追加）
        skills = [normalize_skill(s) for s in re.split(r'\s*,\s*', skills_raw) if s.strip()]
        # 重複削除（順序維持）
        seen = set(); skills_unique = []
        for s in skills:
            if s not in seen:
                seen.add(s); skills_unique.append(s)
        out.append({
            "name": row.get('サポカ名',''),
            "type": row.get('タイプ',''),
            "skills": skills_unique
        })

with open('cards.json', 'w', encoding='utf-8') as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
