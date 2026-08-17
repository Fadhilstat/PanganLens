from pathlib import Path


PROMOTION_SQL = Path("sql/010_promote_staging_to_core.sql")
DISPLAY_DOC = Path("docs/numeric_display_contract.md")


def test_promotion_blocks_conflicting_hashes():
    sql = PROMOTION_SQL.read_text(encoding="utf-8")
    assert "COUNT(DISTINCT record_hash) > 1" in sql
    assert "promotion blocked: conflicting values share a business key" in sql


def test_promotion_collapses_only_exact_duplicates():
    sql = PROMOTION_SQL.read_text(encoding="utf-8")
    assert "PARTITION BY business_key_hash, record_hash" in sql
    assert "WHERE duplicate_rank = 1" in sql
    assert "COUNT(*) = COUNT(DISTINCT business_key_hash)" in sql


def test_promotion_preserves_numeric_price_without_rounding():
    sql = PROMOTION_SQL.read_text(encoding="utf-8")
    assert "price = source.price" in sql
    assert "ROUND(" not in sql.upper()
    assert "price <= 0" in sql


def test_all_fact_scopes_use_merge():
    sql = PROMOTION_SQL.read_text(encoding="utf-8")
    assert "MERGE panganlens_core.food_price_national" in sql
    assert "MERGE panganlens_core.food_price_region" in sql
    assert "MERGE panganlens_core.food_price_market" in sql


def test_source_revisions_are_recorded_before_update():
    sql = PROMOTION_SQL.read_text(encoding="utf-8")
    revision_position = sql.index("INSERT INTO panganlens_ops.revision_history")
    first_merge_position = sql.index("MERGE panganlens_core.food_price_national")
    assert revision_position < first_merge_position
    assert "ACCEPTED_SOURCE_REVISION" in sql


def test_display_contract_keeps_formatting_out_of_core():
    text = DISPLAY_DOC.read_text(encoding="utf-8").lower()
    assert "bigquery stores validated prices as `numeric`" in text
    assert "missing values are not converted to zero" in text
    assert "abbreviated values: disabled" in text
    assert "looker studio is responsible" in text
