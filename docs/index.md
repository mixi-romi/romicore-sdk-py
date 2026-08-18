---
icon: lucide/book-open
---

# RomiCore Python SDK

MIXI が開発した会話 AI ロボット「Romi」を Python から制御するための SDK です。
現在ベータ版として開発中です。ベータ版の期間、後方互換性は保証されないことをご留意ください。

!!! important
    SDK モードが有効な間、Romi の画面右下に SDK アイコン（歯車とスパナ）が表示されます。
    Romi が SDK から制御されている状態であることを、この表示で確認できます。

!!! important
    SDK 利用にはデイリーのレートリミットがあります。
    レートリミットは毎日深夜 0:05 (JST) ごろにリセットされます。

## SDK でできること

- **ツール呼び出し（Tool Calling）** — 独自の処理を、Romi の会話から呼び出せるツールとして登録する
- **発話** — テキストと感情を指定して Romi に発話させる
- **応答生成** — 会話モデルに応答を生成させ、そのまま発話させる
- **会話ストリームの購読** — 会話の進行をリアルタイムに受け取る
- **リソース URL 要求への応答** — Romi からのリソース取得要求に応答する
- **証明書の更新** — SDK デバイス証明書を Romi 経由で更新する

## 次のステップ

- [クイックスタート](quickstart.md) — セットアップから最初のサンプル実行まで
- [API リファレンス](api_spec.md) — クラス・メソッドの詳細仕様

## SDK を使わない場合

SDK を用いず直接 MQTT 通信を行うことも可能です。
MQTT API については [AsyncAPI 仕様](https://mixi-romi.github.io/romicore-sdk-asyncapi/) を参照してください。

## リポジトリ

ソースコードは [GitHub リポジトリ](https://github.com/mixi-romi/romicore-sdk-py) で公開しています。
