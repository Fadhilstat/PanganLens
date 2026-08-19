from pathlib import Path

import pytest

from panganlens.cloud_run_evidence_cli import build_cloud_run_evidence


def _workflow_ref(path: str) -> str:
    return f"Fadhilstat/PanganLens/{path}@refs/heads/main"


def _run_kwargs(path: str) -> dict[str, object]:
    return {
        "run_id": 123456789,
        "workflow_ref": _workflow_ref(path),
        "head_branch": "main",
        "head_sha": "a" * 40,
        "event": "workflow_dispatch",
    }


def test_build_auth_smoke_fragment_from_reviewed_run():
    evidence = build_cloud_run_evidence(
        "auth_smoke",
        **_run_kwargs(".github/workflows/gcp_auth_smoke.yml"),
    )

    assert evidence == {
        "auth_smoke": {
            "run_id": 123456789,
            "conclusion": "success",
            "workflow_path": ".github/workflows/gcp_auth_smoke.yml",
            "head_branch": "main",
            "head_sha": "a" * 40,
            "event": "workflow_dispatch",
        }
    }


def test_build_schema_verification_fragment_keeps_blocked_status():
    evidence = build_cloud_run_evidence(
        "schema_verification",
        result={"status": "BLOCKED", "checks": []},
        **_run_kwargs(".github/workflows/bootstrap_schema_verification.yml"),
    )

    assert evidence["bootstrap"]["schema_verification_run_id"] == 123456789
    assert evidence["bootstrap"]["schema_status"] == "BLOCKED"
    assert evidence["bootstrap"]["schema_verification_head_sha"] == "a" * 40


def test_build_ready_fragment_copies_source_capture_age():
    evidence = build_cloud_run_evidence(
        "readiness",
        result={
            "status": "READY",
            "metrics": {"latest_successful_capture_age_hours": 12},
        },
        **_run_kwargs(".github/workflows/bigquery_readiness.yml"),
    )

    assert evidence["readiness"]["status"] == "READY"
    assert evidence["readiness"]["latest_source_capture_age_hours"] == 12


def test_ready_fragment_rejects_missing_freshness():
    with pytest.raises(ValueError, match="latest successful capture age"):
        build_cloud_run_evidence(
            "readiness",
            result={"status": "READY", "metrics": {}},
            **_run_kwargs(".github/workflows/bigquery_readiness.yml"),
        )


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("run_id", 0, "positive integer"),
        ("head_branch", "feature/test", "head_branch must be main"),
        ("head_sha", "NOT-A-SHA", "40-character commit SHA"),
        ("event", "push", "event must be workflow_dispatch"),
    ],
)
def test_cloud_run_evidence_rejects_unreviewed_metadata(field, value, message):
    kwargs = _run_kwargs(".github/workflows/gcp_auth_smoke.yml")
    kwargs[field] = value

    with pytest.raises(ValueError, match=message):
        build_cloud_run_evidence("auth_smoke", **kwargs)


def test_cloud_run_evidence_rejects_wrong_workflow_ref():
    kwargs = _run_kwargs(".github/workflows/gcp_auth_smoke.yml")
    kwargs["workflow_ref"] = _workflow_ref(".github/workflows/quality.yml")

    with pytest.raises(ValueError, match="reviewed workflow"):
        build_cloud_run_evidence("auth_smoke", **kwargs)


def test_cloud_run_evidence_python_has_no_em_dash():
    source = Path("src/panganlens/cloud_run_evidence_cli.py").read_text(encoding="utf-8")
    assert "\u2014" not in source
    assert "\u2014" not in Path(__file__).read_text(encoding="utf-8")
