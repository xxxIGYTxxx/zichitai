"""情報源（RSS）の一覧。追加・削除はこのリストを編集するだけでよい。

region は区分判定に使う（"海外" の情報源から取った記事は「海外」に入る）。
"""
from urllib.parse import quote

_GNEWS = "https://news.google.com/rss/search?hl=ja&gl=JP&ceid=JP:ja&q="


def _gnews(query: str) -> str:
    # when:1d = 直近1日。1クエリ最大100件のため、一般クエリは語ごとに分ける
    return _GNEWS + quote(f"{query} when:1d")


SOURCES = [
    # 国内の専門サイト
    {"name": "Security NEXT", "region": "国内", "url": "https://www.security-next.com/feed"},
    {"name": "Security NEXT", "region": "国内", "url": "https://www.security-next.com/feed?paged=2"},
    {"name": "ScanNetSecurity", "region": "国内", "url": "https://scan.netsecurity.ne.jp/rss/index.rdf"},
    {"name": "ITmedia", "region": "国内", "url": "https://rss.itmedia.co.jp/rss/2.0/news_security.xml"},
    {"name": "piyolog", "region": "国内", "url": "https://piyolog.hatenadiary.jp/rss"},
    # 国内の公的機関
    {"name": "JPCERT/CC", "region": "国内", "url": "https://www.jpcert.or.jp/rss/jpcert.rdf"},
    {"name": "IPA", "region": "国内", "url": "https://www.ipa.go.jp/security/alert-rss.rdf"},
    # Googleニュース検索（自治体の公表・地方紙を拾う）
    {"name": "Googleニュース", "region": "国内",
     "url": _gnews("(自治体 OR 市役所 OR 町役場 OR 村役場 OR 県 OR 教育委員会) "
                   "(不正アクセス OR 情報漏えい OR ランサムウェア OR サイバー攻撃)")},
    {"name": "Googleニュース", "region": "国内", "url": _gnews("不正アクセス")},
    {"name": "Googleニュース", "region": "国内", "url": _gnews("サイバー攻撃")},
    {"name": "Googleニュース", "region": "国内", "url": _gnews("情報漏えい OR 情報漏洩")},
    {"name": "Googleニュース", "region": "国内", "url": _gnews("ランサムウェア")},
    # 海外
    {"name": "The Hacker News", "region": "海外", "url": "https://feeds.feedburner.com/TheHackersNews"},
    {"name": "BleepingComputer", "region": "海外", "url": "https://www.bleepingcomputer.com/feed/"},
    # 米CISAの共同勧告（国家支援型攻撃・ランサムウェア）。all.xml は5MB超で脆弱性情報ばかりのため使わない
    {"name": "CISA", "region": "海外",
     "url": "https://www.cisa.gov/cybersecurity-advisories/cybersecurity-advisories.xml"},
]
