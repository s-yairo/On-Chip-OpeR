# 工程データの仕様とコースの追加手順

手順コース（ワークフロー）の中身は `data/manual_steps.json` にあり、`app.py` には1工程も書かれていません。`app.py` の [`render_guide()`](../app.py) は、このJSONを読んで画面を組み立てる汎用の描画処理です。

ただし **コースの入口だけはハードコード** されているため、JSONにコースを足しただけでは画面に現れません。詳細は「7. コースを追加する手順」を参照してください。

## 1. ファイル全体の構造

```json
{
  "manual_basis":    { ... },   // 参照マニュアルの版などの記録用メタデータ
  "safety_check":    [ ... ],   // 安全上の注意（文字列の配列）
  "workflows":       { ... },   // コース本体
  "troubleshooting": [ ... ],   // トラブル一覧
  "app_version":     "...",
  "contact":         "...",     // 共通連絡文。異常時セクションの既定値
  "sop_notice":      "..."      // SOP優先の案内文
}
```

`app.py` の `load_data()` は `workflows`、`contact`、`sop_notice`、`troubleshooting` の4つが揃っているかだけを検証し、欠けていればエラーを表示して `st.stop()` で起動を止めます。JSONとして壊れている場合も同様です。工程の中身は検証しません。`manual_basis`、`safety_check`、`app_version` はどこからも参照されていない記録用の項目です。

## 2. `workflows` オブジェクト

キーが **コースキー**（`analysis`、`dgs_a_wo` など）で、値は次の3項目です。

| キー | 型 | 用途 |
| --- | --- | --- |
| `label` | str | 工程画面の見出し。コース名 |
| `description` | str | 見出し直下の説明文 |
| `steps` | list | 工程の配列。**表示順は配列順** |

コースキーは `st.session_state.workflow_key` に入り、進行状態の管理単位になります。

## 3. `steps` の各工程

現在191工程で使われているキーです。「出現数」は現行データでの使用数、「既定」は未指定時の挙動です。

| キー | 型 | 出現 | 描画先 | 備考 |
| --- | --- | ---: | --- | --- |
| `id` | str | 191 | — | **進行状態のキー**。`completed`、`step_branches`、`notes`、ウィジェットキーすべてがこれを使う。変更するとセッション中の状態が壊れる |
| `title` | str | 191 | 工程見出し | `Step N / M` の下に表示 |
| `task` | str | 191 | 「やること」枠 | 未指定なら `instruction` を使う |
| `instruction` | str | 191 | 分岐選択時の `st.info` | 分岐のない工程では `task` の予備として働くだけ |
| `checks` | list[str] | 189 | 「次へ進む前の確認」 | **全項目にチェックが入るまで次へ進めない** |
| `why` | str | 186 | 「なぜこの操作を行うのですか？」 | 折りたたみ。既定は「この工程の理由は確認中です。」 |
| `decision_support` | list[str] | 191 | 「判断の目安」 | 折りたたみ。空配列なら非表示 |
| `warning` | str | 153 | 「異常時」枠 / NG例の既定 | 下記「4. 既定値の連鎖」を参照 |
| `screen_images` | list[obj] | 159 | 「実画面」 | 2列で並ぶ |
| `show_screen_section` | bool | 162 | 「実画面」の表示可否 | 既定 `true` |
| `show_result_sections` | bool | 160 | OK例／NG例／異常時の表示可否 | 既定 `true` |
| `ok_state` | list[str] | 129 | OK例 | 既定は「工程の確認項目をすべて満たしている」 |
| `ng_state` | list[str] | 129 | NG例 | 未指定なら `[warning]` |
| `normal_state` | list[str] | 12 | OK例 | `ok_state` の旧名。`ok_state` が優先 |
| `ok_images` / `ng_images` | list[obj] | 各31 | OK例／NG例の直下 | |
| `abnormal_action` | str | 31 | 「異常時」枠 | `warning` がある工程では表示されない |
| `current_status` | str | 33 | 「現在の状況」 | 工程冒頭の `st.info` |
| `check_help` | dict | 15 | 確認項目の直下 | `{確認項目の文言: 補足文}`。文言の**完全一致**で引く |
| `glossary` | dict | 10 | 「用語解説」 | `{用語: 説明}`。折りたたみ |
| `branches` | list[obj] | 8 | 「進め方を選ぶ」 | 下記「5. 分岐」を参照 |
| `branch_guidance` | str | 8 | 分岐の選択肢の上 | |
| `operation_steps` | list[str] | 8 | 「操作を順番に確認」 | 自動で連番が付く |
| `notice` | str | 6 | `st.warning` | 確認項目の後 |
| `user_note` | bool | 2 | 「利用者メモ（任意）」 | `true` で自由記述欄を表示 |
| `show_signal_figure` | bool | 2 | 「実画面」に `signal.png` を追加 | |
| `show_compensation_figure` | bool | 2 | 「実画面」に補正前後の2図を追加 | |
| `reference` | str | 81 | **描画されない** | 参照したマニュアルの箇所を残す記録用 |
| `section_heading` | str | 2 | **描画されない** | どこからも参照されていない |

