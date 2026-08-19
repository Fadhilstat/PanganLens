"""Command-line entrypoint for one explicit PIHPS ingestion run."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, date, datetime
from uuid import uuid4

from google.cloud import bigquery

from panganlens.ingestion.mapping_resolver import BigQueryReviewedMappingResolver
from panganlens.ingestion.orchestration import IngestionContext
from panganlens.ingestion.pihps_interface import GridRequest, PihpsWebsiteClient
from panganlens.run_coordinator import execute_grid_run
from panganlens.schema_contract import WAREHOUSE_LOCATION
from panganlens.warehouse.loader import BigQueryWarehouse
from panganlens.warehouse.promotion import BigQueryPromotionRunner
from panganlens.warehouse.run_state import BigQueryRunStateManager, PipelineOutcome
from panganlens.warehouse.staging_writer import BigQueryStagingWriter

DEFAULT_LOCATION = WAREHOUSE_LOCATION
SOURCE_METHOD = "pihps_website_json"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="panganlens-ingest",
        description="Run one explicit PIHPS grid ingestion through the guarded warehouse pipeline.",
    )
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--scope", required=True, choices=("national", "region", "market"))
    parser.add_argument("--price-type-id", required=True, type=int)
    parser.add_argument("--comcat-id", required=True)
    parser.add_argument("--province-id", required=True)
    parser.add_argument("--start-date", required=True, type=date.fromisoformat)
    parser.add_argument("--end-date", required=True, type=date.fromisoformat)
    parser.add_argument("--regency-id", action="append", default=[])
    parser.add_argument(
        "--show-regencies",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    parser.add_argument(
        "--show-markets",
        action=argparse.BooleanOptionalAction,
        default=False,
    )
    parser.add_argument("--report-type", type=int, choices=(1, 2, 3), default=1)
    parser.add_argument("--run-id")
    parser.add_argument("--capture-id")
    parser.add_argument("--location", default=DEFAULT_LOCATION)
    return parser


def build_request(args: argparse.Namespace) -> GridRequest:
    return GridRequest(
        price_type_id=args.price_type_id,
        comcat_id=args.comcat_id,
        province_id=args.province_id,
        start_date=args.start_date,
        end_date=args.end_date,
        regency_ids=tuple(args.regency_id),
        show_regencies=args.show_regencies,
        show_markets=args.show_markets,
        report_type=args.report_type,
    )


def build_context(
    args: argparse.Namespace,
    request: GridRequest,
    captured_at: datetime,
) -> IngestionContext:
    run_id = args.run_id or _generated_id("run", captured_at)
    capture_id = args.capture_id or _generated_id("capture", captured_at)
    return IngestionContext(
        run_id=run_id,
        capture_id=capture_id,
        source_method=SOURCE_METHOD,
        scope=args.scope,
        captured_at=captured_at,
        normalized_at=captured_at,
        request_parameters=dict(request.as_params()),
        start_date=request.start_date,
        end_date=request.end_date,
    )


def run(args: argparse.Namespace) -> PipelineOutcome:
    request = build_request(args)
    captured_at = datetime.now(UTC)
    context = build_context(args, request, captured_at)

    client = bigquery.Client(project=args.project_id, location=args.location)
    source_client = PihpsWebsiteClient()
    resolver = BigQueryReviewedMappingResolver(
        args.project_id,
        client=client,
        location=args.location,
    )
    raw_warehouse = BigQueryWarehouse(
        args.project_id,
        client=client,
        location=args.location,
    )
    staging_writer = BigQueryStagingWriter(
        args.project_id,
        client=client,
        location=args.location,
    )
    promotion_runner = BigQueryPromotionRunner(
        args.project_id,
        client=client,
        location=args.location,
    )
    state_manager = BigQueryRunStateManager(
        args.project_id,
        client=client,
        location=args.location,
    )
    return execute_grid_run(
        request,
        context,
        source_client,
        resolver,
        raw_warehouse,
        staging_writer,
        promotion_runner,
        state_manager,
    )


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    outcome = run(args)
    print(json.dumps(_outcome_payload(outcome), sort_keys=True, separators=(",", ":")))
    return 0 if outcome.status in {"SUCCESS", "NO_NEW_DATA"} else 2


def _generated_id(prefix: str, timestamp: datetime) -> str:
    return f"{prefix}-{timestamp:%Y%m%dT%H%M%SZ}-{uuid4().hex[:12]}"


def _outcome_payload(outcome: PipelineOutcome) -> dict[str, object]:
    return {
        "run_id": outcome.run_id,
        "status": outcome.status,
        "source_observation_date": (
            outcome.source_observation_date.isoformat()
            if outcome.source_observation_date is not None
            else None
        ),
        "rows_received": outcome.rows_received,
        "rows_clean": outcome.rows_clean,
        "rows_duplicate": outcome.rows_duplicate,
        "rows_conflict": outcome.rows_conflict,
        "rows_quarantined": outcome.rows_quarantined,
        "error_message": outcome.error_message,
    }


if __name__ == "__main__":
    raise SystemExit(main())
