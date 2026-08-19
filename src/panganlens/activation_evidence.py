"""Validate secret-safe evidence for PanganLens cloud activation."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from panganlens.cloud_config import validate_cloud_variables

REPOSITORY_FULL_NAME = "Fadhilstat/PanganLens"
REPOSITORY_ID = 1335081180
REPOSITORY_OWNER_ID = 179431732
DEFAULT_MAX_SOURCE_CAPTURE_AGE_HOURS = 72
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
COMMIT_SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")
EXPECTED_BRANCH = "main"
EXPECTED_EVENT = "workflow_dispatch"
AUTH_SMOKE_WORKFLOW = ".github/workflows/gcp_auth_smoke.yml"
SCHEMA_VERIFICATION_WORKFLOW = ".github/workflows/bootstrap_schema_verification.yml"
READINESS_WORKFLOW = ".github/workflows/bigquery_readiness.yml"
FORBIDDEN_KEY_PARTS = (
    "access_key",
    "credential",
    "credentials_json",
    "id_token",
    "password",
    "private_key",
    "refresh_token",
    "secret",
    "service_account",
    "token",
)
FORBIDDEN_VALUE_MARKERS = (
    "-----BEGIN PRIVATE KEY-----",
    "-----BEGIN RSA PRIVATE KEY-----",
    '"type": "service_account"',
    '"type":"service_account"',
)


@dataclass(frozen=True, slots=True)
class ActivationEvidenceResult:
    """Summarize whether an activation evidence manifest is acceptable."""

    status: str
    errors: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return {"status": self.status, "errors": list(self.errors)}


def validate_activation_evidence(
    evidence: Mapping[str, Any],
    *,
    require_complete: bool = False,
    max_source_capture_age_hours: int = DEFAULT_MAX_SOURCE_CAPTURE_AGE_HOURS,
) -> ActivationEvidenceResult:
    """Validate non-sensitive activation evidence without contacting Google Cloud."""

    if max_source_capture_age_hours <= 0:
        raise ValueError("max_source_capture_age_hours must be positive")

    errors: list[str] = []
    _reject_sensitive_content(evidence, path="root", errors=errors)
    _validate_identity(evidence, errors)
    _validate_gcp(evidence, errors)
    _validate_wif(evidence, errors)
    _validate_auth_smoke(evidence, errors)
    _validate_bootstrap(evidence, errors)
    _validate_readiness(
        evidence,
        errors,
        max_source_capture_age_hours=max_source_capture_age_hours,
    )

    if require_complete:
        _validate_completion(evidence, errors)

    return ActivationEvidenceResult(
        status="VALID" if not errors else "INVALID",
        errors=tuple(errors),
    )


def _reject_sensitive_content(value: Any, *, path: str, errors: list[str]) -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            normalized_key = str(key).casefold()
            if any(part in normalized_key for part in FORBIDDEN_KEY_PARTS):
                errors.append(f"{path}.{key}: sensitive field names are not allowed")
            _reject_sensitive_content(item, path=f"{path}.{key}", errors=errors)
        return

    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for index, item in enumerate(value):
            _reject_sensitive_content(item, path=f"{path}[{index}]", errors=errors)
        return

    if isinstance(value, str):
        for marker in FORBIDDEN_VALUE_MARKERS:
            if marker.casefold() in value.casefold():
                errors.append(f"{path}: credential-like content is not allowed")
                break


def _validate_identity(evidence: Mapping[str, Any], errors: list[str]) -> None:
    repository = evidence.get("repository")
    if not isinstance(repository, Mapping):
        errors.append("repository: object is required")
        return

    expected = {
        "full_name": REPOSITORY_FULL_NAME,
        "repository_id": REPOSITORY_ID,
        "owner_id": REPOSITORY_OWNER_ID,
    }
    for key, expected_value in expected.items():
        if repository.get(key) != expected_value:
            errors.append(f"repository.{key}: expected {expected_value!r}")


def _validate_gcp(evidence: Mapping[str, Any], errors: list[str]) -> None:
    gcp = evidence.get("gcp")
    if not isinstance(gcp, Mapping):
        errors.append("gcp: object is required")
        return

    project_id = gcp.get("project_id")
    wif_provider = gcp.get("wif_provider")
    if not isinstance(project_id, str) or not isinstance(wif_provider, str):
        errors.append("gcp: project_id and wif_provider must be strings")
        return

    try:
        validate_cloud_variables(project_id, wif_provider)
    except ValueError as exc:
        errors.append(f"gcp: {exc}")


def _validate_wif(evidence: Mapping[str, Any], errors: list[str]) -> None:
    wif = evidence.get("wif")
    if wif is None:
        return
    if not isinstance(wif, Mapping):
        errors.append("wif: must be an object")
        return

    provider_verified = wif.get("provider_verified")
    if not isinstance(provider_verified, bool):
        errors.append("wif.provider_verified: must be boolean")


def _validate_auth_smoke(evidence: Mapping[str, Any], errors: list[str]) -> None:
    auth_smoke = evidence.get("auth_smoke")
    if auth_smoke is None:
        return
    if not isinstance(auth_smoke, Mapping):
        errors.append("auth_smoke: must be an object")
        return

    _validate_run_id(auth_smoke.get("run_id"), "auth_smoke.run_id", errors)
    conclusion = auth_smoke.get("conclusion")
    if conclusion not in {"success", "failure", "cancelled"}:
        errors.append("auth_smoke.conclusion: unsupported conclusion")
    _validate_optional_run_provenance(
        auth_smoke,
        path="auth_smoke",
        expected_workflow=AUTH_SMOKE_WORKFLOW,
        errors=errors,
    )


def _validate_bootstrap(evidence: Mapping[str, Any], errors: list[str]) -> None:
    bootstrap = evidence.get("bootstrap")
    if bootstrap is None:
        return
    if not isinstance(bootstrap, Mapping):
        errors.append("bootstrap: must be an object")
        return

    plan_sha256 = bootstrap.get("plan_sha256")
    if not isinstance(plan_sha256, str) or not SHA256_PATTERN.fullmatch(plan_sha256):
        errors.append("bootstrap.plan_sha256: must be lowercase SHA-256")

    if "schema_verification_run_id" in bootstrap:
        _validate_run_id(
            bootstrap.get("schema_verification_run_id"),
            "bootstrap.schema_verification_run_id",
            errors,
        )

    schema_status = bootstrap.get("schema_status")
    if schema_status is not None and schema_status not in {"SCHEMA_READY", "BLOCKED"}:
        errors.append("bootstrap.schema_status: unsupported status")

    _validate_optional_run_provenance(
        bootstrap,
        path="bootstrap.schema_verification",
        expected_workflow=SCHEMA_VERIFICATION_WORKFLOW,
        errors=errors,
        prefix="schema_verification_",
    )


def _validate_readiness(
    evidence: Mapping[str, Any],
    errors: list[str],
    *,
    max_source_capture_age_hours: int,
) -> None:
    readiness = evidence.get("readiness")
    if readiness is None:
        return
    if not isinstance(readiness, Mapping):
        errors.append("readiness: must be an object")
        return

    _validate_run_id(readiness.get("run_id"), "readiness.run_id", errors)
    status = readiness.get("status")
    if status not in {"READY", "BLOCKED"}:
        errors.append("readiness.status: unsupported status")

    age = readiness.get("latest_source_capture_age_hours")
    if status == "READY" and age is None:
        errors.append(
            "readiness.latest_source_capture_age_hours: required for READY evidence"
        )
    elif age is not None:
        if not isinstance(age, int) or isinstance(age, bool):
            errors.append("readiness.latest_source_capture_age_hours: must be integer")
        elif age < 0:
            errors.append("readiness.latest_source_capture_age_hours: must not be negative")
        elif status == "READY" and age > max_source_capture_age_hours:
            errors.append(
                "readiness.latest_source_capture_age_hours: READY evidence is stale"
            )

    _validate_optional_run_provenance(
        readiness,
        path="readiness",
        expected_workflow=READINESS_WORKFLOW,
        errors=errors,
    )


def _validate_completion(evidence: Mapping[str, Any], errors: list[str]) -> None:
    wif = evidence.get("wif")
    auth_smoke = evidence.get("auth_smoke")
    bootstrap = evidence.get("bootstrap")
    readiness = evidence.get("readiness")

    if not isinstance(wif, Mapping) or wif.get("provider_verified") is not True:
        errors.append("completion: WIF provider verification is required")
    if not isinstance(auth_smoke, Mapping) or auth_smoke.get("conclusion") != "success":
        errors.append("completion: successful auth smoke evidence is required")
    if not isinstance(bootstrap, Mapping) or bootstrap.get("schema_status") != "SCHEMA_READY":
        errors.append("completion: SCHEMA_READY evidence is required")
    if not isinstance(readiness, Mapping) or readiness.get("status") != "READY":
        errors.append("completion: READY evidence is required")

    if isinstance(auth_smoke, Mapping):
        _require_run_provenance(
            auth_smoke,
            path="auth_smoke",
            expected_workflow=AUTH_SMOKE_WORKFLOW,
            errors=errors,
        )
    if isinstance(bootstrap, Mapping):
        _require_run_provenance(
            bootstrap,
            path="bootstrap.schema_verification",
            expected_workflow=SCHEMA_VERIFICATION_WORKFLOW,
            errors=errors,
            prefix="schema_verification_",
        )
    if isinstance(readiness, Mapping):
        _require_run_provenance(
            readiness,
            path="readiness",
            expected_workflow=READINESS_WORKFLOW,
            errors=errors,
        )


def _validate_optional_run_provenance(
    value: Mapping[str, Any],
    *,
    path: str,
    expected_workflow: str,
    errors: list[str],
    prefix: str = "",
) -> None:
    fields = (
        f"{prefix}workflow_path",
        f"{prefix}head_branch",
        f"{prefix}head_sha",
        f"{prefix}event",
    )
    if not any(field in value for field in fields):
        return
    _validate_run_provenance(
        value,
        path=path,
        expected_workflow=expected_workflow,
        errors=errors,
        prefix=prefix,
        require_all=True,
    )


def _require_run_provenance(
    value: Mapping[str, Any],
    *,
    path: str,
    expected_workflow: str,
    errors: list[str],
    prefix: str = "",
) -> None:
    _validate_run_provenance(
        value,
        path=path,
        expected_workflow=expected_workflow,
        errors=errors,
        prefix=prefix,
        require_all=True,
    )


def _validate_run_provenance(
    value: Mapping[str, Any],
    *,
    path: str,
    expected_workflow: str,
    errors: list[str],
    prefix: str,
    require_all: bool,
) -> None:
    workflow_key = f"{prefix}workflow_path"
    branch_key = f"{prefix}head_branch"
    sha_key = f"{prefix}head_sha"
    event_key = f"{prefix}event"

    workflow_path = value.get(workflow_key)
    branch = value.get(branch_key)
    head_sha = value.get(sha_key)
    event = value.get(event_key)

    if require_all and workflow_path is None:
        errors.append(f"{path}.workflow_path: provenance is required")
    elif workflow_path is not None and workflow_path != expected_workflow:
        errors.append(f"{path}.workflow_path: unexpected workflow")

    if require_all and branch is None:
        errors.append(f"{path}.head_branch: provenance is required")
    elif branch is not None and branch != EXPECTED_BRANCH:
        errors.append(f"{path}.head_branch: expected main")

    if require_all and head_sha is None:
        errors.append(f"{path}.head_sha: provenance is required")
    elif head_sha is not None and (
        not isinstance(head_sha, str) or not COMMIT_SHA_PATTERN.fullmatch(head_sha)
    ):
        errors.append(f"{path}.head_sha: must be lowercase 40-character commit SHA")

    if require_all and event is None:
        errors.append(f"{path}.event: provenance is required")
    elif event is not None and event != EXPECTED_EVENT:
        errors.append(f"{path}.event: expected workflow_dispatch")


def _validate_run_id(value: Any, path: str, errors: list[str]) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        errors.append(f"{path}: must be a positive integer")
