"""Print the production bootstrap plan without changing BigQuery."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from panganlens.bootstrap_plan import build_bootstrap_plan


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Show the schema-only PanganLens BigQuery bootstrap plan"
    )
    parser.add_argument("--repo-root", default=str(Path.cwd()))
    return parser


def main() -> int:
    args = build_parser().parse_args()
    payload = build_bootstrap_plan(args.repo_root).as_dict()
    print(json.dumps(payload, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
