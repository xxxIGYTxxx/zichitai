"""見出しの類似度で、同じ事件の記事（転載・別媒体の報道）を1行にまとめる。

見出しを2文字単位に分け、その日の見出し全体で珍しい2文字ほど重く数える
（「カプコン」「1177万」は重く、「情報」「可能性」は軽い）。重なりの重みが
短い方の見出しの DEDUP_THRESHOLD 以上なら同じ行とみなす。
媒体名と定型語は比較前に除く。定型語を残すと「〜に不正アクセス、個人情報が
流出」だけで別事件がまとまってしまうため。
言い回しが大きく違う同じ事件までは、まとめきれない（AIを使わない方式の限界）。
"""
import math
import re
import unicodedata
from collections import Counter
from typing import Dict, List, Set

import config

# 比較から外す定型語（事件の種類を表すだけで、どの事件かを区別しない）
STOP = [
    "不正アクセス", "サイバー攻撃", "個人情報", "情報漏えい", "情報漏洩", "漏えい",
    "漏洩", "流出", "可能性", "おそれ", "恐れ", "システム", "について", "お知らせ",
    "まとめてみた", "まとめ", "速報", "画像", "による", "受け", "した", "された", "件",
]

_MEDIA_PAREN = re.compile(r"[（(][^）)]*[）)]\s*$")   # 末尾の（テレビ新広島）等
_PUNCT = re.compile(r"[\s「」『』【】［］\[\]（）()、。・:：,.!?！？\"'”“’‘|｜/／~〜-]")


def normalize(title: str) -> str:
    # 全角英数（ＪＲ・１１７７）を半角にそろえてから比べる
    t = _MEDIA_PAREN.sub("", unicodedata.normalize("NFKC", title))
    for w in STOP:
        t = t.replace(w, "")
    return _PUNCT.sub("", t).lower()


def bigrams(text: str) -> Set[str]:
    return {text[i:i + 2] for i in range(len(text) - 1)} or {text}


def group_items(items: List[Dict]) -> List[List[Dict]]:
    """記事を行（同じ事件の束）に分ける。各行の中身は見つけた順。"""
    all_grams = [bigrams(normalize(it["title"])) for it in items]
    df = Counter(g for gs in all_grams for g in gs)
    weight = {g: math.log(len(items) / c) for g, c in df.items()}

    def similarity(a: Set[str], b: Set[str]) -> float:
        smaller = min(sum(weight[g] for g in a), sum(weight[g] for g in b))
        return sum(weight[g] for g in a & b) / smaller if smaller > 0 else 0.0

    groups: List[List[Dict]] = []
    grams: List[List[Set[str]]] = []
    links: List[Set[str]] = []
    for it, g in zip(items, all_grams):
        for i, members in enumerate(grams):
            if it["link"] in links[i] or max(similarity(g, m) for m in members) >= config.DEDUP_THRESHOLD:
                groups[i].append(it)
                members.append(g)
                links[i].add(it["link"])
                break
        else:
            groups.append([it])
            grams.append([g])
            links.append({it["link"]})
    return groups
