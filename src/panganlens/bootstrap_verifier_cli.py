"""Command-line entrypoint for metadata-only bootstrap verification."""

from __future__ import annotations

import argparse
import json

from panganlens.bootstrap_verifier import BigQueryBootstrapVerifier
from panganlens.schema_contract import WAREHOUSE_LOCATION


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Verify the PanganLens BigQuery bootstrap using metadata only"
    )
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--location", default=WAREHOUSE_LOCATION)
    return parser


def run(args: argparse.Namespace) -> dict[str, object]:
    verifier = BigQueryBootstrapVerifier(
        project_id=args.project_id,
        location=args.location,
    )
    return verifier.verify().as_dict()


def main() -> int:
    args = build_parser().parse_args()
    payload = run(args)
    print(json.dumps(payload, sort_keys=True, separators=(",", ":")))
    return 0 if payload["status"] == "SCHEMA_READY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
