"""不正アクセス・サイバー攻撃・情報漏えいの事件記事かを判定する。

障害情報モニターの keywords.py と同じ三段構え：

1) EXCLUDE（解説・宣伝）/ MEDICAL（感染症）を見出しに含む記事は無条件で除外
2) STRONG（事件を明確に示す語）を見出し・概要文の冒頭に含めば採用
3) VULN（脆弱性）は、見出しに EXPLOITED（悪用・攻撃・被害）を伴う場合のみ採用
   → 被害の出ていない脆弱性の周知は載せない
"""

# 単独で「事件」と判断できる語（英語は小文字で比較）
STRONG = [
    "不正アクセス", "サイバー攻撃", "情報漏えい", "情報漏洩", "漏えい", "漏洩",
    "情報流出", "個人情報流出", "流出", "ランサムウェア", "マルウェア", "Emotet",
    "乗っ取り", "不正ログイン", "標的型攻撃", "標的型メール", "DDoS", "改ざん",
    "誤送信", "不正送金", "不正利用", "サイバー犯罪", "ハッキング",
    "ransomware", "data breach", "breach", "cyberattack", "cyber attack",
    "hacked", "hackers", "data leak", "leaked", "stolen", "threat actor",
    "cyber actor", "state-sponsored", "nation-state", "espionage", "ddos",
    "compromised",
]

# 脆弱性の語（単独では採用しない）
VULN = ["脆弱性", "vulnerability", "vulnerabilities", "flaw", "zero-day", "ゼロデイ"]

# 脆弱性の記事を採用する条件（悪用・攻撃・被害）
EXPLOITED = [
    "悪用", "攻撃", "被害", "侵害", "exploited", "exploit", "in the wild",
    "attack", "abused",
]

# 解説・宣伝・イベント・脆弱性の周知（見出しに含めば除外）
EXCLUDE = [
    "セミナー", "ウェビナー", "講習会", "見学", "提供開始", "サービス提供",
    "発売", "販売開始", "オプション追加", "を実現", "決意", "白書",
    "べきか", "べき", "とは？", "とは?", "解説", "専門家に聞く", "なぜ",
    "何が起きている", "どこまで", "新常識", "日常化", "急増", "対策を", "対策で",
    "対策学", "対策として", "脆弱性対策", "に備える", "備えた", "正体", "リスク",
    "ランキング", "調査結果", "アンケート", "研究グループ", "を経験", "％",
    "CVSS", "件の脆弱性",
    "webinar", "how to", "best practices", "guide", "report finds",
]

# プレスリリース配信サイト・製品の宣伝（媒体名で除外）
EXCLUDE_MEDIA = ["PR TIMES", "@Press", "ValuePress", "SKYSEA"]

# 感染症・医療の文脈（障害情報モニターと同じ誤検知対策）
MEDICAL = [
    "感染症", "予防接種", "ワクチン", "インフルエンザ", "ノロウイルス",
    "コロナウイルス", "新型コロナ",
]


def _has(low: str, words) -> bool:
    return any(w.lower() in low for w in words)


def is_cyber_incident(title: str, desc: str = "", media: str = "") -> bool:
    """見出し（と概要文の冒頭）が、不正アクセス等の事件記事かを判定。"""
    if not title:
        return False
    low_title = title.lower()
    if _has(low_title, EXCLUDE) or _has(low_title, MEDICAL) or _has(media.lower(), EXCLUDE_MEDIA):
        return False
    if _has(low_title + " " + desc[:100].lower(), STRONG):
        return True
    if _has(low_title, VULN) and _has(low_title, EXPLOITED):
        return True
    return False
