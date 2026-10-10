import csv
import hashlib
import json
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from panganlens.ingestion.pihps_interface import (
    GridRequest,
    PihpsInterfaceError,
    SourceEvidence,
    SourceRows,
)
from panganlens.ingestion.research_sample import (
    RESEARCH_STATUS,
    build_research_sample,
    write_research_sample,
)


def capture(rows):
    payload = json.dumps({"data": rows})
    evidence = SourceEvidence(
        source_url="https://www.bi.go.id/hargapangan/WebSite/TabelHarga/test",
        source_host="www.bi.go.id",
        content_type="application/json",
        payload_bytes=len(payload.encode("utf-8")),
        payload_sha256=hashlib.sha256(payload.encode("utf-8")).hexdigest(),
        request_fingerprint="a" * 64,
        schema_fingerprint="b" * 64,
        requested_at=datetime(2026, 10, 10, 1, tzinfo=UTC),
        completed_at=datetime(2026, 10, 10, 2, tzinfo=UTC),
        http_status=200,
    )
    return SourceRows(tuple(rows), payload, evidence)


def inputs(*, name="DKI Jakarta", price="15.000"):
    provinces = capture([{"id": 13, "name": name}])
    commodities = capture(
        [{"cat_id": "cat_1", "denomination": "kg", "id": "com_3",
          "name": "Beras Medium I", "sort": 3}]
    )
    grid = capture(
        [{"no": 1, "level": "province", "name": name,
          "08/10/2026": price, "09/10/2026": "-"}]
    )
    request = GridRequest(
        price_type_id=1,
        comcat_id="com_3",
        province_id="13",
        start_date=date(2026, 10, 8),
        end_date=date(2026, 10, 9),
    )
    return provinces, commodities, grid, request, date(2026, 10, 10)


def test_research_sample_preserves_real_source_identifiers_without_mapping():
    report, rows = build_research_sample(*inputs())
    assert report["status"] == RESEARCH_STATUS
    assert report["publish_eligible"] is False
    assert report["warehouse_written"] is False
    assert report["usable_price_points"] == 1
    assert report["missing_price_cells"] == 1
    assert report["latest_price_observation_age_days"] == 2
    assert report["review_flags"] == ["SOURCE_MAPPING_NOT_REVIEWED"]
    assert rows[0]["request_province_filter_id"] == "13"
    assert rows[0]["source_commodity_id"] == "com_3"
    assert rows[0]["source_row_name"] == "DKI Jakarta"
    assert rows[0]["price_idr"] == "15000"
    assert rows[0]["review_status"] == RESEARCH_STATUS


def test_research_sample_fails_if_raw_payload_was_modified():
    provinces, commodities, grid, request, today = inputs()
    tampered = SourceRows(grid.rows, grid.payload_text + " ", grid.evidence)
    with pytest.raises(PihpsInterfaceError, match="hash"):
        build_research_sample(provinces, commodities, tampered, request, today)


def test_research_sample_rejects_unknown_commodity_and_category_only():
    provinces, commodities, grid, request, today = inputs()
    with pytest.raises(PihpsInterfaceError, match="exactly one"):
        build_research_sample(
            provinces, capture([{"cat_id": "cat_1", "denomination": "kg",
                                "id": "com_4", "name": "Another", "sort": 4}]),
            grid, request, today
        )
    with pytest.raises(PihpsInterfaceError, match="leaf"):
        build_research_sample(
            provinces, capture([{"cat_id": None, "denomination": "kg",
                                "id": "com_3", "name": "Category", "sort": 1}]),
            grid, request, today
        )


def test_research_sample_rejects_invalid_prices_and_duplicate_keys():
    provinces, commodities, _, request, today = inputs()
    with pytest.raises(PihpsInterfaceError, match="price"):
        build_research_sample(
            provinces, commodities,
            capture([{"no": 1, "level": "province", "name": "DKI Jakarta",
                      "08/10/2026": "12,50"}]), request, today
        )
    duplicate = {"no": 1, "level": "province", "name": "DKI Jakarta",
                 "08/10/2026": "15000"}
    with pytest.raises(PihpsInterfaceError, match="repeated"):
        build_research_sample(
            provinces, commodities, capture([duplicate, duplicate]), request, today
        )


