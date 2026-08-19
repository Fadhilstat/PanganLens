"""Read-only production readiness checks for PanganLens BigQuery resources."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from google.api_core.exceptions import GoogleAPICallError, NotFound
from google.cloud import bigquery

from panganlens.cost_guard import (
    DEFAULT_QUERY_SAFETY_BYTES,
    DEFAULT_STORAGE_SAFETY_BYTES,
    estimate_query_bytes,
    estimate_storage,
    storage_sql,
)
from panganlens.dashboard_snapshot import dashboard_snapshot_queries
from panganlens.schema_contract import (
    REQUIRED_DATASETS,
    WAREHOUSE_LOCATION,
    WAREHOUSE_OBJECTS,
)
from panganlens.warehouse.loader import PROJECT_ID_PATTERN

DEFAULT_LOCATION = WAREHOUSE_LOCATION
DEFAULT_MAXIMUM_BYTES_BILLED = 50_000_000
DEFAULT_MAX_SOURCE_CAPTURE_AGE_HOURS = 72
REQUIRED_OBJECTS = tuple((obj.dataset, obj.name) for obj in WAREHOUSE_OBJECTS)


@dataclass(frozen=True, slots=True)
class ReadinessCheck:
    name: str
    status: str
    detail: str


@dataclass(frozen=True, slots=True)
class ReadinessReport:
    status: str
    checks: tuple[ReadinessCheck, ...]
    metrics: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "checks": [asdict(check) for check in self.checks],
            "metrics": self.metrics,
        }


class BigQueryReadinessInspector:
    """Inspect production readiness without changing warehouse state."""

    def __init__(
        self,
        project_id: str,
        client: bigquery.Client | None = None,
        location: str = DEFAULT_LOCATION,
        maximum_bytes_billed: int = DEFAULT_MAXIMUM_BYTES_BILLED,
        storage_safety_bytes: int = DEFAULT_STORAGE_SAFETY_BYTES,
        query_safety_bytes: int = DEFAULT_QUERY_SAFETY_BYTES,
        max_source_capture_age_hours: int = DEFAULT_MAX_SOURCE_CAPTURE_AGE_HOURS,
    ) -> None:
        if not PROJECT_ID_PATTERN.fullmatch(project_id):
            raise ValueError("project_id is not a valid Google Cloud project ID")
        if not location.strip():
            raise ValueError("location must not be empty")
        if maximum_bytes_billed <= 0:
            raise ValueError("maximum_bytes_billed must be positive")
        if storage_safety_bytes <= 0:
            raise ValueError("storage_safety_bytes must be positive")
        if query_safety_bytes <= 0:
            raise ValueError("query_safety_bytes must be positive")
        if max_source_capture_age_hours <= 0:
            raise ValueError("max_source_capture_age_hours must be positive")
        self.project_id = project_id
        self.location = location
        self.maximum_bytes_billed = maximum_bytes_billed
        self.storage_safety_bytes = storage_safety_bytes
        self.query_safety_bytes = query_safety_bytes
        self.max_source_capture_age_hours = max_source_capture_age_hours
        self.client = client or bigquery.Client(project=project_id, location=location)

    def inspect(self) -> ReadinessReport:
        checks: list[ReadinessCheck] = []
        checks.extend(self._check_datasets())
        checks.extend(self._check_objects())

        metrics: dict[str, Any] = {}
        if all(check.status == "PASS" for check in checks):
            try:
                storage_metrics = self._load_storage_metrics()
            except (GoogleAPICallError, RuntimeError, ValueError) as exc:
                checks.append(
                    ReadinessCheck(
                        "cost:storage",
                        "FAIL",
                        f"Gagal membaca storage guard: {type(exc).__name__}",
                    )
                )
            else:
                metrics.update(storage_metrics)
                checks.append(self._storage_check(storage_metrics))

        if all(check.status == "PASS" for check in checks):
            try:
                query_metrics = self._load_dashboard_query_metrics()
            except (GoogleAPICallError, RuntimeError, ValueError) as exc:
                checks.append(
                    ReadinessCheck(
                        "cost:dashboard_queries",
                        "FAIL",
                        f"Gagal menjalankan dry-run query guard: {type(exc).__name__}",
                    )
                )
            else:
                metrics.update(query_metrics)
                checks.append(self._query_budget_check(query_metrics))

        if all(check.status == "PASS" for check in checks):
            try:
                operational_metrics = self._load_operational_metrics()
            except (GoogleAPICallError, RuntimeError) as exc:
                checks.append(
                    ReadinessCheck(
                        "query:operational_metrics",
                        "FAIL",
                        f"Gagal membaca readiness metrics: {type(exc).__name__}",
                    )
                )
            else:
                metrics.update(operational_metrics)
                checks.extend(self._operational_checks(operational_metrics))

        is_ready = bool(checks) and all(check.status == "PASS" for check in checks)
        status = "READY" if is_ready else "BLOCKED"
        return ReadinessReport(status=status, checks=tuple(checks), metrics=metrics)

    def _check_datasets(self) -> list[ReadinessCheck]:
        checks = []
        for dataset_name in REQUIRED_DATASETS:
            resource = f"{self.project_id}.{dataset_name}"
            try:
                dataset = self.client.get_dataset(resource)
            except NotFound:
                checks.append(
                    ReadinessCheck(
                        f"dataset:{dataset_name}",
                        "FAIL",
                        "Dataset belum tersedia",
                    )
                )
            except GoogleAPICallError as exc:
                checks.append(
                    ReadinessCheck(
                        f"dataset:{dataset_name}",
                        "FAIL",
                        f"Gagal membaca metadata: {type(exc).__name__}",
                    )
                )
            else:
                actual_location = str(getattr(dataset, "location", "") or "")
                location_matches = actual_location.casefold() == self.location.casefold()
                checks.append(
                    ReadinessCheck(
                        f"dataset:{dataset_name}",
                        "PASS" if location_matches else "FAIL",
                        (
                            f"Dataset tersedia di {actual_location}"
                            if location_matches
                            else (
                                f"Lokasi dataset {actual_location or 'tidak diketahui'}; "
                                f"diharapkan {self.location}"
                            )
                        ),
                    )
                )
        return checks

    def _check_objects(self) -> list[ReadinessCheck]:
        checks = []
        for warehouse_object in WAREHOUSE_OBJECTS:
            resource = (
                f"{self.project_id}.{warehouse_object.dataset}.{warehouse_object.name}"
            )
            try:
                table = self.client.get_table(resource)
            except NotFound:
                checks.append(
                    ReadinessCheck(
                        f"object:{warehouse_object.qualified_name}",
                        "FAIL",
                        f"{warehouse_object.object_type} belum tersedia",
                    )
                )
            except GoogleAPICallError as exc:
                checks.append(
                    ReadinessCheck(
                        f"object:{warehouse_object.qualified_name}",
                        "FAIL",
                        f"Gagal membaca metadata: {type(exc).__name__}",
                    )
                )
            else:
                actual_type = str(getattr(table, "table_type", "") or "").upper()
                type_matches = actual_type == warehouse_object.object_type
                checks.append(
                    ReadinessCheck(
                        f"object:{warehouse_object.qualified_name}",
                        "PASS" if type_matches else "FAIL",
                        (
                            f"{warehouse_object.object_type} tersedia"
                            if type_matches
                            else (
                                f"Tipe object {actual_type or 'tidak diketahui'}; "
                                f"diharapkan {warehouse_object.object_type}"
                            )
                        ),
                    )
                )
        return checks

    def _load_storage_metrics(self) -> dict[str, Any]:
        datasets = {
            dataset: self.client.get_dataset(f"{self.project_id}.{dataset}")
            for dataset in REQUIRED_DATASETS
        }
        config = bigquery.QueryJobConfig(
            maximum_bytes_billed=self.maximum_bytes_billed,
        )
        job = self.client.query(
            storage_sql(self.project_id, REQUIRED_DATASETS),
            job_config=config,
            location=self.location,
        )
        rows = [dict(row.items()) for row in job.result()]
        estimate = estimate_storage(
            datasets,
            rows,
            safety_bytes=self.storage_safety_bytes,
        )
        return {
            "storage_billable_bytes": estimate.billable_bytes,
            "storage_safety_bytes": estimate.safety_bytes,
            "storage_free_tier_bytes": estimate.free_tier_bytes,
            "storage_dataset_bytes": estimate.dataset_bytes,
            "storage_billing_models": estimate.billing_models,
        }

    @staticmethod
    def _storage_check(metrics: dict[str, Any]) -> ReadinessCheck:
        billable = int(metrics["storage_billable_bytes"])
        safety = int(metrics["storage_safety_bytes"])
        status = "PASS" if billable <= safety else "FAIL"
        return ReadinessCheck(
            "cost:storage",
            status,
            f"{billable} byte terukur dari batas aman {safety} byte",
        )

    def _load_dashboard_query_metrics(self) -> dict[str, Any]:
        estimate = estimate_query_bytes(
            self.client,
            dashboard_snapshot_queries(self.project_id),
            location=self.location,
            per_query_safety_bytes=self.query_safety_bytes,
        )
        return {
            "dashboard_query_total_bytes_processed": estimate.total_bytes_processed,
            "dashboard_query_safety_bytes": estimate.per_query_safety_bytes,
            "dashboard_query_total_safety_bytes": estimate.total_safety_bytes,
            "dashboard_query_bytes": estimate.query_bytes,
        }

    @staticmethod
    def _query_budget_check(metrics: dict[str, Any]) -> ReadinessCheck:
        per_query = {
            str(name): int(value)
            for name, value in dict(metrics["dashboard_query_bytes"]).items()
        }
        safety = int(metrics["dashboard_query_safety_bytes"])
        over_budget = {name: value for name, value in per_query.items() if value > safety}
        status = "PASS" if not over_budget else "FAIL"
        detail = (
            f"{len(per_query)} query dry-run di bawah {safety} byte per query"
            if not over_budget
            else f"{len(over_budget)} query dry-run melewati batas {safety} byte"
        )
        return ReadinessCheck("cost:dashboard_queries", status, detail)

    def _load_operational_metrics(self) -> dict[str, Any]:
        config = bigquery.QueryJobConfig(
            maximum_bytes_billed=self.maximum_bytes_billed,
        )
        job = self.client.query(
            _readiness_sql(self.project_id),
            job_config=config,
            location=self.location,
        )
        rows = list(job.result())
        if len(rows) != 1:
            raise RuntimeError("readiness query must return exactly one row")
        metrics = dict(rows[0].items())
        metrics["source_capture_max_age_hours"] = self.max_source_capture_age_hours
        return metrics

    def _operational_checks(self, metrics: dict[str, Any]) -> list[ReadinessCheck]:
        active_mappings = int(metrics.get("active_mapping_count") or 0)
        commodity_mappings = int(metrics.get("active_commodity_mapping_count") or 0)
        channel_mappings = int(metrics.get("active_channel_mapping_count") or 0)
        region_mappings = int(metrics.get("active_region_mapping_count") or 0)
        duplicate_mappings = int(metrics.get("duplicate_active_mapping_count") or 0)
        pending_reviews = int(metrics.get("pending_review_count") or 0)
        successful_captures = int(metrics.get("successful_capture_count") or 0)
        latest_capture_at = metrics.get("latest_successful_capture_at")
        latest_capture_age_value = metrics.get("latest_successful_capture_age_hours")
        latest_capture_age = (
            int(latest_capture_age_value)
            if latest_capture_age_value is not None
            else None
        )
        fresh_capture = (
            latest_capture_age is not None
            and 0 <= latest_capture_age <= self.max_source_capture_age_hours
        )
        valid_publish_rows = int(metrics.get("valid_publish_state_count") or 0)
        national_rows = int(metrics.get("national_dashboard_row_count") or 0)
        region_rows = int(metrics.get("region_dashboard_row_count") or 0)
        province_rows = int(metrics.get("province_dashboard_row_count") or 0)

        if latest_capture_age is None:
            capture_freshness_detail = (
                "Capture PIHPS sukses belum memiliki completed_at yang dapat dipakai"
            )
        elif latest_capture_age < 0:
            capture_freshness_detail = (
                f"Capture PIHPS terbaru {latest_capture_at or 'tidak diketahui'} memiliki "
                f"umur {latest_capture_age} jam; timestamp berada di masa depan"
            )
        else:
            capture_freshness_detail = (
                f"Capture PIHPS terbaru {latest_capture_at or 'tidak diketahui'} berumur "
                f"{latest_capture_age} jam; batas {self.max_source_capture_age_hours} jam"
            )

        return [
            ReadinessCheck(
                "mapping:active",
                "PASS" if active_mappings > 0 else "FAIL",
                f"{active_mappings} mapping aktif",
            ),
            ReadinessCheck(
                "mapping:commodity",
                "PASS" if commodity_mappings > 0 else "FAIL",
                f"{commodity_mappings} mapping komoditas aktif",
            ),
            ReadinessCheck(
                "mapping:channel",
                "PASS" if channel_mappings > 0 else "FAIL",
                f"{channel_mappings} mapping channel aktif",
            ),
            ReadinessCheck(
                "mapping:region",
                "PASS" if region_mappings > 0 else "FAIL",
                f"{region_mappings} mapping wilayah aktif",
            ),
            ReadinessCheck(
                "mapping:duplicate_active",
                "PASS" if duplicate_mappings == 0 else "FAIL",
                f"{duplicate_mappings} identitas source memiliki mapping aktif ganda",
            ),
            ReadinessCheck(
                "mapping:pending_review",
                "PASS" if pending_reviews == 0 else "FAIL",
                f"{pending_reviews} kandidat masih menunggu review",
            ),
            ReadinessCheck(
                "source:successful_capture",
                "PASS" if successful_captures > 0 else "FAIL",
                f"{successful_captures} capture sukses tersimpan",
            ),
            ReadinessCheck(
                "source:fresh_capture",
                "PASS" if fresh_capture else "FAIL",
                capture_freshness_detail,
            ),
            ReadinessCheck(
                "publish:public_dashboard",
                "PASS" if valid_publish_rows == 1 else "FAIL",
                f"{valid_publish_rows} publish pointer valid",
            ),
            ReadinessCheck(
                "mart:national",
                "PASS" if national_rows > 0 else "FAIL",
                f"{national_rows} baris dashboard nasional",
            ),
            ReadinessCheck(
                "mart:region",
                "PASS" if region_rows > 0 else "FAIL",
                f"{region_rows} baris dashboard wilayah",
            ),
            ReadinessCheck(
                "mart:province",
                "PASS" if province_rows > 0 else "FAIL",
                f"{province_rows} baris dashboard provinsi",
            ),
        ]


def _readiness_sql(project_id: str) -> str:
    return f"""
