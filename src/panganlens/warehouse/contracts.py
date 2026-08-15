"""Stable dataset names and fact-table grains used by the warehouse layer."""

from dataclasses import dataclass

DATASETS = (
    "panganlens_raw",
    "panganlens_staging",
    "panganlens_core",
    "panganlens_mart",
    "panganlens_ops",
)


@dataclass(frozen=True, slots=True)
class FactContract:
    """Describe the grain that must remain unique in a fact table."""

    table_name: str
    key_columns: tuple[str, ...]


FACT_CONTRACTS = (
    FactContract(
        table_name="food_price_national",
        key_columns=("observation_date", "commodity_id", "channel_id"),
    ),
    FactContract(
        table_name="food_price_region",
        key_columns=("observation_date", "commodity_id", "channel_id", "region_id"),
    ),
    FactContract(
        table_name="food_price_market",
        key_columns=("observation_date", "commodity_id", "market_id"),
    ),
)
