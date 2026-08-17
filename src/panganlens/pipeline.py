"""Turn one staged ingestion summary into an explicit pipeline outcome."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from panganlens.ingestion.orchestration import IngestionContext, IngestionSummary
from panganlens.warehouse.promotion import PromotionBlockedError
from panganlens.warehouse.run_state import PipelineOutcome


class PromotionRunner(Protocol):
    """Minimal promotion contract used by the pipeline coordinator."""

    def promote(self, run_id: str, ingestion_eligible: bool): ...


class RunStateManager(Protocol):
    """Minimal final-state persistence contract used by the coordinator."""

    def finalize(self, outcome: PipelineOutcome) -> None: ...


def finalize_capture_run(
    summary: IngestionSummary,
    context: IngestionContext,
    promotion_runner: PromotionRunner,
    state_manager: RunStateManager,
    finished_at: datetime,
) -> PipelineOutcome:
    """Promote safe data and persist exactly one terminal state for the run."""

    if finished_at.tzinfo is None:
        raise ValueError("finished_at must be timezone-aware")

    if summary.parsed_points == 0 and summary.staged_rows == 0:
        outcome = _outcome(
            summary,
            context,
            finished_at,
            status="NO_NEW_DATA",
            error_message=None,
        )
        state_manager.finalize(outcome)
        return outcome

    if not summary.promotion_eligible:
        outcome = _outcome(
            summary,
            context,
            finished_at,
            status="BLOCKED",
            error_message="ingestion quality gate blocked promotion",
        )
        state_manager.finalize(outcome)
        return outcome

    try:
        promotion_runner.promote(context.run_id, ingestion_eligible=True)
    except PromotionBlockedError as exc:
        outcome = _outcome(
            summary,
            context,
            finished_at,
            status="BLOCKED",
            error_message=str(exc),
        )
        state_manager.finalize(outcome)
        return outcome
    except Exception as exc:
        outcome = _outcome(
            summary,
            context,
            finished_at,
            status="FAILED",
            error_message=f"promotion failed: {type(exc).__name__}",
        )
        state_manager.finalize(outcome)
        raise

    outcome = _outcome(
        summary,
        context,
        finished_at,
        status="SUCCESS",
        error_message=None,
    )
    state_manager.finalize(outcome)
    return outcome


def _outcome(
    summary: IngestionSummary,
    context: IngestionContext,
    finished_at: datetime,
    *,
    status: str,
    error_message: str | None,
) -> PipelineOutcome:
    rows_received = summary.parsed_points + summary.missing_price_cells
    rows_clean = summary.staged_rows - summary.quarantined_rows
    return PipelineOutcome(
        run_id=context.run_id,
        started_at=context.captured_at,
        finished_at=finished_at,
        status=status,
        source_observation_date=summary.latest_observation_date,
        rows_received=rows_received,
        rows_clean=rows_clean,
        rows_duplicate=summary.exact_duplicates,
        rows_conflict=0,
        rows_quarantined=summary.quarantined_rows,
        error_message=error_message,
    )
