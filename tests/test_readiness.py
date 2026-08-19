from dataclasses import dataclass
from datetime import UTC, datetime

from google.api_core.exceptions import NotFound

from panganlens.cost_guard import DEFAULT_QUERY_SAFETY_BYTES, DEFAULT_STORAGE_SAFETY_BYTES
from panganlens.readiness import (
    DEFAULT_MAX_SOURCE_CAPTURE_AGE_HOURS,
    REQUIRED_DATASETS,
    REQUIRED_OBJECTS,
    BigQueryReadinessInspector,
)
from panganlens.schema_contract import WAREHOUSE_LOCATION, WAREHOUSE_OBJECTS


@dataclass
class FakeDataset:
    storage_billing_model: str | None = "LOGICAL"
    location: str = WAREHOUSE_LOCATION


@dataclass
class FakeTable:
    table_type: str


class FakeRow:
    def __init__(self, values):
        self.values = values

    def items(self):
        return self.values.items()


class FakeJob:
    def __init__(self, rows=None, total_bytes_processed=None):
        self.rows = rows or []
        self.total_bytes_processed = total_bytes_processed

    def result(self):
        return self.rows


class FakeClient:
    def __init__(
        self,
        missing_datasets=None,
        missing_objects=None,
        metrics=None,
        storage_rows=None,
        billing_models=None,
        query_estimates=None,
        object_types=None,
        dataset_locations=None,
    ):
        self.missing_datasets = set(missing_datasets or [])
        self.missing_objects = set(missing_objects or [])
        self.metrics = metrics or {}
        self.storage_rows = storage_rows or [
            {
                "dataset_name": dataset,
                "total_logical_bytes": 0,
                "billable_physical_bytes": 0,
            }
            for dataset in REQUIRED_DATASETS
        ]
        self.billing_models = billing_models or {}
        self.query_estimates = list(query_estimates or [10, 20, 30])
        self.object_types = object_types or {}
        self.dataset_locations = dataset_locations or {}
        self.expected_types = {
            warehouse_object.qualified_name: warehouse_object.object_type
            for warehouse_object in WAREHOUSE_OBJECTS
        }
        self.queries = []

    def get_dataset(self, resource):
        dataset = resource.split(".")[-1]
        if dataset in self.missing_datasets:
            raise NotFound("missing")
        return FakeDataset(
            self.billing_models.get(dataset, "LOGICAL"),
            self.dataset_locations.get(dataset, WAREHOUSE_LOCATION),
        )

    def get_table(self, resource):
        key = ".".join(resource.split(".")[-2:])
        if key in self.missing_objects:
            raise NotFound("missing")
        expected_type = self.expected_types[key]
        return FakeTable(self.object_types.get(key, expected_type))

    def query(self, query, job_config=None, location=None):
        self.queries.append((query, job_config, location))
        if "INFORMATION_SCHEMA.TABLE_STORAGE" in query:
            return FakeJob([FakeRow(row) for row in self.storage_rows])
        if job_config is not None and job_config.dry_run:
            return FakeJob(total_bytes_processed=self.query_estimates.pop(0))
        return FakeJob([FakeRow(self.metrics)])


def ready_metrics():
    return {
        "active_mapping_count": 12,
        "active_commodity_mapping_count": 4,
        "active_channel_mapping_count": 2,
        "active_region_mapping_count": 6,
        "duplicate_active_mapping_count": 0,
        "pending_review_count": 0,
        "successful_capture_count": 4,
        "latest_successful_capture_at": datetime(2026, 8, 19, 3, tzinfo=UTC),
        "latest_successful_capture_age_hours": 2,
        "valid_publish_state_count": 1,
        "national_dashboard_row_count": 10,
        "region_dashboard_row_count": 20,
        "province_dashboard_row_count": 10,
    }


def test_readiness_reports_ready_when_all_gates_pass():
    client = FakeClient(metrics=ready_metrics())
    inspector = BigQueryReadinessInspector("panganlens-demo", client=client)

    report = inspector.inspect()

    assert report.status == "READY"
    assert all(check.status == "PASS" for check in report.checks)
    assert len(client.queries) == 5
    storage_query, storage_config, storage_location = client.queries[0]
    assert "INFORMATION_SCHEMA.TABLE_STORAGE" in storage_query
    assert storage_config.maximum_bytes_billed == 50_000_000
    assert storage_location == WAREHOUSE_LOCATION

    dry_runs = client.queries[1:4]
    assert all(config.dry_run for _, config, _ in dry_runs)
    assert all(config.use_query_cache is False for _, config, _ in dry_runs)

    query, config, location = client.queries[4]
    assert "panganlens_ops.source_entity_mapping" in query
    assert "panganlens_ops.source_capture" in query
    assert "latest_successful_capture_age_hours" in query
    assert "duplicate_active_mapping_count" in query
    assert "vw_looker_province_map" in query
    assert config.maximum_bytes_billed == 50_000_000
    assert location == WAREHOUSE_LOCATION
    assert report.metrics["storage_billable_bytes"] == 0
    assert report.metrics["dashboard_query_total_bytes_processed"] == 60
    assert report.metrics["source_capture_max_age_hours"] == DEFAULT_MAX_SOURCE_CAPTURE_AGE_HOURS


