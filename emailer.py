"""ダイジェストのHTML生成とGmail SMTP送信。"""
import smtplib
import ssl
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from html import escape
from typing import Dict, List

import config


def build_html(new_by_site: List[Dict], stats: Dict, is_seeding: bool) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    total_items = sum(len(s["items"]) for s in new_by_site)

    head = f"""
    <div style="font-family:sans-serif;line-height:1.6;color:#222">
    <h2 style="margin:0 0 4px">🖥 全自治体 障害・メンテナンス情報 ダイジェスト</h2>
    <div style="color:#666;font-size:13px">生成: {now}</div>
    <div style="margin:10px 0;padding:8px 12px;background:#f2f6ff;border-radius:6px;font-size:14px">
      監視対象 <b>{stats['sites']}</b> 自治体 ／ 取得成功 <b>{stats['ok']}</b> ／ 失敗 <b>{stats['error']}</b>
    </div>
    """

    if is_seeding:
        body = ("<p>本日は<b>初期化（ベースライン登録）</b>のため差分通知はありません。"
                "明日以降、新規の障害・メンテナンス告知のみをお届けします。</p>")
        return head + body + "</div>"

    if not new_by_site:
        body = "<p>本日、新規の障害・メンテナンス情報は検出されませんでした。</p>"
        return head + body + "</div>"

    body = [f"<p>本日の新規検出: <b>{len(new_by_site)}</b> 自治体 / <b>{total_items}</b> 件</p>"]
    # 都道府県ごとにまとめる
    new_by_site.sort(key=lambda s: (s["pref"], s["city"]))
    cur_pref = None
    for s in new_by_site:
        if s["pref"] != cur_pref:
            if cur_pref is not None:
                body.append("</div>")
            cur_pref = s["pref"]
            body.append(f'<h3 style="margin:16px 0 4px;border-bottom:1px solid #ddd">{escape(cur_pref)}</h3><div>')
        body.append(f'<div style="margin:8px 0"><b>{escape(s["city"])}</b> '
                     f'<a href="{escape(s["url"])}" style="color:#0645ad;font-size:12px">[HP]</a><ul style="margin:4px 0">')
        for it in s["items"]:
            body.append(f'<li><a href="{escape(it["url"])}" style="color:#0645ad">{escape(it["text"])}</a></li>')
        body.append("</ul></div>")
    body.append("</div>")
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
