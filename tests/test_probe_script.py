from datetime import date

from panganlens.ingestion.pihps_interface import SourceEvidence, SourceRows
from panganlens.ingestion.pihps_probe import build_probe_summary, previous_business_day


def _capture(rows):
    evidence = SourceEvidence(
        source_url="https://www.bi.go.id/hargapangan/test",
        source_host="www.bi.go.id",
        content_type="application/json",
        payload_bytes=2,
        payload_sha256="0" * 64,
        request_fingerprint="1" * 64,
        schema_fingerprint="2" * 64,
    )
    return SourceRows(rows=tuple(rows), payload_text="{}", evidence=evidence)


class FakeClient:
    def fetch_reference_capture(self, name, params=None):
        assert params is None
        if name == "provinces":
            return _capture([{"id": 13, "name": "DKI Jakarta"}])
        if name == "commodities":
            return _capture(
                [
                    {
                        "cat_id": "1",
                        "denomination": "Rp/kg",
                        "id": "com_3",
                        "name": "Beras",
                        "sort": 1,
                    }
                ]
            )
        raise KeyError(name)

    def fetch_grid_capture(self, request):
        assert request.province_id == "13"
        assert request.comcat_id == "com_3"
        return _capture(
            [
                {
                    "14/08/2026": 15000,
                    "level": 1,
                    "name": "DKI Jakarta",
                    "no": 1,
                }
            ]
        )


def test_previous_business_day_skips_weekend():
    assert previous_business_day(date(2026, 8, 15)) == date(2026, 8, 14)
    assert previous_business_day(date(2026, 8, 17)) == date(2026, 8, 14)


def test_probe_summary_contains_schema_only_evidence():
    summary = build_probe_summary(FakeClient(), date(2026, 8, 15))

    assert summary["status"] == "pass"
    assert summary["probe_window"]["end_date"] == "2026-08-14"
    assert summary["response_shapes"]["grid"]["row_count"] == 1
    assert summary["response_shapes"]["grid"]["normalized_keys"] == (
        "<date>",
        "level",
        "name",
        "no",
    )