def test_research_sample_rejects_empty_and_future_dated_observations():
    provinces, commodities, _, request, today = inputs()
    with pytest.raises(PihpsInterfaceError, match="no usable price"):
        build_research_sample(
            provinces, commodities,
            capture([{"no": 1, "level": "province", "name": "DKI Jakarta",
                      "08/10/2026": "-"}]), request, today
        )
    future_request = GridRequest(
        price_type_id=1, comcat_id="com_3", province_id="13",
        start_date=date(2026, 10, 11), end_date=date(2026, 10, 11)
    )
    with pytest.raises(ValueError, match="future"):
        build_research_sample(
            provinces, commodities,
            capture([{"no": 1, "level": "province", "name": "DKI Jakarta",
                      "11/10/2026": 15000}]), future_request, today
        )


def test_stale_research_observation_requires_review_not_publish():
    provinces, commodities, _, request, _ = inputs()
    report, _ = build_research_sample(
        provinces, commodities,
        capture([{"no": 1, "level": "province", "name": "DKI Jakarta",
                  "08/10/2026": "15000"}]),
        request, date(2026, 10, 16)
    )
    assert "OBSERVATION_OLDER_THAN_3_DAYS" in report["review_flags"]
    assert report["publish_eligible"] is False


def test_research_files_keep_raw_source_values_and_block_website(tmp_path):
    report, rows = build_research_sample(*inputs(name="=DANGEROUS()"))
    root = tmp_path / "repo"
    website = root / "website"
    website.mkdir(parents=True)
    with pytest.raises(ValueError, match="public website"):
        write_research_sample(report, rows, website / "data", root)

    output = tmp_path / "research"
    manifest, csv_file = write_research_sample(report, rows, output, root)
    loaded = json.loads(manifest.read_text(encoding="utf-8"))
    assert loaded["publish_eligible"] is False
    assert loaded["source_evidence"]["payload_sha256"]
    with csv_file.open(newline="", encoding="utf-8") as file:
        exported = list(csv.DictReader(file))
    assert exported[0]["source_row_name"] == "'=DANGEROUS()"
    assert exported[0]["price_idr"] == "15000"
    assert exported[0]["source_commodity_id"] == "com_3"
    assert "SOURCE_MAPPING_NOT_REVIEWED" in loaded["review_flags"]


def test_research_manifest_rejects_forged_ready_state(tmp_path):
    report, rows = build_research_sample(*inputs())
    report["publish_eligible"] = True
    with pytest.raises(ValueError, match="nonpublishable"):
        write_research_sample(report, rows, tmp_path / "out", Path("."))


def test_province_request_filter_is_not_a_canonical_geographic_row_id():
    provinces, commodities, _, request, today = inputs()
    grid = capture([
        {"no": "I", "level": "0", "name": "Semua Provinsi", "09/10/2026": "16650"},
        {"no": "II", "level": "1", "name": "DKI Jakarta", "09/10/2026": "17050"},
        {"no": "1", "level": "2", "name": "Kota Jakarta Pusat",
         "09/10/2026": "17050"},
    ])
    report, rows = build_research_sample(
        provinces, commodities, grid, request, today
    )
    assert report["request_province_filter_id"] == "13"
    assert report["source_row_level_counts"] == {"0": 1, "1": 1, "2": 1}
    assert {row["source_row_name"] for row in rows} == {
        "Semua Provinsi", "DKI Jakarta", "Kota Jakarta Pusat"
    }
    assert {row["request_province_filter_id"] for row in rows} == {"13"}
    assert all("source_province_id" not in row for row in rows)
    assert report["publish_eligible"] is False
