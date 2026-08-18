"""Retry-safe staging writes for normalized PanganLens price candidates."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from google.cloud import bigquery

SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
VALID_SCOPES = {"national", "region", "market"}
VALID_MAPPING_STATUSES = {"MAPPED", "UNMAPPED"}
VALIDATION_STATUSES = {"VALID", "INVALID", "QUARANTINED"}


@dataclass(frozen=True, slots=True)
class StagingCandidate:
    """One normalized source observation before promotion into warehouse core."""

    run_id: str
    capture_id: str
    observation_date: date
    scope: str
    commodity_id: str | None
    channel_id: str | None
    region_id: str | None
    market_id: str | None
    source_row_name: str
    source_row_level: str
    source_row_no: str
    price: Decimal
    source_method: str
    mapping_status: str
    mapping_version: int | None
    mapping_key_fingerprint: str | None
    validation_status: str
    quarantine_reason: str | None
    normalized_at: datetime

    def validate(self) -> None:
        if not self.run_id.strip() or not self.capture_id.strip():
            raise ValueError("run_id and capture_id must not be empty")
        if self.scope not in VALID_SCOPES:
            raise ValueError("scope is not supported")
        if not self.source_row_name.strip():
            raise ValueError("source_row_name must not be empty")
        if not self.source_row_level.strip() or not self.source_row_no.strip():
            raise ValueError("source row identity must be complete")
        if not self.source_method.strip():
            raise ValueError("source_method must not be empty")
        if self.price <= 0:
            raise ValueError("price must be positive")
        if self.mapping_status not in VALID_MAPPING_STATUSES:
            raise ValueError("mapping_status is not supported")
        if self.validation_status not in VALIDATION_STATUSES:
            raise ValueError("validation_status is not supported")
        if self.normalized_at.tzinfo is None:
            raise ValueError("normalized_at must be timezone-aware")

        if self.mapping_status == "MAPPED":
            if self.commodity_id is None or self.channel_id is None:
                raise ValueError("mapped rows require commodity_id and channel_id")
            if self.mapping_version is None or self.mapping_version <= 0:
                raise ValueError("mapped rows require a positive mapping_version")
            if not self.mapping_key_fingerprint:
                raise ValueError("mapped rows require mapping_key_fingerprint")
            if not SHA256_PATTERN.fullmatch(self.mapping_key_fingerprint):
                raise ValueError("mapping_key_fingerprint must be lowercase SHA-256")
            if self.scope == "region" and self.region_id is None:
                raise ValueError("region rows require region_id")
            if self.scope == "market" and self.market_id is None:
                raise ValueError("market rows require market_id")
        elif not self.quarantine_reason:
            raise ValueError("unmapped rows require quarantine_reason")

        if self.validation_status != "VALID" and not self.quarantine_reason:
            raise ValueError("non-valid rows require quarantine_reason")

    def canonical_business_key(self) -> dict[str, str]:
        if self.mapping_status != "MAPPED":
            raise ValueError("unmapped rows do not have a canonical business key")

        key = {
            "observation_date": self.observation_date.isoformat(),
            "commodity_id": self.commodity_id or "",
        }
        if self.scope == "national":
            key["channel_id"] = self.channel_id or ""
        elif self.scope == "region":
            key["channel_id"] = self.channel_id or ""
            key["region_id"] = self.region_id or ""
        else:
            key["market_id"] = self.market_id or ""
        return key

    def business_key_hash(self) -> str | None:
        if self.mapping_status != "MAPPED":
            return None
        payload = _canonical_json(self.canonical_business_key())
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def record_hash(self) -> str | None:
        business_key_hash = self.business_key_hash()
        if business_key_hash is None:
            return None
        payload = _canonical_json(
            {
                "business_key_hash": business_key_hash,
                "price": _decimal_text(self.price),
            }
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class PreparedBatch:
    """Validated staging rows after exact duplicate collapse."""

    rows: tuple[StagingCandidate, ...]
    exact_duplicate_count: int


class StagingConflictError(ValueError):
    """Raised when validated business keys contain conflicting values."""

    def __init__(self, message: str, conflict_count: int) -> None:
        super().__init__(message)
        if conflict_count <= 0:
            raise ValueError("conflict_count must be positive")
        self.conflict_count = conflict_count


def prepare_batch(candidates: list[StagingCandidate]) -> PreparedBatch:
    if not candidates:
        return PreparedBatch(rows=(), exact_duplicate_count=0)

    for candidate in candidates:
        candidate.validate()

    run_ids = {candidate.run_id for candidate in candidates}
    if len(run_ids) != 1:
        raise ValueError("one staging batch must contain exactly one run_id")

    valid_by_key: dict[str, dict[str, StagingCandidate]] = {}
    passthrough: list[StagingCandidate] = []
    duplicate_count = 0

    for candidate in candidates:
        business_hash = candidate.business_key_hash()
        record_hash = candidate.record_hash()
        if candidate.validation_status != "VALID" or business_hash is None or record_hash is None:
            passthrough.append(candidate)
            continue

        records = valid_by_key.setdefault(business_hash, {})
        if record_hash in records:
            duplicate_count += 1
            continue
        records[record_hash] = candidate

    conflicts = [key for key, records in valid_by_key.items() if len(records) > 1]
    if conflicts:
        raise StagingConflictError(
            "validated candidates contain conflicting values for a business key",
            conflict_count=len(conflicts),
        )

    unique_valid = [next(iter(records.values())) for records in valid_by_key.values()]
    return PreparedBatch(
        rows=tuple(unique_valid + passthrough),
        exact_duplicate_count=duplicate_count,
    )


class BigQueryStagingWriter:
    """Persist normalized candidates without creating duplicate staging facts on retry."""

    def __init__(
        self,
        project_id: str,
        client: bigquery.Client | None = None,
        location: str = "asia-southeast2",
    ) -> None:
        self.project_id = project_id
        self.location = location
        self.client = client or bigquery.Client(project=project_id, location=location)

    def persist_batch(self, candidates: list[StagingCandidate]) -> PreparedBatch:
        prepared = prepare_batch(candidates)
        if not prepared.rows:
            return prepared

        payload = [_row_payload(row) for row in prepared.rows]
        table = f"`{self.project_id}.panganlens_staging.normalized_price_candidate`"
        query = f"""
