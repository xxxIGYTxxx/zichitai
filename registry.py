"""localgovjp.csv から監視対象レジストリ(municipalities.csv)を生成/読込。"""
import csv
from typing import List, Dict

import config


def build_registry() -> List[Dict[str, str]]:
    """元CSVを整形して municipalities.csv を生成し、レコード配列を返す。"""
    rows: List[Dict[str, str]] = []
    with open(config.SOURCE_CSV, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for r in reader:
            url = (r.get("url") or "").strip()
            city = (r.get("city") or "").strip()
            pref = (r.get("pref") or "").strip()
            lgcode = (r.get("lgcode") or "").strip()
            if not url or not city:
                continue
            rows.append({
                "lgcode": lgcode,
                "pref": pref,
                "city": city,
                "url": url,
            })

    # lgcode重複を除去（念のため）
    seen = set()
    uniq = []
    for r in rows:
        key = r["lgcode"] or r["url"]
        if key in seen:
            continue
        seen.add(key)
        uniq.append(r)

    with open(config.REGISTRY_CSV, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["lgcode", "pref", "city", "url"])
        w.writeheader()
        w.writerows(uniq)
    return uniq


def load_registry() -> List[Dict[str, str]]:
    """レジストリを読込（無ければ生成）。"""
    if not config.REGISTRY_CSV.exists():
        return build_registry()
    with open(config.REGISTRY_CSV, encoding="utf-8") as f:
        return list(csv.DictReader(f))


if __name__ == "__main__":
    recs = build_registry()
    print(f"registry built: {len(recs)} 自治体 -> {config.REGISTRY_CSV}")
