"""Single source of truth for the PanganLens BigQuery schema contract."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class WarehouseObject:
    dataset: str
    name: str
    object_type: str

    def __post_init__(self) -> None:
        if self.object_type not in {"TABLE", "VIEW"}:
            raise ValueError("object_type must be TABLE or VIEW")

    @property
    def qualified_name(self) -> str:
        return f"{self.dataset}.{self.name}"


REQUIRED_DATASETS = (
    "panganlens_raw",
    "panganlens_staging",
    "panganlens_core",
    "panganlens_mart",
    "panganlens_ops",
)

WAREHOUSE_OBJECTS = (
    WarehouseObject("panganlens_raw", "raw_food_price_capture", "TABLE"),
    WarehouseObject("panganlens_staging", "normalized_price_candidate", "TABLE"),
    WarehouseObject("panganlens_core", "commodity_category", "TABLE"),
    WarehouseObject("panganlens_core", "unit", "TABLE"),
    WarehouseObject("panganlens_core", "market_channel", "TABLE"),
    WarehouseObject("panganlens_core", "commodity", "TABLE"),
    WarehouseObject("panganlens_core", "region", "TABLE"),
    WarehouseObject("panganlens_core", "market", "TABLE"),
    WarehouseObject("panganlens_core", "food_price_national", "TABLE"),
    WarehouseObject("panganlens_core", "food_price_region", "TABLE"),
    WarehouseObject("panganlens_core", "food_price_market", "TABLE"),
    WarehouseObject("panganlens_ops", "pipeline_run", "TABLE"),
    WarehouseObject("panganlens_ops", "source_capture", "TABLE"),
    WarehouseObject("panganlens_ops", "publish_state", "TABLE"),
    WarehouseObject("panganlens_ops", "data_quality_result", "TABLE"),
    WarehouseObject("panganlens_ops", "duplicate_log", "TABLE"),
    WarehouseObject("panganlens_ops", "conflict_log", "TABLE"),
    WarehouseObject("panganlens_ops", "revision_history", "TABLE"),
    WarehouseObject("panganlens_ops", "source_entity_mapping", "TABLE"),
    WarehouseObject("panganlens_ops", "vw_active_source_entity_mapping", "VIEW"),
    WarehouseObject("panganlens_ops", "source_mapping_review_candidate", "TABLE"),
    WarehouseObject("panganlens_ops", "vw_mapping_review_queue", "VIEW"),
    WarehouseObject("panganlens_mart", "vw_looker_national_price_daily", "VIEW"),
    WarehouseObject("panganlens_mart", "vw_looker_region_price_daily", "VIEW"),
    WarehouseObject("panganlens_mart", "vw_looker_latest_region_price", "VIEW"),
    WarehouseObject("panganlens_mart", "vw_looker_province_map", "VIEW"),
    WarehouseObject("panganlens_mart", "vw_looker_publish_state", "VIEW"),
    WarehouseObject("panganlens_mart", "vw_looker_pipeline_health", "VIEW"),
)

REQUIRED_OBJECTS = tuple((obj.dataset, obj.name) for obj in WAREHOUSE_OBJECTS)
