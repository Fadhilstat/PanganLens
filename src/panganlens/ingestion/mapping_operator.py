"""Operator workflow for reviewed PIHPS source mappings."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from datetime import UTC, date, datetime
from importlib.resources import files
from typing import Any

from google.cloud import bigquery

from panganlens.ingestion.mapping_review import (
    BigQueryMappingReviewQueue,
    build_mapping_candidates,
)
from panganlens.ingestion.orchestration import IngestionContext
from panganlens.ingestion.pihps_interface import extract_rows
from panganlens.ingestion.pihps_parser import parse_grid_rows
from panganlens.warehouse.loader import PROJECT_ID_PATTERN, SHA256_PATTERN

ACTIVATION_SQL_RESOURCE = "016_activate_reviewed_mapping.sql"
REJECTION_SQL_RESOURCE = "017_reject_mapping_candidate.sql"
CANONICAL_LOOKUP_MAXIMUM_BYTES_BILLED = 25_000_000

CANONICAL_LOOKUP_SPECS = {
    "commodity": (
        "commodity",
        "commodity_id",
        "commodity_name",
        "TO_JSON_STRING(STRUCT(category_id, unit_id, display_order))",
    ),
    "channel": (
        "market_channel",
        "channel_id",
        "channel_name",
        "TO_JSON_STRING(STRUCT(source_price_type_id))",
    ),
    "region": (
        "region",
        "region_id",
        "region_name",
        "TO_JSON_STRING(STRUCT(parent_region_id, region_level, official_code))",
    ),
    "market": (
        "market",
        "market_id",
        "market_name",
        "TO_JSON_STRING(STRUCT(region_id, channel_id))",
    ),
}


class MappingOperatorError(RuntimeError):
    """Raised when operator evidence is missing, ambiguous, or inconsistent."""


class BigQueryMappingOperator:
    """Operate reviewed mappings while keeping identity decisions human-controlled."""

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
        self.queue = BigQueryMappingReviewQueue(
            project_id,
            client=self.client,
            location=location,
        )

    def list_pending(self, limit: int = 100) -> list[dict[str, Any]]:
        if not 1 <= limit <= 1000:
            raise ValueError("limit must be between 1 and 1000")
        query = f"""
SELECT
  candidate_fingerprint,
  source_system,
  entity_type,
  source_id,
  source_name_normalized,
  source_level,
  parent_source_id,
  mapping_version,
  evidence_capture_id,
  source_schema_fingerprint,
  first_seen_at,
  last_seen_at
