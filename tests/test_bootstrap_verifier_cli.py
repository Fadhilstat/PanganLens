from argparse import Namespace

from panganlens import bootstrap_verifier_cli
from panganlens.schema_contract import WAREHOUSE_LOCATION


class FakeReport:
    def as_dict(self):
        return {"status": "SCHEMA_READY", "checks": []}


class FakeVerifier:
    def __init__(self, project_id, location):
        self.project_id = project_id
        self.location = location

    def verify(self):
        assert self.project_id == "panganlens-demo"
        assert self.location == WAREHOUSE_LOCATION
        return FakeReport()


def test_verifier_cli_run_returns_schema_report(monkeypatch):
    monkeypatch.setattr(bootstrap_verifier_cli, "BigQueryBootstrapVerifier", FakeVerifier)

    payload = bootstrap_verifier_cli.run(
        Namespace(project_id="panganlens-demo", location=WAREHOUSE_LOCATION)
    )

    assert payload == {"status": "SCHEMA_READY", "checks": []}


def test_verifier_cli_requires_project_id_and_defaults_to_contract_location():
    parser = bootstrap_verifier_cli.build_parser()

    parsed = parser.parse_args(["--project-id", "panganlens-demo"])
    assert parsed.location == WAREHOUSE_LOCATION

    try:
        parser.parse_args([])
    except SystemExit as exc:
        assert exc.code == 2
    else:
        raise AssertionError("--project-id should be required")
