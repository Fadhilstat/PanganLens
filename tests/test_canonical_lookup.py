import pytest

from panganlens.ingestion.mapping_operator import (
    CANONICAL_LOOKUP_MAXIMUM_BYTES_BILLED,
    BigQueryMappingOperator,
)
from panganlens.mapping_cli import build_parser


class FakeRow(dict):
    def items(self):
        return super().items()


class FakeJob:
    def __init__(self, rows):
        self.rows = rows

    def result(self):
        return self.rows


class FakeClient:
    def __init__(self, rows=()):
        self.rows = list(rows)
        self.calls = []

    def query(self, query, job_config=None, location=None):
        self.calls.append((query, job_config, location))
        return FakeJob(self.rows)


@pytest.mark.parametrize(
    ("entity_type", "expected_table"),
    [
        ("commodity", "panganlens_core.commodity"),
        ("channel", "panganlens_core.market_channel"),
        ("region", "panganlens_core.region"),
        ("market", "panganlens_core.market"),
    ],
)
def test_canonical_lookup_is_active_read_only_and_alphabetical(entity_type, expected_table):
    row = FakeRow(canonical_id="id-1", canonical_name="Contoh", context_json="{}")
    client = FakeClient([row])
    operator = BigQueryMappingOperator("panganlens-demo", client=client)

    result = operator.list_canonical_options(entity_type, "contoh", 25)

    assert result[0]["canonical_id"] == "id-1"
    query, config, location = client.calls[0]
    assert expected_table in query
    assert "is_active = TRUE" in query
    assert "ORDER BY canonical_name, canonical_id" in query
    assert "@search" in query
    assert "@limit" in query
    assert "similarity" not in query.lower()
    assert "levenshtein" not in query.lower()
    assert config.maximum_bytes_billed == CANONICAL_LOOKUP_MAXIMUM_BYTES_BILLED
    assert location == "asia-southeast2"


def test_canonical_lookup_validates_entity_search_and_limit():
    operator = BigQueryMappingOperator("panganlens-demo", client=FakeClient())

    with pytest.raises(ValueError, match="entity_type"):
        operator.list_canonical_options("category")
    with pytest.raises(ValueError, match="between 1 and 200"):
        operator.list_canonical_options("commodity", limit=0)
    with pytest.raises(ValueError, match="100 characters"):
        operator.list_canonical_options("commodity", search="a" * 101)


def test_mapping_cli_exposes_canonical_lookup_without_approval_metadata():
    parser = build_parser()
    args = parser.parse_args(
        [
            "--project-id",
            "panganlens-demo",
            "canonical",
            "--entity-type",
            "region",
            "--search",
            "jawa",
            "--limit",
            "20",
        ]
    )

    assert args.command == "canonical"
    assert args.entity_type == "region"
    assert args.search == "jawa"
    assert args.limit == 20
    assert not hasattr(args, "reviewed_by")
