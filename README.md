# RomiCore Python SDK

MIXI が作る [会話 AI ロボット "Romi"](https://romi.ai/) を制御するための Python SDK です。
現在ベータ版として開発中です！ベータ版の期間、後方互換性は保証されないことをご留意ください。

## ドキュメント

セットアップから API 仕様まで、[ドキュメントサイト](https://mixi-romi.github.io/romicore-sdk-py/) にまとめています。

- [クイックスタート](https://mixi-romi.github.io/romicore-sdk-py/quickstart/) — SDK モードの有効化、証明書の準備、サンプルの実行まで
- [API リファレンス](https://mixi-romi.github.io/romicore-sdk-py/api_spec/) — クラス・メソッドの仕様
- [MQTT API 仕様 (AsyncAPI)](https://mixi-romi.github.io/romicore-sdk-asyncapi/) — SDK を使わず直接 MQTT 通信する場合

> [!IMPORTANT]
> SDK 利用にはデイリーのレートリミットがあります。
> レートリミットは毎日深夜 0:05 (JST) ごろにリセットされます。

## ライブラリ開発

### ブランチ戦略

本レポジトリは Trunk Based Development によるブランチ戦略を採用しています。

- `main` は常に動作する状態（CI が通る状態）を保ちます
- 機能追加・修正は短命なブランチで行い、Pull Request 経由で `main` にマージしてください
- `main` への直接 push は想定していません

### 開発環境の準備

このプロジェクトではパッケージ管理およびビルドツールとして `uv` を使用します。

#### uv のインストール

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

#### プロジェクトのセットアップ

```bash
cd romicore-sdk-py
uv sync
```

#### テストの実行

```bash
uv run pytest
```

#### 依存パッケージの追加

```bash
uv add <package_name>
```

#### ビルド

配布用パッケージを作成します。
実行後、`dist/` ディレクトリに `.whl` と `.tar.gz` が生成されます。

```bash
uv build
```

#### ドキュメントのビルド

`docs/` の変更は [Zensical](https://zensical.org/) でビルドできます。

```bash
uv run zensical build --strict
```

ローカルサーバーで確認する場合は以下を使用してください。

```bash
uv run zensical serve
```

### AsyncAPI ドキュメント

RomiCore SDK の MQTT API 仕様は AsyncAPI ドキュメントとして公開しています。

- 公開ドキュメントサイト: <https://mixi-romi.github.io/romicore-sdk-asyncapi/>
- 生成元リポジトリ: <https://github.com/mixi-romi/romicore-sdk-asyncapi>

上記リポジトリは、本レポジトリを参照して AsyncAPI 仕様書（`asyncapi.yml`）とドキュメントサイトのビルドを行います。

#### JSON Schema 生成

以下のコマンドで AsyncAPI 仕様の元となる JSON Schema を生成できます。

```bash
uv run ./tools/generate_json_schema.py
```

生成された `./schemas` は、SDK の payload 定義が変わると CI により `romicore-sdk-asyncapi` へ自動反映され、AsyncAPI ドキュメントが再生成されます。通常この手順を手動で実行する必要はありません。
