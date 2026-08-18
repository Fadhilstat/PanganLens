"""Coordinate one PIHPS grid run from source fetch to terminal state."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from panganlens.ingestion.orchestration import (
    IngestionContext,
    MappingResolver,
    ingest_grid_capture,
)
from panganlens.ingestion.pihps_interface import GridRequest, PihpsWebsiteClient, SourceRows
from panganlens.pipeline import PromotionRunner, RunStateManager, finalize_capture_run
from panganlens.warehouse.loader import BigQueryWarehouse
from panganlens.warehouse.run_state import PipelineOutcome
from panganlens.warehouse.staging_writer import BigQueryStagingWriter


class GridSourceClient(Protocol):
    """Minimal source client contract needed by the run coordinator."""

    def fetch_grid_capture(self, request: GridRequest) -> SourceRows: ...


def execute_grid_run(
    request: GridRequest,
    context: IngestionContext,
    source_client: GridSourceClient | PihpsWebsiteClient,
    resolver: MappingResolver,
    raw_warehouse: BigQueryWarehouse,
    staging_writer: BigQueryStagingWriter,
    promotion_runner: PromotionRunner,
    state_manager: RunStateManager,
    finished_at: datetime,
) -> PipelineOutcome:
    """Execute one reviewed grid request and persist exactly one terminal outcome."""

    if finished_at.tzinfo is None:
        raise ValueError("finished_at must be timezone-aware")
    context.validate()
    _validate_request_context(request, context)

    try:
        source = source_client.fetch_grid_capture(request)
        summary = ingest_grid_capture(
            source,
            context,
            resolver,
            raw_warehouse,
            staging_writer,
        )
    except Exception as exc:
        outcome = PipelineOutcome(
            run_id=context.run_id,
            started_at=context.captured_at,
            finished_at=finished_at,
            status="FAILED",
            source_observation_date=None,
            rows_received=0,
            rows_clean=0,
            rows_duplicate=0,
            rows_conflict=0,
            rows_quarantined=0,
            error_message=f"ingestion failed: {type(exc).__name__}",
        )
        state_manager.finalize(outcome)
        raise

    return finalize_capture_run(
        summary,
        context,
        promotion_runner,
        state_manager,
        finished_at,
    )


def _validate_request_context(request: GridRequest, context: IngestionContext) -> None:
    """Prevent provenance drift between the source request and stored run context."""

    expected = request.as_params()
    if context.start_date != request.start_date or context.end_date != request.end_date:
        raise ValueError("context date window must match the PIHPS grid request")

    for key in ("price_type_id", "comcat_id", "province_id"):
        if str(context.request_parameters.get(key, "")) != str(expected[key]):
            raise ValueError(f"context request parameter {key} does not match the grid request")
