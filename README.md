# SnapShot

ファイルを簡易的にアップロード・ダウンロードするためのサーバー

## 概要

https://snapshot.amania.jp で使用しているサーバーです
アップロードされたファイルは暗号化されデータベース上に保存されます

ダウンロードキーとアップロードキーで使用する API キーが分かれており アプリ内にアップロードキーを書いてもし流出しても サーバーの容量が終わるだけで済みます

## 使用方法

uv を使用することを推奨します

```sh
uv venv
uv pip install -r requeriments.txt

python main.py
```

## API Docs

#### ユーザー登録

```
POST /register
```

-   説明: 新しいユーザーを登録します
-   パラメータ: `username` (JSON), `password` (JSON)
-   レスポンス: API キー

#### ファイルアップロード

```
POST /upload
```

-   説明: ファイルをアップロードします
-   パラメータ: `file` (multipart/form-data), `api_key` (ヘッダー)
-   レスポンス: アップロードキー

#### ファイルダウンロード

```
GET /download/{key}
```

-   説明: ダウンロードキーでファイルを取得します
-   パラメータ: `key` (パス), `api_key` (ヘッダー)
-   レスポンス: ファイルデータ

#### ファイル一覧取得

```
GET /files
```

-   説明: アップロード済みファイルの一覧を取得します
-   パラメータ: `api_key` (ヘッダー)
-   レスポンス: ファイル情報リスト

詳細な仕様やリクエスト例はソースコードを参照してください。

### LICENSE

<a href="https://amania.jp">SnapShot</a> © 2025 by <a href="https://amania.jp/about">amania</a> is licensed under <a href="https://creativecommons.org/licenses/by-nc-sa/4.0/">CC BY-NC-SA 4.0</a>
