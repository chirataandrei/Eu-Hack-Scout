from __future__ import annotations

from euhackscout.http import HttpClient
from euhackscout.models import Hackathon
from euhackscout.sources.engines.jsonld import events_from_html

GEOS = (
    "romania--bucharest",
    "romania--cluj-napoca",
    "united-kingdom--london",
    "germany--berlin",
    "france--paris",
    "netherlands--amsterdam",
    "poland--warsaw",
    "spain--barcelona",
)


def fetch(http: HttpClient) -> list[Hackathon]:
    seen: set[str] = set()
    out: list[Hackathon] = []
    for geo in GEOS:
        url = f"https://www.eventbrite.com/d/{geo}/hackathon/"
        status, body = http.get(url, headers={"Accept": "text/html"})
        if status != 200 or not body:
            continue
        for event in events_from_html(body, page_url=url):
            event_url = event.get("url") or ""
            name = event.get("name") or ""
            if not name or not event_url or event_url in seen:
                continue
            seen.add(event_url)
            out.append(
                Hackathon(
                    name=name,
                    organizer=event.get("organizer") or "Eventbrite",
                    url=event_url,
                    source="eventbrite",
                    location=event.get("location") or "",
                    format=event["format"],
                    start_date=event.get("start_date"),
                    end_date=event.get("end_date"),
                    registration_deadline=event.get("registration_deadline"),
                )
            )
    return out