`app.py` 側には `pre_branch_title`、`pre_branch_text`、`pre_branch_images` を分岐の手前に描く処理もありますが、現行データでは未使用です。

### 画像オブジェクト

`screen_images`、`ok_images`、`ng_images` の要素です。

```json
{ "filename": "dgs_manual_p4.png", "title": "SAMPLEダイヤルを設定する", "caption": "", "hide_title": false }
```

`filename` は `images/` 直下からの相対名です。**ファイルが無くてもエラーにはならず**、「imagesフォルダへ配置してください」というプレースホルダーが表示されます。`show_screen_section` が真で `screen_images` が空の場合は、`{工程ID}.png` を探しにいきます。

## 4. 既定値の連鎖

未指定時に別のキーへ委譲する箇所があります。文言を1か所直したつもりが別の枠にも影響することがあるため、把握しておく必要があります。

- 「やること」= `task` → `instruction`
- OK例 = `ok_state` → `normal_state` → 既定文
- NG例 = `ng_state` → `[warning]` → 既定文
- 異常時 = `warning` → `abnormal_action` → `contact`（トップレベル）
- 異常時の本文に連絡先メールアドレスが含まれない場合、`contact` が自動で末尾へ追記される

`warning` は「NG例」と「異常時」の両方の既定値を兼ねているため、`warning` だけを持つ工程では同じ文言が2か所に出ます。

## 5. 分岐（`branches`）

```json
{
  "value": "reagent_on",
  "label": "REAGENTを使用する",
  "instruction": "REAGENTダイヤルを長押しして有効化し、…",
  "checks": ["REAGENTダイヤルを長押しして有効化した", "…"]
}
```

`value` と `label` は全分岐にあり、残りは工程のキーを上書きする形で任意に指定します。現行データでは `task`、`warning`、`notice`、`checks`、`operation_steps`、`operation_groups`、`screen_images`、`ok_state`、`ng_state`、`show_screen_section`、`show_checks_after_operations` が使われています。

選択されると `active = {**step, **branch}` としてマージされ、**以降の描画はすべて `active` を参照** します。工程そのもの（`step`）を参照し続けるのは、工程ID、タイトル、スキップ、`current_status`、`pre_branch_*` だけです。

分岐のある工程では、選択が変わったときに `clear_step_widgets(step_id, keep_branch=True)` で配下のウィジェットを破棄します。これを怠ると前の選択のチェック状態が残ります。未選択の間は「次へ」が押せません。

## 6. 操作と確認の優先順位

チェックボックスは3系統あり、次の規則で描き分けます。

1. `operation_groups` があれば、グループごとに見出しを付けて通し番号のチェックを出す
2. なければ `operation_steps` を「操作を順番に確認」として連番で出す
3. `checks` は、**操作系がどちらも無い場合**、または `show_checks_after_operations` が真の場合にだけ「次へ進む前の確認」として出す
4. 3系統すべてが空の工程は、確認なしで次へ進める

つまり `operation_steps` と `checks` を両方書くと、既定では `checks` が表示されません。両方出したい場合は `show_checks_after_operations: true` が必要です。

チェックボックスのキーは `{工程ID}_{分岐value|default}_op_{連番}` と `{工程ID}_{分岐value|default}_check_{連番}` です。**連番は配列の位置** なので、確認項目の順序を入れ替えるとセッション中のチェック状態が別の項目へ移ります。

## 7. 描画順序

`render_guide()` が1工程を描く順序です。

1. コース名（`label`）と説明（`description`）
2. `Step N / M` と `title`、右に「この工程をスキップ」
3. `current_status` →「現在の状況」
4. `pre_branch_*`（現行データでは未使用）
5. `branches` →「進め方を選ぶ」。選択すると `instruction` を `st.info` で表示
6. `task` →「やること」
7. JointAIボタンとパネル
8. `operation_groups` / `operation_steps` / `checks`
9. `notice` → `st.warning`
10. `user_note` → メモ欄
11. `why` / `decision_support` / `glossary` の3つの折りたたみ
12. 「実画面」（`screen_images` ほか）
13. 「OK例」「NG例」「異常時」
14. 「← 前へ」「この工程を完了して次へ →」

