from pathlib import Path

import pytest

from panganlens.bootstrap_plan_evidence_cli import (
    EXPECTED_WORKFLOW_REF,
    build_bootstrap_plan_evidence,
)


def _plan():
    return {
        "status": "CLASSIFIED_SCHEMA_ONLY",
        "plan_sha256": "a" * 64,
        "executable_statement_count": 33,
        "audit_statement_count": 2,
        "requires_explicit_apply": True,
    }


def test_build_bootstrap_plan_evidence_from_reviewed_run_metadata():
    evidence = build_bootstrap_plan_evidence(
        _plan(),
        run_id=123456789,
        workflow_ref=EXPECTED_WORKFLOW_REF,
        head_branch="main",
        head_sha="b" * 40,
        event="workflow_dispatch",
    )

    assert evidence == {
        "plan_sha256": "a" * 64,
        "plan_run_id": 123456789,
        "plan_workflow_path": ".github/workflows/bootstrap_plan.yml",
        "plan_head_branch": "main",
        "plan_head_sha": "b" * 40,
        "plan_event": "workflow_dispatch",
    }


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("run_id", 0, "positive integer"),
        (
            "workflow_ref",
            (
                "Fadhilstat/PanganLens/.github/workflows/"
                "quality.yml@refs/heads/main"
            ),
            "reviewed bootstrap plan workflow",
        ),
        ("head_branch", "feature/test", "head_branch must be main"),
        ("head_sha", "NOT-A-SHA", "40-character commit SHA"),
        ("event", "push", "event must be workflow_dispatch"),
    ],
)
def test_build_bootstrap_plan_evidence_rejects_unreviewed_run_metadata(
    field, value, message
):
    kwargs = {
        "run_id": 123456789,
        "workflow_ref": EXPECTED_WORKFLOW_REF,
        "head_branch": "main",
        "head_sha": "b" * 40,
        "event": "workflow_dispatch",
    }
    kwargs[field] = value

    with pytest.raises(ValueError, match=message):
        build_bootstrap_plan_evidence(_plan(), **kwargs)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("status", "DRY_RUN_ONLY", "plan status"),
        ("plan_sha256", "NOT-A-HASH", "plan_sha256"),
        ("requires_explicit_apply", False, "explicit apply"),
        ("executable_statement_count", 0, "executable schema statements"),
    ],
)
def test_build_bootstrap_plan_evidence_rejects_invalid_plan_contract(
    field, value, message
):
    plan = _plan()
    plan[field] = value

    with pytest.raises(ValueError, match=message):
        build_bootstrap_plan_evidence(
            plan,
            run_id=123456789,
            workflow_ref=EXPECTED_WORKFLOW_REF,
            head_branch="main",
            head_sha="b" * 40,
            event="workflow_dispatch",
        )


def test_bootstrap_plan_evidence_python_has_no_em_dash():
    source = Path("src/panganlens/bootstrap_plan_evidence_cli.py").read_text(
        encoding="utf-8"
    )
    assert "\u2014" not in source
    assert "\u2014" not in Path(__file__).read_text(encoding="utf-8")
