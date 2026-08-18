from importlib.resources import files
from pathlib import Path

import pytest

from panganlens.ingestion.mapping_operator import _activation_sql_text
from panganlens.ingestion.mapping_review import MappingReviewCandidate

REPO_ROOT = Path(__file__).resolve().parents[1]
CANONICAL_SQL = REPO_ROOT / "sql" / "016_activate_reviewed_mapping.sql"


def _candidate(**overrides):
    values = {
        "candidate_fingerprint": "a" * 64,
        "source_system": "PIHPS",
        "entity_type": "commodity",
        "source_id": "com_1",
        "source_name_normalized": None,
        "source_level": None,
        "parent_source_id": None,
        "mapping_version": 1,
        "evidence_capture_id": "capture-1",
        "source_schema_fingerprint": "b" * 64,
    }
    values.update(overrides)
    return MappingReviewCandidate(**values)


def test_packaged_activation_sql_matches_canonical_sql():
    canonical = CANONICAL_SQL.read_text(encoding="utf-8")
    packaged = files("panganlens.sql").joinpath(
        "016_activate_reviewed_mapping.sql"
    ).read_text(encoding="utf-8")

    assert packaged == canonical
    assert _activation_sql_text() == canonical


def test_mapping_candidate_rejects_non_hex_fingerprints():
    with pytest.raises(ValueError, match="candidate_fingerprint"):
        _candidate(candidate_fingerprint="g" * 64).validate()

    with pytest.raises(ValueError, match="source_schema_fingerprint"):
        _candidate(source_schema_fingerprint="z" * 64).validate()


def test_mapping_candidate_accepts_lowercase_sha256_digests():
    _candidate().validate()
