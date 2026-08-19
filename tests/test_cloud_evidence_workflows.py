from pathlib import Path

UPLOAD_PIN = (
    "actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02"
)
WORKFLOWS = {
    "auth_smoke": Path(".github/workflows/gcp_auth_smoke.yml"),
    "readiness": Path(".github/workflows/bigquery_readiness.yml"),
    "schema_verification": Path(".github/workflows/bootstrap_schema_verification.yml"),
}


def test_cloud_workflows_build_evidence_from_github_context():
    for kind, workflow in WORKFLOWS.items():
        text = workflow.read_text(encoding="utf-8")
        assert "python -m panganlens.cloud_run_evidence_cli" in text
        assert kind in text
        assert '${{ github.run_id }}' in text
        assert '${{ github.workflow_ref }}' in text
        assert '${{ github.ref_name }}' in text
        assert '${{ github.sha }}' in text
        assert '${{ github.event_name }}' in text
        assert UPLOAD_PIN in text
        assert "retention-days: 7" in text


def test_readiness_and_schema_evidence_survive_blocked_checks():
    readiness = WORKFLOWS["readiness"].read_text(encoding="utf-8")
    schema = WORKFLOWS["schema_verification"].read_text(encoding="utf-8")

    assert "Build readiness activation evidence\n        if: always()" in readiness
    assert (
        "Build schema verification activation evidence\n        if: always()" in schema
    )
    assert "bigquery-readiness-evidence.json" in readiness
    assert "bootstrap-schema-verification-evidence.json" in schema


def test_auth_smoke_evidence_is_only_built_after_successful_query():
    text = WORKFLOWS["auth_smoke"].read_text(encoding="utf-8")

    query_position = text.index("Verify Application Default Credentials with BigQuery")
    evidence_position = text.index("Build auth smoke activation evidence")
    assert query_position < evidence_position
    assert "auth-smoke-evidence.json" in text


def test_cloud_evidence_artifacts_are_commit_bound():
    auth = WORKFLOWS["auth_smoke"].read_text(encoding="utf-8")
    readiness = WORKFLOWS["readiness"].read_text(encoding="utf-8")
    schema = WORKFLOWS["schema_verification"].read_text(encoding="utf-8")

    assert "panganlens-gcp-auth-smoke-${{ github.sha }}" in auth
    assert "panganlens-bigquery-readiness-${{ github.sha }}" in readiness
    assert "panganlens-bootstrap-schema-verification-${{ github.sha }}" in schema


def test_cloud_evidence_workflows_keep_existing_security_boundary():
    auth = WORKFLOWS["auth_smoke"].read_text(encoding="utf-8")
    readiness = WORKFLOWS["readiness"].read_text(encoding="utf-8")
    schema = WORKFLOWS["schema_verification"].read_text(encoding="utf-8")

    for text in (auth, readiness, schema):
        assert "workflow_dispatch:" in text
        assert "schedule:" not in text
        assert "service_account:" not in text
        assert "credentials_json" not in text
        assert "GCP_SERVICE_ACCOUNT" not in text
        assert "contents: write" not in text


def test_cloud_evidence_test_contract_has_no_em_dash():
    assert "\u2014" not in Path(__file__).read_text(encoding="utf-8")
