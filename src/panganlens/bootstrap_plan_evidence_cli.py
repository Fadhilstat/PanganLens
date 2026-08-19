"""Build commit-bound provenance for a reviewed PanganLens bootstrap plan."""

from __future__ import annotations

import argparse
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from panganlens.activation_evidence import (
    BOOTSTRAP_PLAN_WORKFLOW,
    COMMIT_SHA_PATTERN,
    EXPECTED_BRANCH,
    EXPECTED_EVENT,
    REPOSITORY_FULL_NAME,
    SHA256_PATTERN,
)

EXPECTED_PLAN_STATUS = "CLASSIFIED_SCHEMA_ONLY"
EXPECTED_WORKFLOW_REF = (
    f"{REPOSITORY_FULL_NAME}/{BOOTSTRAP_PLAN_WORKFLOW}@refs/heads/{EXPECTED_BRANCH}"
)


def build_bootstrap_plan_evidence(
    plan: Mapping[str, Any],
    *,
    run_id: int,
    workflow_ref: str,
    head_branch: str,
    head_sha: str,
    event: str,
) -> dict[str, object]:
    """Return activation-ready plan evidence from trusted GitHub run metadata."""

    errors: list[str] = []

    if not isinstance(run_id, int) or isinstance(run_id, bool) or run_id <= 0:
        errors.append("run_id must be a positive integer")
    if workflow_ref != EXPECTED_WORKFLOW_REF:
        errors.append("workflow_ref does not match the reviewed bootstrap plan workflow")
    if head_branch != EXPECTED_BRANCH:
        errors.append("head_branch must be main")
    if not isinstance(head_sha, str) or not COMMIT_SHA_PATTERN.fullmatch(head_sha):
        errors.append("head_sha must be a lowercase 40-character commit SHA")
    if event != EXPECTED_EVENT:
        errors.append("event must be workflow_dispatch")

    plan_sha256 = plan.get("plan_sha256")
    if not isinstance(plan_sha256, str) or not SHA256_PATTERN.fullmatch(plan_sha256):
        errors.append("plan_sha256 must be a lowercase SHA-256 value")
    if plan.get("status") != EXPECTED_PLAN_STATUS:
        errors.append("plan status must be CLASSIFIED_SCHEMA_ONLY")
    if plan.get("requires_explicit_apply") is not True:
        errors.append("plan must require explicit apply")

    executable_count = plan.get("executable_statement_count")
    if (
        not isinstance(executable_count, int)
        or isinstance(executable_count, bool)
        or executable_count <= 0
    ):
        errors.append("plan must contain executable schema statements")

    if errors:
        raise ValueError("; ".join(errors))

    return {
        "plan_sha256": plan_sha256,
        "plan_run_id": run_id,
        "plan_workflow_path": BOOTSTRAP_PLAN_WORKFLOW,
        "plan_head_branch": head_branch,
        "plan_head_sha": head_sha,
        "plan_event": event,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build secret-safe provenance for a PanganLens bootstrap plan artifact."
    )
    parser.add_argument("plan", type=Path, help="Path to bootstrap plan JSON")
    parser.add_argument("--run-id", type=int, required=True)
    parser.add_argument("--workflow-ref", required=True)
    parser.add_argument("--head-branch", required=True)
    parser.add_argument("--head-sha", required=True)
    parser.add_argument("--event", required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()

    try:
        plan = json.loads(args.plan.read_text(encoding="utf-8"))
        if not isinstance(plan, dict):
            raise ValueError("plan root must be an object")
        evidence = build_bootstrap_plan_evidence(
            plan,
            run_id=args.run_id,
            workflow_ref=args.workflow_ref,
            head_branch=args.head_branch,
            head_sha=args.head_sha,
            event=args.event,
        )
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(json.dumps({"status": "INVALID", "errors": [str(exc)]}, sort_keys=True))
        return 2

    print(json.dumps(evidence, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
