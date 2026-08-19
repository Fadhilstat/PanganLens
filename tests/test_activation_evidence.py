from panganlens.activation_evidence import validate_activation_evidence


def _base_manifest():
    return {
        "repository": {
            "full_name": "Fadhilstat/PanganLens",
            "repository_id": 1335081180,
            "owner_id": 179431732,
        },
        "gcp": {
            "project_id": "panganlens-prod1",
            "wif_provider": (
                "projects/123456789/locations/global/workloadIdentityPools/"
                "panganlens-github/providers/panganlens-repo"
            ),
        },
    }


def _run_provenance(workflow_path, head_sha="a" * 40):
    return {
        "workflow_path": workflow_path,
        "head_branch": "main",
        "head_sha": head_sha,
        "event": "workflow_dispatch",
    }


def test_partial_manifest_is_valid_without_fabricating_future_evidence():
    result = validate_activation_evidence(_base_manifest())

    assert result.status == "VALID"
    assert result.errors == ()


def test_complete_manifest_requires_real_success_states_and_run_provenance():
    manifest = _base_manifest()
    auth_smoke = {"run_id": 101, "conclusion": "success"}
    auth_smoke.update(_run_provenance(".github/workflows/gcp_auth_smoke.yml"))

    readiness = {
        "run_id": 103,
        "status": "READY",
        "latest_source_capture_age_hours": 12,
    }
    readiness.update(_run_provenance(".github/workflows/bigquery_readiness.yml"))

    bootstrap_provenance = _run_provenance(
        ".github/workflows/bootstrap_schema_verification.yml",
        head_sha="b" * 40,
    )
    bootstrap = {
        "plan_sha256": "c" * 64,
        "schema_verification_run_id": 102,
        "schema_status": "SCHEMA_READY",
        "schema_verification_workflow_path": bootstrap_provenance["workflow_path"],
        "schema_verification_head_branch": bootstrap_provenance["head_branch"],
        "schema_verification_head_sha": bootstrap_provenance["head_sha"],
        "schema_verification_event": bootstrap_provenance["event"],
    }

    manifest.update(
        {
            "wif": {"provider_verified": True},
            "auth_smoke": auth_smoke,
            "bootstrap": bootstrap,
            "readiness": readiness,
        }
    )

    result = validate_activation_evidence(manifest, require_complete=True)

    assert result.status == "VALID"


def test_complete_manifest_rejects_success_without_run_provenance():
    manifest = _base_manifest()
    manifest.update(
        {
            "wif": {"provider_verified": True},
            "auth_smoke": {"run_id": 101, "conclusion": "success"},
            "bootstrap": {
                "plan_sha256": "a" * 64,
                "schema_verification_run_id": 102,
                "schema_status": "SCHEMA_READY",
            },
            "readiness": {
                "run_id": 103,
                "status": "READY",
                "latest_source_capture_age_hours": 12,
            },
        }
    )

    result = validate_activation_evidence(manifest, require_complete=True)

    assert result.status == "INVALID"
    assert sum("provenance is required" in error for error in result.errors) == 12


def test_manifest_rejects_wrong_workflow_branch_event_or_commit_sha():
    manifest = _base_manifest()
    manifest["auth_smoke"] = {
        "run_id": 101,
        "conclusion": "success",
        "workflow_path": ".github/workflows/bigquery_readiness.yml",
        "head_branch": "feature/test",
        "head_sha": "NOT-A-SHA",
        "event": "push",
    }

    result = validate_activation_evidence(manifest)

    assert result.status == "INVALID"
    assert any("unexpected workflow" in error for error in result.errors)
    assert any("expected main" in error for error in result.errors)
    assert any("40-character commit SHA" in error for error in result.errors)
    assert any("expected workflow_dispatch" in error for error in result.errors)


def test_ready_manifest_requires_source_freshness_evidence():
    manifest = _base_manifest()
    manifest["readiness"] = {"run_id": 103, "status": "READY"}

    result = validate_activation_evidence(manifest)

    assert result.status == "INVALID"
    assert any("required for READY evidence" in error for error in result.errors)


def test_complete_manifest_rejects_blocked_or_stale_evidence():
    manifest = _base_manifest()
    manifest.update(
        {
            "wif": {"provider_verified": True},
            "auth_smoke": {"run_id": 101, "conclusion": "failure"},
            "bootstrap": {
                "plan_sha256": "b" * 64,
                "schema_verification_run_id": 102,
                "schema_status": "BLOCKED",
            },
            "readiness": {
                "run_id": 103,
                "status": "READY",
                "latest_source_capture_age_hours": 73,
            },
        }
    )

    result = validate_activation_evidence(manifest, require_complete=True)

    assert result.status == "INVALID"
    assert any("successful auth smoke" in error for error in result.errors)
    assert any("SCHEMA_READY" in error for error in result.errors)
    assert any("READY evidence is stale" in error for error in result.errors)


def test_manifest_rejects_sensitive_fields_recursively():
    manifest = _base_manifest()
    manifest["operator_notes"] = {"credentials_json": "do-not-store-this"}

    result = validate_activation_evidence(manifest)

    assert result.status == "INVALID"
    assert any("sensitive field names" in error for error in result.errors)


def test_manifest_rejects_private_key_content_even_under_safe_key_name():
    manifest = _base_manifest()
    manifest["operator_notes"] = {
        "note": "-----BEGIN PRIVATE KEY-----\nnot-a-real-key"
    }

    result = validate_activation_evidence(manifest)

    assert result.status == "INVALID"
    assert any("credential-like content" in error for error in result.errors)


def test_manifest_reuses_reviewed_cloud_variable_contract():
    manifest = _base_manifest()
    manifest["gcp"]["wif_provider"] = "projects/123/providers/unreviewed"

    result = validate_activation_evidence(manifest)

    assert result.status == "INVALID"
    assert any("GCP_WIF_PROVIDER" in error for error in result.errors)


def test_manifest_rejects_invalid_plan_hash_and_run_ids():
    manifest = _base_manifest()
    manifest.update(
        {
            "auth_smoke": {"run_id": 0, "conclusion": "success"},
            "bootstrap": {
                "plan_sha256": "NOT-A-HASH",
                "schema_verification_run_id": -1,
                "schema_status": "SCHEMA_READY",
            },
        }
    )

    result = validate_activation_evidence(manifest)

    assert result.status == "INVALID"
    assert any("lowercase SHA-256" in error for error in result.errors)
    assert sum("positive integer" in error for error in result.errors) == 2
