# ファイル名: app_json.py

import streamlit as st # type: ignore
from data_loader import load_cards_json
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
# 1. cards.json 読み込み
# ==========================================
try:
    cards = load_cards_json("cards.json")
except Exception as e:
    st.error(f"cards.json の読み込みに失敗しました: {e}")
    st.stop()


# 種類→アイコン変換
def add_icon_to_type(type_name):
    icons = {
        "スピード": "👟", "スタミナ": "❤️", "パワー": "💪",
        "根性": "🔥", "賢さ": "🎓", "友人": "🧢", "グループ": "🧢"
    }
    for key, icon in icons.items():
        if key in str(type_name):
            return f"{icon} {type_name}"
    return type_name


# ==========================================
# 2. サイドバー
# ==========================================
st.sidebar.title("🐴 Menu")

search_source = st.sidebar.radio("検索対象", ["手持ち", "全カード"], horizontal=True)
st.sidebar.divider()

st.sidebar.subheader("🔍 キーワード検索")
search_keyword = st.sidebar.text_input("スキル/キャラ名", placeholder="例：ハイボルテージ")
st.sidebar.divider()

# 手持ち登録
st.sidebar.subheader("🖐️ 手持ち登録")

types = ["スピード", "スタミナ", "パワー", "根性", "賢さ", "友人", "グループ"]
tab_labels = ["👟", "❤️", "💪", "🔥", "🎓", "🧢(友)", "🧢(グ)"]

tabs = st.sidebar.tabs(tab_labels)
selected_cards = []

for t_obj, type_name, label in zip(tabs, types, tab_labels):
    with t_obj:
        filtered = [c["name"] for c in cards if type_name in c["type"]]
        sel = st.multiselect(f"{label}枠", filtered, key=f"sel_{label}")
        selected_cards.extend(sel)

my_inventory = selected_cards

if my_inventory:
    st.sidebar.success(f"{len(my_inventory)} 枚 選択中")
else:
    st.sidebar.caption("タブから所持カードを選択")


# ==========================================
# 3. メイン画面（検索 or レース攻略）
# ==========================================

if search_keyword:
    # =============================
    # 🔍 フリーワード検索
    # =============================
    st.header(f"🔍 検索: {search_keyword}")

    targets = cards if search_source == "全カード" else [
        c for c in cards if c["name"] in my_inventory
    ]

    hits = []
    for card in targets:
        if search_keyword in card["name"] or any(search_keyword in s for s in card["skills"]):
            hits.append(card)

    if hits:
        for card in hits:
            c1, c2 = st.columns([1, 4])
            c1.markdown(
                f"**{card['name']}**<br><small>{add_icon_to_type(card['type'])}</small>",
                unsafe_allow_html=True
            )

            tags = ""
            for s in card["skills"]:
                style = "highlight-tag" if search_keyword in s else ""
                tags += f'<span class="skill-tag {style}">{s}</span>'

            c2.markdown(tags, unsafe_allow_html=True)
            st.divider()
    else:
        st.warning("見つかりませんでした。")


else:
    # =============================
    # 🏁 レース攻略モード
    # =============================
    st.header("🏁 12月チャンミ攻略")

    criteria = race_data.race_criteria
    c1, c2 = st.columns(2)
    race = c1.selectbox("レース", list(criteria.keys()))
    strategy = c2.radio("脚質", ["逃げ", "先行", "差し", "追込"], horizontal=True)

    target_skills = criteria[race].get(strategy, [])

    if target_skills:
        with st.expander(f"📋 必要スキルリスト ({len(target_skills)})", expanded=True):
            st.markdown(" ".join([f'<span class="skill-tag">{s}</span>' for s in target_skills]), unsafe_allow_html=True)

        st.subheader("おすすめサポカ")

        targets = cards if search_source == "全カード" else [
            c for c in cards if c["name"] in my_inventory
        ]
        results = []

        for card in targets:
            matched = [s for s in card["skills"] if s in target_skills]
            if matched:
                results.append({
                    "name": card["name"],
                    "type": card["type"],
                    "skills": matched,
                    "score": len(matched),
                })

        if results:
            results.sort(key=lambda x: x["score"], reverse=True)
            st.success(f"{len(results)} 枚の有効カード")

            for r in results:
                c1, c2 = st.columns([1, 4])
                c1.markdown(
                    f"**{r['name']}**<br><small>{add_icon_to_type(r['type'])}</small>",
                    unsafe_allow_html=True
                )
                c2.progress(min(r['score'] / 5, 1.0), text=f"有効スキル: {r['score']} 個")
                tags = " ".join([f'<span class="skill-tag highlight-tag">{s}</span>' for s in r["skills"]])
                c2.markdown(tags, unsafe_allow_html=True)
                st.divider()
        else:
            st.warning("該当カードなし。")

