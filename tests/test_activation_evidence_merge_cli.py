from pathlib import Path

import pytest

from panganlens.activation_evidence_merge_cli import (
    merge_activation_evidence,
    normalize_fragment,
)

PLAN_SHA = "a" * 64
HEAD_SHA = "b" * 40


def base_manifest() -> dict[str, object]:
    return {
        "repository": {
            "full_name": "Fadhilstat/PanganLens",
            "repository_id": 1335081180,
            "owner_id": 179431732,
        },
        "gcp": {
            "project_id": "panganlens-prod-01",
            "wif_provider": (
                "projects/123456789/locations/global/workloadIdentityPools/"
                "panganlens-github/providers/panganlens-repo"
            ),
        },
        "wif": {"provider_verified": True},
    }


def test_normalize_bootstrap_plan_provenance_wraps_bootstrap():
    fragment = {
        "plan_sha256": PLAN_SHA,
        "plan_run_id": 101,
        "plan_workflow_path": ".github/workflows/bootstrap_plan.yml",
        "plan_head_branch": "main",
        "plan_head_sha": HEAD_SHA,
        "plan_event": "workflow_dispatch",
    }

    assert normalize_fragment(fragment) == {"bootstrap": fragment}


def test_merge_combines_distinct_bootstrap_fragments():
    plan = {
        "plan_sha256": PLAN_SHA,
        "plan_run_id": 101,
        "plan_workflow_path": ".github/workflows/bootstrap_plan.yml",
        "plan_head_branch": "main",
        "plan_head_sha": HEAD_SHA,
        "plan_event": "workflow_dispatch",
    }
    schema = {
        "bootstrap": {
            "schema_verification_run_id": 102,
            "schema_status": "SCHEMA_READY",
            "schema_verification_workflow_path": (
                ".github/workflows/bootstrap_schema_verification.yml"
            ),
            "schema_verification_head_branch": "main",
            "schema_verification_head_sha": HEAD_SHA,
            "schema_verification_event": "workflow_dispatch",
        }
    }

    merged = merge_activation_evidence(base_manifest(), [plan, schema])

    assert merged["bootstrap"]["plan_run_id"] == 101
    assert merged["bootstrap"]["schema_verification_run_id"] == 102


def test_merge_rejects_conflicting_existing_value():
    base = base_manifest()
    base["auth_smoke"] = {"run_id": 201}

    with pytest.raises(ValueError, match="root.auth_smoke.run_id"):
        merge_activation_evidence(base, [{"auth_smoke": {"run_id": 202}}])


def test_merge_allows_identical_existing_value():
    base = base_manifest()
    base["auth_smoke"] = {"run_id": 201}

    merged = merge_activation_evidence(base, [{"auth_smoke": {"run_id": 201}}])

    assert merged["auth_smoke"]["run_id"] == 201


def test_fragment_requires_single_supported_root():
    with pytest.raises(ValueError, match="one supported evidence root"):
        normalize_fragment({"auth_smoke": {}, "readiness": {}})


def test_merge_module_has_no_em_dash():
    module = Path("src/panganlens/activation_evidence_merge_cli.py")
    assert "\u2014" not in module.read_text(encoding="utf-8")
