"""不正アクセス・サイバー攻撃ニュース 日次ダイジェスト エントリポイント。

使い方:
  python3 main.py            # 取得→判定→まとめ→メール送信（本番）
  python3 main.py --dry-run  # メール送信せずHTMLをファイル出力して確認（状態は更新しない）
  python3 main.py --limit 3  # 先頭3情報源のみ（動作確認用）
"""
import argparse
import sys
from datetime import datetime, timedelta, timezone
from typing import Dict, List

import classifier
import config
import dedup
import state as state_mod
from emailer import JST, build_html, send_email
from fetcher import fetch_all
from keywords import is_cyber_incident
from sources import SOURCES

_PREFIX = "[サイバー攻撃ニュース]"


def build_rows(items: List[Dict]) -> Dict[str, List[Dict]]:
    """記事を行にまとめて区分ごとに分け、各区分を新しい順に並べる。"""
    rows_by_cat: Dict[str, List[Dict]] = {c: [] for c in classifier.CATEGORIES}
    oldest = datetime.min.replace(tzinfo=timezone.utc)
    for group in dedup.group_items(items):
        rep = classifier.representative(group)
        rows_by_cat[classifier.classify(group)].append({
            "rep": rep,
            "others": [it for it in group if it is not rep],
            "items": group,
            "latest": max((it["published"] or oldest) for it in group),
        })
    for rows in rows_by_cat.values():
        rows.sort(key=lambda r: r["latest"], reverse=True)
    return rows_by_cat


def trim_rows(rows_by_cat: Dict[str, List[Dict]], limit: int) -> Dict[str, int]:
    """上限を超えたら、自治体・公共機関以外で行の多い区分から古い行を落とす。

    自治体・公共機関は、ほかの区分が空になるまで落とさない。落とした数を返す。
    """
    overflow: Dict[str, int] = {}
    total = sum(len(v) for v in rows_by_cat.values())
    priority = classifier.CATEGORIES[0]
    while total > limit:
        others = [c for c in rows_by_cat if c != priority and rows_by_cat[c]]
        cat = max(others or [priority], key=lambda c: len(rows_by_cat[c]))
        rows_by_cat[cat].pop()
        overflow[cat] = overflow.get(cat, 0) + 1
        total -= 1
    return overflow


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="送信せずHTMLを出力（状態は更新しない）")
    ap.add_argument("--limit", type=int, default=0, help="対象情報源数を制限（テスト用）")
    args = ap.parse_args()

    sources = SOURCES[: args.limit] if args.limit else SOURCES
    results = fetch_all(sources)
    ok = sum(1 for r in results if r["error"] is None)
    # 同名の情報源（Googleニュースの複数クエリ等）は、全部失敗した時だけ失敗と表示する
    failed = sorted({r["source"] for r in results if r["error"]}
                    - {r["source"] for r in results if r["error"] is None})
    for r in results:
        print(f"  {r['source']:<16} {len(r['items']):>4}件 {r['error'] or ''}")
    print(f"取得完了: 成功 {ok} / 失敗 {len(results) - ok}")
    date_s = datetime.now(JST).strftime("%m/%d")

    st = state_mod.load_state()
    is_first = len(st) == 0
    stats = {"sources": len(results), "ok": ok, "items": 0}

    if ok == 0:
        # 全滅：状態は更新せず、翌日に拾い直す
        html = build_html({}, stats, failed, {}, note="すべての情報源で取得に失敗しました。明日の配信で拾い直します。")
        subject = f"{_PREFIX} {date_s} 取得失敗"
        to_mark: List[Dict] = []
        skip_empty = False
    else:
        hours = config.FIRST_RUN_HOURS if is_first else config.LOOKBACK_HOURS
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(hours=hours)
        # 複数クエリで同じ記事が重なるため、URL単位で1本にする
        items = list({it["id"]: it for r in results for it in r["items"]}.values())
        items = [it for it in items if (it["published"] or now) >= cutoff]
        items = [it for it in items if is_cyber_incident(it["title"], it["desc"], it["media"])]
        items = state_mod.filter_new(st, items)
        stats["items"] = len(items)

        rows_by_cat = build_rows(items)
        overflow = trim_rows(rows_by_cat, config.MAX_ROWS)
        to_mark = [it for rows in rows_by_cat.values() for row in rows for it in row["items"]]
        total = sum(len(v) for v in rows_by_cat.values())
        n_public = len(rows_by_cat["自治体・公共機関"])

        note = ""
        if is_first:
            note = (f"本日から配信を開始します。初回は直近{config.FIRST_RUN_HOURS}時間分です。"
                    "明日以降は前日までに送っていない記事だけをお届けします。")
            subject = f"{_PREFIX} 配信開始: 直近{config.FIRST_RUN_HOURS}時間 全体{total}件"
        elif total:
            subject = f"{_PREFIX} {date_s} 自治体・公共{n_public}件 / 全体{total}件"
        else:
            subject = f"{_PREFIX} {date_s} 新着なし"
        html = build_html(rows_by_cat, stats, failed, overflow, note=note)
        skip_empty = (not is_first) and total == 0 and not config.NOTIFY_EMPTY

    if args.dry_run:
        out = config.STATE_DIR / "preview.html"
        out.write_text(html, encoding="utf-8")
        print(f"[dry-run] 件名: {subject}")
        print(f"[dry-run] HTML出力: {out}")
        return 0

    if skip_empty:
        print(f"新着なしのため送信スキップ: {subject}")
        return 0

    send_email(html, subject)
    print(f"送信完了: {subject}")
    # 送信に成功してから記録する（送信失敗時に未送信分を既知扱いにしないため）
    if to_mark:
        state_mod.mark_sent(st, to_mark)
        state_mod.save_state(st)
    return 0


if __name__ == "__main__":
    sys.exit(main())
