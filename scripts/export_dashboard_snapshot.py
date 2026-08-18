"""Export the public dashboard JSON snapshot from curated BigQuery views."""

from __future__ import annotations

import argparse
import json

from panganlens.dashboard_snapshot import BigQueryDashboardSnapshotExporter, write_snapshot
from panganlens.schema_contract import WAREHOUSE_LOCATION


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Export the PanganLens public website snapshot from curated BigQuery views."
    )
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--output", default="website/data/dashboard.json")
    parser.add_argument("--location", default=WAREHOUSE_LOCATION)
    parser.add_argument("--maximum-bytes-billed", type=int, default=250_000_000)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    exporter = BigQueryDashboardSnapshotExporter(
        args.project_id,
        location=args.location,
        maximum_bytes_billed=args.maximum_bytes_billed,
    )
    snapshot = exporter.export()
    write_snapshot(snapshot, args.output)
    print(
        json.dumps(
            {
                "output": args.output,
                "generated_at": snapshot.generated_at,
                "national_rows": len(snapshot.national_prices),
                "province_rows": len(snapshot.province_prices),
                "has_publish_state": snapshot.publish_state is not None,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
