from dataclasses import dataclass

from google.api_core.exceptions import NotFound

from panganlens.bootstrap_verifier import (
    BOOTSTRAP_OBJECTS,
    EXPECTED_VIEW_NAMES,
    BigQueryBootstrapVerifier,
)
from panganlens.readiness import REQUIRED_DATASETS


@dataclass
class FakeDataset:
    location: str = "asia-southeast2"


@dataclass
class FakeTable:
    table_type: str


class FakeClient:
    def __init__(
        self,
        project="panganlens-demo",
        missing_datasets=None,
        missing_objects=None,
        dataset_locations=None,
        object_types=None,
    ):
        self.project = project
        self.missing_datasets = set(missing_datasets or [])
        self.missing_objects = set(missing_objects or [])
        self.dataset_locations = dataset_locations or {}
        self.object_types = object_types or {}
        self.dataset_reads = []
        self.table_reads = []

    def get_dataset(self, resource):
        self.dataset_reads.append(resource)
        dataset_name = resource.split(".")[-1]
        if dataset_name in self.missing_datasets:
            raise NotFound("missing dataset")
        return FakeDataset(self.dataset_locations.get(dataset_name, "asia-southeast2"))

    def get_table(self, resource):
        self.table_reads.append(resource)
        object_name = resource.split(".")[-1]
        if object_name in self.missing_objects:
            raise NotFound("missing object")
        expected_type = "VIEW" if object_name in EXPECTED_VIEW_NAMES else "TABLE"
        return FakeTable(self.object_types.get(object_name, expected_type))

    def query(self, *args, **kwargs):
        raise AssertionError("bootstrap verification must not run SQL queries")


def test_bootstrap_verifier_reports_schema_ready_from_metadata_only():
    client = FakeClient()
    verifier = BigQueryBootstrapVerifier("panganlens-demo", client=client)

    report = verifier.verify()

    assert report.status == "SCHEMA_READY"
    assert all(check.status == "PASS" for check in report.checks)
    assert len(client.dataset_reads) == len(REQUIRED_DATASETS)
    assert len(client.table_reads) == len(BOOTSTRAP_OBJECTS)
    assert len(report.checks) == len(REQUIRED_DATASETS) + len(BOOTSTRAP_OBJECTS)


def test_bootstrap_contract_includes_intermediate_region_view():
    assert (
        "panganlens_mart",
        "vw_looker_latest_region_price",
    ) in BOOTSTRAP_OBJECTS
    assert "vw_looker_latest_region_price" in EXPECTED_VIEW_NAMES


def test_bootstrap_verifier_blocks_missing_dataset():
    verifier = BigQueryBootstrapVerifier(
        "panganlens-demo",
        client=FakeClient(missing_datasets={"panganlens_core"}),
    )

    report = verifier.verify()

    assert report.status == "BLOCKED"
    check = next(check for check in report.checks if check.name == "dataset:panganlens_core")
    assert check.status == "FAIL"
    assert "belum tersedia" in check.detail


def test_bootstrap_verifier_blocks_wrong_dataset_location():
    verifier = BigQueryBootstrapVerifier(
        "panganlens-demo",
        client=FakeClient(dataset_locations={"panganlens_raw": "US"}),
    )

    report = verifier.verify()

    assert report.status == "BLOCKED"
    check = next(check for check in report.checks if check.name == "dataset:panganlens_raw")
    assert check.status == "FAIL"
    assert "US" in check.detail
    assert "asia-southeast2" in check.detail


def test_bootstrap_verifier_blocks_missing_object():
    verifier = BigQueryBootstrapVerifier(
        "panganlens-demo",
        client=FakeClient(missing_objects={"commodity"}),
    )

    report = verifier.verify()

    assert report.status == "BLOCKED"
    check = next(
        check
        for check in report.checks
        if check.name == "object:panganlens_core.commodity"
    )
    assert check.status == "FAIL"
    assert "TABLE belum tersedia" in check.detail


def test_bootstrap_verifier_blocks_wrong_object_type():
    verifier = BigQueryBootstrapVerifier(
        "panganlens-demo",
        client=FakeClient(object_types={"vw_looker_publish_state": "TABLE"}),
    )

    report = verifier.verify()

    assert report.status == "BLOCKED"
    check = next(
        check
        for check in report.checks
        if check.name == "object:panganlens_mart.vw_looker_publish_state"
    )
    assert check.status == "FAIL"
    assert "diharapkan VIEW" in check.detail


def test_bootstrap_verifier_rejects_project_mismatch_and_empty_location():
    try:
        BigQueryBootstrapVerifier(
            "panganlens-demo",
            client=FakeClient(project="another-project"),
        )
    except ValueError as exc:
        assert "does not match" in str(exc)
    else:
        raise AssertionError("project mismatch should fail")

    try:
        BigQueryBootstrapVerifier(
            "panganlens-demo",
            client=FakeClient(),
            location=" ",
        )
    except ValueError as exc:
        assert "location" in str(exc)
    else:
        raise AssertionError("empty location should fail")
