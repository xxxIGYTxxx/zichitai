"""既知アイテム(seen)の永続化と差分計算。"""
import json
from datetime import date, datetime, timedelta
from typing import Dict, List, Tuple

import config


def load_state() -> Dict:
    if config.STATE_FILE.exists():
        with open(config.STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_state(state: Dict) -> None:
    with open(config.STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=0)


def _prune(seen: Dict[str, str], today: date) -> Dict[str, str]:
    """保持日数を超えた既知アイテムを削除。"""
    cutoff = today - timedelta(days=config.SEEN_RETENTION_DAYS)
    kept = {}
    for h, d in seen.items():
        try:
            if datetime.strptime(d, "%Y-%m-%d").date() >= cutoff:
                kept[h] = d
        except ValueError:
            kept[h] = d
    return kept


def diff_and_update(state: Dict, results: List[Dict]) -> Tuple[List[Dict], bool]:
    """巡回結果から新規項目を抽出し、stateを更新。

    戻り値 (新規サイト配列, is_seeding)
    is_seeding=True の初回は差分通知せず既知登録のみ行う。
    """
    is_seeding = len(state) == 0
    today = date.today()
    today_s = today.isoformat()

    new_by_site: List[Dict] = []
    for r in results:
        code = r["lgcode"] or r["url"]
        seen: Dict[str, str] = state.get(code, {})
        fresh = []
        for it in r["items"]:
            if it["hash"] not in seen:
                if not is_seeding:
                    fresh.append(it)
            seen[it["hash"]] = seen.get(it["hash"], today_s)
        seen = _prune(seen, today)
        if seen:
            state[code] = seen
        if fresh:
            new_by_site.append({
                "pref": r["pref"], "city": r["city"],
                "url": r["url"], "items": fresh,
            })
    return new_by_site, is_seeding
