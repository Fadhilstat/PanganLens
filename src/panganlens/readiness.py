"""Read-only production readiness checks for PanganLens BigQuery resources."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from google.api_core.exceptions import GoogleAPICallError, NotFound
from google.cloud import bigquery

from panganlens.warehouse.loader import PROJECT_ID_PATTERN

DEFAULT_LOCATION = "asia-southeast2"
DEFAULT_MAXIMUM_BYTES_BILLED = 50_000_000

REQUIRED_DATASETS = (
    "panganlens_raw",
    "panganlens_staging",
    "panganlens_core",
    "panganlens_mart",
    "panganlens_ops",
)

REQUIRED_OBJECTS = (
    ("panganlens_ops", "pipeline_run"),
    ("panganlens_ops", "source_capture"),
    ("panganlens_ops", "publish_state"),
    ("panganlens_ops", "source_entity_mapping"),
    ("panganlens_ops", "vw_mapping_review_queue"),
    ("panganlens_mart", "vw_looker_national_price_daily"),
    ("panganlens_mart", "vw_looker_region_price_daily"),
    ("panganlens_mart", "vw_looker_province_map"),
    ("panganlens_mart", "vw_looker_publish_state"),
    ("panganlens_mart", "vw_looker_pipeline_health"),
)


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
    ) -> None:
        if not PROJECT_ID_PATTERN.fullmatch(project_id):
            raise ValueError("project_id is not a valid Google Cloud project ID")
        if maximum_bytes_billed <= 0:
            raise ValueError("maximum_bytes_billed must be positive")
        self.project_id = project_id
        self.location = location
        self.maximum_bytes_billed = maximum_bytes_billed
        self.client = client or bigquery.Client(project=project_id, location=location)

    def inspect(self) -> ReadinessReport:
        checks: list[ReadinessCheck] = []
        checks.extend(self._check_datasets())
        checks.extend(self._check_objects())

        metrics: dict[str, Any] = {}
        if all(check.status == "PASS" for check in checks):
            metrics = self._load_operational_metrics()
            checks.extend(self._operational_checks(metrics))

        status = "READY" if checks and all(check.status == "PASS" for check in checks) else "BLOCKED"
        return ReadinessReport(status=status, checks=tuple(checks), metrics=metrics)

    def _check_datasets(self) -> list[ReadinessCheck]:
        checks = []
        for dataset in REQUIRED_DATASETS:
            resource = f"{self.project_id}.{dataset}"
            try:
                self.client.get_dataset(resource)
            except NotFound:
                checks.append(ReadinessCheck(f"dataset:{dataset}", "FAIL", "Dataset belum tersedia"))
            except GoogleAPICallError as exc:
                checks.append(ReadinessCheck(f"dataset:{dataset}", "FAIL", f"Gagal membaca metadata: {type(exc).__name__}"))
            else:
                checks.append(ReadinessCheck(f"dataset:{dataset}", "PASS", "Dataset tersedia"))
        return checks

    def _check_objects(self) -> list[ReadinessCheck]:
        checks = []
        for dataset, object_name in REQUIRED_OBJECTS:
            resource = f"{self.project_id}.{dataset}.{object_name}"
            try:
                self.client.get_table(resource)
            except NotFound:
                checks.append(ReadinessCheck(f"object:{dataset}.{object_name}", "FAIL", "Tabel atau view belum tersedia"))
            except GoogleAPICallError as exc:
                checks.append(ReadinessCheck(f"object:{dataset}.{object_name}", "FAIL", f"Gagal membaca metadata: {type(exc).__name__}"))
            else:
                checks.append(ReadinessCheck(f"object:{dataset}.{object_name}", "PASS", "Tabel atau view tersedia"))
        return checks

    def _load_operational_metrics(self) -> dict[str, Any]:
        config = bigquery.QueryJobConfig(maximum_bytes_billed=self.maximum_bytes_billed)
        rows = list(self.client.query(_readiness_sql(self.project_id), job_config=config, location=self.location).result())
        if len(rows) != 1:
            raise RuntimeError("readiness query must return exactly one row")
        return dict(rows[0].items())

    @staticmethod
    def _operational_checks(metrics: dict[str, Any]) -> list[ReadinessCheck]:
        active_mappings = int(metrics.get("active_mapping_count") or 0)
        pending_reviews = int(metrics.get("pending_review_count") or 0)
        successful_captures = int(metrics.get("successful_capture_count") or 0)
        publish_rows = int(metrics.get("publish_state_count") or 0)

        return [
            ReadinessCheck(
                "mapping:active",
                "PASS" if active_mappings > 0 else "FAIL",
                f"{active_mappings} mapping aktif",
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
                "publish:public_dashboard",
                "PASS" if publish_rows == 1 else "FAIL",
                f"{publish_rows} publish pointer public_dashboard",
            ),
        ]


def _readiness_sql(project_id: str) -> str:
    return f"""
SELECT
  (
    SELECT COUNT(*)
    FROM `{project_id}.panganlens_ops.source_entity_mapping`
    WHERE mapping_status = 'ACTIVE'
      AND valid_from <= CURRENT_TIMESTAMP()
      AND (valid_to IS NULL OR valid_to > CURRENT_TIMESTAMP())
  ) AS active_mapping_count,
  (
    SELECT COUNT(*)
    FROM `{project_id}.panganlens_ops.vw_mapping_review_queue`
  ) AS pending_review_count,
  (
    SELECT COUNT(*)
    FROM `{project_id}.panganlens_ops.source_capture`
    WHERE status = 'SUCCESS'
      AND source_host = 'www.bi.go.id'
      AND payload_sha256 IS NOT NULL
  ) AS successful_capture_count,
  (
    SELECT COUNT(*)
    FROM `{project_id}.panganlens_ops.publish_state`
    WHERE state_name = 'public_dashboard'
  ) AS publish_state_count
"""
