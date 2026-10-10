"""Read-only PIHPS research extract, never a curated or publishable snapshot.

This module retains original PIHPS source identities. It performs no canonical
mapping, warehouse writes, publication pointer changes, or cloud authentication.
"""

from __future__ import annotations

import csv
import json
import re
from datetime import date
from pathlib import Path
from typing import Any

from panganlens.ingestion.pihps_interface import (
    GridRequest,
    PihpsInterfaceError,
    SourceRows,
    validate_schema_contract,
    verify_payload_text,
)
from panganlens.ingestion.pihps_parser import parse_grid_rows
from panganlens.ingestion.pihps_probe import (
    EXPECTED_COMMODITY_KEYS,
    EXPECTED_GRID_KEYS,
    EXPECTED_PROVINCE_KEYS,
)

PROVINCE_ID_PATTERN = re.compile(r"[1-9]\d*")
COMMODITY_ID_PATTERN = re.compile(r"com_[1-9]\d*")
RESEARCH_STATUS = "UNREVIEWED_SOURCE_SAMPLE"
CSV_FIELDS = (
    "review_status",
    "source_system",
    "source_province_id",
    "source_province_name",
    "source_commodity_id",
    "source_commodity_name",
    "source_unit",
    "source_row_level",
    "source_row_no",
    "source_row_name",
    "observation_date",
    "price_idr",
)


def _verified_capture(capture: SourceRows, label: str) -> None:
    if not verify_payload_text(capture.payload_text, capture.evidence.payload_sha256):
        raise PihpsInterfaceError(f"{label} raw capture hash does not match its evidence")
    if capture.evidence.source_host != "www.bi.go.id":
        raise PihpsInterfaceError(f"{label} is not from the approved PIHPS host")
    if capture.evidence.http_status != 200:
        raise PihpsInterfaceError(f"{label} source response was not successful")


def _lookup_reference(
    rows: tuple[dict[str, Any], ...],
    identifier: str,
    *,
    commodity: bool,
) -> dict[str, Any]:
    key = "commodity" if commodity else "province"
    matches = [row for row in rows if str(row.get("id", "")) == identifier]
    if len(matches) != 1:
        raise PihpsInterfaceError(f"selected {key} ID must resolve to exactly one source row")
    row = matches[0]
    if not isinstance(row.get("name"), str) or not row["name"].strip():
        raise PihpsInterfaceError(f"selected {key} has no source display name")
    if commodity and not row.get("cat_id"):
        raise PihpsInterfaceError("selected commodity must be a leaf, not a category")
    if commodity and not str(row.get("denomination", "")).strip():
        raise PihpsInterfaceError("selected commodity has no declared source unit")
    return row


