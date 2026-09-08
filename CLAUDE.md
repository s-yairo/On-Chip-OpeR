# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 概要

On-Chip OpeR は、On-chip Biotechnologies 社のマイクロ流路デバイス／フローサイトメーターの操作を、
1工程ずつ案内する Streamlit 製の実験ナビゲーションアプリ。UI 文言・データ・ドキュメントはすべて日本語。
外部ネットワークへは一切接続しない（AI 応答も現状はダミー固定応答）。

## コマンド

```bash
pip install -r requirements.txt
streamlit run app.py
```

Windows では `launch.bat`（依存インストール＋起動をまとめて実行）。

### 検証

自動テストスイートは存在しない。従来 AUDIT_REPORT.md で報告している検証は次の3種類：

```bash
python -c "import ast,pathlib; [ast.parse(p.read_text(encoding='utf-8')) for p in pathlib.Path('.').rglob('*.py')]"
python -c "import json,pathlib; [json.load(open(p,encoding='utf-8')) for p in pathlib.Path('data').glob('*.json')]"
```

加えて、6ワークフロー・全121工程を疑似 Streamlit で描画して例外が出ないことを確認する慣行がある。
UI 変更時は工程数・チェック件数・製品件数が変わっていないことを必ず数えて確認する（下記「不変条件」）。

## アーキテクチャ

### app.py（約3,500行）が唯一のエントリポイント

末尾の `if st.session_state.page == ...` 連鎖が唯一のルーター。ページ遷移は必ず
`go(page)` / `open_*()` ヘルパー経由で `st.session_state.page` を書き換えて `st.rerun()` する。
モジュール分割はされていないので、新しい画面は `render_xxx()` を定義してこの連鎖に追加する。

実行順序は固定：`init_state()` → `apply_query_navigation()` → `render_sidebar()` → ページ描画 →
`apply_glossary_hover()` → `apply_scroll_to_top()`。後半2つは描画後に JS/CSS を注入するため順序を崩さない。

### データ駆動：工程は JSON に書く、Python には書かない

`data/manual_steps.json` の `workflows` 配下に6ワークフロー（`analysis` 12 / `sorting` 21 /
`dg800_wo` 17 / `dg800_gmd` 26 / `dg1060_1100_wo` 17 / `dg1060_1100_gmd` 28、合計121工程）。
各 step の主なキー：

- `id`（`a04`、`d8w_03` など。進行状態のキーになるので変更しない）、`title`、`instruction`、`task`、`why`
- `checks`：チェックボックス。**全部にチェックが入るまで「次へ」が押せない**
- `operation_steps` / 分岐内グループ化操作：番号付き操作手順
- `branches`：分岐。選択時に `active = {**step, **branch}` とマージされ、以降の描画は `active` を参照する。
  「step を読むか active を読むか」の区別が全描画処理の要。
- `ok_state` / `ng_state` / `abnormal_action` / `ok_images` / `ng_images` / `screen_images`
- `show_screen_section` / `show_result_sections` / `show_checks_after_operations` などの表示フラグ

`current_workflow_steps()` だけが例外的に Python 側で工程列を加工する（Selector 選択時に工程を1件挿入し
1件を移動）。したがって画面上の工程数は JSON の件数と一致しないことがある。

その他のデータ：`product_catalog.json`（製品71件・価格項目を含まないことを `load_product_catalog` が検証）、
`glossary.json`（用語集・工程内ホバーと共通ソース）、`experiment_records.json`（実験記録の永続化）。

### セッション状態がすべて（外部保存はしない）

`init_state()` の `defaults` が状態キーの一覧。工程位置・チェック・分岐・メモは
**開いている Streamlit セッション内だけ**で保持し、進行状況の JSON 保存／再開機能は No.300 で撤去済み。
再導入の指示がない限り復活させない。例外は実験記録（`data/experiment_records.json` へ保存）。

ウィジェットキーは `{step_id}_{suffix}_check_{n}`、`branch_{step_id}`、`note_{step_id}` の規則。
`is_transient_widget_key()` / `clear_step_widgets()` がこの規則に依存しているので、キー命名を崩さない。

