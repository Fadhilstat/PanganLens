"""Orchestrate validated PIHPS captures into audited staging candidates."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Protocol

from panganlens.ingestion.pihps_interface import SourceRows
from panganlens.ingestion.pihps_parser import GridPricePoint, parse_grid_rows
from panganlens.warehouse.loader import BigQueryWarehouse, RawCaptureRecord
from panganlens.warehouse.staging_writer import (
    BigQueryStagingWriter,
    StagingCandidate,
    StagingConflictError,
)

SOURCE_NAME = "PIHPS Bank Indonesia public website interface"


@dataclass(frozen=True, slots=True)
class IngestionContext:
    """Reviewed request context shared across one PIHPS grid capture."""

    run_id: str
    capture_id: str
    source_method: str
    scope: str
    captured_at: datetime
    normalized_at: datetime
    request_parameters: dict[str, object]
    start_date: date
    end_date: date

    def validate(self) -> None:
        if not self.run_id.strip() or not self.capture_id.strip():
            raise ValueError("run_id and capture_id must not be empty")
        if not self.source_method.strip():
            raise ValueError("source_method must not be empty")
        if self.scope not in {"national", "region", "market"}:
            raise ValueError("scope is not supported")
        if self.captured_at.tzinfo is None or self.normalized_at.tzinfo is None:
            raise ValueError("ingestion timestamps must be timezone-aware")
        if self.end_date < self.start_date:
            raise ValueError("end_date cannot be earlier than start_date")


@dataclass(frozen=True, slots=True)
class CanonicalMapping:
    """One reviewed mapping decision for a parsed PIHPS source point."""

    commodity_id: str
    channel_id: str
    mapping_version: int
    mapping_key_fingerprint: str
    region_id: str | None = None
    market_id: str | None = None


class MappingResolver(Protocol):
    """Resolve source points only through reviewed canonical mapping rules."""

    def resolve(
        self,
        point: GridPricePoint,
        context: IngestionContext,
    ) -> CanonicalMapping | None: ...


@dataclass(frozen=True, slots=True)
class IngestionSummary:
    """Auditable outcome for one source capture through the staging boundary."""

    parsed_points: int
    missing_price_cells: int
    staged_rows: int
    exact_duplicates: int
    conflict_rows: int
    quarantined_rows: int
    latest_observation_date: date | None
    promotion_eligible: bool


def ingest_grid_capture(
    source: SourceRows,
    context: IngestionContext,
    resolver: MappingResolver,
    raw_warehouse: BigQueryWarehouse,
    staging_writer: BigQueryStagingWriter,
) -> IngestionSummary:
    """Persist raw evidence first, then parse, map, and write staging rows."""

    context.validate()
    raw_warehouse.persist_raw_capture(_raw_record(source, context))

    parsed = parse_grid_rows(
        source.rows,
        start_date=context.start_date,
        end_date=context.end_date,
    )
    candidates = [
        _staging_candidate(point, context, resolver.resolve(point, context))
        for point in parsed.points
    ]
    latest_observation_date = max(
        (point.observation_date for point in parsed.points),
        default=None,
    )

    try:
        prepared = staging_writer.persist_batch(candidates)
    except StagingConflictError as exc:
        return IngestionSummary(
            parsed_points=len(parsed.points),
            missing_price_cells=parsed.missing_price_cells,
            staged_rows=0,
            exact_duplicates=0,
            conflict_rows=exc.conflict_count,
            quarantined_rows=0,
            latest_observation_date=latest_observation_date,
            promotion_eligible=False,
        )

    quarantined = sum(row.validation_status != "VALID" for row in prepared.rows)
    return IngestionSummary(
        parsed_points=len(parsed.points),
        missing_price_cells=parsed.missing_price_cells,
        staged_rows=len(prepared.rows),
        exact_duplicates=prepared.exact_duplicate_count,
        conflict_rows=0,
        quarantined_rows=quarantined,
        latest_observation_date=latest_observation_date,
        promotion_eligible=quarantined == 0,
    )


def _raw_record(source: SourceRows, context: IngestionContext) -> RawCaptureRecord:
    evidence = source.evidence
    return RawCaptureRecord(
        capture_id=context.capture_id,
        run_id=context.run_id,
        captured_at=context.captured_at,
        source_method=context.source_method,
        request_parameters=context.request_parameters,
        request_fingerprint=evidence.request_fingerprint,
        schema_fingerprint=evidence.schema_fingerprint,
        payload_text=source.payload_text,
        payload_bytes=evidence.payload_bytes,
        payload_sha256=evidence.payload_sha256,
        source_name=SOURCE_NAME,
        source_url=evidence.source_url,
        source_host=evidence.source_host,
        content_type=evidence.content_type,
        requested_at=evidence.requested_at,
        completed_at=evidence.completed_at,
        http_status=evidence.http_status,
    )


def _staging_candidate(
    point: GridPricePoint,
    context: IngestionContext,
    mapping: CanonicalMapping | None,
) -> StagingCandidate:
    if mapping is None:
        return StagingCandidate(
            run_id=context.run_id,
            capture_id=context.capture_id,
            observation_date=point.observation_date,
            scope=context.scope,
            commodity_id=None,
            channel_id=None,
            region_id=None,
            market_id=None,
            source_row_name=point.source_row_name,
            source_row_level=point.source_row_level,
            source_row_no=point.source_row_no,
            price=point.price,
            source_method=context.source_method,
            mapping_status="UNMAPPED",
            mapping_version=None,
            mapping_key_fingerprint=None,
            validation_status="QUARANTINED",
            quarantine_reason="reviewed canonical mapping not found",
            normalized_at=context.normalized_at,
        )

    return StagingCandidate(
        run_id=context.run_id,
        capture_id=context.capture_id,
        observation_date=point.observation_date,
        scope=context.scope,
        commodity_id=mapping.commodity_id,
        channel_id=mapping.channel_id,
        region_id=mapping.region_id,
        market_id=mapping.market_id,
        source_row_name=point.source_row_name,
        source_row_level=point.source_row_level,
        source_row_no=point.source_row_no,
        price=point.price,
        source_method=context.source_method,
        mapping_status="MAPPED",
        mapping_version=mapping.mapping_version,
        mapping_key_fingerprint=mapping.mapping_key_fingerprint,
        validation_status="VALID",
        quarantine_reason=None,
        normalized_at=context.normalized_at,
    )
