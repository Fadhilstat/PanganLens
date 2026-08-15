from pathlib import Path


def test_looker_views_never_read_raw_or_staging():
    sql = Path("sql/006_looker_semantic_views.sql").read_text(encoding="utf-8").lower()
    assert "panganlens_raw." not in sql
    assert "panganlens_staging." not in sql
    assert "panganlens_core." in sql
    assert "panganlens_mart." in sql


def test_looker_prices_remain_numeric_metrics():
    sql = Path("sql/006_looker_semantic_views.sql").read_text(encoding="utf-8")
    assert "fact.price AS price_idr" in sql
    assert "FORMAT(" not in sql.upper()
