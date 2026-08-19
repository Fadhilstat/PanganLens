"""Idempotent BigQuery write path for trusted source captures."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime

from google.cloud import bigquery

from panganlens.schema_contract import WAREHOUSE_LOCATION

PROJECT_ID_PATTERN = re.compile(r"^[a-z][a-z0-9-]{4,28}[a-z0-9]$")
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True, slots=True)
class RawCaptureRecord:
    """One validated raw source response ready for warehouse persistence."""

    capture_id: str
    run_id: str
    captured_at: datetime
    source_method: str
    request_parameters: Mapping[str, object]
    request_fingerprint: str
    schema_fingerprint: str
    payload_text: str
    payload_bytes: int
    payload_sha256: str
    source_name: str
    source_url: str
    source_host: str
    content_type: str
    requested_at: datetime
    completed_at: datetime
    http_status: int
    status: str = "SUCCESS"

    def validate(self) -> None:
        if not self.capture_id.strip():
            raise ValueError("capture_id must not be empty")
        if not self.run_id.strip():
            raise ValueError("run_id must not be empty")
        if not self.source_method.strip():
            raise ValueError("source_method must not be empty")
        if not self.source_name.strip():
            raise ValueError("source_name must not be empty")
        if not self.source_url.strip() or not self.source_host.strip():
            raise ValueError("source URL and host must not be empty")
        if not self.content_type.strip():
            raise ValueError("content_type must not be empty")
        if self.status != "SUCCESS":
            raise ValueError("raw capture status must be SUCCESS")
        if self.captured_at.tzinfo is None:
            raise ValueError("captured_at must be timezone-aware")
        if self.requested_at.tzinfo is None or self.completed_at.tzinfo is None:
            raise ValueError("source timing evidence must be timezone-aware")
        if self.completed_at < self.requested_at:
            raise ValueError("completed_at cannot be earlier than requested_at")
        if not 200 <= self.http_status < 300:
            raise ValueError("http_status must be a successful HTTP status")
        if not SHA256_PATTERN.fullmatch(self.request_fingerprint):
            raise ValueError("request_fingerprint must be a lowercase SHA-256 digest")
        if not SHA256_PATTERN.fullmatch(self.schema_fingerprint):
            raise ValueError("schema_fingerprint must be a lowercase SHA-256 digest")
        if not SHA256_PATTERN.fullmatch(self.payload_sha256):
            raise ValueError("payload_sha256 must be a lowercase SHA-256 digest")

        payload = self.payload_text.encode("utf-8")
        if len(payload) != self.payload_bytes:
            raise ValueError("payload_bytes does not match the UTF-8 payload size")
        actual_hash = hashlib.sha256(payload).hexdigest()
        if actual_hash != self.payload_sha256:
            raise ValueError("payload_sha256 does not match payload_text")


class BigQueryWarehouse:
    """Persist validated records without relying on database-enforced keys."""

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

    def persist_raw_capture(self, record: RawCaptureRecord) -> None:
        """Persist capture audit and raw payload idempotently in one script."""

        record.validate()
        raw_table = f"`{self.project_id}.panganlens_raw.raw_food_price_capture`"
        audit_table = f"`{self.project_id}.panganlens_ops.source_capture`"
        query = f"""
DECLARE existing_hash STRING DEFAULT (
  SELECT ANY_VALUE(payload_sha256)
  FROM {raw_table}
  WHERE capture_id = @capture_id
);
DECLARE existing_request_fingerprint STRING DEFAULT (
  SELECT ANY_VALUE(request_fingerprint)
  FROM {audit_table}
  WHERE capture_id = @capture_id
);
DECLARE existing_schema_fingerprint STRING DEFAULT (
  SELECT ANY_VALUE(schema_fingerprint)
  FROM {audit_table}
  WHERE capture_id = @capture_id
);

ASSERT existing_hash IS NULL OR existing_hash = @payload_sha256
  AS 'capture_id already exists with a different payload hash';
ASSERT existing_request_fingerprint IS NULL
  OR existing_request_fingerprint = @request_fingerprint
  AS 'capture_id already exists with a different request fingerprint';
ASSERT existing_schema_fingerprint IS NULL
  OR existing_schema_fingerprint = @schema_fingerprint
  AS 'capture_id already exists with a different schema fingerprint';

