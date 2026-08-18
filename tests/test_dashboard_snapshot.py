import json
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from panganlens.dashboard_snapshot import (
    BigQueryDashboardSnapshotExporter,
    DashboardSnapshot,
    write_snapshot,
)


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
    def __init__(self, batches):
        self.batches = list(batches)
        self.calls = []

    def query(self, query, job_config=None, location=None):
        self.calls.append((query, job_config, location))
        return FakeJob(self.batches.pop(0))


def test_exporter_reads_only_curated_dashboard_views():
    client = FakeClient(
        [
            [FakeRow({"active_observation_date": date(2026, 8, 18), "freshness_label": "Terkini"})],
            [FakeRow({"commodity_id": "beras", "price_idr": Decimal("62650")})],
            [FakeRow({"province_id": "jabar", "price_idr": Decimal("63000")})],
        ]
    )
    exporter = BigQueryDashboardSnapshotExporter("panganlens-demo", client=client)

    snapshot = exporter.export()

    assert snapshot.publish_state["active_observation_date"] == "2026-08-18"
    assert snapshot.national_prices[0]["price_idr"] == 62650.0
    assert snapshot.province_prices[0]["price_idr"] == 63000.0
    assert len(client.calls) == 3
    for query, config, location in client.calls:
        assert "panganlens_mart.vw_looker_" in query
        assert "panganlens_raw" not in query
        assert "panganlens_staging" not in query
        assert config.maximum_bytes_billed == 250_000_000
        assert location == "asia-southeast2"


def test_exporter_rejects_multiple_publish_state_rows():
    client = FakeClient(
        [
            [FakeRow({"x": 1}), FakeRow({"x": 2})],
            [],
            [],
        ]
    )
    exporter = BigQueryDashboardSnapshotExporter("panganlens-demo", client=client)

    with pytest.raises(RuntimeError, match="more than one row"):
        exporter.export()


def test_write_snapshot_is_valid_json(tmp_path):
    path = tmp_path / "dashboard.json"
    snapshot = DashboardSnapshot(
        generated_at=datetime(2026, 8, 18, 12, 0, tzinfo=UTC).isoformat(),
        publish_state=None,
        national_prices=[],
        province_prices=[],
    )

    write_snapshot(snapshot, path)

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["schema_version"] == 1
    assert payload["national_prices"] == []
    assert not path.with_suffix(".json.tmp").exists()


def test_exporter_rejects_invalid_project_and_cost_limit():
    with pytest.raises(ValueError, match="project_id"):
        BigQueryDashboardSnapshotExporter("Bad Project", client=FakeClient([]))
    with pytest.raises(ValueError, match="maximum_bytes_billed"):
        BigQueryDashboardSnapshotExporter(
            "panganlens-demo",
            client=FakeClient([]),
            maximum_bytes_billed=0,
        )
