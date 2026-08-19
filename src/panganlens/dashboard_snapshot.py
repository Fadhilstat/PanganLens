"""Export a public dashboard snapshot from curated BigQuery views only."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from google.cloud import bigquery

from panganlens.schema_contract import WAREHOUSE_LOCATION
from panganlens.warehouse.loader import PROJECT_ID_PATTERN

DEFAULT_LOCATION = WAREHOUSE_LOCATION
DEFAULT_MAXIMUM_BYTES_BILLED = 250_000_000


@dataclass(frozen=True, slots=True)
class DashboardSnapshot:
    """Small public payload shared by the static website dashboard."""

    generated_at: str
    publish_state: dict[str, Any] | None
    national_prices: list[dict[str, Any]]
    province_prices: list[dict[str, Any]]

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "generated_at": self.generated_at,
            "publish_state": self.publish_state,
            "national_prices": self.national_prices,
            "province_prices": self.province_prices,
        }


class BigQueryDashboardSnapshotExporter:
    """Read only dashboard-facing views with an explicit query cost ceiling."""

    def __init__(
        self,
        project_id: str,
        client: bigquery.Client | None = None,
        location: str = DEFAULT_LOCATION,
        maximum_bytes_billed: int = DEFAULT_MAXIMUM_BYTES_BILLED,
    ) -> None:
        if not PROJECT_ID_PATTERN.fullmatch(project_id):
            raise ValueError("project_id is not a valid Google Cloud project ID")
        if maximum_bytes_billed <= 0:
            raise ValueError("maximum_bytes_billed must be positive")
        self.project_id = project_id
        self.location = location
        self.maximum_bytes_billed = maximum_bytes_billed
        self.client = client or bigquery.Client(project=project_id, location=location)

    def export(self) -> DashboardSnapshot:
        queries = dashboard_snapshot_queries(self.project_id)
        publish_rows = self._query(queries["publish_state"])
        if len(publish_rows) > 1:
            raise RuntimeError("publish state returned more than one row")
        publish_state = publish_rows[0] if publish_rows else None

        return DashboardSnapshot(
            generated_at=datetime.now(UTC).isoformat(),
            publish_state=publish_state,
            national_prices=self._query(queries["national_prices"]),
            province_prices=self._query(queries["province_prices"]),
        )

    def _query(self, sql: str) -> list[dict[str, Any]]:
        config = bigquery.QueryJobConfig(maximum_bytes_billed=self.maximum_bytes_billed)
        rows = self.client.query(sql, job_config=config, location=self.location).result()
        return [_json_safe_row(dict(row.items())) for row in rows]


def dashboard_snapshot_queries(project_id: str) -> dict[str, str]:
    """Return the exact curated queries used to build the public website snapshot."""

    return {
        "publish_state": _publish_state_sql(project_id),
        "national_prices": _national_price_sql(project_id),
        "province_prices": _province_price_sql(project_id),
    }


def write_snapshot(snapshot: DashboardSnapshot, output_path: str | Path) -> None:
    """Write JSON atomically so the website never sees a partial snapshot."""

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(f"{path.suffix}.tmp")
    temporary.write_text(
        json.dumps(snapshot.as_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":")),
        encoding="utf-8",
    )
    temporary.replace(path)


def _publish_state_sql(project_id: str) -> str:
    return f"""
SELECT
  active_observation_date,
  published_at,
  active_run_status,
  rows_received,
  rows_clean,
  rows_duplicate,
  rows_conflict,
  rows_quarantined,
  observation_business_days_old,
  freshness_label
FROM `{project_id}.panganlens_mart.vw_looker_publish_state`
"""


def _national_price_sql(project_id: str) -> str:
    return f"""
WITH history AS (
  SELECT
    observation_date,
    commodity_id,
    commodity_name,
    category_name,
    commodity_display_order,
    unit_symbol,
    channel_id,
    channel_name,
    price_idr,
    LAG(price_idr) OVER (
      PARTITION BY commodity_id, channel_id
      ORDER BY observation_date
    ) AS previous_price_idr,
    ROW_NUMBER() OVER (
      PARTITION BY commodity_id, channel_id
      ORDER BY observation_date DESC, loaded_at DESC
    ) AS latest_rank
  FROM `{project_id}.panganlens_mart.vw_looker_national_price_daily`
)
SELECT
  observation_date,
  commodity_id,
  commodity_name,
  category_name,
  commodity_display_order,
  unit_symbol,
  channel_id,
  channel_name,
  price_idr,
  previous_price_idr,
  SAFE_DIVIDE(price_idr - previous_price_idr, previous_price_idr) AS daily_change_pct
FROM history
WHERE latest_rank = 1
ORDER BY commodity_display_order, commodity_name, channel_name
"""


def _province_price_sql(project_id: str) -> str:
    return f"""
SELECT
  observation_date,
  commodity_id,
  commodity_name,
  category_name,
  commodity_display_order,
  unit_symbol,
  channel_id,
  channel_name,
  province_id,
  province_name,
  price_idr,
  province_average_price_idr,
  price_gap_vs_province_average_pct
FROM `{project_id}.panganlens_mart.vw_looker_province_map`
ORDER BY commodity_display_order, commodity_name, channel_name, province_name
"""


def _json_safe_row(row: dict[str, Any]) -> dict[str, Any]:
    return {key: _json_safe_value(value) for key, value in row.items()}


def _json_safe_value(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return format(value, "f")
    return value
