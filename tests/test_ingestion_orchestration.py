from datetime import UTC, date, datetime

import pytest

from panganlens.ingestion.orchestration import (
    CanonicalMapping,
    IngestionContext,
    ingest_grid_capture,
)
from panganlens.ingestion.pihps_interface import (
    PihpsInterfaceError,
    SourceEvidence,
    SourceRows,
)


class FakeRawWarehouse:
    def __init__(self, events):
        self.events = events
        self.records = []

    def persist_raw_capture(self, record):
        self.events.append("raw")
        self.records.append(record)


class FakeStagingWriter:
    def __init__(self, events):
        self.events = events
        self.candidates = []

    def persist_batch(self, candidates):
        from panganlens.warehouse.staging_writer import prepare_batch

        self.events.append("staging")
        self.candidates = candidates
        return prepare_batch(candidates)


class ExactResolver:
    def __init__(self, mapping=None):
        self.mapping = mapping
        self.points = []

    def resolve(self, point, context):
        self.points.append((point, context))
        return self.mapping


def _source(rows):
    payload_text = '[{"name":"Jawa Barat"}]'
    evidence = SourceEvidence(
        source_url="https://www.bi.go.id/hargapangan/test",
        source_host="www.bi.go.id",
        content_type="application/json",
        payload_bytes=len(payload_text.encode("utf-8")),
        payload_sha256="f" * 64,
        request_fingerprint="a" * 64,
        schema_fingerprint="b" * 64,
    )
    return SourceRows(rows=tuple(rows), payload_text=payload_text, evidence=evidence)


def _context():
    return IngestionContext(
        run_id="run-1",
        capture_id="capture-1",
        source_method="pihps_json",
        scope="region",
        captured_at=datetime(2026, 8, 17, 18, 0, tzinfo=UTC),
        normalized_at=datetime(2026, 8, 17, 18, 1, tzinfo=UTC),
        request_parameters={"province_id": "13"},
        start_date=date(2026, 8, 17),
        end_date=date(2026, 8, 17),
    )


def _rows(price=14625):
    return [
        {
            "17/08/2026": price,
            "level": "province",
            "name": "Jawa Barat",
            "no": "1",
        }
    ]


def _mapping():
    return CanonicalMapping(
        commodity_id="beras-medium",
        channel_id="traditional",
        region_id="jawa-barat",
        mapping_version=1,
        mapping_key_fingerprint="c" * 64,
    )


def test_orchestration_persists_raw_before_staging():
    events = []
    raw = FakeRawWarehouse(events)
    staging = FakeStagingWriter(events)

    summary = ingest_grid_capture(
        _source(_rows()),
        _context(),
        ExactResolver(_mapping()),
        raw,
        staging,
    )

    assert events == ["raw", "staging"]
    assert summary.promotion_eligible is True
    assert summary.quarantined_rows == 0


def test_source_integrity_evidence_is_copied_to_raw_record():
    events = []
    raw = FakeRawWarehouse(events)

    ingest_grid_capture(
        _source(_rows()),
        _context(),
        ExactResolver(_mapping()),
        raw,
        FakeStagingWriter(events),
    )

    record = raw.records[0]
    assert record.request_fingerprint == "a" * 64
    assert record.schema_fingerprint == "b" * 64
    assert record.payload_sha256 == "f" * 64


def test_missing_mapping_is_quarantined_and_blocks_promotion():
    events = []
    staging = FakeStagingWriter(events)

    summary = ingest_grid_capture(
        _source(_rows()),
        _context(),
        ExactResolver(None),
        FakeRawWarehouse(events),
        staging,
    )

    candidate = staging.candidates[0]
    assert candidate.mapping_status == "UNMAPPED"
    assert candidate.validation_status == "QUARANTINED"
    assert candidate.quarantine_reason == "reviewed canonical mapping not found"
    assert summary.promotion_eligible is False


def test_missing_price_is_counted_and_never_staged_as_zero():
    events = []
    staging = FakeStagingWriter(events)

    summary = ingest_grid_capture(
        _source(_rows(price="-")),
        _context(),
        ExactResolver(_mapping()),
        FakeRawWarehouse(events),
        staging,
    )

    assert summary.missing_price_cells == 1
    assert summary.parsed_points == 0
    assert summary.staged_rows == 0
    assert staging.candidates == []


def test_raw_evidence_remains_written_when_parser_rejects_schema():
    events = []
    raw = FakeRawWarehouse(events)
    bad_rows = [
        {
            "17/08/2026": 14625,
            "level": "province",
            "name": "Jawa Barat",
            "no": "1",
            "unexpected": "field",
        }
    ]

    with pytest.raises(PihpsInterfaceError):
        ingest_grid_capture(
            _source(bad_rows),
            _context(),
            ExactResolver(_mapping()),
            raw,
            FakeStagingWriter(events),
        )

    assert events == ["raw"]


def test_mapping_resolution_keeps_exact_decimal_price():
    events = []
    staging = FakeStagingWriter(events)

    ingest_grid_capture(
        _source(_rows(price="14.625")),
        _context(),
        ExactResolver(_mapping()),
        FakeRawWarehouse(events),
        staging,
    )

    assert str(staging.candidates[0].price) == "14625"
