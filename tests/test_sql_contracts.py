from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_looker_views_do_not_read_raw_or_staging_layers():
    sql = (ROOT / "sql" / "006_looker_semantic_views.sql").read_text(encoding="utf-8")

    assert "panganlens_raw." not in sql
    assert "panganlens_staging." not in sql
    assert "panganlens_core." in sql


def test_looker_price_fields_remain_numeric_for_bi_formatting():
    sql = (ROOT / "sql" / "006_looker_semantic_views.sql").read_text(encoding="utf-8")

    assert "fact.price AS price_idr" in sql
    assert "FORMAT(" not in sql


def test_pre_staging_gate_verifies_raw_payload_hash_and_conflicts():
    sql = (ROOT / "sql" / "005_pre_staging_checks.sql").read_text(encoding="utf-8")

    assert "SHA256(payload_text)" in sql
    assert "staging_unmapped_rows_zero" in sql
    assert "staging_business_key_conflicts_zero" in sql
    assert "staging_business_keys_unique" not in sql


def test_staging_rows_keep_mapping_audit_evidence():
    staging_sql = (ROOT / "sql" / "003_raw_staging_ops.sql").read_text(encoding="utf-8")
    gate_sql = (ROOT / "sql" / "005_pre_staging_checks.sql").read_text(encoding="utf-8")

    assert "mapping_version INT64" in staging_sql
    assert "mapping_key_fingerprint STRING" in staging_sql
    assert "staging_mapping_evidence_present" in gate_sql
