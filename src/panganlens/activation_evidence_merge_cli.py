"""Merge reviewed activation evidence fragments without silent overwrites."""

from __future__ import annotations

import argparse
import copy
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from panganlens.activation_evidence import validate_activation_evidence

BOOTSTRAP_PLAN_KEYS = {
    "plan_sha256",
    "plan_run_id",
    "plan_workflow_path",
    "plan_head_branch",
    "plan_head_sha",
    "plan_event",
}
ALLOWED_FRAGMENT_ROOTS = {"auth_smoke", "bootstrap", "readiness"}


def normalize_fragment(fragment: Mapping[str, Any]) -> dict[str, Any]:
    """Return one supported workflow fragment in manifest shape."""

    keys = set(fragment)
    if keys and keys <= BOOTSTRAP_PLAN_KEYS:
        return {"bootstrap": dict(fragment)}

    if len(keys) != 1 or not keys <= ALLOWED_FRAGMENT_ROOTS:
        raise ValueError(
            "fragment must contain one supported evidence root or bootstrap plan provenance"
        )

    root = next(iter(keys))
    value = fragment[root]
    if not isinstance(value, Mapping):
        raise ValueError(f"fragment {root} must be an object")
    return {root: dict(value)}


def merge_activation_evidence(
    base: Mapping[str, Any],
    fragments: list[Mapping[str, Any]],
) -> dict[str, Any]:
    """Merge evidence fragments while rejecting conflicting values."""

    merged = copy.deepcopy(dict(base))
    for fragment in fragments:
        normalized = normalize_fragment(fragment)
        _merge_mapping(merged, normalized, path="root")
    return merged


def _merge_mapping(
    target: dict[str, Any],
    incoming: Mapping[str, Any],
    *,
    path: str,
) -> None:
    for key, value in incoming.items():
        current_path = f"{path}.{key}"
        if key not in target:
            target[key] = copy.deepcopy(value)
            continue

        current = target[key]
        if isinstance(current, Mapping) and isinstance(value, Mapping):
            child = dict(current)
            _merge_mapping(child, value, path=current_path)
            target[key] = child
            continue

        if current != value:
            raise ValueError(f"conflicting evidence at {current_path}")


def _load_object(path: Path) -> Mapping[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise ValueError(f"{path}: JSON root must be an object")
    return value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Merge reviewed activation evidence fragments without silent overwrites"
    )
    parser.add_argument("base", type=Path)
    parser.add_argument("fragments", nargs="+", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--require-complete", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        base = _load_object(args.base)
        fragments = [_load_object(path) for path in args.fragments]
        merged = merge_activation_evidence(base, fragments)
        validation = validate_activation_evidence(
            merged,
            require_complete=args.require_complete,
        )
        if validation.status != "VALID":
            payload = {
                "status": "INVALID",
                "errors": list(validation.errors),
            }
            print(json.dumps(payload, sort_keys=True))
            return 2

        rendered = json.dumps(merged, indent=2, sort_keys=True) + "\n"
        if args.output is not None:
            args.output.write_text(rendered, encoding="utf-8")
        else:
            print(rendered, end="")
        return 0
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(json.dumps({"status": "INVALID", "errors": [str(exc)]}, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
