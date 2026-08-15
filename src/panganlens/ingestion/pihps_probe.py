"""Schema-only probe logic for the PIHPS public website interface."""

from __future__ import annotations

from dataclasses import asdict
from datetime import date, timedelta

from panganlens.ingestion.pihps_interface import (
    GridRequest,
    PihpsInterfaceError,
    PihpsWebsiteClient,
    pick_reference_id,
    response_shape,
)


PROVINCE_ID_KEYS = ("province_id", "id", "value")
COMMODITY_ID_KEYS = ("comcat_id", "id", "value")


def previous_business_day(reference_date: date) -> date:
    """Return the latest completed weekday before the supplied date."""

    candidate = reference_date - timedelta(days=1)
    while candidate.weekday() >= 5:
        candidate -= timedelta(days=1)
    return candidate


def build_probe_summary(client: PihpsWebsiteClient, reference_date: date) -> dict[str, object]:
    """Probe references and one grid request without logging source row values."""

    provinces = client.fetch_reference("provinces")
    commodities = client.fetch_reference("commodities")

    if not provinces:
        raise PihpsInterfaceError("province reference response is empty")
    if not commodities:
        raise PihpsInterfaceError("commodity reference response is empty")

    province_id = pick_reference_id(
        provinces,
        PROVINCE_ID_KEYS,
        preferred="13",
    )
    commodity_id = pick_reference_id(
        commodities,
        COMMODITY_ID_KEYS,
        required_prefix="com_",
    )

    end_date = previous_business_day(reference_date)
    start_date = end_date - timedelta(days=10)
    grid_request = GridRequest(
        price_type_id=1,
        comcat_id=commodity_id,
        province_id=province_id,
        start_date=start_date,
        end_date=end_date,
        show_regencies=True,
        show_markets=False,
        report_type=1,
    )
    grid_rows = client.fetch_grid(grid_request)

    if not grid_rows:
        raise PihpsInterfaceError("grid response is empty for the probe window")

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
            "provinces": asdict(response_shape(provinces)),
            "commodities": asdict(response_shape(commodities)),
            "grid": asdict(response_shape(grid_rows)),
        },
    }
