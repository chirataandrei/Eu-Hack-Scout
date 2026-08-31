from __future__ import annotations

from euhackscout.config import ENV_PATH, SEEN_PATH, load_dotenv
from euhackscout.delivery.emailer import build_email, send_email, split_for_email
from euhackscout.pipeline import scan
from euhackscout.store import load_seen, save_seen, seen_keys_for, split_new


def run(*, send: bool, persist: bool) -> int:
    load_dotenv(ENV_PATH)
    items = scan()
    seen = load_seen()
    new_items, open_items = split_new(items, seen)
    bucharest, europe, online = split_for_email(open_items)
    print(
        f"\nOpen: {len(open_items)}   New: {len(new_items)}   "
        f"Bucharest: {len(bucharest)}   Europe: {len(europe)}   Online: {len(online)}"
    )
    for item in new_items[:100]:
        deadline = item.registration_deadline or item.end_date or item.start_date
        print(f"  [NEW] {item.name} — {item.location} (deadline {deadline})")
        print(f"         {item.url}")

    subject, plain, html_body = build_email(new_items, open_items)
    if send:
        if not new_items:
            print("No new hackathons — email not sent.")
        else:
            send_email(subject, plain, html_body)
            print(f"Email sent: {subject}")
    if persist:
        updated = seen | seen_keys_for(open_items)
        save_seen(updated, SEEN_PATH)
        print(f"Saved {SEEN_PATH} ({len(updated)} ids)")
    return 0