FROM `{self.project_id}.panganlens_ops.vw_mapping_review_queue`
ORDER BY first_seen_at, entity_type, candidate_fingerprint
LIMIT @limit
"""
        config = bigquery.QueryJobConfig(
            query_parameters=[bigquery.ScalarQueryParameter("limit", "INT64", limit)]
        )
        rows = self.client.query(query, job_config=config, location=self.location).result()
        return [dict(row.items()) for row in rows]

    def list_canonical_options(
        self,
        entity_type: str,
        search: str = "",
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        if entity_type not in CANONICAL_LOOKUP_SPECS:
            raise ValueError("entity_type is not supported")
        if not 1 <= limit <= 200:
            raise ValueError("limit must be between 1 and 200")
        search_text = search.strip()
        if len(search_text) > 100:
            raise ValueError("search must not exceed 100 characters")

        config = bigquery.QueryJobConfig(
            maximum_bytes_billed=CANONICAL_LOOKUP_MAXIMUM_BYTES_BILLED,
            query_parameters=[
                bigquery.ScalarQueryParameter("search", "STRING", search_text),
                bigquery.ScalarQueryParameter("limit", "INT64", limit),
            ],
        )
        rows = self.client.query(
            _canonical_lookup_sql(self.project_id, entity_type),
            job_config=config,
            location=self.location,
        ).result()
        return [dict(row.items()) for row in rows]

    def generate_from_capture(
        self,
        capture_id: str,
        scope: str,
        mapping_version: int,
    ) -> dict[str, Any]:
        if not capture_id.strip():
            raise ValueError("capture_id must not be empty")
        if scope not in {"national", "region", "market"}:
            raise ValueError("scope is not supported")
        if mapping_version <= 0:
            raise ValueError("mapping_version must be positive")

        evidence = self._load_capture(capture_id)
        payload_text = evidence["payload_text"]
        payload_sha256 = evidence["payload_sha256"]
        actual_hash = hashlib.sha256(payload_text.encode("utf-8")).hexdigest()
        if actual_hash != payload_sha256:
            raise MappingOperatorError("stored raw payload does not match source capture hash")

        request_parameters = evidence["request_parameters"]
        start_date = _request_date(request_parameters, "start_date")
        end_date = _request_date(request_parameters, "end_date")
        parsed = parse_grid_rows(
            extract_rows(json.loads(payload_text)),
            start_date=start_date,
            end_date=end_date,
        )
        captured_at = evidence["completed_at"]
        context = IngestionContext(
            run_id=evidence["run_id"],
            capture_id=capture_id,
            source_method=evidence["source_method"],
            scope=scope,
            captured_at=captured_at,
            normalized_at=captured_at,
            request_parameters=request_parameters,
            start_date=start_date,
            end_date=end_date,
        )
        candidates = build_mapping_candidates(
            parsed.points,
            context,
            mapping_version=mapping_version,
            source_schema_fingerprint=evidence["schema_fingerprint"],
        )
        persisted = self.queue.persist(candidates)
        return {
            "capture_id": capture_id,
            "scope": scope,
            "mapping_version": mapping_version,
            "parsed_points": len(parsed.points),
            "missing_price_cells": parsed.missing_price_cells,
            "candidate_count": len(candidates),
            "persisted_count": persisted,
            "candidates": [asdict(item) for item in candidates],
        }

    def approve(
        self,
        candidate_fingerprint: str,
        canonical_id: str,
        reviewed_by: str,
        reviewed_at: datetime,
        review_note: str,
    ) -> dict[str, Any]:
        _validate_review_metadata(
            candidate_fingerprint,
            reviewed_by,
            reviewed_at,
            review_note,
        )
        if not canonical_id.strip():
            raise ValueError("canonical_id must not be empty")

        sql = _sql_resource_text(ACTIVATION_SQL_RESOURCE)
        config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter(
                    "candidate_fingerprint", "STRING", candidate_fingerprint
                ),
                bigquery.ScalarQueryParameter("canonical_id", "STRING", canonical_id),
                bigquery.ScalarQueryParameter("reviewed_by", "STRING", reviewed_by),
                bigquery.ScalarQueryParameter("reviewed_at", "TIMESTAMP", reviewed_at),
                bigquery.ScalarQueryParameter("review_note", "STRING", review_note),
            ]
        )
        self.client.query(sql, job_config=config, location=self.location).result()
        return {
            "candidate_fingerprint": candidate_fingerprint,
            "canonical_id": canonical_id,
            "reviewed_by": reviewed_by,
            "reviewed_at": reviewed_at.isoformat(),
            "status": "APPROVED",
        }

    def reject(
        self,
        candidate_fingerprint: str,
        reviewed_by: str,
        reviewed_at: datetime,
        review_note: str,
    ) -> dict[str, Any]:
        _validate_review_metadata(
            candidate_fingerprint,
            reviewed_by,
            reviewed_at,
            review_note,
        )
        sql = _sql_resource_text(REJECTION_SQL_RESOURCE)
        config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter(
                    "candidate_fingerprint", "STRING", candidate_fingerprint
                ),
                bigquery.ScalarQueryParameter("reviewed_by", "STRING", reviewed_by),
                bigquery.ScalarQueryParameter("reviewed_at", "TIMESTAMP", reviewed_at),
                bigquery.ScalarQueryParameter("review_note", "STRING", review_note),
            ]
        )
        self.client.query(sql, job_config=config, location=self.location).result()
        return {
            "candidate_fingerprint": candidate_fingerprint,
            "reviewed_by": reviewed_by,
            "reviewed_at": reviewed_at.isoformat(),
            "status": "REJECTED",
        }

    def _load_capture(self, capture_id: str) -> dict[str, Any]:
        query = f"""
