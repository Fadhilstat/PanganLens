from panganlens import cli, mapping_cli
from panganlens.dashboard_snapshot import DEFAULT_LOCATION as SNAPSHOT_DEFAULT_LOCATION
from panganlens.schema_contract import WAREHOUSE_LOCATION


def test_operator_facing_location_defaults_follow_schema_contract():
    assert cli.DEFAULT_LOCATION == WAREHOUSE_LOCATION
    assert mapping_cli.DEFAULT_LOCATION == WAREHOUSE_LOCATION
    assert SNAPSHOT_DEFAULT_LOCATION == WAREHOUSE_LOCATION


def test_operator_parsers_use_central_location_default():
    ingestion_args = cli.build_parser().parse_args(
        [
            "--project-id",
            "panganlens-demo",
            "--scope",
            "national",
            "--price-type-id",
            "1",
            "--comcat-id",
            "com_1",
            "--province-id",
            "13",
            "--start-date",
            "2026-08-18",
            "--end-date",
            "2026-08-18",
        ]
    )
    mapping_args = mapping_cli.build_parser().parse_args(
        [
            "--project-id",
            "panganlens-demo",
            "list",
        ]
    )

    assert ingestion_args.location == WAREHOUSE_LOCATION
    assert mapping_args.location == WAREHOUSE_LOCATION
