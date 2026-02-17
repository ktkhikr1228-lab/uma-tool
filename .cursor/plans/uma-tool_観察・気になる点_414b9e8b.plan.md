---
name: uma-tool 観察・気になる点
overview: uma-tool フォルダを調査し、データの二重管理・表記ゆれ・ドキュメント不足・エントリポイントの分岐など、気になる点を整理した観察メモです。
todos: []
isProject: false
---

# uma-tool フォルダの観察・気になる点

## 1. データソースの二重化（CSV と JSON）

- **現状**
  - [app.py](c:\uma-tool\app.py) は **cards.csv** を読み、[app_json.py](c:\uma-tool\app_json.py) は **cards.json** を [data_loader.py](c:\uma-tool\data_loader.py) 経由で読み込んでいる。
  - CSV: 列は `レアリティ, キャラクター名, カード名, タイプ, 所持スキル`。所持スキルに日付（例: `2021.02.24`）が混在。
  - JSON: `name`, `type`, `skills` の配列。日付は含まない。
- **懸念**
  - どちらが正とするデータかが不明。更新時に両方揃える必要があり、不整合のリスクがある。
  - 生成元も別（[auto_db_maker.py](c:\uma-tool\auto_db_maker.py) → cards.csv、[data_maker.py](c:\uma-tool\data_maker.py) → cards.json）。

## 2. スキル名の「○」と「◯」の表記ゆれ（検索バグ要因）

- **事実**
  - [cards.json](c:\uma-tool\cards.json) / [cards.csv](c:\uma-tool\cards.csv) のスキルは **○**（U+25CB）で書かれている（例: `先行直線○`, `良バ場○`）。
  - [race_data.py](c:\uma-tool\race_data.py) のレース有効スキルは **◯**（U+25EF）で書かれている（例: `先行直線◯`, `良バ場◯`）。
- **影響**
  - app.py / app_json.py では `race_data.race_criteria` のスキル名とカードのスキル名を突き合わせて「レースで有効なスキル」をハイライトしている。文字が違うため **一致せず、ハイライトされない** 可能性が高い。
- **対応案**
  - どちらか一方に統一する（例: すべて ○ に揃え、race_data.py を修正）、または比較時に両方の文字を同一視する正規化を入れる。

## 3. ドキュメント・依存関係の不足

- **requirements.txt がない**
  - 使用しているのは少なくとも `streamlit`, `pandas`。再現環境のため `requirements.txt`（または pyproject.toml）があるとよい。
- **README がない**
  - プロジェクトの目的、`app.py` / `app_json.py` の起動方法、cards.csv と cards.json の役割や更新手順が分かる簡易 README があると運用しやすい。
- **.gitignore がない**
  - `__pycache__/`、大きなメディアやスクレイプ結果（`gamewith_files/`, `kamigame_files/`, `Wiki_files/`, `images/` など）をリポジトリに含めないようにするため、.gitignore の追加を推奨。

## 4. エントリポイントが 2 つある

- **app.py** … cards.csv ベースの Streamlit アプリ
- **app_json.py** … cards.json ベースの Streamlit アプリ
- 機能はほぼ同じに見えるため、「本番はどちらを使うか」を決めておくとよい。統一するなら、データソースを 1 つ（CSV か JSON）に寄せて 1 つの `app.py` にまとめる選択肢もある。

## 5. その他のファイル・データ

- **umamusume_cards.csv**  
[uma_scraper.py](c:\uma-tool\uma_scraper.py) の出力。列は `rarity, character_name, type, skills, url`。サンプルでは `skills` が空の行が多く、cards.csv / cards.json との関係（スキル投入用か、別用途か）がコード上は明確でない。
- **cards.csv の「所持スキル」**
  - スキル名の羅列に加え、末尾に日付（例: `2021.02.24`）が含まれている。パースや検索時に「スキル名として扱わない」処理が必要。現状の app がどう扱っているかは要確認。
- **race_data.py**
  - 現状は「12月チャンミ（阪神1600m）」用のみ。他レースを追加する場合は、同じくスキル名の表記（○/◯）を統一しておくと安全。

---

## まとめ（優先して直すと良さそうな点）


| 優先度 | 内容                                                                          |
| --- | --------------------------------------------------------------------------- |
| 高   | スキル名の **○ と ◯ の統一**（race_data.py とカードデータの一致）。これがないとレース有効スキルのハイライトが効かない可能性大。 |
| 中   | データソースを **CSV か JSON のどちらかに寄せる**、または「正はどちらか」を README で明記する。                 |
| 中   | **requirements.txt** と簡易 **README**、必要なら **.gitignore** の追加。                |
| 低   | エントリポイントを 1 つにまとめるか、役割を README で説明する。                                       |


以上が、uma-tool フォルダを見て気になった点です。実装はせず、計画モードとして観察結果のみまとめています。