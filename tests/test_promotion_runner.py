from pathlib import Path

import pytest

from panganlens.warehouse.promotion import (
    EXPECTED_PRECHECK_NAMES,
    BigQueryPromotionRunner,
    PromotionBlockedError,
)


class FakeJob:
    def __init__(self, rows=None):
        self.rows = rows or []

    def result(self):
        return self.rows


class FakeClient:
    def __init__(self, pre_rows):
        self.pre_rows = pre_rows
        self.calls = []

    def query(self, query, job_config=None, location=None):
        self.calls.append((query, job_config, location))
        if len(self.calls) == 2:
            return FakeJob(self.pre_rows)
        return FakeJob()


def _sql_dir(tmp_path: Path) -> Path:
    (tmp_path / "005_pre_staging_checks.sql").write_text(
        "SELECT @run_id AS run_id;",
        encoding="utf-8",
    )
    (tmp_path / "010_promote_staging_to_core.sql").write_text(
        "MERGE target USING source ON FALSE WHEN NOT MATCHED THEN INSERT ROW;",
        encoding="utf-8",
    )
    (tmp_path / "011_post_promotion_assertions.sql").write_text(
        "ASSERT TRUE AS 'post check';",
        encoding="utf-8",
    )
    (tmp_path / "013_audit_cross_capture_duplicates.sql").write_text(
        "INSERT INTO audit_log SELECT @run_id;",
        encoding="utf-8",
    )
    return tmp_path


def _pass_rows():
    return [
        {"check_name": name, "failure_count": 0, "status": "PASS"}
        for name in sorted(EXPECTED_PRECHECK_NAMES)
    ]


def _runner(tmp_path: Path, rows):
    client = FakeClient(rows)
    runner = BigQueryPromotionRunner(
        "panganlens-demo",
        client=client,
        sql_dir=_sql_dir(tmp_path),
    )
    return runner, client


def test_ineligible_ingestion_never_queries_bigquery(tmp_path):
    runner, client = _runner(tmp_path, _pass_rows())

    with pytest.raises(PromotionBlockedError, match="not promotion eligible"):
        runner.promote("run-1", ingestion_eligible=False)

    assert client.calls == []


def test_cross_capture_audit_runs_before_prechecks(tmp_path):
    runner, client = _runner(tmp_path, _pass_rows())

    runner.promote("run-1", ingestion_eligible=True)

    assert "INSERT INTO audit_log" in client.calls[0][0]
    assert "SELECT @run_id AS run_id" in client.calls[1][0]


def test_empty_precheck_result_blocks_transaction(tmp_path):
    runner, client = _runner(tmp_path, [])

    with pytest.raises(PromotionBlockedError, match="returned no results"):
        runner.promote("run-1", ingestion_eligible=True)

    assert len(client.calls) == 2


def test_missing_precheck_blocks_transaction(tmp_path):
    rows = _pass_rows()[1:]
    runner, client = _runner(tmp_path, rows)

    with pytest.raises(PromotionBlockedError, match="missing="):
        runner.promote("run-1", ingestion_eligible=True)

    assert len(client.calls) == 2


def test_unknown_precheck_blocks_transaction(tmp_path):
    rows = _pass_rows() + [
        {"check_name": "unexpected_check", "failure_count": 0, "status": "PASS"}
    ]
    runner, _ = _runner(tmp_path, rows)

    with pytest.raises(PromotionBlockedError, match="unknown=unexpected_check"):
        runner.promote("run-1", ingestion_eligible=True)


def test_duplicate_precheck_blocks_transaction(tmp_path):
    rows = _pass_rows()
    rows.append(dict(rows[0]))
    runner, _ = _runner(tmp_path, rows)

    with pytest.raises(PromotionBlockedError, match="duplicate="):
        runner.promote("run-1", ingestion_eligible=True)


def test_negative_failure_count_blocks_contract(tmp_path):
    rows = _pass_rows()
    rows[0] = {**rows[0], "failure_count": -1}
    runner, _ = _runner(tmp_path, rows)

    with pytest.raises(PromotionBlockedError, match="negative_failure_count="):
        runner.promote("run-1", ingestion_eligible=True)


def test_invalid_check_status_blocks_contract(tmp_path):
    rows = _pass_rows()
    rows[0] = {**rows[0], "status": "UNKNOWN"}
    runner, _ = _runner(tmp_path, rows)

    with pytest.raises(PromotionBlockedError, match="invalid_status="):
        runner.promote("run-1", ingestion_eligible=True)


def test_nonzero_failure_count_blocks_even_when_status_says_pass(tmp_path):
    rows = _pass_rows()
    rows[0] = {**rows[0], "failure_count": 1}
    runner, client = _runner(tmp_path, rows)

    with pytest.raises(PromotionBlockedError, match=rows[0]["check_name"]):
        runner.promote("run-1", ingestion_eligible=True)

    assert len(client.calls) == 2


