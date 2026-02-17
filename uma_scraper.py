import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import re
from urllib.parse import urljoin

# --- 設定 ---
TARGET_URL = "https://gamewith.jp/uma-musume/article/show/255035"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

def get_soup(url):
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        response.encoding = response.apparent_encoding
        return BeautifulSoup(response.text, 'html.parser')
    except Exception as e:
        print(f"✗ Network Error: {e}")
        return None

def clean_text(text):
    if not text: return ""
    return text.strip().replace('\n', ' ').replace('\r', '').replace('\t', ' ')

def is_valid_skill_name(text):
    """
    スキル名として妥当かチェック
    """
    if not text or len(text) < 2:
        return False
    
    if len(text) >= 30:
        return False
    
    if text.isdigit():
        return False
    
    # NGワード
    ng_words = [
        '評価', 'の効果', 'ランキング', '一覧', 'まとめ', '攻略',
        'ウマ娘', 'GameWith', 'TOP', 'twitter', 'facebook', 'line',
        '検索', '掲示板', 'デッキ', 'シナリオ', 'ガチャ', 'チェッカー',
        'おすすめ', '報酬', 'ツール', '入手', 'サポート', 'トレーニング',
        '友情', 'ボーナス', 'ヒント発生率', '初期', '効果アップ', 'やる気',
        'レベル', 'サポカ', '編成', '因子', '継承', '固有', '適性',
        '得意練習', 'スキルPt', '短距離', 'マイル', '中距離', '長距離',
        '逃げ', '先行', '差し', '追込'
    ]
    
    for ng in ng_words:
        if ng in text:
            return False
    
    symbol_count = sum(1 for c in text if not c.isalnum() and c not in ['ー', '・', '！', '♪', '◯', '〇'])
    if len(text) > 0 and symbol_count / len(text) > 0.5:
        return False
    
    return True

def extract_skills_from_multiple_sections(soup):
    """
    マルチセクション対応スキル抽出
    
    アルゴリズム:
    1. 全見出し(h2~h4)を取得
    2. 「所持スキル」「育成イベント」「獲得スキル」「イベントで」を含む見出しを全て特定
    3. 各見出しごとに、その下のテーブルからスキルを抽出
    4. 全セクションのスキルを統合し重複を除去
    """
    all_skills = []
    seen_skills = set()
    
    # 1. 全見出しを取得
    all_headers = soup.find_all(['h2', 'h3', 'h4'])
    
    # 2. ターゲット見出しのキーワード
    target_keywords = ["所持スキル", "育成イベント", "獲得スキル", "イベントで", "ヒントスキル"]
    
    # 3. キーワードを含む見出しを全て特定
    target_headers = []
    for header in all_headers:
        header_text = clean_text(header.get_text())
        if any(keyword in header_text for keyword in target_keywords):
            target_headers.append(header)
    
    # デバッグ用: 見つかったセクション数を記録
    section_count = len(target_headers)
    
    # 4. 各ターゲット見出しについて処理
    for header in target_headers:
        section_name = clean_text(header.get_text())
        
        # 見出しの次の兄弟要素から探索開始
        current = header.find_next_sibling()
        checked_elements = 0
        
        while current and checked_elements < 15:  # 最大15要素先まで探索
            # 次の見出しに到達したら終了
            if current.name in ['h2', 'h3', 'h4']:
                break
            
            # tableタグを発見した場合
            if current.name == 'table':
                # テーブル内の全リンクを抽出
                links = current.find_all('a')
                for link in links:
                    skill_text = clean_text(link.get_text())
                    if is_valid_skill_name(skill_text):
                        if skill_text not in seen_skills:
                            seen_skills.add(skill_text)
                            all_skills.append(skill_text)
                
                # テーブル内のテキスト（リンクでないスキル名）も抽出
                cells = current.find_all(['td', 'th'])
                for cell in cells:
                    cell_text = clean_text(cell.get_text())
                    # セル内にリンクがない場合のみテキストを取得
                    if not cell.find('a') and is_valid_skill_name(cell_text):
                        if cell_text not in seen_skills:
                            seen_skills.add(cell_text)
                            all_skills.append(cell_text)
            
            # divの中にtableがある場合
            elif current.name == 'div':
                inner_tables = current.find_all('table', recursive=False)
                for table in inner_tables:
                    links = table.find_all('a')
                    for link in links:
                        skill_text = clean_text(link.get_text())
                        if is_valid_skill_name(skill_text):
                            if skill_text not in seen_skills:
                                seen_skills.add(skill_text)
                                all_skills.append(skill_text)
                    
                    cells = table.find_all(['td', 'th'])
                    for cell in cells:
                        cell_text = clean_text(cell.get_text())
                        if not cell.find('a') and is_valid_skill_name(cell_text):
                            if cell_text not in seen_skills:
                                seen_skills.add(cell_text)
                                all_skills.append(cell_text)
            
            current = current.find_next_sibling()
            checked_elements += 1
    
    return all_skills, section_count

