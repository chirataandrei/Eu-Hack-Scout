# eu-hack-scout

Daily email digest of:

- **Hackathons in Bucharest** (in-person / hybrid)
- **In-person and hybrid hackathons in the rest of Europe**
- **Fully online / remote hackathons**

In-person events on other continents are ignored.

Sources include Devpost, Luma, MLH, Eventbrite, Meetup, GDG, ETHGlobal, Taikai, CASSINI, Hack Club, Devfolio, HackerEarth, Unstop, Superteam, AIcrowd, Romanian student leagues (LSAC, BEST, ASMI, LSE, EESTEC), university news (UniBuc, UPB), local press RSS, and an optional Apify Google cache for LinkedIn/SPA blind spots.

## What you get

Every day around 08:00 (Romania time, summer) an email with **only new** matching events since the last scan, in three sections. Already-seen events are skipped; if nothing is new, no email is sent.

Results are also written to `data/bucharest.json`, `data/europe.json`, and `data/online.json`.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
cp .env.example .env   # then fill SMTP_* / EMAIL_TO
python -m euhackscout scan --no-save
```

Send the digest:

```bash
python -m euhackscout scan --email
```

Apify (optional). Without `APIFY_TOKEN`, refresh is a no-op:

```bash
python -m euhackscout apify-refresh --dry-run
```

## Tests

```bash
python3 -m unittest discover -s tests -v
```