MERGE {table} AS target
USING (
  SELECT
    JSON_VALUE(item, '$.run_id') AS run_id,
    JSON_VALUE(item, '$.capture_id') AS capture_id,
    DATE(JSON_VALUE(item, '$.observation_date')) AS observation_date,
    JSON_VALUE(item, '$.scope') AS scope,
    NULLIF(JSON_VALUE(item, '$.commodity_id'), '') AS commodity_id,
    NULLIF(JSON_VALUE(item, '$.channel_id'), '') AS channel_id,
    NULLIF(JSON_VALUE(item, '$.region_id'), '') AS region_id,
    NULLIF(JSON_VALUE(item, '$.market_id'), '') AS market_id,
    JSON_VALUE(item, '$.source_row_name') AS source_row_name,
    JSON_VALUE(item, '$.source_row_level') AS source_row_level,
    JSON_VALUE(item, '$.source_row_no') AS source_row_no,
    PARSE_NUMERIC(JSON_VALUE(item, '$.price')) AS price,
    JSON_VALUE(item, '$.source_method') AS source_method,
    JSON_VALUE(item, '$.mapping_status') AS mapping_status,
    SAFE_CAST(JSON_VALUE(item, '$.mapping_version') AS INT64) AS mapping_version,
    NULLIF(JSON_VALUE(item, '$.mapping_key_fingerprint'), '') AS mapping_key_fingerprint,
    JSON_VALUE(item, '$.validation_status') AS validation_status,
    NULLIF(JSON_VALUE(item, '$.quarantine_reason'), '') AS quarantine_reason,
    NULLIF(JSON_VALUE(item, '$.business_key_hash'), '') AS business_key_hash,
    NULLIF(JSON_VALUE(item, '$.record_hash'), '') AS record_hash,
    TIMESTAMP(JSON_VALUE(item, '$.normalized_at')) AS normalized_at
  FROM UNNEST(JSON_QUERY_ARRAY(PARSE_JSON(@rows_json))) AS item
) AS source
ON target.run_id = source.run_id
AND target.capture_id = source.capture_id
AND target.source_row_no = source.source_row_no
AND target.observation_date = source.observation_date
AND target.scope = source.scope
AND COALESCE(target.business_key_hash, '') = COALESCE(source.business_key_hash, '')
AND COALESCE(target.record_hash, '') = COALESCE(source.record_hash, '')
WHEN NOT MATCHED THEN
  INSERT (
    run_id, capture_id, observation_date, scope, commodity_id, channel_id,
    region_id, market_id, source_row_name, source_row_level, source_row_no,
    price, source_method, mapping_status, mapping_version, mapping_key_fingerprint,
    validation_status, quarantine_reason, business_key_hash, record_hash, normalized_at
  )
  VALUES (
    source.run_id, source.capture_id, source.observation_date, source.scope,
    source.commodity_id, source.channel_id, source.region_id, source.market_id,
    source.source_row_name, source.source_row_level, source.source_row_no,
    source.price, source.source_method, source.mapping_status, source.mapping_version,
    source.mapping_key_fingerprint, source.validation_status, source.quarantine_reason,
    source.business_key_hash, source.record_hash, source.normalized_at
  );
"""
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter(
                    "rows_json",
                    "STRING",
                    json.dumps(payload, separators=(",", ":"), ensure_ascii=False),
                )
            ]
        )
        self.client.query(query, job_config=job_config, location=self.location).result()
        return prepared


def _row_payload(candidate: StagingCandidate) -> dict[str, object]:
    return {
        "run_id": candidate.run_id,
        "capture_id": candidate.capture_id,
        "observation_date": candidate.observation_date.isoformat(),
        "scope": candidate.scope,
        "commodity_id": candidate.commodity_id or "",
        "channel_id": candidate.channel_id or "",
        "region_id": candidate.region_id or "",
        "market_id": candidate.market_id or "",
        "source_row_name": candidate.source_row_name,
        "source_row_level": candidate.source_row_level,
        "source_row_no": candidate.source_row_no,
        "price": _decimal_text(candidate.price),
        "source_method": candidate.source_method,
        "mapping_status": candidate.mapping_status,
        "mapping_version": candidate.mapping_version,
        "mapping_key_fingerprint": candidate.mapping_key_fingerprint or "",
        "validation_status": candidate.validation_status,
        "quarantine_reason": candidate.quarantine_reason or "",
        "business_key_hash": candidate.business_key_hash() or "",
        "record_hash": candidate.record_hash() or "",
        "normalized_at": candidate.normalized_at.isoformat(),
    }


def _decimal_text(value: Decimal) -> str:
    return format(value, "f")


def _canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
