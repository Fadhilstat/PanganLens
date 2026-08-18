"""Run guarded staging promotion as one transactional BigQuery operation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from google.cloud import bigquery


@dataclass(frozen=True, slots=True)
class QualityCheck:
    """One named warehouse quality result."""

    check_name: str
    failure_count: int
    status: str


@dataclass(frozen=True, slots=True)
class PromotionResult:
    """Outcome of one guarded promotion attempt."""

    run_id: str
    pre_checks: tuple[QualityCheck, ...]
    promoted: bool
    publish_eligible: bool


class PromotionBlockedError(RuntimeError):
    """Raised when a run is not safe to promote."""


class BigQueryPromotionRunner:
    """Audit staging, run quality gates, and promote one run atomically."""

    def __init__(
        self,
        project_id: str,
        client: bigquery.Client | None = None,
        location: str = "asia-southeast2",
        sql_dir: Path | None = None,
    ) -> None:
        self.project_id = project_id
        self.location = location
        self.client = client or bigquery.Client(project=project_id, location=location)
        self.sql_dir = sql_dir or Path(__file__).resolve().parents[3] / "sql"

    def promote(self, run_id: str, ingestion_eligible: bool) -> PromotionResult:
        if not run_id.strip():
            raise ValueError("run_id must not be empty")
        if not ingestion_eligible:
            raise PromotionBlockedError("ingestion summary is not promotion eligible")

        self._audit_cross_capture_rows(run_id)
        pre_checks = self._run_pre_checks(run_id)
        if not pre_checks:
            raise PromotionBlockedError("pre-promotion checks returned no results")

        failed = [
            check.check_name
            for check in pre_checks
            if check.status != "PASS" or check.failure_count != 0
        ]
        if failed:
            names = ", ".join(sorted(failed))
            raise PromotionBlockedError(f"pre-promotion checks failed: {names}")

        promotion_sql = self._read_sql("010_promote_staging_to_core.sql")
        post_assertions = self._read_sql("011_post_promotion_assertions.sql")
        transactional_sql = (
            "BEGIN TRANSACTION;\n"
            + promotion_sql
            + "\n"
            + post_assertions
            + "\nCOMMIT TRANSACTION;\n"
        )
        self._execute(transactional_sql, run_id)
        return PromotionResult(
            run_id=run_id,
            pre_checks=pre_checks,
            promoted=True,
            publish_eligible=True,
        )

    def _audit_cross_capture_rows(self, run_id: str) -> None:
        query = self._read_sql("013_audit_cross_capture_duplicates.sql")
        self._execute(query, run_id)

    def _run_pre_checks(self, run_id: str) -> tuple[QualityCheck, ...]:
        query = self._read_sql("005_pre_staging_checks.sql")
        rows = self._execute(query, run_id)
        return tuple(
            QualityCheck(
                check_name=str(row["check_name"]),
                failure_count=int(row["failure_count"]),
                status=str(row["status"]),
            )
            for row in rows
        )

    def _execute(self, query: str, run_id: str):
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("run_id", "STRING", run_id),
            ]
        )
        return self.client.query(
            query,
            job_config=job_config,
            location=self.location,
        ).result()

    def _read_sql(self, filename: str) -> str:
        path = self.sql_dir / filename
        return path.read_text(encoding="utf-8").strip()
