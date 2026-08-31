from __future__ import annotations

import html
import os
import smtplib
import ssl
from datetime import date, timedelta
from email.message import EmailMessage
from zoneinfo import ZoneInfo

from euhackscout.filters import effective_deadline
from euhackscout.models import Hackathon
from euhackscout.pipeline import route_bucket


def _esc(text: str) -> str:
    return html.escape(text or "", quote=True)


def _fmt_date(value: date | None) -> str:
    return value.strftime("%d.%m.%Y") if value else "—"


def split_for_email(items: list[Hackathon]) -> tuple[list[Hackathon], list[Hackathon], list[Hackathon]]:
    bucharest, europe, online = [], [], []
    for item in items:
        bucket = route_bucket(item)
        if bucket == "bucharest":
            bucharest.append(item)
        elif bucket == "europe":
            europe.append(item)
        else:
            online.append(item)
    key = lambda h: (effective_deadline(h) is None, effective_deadline(h) or date.max, h.name.lower())
    bucharest.sort(key=key)
    europe.sort(key=key)
    online.sort(key=key)
    return bucharest, europe, online


def _deadline_label(item: Hackathon, today: date) -> tuple[str, bool]:
    deadline = effective_deadline(item)
    if deadline is None:
        return "Deadline: unknown", False
    urgent = deadline <= today + timedelta(days=7)
    prefix = "⚠️ " if urgent else ""
    return f"{prefix}Deadline: {_fmt_date(deadline)}", urgent


def _card_html(item: Hackathon, today: date) -> str:
    label, urgent = _deadline_label(item, today)
    color = "#b91c1c" if urgent else "#334155"
    dates = f"{_fmt_date(item.start_date)} – {_fmt_date(item.end_date)}"
    tags = ", ".join(item.tags)
    tags_html = f"<div style='color:#64748b;font-size:12px;margin-top:4px'>{_esc(tags)}</div>" if tags else ""
    return f"""
    <div style="border:1px solid #e2e8f0;border-radius:10px;padding:14px 16px;margin:0 0 10px">
      <div style="font-size:17px;font-weight:700;color:#0f172a">{_esc(item.name)}</div>
      <div style="font-size:14px;color:#1e293b;margin-top:6px">{_esc(item.organizer)}</div>
      <div style="color:#475569;font-size:13px;margin-top:4px">{_esc(item.location)} · {_esc(item.format.value.replace('_', ' '))}</div>
      <div style="color:#475569;font-size:13px;margin-top:2px">{_esc(dates)}</div>
      <div style="margin-top:6px;font-size:13px;font-weight:700;color:{color}">{_esc(label)}</div>
      {tags_html}
      <div style="margin-top:8px;font-size:13px">
        Register:
        <a href="{_esc(item.url)}" style="color:#1d4ed8;word-break:break-all">{_esc(item.url)}</a>
      </div>
    </div>
    """


def _section_html(title: str, items: list[Hackathon], empty: str, today: date) -> str:
    heading = f"<h2 style='font-size:16px;margin:28px 0 10px;color:#0f172a'>{title}</h2>"
    if not items:
        return heading + f"<p style='margin:0 0 16px;color:#64748b'>{_esc(empty)}</p>"
    return heading + "".join(_card_html(item, today) for item in items)


def _plain_section(title: str, items: list[Hackathon], empty: str, today: date) -> list[str]:
    lines = [title, ""]
    if not items:
        lines.append(empty)
        lines.append("")
        return lines
    for item in items:
        label, _ = _deadline_label(item, today)
        lines.append(f"     Name:      {item.name}")
        lines.append(f"     Organizer: {item.organizer}")
        lines.append(f"     Location:  {item.location} ({item.format.value})")
        lines.append(f"     Dates:     {_fmt_date(item.start_date)} – {_fmt_date(item.end_date)}")
        lines.append(f"     {label}")
        lines.append(f"     Register:  {item.url}")
        lines.append("")
    return lines


def build_email(new_items: list[Hackathon], open_items: list[Hackathon]) -> tuple[str, str, str]:
    today = date.today()
    stamp = datetime_now()
    n_new = len(new_items)
    n_open = len(open_items)
    subject = f"EU Hack Scout — {n_new} new ({stamp})"
    bucharest, europe, online = split_for_email(new_items)

    sections = [
        (
            "🚨 TOP PRIORITATE: Hackathoane în București",
            bucharest,
            "Niciun hackathon nou în București de la ultimul scan.",
        ),
        (
            "✈️ Hackathoane în Europa (Fizic/Hibrid)",
            europe,
            "Niciun hackathon fizic/hibrid nou în Europa de la ultimul scan.",
        ),
        (
            "🌐 Hackathoane Globale Online",
            online,
            "Niciun hackathon online nou de la ultimul scan.",
        ),
    ]

    plain_lines = [
        f"Hackathoane noi de la ultimul scan — {stamp}",
        f"New: {n_new}    Still open (already sent): {n_open}",
        "",
        "Doar evenimente pe care nu le-ai primit deja.",
        "",
    ]
    if not new_items:
        plain_lines.append("Nimic nou de la ultimul scan.")
        plain_lines.append("")
    else:
        for title, items, empty in sections:
            if items:
                plain_lines.extend(_plain_section(title, items, empty, today))
    plain = "\n".join(plain_lines)

    if not new_items:
        cards = ["<p style='margin:0 0 16px;color:#64748b'>Nimic nou de la ultimul scan.</p>"]
    else:
        cards = [_section_html(title, items, empty, today) for title, items, empty in sections if items]

    html_body = f"""
    <html>
      <body style="margin:0;padding:0;background:#f8fafc;font-family:-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif">
        <div style="max-width:640px;margin:0 auto;padding:28px 16px">
          <h1 style="font-size:22px;margin:0 0 8px;color:#0f172a">EU Hack Scout</h1>
          <p style="margin:0 0 20px;color:#475569">
            Doar evenimente noi · București · Europa fizic · Online · {stamp}<br>
            <strong>{n_new}</strong> new · {n_open} still open (already sent, skipped)
          </p>
          {''.join(cards)}
          <p style="margin:28px 0 0;color:#94a3b8;font-size:12px">
            eu-hack-scout digest. Evenimentele deja văzute nu sunt incluse.
            In-person extra-european este ignorat.
          </p>
        </div>
      </body>
    </html>
    """
    return subject, plain, html_body


def datetime_now() -> str:
    from datetime import datetime

    return datetime.now(ZoneInfo("Europe/Bucharest")).strftime("%d.%m.%Y")


def send_email(subject: str, plain: str, html_body: str) -> None:
    host = os.environ.get("SMTP_HOST") or "smtp.gmail.com"
    port = int(os.environ.get("SMTP_PORT") or "587")
    user = (os.environ.get("SMTP_USER") or "").strip()
    password = (os.environ.get("SMTP_PASS") or "").replace(" ", "").strip()
    to_addr = (os.environ.get("EMAIL_TO") or "").strip()
    from_addr = (os.environ.get("EMAIL_FROM") or user).strip() or user
    if not (user and password and to_addr):
        raise SystemExit("Set SMTP_USER, SMTP_PASS, and EMAIL_TO (see .env.example).")

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = to_addr
    msg.set_content(plain)
    msg.add_alternative(html_body, subtype="html")

    context = ssl.create_default_context()
    with smtplib.SMTP(host, port, timeout=30) as smtp:
        smtp.starttls(context=context)
        smtp.login(user, password)
        smtp.send_message(msg)
