from dataclasses import dataclass

import pytest

from panganlens.cost_guard import (
    DEFAULT_STORAGE_SAFETY_BYTES,
    FREE_TIER_STORAGE_BYTES,
    estimate_storage,
    normalize_storage_billing_model,
    storage_sql,
)


@dataclass
class FakeDataset:
    storage_billing_model: str | None = None


def test_unspecified_storage_billing_defaults_to_logical():
    assert normalize_storage_billing_model(None) == "LOGICAL"
    assert normalize_storage_billing_model("STORAGE_BILLING_MODEL_UNSPECIFIED") == "LOGICAL"
    assert normalize_storage_billing_model("LOGICAL") == "LOGICAL"
    assert normalize_storage_billing_model("PHYSICAL") == "PHYSICAL"


def test_unknown_storage_billing_model_is_rejected():
    with pytest.raises(ValueError, match="unsupported"):
        normalize_storage_billing_model("FUTURE_MODEL")


def test_storage_estimate_respects_each_dataset_billing_model():
    datasets = {
        "panganlens_raw": FakeDataset("LOGICAL"),
        "panganlens_core": FakeDataset("PHYSICAL"),
    }
    rows = [
        {
            "dataset_name": "panganlens_raw",
            "total_logical_bytes": 100,
            "billable_physical_bytes": 20,
        },
        {
            "dataset_name": "panganlens_core",
            "total_logical_bytes": 500,
            "billable_physical_bytes": 200,
        },
    ]

    estimate = estimate_storage(datasets, rows)

    assert estimate.billable_bytes == 300
    assert estimate.dataset_bytes == {
        "panganlens_raw": 100,
        "panganlens_core": 200,
    }
    assert estimate.billing_models["panganlens_raw"] == "LOGICAL"
    assert estimate.billing_models["panganlens_core"] == "PHYSICAL"
    assert estimate.within_safety_limit


def test_storage_estimate_blocks_before_free_tier_is_exhausted():
    datasets = {"panganlens_raw": FakeDataset("LOGICAL")}
    rows = [
        {
            "dataset_name": "panganlens_raw",
            "total_logical_bytes": DEFAULT_STORAGE_SAFETY_BYTES + 1,
            "billable_physical_bytes": 0,
        }
    ]

    estimate = estimate_storage(datasets, rows)

    assert not estimate.within_safety_limit
    assert estimate.safety_bytes < FREE_TIER_STORAGE_BYTES


def test_storage_safety_limit_cannot_exceed_free_tier():
    datasets = {"panganlens_raw": FakeDataset()}

    with pytest.raises(ValueError, match="within the free tier"):
        estimate_storage(
            datasets,
            [],
            safety_bytes=FREE_TIER_STORAGE_BYTES + 1,
        )


def test_storage_sql_counts_logical_and_physical_billable_bytes():
    sql = storage_sql(
        "panganlens-demo",
        ("panganlens_raw", "panganlens_core"),
    )

    assert "panganlens_raw.INFORMATION_SCHEMA.TABLE_STORAGE" in sql
    assert "panganlens_core.INFORMATION_SCHEMA.TABLE_STORAGE" in sql
    assert "SUM(total_logical_bytes)" in sql
    assert "SUM(total_physical_bytes + fail_safe_physical_bytes)" in sql
    assert "SELECT *" not in sql
