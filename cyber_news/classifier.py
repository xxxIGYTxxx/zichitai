"""行（同じ記事の束）を5つの区分に分け、代表記事を選ぶ。

区分は上から順に判定し、最初に当てはまったものにする。
企業の事故でも自治体に影響が出た記事は「自治体・公共機関」に入る
（自治体への影響を優先して見る目的に合わせている）。
"""
import csv
from functools import lru_cache
from typing import Dict, List, Set

import config

CATEGORIES = ["自治体・公共機関", "国・政府機関", "企業・団体", "個人", "海外"]

# 自治体・公共機関を示す語（自治体名は municipalities.csv から読む）
PUBLIC = [
    "自治体", "市役所", "町役場", "村役場", "区役所", "道庁", "県庁", "都庁", "府庁",
    "教育委員会", "市立", "県立", "町立", "村立", "都立", "府立", "道立", "公立",
    "県の", "県が", "県警", "県委託", "県サイト", "県サービス", "県運営", "市の",
    "市町", "市委託", "国立大学", "大学", "病院", "学校", "機構",
    "独立行政法人", "警察", "消防",
]

# 国・政府機関を示す語（国家が関与する攻撃もここに入れる）
GOVERNMENT = [
    "省", "庁", "政府", "内閣", "国家", "自衛隊", "国会", "NISC", "官公庁",
    "大使館", "中国系", "ロシア系", "北朝鮮", "国家支援",
]

# 個人が被害者になる事件を示す語
PERSONAL = [
    "個人の", "フィッシング", "詐欺", "乗っ取り被害", "金銭被害", "不正送金",
    "不正利用被害", "なりすまし", "不正取引", "不正操作", "損失",
]

# 「北海道電力」など社名にも含まれるため、北海道だけは自治体名から外す（道庁・道内で拾う）
_AMBIGUOUS_NAMES = {"北海道"}


@lru_cache(maxsize=1)
def municipality_names() -> Set[str]:
    names: Set[str] = set()
    with open(config.MUNICIPALITIES_CSV, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            names.add(row["pref"])
            names.add(row["city"].split(" ")[0])  # 「札幌市 中央区」→「札幌市」
    return {n for n in names if len(n) >= 2} - _AMBIGUOUS_NAMES


def _names_municipality(text: str) -> bool:
    """自治体名を含むか。「広島県内の産婦人科」のような所在地の言い方は数えない。

    「青森市（ＡＴＶ青森テレビ）」のように末尾の地名タグが企業の所在地のこともあるが、
    「宮城・名取市」のように被害自治体のこともあり見分けられないため、自治体側に寄せる。
    """
    for n in municipality_names():
        start = text.find(n)
        while start != -1:
            if not text.startswith("内", start + len(n)):
                return True
            start = text.find(n, start + 1)
    return False


def classify(group: List[Dict]) -> str:
    """行の区分を返す。束のどれか1本でも当てはまれば、その区分とする。"""
    if any(it["region"] == "海外" for it in group):
        return "海外"
    titles = " ".join(it["title"] for it in group)
    # 自治体が自ら出した発表（Googleニュースの媒体名が「十日町市」等）も自治体扱い
    from_municipality = any(it["media"] in municipality_names() for it in group)
    if from_municipality or _names_municipality(titles) or any(w in titles for w in PUBLIC):
        return "自治体・公共機関"
    if any(w in titles for w in GOVERNMENT):
        return "国・政府機関"
    if any(w in titles for w in PERSONAL):
        return "個人"
    return "企業・団体"


def _is_official(it: Dict) -> bool:
    """自治体・企業・官公庁が自ら出した発表か（Googleニュースの媒体名で見る）。"""
    m = it["media"]
    return (m in municipality_names() or "株式会社" in m
            or m.endswith(("市", "町", "村", "県", "府", "都", "庁", "省")))


def representative(group: List[Dict]) -> Dict:
    """代表記事：概要文あり → 公式発表 → 最初に見つけた記事 の順。"""
    for pick in (lambda it: bool(it["desc"]), _is_official):
        for it in group:
            if pick(it):
                return it
    return group[0]
