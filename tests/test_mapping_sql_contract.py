from pathlib import Path


def test_source_mapping_registry_is_versioned_and_reviewed():
    sql = Path("sql/008_source_mapping_registry.sql").read_text(encoding="utf-8")

    required_fields = (
        "canonical_id STRING NOT NULL",
        "mapping_version INT64 NOT NULL",
        "mapping_status STRING NOT NULL",
        "reviewed_at TIMESTAMP NOT NULL",
        "reviewed_by STRING NOT NULL",
        "valid_from TIMESTAMP NOT NULL",
        "valid_to TIMESTAMP",
    )
    for field in required_fields:
        assert field in sql


def test_active_mapping_view_only_exposes_reviewed_active_rows():
    sql = Path("sql/008_source_mapping_registry.sql").read_text(encoding="utf-8")

    assert "mapping_status = 'ACTIVE'" in sql
    assert "vw_active_source_entity_mapping" in sql
    assert "HAVING COUNT(*) > 1" in sql
