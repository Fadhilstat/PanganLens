"""Plan or explicitly apply the guarded PanganLens BigQuery bootstrap."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from panganlens.bootstrap_executor import (
    DEFAULT_LOCATION,
    BigQueryBootstrapExecutor,
    build_bootstrap_execution_plan,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Plan or explicitly apply the schema-only PanganLens BigQuery bootstrap"
    )
    parser.add_argument("--repo-root", default=str(Path.cwd()))
    parser.add_argument("--project-id")
    parser.add_argument("--location", default=DEFAULT_LOCATION)
    parser.add_argument("--expected-plan-sha256")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply reviewed schema DDL after exact plan hash confirmation",
    )
    return parser


def run(args: argparse.Namespace) -> dict[str, object]:
    plan = build_bootstrap_execution_plan(args.repo_root)
    if not args.apply:
        return plan.as_dict()

    if not args.project_id:
        raise ValueError("--project-id is required with --apply")
    if not args.expected_plan_sha256:
        raise ValueError("--expected-plan-sha256 is required with --apply")

    executor = BigQueryBootstrapExecutor(
        project_id=args.project_id,
        location=args.location,
    )
    return executor.apply(
        repo_root=args.repo_root,
        expected_plan_sha256=args.expected_plan_sha256,
    ).as_dict()


def main() -> int:
    args = build_parser().parse_args()
    payload = run(args)
    print(json.dumps(payload, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
