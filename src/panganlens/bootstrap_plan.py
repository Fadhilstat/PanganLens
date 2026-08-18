"""Build an auditable BigQuery bootstrap plan without executing SQL."""

from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from pathlib import Path

SCHEMA_BOOTSTRAP_FILES = (
    "001_create_datasets.sql",
    "002_core_3nf.sql",
    "003_raw_staging_ops.sql",
    "008_source_mapping_registry.sql",
    "015_mapping_review_queue.sql",
    "006_looker_semantic_views.sql",
    "012_looker_publish_state.sql",
)

OPERATIONAL_SQL_FILES = (
    "004_post_load_checks.sql",
    "005_pre_staging_checks.sql",
    "009_looker_map_quality.sql",
    "010_promote_staging_to_core.sql",
    "011_post_promotion_assertions.sql",
    "013_audit_cross_capture_duplicates.sql",
    "016_activate_reviewed_mapping.sql",
    "017_reject_mapping_candidate.sql",
)


@dataclass(frozen=True, slots=True)
class BootstrapStep:
    order: int
    filename: str
    sha256: str
    bytes: int


@dataclass(frozen=True, slots=True)
class BootstrapPlan:
    status: str
    steps: tuple[BootstrapStep, ...]
    operational_files_excluded: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "steps": [asdict(step) for step in self.steps],
            "operational_files_excluded": list(self.operational_files_excluded),
        }


def build_bootstrap_plan(repo_root: str | Path) -> BootstrapPlan:
    """Return a deterministic schema-only plan and fail if the contract drifts."""

    root = Path(repo_root).resolve()
    sql_dir = root / "sql"
    if not sql_dir.is_dir():
        raise FileNotFoundError("sql directory is not available")

    existing = {path.name for path in sql_dir.glob("*.sql")}
    expected = set(SCHEMA_BOOTSTRAP_FILES) | set(OPERATIONAL_SQL_FILES)
    unexpected = sorted(existing - expected)
    missing = sorted(expected - existing)
    if missing:
        raise RuntimeError(f"bootstrap SQL contract is missing files: {', '.join(missing)}")
    if unexpected:
        raise RuntimeError(
            "bootstrap SQL contract has unclassified files: " + ", ".join(unexpected)
        )

    steps = []
    for order, filename in enumerate(SCHEMA_BOOTSTRAP_FILES, start=1):
        path = sql_dir / filename
        payload = path.read_bytes()
        if not payload.strip():
            raise RuntimeError(f"bootstrap SQL file is empty: {filename}")
        steps.append(
            BootstrapStep(
                order=order,
                filename=filename,
                sha256=hashlib.sha256(payload).hexdigest(),
                bytes=len(payload),
            )
        )

    return BootstrapPlan(
        status="DRY_RUN_ONLY",
        steps=tuple(steps),
        operational_files_excluded=OPERATIONAL_SQL_FILES,
    )
