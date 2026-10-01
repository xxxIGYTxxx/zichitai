"""全自治体 障害情報モニター エントリポイント。

使い方:
  python3 main.py            # 巡回→差分→メール送信（本番）
  python3 main.py --dry-run  # メール送信せずHTMLをファイル出力して確認
  python3 main.py --limit 50 # 先頭50自治体のみ（動作確認用）
"""
import argparse
import sys
from datetime import datetime

import config
import registry
import state as state_mod
from crawler import crawl_all
from emailer import build_html, send_email


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="送信せずHTMLを出力")
    ap.add_argument("--limit", type=int, default=0, help="対象自治体数を制限（テスト用）")
    ap.add_argument("--report", action="store_true",
                    help="差分ではなく現在検出できる全項目をメール（状態は更新しない）")
    args = ap.parse_args()

    records = registry.load_registry()
    if args.limit:
        records = records[: args.limit]
    print(f"監視対象: {len(records)} 自治体")

    results = crawl_all(records)
    ok = sum(1 for r in results if r["error"] is None)
    err = len(results) - ok
    print(f"巡回完了: 成功 {ok} / 失敗 {err}")

    stats = {"sites": len(records), "ok": ok, "error": err}
    date_s = datetime.now().strftime("%m/%d")

    if args.report:
        # 現状スナップショット：検出済みの全項目を載せる（差分計算・状態更新はしない）
        by_site = [
            {"pref": r["pref"], "city": r["city"], "url": r["url"], "items": r["items"]}
            for r in results if r["items"]
        ]
        html = build_html(by_site, stats, is_seeding=False)
        total = sum(len(s["items"]) for s in by_site)
        subject = f"[自治体障害情報] 現状スナップショット {date_s} 全国{total}件 / {len(by_site)}自治体"
        skip_empty = False
    else:
        st = state_mod.load_state()
        new_by_site, is_seeding = state_mod.diff_and_update(st, results)
        state_mod.save_state(st)
        total_new = sum(len(s["items"]) for s in new_by_site)
        if is_seeding:
            # 初回/キャッシュ消失後。静かに既知化すると進行中の障害を丸ごと
            # 取りこぼすため、現在検出できる障害を全件スナップショットで通知する。
            snapshot = [
                {"pref": r["pref"], "city": r["city"], "url": r["url"], "items": r["items"]}
                for r in results if r["items"]
            ]
            html = build_html(snapshot, stats, is_seeding=False)
            total_cur = sum(len(s["items"]) for s in snapshot)
            subject = (f"[自治体障害情報] 監視開始: 現在の障害 "
                       f"全国{total_cur}件 / {len(snapshot)}自治体")
        else:
            html = build_html(new_by_site, stats, is_seeding)
            if total_new:
                subject = f"[自治体障害情報] {date_s} 新規{total_new}件 / {len(new_by_site)}自治体"
            else:
                subject = f"[自治体障害情報] {date_s} 新規なし"
        # 毎時実行では「新規なし」メールを送らない（NOTIFY_EMPTY=false時）
        skip_empty = (not is_seeding) and total_new == 0 and not config.NOTIFY_EMPTY

    if args.dry_run:
        out = config.STATE_DIR / "preview.html"
        out.write_text(html, encoding="utf-8")
        print(f"[dry-run] 件名: {subject}")
        print(f"[dry-run] HTML出力: {out}")
        return 0

    if skip_empty:
        print(f"新規なしのため送信スキップ: {subject}")
        return 0

    send_email(html, subject)
    print(f"送信完了: {subject}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
