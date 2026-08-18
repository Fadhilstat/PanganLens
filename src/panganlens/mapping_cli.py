"""Human-operated CLI for reviewed PIHPS source mappings."""

from __future__ import annotations

import argparse
import json
from datetime import datetime

from google.cloud import bigquery

from panganlens.ingestion.mapping_operator import BigQueryMappingOperator

DEFAULT_LOCATION = "asia-southeast2"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="panganlens-mapping",
        description="Review PIHPS source identities without fuzzy or automatic approval.",
    )
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--location", default=DEFAULT_LOCATION)
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list", help="List mappings waiting for review.")
    list_parser.add_argument("--limit", type=int, default=100)

    generate = subparsers.add_parser(
        "generate",
        help="Generate review candidates from one stored source capture.",
    )
    generate.add_argument("--capture-id", required=True)
    generate.add_argument("--scope", required=True, choices=("national", "region", "market"))
    generate.add_argument("--mapping-version", required=True, type=int)

    approve = subparsers.add_parser(
        "approve",
        help="Activate one mapping after an explicit human decision.",
    )
    approve.add_argument("--candidate-fingerprint", required=True)
    approve.add_argument("--canonical-id", required=True)
    _add_review_metadata(approve)

    reject = subparsers.add_parser(
        "reject",
        help="Reject one mapping candidate after an explicit human review.",
    )
    reject.add_argument("--candidate-fingerprint", required=True)
    _add_review_metadata(reject)
    return parser


def _add_review_metadata(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--reviewed-by", required=True)
    parser.add_argument("--reviewed-at", required=True, type=datetime.fromisoformat)
    parser.add_argument("--review-note", required=True)


def run(args: argparse.Namespace) -> dict[str, object] | list[dict[str, object]]:
    client = bigquery.Client(project=args.project_id, location=args.location)
    operator = BigQueryMappingOperator(
        args.project_id,
        client=client,
        location=args.location,
    )
    if args.command == "list":
        return operator.list_pending(args.limit)
    if args.command == "generate":
        return operator.generate_from_capture(
            args.capture_id,
            args.scope,
            args.mapping_version,
        )
    if args.command == "approve":
        return operator.approve(
            args.candidate_fingerprint,
            args.canonical_id,
            args.reviewed_by,
            args.reviewed_at,
            args.review_note,
        )
    if args.command == "reject":
        return operator.reject(
            args.candidate_fingerprint,
            args.reviewed_by,
            args.reviewed_at,
            args.review_note,
        )
    raise ValueError("unsupported mapping command")


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    payload = run(args)
    print(json.dumps(payload, default=str, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
