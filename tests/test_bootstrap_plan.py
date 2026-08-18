from pathlib import Path

import pytest

from panganlens.bootstrap_plan import (
    OPERATIONAL_SQL_FILES,
    SCHEMA_BOOTSTRAP_FILES,
    build_bootstrap_plan,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_bootstrap_plan_is_schema_only_and_deterministic():
    plan = build_bootstrap_plan(REPO_ROOT)

    assert plan.status == "DRY_RUN_ONLY"
    assert [step.filename for step in plan.steps] == list(SCHEMA_BOOTSTRAP_FILES)
    assert plan.operational_files_excluded == OPERATIONAL_SQL_FILES
    assert all(len(step.sha256) == 64 for step in plan.steps)
    assert all(step.bytes > 0 for step in plan.steps)


def test_bootstrap_plan_excludes_data_changing_operational_sql():
    plan = build_bootstrap_plan(REPO_ROOT)
    planned = {step.filename for step in plan.steps}

    assert "010_promote_staging_to_core.sql" not in planned
    assert "016_activate_reviewed_mapping.sql" not in planned
    assert "011_post_promotion_assertions.sql" not in planned


def test_bootstrap_plan_fails_when_sql_contract_drifts(tmp_path):
    sql_dir = tmp_path / "sql"
    sql_dir.mkdir()
    for filename in (*SCHEMA_BOOTSTRAP_FILES, *OPERATIONAL_SQL_FILES):
        (sql_dir / filename).write_text("SELECT 1;\n", encoding="utf-8")
    (sql_dir / "999_unclassified.sql").write_text("SELECT 1;\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match="unclassified"):
        build_bootstrap_plan(tmp_path)
