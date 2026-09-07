# 実験条件検討 有料オプション（開発プレビュー）

このディレクトリは、標準の実験ナビ本体から切り離せる有料オプションです。

## 分離ルール

- コアの `manual_steps.json` に本プラグイン固有の工程や入力項目を追加しません。
- 既存の進行状況保存（`PROGRESS_SCHEMA_VERSION=1`）へ、プラグイン入力を混在させません。
- コアコードからこのパッケージを直接 import しません。`core/feature_registry.py` が `plugin_manifest.json` を読み、実行時に entrypoint をロードします。
- プラグイン固有のPDF依存関係は `optional_requirements/experiment_condition_advisor.txt` に分離します。
- `plugins/experiment_condition_advisor/` と専用optional requirementsを削除しても、標準アプリが起動することを必須条件とします。
- 製品一覧との連携は `core/product_catalog.py` の公開関数を介し、製品一覧ページの表示処理へ直接依存しません。

## 現在のAI扱い

外部AIや外部送信は実装していません。現在は承認済み文献メタデータ、入力検証、物理計算、明示的なルールを使う「閉域見解エンジン（ルールベース試作）」です。

表示する「成立見込み」は成功率の保証ではありません。圧力、流量、界面活性剤濃度など、製品マニュアルまたは社内検証データにない具体値は生成しません。

## 配布状態の切り替え

`config/features.json` の `experiment_condition_advisor` を変更します。

- `development_preview`: 開発プレビューとして利用可能
- `licensed`: ライセンス済みとして利用可能
- `unlicensed`: 搭載済み・未契約表示
- `disabled`: 無効

環境変数 `ONCHIP_EXPERIMENT_CONDITION_ADVISOR_MODE` でも上書きできます。
