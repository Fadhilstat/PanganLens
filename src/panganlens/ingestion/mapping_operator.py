"""Operator workflow for reviewed PIHPS source mappings."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from datetime import date, datetime
from pathlib import Path
from typing import Any

from google.cloud import bigquery

from panganlens.ingestion.mapping_review import (
    BigQueryMappingReviewQueue,
    build_mapping_candidates,
)
from panganlens.ingestion.orchestration import IngestionContext
from panganlens.ingestion.pihps_interface import extract_rows
from panganlens.ingestion.pihps_parser import parse_grid_rows
from panganlens.warehouse.loader import PROJECT_ID_PATTERN

ACTIVATION_SQL = Path(__file__).resolve().parents[3] / "sql/016_activate_reviewed_mapping.sql"
SOURCE_METHOD = "pihps_website_json"


class MappingOperatorError(RuntimeError):
    """Raised when operator evidence is missing, ambiguous, or inconsistent."""


class BigQueryMappingOperator:
    """List, generate, and approve mappings without automatic identity guesses."""

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
        if len(candidate_fingerprint) != 64:
            raise ValueError("candidate_fingerprint must be a SHA-256 hex digest")
        if not canonical_id.strip():
            raise ValueError("canonical_id must not be empty")
        if not reviewed_by.strip():
            raise ValueError("reviewed_by must not be empty")
        if reviewed_at.tzinfo is None:
            raise ValueError("reviewed_at must be timezone-aware")
        if not review_note.strip():
            raise ValueError("review_note must explain the human mapping decision")

        sql = ACTIVATION_SQL.read_text(encoding="utf-8")
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
  USING (capture_id)
WHERE raw.capture_id = @capture_id
  AND audit.status = 'SUCCESS'
  AND raw.payload_sha256 = audit.payload_sha256
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


def _request_date(params: dict[str, object], key: str) -> date:
    value = str(params.get(key) or "").strip()
    if not value:
        raise MappingOperatorError(f"stored request_parameters is missing {key}")
    try:
        return date.fromisoformat(value[:10])
    except ValueError as exc:
        raise MappingOperatorError(f"stored {key} is not a valid ISO date") from exc
