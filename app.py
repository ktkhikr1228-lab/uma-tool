import streamlit as st # type: ignore
import pandas as pd # type: ignore
import os
# ★さっき作ったファイルを読み込む！
import race_data 

st.set_page_config(page_title="Uma-Factor Search", layout="wide")

# ==========================================
# 0. デザイン設定
# ==========================================
st.markdown("""
<style>
.skill-tag {
    display: inline-block;
    padding: 3px 10px;
    margin: 3px;
    border-radius: 5px;
    background-color: #f8f9fa;
    color: #333333;
    border: 1px solid #d1d5db;
    font-weight: 600;
    font-size: 0.9em;
}
.highlight-tag {
    background-color: #fff3cd;
    color: #856404;
    border: 1px solid #ffeeba;
    font-weight: bold;
}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 1. データ読み込み (cards.csv)
# ==========================================
csv_file = 'cards.csv'
if os.path.exists(csv_file):
    df_all_cards = pd.read_csv(csv_file)
    df_all_cards['所持スキル'] = df_all_cards['所持スキル'].fillna("").astype(str)
else:
    st.error(f"エラー: '{csv_file}' が見つかりません。")
    st.stop()

def add_icon_to_type(type_name):
    icons = { "スピード": "👟", "スタミナ": "❤️", "パワー": "💪", "根性": "🔥", "賢さ": "🎓", "友人": "🧢", "グループ": "🧢" }
    for key, icon in icons.items():
        if key in str(type_name): return f"{icon} {type_name}"
    return type_name

# ==========================================
# 2. サイドバー (メニュー)
# ==========================================
st.sidebar.title("🐴 Menu")

# A. 検索モード
search_source = st.sidebar.radio("検索対象", ["手持ち", "全カード"], horizontal=True)
st.sidebar.divider()

# B. フリーワード検索
st.sidebar.subheader("🔍 キーワード検索")
search_keyword = st.sidebar.text_input("スキル/キャラ名", placeholder="例：ハイボルテージ")
st.sidebar.divider()

# C. 手持ち登録 (ここを修正してDeltaGeneratorエラーを解消済)
st.sidebar.subheader("🖐️ 手持ち登録")

tab_labels = ["👟", "❤️", "💪", "🔥", "🎓", "🧢"]
# タブを作成
tabs = st.sidebar.tabs(tab_labels)
filter_keywords = ["スピード", "スタミナ", "パワー", "根性", "賢さ", ["友人", "グループ"]]

selected_cards_all = []

# zipを使ってタブと中身を対応させる
for t_obj, keyword, label in zip(tabs, filter_keywords, tab_labels):
    with t_obj:
        if isinstance(keyword, list):
            mask = df_all_cards['タイプ'].str.contains('|'.join(keyword), na=False)
        else:
            mask = df_all_cards['タイプ'].str.contains(keyword, na=False)
        
        cards = df_all_cards[mask]['サポカ名'].unique()
        # keyをユニークにすることでバグを防ぐ
        sel = st.multiselect(f"{label}枠", cards, key=f"sel_{label}")
        selected_cards_all.extend(sel)

my_inventory = selected_cards_all

if my_inventory:
    st.sidebar.success(f"{len(my_inventory)} 枚 選択中")
else:
    st.sidebar.caption("タブから所持カードを選択")


# ==========================================
# 3. メイン画面
# ==========================================

# 検索対象のリストを決める
target_list = my_inventory if search_source == "手持ち" else df_all_cards['サポカ名'].unique()

if search_keyword:
    # --- フリーワード検索モード ---
    st.header(f"🔍 検索: {search_keyword}")
    results = []
    for name in target_list:
        row = df_all_cards[df_all_cards['サポカ名'] == name].iloc[0]
        skills = row['所持スキル']
        
        if search_keyword in name or search_keyword in skills:
            # ヒットしたスキルをハイライト
            tags = ""
            for s in skills.split(','):
                style = "highlight-tag" if search_keyword in s else ""
                tags += f'<span class="skill-tag {style}">{s}</span>'
            
            results.append({"name": name, "type": row['タイプ'], "tags": tags})

    if results:
        for res in results:
            c1, c2 = st.columns([1, 4])
            c1.markdown(f"**{res['name']}**<br><small>{add_icon_to_type(res['type'])}</small>", unsafe_allow_html=True)
            c2.markdown(res['tags'], unsafe_allow_html=True)
            st.divider()
    else:
        st.warning("見つかりませんでした")

else:
    # --- レース攻略モード ---
    st.header("🏁 12月チャンミ攻略")
    
    # ★ここで別ファイル(race_data.py)からデータを呼び出す！
    # これで app.py がスッキリしました
    criteria = race_data.race_criteria
    
    c1, c2 = st.columns(2)
    race_name = c1.selectbox("レース", list(criteria.keys()))
    strategy = c2.radio("脚質", ["逃げ", "先行", "差し", "追込"], horizontal=True)
    
    # 選んだ条件のスキルリストを取得
    target_skills = criteria[race_name].get(strategy, [])
    
    if target_skills:
        with st.expander(f"📋 必要なスキルリスト ({len(target_skills)}種)", expanded=True):
            st.markdown(" ".join([f'<span class="skill-tag">{s}</span>' for s in target_skills]), unsafe_allow_html=True)
        
        st.subheader("おすすめサポカ")
        
        results = []
        for name in target_list:
            row = df_all_cards[df_all_cards['サポカ名'] == name].iloc[0]
            skills = row['所持スキル']
            
            # マッチング処理
            matched = [t for t in target_skills if t in skills]
            
            if matched:
                tags = ""
                for s in skills.split(','):
                    if s in matched:
                        tags += f'<span class="skill-tag highlight-tag">{s}</span>'
                
                results.append({
                    "name": name,
                    "type": row['タイプ'],
                    "tags": tags,
                    "count": len(matched)
                })
        
        # マッチ数順にソート
        if results:
            results.sort(key=lambda x: x['count'], reverse=True)
            st.success(f"{len(results)} 枚の有効なカードが見つかりました")
            
            for res in results:
                c1, c2 = st.columns([1, 4])
                c1.markdown(f"**{res['name']}**<br><small>{add_icon_to_type(res['type'])}</small>", unsafe_allow_html=True)
                # 適合度バー
                c2.progress(min(res['count'] / 5.0, 1.0), text=f"有効スキル: {res['count']}個")
                c2.markdown(res['tags'], unsafe_allow_html=True)
                st.divider()
        else:
            st.warning("有効なカードが見つかりませんでした。")
    else:
        st.info("この脚質のデータはまだありません。race_data.py に追記してください。")