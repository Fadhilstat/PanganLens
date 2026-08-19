from pathlib import Path

AUTH_PIN = "google-github-actions/auth@7c6bc770dae815cd3e89ee6cdf493a5fab2cc093"
CLOUD_VALIDATION = "python -m panganlens.cloud_config_cli"
WORKFLOWS = (
    Path(".github/workflows/gcp_auth_smoke.yml"),
    Path(".github/workflows/bigquery_readiness.yml"),
    Path(".github/workflows/bootstrap_schema_verification.yml"),
    Path(".github/workflows/dashboard_pages.yml"),
)


def test_read_only_cloud_workflows_use_direct_wif_without_service_account():
    for workflow in WORKFLOWS:
        text = workflow.read_text(encoding="utf-8")
        assert AUTH_PIN in text
        assert "workload_identity_provider:" in text
        assert "GCP_SERVICE_ACCOUNT" not in text
        assert "service_account:" not in text
        assert "credentials_json" not in text


def test_cloud_access_is_restricted_to_main_for_manual_bigquery_actions():
    auth_smoke = WORKFLOWS[0].read_text(encoding="utf-8")
    readiness = WORKFLOWS[1].read_text(encoding="utf-8")
    schema_verification = WORKFLOWS[2].read_text(encoding="utf-8")
    dashboard = WORKFLOWS[3].read_text(encoding="utf-8")

    assert "github.ref == 'refs/heads/main'" in auth_smoke
    assert "github.ref == 'refs/heads/main'" in readiness
    assert "github.ref == 'refs/heads/main'" in schema_verification
    assert 'GITHUB_REF" != "refs/heads/main"' in dashboard


def test_manual_cloud_workflows_validate_variables_before_authentication():
    for workflow in WORKFLOWS[:3]:
        text = workflow.read_text(encoding="utf-8")
        assert CLOUD_VALIDATION in text
        assert text.index(CLOUD_VALIDATION) < text.index("- id: auth")


def test_cloud_workflows_do_not_override_central_warehouse_location():
    for workflow in WORKFLOWS:
        text = workflow.read_text(encoding="utf-8")
        assert "BIGQUERY_LOCATION" not in text

    auth_smoke = WORKFLOWS[0].read_text(encoding="utf-8")
    dashboard = WORKFLOWS[3].read_text(encoding="utf-8")
    assert "from panganlens.schema_contract import WAREHOUSE_LOCATION" in auth_smoke
    assert "--location" not in dashboard
