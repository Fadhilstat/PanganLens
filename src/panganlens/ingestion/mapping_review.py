"""Build and persist mapping candidates without guessing canonical identities."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime

from google.cloud import bigquery

from panganlens.ingestion.mapping_resolver import (
    SOURCE_SYSTEM,
    MappingKey,
    normalize_source_level,
    normalize_source_name,
)
from panganlens.ingestion.orchestration import IngestionContext
from panganlens.ingestion.pihps_parser import GridPricePoint
from panganlens.schema_contract import WAREHOUSE_LOCATION
from panganlens.warehouse.loader import PROJECT_ID_PATTERN, SHA256_PATTERN


@dataclass(frozen=True, slots=True)
class MappingReviewCandidate:
    """One exact source identity waiting for an explicit human mapping decision."""

    candidate_fingerprint: str
    source_system: str
    entity_type: str
    source_id: str | None
    source_name_normalized: str | None
    source_level: str | None
    parent_source_id: str | None
    mapping_version: int
    evidence_capture_id: str
    source_schema_fingerprint: str

    def validate(self) -> None:
        if self.source_system != SOURCE_SYSTEM:
            raise ValueError("source_system is not supported")
        if self.entity_type not in {"commodity", "channel", "region", "market"}:
            raise ValueError("entity_type is not supported")
        if self.mapping_version <= 0:
            raise ValueError("mapping_version must be positive")
        if not self.evidence_capture_id.strip():
            raise ValueError("evidence_capture_id must not be empty")
        if not SHA256_PATTERN.fullmatch(self.source_schema_fingerprint):
            raise ValueError("source_schema_fingerprint must be a lowercase SHA-256 digest")
        if not SHA256_PATTERN.fullmatch(self.candidate_fingerprint):
            raise ValueError("candidate_fingerprint must be a lowercase SHA-256 digest")


def build_mapping_candidates(
    points: Iterable[GridPricePoint],
    context: IngestionContext,
    *,
    mapping_version: int,
    source_schema_fingerprint: str,
) -> tuple[MappingReviewCandidate, ...]:
    """Return deterministic review candidates from exact production mapping keys."""

    context.validate()
    if mapping_version <= 0:
        raise ValueError("mapping_version must be positive")

    keys: set[MappingKey] = set()
    params = context.request_parameters
    commodity_id = _required_param(params, "comcat_id")
    channel_id = _required_param(params, "price_type_id")
    keys.add(MappingKey(entity_type="commodity", source_id=commodity_id))
    keys.add(MappingKey(entity_type="channel", source_id=channel_id))

    for point in points:
        if context.scope == "region":
            keys.add(
                MappingKey(
                    entity_type="region",
                    source_name_normalized=normalize_source_name(point.source_row_name),
                    source_level=normalize_source_level(point.source_row_level),
                )
            )
        elif context.scope == "market":
            keys.add(
                MappingKey(
                    entity_type="market",
                    source_name_normalized=normalize_source_name(point.source_row_name),
                    source_level=normalize_source_level(point.source_row_level),
                    parent_source_id=_required_param(params, "province_id"),
                )
            )

    candidates = [
        _candidate(
            key,
            mapping_version=mapping_version,
            evidence_capture_id=context.capture_id,
            source_schema_fingerprint=source_schema_fingerprint,
        )
        for key in keys
    ]
    return tuple(sorted(candidates, key=lambda item: item.candidate_fingerprint))


class BigQueryMappingReviewQueue:
    """Persist exact source identities into a human review queue idempotently."""

    def __init__(
        self,
        project_id: str,
        client: bigquery.Client | None = None,
        location: str = WAREHOUSE_LOCATION,
    ) -> None:
        if not PROJECT_ID_PATTERN.fullmatch(project_id):
            raise ValueError("project_id is not a valid Google Cloud project ID")
        self.project_id = project_id
        self.location = location
        self.client = client or bigquery.Client(project=project_id, location=location)

    def persist(self, candidates: Iterable[MappingReviewCandidate]) -> int:
        rows = tuple(candidates)
        for candidate in rows:
            candidate.validate()
        if not rows:
            return 0

        payload = [_payload(candidate) for candidate in rows]
        query = f"""
