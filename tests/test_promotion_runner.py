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
        if len(self.calls) == 1:
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

    assert len(client.calls) == 1


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
    assert len(client.calls) == 2
    transaction_sql = client.calls[1][0]
    assert transaction_sql.startswith("BEGIN TRANSACTION;")
    assert "MERGE target" in transaction_sql
    assert "ASSERT TRUE" in transaction_sql
    assert transaction_sql.rstrip().endswith("COMMIT TRANSACTION;")
    assert transaction_sql.index("MERGE target") < transaction_sql.index("ASSERT TRUE")


def test_run_id_is_parameterized_for_checks_and_transaction(tmp_path):
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


def test_post_assertion_contract_contains_duplicate_and_numeric_gates():
    sql = Path("sql/011_post_promotion_assertions.sql").read_text(encoding="utf-8")

    assert "national business key is not unique" in sql
    assert "region business key is not unique" in sql
    assert "market business key is not unique" in sql
    assert "non-positive price" in sql
    assert "unresolved conflicts remain" in sql
