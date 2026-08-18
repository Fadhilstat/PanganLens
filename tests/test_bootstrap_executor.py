from pathlib import Path

import pytest

from panganlens.bootstrap_executor import (
    EXECUTE,
    SKIP_AUDIT,
    BigQueryBootstrapExecutor,
    build_bootstrap_execution_plan,
    classify_bootstrap_statement,
    split_sql_statements,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


class FakeJob:
    def __init__(self):
        self.timeouts = []

    def result(self, timeout=None):
        self.timeouts.append(timeout)
        return []


class FakeClient:
    def __init__(self, project="panganlens-demo"):
        self.project = project
        self.queries = []

    def query(self, sql, job_config=None, location=None):
        job = FakeJob()
        self.queries.append((sql, job_config, location, job))
        return job


def test_split_sql_statements_respects_semicolons_in_strings_and_comments():
    sql = """
    CREATE TABLE IF NOT EXISTS panganlens_ops.example (
      note STRING DEFAULT 'a;b'
    );
    -- audit; comment
    SELECT 'x;y' AS value;
    """

    statements = split_sql_statements(sql)

    assert len(statements) == 2
    assert "'a;b'" in statements[0]
    assert "'x;y'" in statements[1]


def test_classifier_allows_only_reviewed_schema_shapes():
    assert classify_bootstrap_statement(
        "CREATE SCHEMA IF NOT EXISTS panganlens_raw"
    ) == ("CREATE_SCHEMA", EXECUTE)
    assert classify_bootstrap_statement(
        "CREATE TABLE IF NOT EXISTS panganlens_core.example (id STRING)"
    ) == ("CREATE_TABLE", EXECUTE)
    assert classify_bootstrap_statement(
        "CREATE OR REPLACE VIEW panganlens_mart.example AS SELECT 1 AS value"
    ) == ("CREATE_VIEW", EXECUTE)
    assert classify_bootstrap_statement("SELECT 1") == ("READ_ONLY_AUDIT", SKIP_AUDIT)


@pytest.mark.parametrize(
    "sql",
    [
        "DROP TABLE panganlens_core.example",
        "DELETE FROM panganlens_core.example WHERE TRUE",
        "MERGE panganlens_core.example AS target USING x ON TRUE WHEN MATCHED THEN DELETE",
        "CREATE OR REPLACE TABLE panganlens_core.example AS SELECT 1 AS value",
        "CREATE TABLE IF NOT EXISTS other_dataset.example (id STRING)",
    ],
)
def test_classifier_rejects_unreviewed_or_data_changing_statements(sql):
    with pytest.raises(RuntimeError, match="unclassified"):
        classify_bootstrap_statement(sql)


def test_classifier_rejects_create_table_as_query():
    with pytest.raises(RuntimeError, match="CREATE TABLE AS"):
        classify_bootstrap_statement(
            "CREATE TABLE IF NOT EXISTS panganlens_core.example AS SELECT 1 AS value"
        )


def test_repository_plan_classifies_mixed_schema_files_without_executing_audits():
    plan = build_bootstrap_execution_plan(REPO_ROOT)

    assert plan.status == "CLASSIFIED_SCHEMA_ONLY"
    assert len(plan.plan_sha256) == 64
    assert plan.executable_statements
    assert plan.audit_statements
    assert all(statement.action == EXECUTE for statement in plan.executable_statements)
    assert all(statement.action == SKIP_AUDIT for statement in plan.audit_statements)

    audit_files = {statement.filename for statement in plan.audit_statements}
    assert "008_source_mapping_registry.sql" in audit_files
    assert "015_mapping_review_queue.sql" in audit_files
    assert all(not statement.sql.lstrip().upper().startswith("SELECT") for statement in plan.executable_statements)


def test_repository_plan_excludes_operational_sql_files():
    plan = build_bootstrap_execution_plan(REPO_ROOT)
    planned_files = {statement.filename for statement in plan.statements}

    assert "010_promote_staging_to_core.sql" not in planned_files
    assert "016_activate_reviewed_mapping.sql" not in planned_files
    assert "017_reject_mapping_candidate.sql" not in planned_files


def test_plan_hash_changes_when_schema_sql_changes(tmp_path):
    sql_dir = tmp_path / "sql"
    sql_dir.mkdir()

    from panganlens.bootstrap_plan import OPERATIONAL_SQL_FILES, SCHEMA_BOOTSTRAP_FILES

    for filename in OPERATIONAL_SQL_FILES:
        (sql_dir / filename).write_text("SELECT 1;\n", encoding="utf-8")
    for filename in SCHEMA_BOOTSTRAP_FILES:
        (sql_dir / filename).write_text(
            "CREATE TABLE IF NOT EXISTS panganlens_ops.example (id STRING);\n",
            encoding="utf-8",
        )

    first = build_bootstrap_execution_plan(tmp_path)
    target = sql_dir / SCHEMA_BOOTSTRAP_FILES[0]
    target.write_text(
        "CREATE TABLE IF NOT EXISTS panganlens_ops.example (id STRING, note STRING);\n",
        encoding="utf-8",
    )
    second = build_bootstrap_execution_plan(tmp_path)

    assert first.plan_sha256 != second.plan_sha256


def test_executor_requires_exact_reviewed_plan_hash_before_any_query():
    client = FakeClient()
    executor = BigQueryBootstrapExecutor("panganlens-demo", client=client)

    with pytest.raises(RuntimeError, match="plan changed"):
        executor.apply(REPO_ROOT, "0" * 64)

    assert client.queries == []


def test_executor_applies_only_classified_ddl_and_skips_audits():
    client = FakeClient()
    plan = build_bootstrap_execution_plan(REPO_ROOT)
    executor = BigQueryBootstrapExecutor("panganlens-demo", client=client)

    result = executor.apply(REPO_ROOT, plan.plan_sha256)

    assert result.status == "SUCCESS"
    assert result.applied_statement_count == len(plan.executable_statements)
    assert result.skipped_audit_statement_count == len(plan.audit_statements)
    assert len(client.queries) == len(plan.executable_statements)
    assert all(not sql.lstrip().upper().startswith("SELECT") for sql, *_ in client.queries)
    assert all(config.use_legacy_sql is False for _, config, _, _ in client.queries)
    assert all(location == "asia-southeast2" for _, _, location, _ in client.queries)
    assert all(job.timeouts == [120.0] for *_, job in client.queries)


def test_executor_rejects_invalid_hash_project_mismatch_and_timeout():
    client = FakeClient(project="another-project")

    with pytest.raises(ValueError, match="does not match"):
        BigQueryBootstrapExecutor("panganlens-demo", client=client)

    with pytest.raises(ValueError, match="statement_timeout_seconds"):
        BigQueryBootstrapExecutor(
            "panganlens-demo",
            client=FakeClient(),
            statement_timeout_seconds=0,
        )

    executor = BigQueryBootstrapExecutor("panganlens-demo", client=FakeClient())
    with pytest.raises(ValueError, match="lowercase SHA-256"):
        executor.apply(REPO_ROOT, "not-a-hash")
