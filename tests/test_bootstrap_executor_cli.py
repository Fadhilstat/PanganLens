from argparse import Namespace
from pathlib import Path

import pytest

from panganlens.bootstrap_executor import build_bootstrap_execution_plan
from panganlens.bootstrap_executor_cli import run

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_cli_defaults_to_plan_only_without_project_id():
    payload = run(
        Namespace(
            repo_root=str(REPO_ROOT),
            project_id=None,
            location="asia-southeast2",
            expected_plan_sha256=None,
            apply=False,
        )
    )

    assert payload["status"] == "CLASSIFIED_SCHEMA_ONLY"
    assert payload["requires_explicit_apply"] is True
    assert payload["executable_statement_count"] > 0


def test_cli_apply_requires_project_id_and_exact_plan_hash():
    plan = build_bootstrap_execution_plan(REPO_ROOT)

    with pytest.raises(ValueError, match="--project-id"):
        run(
            Namespace(
                repo_root=str(REPO_ROOT),
                project_id=None,
                location="asia-southeast2",
                expected_plan_sha256=plan.plan_sha256,
                apply=True,
            )
        )

    with pytest.raises(ValueError, match="--expected-plan-sha256"):
        run(
            Namespace(
                repo_root=str(REPO_ROOT),
                project_id="panganlens-demo",
                location="asia-southeast2",
                expected_plan_sha256=None,
                apply=True,
            )
        )
