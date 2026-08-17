PROMOTION_SQL = "sql/010_promote_staging_to_core.sql"
DISPLAY_DOC = "docs/numeric_display_contract.md"


def _read_text(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def test_promotion_blocks_conflicting_hashes():
    sql = _read_text(PROMOTION_SQL)
    assert "COUNT(DISTINCT record_hash) > 1" in sql
    assert "promotion blocked: conflicting values share a business key" in sql


def test_promotion_collapses_only_exact_duplicates():
    sql = _read_text(PROMOTION_SQL)
    assert "PARTITION BY business_key_hash, record_hash" in sql
    assert "WHERE duplicate_rank = 1" in sql
    assert "COUNT(*) = COUNT(DISTINCT business_key_hash)" in sql


def test_promotion_preserves_numeric_price_without_rounding():
    sql = _read_text(PROMOTION_SQL)
    assert "price = source.price" in sql
    assert "ROUND(" not in sql.upper()
    assert "price <= 0" in sql


def test_all_fact_scopes_use_merge():
    sql = _read_text(PROMOTION_SQL)
    assert "MERGE panganlens_core.food_price_national" in sql
    assert "MERGE panganlens_core.food_price_region" in sql
    assert "MERGE panganlens_core.food_price_market" in sql


def test_source_revisions_are_recorded_before_update():
    sql = _read_text(PROMOTION_SQL)
    revision_position = sql.index("INSERT INTO panganlens_ops.revision_history")
    first_merge_position = sql.index("MERGE panganlens_core.food_price_national")
    assert revision_position < first_merge_position
    assert "ACCEPTED_SOURCE_REVISION" in sql


def test_display_contract_keeps_formatting_out_of_core():
    text = _read_text(DISPLAY_DOC).lower()
    assert "bigquery stores validated prices as `numeric`" in text
    assert "missing values are not converted to zero" in text
    assert "abbreviated values: disabled" in text
    assert "looker studio is responsible" in text
