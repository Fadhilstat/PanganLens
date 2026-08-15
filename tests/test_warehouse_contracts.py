from pathlib import Path

from panganlens.warehouse.contracts import FACT_CONTRACTS


def test_fact_contracts_match_bigquery_primary_keys():
    root = Path(__file__).resolve().parents[1]
    ddl = (root / "sql" / "002_core_3nf.sql").read_text(encoding="utf-8")

    for contract in FACT_CONTRACTS:
        columns = ", ".join(contract.key_columns)
        expected = f"PRIMARY KEY ({columns}) NOT ENFORCED"
        assert expected in ddl, contract.table_name
