"""Capture one narrow, UNREVIEWED PIHPS research sample without GCP access."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from panganlens.ingestion.pihps_interface import (
    GridRequest,
    PihpsInterfaceError,
    PihpsWebsiteClient,
)
from panganlens.ingestion.pihps_probe import previous_business_day
from panganlens.ingestion.research_sample import (
    build_research_sample,
    write_research_sample,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--province-id", default="13")
    parser.add_argument("--commodity-id", default="com_3")
    parser.add_argument("--window-days", type=int, default=11)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)

    if not 1 <= args.window_days <= 15:
        parser.error("--window-days must be from 1 to 15")

    today = datetime.now(ZoneInfo("Asia/Jakarta")).date()
    end = previous_business_day(today)
    start = end - timedelta(days=args.window_days - 1)
    request = GridRequest(
        price_type_id=1,
        comcat_id=args.commodity_id,
        province_id=args.province_id,
        start_date=start,
        end_date=end,
        show_regencies=True,
        show_markets=False,
        report_type=1,
    )
    try:
        client = PihpsWebsiteClient()
        provinces = client.fetch_reference_capture("provinces")
        commodities = client.fetch_reference_capture("commodities")
        grid = client.fetch_grid_capture(request)
        report, rows = build_research_sample(
            provinces, commodities, grid, request, today
        )
        paths = write_research_sample(
            report,
            rows,
            args.output_dir,
            Path(__file__).resolve().parents[1],
        )
    except (PihpsInterfaceError, OSError, ValueError) as exc:
        print(f"PIHPS_RESEARCH_CAPTURE_BLOCKED: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    # The console contains only source health and output paths, never source prices.
    print(
        "PIHPS_RESEARCH_SAMPLE_PASS "
        + json.dumps(
            {
                "status": report["status"],
                "usable_price_points": report["usable_price_points"],
                "missing_price_cells": report["missing_price_cells"],
                "latest_price_observation_date": report["latest_price_observation_date"],
                "review_flags": report["review_flags"],
                "files": [str(path) for path in paths],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
