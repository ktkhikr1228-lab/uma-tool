from playwright.sync_api import sync_playwright
import bs4
from bs4 import BeautifulSoup
import json
import time
import re
from pathlib import Path

def clean_garbage_skills(existing_dict):
    """過去の実行で cards.json に混入してしまったゴミデータを自動で除菌するんだよ！"""
    bad_keywords = [
        "交換", "コミカライズ", "上げる", "上げ方", "有馬記念", "コメントを読む", 
        "やり方", "効果", "序盤", "使い道", "ループ", "グッズ", "シリアルコード", 
        "確率", "フィギュア", "影響", "解説", "勝負服", "診断", "解放条件", "基礎能力", 
        "原因", "対策", "楽曲", "検証", "タイミング", "厳選", "連携", "上限解放", 
        "入手方法", "試験", "研究", "アイテム", "ステータス", "出演", "稼ぎ方", 
        "デッキ", "組み合わせ", "種類", "のアイコン", "使い方", "メリット", "適性",
        "星1", "星2", "星3", "通常Ver", "新衣装Ver", "▶", "リセマラ", "一覧"
    ]
    bad_exact = ["スタミナ", "スピード", "パワー", "根性", "賢さ", "友人", "グループ", "アニメ"]
    
    cleaned_count = 0
    for name, data in existing_dict.items():
        old_skills = data.get("skills", [])
        new_skills = []
        for s in old_skills:
            if s in bad_exact:
                continue
            if any(bad in s for bad in bad_keywords):
                continue
            new_skills.append(s)
            
        if len(old_skills) != len(new_skills):
            data["skills"] = new_skills
            cleaned_count += 1
            
    if cleaned_count > 0:
        print(f"🧹 自動クリーンアップ完了！汚染されていた {cleaned_count} 枚のサポカからゴミデータを消去したんだよ！")
    return existing_dict