WITH active_mapping AS (
  SELECT
    source_system,
    entity_type,
    source_id,
    source_name_normalized,
    source_level,
    parent_source_id
  FROM `{project_id}.panganlens_ops.source_entity_mapping`
  WHERE mapping_status = 'ACTIVE'
    AND valid_from <= CURRENT_TIMESTAMP()
    AND (valid_to IS NULL OR valid_to > CURRENT_TIMESTAMP())
),
valid_source_capture AS (
  SELECT completed_at
  FROM `{project_id}.panganlens_ops.source_capture`
  WHERE status = 'SUCCESS'
    AND source_host = 'www.bi.go.id'
    AND payload_sha256 IS NOT NULL
    AND completed_at IS NOT NULL
)
SELECT
  (SELECT COUNT(*) FROM active_mapping) AS active_mapping_count,
  (
    SELECT COUNTIF(entity_type = 'commodity')
    FROM active_mapping
  ) AS active_commodity_mapping_count,
  (
    SELECT COUNTIF(entity_type = 'channel')
    FROM active_mapping
  ) AS active_channel_mapping_count,
  (
    SELECT COUNTIF(entity_type = 'region')
    FROM active_mapping
  ) AS active_region_mapping_count,
  (
    SELECT COUNT(*)
    FROM (
      SELECT 1
      FROM active_mapping
      GROUP BY
        source_system,
        entity_type,
        source_id,
        source_name_normalized,
        source_level,
        parent_source_id
      HAVING COUNT(*) > 1
    )
  ) AS duplicate_active_mapping_count,
  (
    SELECT COUNT(*)
    FROM `{project_id}.panganlens_ops.vw_mapping_review_queue`
  ) AS pending_review_count,
  (SELECT COUNT(*) FROM valid_source_capture) AS successful_capture_count,
  (SELECT MAX(completed_at) FROM valid_source_capture) AS latest_successful_capture_at,
  TIMESTAMP_DIFF(
    CURRENT_TIMESTAMP(),
    (SELECT MAX(completed_at) FROM valid_source_capture),
    HOUR
  ) AS latest_successful_capture_age_hours,
  (
    SELECT COUNT(*)
    FROM `{project_id}.panganlens_ops.publish_state` AS state
    INNER JOIN `{project_id}.panganlens_ops.pipeline_run` AS run
      ON state.active_run_id = run.run_id
    WHERE state.state_name = 'public_dashboard'
      AND run.status = 'SUCCESS'
      AND run.rows_conflict = 0
      AND run.rows_quarantined = 0
      AND state.active_observation_date = run.source_observation_date
  ) AS valid_publish_state_count,
  (
    SELECT COUNT(*)
    FROM `{project_id}.panganlens_mart.vw_looker_national_price_daily`
  ) AS national_dashboard_row_count,
  (
    SELECT COUNT(*)
    FROM `{project_id}.panganlens_mart.vw_looker_region_price_daily`
  ) AS region_dashboard_row_count,
  (
    SELECT COUNT(*)
    FROM `{project_id}.panganlens_mart.vw_looker_province_map`
  ) AS province_dashboard_row_count
"""
