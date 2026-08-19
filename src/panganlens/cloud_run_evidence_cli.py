"""Build activation-ready evidence fragments from reviewed cloud workflow runs."""

from __future__ import annotations

import argparse
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from panganlens.activation_evidence import (
    AUTH_SMOKE_WORKFLOW,
    COMMIT_SHA_PATTERN,
    EXPECTED_BRANCH,
    EXPECTED_EVENT,
    READINESS_WORKFLOW,
    REPOSITORY_FULL_NAME,
    SCHEMA_VERIFICATION_WORKFLOW,
)

WORKFLOW_PATHS = {
    "auth_smoke": AUTH_SMOKE_WORKFLOW,
    "readiness": READINESS_WORKFLOW,
    "schema_verification": SCHEMA_VERIFICATION_WORKFLOW,
}


def build_cloud_run_evidence(
    kind: str,
    *,
    run_id: int,
    workflow_ref: str,
    head_branch: str,
    head_sha: str,
    event: str,
    result: Mapping[str, Any] | None = None,
) -> dict[str, object]:
    """Return a secret-safe manifest fragment from one reviewed GitHub run."""

    workflow_path = WORKFLOW_PATHS.get(kind)
    if workflow_path is None:
        raise ValueError(f"unsupported workflow evidence kind: {kind}")

    expected_workflow_ref = (
        f"{REPOSITORY_FULL_NAME}/{workflow_path}@refs/heads/{EXPECTED_BRANCH}"
    )
    errors: list[str] = []

    if not isinstance(run_id, int) or isinstance(run_id, bool) or run_id <= 0:
        errors.append("run_id must be a positive integer")
    if workflow_ref != expected_workflow_ref:
        errors.append("workflow_ref does not match the reviewed workflow")
    if head_branch != EXPECTED_BRANCH:
        errors.append("head_branch must be main")
    if not isinstance(head_sha, str) or not COMMIT_SHA_PATTERN.fullmatch(head_sha):
        errors.append("head_sha must be a lowercase 40-character commit SHA")
    if event != EXPECTED_EVENT:
        errors.append("event must be workflow_dispatch")

    if kind != "auth_smoke" and not isinstance(result, Mapping):
        errors.append(f"{kind} result JSON is required")

    if errors:
        raise ValueError("; ".join(errors))

    if kind == "auth_smoke":
        return {
            "auth_smoke": {
                "run_id": run_id,
                "conclusion": "success",
                "workflow_path": workflow_path,
                "head_branch": head_branch,
                "head_sha": head_sha,
                "event": event,
            }
        }

    assert result is not None
    if kind == "schema_verification":
        status = result.get("status")
        if status not in {"SCHEMA_READY", "BLOCKED"}:
            raise ValueError("schema verification result has an unsupported status")
        return {
            "bootstrap": {
                "schema_verification_run_id": run_id,
                "schema_status": status,
                "schema_verification_workflow_path": workflow_path,
                "schema_verification_head_branch": head_branch,
                "schema_verification_head_sha": head_sha,
                "schema_verification_event": event,
            }
        }

    status = result.get("status")
    if status not in {"READY", "BLOCKED"}:
        raise ValueError("readiness result has an unsupported status")

    metrics = result.get("metrics")
    age: int | None = None
    if isinstance(metrics, Mapping):
        age_value = metrics.get("latest_successful_capture_age_hours")
        if age_value is not None:
            if not isinstance(age_value, int) or isinstance(age_value, bool):
                raise ValueError("latest successful capture age must be an integer")
            age = age_value

    if status == "READY" and age is None:
        raise ValueError("READY result must include latest successful capture age")

    readiness: dict[str, object] = {
        "run_id": run_id,
        "status": status,
        "workflow_path": workflow_path,
        "head_branch": head_branch,
        "head_sha": head_sha,
        "event": event,
    }
    if age is not None:
        readiness["latest_source_capture_age_hours"] = age

    return {"readiness": readiness}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build secret-safe activation evidence from a reviewed cloud run."
    )
    parser.add_argument("kind", choices=sorted(WORKFLOW_PATHS))
    parser.add_argument("--result", type=Path)
    parser.add_argument("--run-id", type=int, required=True)
    parser.add_argument("--workflow-ref", required=True)
    parser.add_argument("--head-branch", required=True)
    parser.add_argument("--head-sha", required=True)
    parser.add_argument("--event", required=True)
    return parser


def _load_result(path: Path | None) -> Mapping[str, Any] | None:
    if path is None:
        return None
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise ValueError("result root must be an object")
    return value


def main() -> int:
    args = build_parser().parse_args()
    try:
        result = _load_result(args.result)
        evidence = build_cloud_run_evidence(
            args.kind,
            run_id=args.run_id,
            workflow_ref=args.workflow_ref,
            head_branch=args.head_branch,
            head_sha=args.head_sha,
            event=args.event,
            result=result,
        )
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(json.dumps({"status": "INVALID", "errors": [str(exc)]}, sort_keys=True))
        return 2

    print(json.dumps(evidence, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
