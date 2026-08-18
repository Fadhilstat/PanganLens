import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from panganlens.ingestion.mapping_operator import (
    BigQueryMappingOperator,
    MappingOperatorError,
)
from panganlens.mapping_cli import build_parser

ACTIVATION_SQL = Path("sql/016_activate_reviewed_mapping.sql")


class FakeRow(dict):
    def items(self):
        return super().items()


class FakeJob:
    def __init__(self, rows=()):
        self.rows = list(rows)

    def result(self):
        return self.rows


class FakeClient:
    def __init__(self, responses=()):
        self.responses = list(responses)
        self.calls = []

    def query(self, query, job_config=None, location=None):
        self.calls.append((query, job_config, location))
        rows = self.responses.pop(0) if self.responses else ()
        return FakeJob(rows)


class FakeQueue:
    def __init__(self):
        self.candidates = ()

    def persist(self, candidates):
        self.candidates = tuple(candidates)
        return len(self.candidates)


def _capture_row(payload_text):
    payload_sha256 = hashlib.sha256(payload_text.encode("utf-8")).hexdigest()
    return FakeRow(
        capture_id="capture-1",
        run_id="run-1",
        source_method="pihps_website_json",
        request_parameters={
            "price_type_id": "1",
            "comcat_id": "com_1",
            "province_id": "13",
            "start_date": "2026-08-17T00:00:00.000",
            "end_date": "2026-08-17T00:00:00.000",
        },
        payload_text=payload_text,
        payload_sha256=payload_sha256,
        schema_fingerprint="a" * 64,
        completed_at=datetime(2026, 8, 18, 12, 0, tzinfo=UTC),
        status="SUCCESS",
    )


def test_generate_uses_stored_capture_and_exact_mapping_keys():
    payload = json.dumps(
        {
            "data": [
                {
                    "17/08/2026": 62650,
                    "level": "Provinsi",
                    "name": "DKI Jakarta",
                    "no": "1",
                }
            ]
        }
    )
    client = FakeClient(responses=[[_capture_row(payload)]])
    operator = BigQueryMappingOperator("panganlens-demo", client=client)
    queue = FakeQueue()
    operator.queue = queue

    result = operator.generate_from_capture("capture-1", "region", 3)

    assert result["parsed_points"] == 1
    assert result["candidate_count"] == 3
    assert result["persisted_count"] == 3
    by_type = {item.entity_type: item for item in queue.candidates}
    assert by_type["commodity"].source_id == "com_1"
    assert by_type["channel"].source_id == "1"
    assert by_type["region"].source_name_normalized == "dki jakarta"
    query = client.calls[0][0]
    assert "audit.request_fingerprint = raw.request_fingerprint" in query
    assert "audit.schema_fingerprint = raw.schema_fingerprint" in query
    assert "audit.source_method = raw.source_method" in query
    assert "audit.status = 'SUCCESS'" in query
    assert "audit.source_host = 'www.bi.go.id'" in query


def test_generate_rejects_ambiguous_or_missing_capture():
    operator = BigQueryMappingOperator("panganlens-demo", client=FakeClient(responses=[[]]))

    with pytest.raises(MappingOperatorError, match="exactly once"):
        operator.generate_from_capture("capture-1", "region", 1)


def test_list_pending_is_project_scoped_and_bounded():
    row = FakeRow(candidate_fingerprint="a" * 64, entity_type="commodity")
    client = FakeClient(responses=[[[row][0]]])
    operator = BigQueryMappingOperator("panganlens-demo", client=client)

    result = operator.list_pending(25)

    assert result[0]["entity_type"] == "commodity"
    query = client.calls[0][0]
    assert "`panganlens-demo.panganlens_ops.vw_mapping_review_queue`" in query
    assert "LIMIT @limit" in query

    with pytest.raises(ValueError, match="between 1 and 1000"):
        operator.list_pending(0)


def test_approve_requires_human_evidence_and_safe_timestamp():
    operator = BigQueryMappingOperator("panganlens-demo", client=FakeClient())
    reviewed_at = datetime.now(UTC) - timedelta(minutes=1)

    with pytest.raises(ValueError, match="lowercase SHA-256"):
        operator.approve("not-a-hash", "commodity-1", "fadhil", reviewed_at, "checked")
    with pytest.raises(ValueError, match="review_note"):
        operator.approve("a" * 64, "commodity-1", "fadhil", reviewed_at, "")
    with pytest.raises(ValueError, match="future"):
        operator.approve(
            "a" * 64,
            "commodity-1",
            "fadhil",
            datetime.now(UTC) + timedelta(days=1),
            "matched against reviewed dimension",
        )


def test_approve_executes_guarded_activation_sql():
    client = FakeClient()
    operator = BigQueryMappingOperator("panganlens-demo", client=client)
    reviewed_at = datetime.now(UTC) - timedelta(minutes=1)

    result = operator.approve(
        "a" * 64,
        "commodity-1",
        "fadhil",
        reviewed_at,
        "matched source commodity to reviewed canonical dimension row",
    )

    assert result["status"] == "APPROVED"
    query = client.calls[0][0]
    assert "BEGIN TRANSACTION;" in query
    assert "capture.status = 'SUCCESS'" in query
    assert "capture.payload_sha256 IS NOT NULL" in query
    assert "reviewed_at must not be in the future" in query
    assert "COMMIT TRANSACTION;" in query


def test_mapping_cli_requires_explicit_approval_metadata():
    parser = build_parser()
    args = parser.parse_args(
        [
            "--project-id",
            "panganlens-demo",
            "approve",
            "--candidate-fingerprint",
            "a" * 64,
            "--canonical-id",
            "commodity-1",
            "--reviewed-by",
            "fadhil",
            "--reviewed-at",
            "2026-08-18T20:00:00+07:00",
            "--review-note",
            "matched against reviewed canonical dimension row",
        ]
    )

    assert args.command == "approve"
    assert args.reviewed_by == "fadhil"
    assert args.review_note.startswith("matched")


def test_activation_sql_keeps_operator_guards():
    text = ACTIVATION_SQL.read_text(encoding="utf-8")

    assert "capture.status = 'SUCCESS'" in text
    assert "capture.payload_sha256 IS NOT NULL" in text
    assert "reviewed_at must not be in the future" in text
