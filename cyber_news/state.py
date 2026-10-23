"""送信済み記事(seen)の永続化と、未送信記事の抽出。

キーは「記事URLのハッシュ」と「見出しのハッシュ」の2つ。同じ見出しが
別のURL（転載先）で翌日に出てきても、再送しないようにするため。
"""
import hashlib
import json
import re
import unicodedata
from datetime import date, datetime, timedelta
from typing import Dict, List

import config

# 「不正アクセスについて」のような短い見出しは別組織の発表と衝突するため、URLだけで見る
_MIN_TITLE_KEY_LEN = 15
_PUNCT = re.compile(r"[\s「」『』【】［］\[\]（）()、。・:：,.!?！？\"'”“’‘|｜/／~〜-]")


def load_state() -> Dict[str, str]:
    if config.STATE_FILE.exists():
        with open(config.STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_state(state: Dict[str, str]) -> None:
    with open(config.STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=0)


def _keys(item: Dict) -> List[str]:
    keys = [item["id"]]
    t = _PUNCT.sub("", unicodedata.normalize("NFKC", item["title"])).lower()
    if len(t) >= _MIN_TITLE_KEY_LEN:
        keys.append("t:" + hashlib.sha1(t.encode("utf-8")).hexdigest()[:16])
    return keys


def filter_new(state: Dict[str, str], items: List[Dict]) -> List[Dict]:
    """まだ送っていない記事だけを返す。"""
    return [it for it in items if not any(k in state for k in _keys(it))]


def mark_sent(state: Dict[str, str], items: List[Dict]) -> None:
    """送った記事を記録し、保持日数を超えた記録を掃除する。"""
    today = date.today()
    for it in items:
        for k in _keys(it):
            state.setdefault(k, today.isoformat())
    cutoff = today - timedelta(days=config.SEEN_RETENTION_DAYS)
    for k, d in list(state.items()):
        try:
            if datetime.strptime(d, "%Y-%m-%d").date() < cutoff:
                del state[k]
        except ValueError:
            continue
