from pathlib import Path


LOOKER_SQL = Path("sql/006_looker_semantic_views.sql")
MAP_QA_SQL = Path("sql/009_looker_map_quality.sql")
MAP_DOC = Path("docs/looker_province_map.md")


def test_looker_views_never_read_raw_or_staging():
    sql = LOOKER_SQL.read_text(encoding="utf-8").lower()
    assert "panganlens_raw." not in sql
    assert "panganlens_staging." not in sql
    assert "panganlens_core." in sql
    assert "panganlens_mart." in sql


def test_looker_prices_remain_numeric_metrics():
    sql = LOOKER_SQL.read_text(encoding="utf-8")
    assert "fact.price AS price_idr" in sql
    assert "FORMAT(" not in sql.upper()


def test_province_map_uses_curated_province_grain():
    sql = LOOKER_SQL.read_text(encoding="utf-8")
    assert "vw_looker_province_map" in sql
    assert "WHERE region_level = 'province'" in sql
    assert "region_name AS map_location" in sql
    assert "'ID' AS map_country_code" in sql
    assert "price_gap_vs_province_average_pct" in sql


def test_province_map_has_publish_quality_checks():
    sql = MAP_QA_SQL.read_text(encoding="utf-8")
    assert "province_map_unique_grain" in sql
    assert "province_map_required_fields" in sql
    assert "province_id" in sql
    assert "map_country_code != 'ID'" in sql


def test_province_map_document_requires_cross_filtering():
    text = MAP_DOC.read_text(encoding="utf-8").lower()
    assert "filled map" in text
    assert "cross-filtering: enabled" in text
    assert "country subdivision, first level" in text
    assert "reset pilihan" in text
