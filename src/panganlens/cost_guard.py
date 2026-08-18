"""Read-only BigQuery cost guardrails for PanganLens production checks."""

from __future__ import annotations

from dataclasses import dataclass

from google.cloud import bigquery

FREE_TIER_STORAGE_BYTES = 10 * 1024**3
DEFAULT_STORAGE_SAFETY_BYTES = 8 * 1024**3


@dataclass(frozen=True, slots=True)
class StorageEstimate:
    """Storage estimate using each dataset's configured billing model."""

    billable_bytes: int
    safety_bytes: int
    free_tier_bytes: int
    dataset_bytes: dict[str, int]
    billing_models: dict[str, str]

    @property
    def within_safety_limit(self) -> bool:
        return self.billable_bytes <= self.safety_bytes


def normalize_storage_billing_model(value: str | None) -> str:
    """Return a supported billing model, defaulting unspecified datasets to logical."""

    if value in {None, "STORAGE_BILLING_MODEL_UNSPECIFIED", "LOGICAL"}:
        return "LOGICAL"
    if value == "PHYSICAL":
        return "PHYSICAL"
    raise ValueError(f"unsupported BigQuery storage billing model: {value}")


def estimate_storage(
    datasets: dict[str, bigquery.Dataset],
    rows: list[dict[str, object]],
    safety_bytes: int = DEFAULT_STORAGE_SAFETY_BYTES,
) -> StorageEstimate:
    """Calculate billable storage bytes for the PanganLens datasets."""

    if safety_bytes <= 0 or safety_bytes > FREE_TIER_STORAGE_BYTES:
        raise ValueError("storage safety limit must be positive and within the free tier")

    row_by_dataset = {str(row["dataset_name"]): row for row in rows}
    dataset_bytes: dict[str, int] = {}
    billing_models: dict[str, str] = {}

    for dataset_name, dataset in datasets.items():
        model = normalize_storage_billing_model(dataset.storage_billing_model)
        billing_models[dataset_name] = model
        row = row_by_dataset.get(dataset_name, {})
        if model == "PHYSICAL":
            value = int(row.get("billable_physical_bytes") or 0)
        else:
            value = int(row.get("total_logical_bytes") or 0)
        dataset_bytes[dataset_name] = value

    return StorageEstimate(
        billable_bytes=sum(dataset_bytes.values()),
        safety_bytes=safety_bytes,
        free_tier_bytes=FREE_TIER_STORAGE_BYTES,
        dataset_bytes=dataset_bytes,
        billing_models=billing_models,
    )


def storage_sql(project_id: str, datasets: tuple[str, ...]) -> str:
    """Build a stable storage snapshot query across PanganLens datasets."""

    parts = []
    for dataset in datasets:
        parts.append(
            f"""
SELECT
  '{dataset}' AS dataset_name,
  COALESCE(SUM(total_logical_bytes), 0) AS total_logical_bytes,
  COALESCE(SUM(total_physical_bytes + fail_safe_physical_bytes), 0)
    AS billable_physical_bytes
FROM `{project_id}.{dataset}.INFORMATION_SCHEMA.TABLE_STORAGE`
""".strip()
        )
    return "\nUNION ALL\n".join(parts)