def scrape_card_details(soup, url):
    """
    詳細ページ解析 - マルチセクション対応版
    """
    # タイトル取得
    h1 = soup.find('h1')
    page_title = clean_text(h1.get_text()) if h1 else ""
    
    # --- 1. ゴミページの徹底排除 ---
    strict_ng_words = [
        "一覧", "ランキング", "まとめ", "最強", "チェッカー", "掲示板",
        "評価点", "ツール", "報酬", "攻略", "検索", "比較", "タイプ",
        "SRサポート", "Rサポート", "SSRサポート", "おすすめ", "入手方法"
    ]
    
    for ng in strict_ng_words:
        if ng in page_title:
            if "評価" not in page_title or ng in ["タイプ", "SRサポート", "Rサポート", "SSRサポート"]:
                return None, f"NG Title: {page_title}"
    
    # --- 2. 基本情報抽出 ---
    rarity = "Unknown"
    if "SSR" in page_title:
        rarity = "SSR"
    elif "SR" in page_title:
        rarity = "SR"
    elif "R" in page_title:
        rarity = "R"
    
    # キャラ名抽出
    temp_name = page_title.replace("【ウマ娘】", "").split("の評価")[0].split("(")[0]
    char_name = re.sub(r'[（(].+?[）)]', '', temp_name).strip()
    
    if not char_name or len(char_name) < 2:
        char_name = temp_name
    
    for ng in strict_ng_words:
        if ng in char_name:
            return None, f"NG CharName: {char_name}"
    
    # --- 3. タイプ判定 ---
    card_type = "Unknown"
    type_keywords = ['スピード', 'スタミナ', 'パワー', '根性', '賢さ', '友人', 'グループ']
    
    # A. 画像alt属性
    for t in type_keywords:
        img = soup.find('img', alt=t) or soup.find('img', alt=re.compile(f"^{t}"))
        if img:
            card_type = t
            break
    
    # B. テーブル内テキスト
    if card_type == "Unknown":
        tables = soup.find_all('table')
        for table in tables:
            table_text = table.get_text()
            if "得意練習" in table_text or "タイプ" in table_text:
                for t in type_keywords:
                    if t in table_text:
                        card_type = t
                        break
                if card_type != "Unknown":
                    break
    
    # --- 4. スキル抽出（マルチセクション対応） ---
    skills, section_count = extract_skills_from_multiple_sections(soup)
    
    return {
        "rarity": rarity,
        "character_name": char_name,
        "type": card_type,
        "skills": " | ".join(skills) if skills else "",
        "section_count": section_count,  # デバッグ用
        "url": url
    }, page_title

