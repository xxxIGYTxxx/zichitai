"""ダイジェストのHTML生成とGmail SMTP送信（送信部は障害情報モニターと同じ）。"""
import smtplib
import ssl
from datetime import datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from html import escape
from typing import Dict, List, Optional

import config

JST = timezone(timedelta(hours=9))
_MAX_OTHER_LINKS = 5   # 「他N媒体」のうち、リンクを並べる数


def _when(dt: Optional[datetime]) -> str:
    return dt.astimezone(JST).strftime("%m/%d %H:%M") if dt else ""


def _summary(desc: str) -> str:
    if len(desc) <= config.SUMMARY_CHARS:
        return desc
    return desc[: config.SUMMARY_CHARS] + "…"


def _row_html(row: Dict) -> str:
    rep, others = row["rep"], row["others"]
    parts = [f'<li style="margin:0 0 10px">'
             f'<a href="{escape(rep["link"])}" style="color:#0645ad;font-weight:bold">{escape(rep["title"])}</a>']
    if rep["desc"]:
        parts.append(f'<div style="font-size:13px;color:#333">{escape(_summary(rep["desc"]))}</div>')
    meta = escape(rep["media"])
    if rep["published"]:
        meta += f'・{_when(rep["published"])}'
    if others:
        links = "、".join(f'<a href="{escape(o["link"])}" style="color:#0645ad">{escape(o["media"])}</a>'
                         for o in others[:_MAX_OTHER_LINKS])
        rest = len(others) - _MAX_OTHER_LINKS
        meta += f'（他{len(others)}媒体: {links}{f" ほか{rest}件" if rest > 0 else ""}）'
    parts.append(f'<div style="font-size:12px;color:#666">{meta}</div></li>')
    return "".join(parts)


def build_html(rows_by_cat: Dict[str, List[Dict]], stats: Dict, failed: List[str],
               overflow: Dict[str, int], note: str = "") -> str:
    now = datetime.now(JST).strftime("%Y-%m-%d %H:%M")
    total_rows = sum(len(v) for v in rows_by_cat.values())

    head = f"""
    <div style="font-family:sans-serif;line-height:1.6;color:#222">
    <h2 style="margin:0 0 4px">🛡 不正アクセス・サイバー攻撃 ニュースダイジェスト</h2>
    <div style="color:#666;font-size:13px">生成: {now}</div>
    <div style="margin:10px 0;padding:8px 12px;background:#f2f6ff;border-radius:6px;font-size:14px">
      情報源 <b>{stats['sources']}</b> ／ 取得成功 <b>{stats['ok']}</b> ／
      対象記事 <b>{stats['items']}</b>件 → <b>{total_rows}</b>行
    </div>
    """
    body: List[str] = []
    if note:
        body.append(f"<p>{note}</p>")
    if not total_rows and not note:
        body.append("<p>本日、新着の不正アクセス・サイバー攻撃・情報漏えいのニュースはありませんでした。</p>")

    for cat, rows in rows_by_cat.items():
        if not rows:
            continue
        body.append(f'<h3 style="margin:18px 0 6px;border-bottom:1px solid #ddd">{escape(cat)}（{len(rows)}件）</h3>')
        body.append('<ul style="margin:4px 0;padding-left:20px">')
        body.extend(_row_html(r) for r in rows)
        body.append("</ul>")

    foot = []
    if overflow:
        detail = "、".join(f"{escape(c)} {n}件" for c, n in overflow.items())
        foot.append(f"行数の上限（{config.MAX_ROWS}行）を超えたため、古い順に省略: 他{sum(overflow.values())}件（{detail}）。"
                    "省略分は48時間以内なら翌日に載ります。")
    foot.append("取得できなかった情報源: " + (escape("、".join(failed)) if failed else "なし"))
    body.append('<hr style="margin-top:20px;border:none;border-top:1px solid #ddd">'
                '<div style="font-size:12px;color:#666">' + "<br>".join(foot) + "</div>")
    return head + "".join(body) + "</div>"


def send_email(html: str, subject: str) -> None:
    if not config.GMAIL_USER or not config.GMAIL_APP_PASSWORD:
        raise RuntimeError("GMAIL_USER / GMAIL_APP_PASSWORD が未設定です")

    recipients = config.MAIL_TO_LIST or [config.MAIL_TO]
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = config.MAIL_FROM
    msg["To"] = ", ".join(recipients)
    msg.attach(MIMEText("HTMLメール対応のクライアントでご覧ください。", "plain", "utf-8"))
    msg.attach(MIMEText(html, "html", "utf-8"))

    ctx = ssl.create_default_context()
    with smtplib.SMTP_SSL(config.SMTP_HOST, config.SMTP_PORT, context=ctx) as server:
        server.login(config.GMAIL_USER, config.GMAIL_APP_PASSWORD)
        server.sendmail(config.MAIL_FROM, recipients, msg.as_string())
