"""Collect schema-only evidence from the PIHPS public website interface."""

from __future__ import annotations

import argparse
import json
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from panganlens.ingestion.pihps_interface import PihpsInterfaceError, PihpsWebsiteClient
from panganlens.ingestion.pihps_probe import build_probe_summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--base-url",
        default="https://www.bi.go.id/hargapangan",
    )
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    today_jakarta = date.today()
    try:
        today_jakarta = datetime.now(ZoneInfo("Asia/Jakarta")).date()
        client = PihpsWebsiteClient(
            base_url=args.base_url,
            timeout_seconds=args.timeout,
        )
        summary = build_probe_summary(client, today_jakarta)
        exit_code = 0
    except (PihpsInterfaceError, KeyError, ValueError) as exc:
        summary = {
            "status": "fail",
            "source": "PIHPS Bank Indonesia public website interface",
            "reference_date": today_jakarta.isoformat(),
            "error": str(exc),
        }
        exit_code = 1

    rendered = json.dumps(summary, indent=2, sort_keys=True)
    print(rendered)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(f"{rendered}\n", encoding="utf-8")

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
