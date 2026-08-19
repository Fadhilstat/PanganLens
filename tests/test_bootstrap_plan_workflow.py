from pathlib import Path


WORKFLOW = Path(".github/workflows/bootstrap_plan.yml")


def _workflow_text() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


def test_bootstrap_plan_workflow_is_manual_and_read_only():
    text = _workflow_text()

    assert "workflow_dispatch:" in text
    assert "schedule:" not in text
    assert "pull_request:" not in text
    assert "push:" not in text
    assert "permissions:\n  contents: read" in text
    assert "id-token: write" not in text
    assert "google-github-actions/auth@" not in text


def test_bootstrap_plan_workflow_never_applies_schema():
    text = _workflow_text()

    assert "python -m panganlens.bootstrap_executor_cli" in text
    assert "--repo-root ." in text
    assert "--apply" not in text
    assert "--project-id" not in text
    assert "--expected-plan-sha256" not in text


def test_bootstrap_plan_workflow_keeps_commit_bound_artifact():
    text = _workflow_text()

    assert "panganlens-bootstrap-plan-${{ github.sha }}" in text
    assert "if-no-files-found: error" in text
    assert "retention-days: 7" in text
    assert "actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02" in text


def test_bootstrap_plan_python_contract_has_no_em_dash():
    assert "\u2014" not in _workflow_text()
    assert "\u2014" not in Path(__file__).read_text(encoding="utf-8")
