"""Registered hackathon sources. Order matters: earlier wins on fingerprint collision."""

from __future__ import annotations

from euhackscout.sources import (
    aicrowd,
    apify_scout,
    cassini,
    devfolio,
    devpost,
    ethglobal,
    eventbrite,
    gdg_bevy,
    hackclub,
    hackerearth,
    luma,
    meetup,
    mlh,
    ro_orgs,
    superteam,
    taikai,
    unstop,
)
from euhackscout.sources.base import SourceSpec

SOURCES: list[SourceSpec] = [
    SourceSpec("Luma", "luma", luma.fetch, require_keyword=True),
    SourceSpec("RO orgs", "ro_orgs", ro_orgs.fetch, assume_bucharest=True, require_keyword=True),
    SourceSpec("Eventbrite", "eventbrite", eventbrite.fetch, require_keyword=True),
    SourceSpec("Meetup", "meetup", meetup.fetch, require_keyword=True),
    SourceSpec("GDG", "gdg", gdg_bevy.fetch, require_keyword=True),
    SourceSpec("MLH", "mlh", mlh.fetch),
    SourceSpec("ETHGlobal", "ethglobal", ethglobal.fetch),
    SourceSpec("Taikai", "taikai", taikai.fetch),
    SourceSpec("CASSINI", "cassini", cassini.fetch),
    SourceSpec("Devpost", "devpost", devpost.fetch),
    SourceSpec("Hack Club", "hackclub", hackclub.fetch),
    SourceSpec("Devfolio", "devfolio", devfolio.fetch),
    SourceSpec("HackerEarth", "hackerearth", hackerearth.fetch),
    SourceSpec("Unstop", "unstop", unstop.fetch),
    SourceSpec("Superteam", "superteam", superteam.fetch, require_keyword=True),
    SourceSpec("AIcrowd", "aicrowd", aicrowd.fetch),
    SourceSpec("RSS RO", "rss_ro", ro_orgs.fetch_press, assume_bucharest=True, require_keyword=True),
    SourceSpec("Apify cache", "apify", apify_scout.fetch, require_keyword=True),
]
