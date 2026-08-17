"""Schema-only probe logic for the PIHPS public website interface."""

from __future__ import annotations

from dataclasses import asdict
from datetime import date, timedelta

from panganlens.ingestion.pihps_interface import (
    GridRequest,
    PihpsInterfaceError,
    PihpsWebsiteClient,
    SourceRows,
    pick_reference_id,
    validate_schema_contract,
)

PROVINCE_ID_KEYS = ("province_id", "id", "value")
COMMODITY_ID_KEYS = ("comcat_id", "id", "value")
EXPECTED_PROVINCE_KEYS = frozenset({"id", "name"})
EXPECTED_COMMODITY_KEYS = frozenset({"cat_id", "denomination", "id", "name", "sort"})
EXPECTED_GRID_KEYS = frozenset({"<date>", "level", "name", "no"})


def previous_business_day(reference_date: date) -> date:
    """Return the latest completed weekday before the supplied date."""

    candidate = reference_date - timedelta(days=1)
    while candidate.weekday() >= 5:
        candidate -= timedelta(days=1)
    return candidate


def build_probe_summary(client: PihpsWebsiteClient, reference_date: date) -> dict[str, object]:
    """Probe references and one grid request without logging source row values."""

    province_capture = client.fetch_reference_capture("provinces")
    commodity_capture = client.fetch_reference_capture("commodities")
    provinces = list(province_capture.rows)
    commodities = list(commodity_capture.rows)
    if not provinces:
        raise PihpsInterfaceError("province reference response is empty")
    if not commodities:
        raise PihpsInterfaceError("commodity reference response is empty")

    province_shape = validate_schema_contract(provinces, EXPECTED_PROVINCE_KEYS)
    commodity_shape = validate_schema_contract(commodities, EXPECTED_COMMODITY_KEYS)
    province_id = pick_reference_id(provinces, PROVINCE_ID_KEYS, preferred="13")
    commodity_id = pick_reference_id(
        commodities,
        COMMODITY_ID_KEYS,
        required_prefix="com_",
    )

    end_date = previous_business_day(reference_date)
    start_date = end_date - timedelta(days=10)
    request = GridRequest(
        price_type_id=1,
        comcat_id=commodity_id,
        province_id=province_id,
        start_date=start_date,
        end_date=end_date,
        show_regencies=True,
        show_markets=False,
        report_type=1,
    )
    grid_capture = client.fetch_grid_capture(request)
    grid_rows = list(grid_capture.rows)
    if not grid_rows:
        raise PihpsInterfaceError("grid response is empty for the probe window")
    grid_shape = validate_schema_contract(grid_rows, EXPECTED_GRID_KEYS)

    return {
        "status": "pass",
        "source": "PIHPS Bank Indonesia public website interface",
        "reference_date": reference_date.isoformat(),
        "probe_window": {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        },
        "selected_reference_ids": {
            "province_id": province_id,
            "commodity_id": commodity_id,
        },
        "response_shapes": {
            "provinces": asdict(province_shape),
            "commodities": asdict(commodity_shape),
            "grid": asdict(grid_shape),
        },
        "source_evidence": {
            "provinces": _safe_evidence(province_capture),
            "commodities": _safe_evidence(commodity_capture),
            "grid": _safe_evidence(grid_capture),
        },
    }


def _safe_evidence(capture: SourceRows) -> dict[str, object]:
    """Expose integrity metadata without including source row values."""

    evidence = asdict(capture.evidence)
    evidence.pop("source_url", None)
    return evidence
