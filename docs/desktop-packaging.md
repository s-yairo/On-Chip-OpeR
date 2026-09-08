# デスクトップアプリ化の検討

Streamlit製の本アプリをデスクトップアプリとして配布できるかの検討メモです。

**現時点では方式を決定していません。** ライセンス上の可否と、変換前に直しておく必要がある箇所を記録するための文書です。

- 調査日：2026年9月8日
- 調査環境：Python 3.12.10 / streamlit 1.63.0 / reportlab 4.5.1

## 1. ライセンス上の可否

### 結論

**変換・配布を妨げる条項はありません。** Streamlit は Apache License 2.0 で、商用利用、改変、再配布、クローズドソース製品への組み込みが認められています。コピーレフトではないため、`app.py` 以下の自社コードを公開する義務も生じません。

ただし本メモは法務の専門判断ではありません。製品として出荷する前に社内での確認を通してください。

### 満たすべき条件

Apache License 2.0 の再頒布条件です。

- ライセンス本文の写しを配布物へ同梱する
- 著作権表示、特許表示、商標表示、帰属表示を保持する
- 配布物に `NOTICE` ファイルが含まれる場合、その内容を読める形で引き継ぐ
- 改変したファイルには、変更した旨を目立つ形で記載する
- Streamlit の名称・ロゴを、製品名や「推奨されている」ことを示す用途に使わない

実務上は、オープンソースライセンスの一覧画面かテキストファイルを同梱する形になります。

### 依存関係のライセンス

調査時点で本アプリの依存ツリーに含まれるものです。**GPL／LGPL は含まれていません。**

| 種別 | パッケージ |
| --- | --- |
| Apache-2.0 | streamlit, pyarrow, pydeck, requests, watchdog, python-multipart |
| BSD系 | altair, click, numpy, pandas, protobuf, starlette, uvicorn, websockets, itsdangerous, reportlab |
| MIT系 | anyio, httptools, toml, pillow（MIT-CMU） |
| PSF | matplotlib, typing-extensions |

環境全体を走査すると `WSDiscovery`（LGPLv3+）と `hidapi`（GPLv3）が検出されますが、いずれも本アプリの依存ツリー外で、同じ環境に入っていた別作業由来のものです。

### 棚卸しの方法

配布物を作る段階では、**クリーンな仮想環境で改めて確認してください。** 開発機の環境には無関係なパッケージが混ざります。

```python
# 依存ツリーの宣言ライセンスを一覧する
import importlib.metadata as m
import re

def short(p):
    try:
        md = m.metadata(p)
    except Exception:
        return "(未インストール)"
    v = md.get("License-Expression")
    if v:
        return v.strip()
    cl = [c.split("::")[-1].strip()
          for c in (md.get_all("Classifier") or []) if c.startswith("License")]
    if cl:
        return "; ".join(cl)
    lic = (md.get("License") or "").strip().splitlines()
    return lic[0][:70] if lic else "(記載なし)"

reqs = m.metadata("streamlit").get_all("Requires-Dist") or []
for n in sorted({re.split(r"[\s<>=!;\[(]", r.strip())[0] for r in reqs}):
    print(f"{n:24} {short(n)}")
```

```python
# 環境内にGPL系の宣言が無いか走査する
import importlib.metadata as m

for d in m.distributions():
    name = d.metadata.get("Name")
    fields = [d.metadata.get("License-Expression") or ""]
    fields += [c for c in (d.metadata.get_all("Classifier") or []) if c.startswith("License")]
    if "GPL" in " ".join(fields).upper():
        print(name, fields)
```

`License` フィールドにライセンス本文全体を入れている配布物（numpy など）があるため、`License-Expression` と分類子を優先して読むほうが実用的です。

## 2. 変換方式の選択肢

現状の `launch.bat` が既に「ローカルでサーバを起動してブラウザで開く」構成のため、実質は外側のシェルを付け替える作業になります。

| 方式 | 概要 | 所見 |
| --- | --- | --- |
| ランチャー配布 | Python同梱の起動exeがサーバを立ててブラウザを開く | 最も確実。見た目はブラウザのまま |
| WebViewシェル | pywebview / Electron / Tauri で `localhost` を専用ウィンドウに表示 | アプリらしい外観になる。実装量は中程度 |
| 単一exe化（PyInstaller等） | 実行ファイルへ固める | Streamlitは `streamlit run` 前提の起動処理と静的アセットを持つため、`streamlit.web.bootstrap` を直接呼び、データファイルを明示的に同梱する調整が必要 |
| stlite（Pyodide）+ Electron | Pythonをブラウザ内で動かしサーバを不要にする | サーバレスにできる反面、ReportLab など純Python以外の依存が動作するかの検証が必要。**未検証** |

装置の横で1人が使うという本アプリの性質からは、WebViewシェルが素直と考えられます（判断であり、検証結果ではありません）。

## 3. 変換前に直す必要がある箇所

### 書き込み先がアプリ本体のディレクトリになっている

```
app.py:36  EXPERIMENT_RECORDS_PATH           = BASE_DIR / "data" / "experiment_records.json"
app.py:37  EXPERIMENT_RECORD_ATTACHMENTS_DIR = BASE_DIR / "data" / "experiment_record_attachments"
```

`BASE_DIR` は `Path(__file__).parent` です。手元のフォルダで実行している限り問題ありませんが、インストーラで `C:\Program Files\` 配下へ配置すると **実験記録の保存が権限エラーで失敗します**。

デスクトップ化するなら、書き込み系のパスだけを `%LOCALAPPDATA%` などのユーザー領域へ逃がす必要があります。読み取り専用の `data/manual_steps.json`、`data/product_catalog.json`、`data/glossary.json`、`images/`、`config/` は本体側のままで構いません。

なお `_save_experiment_condition_report()` は添付ファイルの保存先を `BASE_DIR` からの相対パスとして記録し（app.py:3241）、読み出し時に `BASE_DIR` を基準に解決したうえで添付ディレクトリ配下かを検証しています（app.py:3253-3254）。保存先を移す場合は、この基準ディレクトリの扱いもあわせて変更する必要があります。

## 4. 確認が必要な点

| 項目 | 内容 |
| --- | --- |
| ポート競合 | Streamlitは既定で 8501 を使う。使用中の場合に別ポートを選ぶ処理が要る |
| ダウンロード | `st.download_button` が実験条件検討に2か所（入力JSON、レポートPDF）。WebViewシェルは既定でダウンロードを受け取れないため、保存ダイアログのハンドラ登録が必要 |
| ファイル選択 | `st.file_uploader` が3か所（app.py:1219 JointAI参考資料、app.py:1768 JointAIパネル、app.py:3316 実験条件検討レポートの添付）。シェル側の対応が要る |
| 起動時間 | サーバ起動に数秒かかる。スプラッシュ表示の有無で体感が変わる |
| 埋め込みJS | 用語集ホバー（`apply_glossary_hover`）が `components.html` から `window.parent` を操作する。WebViewも通常のブラウザ同等のため、そのまま動作する見込み |
| Pythonランタイム | 同梱方式（embeddable package、venv同梱、PyInstallerのバンドル）を決める必要がある |

## 5. 未決定事項

- 変換方式
- 書き込み領域の移設先と、既存データの移行有無
- インストーラの要否（zip配布で足りるか）
- オープンソースライセンス表示の置き場所（アプリ内画面か同梱テキストか）