def test_readiness_blocks_when_dashboard_query_exceeds_budget():
    client = FakeClient(
        metrics=ready_metrics(),
        query_estimates=[10, DEFAULT_QUERY_SAFETY_BYTES + 1, 30],
    )
    inspector = BigQueryReadinessInspector("panganlens-demo", client=client)

    report = inspector.inspect()

    assert report.status == "BLOCKED"
    query_check = next(
        check for check in report.checks if check.name == "cost:dashboard_queries"
    )
    assert query_check.status == "FAIL"
    assert len(client.queries) == 4
    assert "panganlens_ops.source_entity_mapping" not in client.queries[-1][0]


def test_readiness_blocks_when_storage_exceeds_safety_limit():
    storage_rows = [
        {
            "dataset_name": "panganlens_raw",
            "total_logical_bytes": DEFAULT_STORAGE_SAFETY_BYTES + 1,
            "billable_physical_bytes": 0,
        }
    ]
    client = FakeClient(metrics=ready_metrics(), storage_rows=storage_rows)
    inspector = BigQueryReadinessInspector("panganlens-demo", client=client)

    report = inspector.inspect()

    assert report.status == "BLOCKED"
    storage = next(check for check in report.checks if check.name == "cost:storage")
    assert storage.status == "FAIL"
    assert len(client.queries) == 1


def test_readiness_uses_physical_bytes_for_physical_dataset():
    storage_rows = [
        {
            "dataset_name": "panganlens_core",
            "total_logical_bytes": DEFAULT_STORAGE_SAFETY_BYTES + 100,
            "billable_physical_bytes": 123,
        }
    ]
    client = FakeClient(
        metrics=ready_metrics(),
        storage_rows=storage_rows,
        billing_models={"panganlens_core": "PHYSICAL"},
    )
    inspector = BigQueryReadinessInspector("panganlens-demo", client=client)

    report = inspector.inspect()

    assert report.status == "READY"
    assert report.metrics["storage_dataset_bytes"]["panganlens_core"] == 123
    assert report.metrics["storage_billing_models"]["panganlens_core"] == "PHYSICAL"


def test_readiness_blocks_when_mapping_review_is_pending():
    metrics = ready_metrics()
    metrics["pending_review_count"] = 2
    inspector = BigQueryReadinessInspector(
        "panganlens-demo",
        client=FakeClient(metrics=metrics),
    )

    report = inspector.inspect()

    assert report.status == "BLOCKED"
    pending = next(check for check in report.checks if check.name == "mapping:pending_review")
    assert pending.status == "FAIL"
    assert "2 kandidat" in pending.detail


def test_readiness_blocks_stale_source_capture():
    metrics = ready_metrics()
    metrics["latest_successful_capture_age_hours"] = DEFAULT_MAX_SOURCE_CAPTURE_AGE_HOURS + 1
    inspector = BigQueryReadinessInspector(
        "panganlens-demo",
        client=FakeClient(metrics=metrics),
    )

    report = inspector.inspect()

    assert report.status == "BLOCKED"
    source = next(check for check in report.checks if check.name == "source:fresh_capture")
    assert source.status == "FAIL"
    assert str(DEFAULT_MAX_SOURCE_CAPTURE_AGE_HOURS) in source.detail


def test_readiness_blocks_missing_or_future_source_capture_timestamp():
    missing = ready_metrics()
    missing["latest_successful_capture_at"] = None
    missing["latest_successful_capture_age_hours"] = None
    missing_report = BigQueryReadinessInspector(
        "panganlens-demo",
        client=FakeClient(metrics=missing),
    ).inspect()
    missing_check = next(
        check for check in missing_report.checks if check.name == "source:fresh_capture"
    )
    assert missing_report.status == "BLOCKED"
    assert missing_check.status == "FAIL"
    assert "completed_at" in missing_check.detail

    future = ready_metrics()
    future["latest_successful_capture_age_hours"] = -1
    future_report = BigQueryReadinessInspector(
        "panganlens-demo",
        client=FakeClient(metrics=future),
    ).inspect()
    future_check = next(
        check for check in future_report.checks if check.name == "source:fresh_capture"
    )
    assert future_report.status == "BLOCKED"
    assert future_check.status == "FAIL"
    assert "masa depan" in future_check.detail


