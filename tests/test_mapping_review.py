from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

from panganlens.ingestion.mapping_review import build_mapping_candidates
from panganlens.ingestion.orchestration import IngestionContext
from panganlens.ingestion.pihps_parser import GridPricePoint


ACTIVATION_SQL = Path("sql/016_activate_reviewed_mapping.sql")
QUEUE_SQL = Path("sql/015_mapping_review_queue.sql")


def _context(scope: str = "region") -> IngestionContext:
    return IngestionContext(
        run_id="run-review-1",
        capture_id="capture-review-1",
        source_method="pihps_website_json",
        scope=scope,
        captured_at=datetime(2026, 8, 18, 12, 0, tzinfo=UTC),
        normalized_at=datetime(2026, 8, 18, 12, 0, tzinfo=UTC),
        request_parameters={
            "price_type_id": 1,
            "comcat_id": "com_1",
            "province_id": "13",
        },
        start_date=date(2026, 8, 17),
        end_date=date(2026, 8, 17),
    )


def _point(name: str = "DKI Jakarta", level: str = "Provinsi") -> GridPricePoint:
    return GridPricePoint(
        observation_date=date(2026, 8, 17),
        source_row_name=name,
        source_row_level=level,
        source_row_no="1",
        price=Decimal("62650"),
    )


def test_region_candidates_use_exact_resolver_identity_without_canonical_guess():
    candidates = build_mapping_candidates(
        [_point(), _point()],
        _context(),
        mapping_version=1,
        source_schema_fingerprint="a" * 64,
    )

    assert len(candidates) == 3
    by_type = {candidate.entity_type: candidate for candidate in candidates}
    assert by_type["commodity"].source_id == "com_1"
    assert by_type["channel"].source_id == "1"
    assert by_type["region"].source_name_normalized == "dki jakarta"
    assert by_type["region"].source_level == "provinsi"
    assert all(candidate.evidence_capture_id == "capture-review-1" for candidate in candidates)
    assert all(len(candidate.candidate_fingerprint) == 64 for candidate in candidates)


def test_market_candidate_keeps_province_parent_source_id():
    candidates = build_mapping_candidates(
        [_point("Pasar Senen", "Pasar")],
        _context(scope="market"),
        mapping_version=2,
        source_schema_fingerprint="b" * 64,
    )

    market = next(item for item in candidates if item.entity_type == "market")
    assert market.source_name_normalized == "pasar senen"
    assert market.source_level == "pasar"
    assert market.parent_source_id == "13"


def test_candidate_fingerprint_is_deterministic_across_capture_retries():
    first = build_mapping_candidates(
        [_point()],
        _context(),
        mapping_version=3,
        source_schema_fingerprint="c" * 64,
    )
    retry_context = _context()
    object.__setattr__(retry_context, "capture_id", "capture-review-2")
    second = build_mapping_candidates(
        [_point()],
        retry_context,
        mapping_version=3,
        source_schema_fingerprint="d" * 64,
    )

    assert [item.candidate_fingerprint for item in first] == [
        item.candidate_fingerprint for item in second
    ]


def test_review_queue_starts_without_a_canonical_decision():
    text = QUEUE_SQL.read_text(encoding="utf-8")

    assert "'REVIEW_REQUIRED'" in text
    assert "proposed_canonical_id STRING" in text
    assert "WHERE review_status = 'REVIEW_REQUIRED'" in text


def test_activation_requires_human_review_provenance_and_valid_canonical_id():
    text = ACTIVATION_SQL.read_text(encoding="utf-8")

    assert "reviewed_by must not be empty" in text
    assert "mapping candidate source evidence is missing or inconsistent" in text
    assert "canonical_id does not exist for the candidate entity type" in text
    assert "active mapping version must be older than the reviewed candidate" in text
    assert "mapping_status = 'SUPERSEDED'" in text
    assert "'ACTIVE'" in text
    assert "review_status = 'APPROVED'" in text
    assert "BEGIN TRANSACTION;" in text
    assert "COMMIT TRANSACTION;" in text