SELECT
  raw.capture_id,
  raw.run_id,
  raw.source_method,
  raw.request_parameters,
  raw.payload_text,
  raw.payload_sha256,
  audit.schema_fingerprint,
  audit.completed_at,
  audit.status
FROM `{self.project_id}.panganlens_raw.raw_food_price_capture` AS raw
JOIN `{self.project_id}.panganlens_ops.source_capture` AS audit
  ON audit.capture_id = raw.capture_id
 AND audit.run_id = raw.run_id
 AND audit.source_method = raw.source_method
 AND audit.request_fingerprint = raw.request_fingerprint
 AND audit.schema_fingerprint = raw.schema_fingerprint
 AND audit.payload_sha256 = raw.payload_sha256
WHERE raw.capture_id = @capture_id
  AND audit.status = 'SUCCESS'
  AND audit.source_host = 'www.bi.go.id'
  AND STARTS_WITH(LOWER(audit.content_type), 'application/json')
"""
        config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("capture_id", "STRING", capture_id)
            ]
        )
        rows = list(
            self.client.query(query, job_config=config, location=self.location).result()
        )
        if len(rows) != 1:
            raise MappingOperatorError(
                "capture must exist exactly once with matching successful provenance"
            )
        row = dict(rows[0].items())
        params = row["request_parameters"]
        if isinstance(params, str):
            params = json.loads(params)
        row["request_parameters"] = dict(params)
        return row


def _canonical_lookup_sql(project_id: str, entity_type: str) -> str:
    table, id_column, name_column, context_expression = CANONICAL_LOOKUP_SPECS[entity_type]
    return f"""
SELECT
  {id_column} AS canonical_id,
  {name_column} AS canonical_name,
  {context_expression} AS context_json
FROM `{project_id}.panganlens_core.{table}`
WHERE is_active = TRUE
  AND (
    @search = ''
    OR STRPOS(LOWER({name_column}), LOWER(@search)) > 0
    OR STRPOS(LOWER({id_column}), LOWER(@search)) > 0
  )
ORDER BY canonical_name, canonical_id
LIMIT @limit
"""


def _validate_review_metadata(
    candidate_fingerprint: str,
    reviewed_by: str,
    reviewed_at: datetime,
    review_note: str,
) -> None:
    if not SHA256_PATTERN.fullmatch(candidate_fingerprint):
        raise ValueError("candidate_fingerprint must be a lowercase SHA-256 digest")
    if not reviewed_by.strip():
        raise ValueError("reviewed_by must not be empty")
    if reviewed_at.tzinfo is None:
        raise ValueError("reviewed_at must be timezone-aware")
    if reviewed_at > datetime.now(UTC):
        raise ValueError("reviewed_at must not be in the future")
    if not review_note.strip():
        raise ValueError("review_note must explain the human review decision")


def _sql_resource_text(resource_name: str) -> str:
    try:
        resource = files("panganlens.sql").joinpath(resource_name)
        return resource.read_text(encoding="utf-8")
    except (FileNotFoundError, ModuleNotFoundError) as exc:
        raise MappingOperatorError(
            f"mapping SQL package resource is unavailable: {resource_name}"
        ) from exc


def _activation_sql_text() -> str:
    return _sql_resource_text(ACTIVATION_SQL_RESOURCE)


def _request_date(params: dict[str, object], key: str) -> date:
    value = str(params.get(key) or "").strip()
    if not value:
        raise MappingOperatorError(f"stored request_parameters is missing {key}")
    try:
        return date.fromisoformat(value[:10])
    except ValueError as exc:
        raise MappingOperatorError(f"stored {key} is not a valid ISO date") from exc
