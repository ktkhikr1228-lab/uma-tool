import bs4
from bs4 import BeautifulSoup
import re

def test_skill_extraction(html_file):
    print(f"🔍 {html_file} の中身をデバッグ解析するんだよ！\n")
    
    with open(html_file, "r", encoding="utf-8", errors="ignore") as f:
        soup = BeautifulSoup(f, "html.parser")
        
    skills = set()
    
    # テーブル縛りをなくして、ページ内の「/article/show/」を含む全リンクを調査！
    for a in soup.find_all("a", href=True):
        if "/article/show/" in a["href"]:
            skill_name = a.get_text(strip=True)
            
            # ゴミデータ除外フィルター
            invalid_exact = [
                "スタミナ", "スピード", "パワー", "根性", "賢さ", "友人", "グループ", 
                "星1", "星2", "星3", "通常Ver", "新衣装Ver", "距離適性", "バ場適性", "脚質適性",
                "詳細を見る", "隠しイベント", "プロフィール", "逃げ", "先行", "差し", "追込",
                "短距離", "マイル", "中距離", "長距離", "ダート", "アニメ", "サポート"
            ]
            invalid_partial = [
                "一覧", "評価", "ガチャ", "まとめ", "▶", "ランキング", "シミュ", 
                "チェッカー", "クイズ", "攻略", "掲示板", "ログイン", "リセマラ", 
                "のアイコン", "おすすめ", "キャンペーン", "コメント", "SSR", "SR", "R"
            ]
            
            if 1 < len(skill_name) < 25:
                if skill_name in invalid_exact:
                    continue
                if any(inv in skill_name for inv in invalid_partial):
                    continue
                    
                clean_name = skill_name.replace('◯', '○').replace('〇', '○').replace('O', '○').replace('0', '○')
                clean_name = re.sub(r'[<＜].*?[>＞]', '', clean_name).strip()
                if clean_name:
                    skills.add(clean_name)
                    
    print("✨ 【抽出されたスキル一覧】 ✨")
    if not skills:
        print("0件なんだよ…DOM構造が完全に変わっているでしょ！")
    else:
        for s in skills:
            print(f"・ {s}")

if __name__ == "__main__":
    test_skill_extraction("test.html")