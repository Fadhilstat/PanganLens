"""Validate a static dashboard snapshot without cloud dependencies."""

from __future__ import annotations

import argparse
import json
import re
from datetime import date
from pathlib import Path

FRESHNESS = frozenset({"Terkini", "Perlu diperiksa", "Data lama"})


def check_snapshot(path: str | Path) -> None:
    """Block invalid payloads before CI uploads them to public Pages."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict) or type(data.get("schema_version")) is not int:
        raise ValueError("invalid snapshot schema")
    if data["schema_version"] != 1:
        raise ValueError("unsupported snapshot schema_version")
    national = data.get("national_prices")
    provinces = data.get("province_prices")
    if not isinstance(national, list) or not isinstance(provinces, list):
        raise ValueError("prices must be arrays")

    state = data.get("publish_state")
    if state is None:
        if national or provinces:
            raise ValueError("nonempty prices require an active publish state")
        return

    if not isinstance(state, dict) or state.get("active_run_status") != "SUCCESS":
        raise ValueError("publish state must reference a successful run")
    day = state.get("active_observation_date")
    if not isinstance(day, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", day):
        raise ValueError("invalid active observation date")
    try:
        date.fromisoformat(day)
    except ValueError as error:
        raise ValueError("invalid calendar date") from error
    if state.get("freshness_label") not in FRESHNESS:
        raise ValueError("invalid freshness label")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the PanganLens Pages snapshot")
    parser.add_argument("file", type=Path)
    args = parser.parse_args()
    try:
        check_snapshot(args.file)
    except (ValueError, OSError) as exc:
        parser.exit(1, "Snapshot rejected: " + str(exc) + "\n")
    print("Snapshot publication contract: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
