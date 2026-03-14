import streamlit as st
from data_loader import load_cards_json
from race_loader import load_races, load_race_skills, get_race_by_id

# 画面設定
st.set_page_config(page_title="因子周回サポカ評価", layout="wide", initial_sidebar_state="collapsed")

# ==========================================
# カスタムCSS
# ==========================================
st.markdown("""
<style>
  /* 全体 */
  .block-container { padding-top: 1rem; padding-bottom: 2rem; }
  
  /* ヘッダー */
  .factor-header { 
    background: linear-gradient(to right, #f8fafc, #ffffff); 
    border-bottom: 1px solid #e2e8f0; 
    padding: 1rem 1.5rem; 
    margin: -1rem -1rem 1.5rem -1rem; 
    display: flex; align-items: center; justify-content: space-between; 
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
  }
  .factor-header h1 { font-size: 1.25rem; font-weight: 800; color: #0f172a; margin: 0; display: flex; align-items: center; gap: 0.5rem; }
  .factor-header .version { font-size: 0.75rem; color: #64748b; background: #f1f5f9; padding: 0.25rem 0.5rem; border-radius: 9999px; font-family: monospace; border: 1px solid #cbd5e1; }
  
  /* バッジ */
  .step-badge { background: #3b82f6; color: white; font-size: 11px; font-weight: 700; letter-spacing: 0.05em; padding: 3px 10px; border-radius: 9999px; display: inline-block; margin-right: 8px; box-shadow: 0 2px 4px rgba(59, 130, 246, 0.3); }
  .step-title { font-weight: 700; color: #334155; font-size: 0.95rem; display: flex; align-items: center; gap: 0.5rem; }

  /* スキルタグ - ビンゴ表示用 */
  .race-skills-container {
    background: white; border: 1px solid #e2e8f0; border-radius: 12px; padding: 1.25rem; margin-bottom: 1.5rem;
    line-height: 2; box-shadow: 0 1px 3px rgba(0,0,0,0.05);
  }
  .skill-tag { 
    display: inline-block; padding: 3px 10px; border-radius: 6px; font-size: 11px; margin: 3px; font-weight: 600; border: 1px solid transparent; transition: all 0.2s;
  }
  .skill-tag.active { 
    background: #eff6ff; color: #2563eb; border-color: #bfdbfe; box-shadow: 0 2px 4px rgba(37,99,235,0.15); transform: translateY(-1px);
  }
  .skill-tag.inactive { 
    background: #f8fafc; color: #94a3b8; border-color: #f1f5f9; opacity: 0.7;
  }

  /* ライブラリリスト用 */
  .lib-card-row {
    padding: 10px; border-bottom: 1px solid #f1f5f9; display: flex; justify-content: space-between; align-items: center; transition: background 0.1s;
  }
  .lib-card-row:hover { background: #f8fafc; }
  .lib-card-info { flex: 1; margin-right: 12px; }

  /* ボタン調整 */
  .stButton button { width: 100%; border-radius: 6px; font-size: 12px; font-weight: 600; transition: all 0.2s; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 関数定義
# ==========================================

@st.cache_data
def load_cards(path: str = "cards.json"):
    return load_cards_json(path)

def icon_for_type(t: str) -> str:
    m = {"スピード": "👟", "スタミナ": "❤️", "パワー": "💪", "根性": "🔥", "賢さ": "🎓", "友人": "🧢", "グループ": "🧢"}
    for k, v in m.items():
        if k in str(t): return v
    return ""

TYPE_COLORS = {
    "スピード": "#3b82f6", "スタミナ": "#f97316", "パワー": "#ec4899", 
    "根性": "#f87171", "賢さ": "#10b981", "友人": "#eab308", "グループ": "#eab308"
}

def type_badge_color(t: str) -> str:
    for k, v in TYPE_COLORS.items():
        if k in str(t): return v
    return "#94a3b8"

def get_matching_skills(card_skills: list[str], effective_skill_names: set[str]) -> list[str]:
    if not card_skills: return []
    return [s for s in card_skills if s in effective_skill_names]

# ==========================================
# Fragment定義 (部分更新エリア)
# ==========================================
@st.fragment
def deck_builder_ui(cards, races_data):
    """
    デッキ構築に関するUI全体。
    レイアウトを合わせるため、STEP1のレース選択もFragment内部に移動しました。
    """
    col_library, col_deck = st.columns([1, 1.5], gap="large")

    # ------------------------------------------
    # 左カラム: STEP 1 ＆ ライブラリ
    # ------------------------------------------
    with col_library:
        # --- レース選択 (STEP 1) ---
        st.markdown('<div style="margin-bottom:8px;"><span class="step-badge">STEP 1</span><span class="step-title" style="display:inline;">レース選択 / Target Race</span></div>', unsafe_allow_html=True)
        race_options = {f"{r['label']}（{r.get('course','')} {r.get('direction','')} {r.get('weather','')}）": r["id"] for r in races_data}
        race_label = st.selectbox("レース", options=list(race_options.keys()), key="factor_race_label", label_visibility="collapsed")
        race_id = race_options[race_label]
        
        # 選択されたレースのスキルデータをロード
        effective_list = load_race_skills(race_id)
        effective_skill_names_set = {s["name"] for s in effective_list}
        
        # セッションステートの初期化
        deck_session_key = f"factor_deck_{race_id}_v2"
        if deck_session_key not in st.session_state:
            st.session_state[deck_session_key] = []
        current_deck_names = st.session_state[deck_session_key]

        st.markdown("<br>", unsafe_allow_html=True)

        # --- サポカ一覧 ---
        st.markdown(f'<span class="step-title">📚 サポカ一覧 ({len(cards)})</span>', unsafe_allow_html=True)
        st.caption("有効スキルの多い順に表示しています")
        
        # 検索・フィルタ
        search_query = st.text_input("検索 filter", placeholder="カード名・スキル名...", key="lib_search").strip().lower()
        
        # リスト作成
        display_candidates = []
        for c in cards:
            c_skills = c.get("skills") or []
            matched = get_matching_skills(c_skills, effective_skill_names_set)
            match_count = len(matched)
            
            if search_query:
                if search_query not in c["name"].lower() and not any(search_query in s.lower() for s in c_skills):
                    continue
            
            display_candidates.append({
                "card": c,
                "match_count": match_count,
                "matched_skills": matched
            })
        
        display_candidates.sort(key=lambda x: x["match_count"], reverse=True)
        
        limit = 20 if not search_query else 100
        shown_candidates = display_candidates[:limit]
        
        if not search_query:
            st.caption(f"※動作軽量化のため上位{limit}件のみ表示中")
        else:
            st.caption(f"{len(shown_candidates)}件表示中")
        
        with st.container(height=550, border=True):
            for idx, item in enumerate(shown_candidates):
                c = item["card"]
                match_count = item["match_count"]
                in_deck = c["name"] in current_deck_names
                type_color = type_badge_color(c.get('type', ''))
                
                st.markdown(f"""
                <div class="lib-card-row" style="padding: 8px 10px;">
                    <div class="lib-card-info" style="display:flex; align-items:center; justify-content:space-between; width:100%;">
                        <div style="display:flex; align-items:center; gap:8px;">
                            <span class="type-badge" style="background:{type_color}; min-width:24px;">{icon_for_type(c.get('type',''))}</span>
                            <div style="font-size:13px; font-weight:700; color:#334155;">{c['name']}</div>
                        </div>
                        <div style="font-size:12px; font-weight:700; color:{'#e11d48' if match_count > 0 else '#94a3b8'}; white-space:nowrap;">
                            {match_count} <span style="font-size:10px; color:#64748b; font-weight:normal;">Hit</span>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                if in_deck:
                    st.button("追加済", key=f"btn_add_disabled_{idx}", disabled=True)
                else:
                    if len(current_deck_names) >= 6:
                         st.button("満員", key=f"btn_full_{idx}", disabled=True)
                    else:
                        if st.button("追加", key=f"btn_add_{idx}", type="primary" if match_count > 0 else "secondary"):
                            st.session_state[deck_session_key].append(c["name"])
                            st.rerun()

    # ------------------------------------------
    # 右カラム: レーススキル ＆ デッキ
    # ------------------------------------------
    with col_deck:
        deck_all_skills = set()
        for name in current_deck_names:
            c_data = next((c for c in cards if c["name"] == name), None)
            if c_data:
                for s in (c_data.get("skills") or []):
                    deck_all_skills.add(s)

        achieved_count = len(deck_all_skills & effective_skill_names_set)
        total_effective = len(effective_skill_names_set)
        coverage_pct = int(achieved_count / total_effective * 100) if total_effective > 0 else 0
        
        st.markdown(f"""
        <div style="display:flex; justify-content:space-between; align-items:end; margin-bottom:8px;">
            <span class="step-title">🎯 レース有効スキル (Bingo)</span>
            <span style="font-size:12px; font-weight:700; color:#2563eb;">達成率: {achieved_count} / {total_effective} ({coverage_pct}%)</span>
        </div>
        """, unsafe_allow_html=True)
        
        if not effective_list:
            st.warning(f"「{race_id}」の有効スキルデータがありません。")
        else:
            skills_html = '<div class="race-skills-container">'
            for s in effective_list:
                s_name = s["name"]
                is_active = s_name in deck_all_skills
                cls = "active" if is_active else "inactive"
                icon = "✅ " if is_active else ""
                skills_html += f'<span class="skill-tag {cls}">{icon}{s_name}</span>'
            skills_html += '</div>'
            st.markdown(skills_html, unsafe_allow_html=True)

        st.markdown(f'<span class="step-title" style="margin-top:24px;">🎴 選択中デッキ ({len(current_deck_names)}/6)</span>', unsafe_allow_html=True)
        
        with st.container(height=480, border=True):
            if not current_deck_names:
                st.info("👈 左のリストからカードを追加してください\n\n※ここに最大6枚のカードが配置されます。")
            
            if current_deck_names:
                for i in range(0, len(current_deck_names), 2):
                    cols = st.columns(2)
                    row_cards = current_deck_names[i : i + 2]
                    
                    for j, name in enumerate(row_cards):
                        idx = i + j
                        with cols[j]:
                            c = next((x for x in cards if x["name"] == name), {"name": name, "type": "?", "skills": []})
                            c_skills = c.get("skills") or []
                            matched_skills = get_matching_skills(c_skills, effective_skill_names_set)
                            type_color = type_badge_color(c.get('type', ''))
                            
                            with st.container(border=True):
                                h_col1, h_col2 = st.columns([4, 1], vertical_alignment="center")
                                
                                with h_col1:
                                    st.markdown(f"""
                                    <div style="font-size:13px; font-weight:700; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; padding-top:4px;" title="{c['name']}">
                                        <span style="background:{type_color}; padding:2px 6px; border-radius:4px; color:white; font-size:10px; margin-right:4px;">{icon_for_type(c.get('type',''))}</span>
                                        {c['name']}
                                    </div>
                                    """, unsafe_allow_html=True)
                                
                                with h_col2:
                                    if st.button("削除", key=f"btn_del_{idx}"):
                                        current_deck_names.pop(idx)
                                        st.session_state[deck_session_key] = current_deck_names
                                        st.rerun()
                                
                                with st.expander(f"有効スキル: {len(matched_skills)}個"):
                                    if matched_skills:
                                        tags = "".join([f'<span class="skill-tag active" style="font-size:10px; margin:2px;">{s}</span>' for s in matched_skills])
                                        st.markdown(f'<div style="margin-bottom:8px;">{tags}</div>', unsafe_allow_html=True)
                                    else:
                                        st.caption("有効スキルなし")
                                    
                                    st.markdown("---")
                                    if c_skills:
                                        skill_txts = [f"**{s}**" if s in effective_skill_names_set else s for s in c_skills]
                                        st.caption(" / ".join(skill_txts))

# ==========================================
# メインプロセス (画面外枠)
# ==========================================
st.markdown("""
<div class="factor-header">
  <h1><span>🐴</span> 因子周回サポカ評価</h1>
  <span class="version">v1.5.0 (Fragment Edition)</span>
</div>
""", unsafe_allow_html=True)

try:
    cards_data = load_cards("cards.json")
except FileNotFoundError as e:
    st.error(f"カードデータが見つかりません: {e}")
    st.stop()

races_data = load_races()
if not races_data:
    st.warning("race/races.json にレースが登録されていません。")
    st.stop()

# レイアウト変更により、ここにあった STEP1 は deck_builder_ui 内部へ移動しました！
deck_builder_ui(cards_data, races_data)