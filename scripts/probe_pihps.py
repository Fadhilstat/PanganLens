"""Probe candidate PIHPS JSON endpoints from a local machine or CI runner."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict

from panganlens.ingestion.pihps_candidates import PihpsCandidateProbe


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--base-url",
        default="https://www.bi.go.id/hargapangan",
    )
    parser.add_argument("--timeout", type=int, default=30)
    args = parser.parse_args()

    probe = PihpsCandidateProbe(
        base_url=args.base_url,
        timeout_seconds=args.timeout,
    )

    results = [
        probe.probe_reference("provinces"),
        probe.probe_reference("commodities"),
    ]
    print(json.dumps([asdict(result) for result in results], indent=2))

    healthy = all(
        result.status_code == 200 and result.is_json and result.error is None
        for result in results
    )
    return 0 if healthy else 1


if __name__ == "__main__":
    raise SystemExit(main())
