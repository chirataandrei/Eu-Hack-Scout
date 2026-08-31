from __future__ import annotations

import argparse


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Scan Bucharest, European in-person, and online hackathons."
    )
    parser.add_argument(
        "command",
        nargs="?",
        default="scan",
        choices=["scan", "apify-refresh"],
    )
    parser.add_argument("--email", action="store_true", help="Send the digest by email (SMTP_* / EMAIL_TO)")
    parser.add_argument("--no-save", action="store_true", help="Do not update data/seen.json")
    parser.add_argument("--dry-run", action="store_true", help="Print Apify actor input and estimated cost, no network")
    parser.add_argument("--force", action="store_true", help="apify-refresh: skip the 6h cooldown (budget still applies)")
    args = parser.parse_args(argv)

    if args.command == "scan":
        from euhackscout.runner import run

        return run(send=args.email, persist=not args.no_save)

    if args.command == "apify-refresh":
        from euhackscout.discover import apify_refresh

        return apify_refresh(dry_run=args.dry_run, force=args.force)

    parser.error(f"unknown command {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
