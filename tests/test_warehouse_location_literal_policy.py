from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = REPO_ROOT / "src" / "panganlens"
WAREHOUSE_LOCATION_LITERAL = "asia-southeast2"

EXPECTED_LITERAL_FILES = {
    "src/panganlens/schema_contract.py",
    "src/panganlens/bootstrap_executor.py",
    "src/panganlens/ingestion/mapping_operator.py",
    "src/panganlens/ingestion/mapping_resolver.py",
    "src/panganlens/ingestion/mapping_review.py",
    "src/panganlens/warehouse/loader.py",
    "src/panganlens/warehouse/promotion.py",
    "src/panganlens/warehouse/run_state.py",
    "src/panganlens/warehouse/staging_writer.py",
}


def test_warehouse_location_literal_debt_is_explicit_and_cannot_grow():
    literal_files = {
        str(path.relative_to(REPO_ROOT))
        for path in SOURCE_ROOT.rglob("*.py")
        if WAREHOUSE_LOCATION_LITERAL in path.read_text(encoding="utf-8")
    }

    assert literal_files == EXPECTED_LITERAL_FILES