### core/ ：本体から切り出した4つの層

- `core/experiment_condition_advisor/`：実験条件検討。`app.py` から
  `render(navigation_version=..., product_catalog=..., product_matcher=...)` で直接呼ぶ。
  閉域のルールベース試作で、外部送信も生成モデルも使わない。
- `core/ai/`：AI 呼び出しの単一窓口。UI からは `AIConnector.ask(question, context)` のみを呼ぶ。
  provider は `config/features.json` の `joint_ai.provider` で決まり、現状 `dummy`（固定応答「これはテストです」、
  ネットワークアクセスなし）だけが実装済み。`AIConnector` は例外を投げず、必ず `AIResponse` を返す設計。
- `core/product_catalog.py`：製品名の完全一致インデックスと、工程文中の製品名スパン検出（ホバーカード用）。
- `core/experiment_records.py`：`schema_version=1` 固定。一時ファイル＋`replace()` による原子的保存。

### JointAI は読み取り専用

工程・チェック・分岐・メモを AI が書き換える経路は存在しない。`build_joint_ai_context()` が工程情報を
読み取り専用コンテキストとして渡すだけ。サイドバーの参考資料アップロードもファイル名・MIME・サイズのみを
コンテキストに含め、本文解析はしない。この境界は仕様として明示されているので、拡張時は必ず確認を取る。

### 参照されていない旧プラグイン機構

`plugins/`、`optional_requirements/`、`core/feature_registry.py` は、No.378 で実験条件検討を
`core/` へ統合した時点から **どこからも import されていない**。`plugins/experiment_condition_advisor/` は
`core/experiment_condition_advisor/` とほぼ同一内容の重複コピーなので、実験条件検討を直すときは
`core/` 側だけを編集する。仕様と経緯は [docs/plugin-architecture.md](docs/plugin-architecture.md)。

### 画像

`images/` 直下にファイル名で参照（`image_placeholder()` はファイルが無ければプレースホルダーを描画するので、
存在しない画像を指定してもクラッシュはしない）。製品画像は `images/products/*.webp` を
app.py 冒頭の `PRODUCT_IMAGE_BY_NUMBER`（製品番号→ファイル名）でマッピングし、data URI 化して埋め込む。
一部の説明図は SVG のオリジナル図（`fluorescence_wavelength_channels.svg` など）。

## 開発の進め方（このリポジトリ固有）

- 変更依頼は `No.XXX` という連番で来る。CHANGELOG.md の先頭と AUDIT_REPORT.md に、
  その番号範囲で何を変えて何を変えなかったかを追記するのが慣行（新しい番号が上）。
  README.md はリポジトリの説明書であり、変更履歴を書き足す場所ではない。
- app.py 内のコメントも `# No.370: ...` の形で変更根拠の番号を残す。
- `VERSION`（app.py 冒頭）はアプリ表示版。README/AUDIT_REPORT の記載と食い違うことがあるので、
  現在値は必ず app.py を見る。AUDIT_REPORT.md は最新コードより遅れている場合がある。
- 依頼された範囲だけを変更する。特に工程数・工程ID・工程順・チェック総数・製品件数・用語集件数は
  明示的な指示がない限り変えない（AUDIT_REPORT の「明示的に変更していない範囲」節が毎回この確認をしている）。
- 文言は既存の敬体・表記ゆれに合わせる。マニュアルにない具体値（圧力・流量・濃度など）を新規に作らない。
- git リポジトリではないため、変更前後の差分確認は自前でファイルを退避して行う。

## 不変条件（変更時に壊しやすい点）

- 全ユーザー向け文字列は `html.escape()` を通すか、`unsafe_allow_html=True` を使う箇所では
  エスケープ済みの断片だけを埋め込む（`html_lines()`、`product_hover_text_html()` を使う）。
- `st.rerun()` を伴う状態変更は必ずヘルパー関数側で行い、描画途中で状態を書き換えない。
- 分岐のある工程では、選択が変わると `clear_step_widgets(step_id, keep_branch=True)` で
  下位ウィジェットを破棄する必要がある（古いチェック状態の残留を防ぐ）。