MERGE {audit_table} AS target
USING (
  SELECT
    @capture_id AS capture_id,
    @run_id AS run_id,
    @source_name AS source_name,
    @source_method AS source_method,
    @source_url AS source_url,
    @source_host AS source_host,
    @content_type AS content_type,
    @request_fingerprint AS request_fingerprint,
    @schema_fingerprint AS schema_fingerprint,
    @requested_at AS requested_at,
    @completed_at AS completed_at,
    @http_status AS http_status,
    @payload_bytes AS payload_bytes,
    @payload_sha256 AS payload_sha256,
    @status AS status
) AS source
ON target.capture_id = source.capture_id
WHEN NOT MATCHED THEN
  INSERT (
    capture_id, run_id, source_name, source_method, source_url, source_host,
    content_type, request_fingerprint, schema_fingerprint, requested_at,
    completed_at, http_status, payload_bytes, payload_sha256, status, error_message
  )
  VALUES (
    source.capture_id, source.run_id, source.source_name, source.source_method,
    source.source_url, source.source_host, source.content_type,
    source.request_fingerprint, source.schema_fingerprint, source.requested_at,
    source.completed_at, source.http_status, source.payload_bytes,
    source.payload_sha256, source.status, NULL
  );

MERGE {raw_table} AS target
USING (
  SELECT
    @capture_id AS capture_id,
    @run_id AS run_id,
    @captured_at AS captured_at,
    @source_method AS source_method,
    PARSE_JSON(@request_parameters_json) AS request_parameters,
    @request_fingerprint AS request_fingerprint,
    @schema_fingerprint AS schema_fingerprint,
    @payload_text AS payload_text,
    @payload_bytes AS payload_bytes,
    @payload_sha256 AS payload_sha256
) AS source
ON target.capture_id = source.capture_id
WHEN NOT MATCHED THEN
  INSERT (
    capture_id,
    run_id,
    captured_at,
    source_method,
    request_parameters,
    request_fingerprint,
    schema_fingerprint,
    payload_text,
    payload_bytes,
    payload_sha256
  )
  VALUES (
    source.capture_id,
    source.run_id,
    source.captured_at,
    source.source_method,
    source.request_parameters,
    source.request_fingerprint,
    source.schema_fingerprint,
    source.payload_text,
    source.payload_bytes,
    source.payload_sha256
  );
"""
        parameters = [
            bigquery.ScalarQueryParameter("capture_id", "STRING", record.capture_id),
            bigquery.ScalarQueryParameter("run_id", "STRING", record.run_id),
            bigquery.ScalarQueryParameter("captured_at", "TIMESTAMP", record.captured_at),
            bigquery.ScalarQueryParameter("source_name", "STRING", record.source_name),
            bigquery.ScalarQueryParameter("source_method", "STRING", record.source_method),
            bigquery.ScalarQueryParameter("source_url", "STRING", record.source_url),
            bigquery.ScalarQueryParameter("source_host", "STRING", record.source_host),
            bigquery.ScalarQueryParameter("content_type", "STRING", record.content_type),
            bigquery.ScalarQueryParameter(
                "request_parameters_json",
                "STRING",
                json.dumps(record.request_parameters, sort_keys=True, separators=(",", ":")),
            ),
            bigquery.ScalarQueryParameter(
                "request_fingerprint", "STRING", record.request_fingerprint
            ),
            bigquery.ScalarQueryParameter(
                "schema_fingerprint", "STRING", record.schema_fingerprint
            ),
            bigquery.ScalarQueryParameter("requested_at", "TIMESTAMP", record.requested_at),
            bigquery.ScalarQueryParameter("completed_at", "TIMESTAMP", record.completed_at),
            bigquery.ScalarQueryParameter("http_status", "INT64", record.http_status),
            bigquery.ScalarQueryParameter("payload_text", "STRING", record.payload_text),
            bigquery.ScalarQueryParameter("payload_bytes", "INT64", record.payload_bytes),
            bigquery.ScalarQueryParameter("payload_sha256", "STRING", record.payload_sha256),
            bigquery.ScalarQueryParameter("status", "STRING", record.status),
        ]
        job_config = bigquery.QueryJobConfig(query_parameters=parameters)
        self.client.query(query, job_config=job_config, location=self.location).result()