MERGE `{self.project_id}.panganlens_ops.source_mapping_review_candidate` AS target
USING (
  SELECT
    JSON_VALUE(item, '$.candidate_fingerprint') AS candidate_fingerprint,
    JSON_VALUE(item, '$.source_system') AS source_system,
    JSON_VALUE(item, '$.entity_type') AS entity_type,
    NULLIF(JSON_VALUE(item, '$.source_id'), '') AS source_id,
    NULLIF(JSON_VALUE(item, '$.source_name_normalized'), '') AS source_name_normalized,
    NULLIF(JSON_VALUE(item, '$.source_level'), '') AS source_level,
    NULLIF(JSON_VALUE(item, '$.parent_source_id'), '') AS parent_source_id,
    CAST(JSON_VALUE(item, '$.mapping_version') AS INT64) AS mapping_version,
    JSON_VALUE(item, '$.evidence_capture_id') AS evidence_capture_id,
    JSON_VALUE(item, '$.source_schema_fingerprint') AS source_schema_fingerprint
  FROM UNNEST(JSON_QUERY_ARRAY(PARSE_JSON(@rows_json))) AS item
) AS source
ON target.candidate_fingerprint = source.candidate_fingerprint
WHEN MATCHED AND target.review_status = 'REVIEW_REQUIRED' THEN
  UPDATE SET
    evidence_capture_id = source.evidence_capture_id,
    source_schema_fingerprint = source.source_schema_fingerprint,
    last_seen_at = CURRENT_TIMESTAMP()
WHEN NOT MATCHED THEN
  INSERT (
    candidate_fingerprint, source_system, entity_type, source_id,
    source_name_normalized, source_level, parent_source_id, mapping_version,
    review_status, proposed_canonical_id, evidence_capture_id,
    source_schema_fingerprint, created_at, last_seen_at, reviewed_at,
    reviewed_by, review_note
  )
  VALUES (
    source.candidate_fingerprint, source.source_system, source.entity_type,
    source.source_id, source.source_name_normalized, source.source_level,
    source.parent_source_id, source.mapping_version, 'REVIEW_REQUIRED', NULL,
    source.evidence_capture_id, source.source_schema_fingerprint,
    CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP(), NULL, NULL, NULL
  );
"""
        config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter(
                    "rows_json",
                    "STRING",
                    json.dumps(payload, sort_keys=True, separators=(",", ":")),
                )
            ]
        )
        self.client.query(query, job_config=config, location=self.location).result()
        return len(rows)


def _candidate(
    key: MappingKey,
    *,
    mapping_version: int,
    evidence_capture_id: str,
    source_schema_fingerprint: str,
) -> MappingReviewCandidate:
    identity = {
        "source_system": SOURCE_SYSTEM,
        "entity_type": key.entity_type,
        "source_id": key.source_id,
        "source_name_normalized": key.source_name_normalized,
        "source_level": key.source_level,
        "parent_source_id": key.parent_source_id,
        "mapping_version": mapping_version,
    }
    text = json.dumps(identity, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return MappingReviewCandidate(
        candidate_fingerprint=hashlib.sha256(text.encode("utf-8")).hexdigest(),
        source_system=SOURCE_SYSTEM,
        entity_type=key.entity_type,
        source_id=key.source_id,
        source_name_normalized=key.source_name_normalized,
        source_level=key.source_level,
        parent_source_id=key.parent_source_id,
        mapping_version=mapping_version,
        evidence_capture_id=evidence_capture_id,
        source_schema_fingerprint=source_schema_fingerprint,
    )


def _payload(candidate: MappingReviewCandidate) -> dict[str, object]:
    return {
        "candidate_fingerprint": candidate.candidate_fingerprint,
        "source_system": candidate.source_system,
        "entity_type": candidate.entity_type,
        "source_id": candidate.source_id or "",
        "source_name_normalized": candidate.source_name_normalized or "",
        "source_level": candidate.source_level or "",
        "parent_source_id": candidate.parent_source_id or "",
        "mapping_version": candidate.mapping_version,
        "evidence_capture_id": candidate.evidence_capture_id,
        "source_schema_fingerprint": candidate.source_schema_fingerprint,
        "generated_at": datetime.now(UTC).isoformat(),
    }


def _required_param(params: dict[str, object], name: str) -> str:
    value = str(params.get(name) or "").strip()
    if not value:
        raise ValueError(f"request_parameters must include {name}")
    return value