def test_failed_precheck_blocks_transaction(tmp_path):
    rows = _pass_rows()
    rows[0] = {**rows[0], "failure_count": 1, "status": "FAIL"}
    runner, client = _runner(tmp_path, rows)

    with pytest.raises(PromotionBlockedError, match=rows[0]["check_name"]):
        runner.promote("run-1", ingestion_eligible=True)

    assert len(client.calls) == 2


def test_promotion_and_post_assertions_share_one_transaction(tmp_path):
    runner, client = _runner(tmp_path, _pass_rows())

    result = runner.promote("run-1", ingestion_eligible=True)

    assert result.promoted is True
    assert result.publish_eligible is True
    assert len(client.calls) == 3
    transaction_sql = client.calls[2][0]
    assert transaction_sql.startswith("BEGIN TRANSACTION;")
    assert "MERGE target" in transaction_sql
    assert "ASSERT TRUE" in transaction_sql
    assert transaction_sql.rstrip().endswith("COMMIT TRANSACTION;")
    assert transaction_sql.index("MERGE target") < transaction_sql.index("ASSERT TRUE")


def test_run_id_is_parameterized_for_audit_checks_and_transaction(tmp_path):
    runner, client = _runner(tmp_path, _pass_rows())

    runner.promote("run-20260818", ingestion_eligible=True)

    for _, job_config, location in client.calls:
        assert location == "asia-southeast2"
        parameter = job_config.query_parameters[0]
        assert parameter.name == "run_id"
        assert parameter.value == "run-20260818"


def test_invalid_project_id_is_rejected_before_client_creation():
    with pytest.raises(ValueError, match="project_id"):
        BigQueryPromotionRunner("INVALID PROJECT")


def test_promotion_scope_matches_lowercase_staging_contract():
    sql = Path("sql/010_promote_staging_to_core.sql").read_text(encoding="utf-8")

    assert "scope = 'national'" in sql
    assert "scope = 'region'" in sql
    assert "scope = 'market'" in sql
    assert "scope = 'NATIONAL'" not in sql
    assert "scope = 'REGION'" not in sql
    assert "scope = 'MARKET'" not in sql


def test_promotion_batch_must_not_be_empty():
    sql = Path("sql/010_promote_staging_to_core.sql").read_text(encoding="utf-8")

    assert "SELECT COUNT(*) > 0" in sql
    assert "promotion blocked: promotion batch is empty" in sql


def test_cross_capture_audit_is_idempotent_and_logs_true_conflicts():
    sql = Path("sql/013_audit_cross_capture_duplicates.sql").read_text(encoding="utf-8")

    assert "panganlens_ops.duplicate_log" in sql
    assert "panganlens_ops.conflict_log" in sql
    assert "COUNT(DISTINCT capture_id) > 1" in sql
    assert "COUNT(DISTINCT record_hash) > 1" in sql
    assert "resolution_status" in sql
    assert "'OPEN'" in sql
    assert "NOT EXISTS" in sql


def test_precheck_allows_exact_duplicates_but_blocks_conflicting_hashes():
    sql = Path("sql/005_pre_staging_checks.sql").read_text(encoding="utf-8")

    assert "staging_business_key_conflicts_zero" in sql
    assert "HAVING COUNT(DISTINCT record_hash) > 1" in sql
    assert "staging_business_keys_unique" not in sql


def test_post_assertion_contract_contains_duplicate_numeric_and_reconciliation_gates():
    sql = Path("sql/011_post_promotion_assertions.sql").read_text(encoding="utf-8")

    assert "national business key is not unique" in sql
    assert "region business key is not unique" in sql
    assert "market business key is not unique" in sql
    assert "non-positive price" in sql
    assert "unresolved conflicts remain" in sql
    assert "national row missing from core" in sql
    assert "region row missing from core" in sql
    assert "market row missing from core" in sql


def test_post_assertion_contract_enforces_dimension_and_fact_references():
    sql = Path("sql/011_post_promotion_assertions.sql").read_text(encoding="utf-8")

    assert "dimension primary key is not unique" in sql
    assert "commodity foreign key is invalid" in sql
    assert "market foreign key is invalid" in sql
    assert "region parent reference is invalid" in sql
    assert "national price has an unknown commodity" in sql
    assert "national price has an unknown channel" in sql
    assert "region price has an unknown commodity" in sql
    assert "region price has an unknown channel" in sql
    assert "region price has an unknown region" in sql
    assert "market price has an unknown commodity" in sql
    assert "market price has an unknown market" in sql


def test_post_load_checks_cover_all_fact_foreign_keys():
    sql = Path("sql/004_post_load_checks.sql").read_text(encoding="utf-8")

    expected_checks = {
        "national_prices_have_known_commodities",
        "national_prices_have_known_channels",
        "region_prices_have_known_commodities",
        "region_prices_have_known_channels",
        "region_prices_have_known_regions",
        "market_prices_have_known_commodities",
        "market_prices_have_known_markets",
    }
    for check_name in expected_checks:
        assert check_name in sql
