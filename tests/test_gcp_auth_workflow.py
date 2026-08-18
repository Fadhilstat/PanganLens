from pathlib import Path

WORKFLOW = Path(".github/workflows/gcp_auth_smoke.yml")
SETUP_DOC = Path("docs/gcp_wif_setup.md")
AUTH_PIN = "google-github-actions/auth@7c6bc770dae815cd3e89ee6cdf493a5fab2cc093"


def test_gcp_auth_workflow_is_manual_direct_wif_and_keyless():
    text = WORKFLOW.read_text(encoding="utf-8")

    assert "workflow_dispatch:" in text
    assert "schedule:" not in text
    assert "github.ref == 'refs/heads/main'" in text
    assert "id-token: write" in text
    assert AUTH_PIN in text
    assert "workload_identity_provider:" in text
    assert "service_account:" not in text
    assert "credentials_json" not in text
    assert "GCP_WIF_PROVIDER" in text
    assert "GCP_SERVICE_ACCOUNT" not in text


def test_oidc_permission_is_limited_to_auth_job():
    text = WORKFLOW.read_text(encoding="utf-8")
    preflight = text.split("  auth-smoke:", maxsplit=1)[0]
    auth_job = text.split("  auth-smoke:", maxsplit=1)[1]

    assert "id-token: write" not in preflight
    assert "id-token: write" in auth_job
    assert "contents: read" in preflight
    assert "contents: read" in auth_job


def test_auth_workflow_checks_bigquery_through_adc():
    text = WORKFLOW.read_text(encoding="utf-8")

    assert "google.cloud import bigquery" in text
    assert 'client.query("SELECT 1 AS ok"' in text
    assert "Direct keyless Google Cloud authentication and BigQuery access verified" in text


def test_wif_setup_uses_immutable_repository_identifiers_and_direct_access():
    text = SETUP_DOC.read_text(encoding="utf-8")

    assert "1335081180" in text
    assert "179431732" in text
    assert "attribute.repository_id=assertion.repository_id" in text
    assert "attribute.repository_owner_id=assertion.repository_owner_id" in text
    assert 'attribute.ref == "refs/heads/main"' in text
    assert "principalSet://iam.googleapis.com/" in text
    assert "roles/bigquery.jobUser" in text
    assert "roles/bigquery.dataViewer" in text
    assert "roles/iam.workloadIdentityUser" not in text
    assert "GCP_SERVICE_ACCOUNT` is not used" in text
    assert "Do not create or upload a service account key file." in text


def test_generated_google_auth_credentials_are_ignored():
    text = Path(".gitignore").read_text(encoding="utf-8")

    assert "gha-creds-*.json" in text
