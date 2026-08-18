from pathlib import Path

WORKFLOW = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "bigquery_readiness.yml"
AUTH_PIN = "google-github-actions/auth@7c6bc770dae815cd3e89ee6cdf493a5fab2cc093"
UPLOAD_ARTIFACT_PIN = "actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02"


def test_readiness_workflow_is_manual_direct_wif_and_keyless():
    text = WORKFLOW.read_text(encoding="utf-8")

    assert "workflow_dispatch:" in text
    assert "schedule:" not in text
    assert "github.ref == 'refs/heads/main'" in text
    assert "id-token: write" in text
    assert AUTH_PIN in text
    assert "GCP_WIF_PROVIDER" in text
    assert "GCP_SERVICE_ACCOUNT" not in text
    assert "service_account:" not in text
    assert "service_account_key" not in text
    assert "credentials_json" not in text


def test_readiness_workflow_runs_read_only_cli_and_keeps_evidence():
    text = WORKFLOW.read_text(encoding="utf-8")

    assert "python -m panganlens.readiness_cli" in text
    assert "set -euo pipefail" in text
    assert "bigquery-readiness.json" in text
    assert UPLOAD_ARTIFACT_PIN in text
    assert "retention-days: 7" in text


def test_readiness_workflow_uses_central_location_default():
    text = WORKFLOW.read_text(encoding="utf-8")

    assert "BIGQUERY_LOCATION" not in text
    assert "--location" not in text
