from playwright.sync_api import sync_playwright
import bs4
from bs4 import BeautifulSoup
import json
import re
from pathlib import Path
import sys

def parse_skills(raw_text: str) -> list[str]:
    """
    Wiki特有の文字列ノイズをクリーニングして、純粋なスキル名のリストを抽出するんだよ！
    """
    if not raw_text or raw_text.strip() == "" or raw_text.strip() == "なし":
        return []
        
    # 誤認識しやすい文字の補正 (○に統一)
    text = raw_text.replace('◯', '○').replace('〇', '○').replace('O', '○').replace('0', '○')
    
    # <マ> や <逃> などの脚質・距離条件のタグを削除
    text = re.sub(r'<[^>]+>', ' ', text)
    
    # 「→」で繋がっている進化先・上位スキルを分割して両方取得
    text = text.replace('→', ' ')
    
    # 空白や改行で分割してリスト化
    skills = re.split(r'\s+', text.strip())
    
    # ゴミデータを弾く
    return [s for s in skills if len(s) > 1]

def update_cards_from_wikiru_automated(target_url: str, output_file_path: str = "cards.json") -> None:
    print("Playwrightを起動してWikiruにアクセスするんだよ…！")
    
    html_content = ""
    
    # PlaywrightによるHeadless Browserの起動
    with sync_playwright() as p:
        # headless=True で画面を表示せずにバックグラウンドで処理するんだよ
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        try:
            # ネットワーク通信が落ち着く(networkidle)まで待機することで、JSの実行完了を担保するんだよ！
            page.goto(target_url, wait_until="networkidle", timeout=60000)
            
            # テーブル要素が確実にDOMに描画されるまで最大10秒待機
            page.wait_for_selector("table", timeout=10000)
            
            # 完成したHTMLを抽出
            html_content = page.content()
            print("ページの読み込みとレンダリングが完了したんだよ！")
            
        except Exception as e:
            print(f"エラー: ページの取得に失敗したんだよ…: {e}")
            browser.close()
            sys.exit(1)
            
        finally:
            browser.close()

    print("HTMLの解析を始めるんだよ！")
    parsed_html = BeautifulSoup(html_content, "html.parser")
        
    target_table = None
    for tbl in parsed_html.find_all("table"):
        header_texts = [th.get_text(strip=True) for th in tbl.find_all("th")]
        if "画像" in header_texts and "名前" in header_texts and "所持スキル" in header_texts:
            target_table = tbl
            break
            
    if not target_table:
        print("目的のテーブルが見つからないんだよ…DOM構造が変わったか、WAFにブロックされた可能性があるでしょ（要追加調査）。")
        return

    extracted_cards = []
    table_rows = target_table.find_all("tr")
    
    for row in table_rows:
        cells = row.find_all(["td", "th"])
        
        if len(cells) < 7 or "名前" in cells[1].get_text(strip=True):
            continue
            
        card_name = cells[1].get_text(strip=True)
        card_rarity = cells[2].get_text(strip=True)
        card_type = cells[3].get_text(strip=True)
        
        if card_rarity not in ["SSR", "SR", "R"]:
            continue
            
        skill_text_owned = cells[4].get_text(separator=" ").strip()
        skill_text_event = cells[5].get_text(separator=" ").strip()
        
        skills_owned_list = parse_skills(skill_text_owned)
        skills_event_list = parse_skills(skill_text_event)
        
        unique_all_skills = list(set(skills_owned_list + skills_event_list))
        
        extracted_cards.append({
            "name": card_name,
            "type": card_type,
            "skills": unique_all_skills
        })

    # JSONとのマージ処理
    json_path_object = Path(output_file_path)
    existing_cards_list = []
    
    if json_path_object.exists():
        with open(json_path_object, "r", encoding="utf-8") as file_handler:
            try:
                existing_cards_list = json.load(file_handler)
            except json.JSONDecodeError:
                print("既存のJSONが壊れているから、新規作成として扱うんだよ！")
                
    existing_cards_dictionary = {c["name"]: c for c in existing_cards_list}
    
    count_added = 0
    count_updated = 0
    
    for new_card in extracted_cards:
        if new_card["name"] in existing_cards_dictionary:
            old_skills_set = set(existing_cards_dictionary[new_card["name"]].get("skills", []))
            new_skills_set = set(new_card["skills"])
            merged_skills_list = list(old_skills_set | new_skills_set)
            
            if len(merged_skills_list) > len(old_skills_set) or existing_cards_dictionary[new_card["name"]].get("type") != new_card["type"]:
                existing_cards_dictionary[new_card["name"]]["skills"] = merged_skills_list
                existing_cards_dictionary[new_card["name"]]["type"] = new_card["type"]
                count_updated += 1
        else:
            existing_cards_dictionary[new_card["name"]] = new_card
            count_added += 1
            
    final_cards_list = list(existing_cards_dictionary.values())
    
    with open(json_path_object, "w", encoding="utf-8") as file_handler:
        json.dump(final_cards_list, file_handler, ensure_ascii=False, indent=2)
        
    print(f"大成功なんだよ！新規追加: {count_added} 枚, スキル更新: {count_updated} 枚")
    print(f"最新のデータを {output_file_path} に保存したでしょ！")

if __name__ == "__main__":
    url = "https://umamusume.wikiru.jp/index.php?%E3%83%86%E3%83%BC%E3%83%96%E3%83%AB/%E3%82%B5%E3%83%9D%E3%83%BC%E3%83%88%E3%82%AB%E3%83%BC%E3%83%89%E4%B8%80%E8%A6%A7"
    update_cards_from_wikiru_automated(url)