from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from panganlens.ingestion.mapping_resolver import (
    BigQueryReviewedMappingResolver,
    MappingRegistryError,
    normalize_source_name,
)
from panganlens.ingestion.orchestration import IngestionContext
from panganlens.ingestion.pihps_parser import GridPricePoint


class FakeJob:
    def __init__(self, rows):
        self.rows = rows

    def result(self):
        return self.rows


class FakeClient:
    def __init__(self, rows_by_entity):
        self.rows_by_entity = rows_by_entity
        self.calls = []

    def query(self, query, job_config, location):
        params = {item.name: item.value for item in job_config.query_parameters}
        self.calls.append((query, params, location))
        return FakeJob(self.rows_by_entity.get(params["entity_type"], []))


def _context(scope="region"):
    return IngestionContext(
        run_id="run-1",
        capture_id="capture-1",
        source_method="pihps_json",
        scope=scope,
        captured_at=datetime(2026, 8, 18, 11, 0, tzinfo=UTC),
        normalized_at=datetime(2026, 8, 18, 11, 1, tzinfo=UTC),
        request_parameters={
            "comcat_id": "com_1",
            "price_type_id": 1,
            "province_id": "13",
        },
        start_date=date(2026, 8, 18),
        end_date=date(2026, 8, 18),
    )


def _point(name="Jawa Barat", level="province"):
    return GridPricePoint(
        observation_date=date(2026, 8, 18),
        source_row_name=name,
        source_row_level=level,
        source_row_no="1",
        price=Decimal("14625"),
    )


def _active_rows(version=3):
    return {
        "commodity": [{"canonical_id": "beras-medium", "mapping_version": version}],
        "channel": [{"canonical_id": "traditional", "mapping_version": version}],
        "region": [{"canonical_id": "jawa-barat", "mapping_version": version}],
    }


def test_region_point_resolves_only_from_reviewed_exact_mappings():
    client = FakeClient(_active_rows())
    resolver = BigQueryReviewedMappingResolver("panganlens-prod", client=client)

    mapping = resolver.resolve(_point(), _context())

    assert mapping is not None
    assert mapping.commodity_id == "beras-medium"
    assert mapping.channel_id == "traditional"
    assert mapping.region_id == "jawa-barat"
    assert mapping.market_id is None
    assert mapping.mapping_version == 3
    assert len(mapping.mapping_key_fingerprint) == 64
    assert {call[1]["entity_type"] for call in client.calls} == {
        "commodity",
        "channel",
        "region",
    }
    region_call = next(call for call in client.calls if call[1]["entity_type"] == "region")
    assert region_call[1]["source_name_normalized"] == "jawa barat"
    assert region_call[1]["source_level"] == "province"


def test_missing_reviewed_mapping_returns_none_and_blocks_fuzzy_guessing():
    rows = _active_rows()
    rows["region"] = []
    resolver = BigQueryReviewedMappingResolver(
        "panganlens-prod",
        client=FakeClient(rows),
    )

    assert resolver.resolve(_point(name="Jawa Barat Baru"), _context()) is None


def test_duplicate_active_mapping_fails_closed():
    rows = _active_rows()
    rows["region"] = [
        {"canonical_id": "jawa-barat", "mapping_version": 3},
        {"canonical_id": "jawa-barat-alt", "mapping_version": 3},
    ]
    resolver = BigQueryReviewedMappingResolver(
        "panganlens-prod",
        client=FakeClient(rows),
    )

    with pytest.raises(MappingRegistryError, match="more than one active mapping"):
        resolver.resolve(_point(), _context())


def test_mapping_versions_must_describe_one_reviewed_snapshot():
    rows = _active_rows()
    rows["channel"] = [{"canonical_id": "traditional", "mapping_version": 4}]
    resolver = BigQueryReviewedMappingResolver(
        "panganlens-prod",
        client=FakeClient(rows),
    )

    with pytest.raises(MappingRegistryError, match="one mapping version"):
        resolver.resolve(_point(), _context())


def test_exact_lookup_is_cached_for_repeated_points():
    client = FakeClient(_active_rows())
    resolver = BigQueryReviewedMappingResolver("panganlens-prod", client=client)

    resolver.resolve(_point(), _context())
    resolver.resolve(_point(), _context())

    assert len(client.calls) == 3


def test_request_context_requires_source_commodity_and_channel_ids():
    context = _context()
    context = IngestionContext(
        run_id=context.run_id,
        capture_id=context.capture_id,
        source_method=context.source_method,
        scope=context.scope,
        captured_at=context.captured_at,
        normalized_at=context.normalized_at,
        request_parameters={"province_id": "13"},
        start_date=context.start_date,
        end_date=context.end_date,
    )
    resolver = BigQueryReviewedMappingResolver(
        "panganlens-prod",
        client=FakeClient(_active_rows()),
    )

    with pytest.raises(ValueError, match="comcat_id"):
        resolver.resolve(_point(), context)


def test_source_name_normalization_is_deterministic_not_fuzzy():
    assert normalize_source_name("  JAWA   Barat  ") == "jawa barat"
    assert normalize_source_name("Jawa Barat") != normalize_source_name("Jawa Barat Baru")


def test_invalid_project_id_is_rejected_before_client_creation():
    with pytest.raises(ValueError, match="project_id"):
        BigQueryReviewedMappingResolver("INVALID PROJECT")
