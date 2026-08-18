---
icon: lucide/rocket
---

# クイックスタート

ここでは、`examples/` ディレクトリ内の例を実行し、Romi を制御する手順について説明します。

## 準備

- Romi Lacatan
    - インターネットに接続されていること
    - SDK を実行するデバイスと同じ LAN に接続されていること
    - 最新のファームウェアをインストールしていること
        - インターネットに接続された状態で電源が入っていれば、自動で最新のファームウェアがインストールされます
    - 会話モデルが ChatRomi2.0 であること
        - 現時点で、ChatRomi1.0 は SDK 非対応です
- SDK を用いたプログラムを実行するデバイス
    - Python を実行可能なこと
    - インターネットに接続されていること
    - 制御対象の Romi Lacatan と同じ LAN に接続されていること
- [uv](https://docs.astral.sh/uv/)
    - 適切なバージョンの Python と依存パッケージのインストールに用います
    - SDK 実行デバイスにインストールしてください

## 1. Romi の SDK モード有効化

1. [開発者向けコンソール](https://developers.romi.ai/console/romi) にアクセスし、ログイン
2. `Romiの管理` 画面から、対象の Romi の `SDK有効化` ボタンを押下
3. Romi が再起動するのでしばらく待つ
    - 更新ボタンで状態を更新しつつ、`SDK Mode` が `Enabled` になるのを待ってください
    - Romi が起動後、1分以内には `Enabled` となるはずです
4. `Romi ID` と `mDNS Host Name` が表示されるのでそれぞれコピーする（後ほど使います）

!!! important
    Romi を再起動すると SDK モードは無効化されます。再度利用する際は、
    この手順を最初からやり直して SDK モードを有効化してください。

## 2. SDK 証明書の準備

SDK と Romi の通信には TLS クライアント証明書が必要です。
クライアント証明書は開発者向けコンソールから取得できます。

### CSR（証明書署名要求）の生成

適当な作業ディレクトリで以下のスクリプトを作成・実行し、秘密鍵と CSR を生成します。

```bash
#!/usr/bin/env bash
set -euo pipefail

if [ $# -ne 1 ]; then
  echo "Usage: $0 <client_ID>" >&2
  exit 1
fi

client_ID="$1"
key_file="client.key"
csr_file="client.csr"

# Generate RSA private key
openssl genrsa -out "${key_file}" 2048

# Generate CSR
openssl req -new \
  -key "${key_file}" \
  -out "${csr_file}" \
  -subj "/CN=${client_ID}" \
  -addext "subjectAltName=DNS:${client_ID}"

echo ""
echo "=== CSR generated: ${csr_file} ==="
```

```bash
chmod +x generate-client-csr.sh
./generate-client-csr.sh <任意のSDK ID>
```

### 証明書の発行

1. 開発者向けコンソールの `証明書発行` 画面で、`ファイルから読み込み` から `client.csr` を選択
2. `証明書を発行` ボタンを押下
3. クライアント証明書（`client.crt`）と CA 証明書チェーン（`ca.crt`）をダウンロード
4. 作業ディレクトリに配置

最終的に以下の 3 ファイルが揃っていることを確認してください。

```text
certs/
├── ca.crt        # CA 証明書チェーン
├── client.crt    # クライアント証明書
└── client.key    # 秘密鍵
```

## 3. セットアップ

```bash
git clone https://github.com/mixi-romi/romicore-sdk-py.git
cd romicore-sdk-py
uv sync
```

`uv sync` により仮想環境（`.venv`）が作成され、SDK と依存パッケージがインストールされます。
必要があれば適切なバージョンの Python もインストールされます。

## 4. サンプルの実行

`examples/` ディレクトリにサンプルスクリプトがあります。
ここでは `examples/tool_calling.py` を実行する例を示します。
他の例も同様に実行できます。

まず、スクリプト冒頭の定数を自分の環境に合わせて編集してください。

```python
HOST = "<mDNS host name>"           # 手順1でコピーした .local で終わるホスト名
BROKER_PORT = 443
TARGET_ROMI_ID = "<Romi ID>"        # 手順1でコピーした Romi ID
CERTS_PATH = "<Path to certs dir>"  # client.key, client.crt, ca.crt があるパス
```

その後、以下のコマンドで実行できます。

```bash
uv run examples/tool_calling.py
```

## 5. 証明書の更新

!!! warning
    デバイス証明書の期限は7日間です。
    証明書の期限切れを防ぐため、期限が近づいたら以下の方法で証明書を更新してください。

一度 Romi への接続が成功した後は、デバイス証明書を Romi 経由で更新することができます。
更新方法については `examples/refresh_sdk_device_certificate.py` を参照してください。
