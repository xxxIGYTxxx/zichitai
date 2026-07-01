"""自治体HPを巡回し、障害・メンテナンス系の告知項目を抽出する。"""
import hashlib
import re
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

import config
from keywords import is_failure_notice

# 一部自治体はRSS/XMLを返すため、HTMLパーサ警告は抑制
warnings.filterwarnings("ignore", category=getattr(__import__("bs4"), "XMLParsedAsHTMLWarning", Warning))

_WS = re.compile(r"\s+")

# 「お知らせ/新着一覧」page候補を示すアンカー文言
NEWS_HINTS = ["新着", "お知らせ", "緊急", "重要なお知らせ", "更新情報",
             "トピックス", "障害情報", "メンテナンス", "利用状況", "重要"]


def _norm(text: str) -> str:
    return _WS.sub(" ", (text or "").strip())


def _find_news_links(soup: "BeautifulSoup", base_url: str) -> List[str]:
    """トップpageから『お知らせ一覧』候補URLを抽出（最大 MAX_FOLLOW 件）。"""
    links: List[str] = []
    seen = set()
    for a in soup.find_all("a"):
        text = _norm(a.get_text())
        href = a.get("href") or ""
        if not href:
            continue
        if any(h in text for h in NEWS_HINTS):
            link = urljoin(base_url, href)
            if link in seen or link == base_url:
                continue
            seen.add(link)
            links.append(link)
        if len(links) >= config.MAX_FOLLOW:
            break
    return links


def item_hash(text: str, url: str) -> str:
    return hashlib.sha1(f"{_norm(text)}|{url}".encode("utf-8")).hexdigest()[:16]


def _items_from_soup(soup: "BeautifulSoup", base_url: str) -> List[Dict[str, str]]:
    """1つのpageのアンカーから障害系項目を抽出。"""
    items: List[Dict[str, str]] = []
    for a in soup.find_all("a"):
        text = _norm(a.get_text())
        if not text or len(text) < 4:
            continue
        if not is_failure_notice(text):
            continue
        href = a.get("href") or ""
        link = urljoin(base_url, href) if href else base_url
        items.append({"text": text[:200], "url": link, "hash": item_hash(text, link)})
    return items


def _decode(resp) -> str:
    if not resp.encoding or resp.encoding.lower() == "iso-8859-1":
        resp.encoding = resp.apparent_encoding
    return resp.text


def _get(url: str):
    resp = requests.get(
        url, timeout=config.HTTP_TIMEOUT,
        headers={"User-Agent": config.USER_AGENT}, allow_redirects=True,
    )
    resp.raise_for_status()
    return resp


def fetch_site(rec: Dict[str, str]) -> Dict:
    """1自治体を巡回。結果 {lgcode,pref,city,url,items,error} を返す。"""
    url = rec["url"]
    out = {
        "lgcode": rec.get("lgcode", ""),
        "pref": rec.get("pref", ""),
        "city": rec.get("city", ""),
        "url": url,
        "items": [],
        "error": None,
    }
    try:
        resp = _get(url)
        top = BeautifulSoup(_decode(resp), "html.parser")
        merged: Dict[str, Dict[str, str]] = {}
        for it in _items_from_soup(top, resp.url):
            merged[it["hash"]] = it

        # 「お知らせ一覧」pageを1階層だけ追跡して取りこぼしを補う
        for news_url in _find_news_links(top, resp.url):
            try:
                r2 = _get(news_url)
                sub = BeautifulSoup(_decode(r2), "html.parser")
                for it in _items_from_soup(sub, r2.url):
                    merged.setdefault(it["hash"], it)
            except Exception:  # noqa: BLE001 下層pageの失敗は無視
                continue

        out["items"] = list(merged.values())[: config.MAX_ITEMS_PER_SITE]
    except Exception as e:  # noqa: BLE001 通信エラーは記録して続行
        out["error"] = f"{type(e).__name__}: {str(e)[:120]}"
    return out


def crawl_all(records: List[Dict[str, str]], progress: bool = True) -> List[Dict]:
    """全自治体を並列巡回。"""
    results: List[Dict] = []
    total = len(records)
    done = 0
    with ThreadPoolExecutor(max_workers=config.MAX_WORKERS) as ex:
        futures = {ex.submit(fetch_site, r): r for r in records}
        for fut in as_completed(futures):
            results.append(fut.result())
            done += 1
            if progress and done % 100 == 0:
                print(f"  crawled {done}/{total}")
    return results
