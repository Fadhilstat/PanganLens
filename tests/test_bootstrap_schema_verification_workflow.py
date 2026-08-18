from pathlib import Path

WORKFLOW = (
    Path(__file__).resolve().parents[1]
    / ".github"
    / "workflows"
    / "bootstrap_schema_verification.yml"
)
AUTH_PIN = "google-github-actions/auth@7c6bc770dae815cd3e89ee6cdf493a5fab2cc093"
CHECKOUT_PIN = "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1"
SETUP_PYTHON_PIN = "actions/setup-python@ece7cb06caefa5fff74198d8649806c4678c61a1"
UPLOAD_ARTIFACT_PIN = "actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02"


def test_bootstrap_verification_workflow_is_manual_main_only_and_keyless():
    text = WORKFLOW.read_text(encoding="utf-8")

    assert "workflow_dispatch:" in text
    assert "schedule:" not in text
    assert "github.ref == 'refs/heads/main'" in text
    assert "id-token: write" in text
    assert "GCP_PROJECT_ID" in text
    assert "GCP_WIF_PROVIDER" in text
    assert AUTH_PIN in text
    assert CHECKOUT_PIN in text
    assert SETUP_PYTHON_PIN in text
    assert "GCP_SERVICE_ACCOUNT" not in text
    assert "service_account:" not in text
    assert "credentials_json" not in text


def test_bootstrap_verification_workflow_runs_metadata_cli_and_keeps_evidence():
    text = WORKFLOW.read_text(encoding="utf-8")

    assert "python -m panganlens.bootstrap_verifier_cli" in text
    assert "python -m panganlens.bootstrap_executor_cli" not in text
    assert "--apply" not in text
    assert "set -euo pipefail" in text
    assert "bootstrap-schema-verification.json" in text
    assert UPLOAD_ARTIFACT_PIN in text
    assert "if: always()" in text
    assert "retention-days: 7" in text


def test_bootstrap_verification_workflow_uses_ci_constraints():
    text = WORKFLOW.read_text(encoding="utf-8")

    assert "python -m pip install -c constraints/ci.txt -e ." in text
