"""Persist pipeline outcomes without moving the public publish pointer unsafely."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from google.cloud import bigquery

from panganlens.warehouse.loader import PROJECT_ID_PATTERN

VALID_FINAL_STATUSES = {"SUCCESS", "NO_NEW_DATA", "BLOCKED", "FAILED"}


@dataclass(frozen=True, slots=True)
class PipelineOutcome:
    """Final operational state for one ingestion run."""

    run_id: str
    started_at: datetime
    finished_at: datetime
    status: str
    source_observation_date: date | None
    rows_received: int
    rows_clean: int
    rows_duplicate: int
    rows_conflict: int
    rows_quarantined: int
    error_message: str | None = None

    def validate(self) -> None:
        if not self.run_id.strip():
            raise ValueError("run_id must not be empty")
        if self.started_at.tzinfo is None or self.finished_at.tzinfo is None:
            raise ValueError("pipeline timestamps must be timezone-aware")
        if self.finished_at < self.started_at:
            raise ValueError("finished_at cannot be earlier than started_at")
        if self.status not in VALID_FINAL_STATUSES:
            raise ValueError("pipeline status is not supported")

        counts = (
            self.rows_received,
            self.rows_clean,
            self.rows_duplicate,
            self.rows_conflict,
            self.rows_quarantined,
        )
        if any(value < 0 for value in counts):
            raise ValueError("pipeline row counts cannot be negative")
        if self.rows_clean > self.rows_received:
            raise ValueError("rows_clean cannot exceed rows_received")
        if self.status == "SUCCESS" and self.source_observation_date is None:
            raise ValueError("successful runs require source_observation_date")
        if self.status in {"BLOCKED", "FAILED"} and not self.error_message:
            raise ValueError("blocked and failed runs require error_message")


class BigQueryRunStateManager:
    """Write final run state and advance publish state only after success."""

    def __init__(
        self,
        project_id: str,
        client: bigquery.Client | None = None,
        location: str = "asia-southeast2",
    ) -> None:
        if not PROJECT_ID_PATTERN.fullmatch(project_id):
            raise ValueError("project_id is not a valid Google Cloud project ID")
        self.project_id = project_id
        self.location = location
        self.client = client or bigquery.Client(project=project_id, location=location)

    def finalize(self, outcome: PipelineOutcome) -> None:
        outcome.validate()
        query = self._finalize_query(advance_publish=outcome.status == "SUCCESS")
        job_config = bigquery.QueryJobConfig(
            query_parameters=self._query_parameters(outcome)
        )
        self.client.query(
            query,
            job_config=job_config,
            location=self.location,
        ).result()

    @staticmethod
    def _finalize_query(advance_publish: bool) -> str:
        run_merge = """
ASSERT (
  SELECT COUNT(*) = 0
  FROM panganlens_ops.pipeline_run
  WHERE run_id = @run_id
    AND status IN ('SUCCESS', 'NO_NEW_DATA', 'BLOCKED', 'FAILED')
    AND status != @status
) AS 'pipeline run already finalized with a different status';

MERGE panganlens_ops.pipeline_run AS target
USING (
  SELECT
    @run_id AS run_id,
    @started_at AS started_at,
    @finished_at AS finished_at,
    @status AS status,
    @source_observation_date AS source_observation_date,
    @rows_received AS rows_received,
    @rows_clean AS rows_clean,
    @rows_duplicate AS rows_duplicate,
    @rows_conflict AS rows_conflict,
    @rows_quarantined AS rows_quarantined,
    @error_message AS error_message
) AS source
ON target.run_id = source.run_id
WHEN MATCHED THEN
  UPDATE SET
    finished_at = source.finished_at,
    source_observation_date = source.source_observation_date,
    rows_received = source.rows_received,
    rows_clean = source.rows_clean,
    rows_duplicate = source.rows_duplicate,
    rows_conflict = source.rows_conflict,
    rows_quarantined = source.rows_quarantined,
    error_message = source.error_message
WHEN NOT MATCHED THEN
  INSERT (
    run_id,
    started_at,
    finished_at,
    status,
    source_observation_date,
    rows_received,
    rows_clean,
    rows_duplicate,
    rows_conflict,
    rows_quarantined,
    error_message
  )
  VALUES (
    source.run_id,
    source.started_at,
    source.finished_at,
    source.status,
    source.source_observation_date,
    source.rows_received,
    source.rows_clean,
    source.rows_duplicate,
    source.rows_conflict,
    source.rows_quarantined,
    source.error_message
  );
""".strip()

        if not advance_publish:
            return run_merge

        publish_merge = """
MERGE panganlens_ops.publish_state AS target
USING (
  SELECT
    'public_dashboard' AS state_name,
    @run_id AS active_run_id,
    @source_observation_date AS active_observation_date,
    @finished_at AS published_at
) AS source
ON target.state_name = source.state_name
WHEN MATCHED
  AND (
    source.active_observation_date > target.active_observation_date
    OR (
      source.active_observation_date = target.active_observation_date
      AND source.published_at >= target.published_at
    )
  ) THEN
  UPDATE SET
    active_run_id = source.active_run_id,
    active_observation_date = source.active_observation_date,
    published_at = source.published_at
WHEN NOT MATCHED THEN
  INSERT (
    state_name,
    active_run_id,
    active_observation_date,
    published_at
  )
  VALUES (
    source.state_name,
    source.active_run_id,
    source.active_observation_date,
    source.published_at
  );
""".strip()
        return (
            "BEGIN TRANSACTION;\n"
            + run_merge
            + "\n\n"
            + publish_merge
            + "\nCOMMIT TRANSACTION;"
        )

    @staticmethod
    def _query_parameters(outcome: PipelineOutcome) -> list[bigquery.ScalarQueryParameter]:
        return [
            bigquery.ScalarQueryParameter("run_id", "STRING", outcome.run_id),
            bigquery.ScalarQueryParameter("started_at", "TIMESTAMP", outcome.started_at),
            bigquery.ScalarQueryParameter("finished_at", "TIMESTAMP", outcome.finished_at),
            bigquery.ScalarQueryParameter("status", "STRING", outcome.status),
            bigquery.ScalarQueryParameter(
                "source_observation_date",
                "DATE",
                outcome.source_observation_date,
            ),
            bigquery.ScalarQueryParameter("rows_received", "INT64", outcome.rows_received),
            bigquery.ScalarQueryParameter("rows_clean", "INT64", outcome.rows_clean),
            bigquery.ScalarQueryParameter(
                "rows_duplicate",
                "INT64",
                outcome.rows_duplicate,
            ),
            bigquery.ScalarQueryParameter("rows_conflict", "INT64", outcome.rows_conflict),
            bigquery.ScalarQueryParameter(
                "rows_quarantined",
                "INT64",
                outcome.rows_quarantined,
            ),
            bigquery.ScalarQueryParameter("error_message", "STRING", outcome.error_message),
        ]
