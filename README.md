# On-Chip OpeR

AI×オペレーティングシステムによる対話型実行支援システム。

On-chip Biotechnologies 社のマイクロ流路デバイスとフローサイトメーターの操作を、画面上で1工程ずつ案内する Streamlit 製の実験ナビゲーションアプリです。

## 概要

On-chipデバイスやフローサイトメーターに慣れていない人でも、装置を使いこなせるようにすることを目的としています。

- **目的から始める** — トップページで「何をしたいか」を選ぶと、装置・流路チップ・作製物の選択を経て、該当するマニュアルに沿った工程へ進みます
- **1工程ずつ案内する** — 各工程は「やること」「確認項目」「OK例／NG例」「異常時の対応」で構成され、確認項目にすべてチェックを入れるまで次の工程へ進めません
- **根拠を示す** — 「なぜこの操作を行うのですか？」「判断の目安」「用語解説」を工程ごとに開けます。参照したマニュアルの該当箇所も各工程に記載しています
- **施設SOPを優先する** — ナビの内容と施設SOPが異なる場合は施設SOPに従う前提で案内します。マニュアルや社内検証データにない圧力・流量・濃度などの具体値は表示しません
- **閉域で動く** — 外部ネットワークへ接続しません。AI機能（JointAI）もすべて `core/ai/AIConnector` を経由し、現在は固定応答を返すダミー接続のみが有効です
- 画面表示・データ・ドキュメントはすべて日本語です

## 主な機能

トップページには6つのエントリーがあります。

| エントリー | 内容 | 状態 |
| --- | --- | --- |
| ドロップレットを作る | W/Oドロップレット・ゲルマイクロドロップ（GMD）の作製工程 | 利用可能 |
| ソーティング・分注を行う | サンプルの解析・分離・分注の工程 | 利用可能 |
| ドロップレットから取り出す | サンプルの解放（On-chip Merge／On-chip Droplet Dispenser） | 利用不可 |
| 実験条件検討 | 実験目的・封入対象・培地・目標液滴・後工程から見解とPDFを作成 | 利用可能 |
| 測定結果を確認する | フローサイトメーターの原理とプロットの見方をSTEP 1〜STEP 8で解説 | 利用可能 |
| トラブルを解決する | 症状から確認項目と対応候補を探す | 利用可能 |

このほか、サイドバーから製品一覧、用語集、実験記録を利用できます。

### 収録している工程

| コース | 対応装置・流路 | 工程数 |
| --- | --- | ---: |
| `analysis` ソーティングを行う | On-chip Sort／Selectorのバルクソーティング | 12 |
| `sorting` ソーティング・分注を行う | On-chip Droplet Selectorの分離・分注 | 21 |
| `dg800_wo` | Droplet Generator／2D Chip-800DG／W/O | 17 |
| `dg800_gmd` | Droplet Generator／2D Chip-800DG／GMD | 26 |
| `dg1060_1100_wo` | Droplet Generator／2D Chip-1060DG or 1100DG／W/O | 17 |
| `dg1060_1100_gmd` | Droplet Generator／2D Chip-1060DG or 1100DG／GMD | 28 |
| `dgs_a_wo` | Droplet Generator S／2液混合 Chip Holder（35〜45 µm）／W/O | 12 |
| `dgs_a_gmd` | Droplet Generator S／2液混合 Chip Holder（35〜45 µm）／GMD | 23 |
| `dgs_b_wo` | Droplet Generator S／DG1 Chip Holder（60〜120 µm）／W/O | 12 |
| `dgs_b_gmd` | Droplet Generator S／DG1 Chip Holder（60〜120 µm）／GMD | 23 |

基本工程データは全10コース・合計191工程です。On-chip Droplet Selectorを選択した場合は実行時に工程構成が変わるため、画面に表示される工程数はこの表と一致しません。

そのほかの収録データは、確認項目735件（工程直下645件、分岐内90件）、製品71件、用語集319語・8分野、トラブル案内13項目です。

## 動作環境

- Python 3.12（動作確認環境）
- Streamlit 1.36 以上 2 未満
- ブラウザ（Streamlitが起動時に開きます）

## インストール方法

