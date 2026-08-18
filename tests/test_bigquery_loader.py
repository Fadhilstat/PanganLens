import hashlib
from datetime import UTC, datetime

import pytest

from panganlens.warehouse.loader import BigQueryWarehouse, RawCaptureRecord


class FakeJob:
    def __init__(self):
        self.result_called = False

    def result(self):
        self.result_called = True
        return []


class FakeClient:
    def __init__(self):
        self.calls = []
        self.job = FakeJob()

    def query(self, query, job_config=None, location=None):
        self.calls.append((query, job_config, location))
        return self.job


def _record(payload_text='{"ok":true}'):
    payload = payload_text.encode("utf-8")
    digest = hashlib.sha256(payload).hexdigest()
    requested_at = datetime(2026, 8, 17, 17, 59, tzinfo=UTC)
    completed_at = datetime(2026, 8, 17, 18, 0, tzinfo=UTC)
    return RawCaptureRecord(
        capture_id="capture-001",
        run_id="run-001",
        captured_at=completed_at,
        source_method="pihps_json",
        request_parameters={"province_id": "13", "price_type_id": 1},
        request_fingerprint="1" * 64,
        schema_fingerprint="2" * 64,
        payload_text=payload_text,
        payload_bytes=len(payload),
        payload_sha256=digest,
        source_name="PIHPS Bank Indonesia public website interface",
        source_url="https://www.bi.go.id/hargapangan/test",
        source_host="www.bi.go.id",
        content_type="application/json",
        requested_at=requested_at,
        completed_at=completed_at,
        http_status=200,
    )


def test_raw_capture_rejects_payload_hash_mismatch():
    record = _record()
    broken = RawCaptureRecord(
        capture_id=record.capture_id,
        run_id=record.run_id,
        captured_at=record.captured_at,
        source_method=record.source_method,
        request_parameters=record.request_parameters,
        request_fingerprint=record.request_fingerprint,
        schema_fingerprint=record.schema_fingerprint,
        payload_text=record.payload_text,
        payload_bytes=record.payload_bytes,
        payload_sha256="0" * 64,
        source_name=record.source_name,
        source_url=record.source_url,
        source_host=record.source_host,
        content_type=record.content_type,
        requested_at=record.requested_at,
        completed_at=record.completed_at,
        http_status=record.http_status,
    )

    with pytest.raises(ValueError, match="does not match payload_text"):
        broken.validate()


def test_raw_capture_requires_timezone_aware_timestamp():
    record = _record()
    broken = RawCaptureRecord(
        capture_id=record.capture_id,
        run_id=record.run_id,
        captured_at=datetime(2026, 8, 17, 18, 0),
        source_method=record.source_method,
        request_parameters=record.request_parameters,
        request_fingerprint=record.request_fingerprint,
        schema_fingerprint=record.schema_fingerprint,
        payload_text=record.payload_text,
        payload_bytes=record.payload_bytes,
        payload_sha256=record.payload_sha256,
        source_name=record.source_name,
        source_url=record.source_url,
        source_host=record.source_host,
        content_type=record.content_type,
        requested_at=record.requested_at,
        completed_at=record.completed_at,
        http_status=record.http_status,
    )

    with pytest.raises(ValueError, match="timezone-aware"):
        broken.validate()


def test_loader_persists_capture_audit_and_raw_payload_together():
    client = FakeClient()
    warehouse = BigQueryWarehouse("panganlens-demo", client=client)

    warehouse.persist_raw_capture(_record())

    query, job_config, location = client.calls[0]
    assert "panganlens_ops.source_capture" in query
    assert "panganlens_raw.raw_food_price_capture" in query
    assert "ASSERT existing_hash IS NULL OR existing_hash = @payload_sha256" in query
    assert "different request fingerprint" in query
    assert "different schema fingerprint" in query
    assert query.count("ON target.capture_id = source.capture_id") == 2
    assert location == "asia-southeast2"
    assert len(job_config.query_parameters) == 18
    assert client.job.result_called is True


def test_loader_rejects_invalid_project_id():
    with pytest.raises(ValueError, match="project_id"):
        BigQueryWarehouse("Bad Project ID", client=FakeClient())
