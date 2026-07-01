"""失敗自治体の原因を分類する診断スクリプト。"""
import json
from collections import Counter

import registry
from crawler import crawl_all


def categorize(err: str) -> str:
    if not err:
        return "ok"
    e = err.lower()
    if "timeout" in e or "timed out" in e:
        return "タイムアウト"
    if "ssl" in e or "certificate" in e:
        return "SSL証明書"
    if "connection" in e or "connect" in e or "resolve" in e or "name or service" in e:
        return "接続不可(DNS/拒否)"
    if "403" in e:
        return "403 アクセス拒否(bot対策)"
    if "404" in e:
        return "404 not found"
    if "500" in e or "502" in e or "503" in e:
        return "5xx サーバエラー"
    if "toomanyredirects" in e or "redirect" in e:
        return "リダイレクト過多"
    return "その他"


def main():
    recs = registry.load_registry()
    print(f"診断対象: {len(recs)} 自治体")
    results = crawl_all(recs)

    failures = [r for r in results if r["error"]]
    cats = Counter(categorize(r["error"]) for r in failures)

    print(f"\n=== 失敗 {len(failures)} 件の内訳 ===")
    for cat, n in cats.most_common():
        print(f"  {cat}: {n}")

    out = [{"pref": r["pref"], "city": r["city"], "url": r["url"],
            "cat": categorize(r["error"]), "error": r["error"]} for r in failures]
    with open("state/failures.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("\n詳細 -> state/failures.json")

    print("\n=== 各カテゴリの例 ===")
    seen = set()
    for r in out:
        if r["cat"] not in seen:
            seen.add(r["cat"])
            print(f"  [{r['cat']}] {r['pref']}{r['city']} {r['url']}")
            print(f"      {r['error']}")


if __name__ == "__main__":
    main()
