from playwright.sync_api import sync_playwright
import bs4
from bs4 import BeautifulSoup
import json
import re
from pathlib import Path
import time

def smart_gametora_crawler(list_url: str, output_file: str = "cards.json", cache_file: str = "gametora_cache.json"):
    print("🚀 GameToraの最強データベースを解析するんだよ！")
    
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

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        page = context.new_page()
        
        try:
            print("📚 GameToraのサポカ一覧にアクセス中...")
            page.goto(list_url, wait_until="domcontentloaded", timeout=60000)
            
            page.wait_for_selector("a[href*='/supports/']", timeout=15000)
            page.wait_for_timeout(2000) 
            
            list_html = page.content()
            soup = BeautifulSoup(list_html, "html.parser")
            
            card_links = []
            for a in soup.find_all("a", href=True):
                href = a["href"]
                # 🚨 【最強ロジック】URLの揺らぎを完全に吸収するRegex！
                # hrefの中に「/supports/数字」があれば、その数字（ID）を抜き出すんだよ！
                match = re.search(r'/supports/(\d+)', href)
                if match:
                    card_id = match.group(1)
                    # 抜き出したIDを使って、絶対に正しい絶対URLを再構築するでしょ！
                    url = f"https://gametora.com/ja/umamusume/supports/{card_id}"
                    if url not in visited_urls and url not in card_links:
                        card_links.append(url)
                        
            print(f"🎯 新しくチェックするサポカ候補が {len(card_links)} 件見つかったんだよ！")
            
            MAX_PAGES_PER_RUN = 30
            target_links = card_links[:MAX_PAGES_PER_RUN]
            
            if len(card_links) > MAX_PAGES_PER_RUN:
                print(f"⚠️ 今回は最初の {MAX_PAGES_PER_RUN} 件だけを処理するでしょ！残りは再度実行してね！")
                
            added_count = 0
            updated_count = 0
            
            for idx, url in enumerate(target_links):
                print(f"[{idx+1}/{len(target_links)}] アクセス中: {url}", end="")
                
                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=30000)
                    
                    page.wait_for_selector("h1", timeout=15000)
                    page.wait_for_timeout(1000)
                    
                    detail_html = page.content()
                    detail_soup = BeautifulSoup(detail_html, "html.parser")
                    
                    h1_tag = detail_soup.find("h1")
                    full_name = h1_tag.get_text(strip=True) if h1_tag else "Unknown"
                    
                    if full_name != "Unknown":
                        full_name = re.sub(r'^(SSR|SR|R)\s+', '', full_name)
                        full_name = full_name.replace('[', '［').replace(']', '］')
                        
                    title_text = detail_soup.title.get_text() if detail_soup.title else ""
                    card_type = "Unknown"
                    for t in ["スピード", "スタミナ", "パワー", "根性", "賢さ", "友人", "グループ"]:
                        if t in title_text or t in full_name:
                            card_type = t
                            break
                    
                    if card_type == "Unknown":
                        body_text = detail_soup.get_text()
                        for t in ["スピード", "スタミナ", "パワー", "根性", "賢さ", "友人", "グループ"]:
                            if f"{t}サポート" in body_text or f"得意練習{t}" in body_text:
                                card_type = t
                                break
                            
                    skills = set()
                    for a in detail_soup.find_all("a", href=True):
                        # スキルの抽出も、/ja/の有無を無視するロジックに変更したんだよ！
                        if "/skills/" in a["href"]:
                            skill_name = a.get_text(strip=True)
                            clean_name = skill_name.replace('◯', '○').replace('〇', '○').replace('O', '○').replace('0', '○')
                            if len(clean_name) > 1:
                                skills.add(clean_name)
                                
                    if full_name != "Unknown" and len(skills) > 0:
                        if full_name in existing_dict:
                            old_skills = set(existing_dict[full_name].get("skills", []))
                            new_skills = skills
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
                        
                        visited_urls.add(url)
                    else:
                        print(f" ➔ ⚠️ スキップ: H1は見つかったけどスキルが無いんだよ… ({full_name})")
                        
                except Exception as inner_e:
                    print(f" ➔ 🚨 エラーでスキップ: ページの読み込みが間に合わなかったんだよ…")
                
                with open(json_path, "w", encoding="utf-8") as f:
                    json.dump(list(existing_dict.values()), f, ensure_ascii=False, indent=2)
                with open(cache_path, "w", encoding="utf-8") as f:
                    json.dump(list(visited_urls), f, ensure_ascii=False, indent=2)

            print(f"\n大成功なんだよ！新規追加: {added_count} 枚, スキル更新: {updated_count} 枚")

        except Exception as e:
            print(f"\nエラーが発生したんだよ…: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    target_url = "https://gametora.com/ja/umamusume/supports"
    smart_gametora_crawler(target_url)