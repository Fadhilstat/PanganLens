from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from panganlens.warehouse.staging_writer import (
    BigQueryStagingWriter,
    StagingCandidate,
    StagingConflictError,
    prepare_batch,
)


class FakeJob:
    def result(self):
        return None


class FakeClient:
    def __init__(self):
        self.calls = []

    def query(self, query, job_config=None, location=None):
        self.calls.append((query, job_config, location))
        return FakeJob()


def _candidate(**overrides):
    values = {
        "run_id": "run-1",
        "capture_id": "capture-1",
        "observation_date": date(2026, 8, 17),
        "scope": "region",
        "commodity_id": "beras-medium",
        "channel_id": "traditional",
        "region_id": "jawa-barat",
        "market_id": None,
        "source_row_name": "Jawa Barat",
        "source_row_level": "province",
        "source_row_no": "1",
        "price": Decimal("14625.50"),
        "source_method": "pihps_json",
        "mapping_status": "MAPPED",
        "mapping_version": 1,
        "mapping_key_fingerprint": "a" * 64,
        "validation_status": "VALID",
        "quarantine_reason": None,
        "normalized_at": datetime(2026, 8, 17, 18, 0, tzinfo=UTC),
    }
    values.update(overrides)
    return StagingCandidate(**values)


def test_exact_duplicates_are_collapsed_before_write():
    first = _candidate()
    second = _candidate(capture_id="capture-2")

    prepared = prepare_batch([first, second])

    assert len(prepared.rows) == 1
    assert prepared.exact_duplicate_count == 1


def test_conflicting_prices_block_entire_batch():
    first = _candidate(price=Decimal("14625.50"))
    second = _candidate(capture_id="capture-2", price=Decimal("14700.00"))

    with pytest.raises(StagingConflictError):
        prepare_batch([first, second])


def test_business_key_ignores_price_but_record_hash_does_not():
    first = _candidate(price=Decimal("14625.50"))
    second = _candidate(price=Decimal("14700.00"))

    assert first.business_key_hash() == second.business_key_hash()
    assert first.record_hash() != second.record_hash()


def test_unmapped_rows_require_quarantine_reason():
    candidate = _candidate(
        commodity_id=None,
        channel_id=None,
        region_id=None,
        mapping_status="UNMAPPED",
        mapping_version=None,
        mapping_key_fingerprint=None,
        validation_status="QUARANTINED",
        quarantine_reason=None,
    )

    with pytest.raises(ValueError, match="quarantine_reason"):
        candidate.validate()


def test_decimal_price_is_preserved_as_exact_text_in_query_parameter():
    client = FakeClient()
    writer = BigQueryStagingWriter("panganlens-demo", client=client)

    writer.persist_batch([_candidate(price=Decimal("14625.50"))])

    assert len(client.calls) == 1
    _, job_config, location = client.calls[0]
    assert location == "asia-southeast2"
    parameter = job_config.query_parameters[0]
    assert '"price":"14625.50"' in parameter.value


def test_writer_uses_merge_and_parse_numeric_for_retry_safe_exact_values():
    client = FakeClient()
    writer = BigQueryStagingWriter("panganlens-demo", client=client)

    writer.persist_batch([_candidate()])

    query, _, _ = client.calls[0]
    assert "MERGE `panganlens-demo.panganlens_staging.normalized_price_candidate`" in query
    assert "PARSE_NUMERIC" in query
    assert "ROUND(" not in query.upper()
    assert "WHEN NOT MATCHED THEN" in query


def test_market_business_key_does_not_depend_on_channel_id():
    first = _candidate(
        scope="market",
        region_id=None,
        market_id="pasar-a",
        channel_id="traditional",
    )
    second = _candidate(
        scope="market",
        region_id=None,
        market_id="pasar-a",
        channel_id="other-channel",
    )

    assert first.business_key_hash() == second.business_key_hash()


def test_batch_must_have_one_run_id():
    with pytest.raises(ValueError, match="one staging batch"):
        prepare_batch([_candidate(), _candidate(run_id="run-2")])
