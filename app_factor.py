
import streamlit as st  # type: ignore[reportMissingImports]
from data_loader import load_cards_json # type: ignore[reportMissingImports]
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

  /* カードコンポーネント */
  .card-box {
    background: white; border: 1px solid #e2e8f0; border-radius: 10px; padding: 14px; margin-bottom: 12px;
    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
    position: relative;
    overflow: hidden;
  }
  
  .card-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 10px; }
  .card-title { font-size: 14px; font-weight: 700; color: #1e293b; display: flex; align-items: center; gap: 8px; line-height: 1.4; }
  .type-badge { font-size: 10px; padding: 3px 8px; border-radius: 4px; color: white; font-weight: 700; min-width: 24px; text-align: center; }
  
  .matched-skills-area { margin-top: 10px; padding-top: 10px; border-top: 1px dashed #e2e8f0; }
  .matched-label { font-size: 10px; color: #64748b; font-weight: 700; margin-bottom: 6px; text-transform: uppercase; letter-spacing: 0.05em; }
  
  /* ライブラリリスト用 */
  .lib-card-row {
    padding: 10px; border-bottom: 1px solid #f1f5f9; display: flex; justify-content: space-between; align-items: center; transition: background 0.1s;
  }
  .lib-card-row:hover { background: #f8fafc; }
  .lib-card-info { flex: 1; margin-right: 12px; }
  .lib-card-match { font-size: 11px; color: #2563eb; font-weight: 600; margin-top: 2px; text-overflow: ellipsis; white-space: nowrap; overflow: hidden; max-width: 100%; }

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

def count_matching_skills(card_skills: list[str], effective_skill_names: set[str]) -> int:
    if not card_skills: return 0
    return sum(1 for s in card_skills if s in effective_skill_names)

def get_matching_skills(card_skills: list[str], effective_skill_names: set[str]) -> list[str]:
    if not card_skills: return []
    return [s for s in card_skills if s in effective_skill_names]

# ==========================================
# メイン処理
# ==========================================

# ヘッダー
st.markdown("""
<div class="factor-header">
  <h1><span>🐴</span> 因子周回サポカ評価</h1>
  <span class="version">v1.4.1</span>
</div>
""", unsafe_allow_html=True)

# データ読み込み
try:
    cards = load_cards("cards.json")
except FileNotFoundError as e:
    st.error(f"カードデータが見つかりません: {e}")
    st.stop()

# レース読み込み
races = load_races()
if not races:
    st.warning("race/races.json にレースが登録されていません。")
    st.stop()

# STEP 1: レース選択
col_step1, col_step1_b = st.columns([2, 1])
with col_step1:
    st.markdown('<div style="margin-bottom:8px;"><span class="step-badge">STEP 1</span><span class="step-title" style="display:inline;">レース選択 / Target Race</span></div>', unsafe_allow_html=True)
    race_options = {f"{r['label']}（{r.get('course','')} {r.get('direction','')} {r.get('weather','')}）": r["id"] for r in races}
    race_label = st.selectbox("レース", options=list(race_options.keys()), key="factor_race_label", label_visibility="collapsed")
    race_id = race_options[race_label]

# レースデータ取得
effective_list = load_race_skills(race_id)
effective_skill_names = {s["name"] for s in effective_list}

if not effective_list:
    st.warning(f"「{race_id}」の有効スキルデータがありません。")
    st.stop()

# セッション状態管理（デッキ）
deck_key = f"factor_deck_{race_id}_v2"
if deck_key not in st.session_state:
    st.session_state[deck_key] = [] # 名前リスト

current_deck_names = st.session_state[deck_key]

# デッキ内の全ユニークスキル（ハイライト用）
deck_all_skills = set()
for name in current_deck_names:
    c_data = next((c for c in cards if c["name"] == name), None)
    if c_data:
        for s in (c_data.get("skills") or []):
            deck_all_skills.add(s)

# ==========================================
# レイアウト
# ==========================================
st.markdown("---")
col_library, col_deck = st.columns([1, 1.5], gap="large") # Adjust column ratio

# ------------------------------------------
# 左カラム: ライブラリ（検索・追加）
# ------------------------------------------
with col_library:
    st.markdown(f'<span class="step-title">📚 サポカ一覧 ({len(cards)})</span>', unsafe_allow_html=True)
    st.caption("有効スキルの多い順に表示しています")
    
    # 検索・フィルタ
    search_query = st.text_input("検索 filter", placeholder="カード名・スキル名...", key="lib_search").strip().lower()
    
    # リスト作成（有効スキル数順でソート）
    display_candidates = []
    for c in cards:
        c_skills = c.get("skills") or []
        matched = get_matching_skills(c_skills, effective_skill_names)
        match_count = len(matched)
        
        # 検索フィルタ
        if search_query:
            if search_query not in c["name"].lower() and not any(search_query in s.lower() for s in c_skills):
                continue
        
        display_candidates.append({
            "card": c,
            "match_count": match_count,
            "matched_skills": matched
        })
    
    # ソート: 有効スキル数 降順
    display_candidates.sort(key=lambda x: x["match_count"], reverse=True)
    
    # 表示件数制限 (パフォーマンス対策)
    limit = 20 if not search_query else 100
    shown_candidates = display_candidates[:limit]
    
    if not search_query:
        st.caption(f"※動作軽量化のため上位{limit}件のみ表示中")
    else:
        st.caption(f"{len(shown_candidates)}件表示中")
    
    # 表示
    for idx, item in enumerate(shown_candidates):
        c = item["card"]
        match_count = item["match_count"]
        matched_skills = item["matched_skills"]
        in_deck = c["name"] in current_deck_names
        
        with st.container():
            # カード行UI
            type_color = type_badge_color(c.get('type', ''))
            matched_text = " / ".join(matched_skills) if matched_skills else "なし"
            
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
            
            # 追加ボタン
            if in_deck:
                st.button("追加済", key=f"btn_add_disabled_{idx}", disabled=True)
            else:
                if len(current_deck_names) >= 6:
                     st.button("満員", key=f"btn_full_{idx}", disabled=True)
                else:
                    if st.button("追加", key=f"btn_add_{idx}", type="primary" if match_count > 0 else "secondary"):
                        st.session_state[deck_key].append(c["name"])
                        st.rerun()

# ------------------------------------------
# 右カラム: デッキ ＆ レーススキル
# ------------------------------------------
with col_deck:
    # 1. レーススキル（Bingo表示）
    achieved_count = len(deck_all_skills & effective_skill_names)
    total_effective = len(effective_skill_names)
    coverage_pct = int(achieved_count / total_effective * 100) if total_effective > 0 else 0
    
    st.markdown(f"""
    <div style="display:flex; justify-content:space-between; align-items:end; margin-bottom:8px;">
        <span class="step-title">🎯 レース有効スキル (Bingo)</span>
        <span style="font-size:12px; font-weight:700; color:#2563eb;">達成率: {achieved_count} / {total_effective} ({coverage_pct}%)</span>
    </div>
    """, unsafe_allow_html=True)
    
    skills_html = '<div class="race-skills-container">'
    for s in effective_list:
        s_name = s["name"]
        is_active = s_name in deck_all_skills
        cls = "active" if is_active else "inactive"
        icon = "✅ " if is_active else ""
        skills_html += f'<span class="skill-tag {cls}">{icon}{s_name}</span>'
    skills_html += '</div>'
    st.markdown(skills_html, unsafe_allow_html=True)

    # 2. デッキ表示 (6枚)
    st.markdown(f'<span class="step-title" style="margin-top:24px;">🎴 選択中デッキ ({len(current_deck_names)}/6)</span>', unsafe_allow_html=True)
    
    if not current_deck_names:
        st.info("👈 左のリストからカードを追加してください")
    
    # グリッド表示 (2カラム x 3行 の Z順配置)
    if current_deck_names:
        # 2つずつチャンクに分割して行ごとに表示する
        for i in range(0, len(current_deck_names), 2):
            cols = st.columns(2)
            # この行に表示するカード (最大2枚)
            row_cards = current_deck_names[i : i + 2]
            
            for j, name in enumerate(row_cards):
                # 全体インデックス
                idx = i + j
                
                with cols[j]:
                    # データ取得
                    c = next((x for x in cards if x["name"] == name), {"name": name, "type": "?", "skills": []})
                    c_skills = c.get("skills") or []
                    
                    # 有効スキル抽出
                    matched_skills = get_matching_skills(c_skills, effective_skill_names)
                    
                    # カードUI (ヘッダー部分)
                    type_color = type_badge_color(c.get('type', ''))
                    
                    st.markdown(f"""
                    <div class="card-box" style="margin-bottom:0px; border-bottom-left-radius:0; border-bottom-right-radius:0; border-bottom:none;">
                        <div class="card-header" style="margin-bottom:0;">
                            <div class="card-title">
                                <span class="type-badge" style="background:{type_color}">{icon_for_type(c.get('type',''))}</span>
                                {c['name']}
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Expander (カードの下に結合)
                    with st.expander(f"有効スキル: {len(matched_skills)}個"):
                        # 有効スキルタグ
                        if matched_skills:
                            tags = "".join([f'<span class="skill-tag active" style="font-size:10px;">{s}</span>' for s in matched_skills])
                            st.markdown(f'<div style="margin-bottom:8px;">{tags}</div>', unsafe_allow_html=True)
                        else:
                            st.caption("有効スキルなし")
                        
                        # 全スキル表示
                        st.markdown("---")
                        if c_skills:
                            skill_txts = []
                            for s in c_skills:
                                if s in effective_skill_names:
                                    skill_txts.append(f"**{s}**")
                                else:
                                    skill_txts.append(s)
                            st.caption(" / ".join(skill_txts))
                        
                        # 削除ボタン
                        if st.button("削除", key=f"btn_del_{idx}"):
                            current_deck_names.pop(idx)
                            st.session_state[deck_key] = current_deck_names
                            st.rerun()
