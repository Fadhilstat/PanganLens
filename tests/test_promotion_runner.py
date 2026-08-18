from pathlib import Path

import pytest

from panganlens.warehouse.promotion import (
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
        {"check_name": "duplicate_gate", "failure_count": 0, "status": "PASS"},
        {"check_name": "numeric_gate", "failure_count": 0, "status": "PASS"},
    ]


def test_ineligible_ingestion_never_queries_bigquery(tmp_path):
    client = FakeClient(_pass_rows())
    runner = BigQueryPromotionRunner(
        "panganlens-demo",
        client=client,
        sql_dir=_sql_dir(tmp_path),
    )

    with pytest.raises(PromotionBlockedError, match="not promotion eligible"):
        runner.promote("run-1", ingestion_eligible=False)

    assert client.calls == []


def test_cross_capture_audit_runs_before_prechecks(tmp_path):
    client = FakeClient(_pass_rows())
    runner = BigQueryPromotionRunner(
        "panganlens-demo",
        client=client,
        sql_dir=_sql_dir(tmp_path),
    )

    runner.promote("run-1", ingestion_eligible=True)

    assert "INSERT INTO audit_log" in client.calls[0][0]
    assert "SELECT @run_id AS run_id" in client.calls[1][0]


def test_empty_precheck_result_blocks_transaction(tmp_path):
    client = FakeClient([])
    runner = BigQueryPromotionRunner(
        "panganlens-demo",
        client=client,
        sql_dir=_sql_dir(tmp_path),
    )

    with pytest.raises(PromotionBlockedError, match="returned no results"):
        runner.promote("run-1", ingestion_eligible=True)

    assert len(client.calls) == 2


def test_nonzero_failure_count_blocks_even_when_status_says_pass(tmp_path):
    rows = [{"check_name": "duplicate_gate", "failure_count": 1, "status": "PASS"}]
    client = FakeClient(rows)
    runner = BigQueryPromotionRunner(
        "panganlens-demo",
        client=client,
        sql_dir=_sql_dir(tmp_path),
    )

    with pytest.raises(PromotionBlockedError, match="duplicate_gate"):
        runner.promote("run-1", ingestion_eligible=True)

    assert len(client.calls) == 2


def test_failed_precheck_blocks_transaction(tmp_path):
    rows = [{"check_name": "duplicate_gate", "failure_count": 1, "status": "FAIL"}]
    client = FakeClient(rows)
    runner = BigQueryPromotionRunner(
        "panganlens-demo",
        client=client,
        sql_dir=_sql_dir(tmp_path),
    )

    with pytest.raises(PromotionBlockedError, match="duplicate_gate"):
        runner.promote("run-1", ingestion_eligible=True)

    assert len(client.calls) == 2


def test_promotion_and_post_assertions_share_one_transaction(tmp_path):
    client = FakeClient(_pass_rows())
    runner = BigQueryPromotionRunner(
        "panganlens-demo",
        client=client,
        sql_dir=_sql_dir(tmp_path),
    )

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
    client = FakeClient(_pass_rows())
    runner = BigQueryPromotionRunner(
        "panganlens-demo",
        client=client,
        sql_dir=_sql_dir(tmp_path),
    )

    runner.promote("run-20260818", ingestion_eligible=True)

    for _, job_config, location in client.calls:
        assert location == "asia-southeast2"
        parameter = job_config.query_parameters[0]
        assert parameter.name == "run_id"
        assert parameter.value == "run-20260818"


def test_promotion_scope_matches_lowercase_staging_contract():
    sql = Path("sql/010_promote_staging_to_core.sql").read_text(encoding="utf-8")

    assert "scope = 'national'" in sql
    assert "scope = 'region'" in sql
    assert "scope = 'market'" in sql
    assert "scope = 'NATIONAL'" not in sql
    assert "scope = 'REGION'" not in sql
    assert "scope = 'MARKET'" not in sql


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
