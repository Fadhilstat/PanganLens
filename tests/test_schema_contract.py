import re
from pathlib import Path

import pytest

from panganlens.bootstrap_executor import build_bootstrap_execution_plan
from panganlens.schema_contract import (
    REQUIRED_DATASETS,
    WAREHOUSE_LOCATION,
    WAREHOUSE_OBJECTS,
    WarehouseObject,
)

REPO_ROOT = Path(__file__).resolve().parents[1]

SCHEMA_TARGET = re.compile(
    r"CREATE\s+SCHEMA\s+IF\s+NOT\s+EXISTS\s+(panganlens_[a-z0-9_]+)\b",
    re.IGNORECASE,
)
TABLE_TARGET = re.compile(
    r"CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+"
    r"(panganlens_[a-z0-9_]+)\.([a-z0-9_]+)\b",
    re.IGNORECASE,
)
VIEW_TARGET = re.compile(
    r"CREATE\s+OR\s+REPLACE\s+VIEW\s+"
    r"(panganlens_[a-z0-9_]+)\.([a-z0-9_]+)\b",
    re.IGNORECASE,
)


def test_schema_contract_is_unique_and_uses_required_datasets():
    qualified_names = [obj.qualified_name for obj in WAREHOUSE_OBJECTS]

    assert WAREHOUSE_LOCATION == "asia-southeast2"
    assert len(qualified_names) == len(set(qualified_names))
    assert set(REQUIRED_DATASETS) == {
        "panganlens_raw",
        "panganlens_staging",
        "panganlens_core",
        "panganlens_mart",
        "panganlens_ops",
    }
    assert all(obj.dataset in REQUIRED_DATASETS for obj in WAREHOUSE_OBJECTS)


def test_schema_contract_matches_every_bootstrap_ddl_target():
    plan = build_bootstrap_execution_plan(REPO_ROOT)
    schema_targets = set()
    ddl_objects = set()

    for statement in plan.executable_statements:
        sql = statement.sql.strip()
        if match := SCHEMA_TARGET.search(sql):
            schema_targets.add(match.group(1).lower())
            continue
        if match := TABLE_TARGET.search(sql):
            ddl_objects.add((match.group(1).lower(), match.group(2).lower(), "TABLE"))
            continue
        if match := VIEW_TARGET.search(sql):
            ddl_objects.add((match.group(1).lower(), match.group(2).lower(), "VIEW"))
            continue
        raise AssertionError(f"unrecognized executable bootstrap statement: {statement.kind}")

    contract_objects = {
        (obj.dataset, obj.name, obj.object_type) for obj in WAREHOUSE_OBJECTS
    }

    assert schema_targets == set(REQUIRED_DATASETS)
    assert ddl_objects == contract_objects


def test_warehouse_object_rejects_unknown_object_type():
    with pytest.raises(ValueError, match="TABLE or VIEW"):
        WarehouseObject("panganlens_core", "bad_object", "MATERIALIZED_VIEW")
