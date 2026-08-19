"""Command-line validation for PanganLens Google Cloud repository variables."""

from __future__ import annotations

import argparse

from panganlens.cloud_config import validate_cloud_variables


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate PanganLens Google Cloud activation variables"
    )
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--wif-provider", required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    validate_cloud_variables(args.project_id, args.wif_provider)
    print("Google Cloud activation variables passed validation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
