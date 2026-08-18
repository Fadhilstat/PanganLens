from google.api_core.exceptions import NotFound

from panganlens.readiness import REQUIRED_DATASETS, REQUIRED_OBJECTS, BigQueryReadinessInspector


class FakeRow:
    def __init__(self, values):
        self.values = values

    def items(self):
        return self.values.items()


class FakeJob:
    def __init__(self, rows):
        self.rows = rows

    def result(self):
        return self.rows


class FakeClient:
    def __init__(self, missing_datasets=None, missing_objects=None, metrics=None):
        self.missing_datasets = set(missing_datasets or [])
        self.missing_objects = set(missing_objects or [])
        self.metrics = metrics or {}
        self.queries = []

    def get_dataset(self, resource):
        if resource.split(".")[-1] in self.missing_datasets:
            raise NotFound("missing")
        return object()

    def get_table(self, resource):
        key = ".".join(resource.split(".")[-2:])
        if key in self.missing_objects:
            raise NotFound("missing")
        return object()

    def query(self, query, job_config=None, location=None):
        self.queries.append((query, job_config, location))
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
    assert len(client.queries) == 1
    query, config, location = client.queries[0]
    assert "panganlens_ops.source_entity_mapping" in query
    assert "panganlens_ops.source_capture" in query
    assert "run.status = 'SUCCESS'" in query
    assert "duplicate_active_mapping_count" in query
    assert "vw_looker_province_map" in query
    assert config.maximum_bytes_billed == 50_000_000
    assert location == "asia-southeast2"


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


def test_readiness_stops_before_operational_query_when_metadata_is_missing():
    inspector = BigQueryReadinessInspector(
        "panganlens-demo",
        client=FakeClient(missing_datasets={"panganlens_mart"}, metrics=ready_metrics()),
    )

    report = inspector.inspect()

    assert report.status == "BLOCKED"
    assert report.metrics == {}
    assert report.checks[0].name == f"dataset:{REQUIRED_DATASETS[0]}"


def test_readiness_checks_all_required_objects():
    client = FakeClient(metrics=ready_metrics())
    inspector = BigQueryReadinessInspector("panganlens-demo", client=client)

    report = inspector.inspect()

    object_checks = [check for check in report.checks if check.name.startswith("object:")]
    assert len(object_checks) == len(REQUIRED_OBJECTS)


def test_readiness_rejects_invalid_project_and_query_ceiling():
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
            maximum_bytes_billed=0,
        )
    except ValueError as exc:
        assert "maximum_bytes_billed" in str(exc)
    else:
        raise AssertionError("non-positive query ceiling should fail")