def main():
    print("=" * 80)
    print("ウマ娘サポートカードスクレイピング（マルチセクション対応版）")
    print("=" * 80)
    
    soup = get_soup(TARGET_URL)
    if not soup:
        print("✗ 一覧ページの取得に失敗しました")
        return
    
    # --- Phase 1: URL収集 ---
    print("\n[Phase 1] URL収集中...")
    main_area = soup.find('div', class_='js-article-body')
    if not main_area:
        main_area = soup.find('div', class_='w-article-body')
    if not main_area:
        main_area = soup
    
    raw_links = main_area.find_all('a')
    unique_urls = []
    seen = set()
    
    initial_ng = [
        "line.me", "twitter.com", "facebook.com", "一覧", "ランキング",
        "まとめ", "最強", "チェッカー", "掲示板", "評価点", "ツール",
        "報酬", "攻略", "検索", "比較", "コメント", "投票", "おすすめ"
    ]
    
    for link in raw_links:
        href = link.get('href')
        text = clean_text(link.get_text())
        
        if href and "article/show" in href and re.search(r'\d+$', href):
            if any(ng in text for ng in initial_ng):
                continue
            
            full_url = urljoin(TARGET_URL, href)
            
            if full_url not in seen:
                seen.add(full_url)
                unique_urls.append({'url': full_url, 'text': text})
    
    print(f"✓ {len(unique_urls)}件のURLを収集しました")
    
    # --- Phase 2: 詳細ページ巡回 ---
    print("\n[Phase 2] 詳細ページ巡回中...")
    print("-" * 80)
    
    card_database = []
    skip_count = 0
    error_count = 0
    
    for i, item in enumerate(unique_urls):
        url = item['url']
        display_text = item['text'][:40] + "..." if len(item['text']) > 40 else item['text']
        print(f"[{i+1}/{len(unique_urls)}] {display_text}", end=" ", flush=True)
        
        try:
            detail_soup = get_soup(url)
            if detail_soup:
                data, msg = scrape_card_details(detail_soup, url)
                
                if data:
                    if data['character_name'] in ["SSRサポートカード", "SRサポートカード", "LINE", "Unknown"]:
                        print("⊗ 無効")
                        skip_count += 1
                    else:
                        skill_count = len(data['skills'].split('|')) if data['skills'] else 0
                        section_count = data.get('section_count', 0)
                        print(f"✓ {data['rarity']} {data['type']} / {skill_count}スキル ({section_count}セクション)")
                        
                        # section_countは保存しない（デバッグ用）
                        data_to_save = {k: v for k, v in data.items() if k != 'section_count'}
                        card_database.append(data_to_save)
                else:
                    print("⊗ スキップ")
                    skip_count += 1
            else:
                print("✗ エラー")
                error_count += 1
        except Exception as e:
            print(f"✗ {str(e)[:30]}")
            error_count += 1
        
        time.sleep(1.0)
    
    # --- Phase 3: CSV出力 ---
    print("\n" + "=" * 80)
    print("[Phase 3] データ出力")
    print("=" * 80)
    
    if card_database:
        df = pd.DataFrame(card_database)
        
        df = df[~((df['type'] == 'Unknown') & (df['skills'] == ''))]
        df = df[~df['character_name'].str.contains(
            "一覧|ランキング|まとめ|LINE|タイプ|SRサポート|Rサポート|SSRサポート",
            regex=True, na=False
        )]
        
        df = df.drop_duplicates(subset=['character_name', 'rarity'], keep='first')
        
        output_file = "umamusume_cards.csv"
        df.to_csv(output_file, index=False, encoding='utf-8-sig')
        
        print(f"✓ {len(df)}枚のサポートカードデータを保存しました")
        print(f"✓ ファイル名: {output_file}")
        
        print("\n【統計情報】")
        print(f"  総処理数: {len(unique_urls)}")
        print(f"  取得成功: {len(card_database)}")
        print(f"  スキップ: {skip_count}")
        print(f"  エラー: {error_count}")
        print(f"  最終保存: {len(df)}枚")
        
        if len(df) > 0:
            print(f"\n  レアリティ別:")
            for rarity, count in df['rarity'].value_counts().items():
                print(f"    {rarity}: {count}枚")
            
            print(f"\n  タイプ別:")
            for card_type, count in df['type'].value_counts().items():
                print(f"    {card_type}: {count}枚")
            
            # スキル数の統計
            df['skill_count'] = df['skills'].apply(lambda x: len(x.split('|')) if x else 0)
            print(f"\n  スキル数統計:")
            print(f"    平均: {df['skill_count'].mean():.1f}個")
            print(f"    最小: {df['skill_count'].min()}個")
            print(f"    最大: {df['skill_count'].max()}個")
    else:
        print("✗ 有効なデータが取得できませんでした")
    
    print("=" * 80)
    print("処理完了")
    print("=" * 80)

if __name__ == "__main__":
    main()