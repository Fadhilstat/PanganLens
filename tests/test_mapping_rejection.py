from datetime import UTC, datetime, timedelta
from importlib.resources import files
from pathlib import Path

import pytest

from panganlens.ingestion.mapping_operator import BigQueryMappingOperator
from panganlens.mapping_cli import build_parser

REPO_ROOT = Path(__file__).resolve().parents[1]
CANONICAL_SQL = REPO_ROOT / "sql" / "017_reject_mapping_candidate.sql"


class FakeJob:
    def result(self):
        return []


class FakeClient:
    def __init__(self):
        self.calls = []

    def query(self, query, job_config=None, location=None):
        self.calls.append((query, job_config, location))
        return FakeJob()


def test_reject_executes_guarded_candidate_only_transaction():
    client = FakeClient()
    operator = BigQueryMappingOperator("panganlens-demo", client=client)
    reviewed_at = datetime.now(UTC) - timedelta(minutes=1)

    result = operator.reject(
        "a" * 64,
        "fadhil",
        reviewed_at,
        "source identity is not a valid production mapping candidate",
    )

    assert result["status"] == "REJECTED"
    query = client.calls[0][0]
    assert "BEGIN TRANSACTION;" in query
    assert "review_status = 'REJECTED'" in query
    assert "proposed_canonical_id = NULL" in query
    assert "source_entity_mapping" not in query
    assert "COMMIT TRANSACTION;" in query


def test_reject_requires_explicit_review_metadata():
    operator = BigQueryMappingOperator("panganlens-demo", client=FakeClient())
    reviewed_at = datetime.now(UTC) - timedelta(minutes=1)

    with pytest.raises(ValueError, match="lowercase SHA-256"):
        operator.reject("not-a-hash", "fadhil", reviewed_at, "reviewed")
    with pytest.raises(ValueError, match="review_note"):
        operator.reject("a" * 64, "fadhil", reviewed_at, "")
    with pytest.raises(ValueError, match="future"):
        operator.reject(
            "a" * 64,
            "fadhil",
            datetime.now(UTC) + timedelta(days=1),
            "reviewed",
        )


def test_mapping_cli_exposes_reject_with_human_metadata():
    parser = build_parser()
    args = parser.parse_args(
        [
            "--project-id",
            "panganlens-demo",
            "reject",
            "--candidate-fingerprint",
            "a" * 64,
            "--reviewed-by",
            "fadhil",
            "--reviewed-at",
            "2026-08-18T20:00:00+07:00",
            "--review-note",
            "not a valid canonical source identity",
        ]
    )

    assert args.command == "reject"
    assert args.reviewed_by == "fadhil"
    assert args.review_note.startswith("not a valid")


def test_packaged_rejection_sql_matches_canonical_sql():
    canonical = CANONICAL_SQL.read_text(encoding="utf-8")
    packaged = files("panganlens.sql").joinpath(
        "017_reject_mapping_candidate.sql"
    ).read_text(encoding="utf-8")

    assert packaged == canonical
