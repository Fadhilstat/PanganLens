"""CLI for validating PanganLens cloud activation evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from panganlens.activation_evidence import validate_activation_evidence


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate a secret-safe PanganLens cloud activation manifest."
    )
    parser.add_argument("manifest", type=Path, help="Path to activation evidence JSON")
    parser.add_argument(
        "--require-complete",
        action="store_true",
        help="Require WIF, auth smoke, SCHEMA_READY, and READY evidence.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        evidence = json.loads(args.manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "INVALID", "errors": [str(exc)]}, indent=2))
        return 2

    if not isinstance(evidence, dict):
        print(
            json.dumps(
                {"status": "INVALID", "errors": ["manifest root must be an object"]},
                indent=2,
            )
        )
        return 2

    result = validate_activation_evidence(
        evidence,
        require_complete=args.require_complete,
    )
    print(json.dumps(result.as_dict(), indent=2, sort_keys=True))
    return 0 if result.status == "VALID" else 1


if __name__ == "__main__":
    raise SystemExit(main())
