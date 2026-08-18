"""Command-line entrypoint for PanganLens BigQuery readiness checks."""

from __future__ import annotations

import argparse
import json

from panganlens.readiness import DEFAULT_LOCATION, BigQueryReadinessInspector


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Check PanganLens BigQuery production readiness")
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--location", default=DEFAULT_LOCATION)
    return parser


def run(args: argparse.Namespace) -> dict[str, object]:
    inspector = BigQueryReadinessInspector(
        project_id=args.project_id,
        location=args.location,
    )
    return inspector.inspect().as_dict()


def main() -> int:
    args = build_parser().parse_args()
    payload = run(args)
    print(json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str))
    return 0 if payload["status"] == "READY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
