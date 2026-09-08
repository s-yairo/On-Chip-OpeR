# 内部仕様ドキュメント

On-Chip OpeR の内部構造を記録するディレクトリです。コードを読まなくても構造を把握できること、および過去に採用して取りやめた設計の理由を残すことを目的にしています。

## 収録している文書

| ファイル | 内容 |
| --- | --- |
| [workflow-data.md](workflow-data.md) | `data/manual_steps.json` の工程データ仕様、描画順序、`app.py` との結合点、コースを追加する手順 |
| [plugin-architecture.md](plugin-architecture.md) | 有料オプションプラグイン機構（`plugins/`、`optional_requirements/`、`core/feature_registry.py`）の仕様と、No.378でメインプログラムへ統合するまでの経緯 |
| [desktop-packaging.md](desktop-packaging.md) | デスクトップアプリ化の検討メモ。ライセンス上の可否、変換方式の選択肢、変換前に直す必要がある箇所（**方式は未決定**） |

## 記載方針

- 実装から確認できる事実を書き、推測は「推測」と明記する
- 決定前の検討も残す。その場合は冒頭に未決定である旨と調査日を書く
- 廃止・置換した仕組みは、削除せず「現在の扱い」を追記して残す。後から同じ設計を再検討するときの判断材料にするため
- 利用者向けの説明は [README.md](../README.md)、変更の時系列は [CHANGELOG.md](../CHANGELOG.md)、作業時の規約は [CLAUDE.md](../CLAUDE.md) に置き、この配下では内部構造だけを扱う