def build_research_sample(
    province_capture: SourceRows,
    commodity_capture: SourceRows,
    grid_capture: SourceRows,
    request: GridRequest,
    reference_date: date,
) -> tuple[dict[str, Any], list[dict[str, str]]]:
    """Validate one small source capture and return audit metadata and raw research rows."""

    if not PROVINCE_ID_PATTERN.fullmatch(request.province_id):
        raise ValueError("source province ID must be a positive integer")
    if not COMMODITY_ID_PATTERN.fullmatch(request.comcat_id):
        raise ValueError("source commodity ID must identify one commodity")
    if (request.end_date - request.start_date).days > 14:
        raise ValueError("research capture window cannot exceed 15 calendar days")
    if request.end_date > reference_date:
        raise ValueError("research capture cannot request future dates")

    for label, capture in (
        ("province reference", province_capture),
        ("commodity reference", commodity_capture),
        ("price grid", grid_capture),
    ):
        _verified_capture(capture, label)

    validate_schema_contract(province_capture.rows, EXPECTED_PROVINCE_KEYS)
    validate_schema_contract(commodity_capture.rows, EXPECTED_COMMODITY_KEYS)
    validate_schema_contract(grid_capture.rows, EXPECTED_GRID_KEYS)
    province = _lookup_reference(province_capture.rows, request.province_id, commodity=False)
    commodity = _lookup_reference(commodity_capture.rows, request.comcat_id, commodity=True)

    if not grid_capture.rows:
        raise PihpsInterfaceError("selected PIHPS research grid contains no source rows")

    parsed = parse_grid_rows(
        grid_capture.rows,
        start_date=request.start_date,
        end_date=request.end_date,
    )
    if not parsed.points:
        raise PihpsInterfaceError("selected PIHPS research grid has no usable price points")

    # A source key is descriptive, not a canonical warehouse entity identifier.
    # Any repeat or conflicting value must be reviewed before mapping.
    keys: set[tuple[date, str, str, str]] = set()
    rows: list[dict[str, str]] = []
    for point in parsed.points:
        key = (
            point.observation_date,
            point.source_row_level,
            point.source_row_no,
            point.source_row_name,
        )
        if key in keys:
            raise PihpsInterfaceError("repeated source row key requires human review")
        keys.add(key)
        rows.append(
            {
                "review_status": RESEARCH_STATUS,
                "source_system": "PIHPS",
                "source_province_id": request.province_id,
                "source_province_name": province["name"].strip(),
                "source_commodity_id": request.comcat_id,
                "source_commodity_name": commodity["name"].strip(),
                "source_unit": str(commodity["denomination"]).strip(),
                "source_row_level": point.source_row_level,
                "source_row_no": point.source_row_no,
                "source_row_name": point.source_row_name,
                "observation_date": point.observation_date.isoformat(),
                "price_idr": format(point.price, "f"),
            }
        )
    rows.sort(
        key=lambda row: (
            row["observation_date"],
            row["source_row_level"],
            row["source_row_name"],
            row["source_row_no"],
        )
    )
    latest = max(point.observation_date for point in parsed.points)
    if latest > reference_date:
        raise PihpsInterfaceError("latest source price observation is future-dated")
    lag = (reference_date - latest).days
    review_flags = ["SOURCE_MAPPING_NOT_REVIEWED"]
    if lag > 3:
        review_flags.append("OBSERVATION_OLDER_THAN_3_DAYS")

    report = {
        "status": RESEARCH_STATUS,
        "publish_eligible": False,
        "warehouse_written": False,
        "source": "PIHPS Bank Indonesia public website interface",
        "reference_date": reference_date.isoformat(),
        "source_province_id": request.province_id,
        "source_province_name": province["name"].strip(),
        "source_commodity_id": request.comcat_id,
        "source_commodity_name": commodity["name"].strip(),
        "source_unit": str(commodity["denomination"]).strip(),
        "request_window": {
            "start": request.start_date.isoformat(),
            "end": request.end_date.isoformat(),
        },
        "source_reference_counts": {
            "provinces": len(province_capture.rows),
            "commodity_and_category_rows": len(commodity_capture.rows),
        },
        "grid_rows": len(grid_capture.rows),
        "usable_price_points": len(parsed.points),
        "missing_price_cells": parsed.missing_price_cells,
        "observed_days": len({point.observation_date for point in parsed.points}),
        "latest_price_observation_date": latest.isoformat(),
        "latest_price_observation_age_days": lag,
        "review_flags": review_flags,
        "source_evidence": {
            "http_status": grid_capture.evidence.http_status,
            "source_host": grid_capture.evidence.source_host,
            "captured_at": grid_capture.evidence.completed_at.isoformat(),
            "payload_sha256": grid_capture.evidence.payload_sha256,
            "schema_fingerprint": grid_capture.evidence.schema_fingerprint,
            "request_fingerprint": grid_capture.evidence.request_fingerprint,
        },
        "publication_note": (
            "Raw research observations only. Canonical mapping, BigQuery "
            "quality gates and active publish state have not been verified."
        ),
    }
    return report, rows


def _spreadsheet_safe(value: str) -> str:
    """Prevent spreadsheet formula execution without changing the source capture."""
    if value.lstrip().startswith(("=", "+", "-", "@")):
        return "'" + value
    return value


def write_research_sample(
    report: dict[str, Any],
    rows: list[dict[str, str]],
    output_dir: Path,
    repository_root: Path,
) -> tuple[Path, Path]:
    """Write only non-public research artifacts; never write the website tree."""

    destination = output_dir.resolve()
    root = repository_root.resolve()
    if destination.is_relative_to(root / "website"):
        raise ValueError("research data cannot be written inside the public website")
    if destination.is_relative_to(root / "sql"):
        raise ValueError("research data cannot be written inside SQL definitions")
    if report.get("status") != RESEARCH_STATUS or report.get("publish_eligible") is not False:
        raise ValueError("only unreviewed, nonpublishable research samples may be exported")
    destination.mkdir(parents=True, exist_ok=True)
    report_path = destination / "source_audit.json"
    csv_path = destination / "unreviewed_source_prices.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({name: _spreadsheet_safe(row[name]) for name in CSV_FIELDS})
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return report_path, csv_path