def parse_gamewith_skills(soup: BeautifulSoup) -> list[str]:
    skills = set()
    
    for table in soup.find_all("table"):
        table_text = table.get_text()
        
        # 🚨 フッターやサイドバーの巨大リンク表を完全にシャットアウト！
        if "最新コメントを読む" in table_text or "リセマラランキング" in table_text or "交換アイテム" in table_text or "出演情報" in table_text:
            continue
            
        # スキルやイベントの表である可能性が高いものだけを処理
        if "スキル" in table_text or "イベント" in table_text or "ヒント" in table_text or "発動" in table_text:
            for a in table.find_all("a", href=True):
                if "/article/show/" in a["href"]:
                    skill_name = a.get_text(strip=True)
                    
                    invalid_exact = [
                        "スタミナ", "スピード", "パワー", "根性", "賢さ", "友人", "グループ", 
                        "星1", "星2", "星3", "通常Ver", "新衣装Ver", "距離適性", "バ場適性", "脚質適性",
                        "詳細を見る", "隠しイベント", "プロフィール", "逃げ", "先行", "差し", "追込",
                        "短距離", "マイル", "中距離", "長距離", "ダート", "アニメ"
                    ]
                    
                    invalid_partial = [
                        "一覧", "評価", "ガチャ", "まとめ", "▶", "ランキング", "シミュ", 
                        "チェッカー", "クイズ", "攻略", "掲示板", "ログイン", "リセマラ", 
                        "のアイコン", "ウマ娘", "おすすめ", "キャンペーン", "コメント"
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
    return list(skills)

def smart_gamewith_crawler(list_url: str, output_file: str = "cards.json", cache_file: str = "gamewith_cache.json"):
    print("🚀 Playwrightを起動してGameWithの最新メタを調査するんだよ！")
    
    visited_urls = set()
    cache_path = Path(cache_file)
    if cache_path.exists():
        with open(cache_path, "r", encoding="utf-8") as f:
            visited_urls = set(json.load(f))
            
    json_path = Path(output_file)
    existing_cards = []
    if json_path.exists():
        with open(json_path, "r", encoding="utf-8") as f:
            try:
                existing_cards = json.load(f)
            except json.JSONDecodeError:
                pass
                
    existing_dict = {c["name"]: c for c in existing_cards}
    # 実行直後にゴミデータを全自動で除菌するんだよ！
    existing_dict = clean_garbage_skills(existing_dict)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        context = browser.new_context(user_agent=user_agent)
        page = context.new_page()
        
        try:
            print("📚 サポカ一覧ページを解析中...")
            page.goto(list_url, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_selector("table", timeout=15000)
            list_html = page.content()
            
            soup = BeautifulSoup(list_html, "html.parser")
            card_links = []
            
            for table in soup.find_all("table"):
                if "レア" in table.get_text() and "タイプ" in table.get_text():
                    for a in table.find_all("a", href=True):
                        if "/article/show/" in a["href"]:
                            url = "https://gamewith.jp" + a["href"] if a["href"].startswith("/") else a["href"]
                            if url not in visited_urls and url not in card_links:
                                card_links.append(url)
                                
            print(f"🎯 新しくチェックするサポカ候補が {len(card_links)} 件見つかったんだよ！")
            
            MAX_PAGES_PER_RUN = 30
            target_links = card_links[:MAX_PAGES_PER_RUN]
            
            if len(card_links) > MAX_PAGES_PER_RUN:
                print(f"⚠️ 今回は安全のために最初の {MAX_PAGES_PER_RUN} 件だけを処理するでしょ！残りは再度実行してね！")
                
            added_count = 0
            updated_count = 0
            
            for idx, url in enumerate(target_links):
                print(f"[{idx+1}/{len(target_links)}] アクセス中: {url}", end="")
                
                try:
                    time.sleep(3.0) 
                    page.goto(url, wait_until="domcontentloaded", timeout=30000)
                    
                    detail_html = page.content()
                    detail_soup = BeautifulSoup(detail_html, "html.parser")
                    title_text = detail_soup.title.get_text() if detail_soup.title else ""
                    
                    if not any(r in title_text for r in ["(SSR", "(SR", "(R"]):
                        print(" ➔ ⚠️ スキップ: 育成ウマ娘などサポカ以外のページなんだよ！")
                        visited_urls.add(url)
                        continue

                    base_name = None
                    h1_tag = detail_soup.find("h1")
                    if h1_tag:
                        h1_text = h1_tag.get_text(strip=True).replace('【ウマ娘】', '')
                        m = re.search(r'(.+?)[(（]', h1_text)
                        if m:
                            base_name = m.group(1).strip()
                            
                    if not base_name:
                        print(" ➔ ⚠️ スキップ: 名前が抽出できない構造なんだよ…")
                        visited_urls.add(url)
                        continue

                    crown_name = ""
                    for th in detail_soup.find_all(["th", "td"]):
                        if "二つ名" in th.get_text():
                            td = th.find_next_sibling("td")
                            if td:
                                crown_name = td.get_text(strip=True)
                                break
                                
                    full_name = f"［{crown_name}］{base_name}" if crown_name else base_name
                    full_name = full_name.replace('[', '［').replace(']', '］')
                    
                    card_type = "Unknown"
                    for t in ["スピード", "スタミナ", "パワー", "根性", "賢さ", "友人", "グループ"]:
                        if t in title_text:
                            card_type = t
                            break

                    skills = parse_gamewith_skills(detail_soup)
                    
                    if len(skills) > 0:
                        if full_name in existing_dict:
                            old_skills = set(existing_dict[full_name].get("skills", []))
                            new_skills = set(skills)
                            merged = list(old_skills | new_skills)
                            if len(merged) > len(old_skills) or existing_dict[full_name].get("type") != card_type:
                                existing_dict[full_name]["skills"] = merged
                                existing_dict[full_name]["type"] = card_type
                                updated_count += 1
                                print(f" ➔ ✨ 更新: {full_name} (スキル {len(old_skills)} -> {len(merged)}個)")
                            else:
                                print(f" ➔ ✅ 確認済: {full_name}")
                        else:
                            existing_dict[full_name] = {"name": full_name, "type": card_type, "skills": list(skills)}
                            added_count += 1
                            print(f" ➔ 🆕 追加: {full_name} ({card_type})")
                    else:
                        print(f" ➔ ⚠️ スキップ: スキルが見つからないんだよ… ({full_name})")
                    
                    visited_urls.add(url)
                    
                    with open(json_path, "w", encoding="utf-8") as f:
                        json.dump(list(existing_dict.values()), f, ensure_ascii=False, indent=2)
                    with open(cache_path, "w", encoding="utf-8") as f:
                        json.dump(list(visited_urls), f, ensure_ascii=False, indent=2)
                        
                except Exception as inner_e:
                    print(f" ➔ 🚨 タイムアウトでスキップ: ページの応答がなかったんだよ…")
                    
            print(f"\n大成功なんだよ！新規追加: {added_count} 枚, スキル更新: {updated_count} 枚")

        except Exception as e:
            print(f"\n一覧ページの取得でエラーが発生したんだよ…: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    target_url = "https://gamewith.jp/uma-musume/article/show/255035"
    smart_gamewith_crawler(target_url)