```bash
git clone <repository-url>
cd on-chip-oper
```

仮想環境を使う場合は、先に作成して有効化します。

```bash
python -m venv .venv
```

有効化のコマンドは環境ごとに異なります。Windowsのコマンドプロンプトでは `.venv\Scripts\activate`、PowerShellでは `.venv\Scripts\Activate.ps1`、macOS・Linuxでは `source .venv/bin/activate` を実行します。

依存関係をインストールします。PDF出力に使う ReportLab を含め、必要なものは `requirements.txt` にまとまっています。

```bash
pip install -r requirements.txt
```

## 起動方法

```bash
streamlit run app.py
```

ブラウザが自動で開かない場合は、ターミナルに表示される `http://localhost:8501` を開いてください。停止するときはターミナルで `Ctrl+C` を押します。

Windowsでは `launch.bat` をダブルクリックしても起動できます。依存関係のインストールと起動をまとめて実行します。

## 設定

`config/features.json` でAI機能（JointAI）の状態を切り替えます。

```json
{
  "features": {
    "joint_ai": { "enabled": true, "mode": "dummy", "provider": "dummy" }
  }
}
```

`provider` に指定できるのは現在 `dummy` だけです。ダミー接続はネットワークへアクセスせず、固定の応答を返します。`enabled` を `false` にすると、画面からJointAIの入口が消えます。

## リポジトリ構成

```
app.py                          画面とルーティング（単一のエントリポイント）
config/features.json            機能の有効・無効設定
core/
  ai/                           AI呼び出しの単一窓口（AIConnector とプロバイダー）
  experiment_condition_advisor/ 実験条件検討
  experiment_records.py         実験記録の読み書き
  product_catalog.py            製品一覧の検索・絞り込み
data/
  manual_steps.json             全コースの工程データ
  product_catalog.json          製品一覧
  glossary.json                 用語集
  experiment_records.json       実験記録の保存先
images/                         工程の画面画像・解説図（products/ は製品画像）
```

工程の追加・変更は `data/manual_steps.json` で行い、`app.py` には工程内容を書きません。

## データの扱い

- 工程位置、確認項目のチェック、分岐の選択、メモ、観察履歴は、アプリを開いている Streamlit セッション内だけで保持します。進行状況を外部ファイルへ保存・再開する機能はありません
- 実験記録だけは `data/experiment_records.json` へ保存します。添付ファイルは `data/experiment_record_attachments/` に置かれます
- いずれのデータも外部へ送信しません

## 画面仕様の維持事項

- トップページは6カードを3列×2段で表示し、デスクトップでは同じ高さにそろえる
- 「ドロップレットから取り出す」以外の5カードに「利用可能」バッジ、当該カードには「利用不可」バッジを表示する
- トップカードの表題とブラウザータブに装飾用の絵文字を使わない
- 「測定結果を確認する」はSTEP 1〜STEP 8をそれぞれ独立した単独ページで表示し、項目一覧は4列×2段の8ボタンとする
- 各単独ページの下部に「前の項目」「項目一覧へ戻る」「次の項目」を置く
- マニュアル由来の説明と、一般的なFACSの補足説明を表示上で区別する
- 「トラブルを解決する」は既存6項目と公式サポート案内7項目の合計13項目とし、公式サポート案内では資料にない独自の対処手順を表示せず、株式会社オンチップ・バイオテクノロジーズの該当記事へ案内する
- 共通連絡文は「上記以外で装置の異常があった際は、保守（tech@on-chip.co.jp）へご連絡ください。」とする

## 参照資料

- On-chip Droplet Selector ユーザーマニュアル Ver. 1.0.4
- On-chip Droplet Generator 2D Chip-800DG用マニュアル Ver. 1.3.0S
- On-chip Droplet Generator 2D Chip-1060DG用マニュアル Ver. 2.0.0S
- ドロップレットジェネレータ S ユーザーマニュアル Document Version 2.0.0
- GMD作製プロトコル（アガロース）
- 株式会社オンチップ・バイオテクノロジーズ「サポート ＞ トラブルシューティング」

## 変更履歴

過去の変更内容は [CHANGELOG.md](CHANGELOG.md) を参照してください。