def test_readiness_blocks_invalid_publish_pointer_and_duplicate_mapping():
    metrics = ready_metrics()
    metrics["valid_publish_state_count"] = 0
    metrics["duplicate_active_mapping_count"] = 1
    inspector = BigQueryReadinessInspector(
        "panganlens-demo",
        client=FakeClient(metrics=metrics),
    )

    report = inspector.inspect()

    assert report.status == "BLOCKED"
    checks = {check.name: check.status for check in report.checks}
    assert checks["publish:public_dashboard"] == "FAIL"
    assert checks["mapping:duplicate_active"] == "FAIL"


def test_readiness_blocks_when_dashboard_mart_is_empty():
    metrics = ready_metrics()
    metrics["province_dashboard_row_count"] = 0
    inspector = BigQueryReadinessInspector(
        "panganlens-demo",
        client=FakeClient(metrics=metrics),
    )

    report = inspector.inspect()

    assert report.status == "BLOCKED"
    province = next(check for check in report.checks if check.name == "mart:province")
    assert province.status == "FAIL"


def test_readiness_stops_before_queries_when_metadata_is_missing():
    client = FakeClient(
        missing_datasets={"panganlens_mart"},
        metrics=ready_metrics(),
    )
    inspector = BigQueryReadinessInspector("panganlens-demo", client=client)

    report = inspector.inspect()

    assert report.status == "BLOCKED"
    assert report.metrics == {}
    assert report.checks[0].name == f"dataset:{REQUIRED_DATASETS[0]}"
    assert client.queries == []


def test_readiness_blocks_wrong_dataset_location_before_queries():
    client = FakeClient(
        metrics=ready_metrics(),
        dataset_locations={"panganlens_core": "US"},
    )
    inspector = BigQueryReadinessInspector("panganlens-demo", client=client)

    report = inspector.inspect()

    assert report.status == "BLOCKED"
    check = next(
        check for check in report.checks if check.name == "dataset:panganlens_core"
    )
    assert check.status == "FAIL"
    assert "US" in check.detail
    assert WAREHOUSE_LOCATION in check.detail
    assert client.queries == []


def test_readiness_blocks_blank_dataset_location_before_queries():
    client = FakeClient(
        metrics=ready_metrics(),
        dataset_locations={"panganlens_raw": ""},
    )
    inspector = BigQueryReadinessInspector("panganlens-demo", client=client)

    report = inspector.inspect()

    assert report.status == "BLOCKED"
    check = next(
        check for check in report.checks if check.name == "dataset:panganlens_raw"
    )
    assert check.status == "FAIL"
    assert "tidak diketahui" in check.detail
    assert client.queries == []


def test_readiness_checks_all_required_objects():
    client = FakeClient(metrics=ready_metrics())
    inspector = BigQueryReadinessInspector("panganlens-demo", client=client)

    report = inspector.inspect()

    object_checks = [check for check in report.checks if check.name.startswith("object:")]
    assert len(object_checks) == len(REQUIRED_OBJECTS)
    assert any(
        check.name == "object:panganlens_mart.vw_looker_latest_region_price"
        for check in object_checks
    )


def test_readiness_blocks_wrong_object_type_before_running_queries():
    client = FakeClient(
        metrics=ready_metrics(),
        object_types={"panganlens_mart.vw_looker_publish_state": "TABLE"},
    )
    inspector = BigQueryReadinessInspector("panganlens-demo", client=client)

    report = inspector.inspect()

    assert report.status == "BLOCKED"
    check = next(
        check
        for check in report.checks
        if check.name == "object:panganlens_mart.vw_looker_publish_state"
    )
    assert check.status == "FAIL"
    assert "diharapkan VIEW" in check.detail
    assert client.queries == []


def test_readiness_rejects_invalid_project_location_and_query_ceiling():
    try:
        BigQueryReadinessInspector("Bad Project", client=FakeClient())
    except ValueError as exc:
        assert "project_id" in str(exc)
    else:
        raise AssertionError("invalid project ID should fail")

    try:
        BigQueryReadinessInspector(
            "panganlens-demo",
            client=FakeClient(),
            location=" ",
        )
    except ValueError as exc:
        assert "location" in str(exc)
    else:
        raise AssertionError("empty location should fail")

    try:
        BigQueryReadinessInspector(
            "panganlens-demo",
            client=FakeClient(),
            maximum_bytes_billed=0,
        )
    except ValueError as exc:
        assert "maximum_bytes_billed" in str(exc)
    else:
        raise AssertionError("non-positive query ceiling should fail")

    try:
        BigQueryReadinessInspector(
            "panganlens-demo",
            client=FakeClient(),
            max_source_capture_age_hours=0,
        )
    except ValueError as exc:
        assert "max_source_capture_age_hours" in str(exc)
    else:
        raise AssertionError("non-positive source age limit should fail")
