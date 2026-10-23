"""RSS/RDF/Atom を並列取得し、記事を共通の形に正規化する。"""
import hashlib
import html
import re
import time
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Dict, List, Optional

import requests

import config

# CISA は Accept / Accept-Language が無いと403を返す
HEADERS = {
    "User-Agent": config.USER_AGENT,
    "Accept": "application/rss+xml,application/atom+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
}

_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"\s+")
# Googleニュースの見出し末尾「 - 媒体名」
_GNEWS_SUFFIX = re.compile(r"\s+-\s+[^-]+$")


def clean(text: Optional[str]) -> str:
    """HTMLタグ・実体参照・余分な空白を除く。"""
    text = _TAG.sub(" ", html.unescape(text or ""))
    return _WS.sub(" ", html.unescape(text)).strip()


def url_hash(url: str) -> str:
    return hashlib.sha1(url.strip().encode("utf-8")).hexdigest()[:16]


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _child(el: ET.Element, *names: str) -> Optional[ET.Element]:
    for c in el:
        if _local(c.tag) in names:
            return c
    return None


def _child_text(el: ET.Element, *names: str) -> str:
    # 名前の優先順に探す（description が無ければ summary、の順）
    for n in names:
        c = _child(el, n)
        if c is not None and (c.text or "").strip():
            return c.text.strip()
    return ""


def _link(el: ET.Element) -> str:
    for c in el:
        if _local(c.tag) != "link":
            continue
        if c.attrib.get("href") and c.attrib.get("rel", "alternate") == "alternate":
            return c.attrib["href"].strip()  # Atom
        if (c.text or "").strip():
            return c.text.strip()            # RSS / RDF
    return ""


def parse_date(text: str) -> Optional[datetime]:
    """RFC822（RSS）と ISO8601（RDF/Atom）の両方を読む。読めなければ None。"""
    if not text:
        return None
    try:
        dt = parsedate_to_datetime(text)
    except (TypeError, ValueError):
        try:
            dt = datetime.fromisoformat(text.strip().replace("Z", "+00:00"))
        except ValueError:
            return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def parse_feed(content: bytes, src: Dict[str, str]) -> List[Dict]:
    root = ET.fromstring(content)
    items: List[Dict] = []
    for el in root.iter():
        if _local(el.tag) not in ("item", "entry"):
            continue
        title = clean(_child_text(el, "title"))
        link = _link(el)
        if not title or not link:
            continue
        desc = clean(_child_text(el, "description", "summary", "encoded", "content"))
        media = src["name"]
        source_el = _child(el, "source")
        if source_el is not None and (source_el.text or "").strip():
            # Googleニュース：<source> が配信元の媒体名。見出し末尾の媒体名は外す
            media = source_el.text.strip()
            title = _GNEWS_SUFFIX.sub("", title)
        # Googleニュース等、概要文が見出しの繰り返しなら概要なし扱い
        if desc and (title in desc or desc in title):
            desc = ""
        items.append({
            "id": url_hash(link),
            "title": title,
            "link": link,
            "desc": desc,
            "media": media,
            "source": src["name"],
            "region": src["region"],
            "published": parse_date(_child_text(el, "pubDate", "date", "published", "updated")),
        })
    return items


def fetch_source(src: Dict[str, str]) -> Dict:
    """1情報源を取得。結果 {source, url, items, error} を返す。"""
    out = {"source": src["name"], "url": src["url"], "items": [], "error": None}
    for attempt in range(config.HTTP_RETRIES + 1):
        try:
            resp = requests.get(src["url"], headers=HEADERS, timeout=config.HTTP_TIMEOUT)
            resp.raise_for_status()
            out["items"] = parse_feed(resp.content, src)
            out["error"] = None
            return out
        except Exception as e:  # noqa: BLE001 通信・形式エラーは記録して再試行
            out["error"] = f"{type(e).__name__}: {str(e)[:120]}"
            if attempt < config.HTTP_RETRIES:
                time.sleep(2 * (attempt + 1))
    return out


def fetch_all(sources: List[Dict[str, str]]) -> List[Dict]:
    """全情報源を並列取得（結果は sources と同じ順）。"""
    with ThreadPoolExecutor(max_workers=config.MAX_WORKERS) as ex:
        return list(ex.map(fetch_source, sources))
