# 全自治体 障害情報モニター

全国 **1,741 自治体（＋政令市の行政区175、計1,916サイト）** の公式HPを毎日巡回し、
**システム障害・メンテナンス情報の新着分だけ**を抽出して、毎朝 8:00 頃にメールで届ける仕組み。

## 何をするか

1. 全自治体の公式HP（オープンデータ `code4fukui/localgovjp` 由来）を並列巡回
2. トップページ＋「お知らせ/新着情報」一覧（1階層）から、
   **システム障害・メンテナンス系のリンク**だけをキーワード判定で抽出
   - 「障害者福祉」「ごみ受け入れ停止」「道路通行止め」などは**誤検知として除外**
3. 前日までの既知分と照合し、**新規・更新分のみ**をまとめる
4. Gmail でHTMLダイジェストを送信（新着ゼロの日も「新規なし」を通知）

## ファイル構成

| ファイル | 役割 |
|---|---|
| `config.py` | 設定（並列数・タイムアウト・メール等）。`.env` を自動読込 |
| `keywords.py` | 障害/メンテ判定（三段構え：福祉除外→強語→文脈語） |
| `registry.py` | オープンデータ→監視レジストリ `data/municipalities.csv` 生成 |
| `crawler.py` | 並列巡回・お知らせ一覧の1階層追跡・項目抽出 |
| `state.py` | 既知分の永続化(`state/seen.json`)と差分計算 |
| `emailer.py` | HTMLダイジェスト生成・Gmail SMTP送信 |
| `main.py` | エントリポイント |

## セットアップ

```bash
cd jichitai_monitor
pip install -r requirements.txt
python3 registry.py          # レジストリ生成（初回のみ）
```

### メール設定（Gmailアプリパスワード）

1. Googleアカウントで**2段階認証を有効化**
2. [アプリパスワード](https://myaccount.google.com/apppasswords) を発行（16桁）
3. `.env.example` を `.env` にコピーして値を設定
   ```
   GMAIL_USER=niwatori67@gmail.com
   GMAIL_APP_PASSWORD=発行した16桁
   MAIL_TO=niwatori67@gmail.com
   ```

### 動作確認

```bash
python3 main.py --dry-run --limit 50   # 送信せずHTMLを state/preview.html に出力
python3 main.py --dry-run              # 全件巡回してプレビュー
python3 main.py                        # 本番（メール送信）
```

> 初回実行は**ベースライン登録（seeding）**として全件を既知化し、差分通知はしません。
> 翌日以降、新規の障害・メンテ告知のみが届きます。

## 毎日の自動実行

### 方式A：GitHub Actions（推奨・常時稼働・無料）

1. このディレクトリをGitHubリポジトリにpush
2. リポジトリの **Settings → Secrets and variables → Actions** に登録
   - `GMAIL_USER` / `GMAIL_APP_PASSWORD` / `MAIL_TO`
3. `.github/workflows/daily-monitor.yml` が **毎日7:50 JST** に自動実行
   - 差分状態はActionsキャッシュで永続化
   - `Actions` タブから手動実行(workflow_dispatch)も可

### 方式B：macOS launchd（Macが起動している場合）

```bash
chmod +x run.sh
cp com.jichitai.monitor.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.jichitai.monitor.plist
```
（plist内のパスは自環境に合わせて調整。ログは `state/logs/` と `/tmp/jichitai_monitor.*`）

## 調整ポイント

- 検出語の追加・除外は `keywords.py`（`STRONG` / `CONTEXTUAL` / `SYSTEM_CONTEXT` / `DISABILITY`）
- 並列数・タイムアウト・追跡page数は `.env` または `config.py`
- 監視対象の増減は `data/municipalities.csv` を直接編集

## 関連：不正アクセス・サイバー攻撃ニュース

同じ仕組み・同じGmail設定で、不正アクセス・サイバー攻撃・情報漏えいのニュースを毎朝届ける
日次ダイジェストを `cyber_news/` に置いている（ワークフロー `.github/workflows/cyber-news.yml`）。
詳細は [cyber_news/README.md](cyber_news/README.md)。

## 精度について

- 判定は**リンク文言ベース**。障害告知は多くが「お知らせ一覧」に載るため1階層追跡で捕捉
- ページがJavaScript描画のみ／告知が画像の自治体は取りこぼす可能性あり（今後の改善余地）
- 「新規」の単位はリンク文言＋URLのハッシュ。文言が変わると別項目として再通知される場合あり
