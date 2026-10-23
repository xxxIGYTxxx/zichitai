# 不正アクセス・サイバー攻撃ニュース 日次ダイジェスト

自治体・公共機関／国・政府機関／企業・団体／個人／海外の
**不正アクセス・サイバー攻撃・情報漏えいのニュース**をRSSから毎朝集め、
見出し・概要・元記事リンクを区分別にまとめて **毎朝 8:00 頃にメールで届ける**仕組み。
AIは使わず、費用は0円（GitHub Actions・Gmail の無料範囲）。

構成・送信経路は親フォルダの障害情報モニターと同じ。Gmail設定（Secrets / `.env`）も共用する。

## 何をするか

1. 15本のRSS（国内専門サイト・公的機関・Googleニュース検索・海外）を並列取得
2. 見出しの語判定で事件記事だけを残す（解説・宣伝・被害の出ていない脆弱性の周知は除外）
3. 前日までに送った記事を除く
4. 見出しの類似度で、同じ事件の記事を1行にまとめる
5. 自治体名（`../data/municipalities.csv`）などで5区分に分け、自治体・公共機関を最上段に
6. Gmail でHTMLダイジェストを送信し、送信に成功したら送信済みとして記録

## ファイル構成

| ファイル | 役割 |
|---|---|
| `config.py` | 設定。`.env`（このフォルダ → 親フォルダの順）を自動読込 |
| `sources.py` | 情報源（RSS）の一覧 |
| `fetcher.py` | RSS/RDF/Atom の並列取得・正規化 |
| `keywords.py` | 事件記事の判定（三段構え：除外→強語→脆弱性は悪用時のみ） |
| `dedup.py` | 見出しの類似度で同じ事件をまとめる |
| `classifier.py` | 5区分の判定と代表記事の選択 |
| `state.py` | 送信済み記事の記録（`state/seen.json`） |
| `emailer.py` | HTMLダイジェスト生成・Gmail SMTP送信 |
| `main.py` | エントリポイント |

## 動作確認

```bash
cd cyber_news
python3 main.py --dry-run           # 送信せず state/preview.html に出力（状態は更新しない）
python3 main.py --dry-run --limit 3 # 先頭3情報源だけで確認
python3 main.py                     # 本番（メール送信）
```

> 初回（状態なし）は直近24時間分を「配信開始」として送る。翌日以降は未送信の記事だけが届く。

## 毎日の自動実行

### 方式A：GitHub Actions（推奨）

`.github/workflows/cyber-news.yml` が **毎朝 7:30 JST** に起動する（8:00頃着）。
Secrets（`GMAIL_USER` / `GMAIL_APP_PASSWORD` / `MAIL_TO`）は障害情報モニターと共用なので、追加登録は不要。
`Actions` タブから手動実行（workflow_dispatch）もできる。

### 方式B：macOS launchd

```bash
chmod +x run.sh
cp com.jichitai.cybernews.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.jichitai.cybernews.plist
```
方式Aと両方動かすとメールが2通届くので、どちらか一方にする。

## 調整ポイント

- 誤検知・取りこぼし → `keywords.py`（`STRONG` / `EXCLUDE` / `EXCLUDE_MEDIA`）
- 区分の誤り → `classifier.py`（`PUBLIC` / `GOVERNMENT` / `PERSONAL`）
- まとめ過ぎ・まとまらない → `.env` の `DEDUP_THRESHOLD`（既定0.5。下げるほどまとまる）
- 情報源の追加・削除 → `sources.py`
- 1通の行数上限 → `MAX_ROWS`（既定150。超えた分は行の多い区分の古い順に省略）

## 精度について（AIを使わない方式の限界）

- 言い回しが大きく違う同じ事件は、別の行に残ることがある
- 要約はRSSに付いている概要文の先頭のみ。Googleニュース由来の記事は見出しだけ
- 見出し末尾の地名タグ（「青森市（ＡＴＶ青森テレビ）」等）が企業の所在地でも、自治体に分類されることがある
- 海外の記事は英語のまま載る