## 8. `app.py` が工程IDを直接見ている箇所

汎用の描画処理の中に、特定の工程IDへの分岐が5か所あります。**工程IDを変更・削除するときはここも確認が必要です。**

| 場所 | 対象 | 内容 |
| --- | --- | --- |
| `current_workflow_steps()` | `a11`、`a10` | No.370。Selector選択時に `a11` を `a10` の直後へ移動 |
| `current_workflow_steps()` | `a04` | No.367。Selector選択時に `a04` の直後へブランク工程を挿入 |
| `render_guide()` | `a08` | Selector選択時、分岐の `value` の接頭辞（`emulsion_` / `gmd_`）に応じて継ぎ足しカップの確認項目を追加 |
| `render_guide()` | `a03` | `analysis` / `sorting` のとき「アカウントの設定方法」リンクを併記 |
| `render_guide()` | 確認項目の文言 | `SampleとOilを準備した` に一致する項目の直下へOil調製の注釈を出す |

最後の1つは工程IDではなく **確認項目の文言との完全一致** で動くため、この文言を変更すると注釈が消えます。

## 9. コースを追加する手順

### 9.1 JSONへコースを追加する

`workflows` へコースキーを足し、`label`、`description`、`steps` を書きます。工程IDは他コースと重複しない接頭辞を付けます（例：`dgs_a_wo_00`）。

### 9.2 `app.py` に入口を配線する

`DATA["workflows"]` は現在の1コースを引くためだけに使われており、全コースを走査している箇所がありません。コース開始も次の3か所しかなく、いずれも遷移先が固定です。

```
app.py:1601  start_workflow(workflow_map[(dg_chip, dg_product)])   # ドロップレット作製の8コース
app.py:1650  start_workflow("analysis")                            # On-chip Sort
app.py:1693  start_workflow(workflow)                              # Selector（分注なら sorting、バルクなら analysis）
```

ドロップレット作製へ流路チップを1つ増やす場合、`render_dg_setup()` の次の3か所に追記します。

| 場所 | 追記内容 |
| --- | --- |
| `chip_options`（app.py:1482） | `("新チップの値", "画面に出す名称")` |
| `chip_labels`（app.py:1507） | 選択内容の要約に出す名称 |
| `workflow_map`（app.py:1584） | `("新チップの値", "wo")` → 新コースキー |

作りたいものが `wo` / `gmd` 以外になる場合は、③の選択ボタン（app.py:1541以降。`dg_select_product_wo` / `dg_select_product_gmd` の2つが直接書かれています）と `product_labels`（app.py:1566）にも追記が必要です。**新しい装置カテゴリを足す場合**は、DG-Sを追加したときのように、②の選択ステップ自体を装置ごとに分岐させる必要があります（`render_dg_setup()` の `if st.session_state.dg_device == "generator":` 以下）。

### 9.3 画像を配置する

工程が参照するファイル名で `images/` 直下へ置きます。未配置でもアプリは動作し、該当箇所にプレースホルダーが出ます。

### 9.4 確認する

```bash
python -c "import json; json.load(open('data/manual_steps.json', encoding='utf-8'))"
```

全コース・全工程・全分岐を描画して例外が出ないことは、疑似Streamlitで確認できます。

```python
from streamlit.testing.v1 import AppTest
at = AppTest.from_file('app.py', default_timeout=120)
at.session_state['page'] = 'guide'
at.session_state['workflow_key'] = '新コースキー'
at.session_state['step_index'] = 0
at.run()
assert not at.exception
```

追加後は工程数の合計を数え直し、[CHANGELOG.md](../CHANGELOG.md) と [README.md](../README.md) の「収録している工程」を更新します。

## 10. 補足：測定結果ページとの違い

同じ「表示するコンテンツ」でも、「測定結果を確認する」のSTEP 1〜8は工程データと異なり、本文が `app.py` の `render_result_step1()` 〜 `render_result_step8()` に直接書かれています（合計493行）。`RESULT_PAGES`（app.py:2373）が持つのは見出しとキーだけです。文言修正のたびに `app.py` の変更が必要になるため、将来のデータ化の候補ですが、各STEPが図版の挿入位置や独自レイアウトを持つため、工程データとは別のスキーマ設計が要ります。
