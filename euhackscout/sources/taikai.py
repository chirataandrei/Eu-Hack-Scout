from __future__ import annotations

from typing import Any

from euhackscout.http import HttpClient
from euhackscout.models import Format, Hackathon, parse_date_range

# ChallengeStep has startDate only — endDate 400s the whole query.
QUERY = """
query ActiveHackathons {
  challenges(perPage: 50) {
    id
    name
    slug
    organization { name }
    currentStep { name startDate }
  }
}
"""


def hackathons_from_payload(data: dict[str, Any]) -> list[Hackathon]:
    challenges = ((data.get("data") or {}).get("challenges")) or []
    out: list[Hackathon] = []
    for row in challenges:
        if not isinstance(row, dict):
            continue
        name = str(row.get("name") or "").strip()
        slug = str(row.get("slug") or "").strip()
        org = ((row.get("organization") or {}) or {}).get("name") if isinstance(row.get("organization"), dict) else ""
        if not name or not slug:
            continue
        cassini = "cassini" in name.lower() or "cassini" in str(org).lower()
        start, end = parse_date_range(name)
        out.append(
            Hackathon(
                name=name,
                organizer=str(org or "Taikai"),
                url=f"https://taikai.network/hackathons/{slug}",
                source="taikai",
                location="Europe" if cassini else "Online",
                format=Format.HYBRID if cassini else Format.ONLINE,
                start_date=start,
                end_date=end,
                tags=("taikai",) + (("eu", "space") if cassini else ()),
            )
        )
    return out


def fetch(http: HttpClient) -> list[Hackathon]:
    status, data = http.post_json(
        "https://api.taikai.network/api/graphql",
        {"query": QUERY},
    )
    if status != 200 or not isinstance(data, dict) or data.get("errors"):
        return []
    return hackathons_from_payload(data)
