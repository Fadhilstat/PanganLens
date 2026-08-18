from pathlib import Path

WORKFLOW = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "bigquery_readiness.yml"


def test_readiness_workflow_is_manual_and_keyless():
    text = WORKFLOW.read_text(encoding="utf-8")

    assert "workflow_dispatch:" in text
    assert "schedule:" not in text
    assert "id-token: write" in text
    assert "google-github-actions/auth@v3" in text
    assert "GCP_WIF_PROVIDER" in text
    assert "GCP_SERVICE_ACCOUNT" in text
    assert "service_account_key" not in text
    assert "credentials_json" not in text


def test_readiness_workflow_runs_read_only_cli_and_keeps_evidence():
    text = WORKFLOW.read_text(encoding="utf-8")

    assert "python -m panganlens.readiness_cli" in text
    assert "set -euo pipefail" in text
    assert "bigquery-readiness.json" in text
    assert "actions/upload-artifact@v4" in text
    assert "retention-days: 7" in text
